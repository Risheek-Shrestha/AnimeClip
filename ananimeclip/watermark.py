"""
Anti-Piracy Canvas Watermark
==============================
Burns the logged-in user's username/email into the video as a canvas overlay
so ripped content can be traced back to the source account.

This is a deterrent — not forensic-grade steganography.

Usage in your streaming template:
    {% load animeclip_extras %}
    <canvas id="wm-canvas" style="position:absolute;top:0;left:0;pointer-events:none;opacity:0.08;z-index:10;"></canvas>
    <script>AnimeClipWatermark.init("{{ request.user|watermark_label }}", document.getElementById('wm-canvas'));</script>

The `watermark_label` template filter is registered below (import it in
templatetags/animeclip_extras.py).

Alternatively, include the pure-CSS layer (no canvas needed):
    <div class="watermark-overlay" data-wm="{{ request.user|watermark_label }}"></div>
    (style it via style-3d.css)
"""

from __future__ import annotations


def get_watermark_label(user) -> str:
    """
    Build the string that will be displayed on the video.
    Uses email if available (harder to fake), falls back to username.
    Partial obfuscation: show first 3 chars + *** so it's identifiable but
    not immediately visible to casual viewers.
    """
    if not user or not user.is_authenticated:
        return ''
    email = getattr(user, 'email', '') or ''
    if email:
        local, _, domain = email.partition('@')
        obscured = local[:3] + '***@' + domain if len(local) > 3 else email
        return obscured
    username = user.username
    return username[:3] + '***' if len(username) > 3 else username


# ── Template filter (register in animeclip_extras.py) ──────────────────────
# In ananimeclip/templatetags/animeclip_extras.py add:
#
#   from ananimeclip.watermark import get_watermark_label
#   @register.filter
#   def watermark_label(user):
#       return get_watermark_label(user)
