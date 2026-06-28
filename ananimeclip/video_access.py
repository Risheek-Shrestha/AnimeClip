"""
Time-limited "signed" playback links for video sources.

Video files are stored as permanent, unauthenticated URLs (Cloudinary
`secure_url`s returned by the unsigned upload widget — see widgets.py).
That means anyone who gets hold of one of those raw URLs can stream or
re-share it forever, completely bypassing the age-gate, login, and any
future paywall — the checks in content_access.py only ever protect the
*page* that reveals the link, never the link itself.

This module closes part of that gap at the Django layer: instead of ever
putting the raw, permanent URL in rendered HTML, views hand out a
short-lived signed token (via sign_video_url) that resolves through
views.stream_redirect back to the real URL, then expires. Every playback
request is funnelled back through this app's own access checks, and a
copied/leaked link stops working after DEFAULT_MAX_AGE instead of working
forever.

CDN-level token authentication (CLOUDINARY_AUTH_TOKEN)
-------------------------------------------------------
For *real* CDN-enforced protection set the following in your Cloudinary
account dashboard:

  1. Change the delivery type of video assets to "authenticated".
  2. Enable "Token-based access control" on your account.
  3. Set CLOUDINARY_AUTH_TOKEN_KEY in your .env to the signing key provided
     by Cloudinary.

When CLOUDINARY_AUTH_TOKEN_KEY is present, ``sign_video_url`` will append a
Cloudinary auth_token to the URL so even the raw Cloudinary link itself
expires and requires a valid token — making it impossible to use a captured
redirect target as a permanent link.
"""

import hashlib
import hmac
import re
import time

from django.conf import settings
from django.core import signing

SALT = 'ananimeclip.video-stream'
DEFAULT_MAX_AGE = 4 * 60 * 60  # 4 hours

# Matches Cloudinary's video delivery URL shape, e.g.
#   https://res.cloudinary.com/<cloud>/video/upload/v123/some_id.mp4
# Capturing the bit right after "/upload/" lets us insert a streaming-profile
# transformation (sp_auto) without disturbing the version/public_id that follow.
_CLOUDINARY_VIDEO_UPLOAD_RE = re.compile(r'^(https?://res\.cloudinary\.com/[^/]+/video/upload/)(.+)\.[A-Za-z0-9]+$')


def _build_cloudinary_auth_token(url: str, expiry: int) -> str | None:
    """
    Append a Cloudinary token-auth query string to *url* so that Cloudinary's
    CDN edge enforces expiry — meaning even a leaked raw Cloudinary URL stops
    working after *expiry* seconds from now.

    Requires:
      - CLOUDINARY_AUTH_TOKEN_KEY set in settings / .env
      - Assets uploaded as delivery_type="authenticated" on the Cloudinary side

    Returns None (no-op) when the key is absent so the app degrades gracefully
    to Django-layer signing only.
    """
    key_hex = getattr(settings, 'CLOUDINARY_AUTH_TOKEN_KEY', None)
    if not key_hex:
        return None

    try:
        key_bytes = bytes.fromhex(key_hex)
    except ValueError:
        import logging
        logging.getLogger(__name__).error(
            'CLOUDINARY_AUTH_TOKEN_KEY is not valid hex — CDN token auth disabled.'
        )
        return None

    exp = int(time.time()) + expiry
    # Cloudinary token auth spec:
    #   HMAC-SHA256 over "exp=<expiry>~url=<url_path>" (tilde-separated)
    # See: https://cloudinary.com/documentation/video_player_token_authentication
    url_path = re.sub(r'^https?://[^/]+', '', url)
    to_sign = f'exp={exp}~url={url_path}'
    digest = hmac.new(key_bytes, to_sign.encode(), hashlib.sha256).hexdigest()
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}__cld_token__=exp={exp}~hmac={digest}'


def sign_video_url(raw_url: str) -> str:
    """Wrap a raw video URL in a signed, time-limited Django token."""
    return signing.dumps(raw_url, salt=SALT, compress=True)


def unsign_video_url(token, max_age=DEFAULT_MAX_AGE):
    """
    Recover the raw URL from a token, or return None if the token is
    missing, tampered with, malformed, or older than max_age seconds.

    If CLOUDINARY_AUTH_TOKEN_KEY is configured, also returns a Cloudinary
    CDN-signed URL so the redirect target itself expires at the CDN edge.
    """
    if not token:
        return None
    try:
        raw_url = signing.loads(token, salt=SALT, max_age=max_age)
    except signing.BadSignature:
        return None

    # Upgrade to CDN-signed URL when token auth is configured.
    cdn_url = _build_cloudinary_auth_token(raw_url, expiry=DEFAULT_MAX_AGE)
    return cdn_url if cdn_url else raw_url


def to_hls_url(raw_url):
    """
    Turn a Cloudinary video URL into an adaptive-bitrate HLS manifest URL by
    inserting the `sp_auto` streaming-profile transformation and switching
    the extension to .m3u8. Cloudinary generates the multi-bitrate
    renditions from the *same* already-uploaded asset on first request —
    no re-upload or admin workflow change needed.

    Returns None for anything that isn't a recognizable Cloudinary video
    upload URL (e.g. an admin pasted an arbitrary external URL), so callers
    can cleanly fall back to plain MP4 instead of generating a broken link.

    Note: the very first request for a given video pays a one-time
    transcoding delay while Cloudinary processes it; subsequent requests
    are served from cache. This also consumes Cloudinary transformation
    credits, so it's worth keeping an eye on usage at scale.
    """
    if not raw_url:
        return None
    match = _CLOUDINARY_VIDEO_UPLOAD_RE.match(raw_url)
    if not match:
        return None
    prefix, rest = match.groups()
    return f'{prefix}sp_auto/{rest}.m3u8'
