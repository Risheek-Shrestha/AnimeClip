"""
transcoding.py — Eager multi-resolution transcoding pipeline via Cloudinary.

When a VideoSource or MovieSource gets a new video_url pointing at a
Cloudinary asset, this module fans out an *eager* transformation job so
that Cloudinary pre-generates every rendition we need before the first
viewer ever hits play.

Resolutions produced (height, Cloudinary quality target):
  - 1080p  (vc_h265, q_auto:best)
  - 720p   (vc_h264, q_auto:good)  — primary HLS ladder rung
  - 480p   (vc_h264, q_auto:good)
  - 360p   (vc_h264, q_auto:eco)   — low-bandwidth / mobile

Without eager transforms, Cloudinary generates each streaming rendition
the first time someone requests it (lazy, on-the-fly transcoding).  That
causes a multi-second delay for the very first viewer of every new
upload.  Eager transforms shift that cost to upload time so all
subsequent viewers get instant playback.

The eager transforms also pre-generate the HLS (.m3u8) manifest and the
individual .ts segments so that to_hls_url() in video_access.py returns
a URL that is already warm in Cloudinary's CDN cache.

Usage
-----
The ``request_eager_transcoding(video_url)`` function is the public entry
point.  It is called by the ``post_save`` signal handler in signals.py
whenever a VideoSource / MovieSource is saved with a Cloudinary URL.

It can also be invoked manually from the Django admin via the
``trigger_transcoding`` admin action in admin.py.

Cloudinary SDK note
-------------------
The ``cloudinary.uploader.explicit()`` call is used rather than
``uploader.upload()`` because the video already lives on Cloudinary — we
just need to attach the eager transformation list to the existing asset
without re-uploading the bytes.  ``explicit()`` is designed exactly for
this: it applies transformations to an already-uploaded resource and
returns the full asset metadata including the eager URLs.
"""

import logging
import re

import cloudinary.uploader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cloudinary public_id extractor
# ---------------------------------------------------------------------------

# Matches URLs of the form:
#   https://res.cloudinary.com/<cloud>/video/upload/[v<ver>/]<public_id>.<ext>
#
# public_id may itself contain folder segments (e.g. "my_folder/clip") — those
# are captured as part of group 1, not stripped. The only thing optionally
# skipped before the public_id is a version segment like "v1234567890/".
_PUBLIC_ID_RE = re.compile(
    r'https?://res\.cloudinary\.com/[^/]+/video/upload/'
    r'(?:v\d+/)?'  # optional version segment  v123/
    r'([^.]+)'  # public_id (no extension) — may contain folder segments
    r'\.[A-Za-z0-9]+'  # extension
    r'$'
)


def _extract_public_id(cloudinary_url: str) -> str | None:
    """
    Pull the Cloudinary public_id out of a delivery URL.

    Returns None if the URL does not look like a Cloudinary video upload URL.
    """
    if not cloudinary_url:
        return None
    m = _PUBLIC_ID_RE.match(cloudinary_url)
    if not m:
        return None
    return m.group(1)


# ---------------------------------------------------------------------------
# Eager transformation presets
# ---------------------------------------------------------------------------

#: The set of eager transformations we pre-generate for every video.
#: Each dict is passed directly to the Cloudinary SDK as a transformation.
#:
#: We request both an mp4 rendition (for direct-download / fallback) and
#: an m3u8 (HLS) rendition at each quality rung so the streaming player
#: always has a warm manifest to fetch.
EAGER_TRANSFORMS = [
    # 1080p — best quality, H.265 where supported
    {'streaming_profile': 'full_hd', 'format': 'm3u8'},
    {'width': 1920, 'height': 1080, 'crop': 'limit', 'video_codec': 'h265', 'quality': 'auto:best', 'format': 'mp4'},
    # 720p — primary HLS rung, H.264 for broad device compatibility
    {'streaming_profile': 'hd', 'format': 'm3u8'},
    {'width': 1280, 'height': 720, 'crop': 'limit', 'video_codec': 'h264', 'quality': 'auto:good', 'format': 'mp4'},
    # 480p
    {'width': 854, 'height': 480, 'crop': 'limit', 'video_codec': 'h264', 'quality': 'auto:good', 'format': 'mp4'},
    # 360p — low-bandwidth / mobile
    {'width': 640, 'height': 360, 'crop': 'limit', 'video_codec': 'h264', 'quality': 'auto:eco', 'format': 'mp4'},
    # Adaptive HLS master manifest (Cloudinary picks the right rungs)
    {'streaming_profile': 'auto', 'format': 'm3u8'},
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def request_eager_transcoding(video_url: str) -> bool:
    """
    Ask Cloudinary to eagerly pre-generate all transcoded renditions for
    the asset at *video_url*.

    Returns True if the API call succeeded, False otherwise (the caller
    should treat False as non-fatal — the lazy on-the-fly fallback still
    works, just with a delay for the first viewer).
    """
    public_id = _extract_public_id(video_url)
    if not public_id:
        logger.warning(
            'transcoding: skipping eager transforms — URL does not look like a Cloudinary video upload URL: %s',
            video_url,
        )
        return False

    try:
        result = cloudinary.uploader.explicit(
            public_id,
            type='upload',
            resource_type='video',
            eager=EAGER_TRANSFORMS,
            eager_async=True,  # don't block the web request
            eager_notification_url='',  # set via CLOUDINARY_NOTIFICATION_URL env var if needed
        )
        logger.info(
            'transcoding: eager job queued for public_id=%r (%d transforms). Cloudinary response version=%s',
            public_id,
            len(EAGER_TRANSFORMS),
            result.get('version', '?'),
        )
        return True

    except Exception:  # noqa: BLE001 — log and degrade gracefully
        logger.exception('transcoding: failed to queue eager transforms for public_id=%r', public_id)
        return False


def get_rendition_url(video_url: str, height: int, fmt: str = 'mp4') -> str | None:
    """
    Build the Cloudinary delivery URL for a specific pre-generated rendition.

    height — target height in pixels (360, 480, 720, 1080)
    fmt    — "mp4" for progressive download, "m3u8" for HLS

    Returns None if *video_url* is not a Cloudinary URL.

    This does NOT make any API call — it just constructs the URL that
    Cloudinary will serve once the eager transform has completed.
    """
    if not video_url:
        return None
    m = re.match(
        r'^(https?://res\.cloudinary\.com/[^/]+/video/upload/)'
        r'(?:(?:v\d+/)?)([^.]+)\.[A-Za-z0-9]+$',
        video_url,
    )
    if not m:
        return None
    base, public_id = m.group(1), m.group(2)
    transform = f'h_{height},c_limit,vc_h264,q_auto'
    return f'{base}{transform}/{public_id}.{fmt}'
