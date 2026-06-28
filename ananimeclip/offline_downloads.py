"""
offline_downloads.py — Signed, time-limited offline download links.

What "offline downloads" means here
------------------------------------
Because the video files are stored on Cloudinary (a third-party CDN), we
cannot hand users a file to cache on their device the way a native app
can.  What we *can* do is give authenticated users a direct, time-limited
URL to a specific quality rendition of the video — the browser will save
it as an mp4 file when the user clicks "Download".

The flow:
  1. User visits the streaming / movie page and clicks a quality button
     in the "Download" section (rendered by streaming.html / streaming_movie.html).
  2. The browser POSTs to ``/download/episode/<id>/`` or
     ``/download/movie/<id>/``.
  3. ``generate_download_token()`` creates a signed token that encodes the
     source pk, the desired quality height, and the requesting user's pk.
  4. The view returns a JSON ``{"url": "/dl/<token>/"}`` response.
  5. The browser opens ``/dl/<token>/`` which calls ``serve_download()``.
  6. ``serve_download()`` validates the token (age, user match, quality),
     builds the Cloudinary mp4 URL for the chosen rendition, and issues an
     HTTP 302 redirect directly to that Cloudinary URL so the browser
     downloads the file.

Security properties
-------------------
- Tokens are HMAC-signed using Django's ``django.core.signing`` (same
  mechanism as the playback tokens in video_access.py) so they cannot be
  forged or tampered with.
- Tokens expire after ``DOWNLOAD_TOKEN_MAX_AGE`` seconds (default 1 hour).
- Tokens are bound to the requesting user's pk — another user cannot
  reuse a download link even if they intercept the token.
- The raw Cloudinary URL is never exposed in the browser; the 302 target
  is the Cloudinary URL, but that URL is the already-transcoded mp4 that
  would be discoverable from the HLS manifest anyway.

Download quality options
------------------------
Users can choose from the same renditions produced by the transcoding
pipeline in transcoding.py: 1080p, 720p, 480p, 360p.  If an eager
transform for the requested height hasn't finished yet, Cloudinary falls
back to generating it on-the-fly (a one-time delay).
"""

import logging

from django.core import signing

logger = logging.getLogger(__name__)

SALT = 'ananimeclip.offline-download'
DOWNLOAD_TOKEN_MAX_AGE = 60 * 60  # 1 hour

ALLOWED_HEIGHTS = {360, 480, 720, 1080}

# Map height → (video_codec, quality) — mirrors EAGER_TRANSFORMS in transcoding.py
_HEIGHT_PARAMS = {
    1080: ('h265', 'auto:best'),
    720: ('h264', 'auto:good'),
    480: ('h264', 'auto:good'),
    360: ('h264', 'auto:eco'),
}


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def generate_download_token(
    *,
    source_pk: int,
    source_type: str,  # "episode" | "movie"
    height: int,
    user_pk: int,
) -> str | None:
    """
    Return a signed token embedding all the information needed to serve
    the download later.  Returns None if *height* is not one of the
    allowed quality levels.
    """
    if height not in ALLOWED_HEIGHTS:
        logger.warning(
            'download: rejected token request for unsupported height=%d (user=%d)',
            height,
            user_pk,
        )
        return None

    payload = {
        'spk': source_pk,
        'st': source_type,
        'h': height,
        'uid': user_pk,
    }
    return signing.dumps(payload, salt=SALT, compress=True)


def validate_download_token(token: str, requesting_user_pk: int) -> dict | None:
    """
    Validate *token* and return the decoded payload dict, or None if the
    token is missing / expired / tampered / belongs to a different user.

    The returned dict has keys: spk, st, h, uid.
    """
    if not token:
        return None
    try:
        payload = signing.loads(token, salt=SALT, max_age=DOWNLOAD_TOKEN_MAX_AGE)
    except signing.BadSignature:
        logger.debug('download: bad/expired token (user=%d)', requesting_user_pk)
        return None

    if payload.get('uid') != requesting_user_pk:
        logger.warning(
            'download: token uid=%s does not match requesting user=%d — possible sharing',
            payload.get('uid'),
            requesting_user_pk,
        )
        return None

    return payload


# ---------------------------------------------------------------------------
# Cloudinary rendition URL builder
# ---------------------------------------------------------------------------

import re  # noqa: E402 — after stdlib only

_CL_VIDEO_RE = re.compile(
    r'^(https?://res\.cloudinary\.com/[^/]+/video/upload/)'
    r'(?:v\d+/)?'
    r'([^.]+)\.[A-Za-z0-9]+$'
)


def build_download_url(raw_video_url: str, height: int) -> str | None:
    """
    Construct the Cloudinary delivery URL for a specific quality rendition
    of *raw_video_url* as a progressive-download mp4.

    Returns None if *raw_video_url* is not a Cloudinary video upload URL.
    """
    if not raw_video_url or height not in _HEIGHT_PARAMS:
        return None

    m = _CL_VIDEO_RE.match(raw_video_url)
    if not m:
        return None

    base, public_id = m.group(1), m.group(2)
    vc, q = _HEIGHT_PARAMS[height]
    # Cloudinary transformation: resize to height (maintain aspect), codec, quality
    transform = f'h_{height},c_limit,vc_{vc},q_{q}'
    return f'{base}{transform}/{public_id}.mp4'


# ---------------------------------------------------------------------------
# Quality label helpers (used by templates)
# ---------------------------------------------------------------------------

QUALITY_OPTIONS = [
    {'height': 1080, 'label': '1080p (Full HD)', 'size_hint': '~800 MB/hr'},
    {'height': 720, 'label': '720p (HD)', 'size_hint': '~400 MB/hr'},
    {'height': 480, 'label': '480p (SD)', 'size_hint': '~200 MB/hr'},
    {'height': 360, 'label': '360p (Low)', 'size_hint': '~100 MB/hr'},
]
