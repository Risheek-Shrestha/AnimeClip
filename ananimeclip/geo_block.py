"""
Geo-Blocking via MaxMind GeoLite2
====================================
Blocks or allows requests based on the visitor's country, using a local
GeoLite2-Country.mmdb database file (no live API calls).

Setup:
  1. Download the free GeoLite2-Country database from MaxMind:
       https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
  2. Place the .mmdb file somewhere accessible and set in .env:
       GEOIP2_DB_PATH=/path/to/GeoLite2-Country.mmdb
  3. List blocked/allowed country codes in settings:
       GEOBLOCK_DENIED_COUNTRIES = ['CN', 'RU']   # deny these
       GEOBLOCK_ALLOWED_COUNTRIES = []             # empty = allow all others
  4. Add to MIDDLEWARE (after SessionMiddleware):
       'ananimeclip.geo_block.GeoBlockMiddleware'

The database needs to be refreshed periodically (MaxMind updates it monthly).
A cron job / management command to re-download is recommended.
"""

from __future__ import annotations

import logging
import os

from django.conf import settings
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)

_reader = None  # lazy-loaded geoip2 reader


def _get_reader():
    global _reader
    if _reader is not None:
        return _reader
    db_path = getattr(settings, 'GEOIP2_DB_PATH', os.getenv('GEOIP2_DB_PATH', ''))
    if not db_path:
        logger.warning('GeoBlockMiddleware: GEOIP2_DB_PATH not set — geo-blocking disabled.')
        return None
    try:
        import geoip2.database  # type: ignore[import]

        _reader = geoip2.database.Reader(db_path)
        logger.info('GeoBlockMiddleware: loaded %s', db_path)
    except Exception as exc:
        logger.error('GeoBlockMiddleware: could not open DB — %s', exc)
    return _reader


def get_country_code(ip: str) -> str | None:
    reader = _get_reader()
    if reader is None:
        return None
    try:
        response = reader.country(ip)
        return response.country.iso_code  # e.g. "US", "JP"
    except Exception:
        return None


def _client_ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


class GeoBlockMiddleware:
    """
    Checks the visitor's country against GEOBLOCK_DENIED_COUNTRIES (block list)
    and GEOBLOCK_ALLOWED_COUNTRIES (allow list — empty means allow all).
    Returns 403 for blocked countries. Staff/superusers bypass the block.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.denied = set(getattr(settings, 'GEOBLOCK_DENIED_COUNTRIES', []))
        self.allowed = set(getattr(settings, 'GEOBLOCK_ALLOWED_COUNTRIES', []))

    def __call__(self, request):
        # Staff / superusers are never blocked
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return self.get_response(request)

        ip = _client_ip(request)
        country = get_country_code(ip)

        if country:
            if self.denied and country in self.denied:
                return HttpResponseForbidden(f'This content is not available in your region ({country}).')
            if self.allowed and country not in self.allowed:
                return HttpResponseForbidden(f'This content is not available in your region ({country}).')

        return self.get_response(request)
