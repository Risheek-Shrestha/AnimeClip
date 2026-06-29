"""
Custom template filters for AnimeClip.
"""

from django import template

register = template.Library()


@register.filter(name='split')
def split_filter(value, delimiter=','):
    """Split a string by delimiter. Usage: {{ "a,b,c"|split:"," }}"""
    return str(value).split(delimiter)


# ── Anti-piracy watermark label ─────────────────────────────────────────────
from ananimeclip.watermark import get_watermark_label  # noqa: E402

@register.filter
def watermark_label(user):
    """Return an obfuscated user identifier for the canvas watermark overlay."""
    return get_watermark_label(user)
