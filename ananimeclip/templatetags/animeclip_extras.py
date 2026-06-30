"""
Custom template filters for AnimeClip.
"""

from django import template

from ananimeclip.watermark import get_watermark_label

register = template.Library()


@register.filter(name='split')
def split_filter(value, delimiter=','):
    """Split a string by delimiter. Usage: {{ "a,b,c"|split:"," }}"""
    return str(value).split(delimiter)


# ── Anti-piracy watermark label ────────────────────────────────────────────


@register.filter
def watermark_label(user):
    """Return an obfuscated user identifier for the canvas watermark overlay."""
    return get_watermark_label(user)


@register.filter
def dict_get(d, key):
    """Look up a key in a dict from a template. Usage: {{ mydict|dict_get:key }}"""
    if isinstance(d, dict):
        return d.get(key, [])
    return []
