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

This is NOT the same as real CDN-level DRM/token-authenticated delivery
(that would require switching the Cloudinary delivery type to
"authenticated" and enabling token auth on the account — an account-level
change, not something this code change can do on its own). Treat this as
raising the bar, not as airtight content protection.
"""
from django.core import signing

SALT = 'ananimeclip.video-stream'
DEFAULT_MAX_AGE = 4 * 60 * 60  # 4 hours


def sign_video_url(raw_url):
    """Wrap a raw video URL in a signed, time-limited token."""
    return signing.dumps(raw_url, salt=SALT, compress=True)


def unsign_video_url(token, max_age=DEFAULT_MAX_AGE):
    """
    Recover the raw URL from a token, or return None if the token is
    missing, tampered with, malformed, or older than max_age seconds.
    """
    if not token:
        return None
    try:
        return signing.loads(token, salt=SALT, max_age=max_age)
    except signing.BadSignature:
        return None
