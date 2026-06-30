"""
Management command: download_geoip_db
=====================================
Downloads the MaxMind GeoLite2-Country database so GeoBlockMiddleware
can actually enforce geo-restrictions.

Usage:
    python manage.py download_geoip_db

Requirements:
    pip install requests
    Set MAXMIND_LICENSE_KEY in your environment (free at maxmind.com).

The DB is written to the path set in GEOIP2_DB_PATH (settings), defaulting
to BASE_DIR/geoip/GeoLite2-Country.mmdb.

Add to your crontab or Celery beat to refresh monthly (MaxMind updates weekly):
    0 3 1 * * cd /app && python manage.py download_geoip_db
"""

import io
import os
import tarfile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Download/refresh the MaxMind GeoLite2-Country database for geo-blocking.'

    def handle(self, *args, **options):
        try:
            import requests
        except ImportError as exc:
            raise CommandError('requests is required: pip install requests') from exc

        license_key = os.getenv('MAXMIND_LICENSE_KEY', '')
        if not license_key:
            raise CommandError(
                'MAXMIND_LICENSE_KEY environment variable is not set.\n'
                'Register for a free key at https://www.maxmind.com/en/geolite2/signup'
            )

        db_path = getattr(settings, 'GEOIP2_DB_PATH', None)
        if not db_path:
            db_path = str(settings.BASE_DIR / 'geoip' / 'GeoLite2-Country.mmdb')

        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        url = (
            f'https://download.maxmind.com/app/geoip_download'
            f'?edition_id=GeoLite2-Country&license_key={license_key}&suffix=tar.gz'
        )
        self.stdout.write('Downloading GeoLite2-Country database…')
        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f'Download failed: {exc}') from exc

        raw = io.BytesIO(resp.content)
        with tarfile.open(fileobj=raw, mode='r:gz') as tar:
            mmdb_member = next((m for m in tar.getmembers() if m.name.endswith('.mmdb')), None)
            if mmdb_member is None:
                raise CommandError('Could not find .mmdb file in the downloaded archive.')
            f = tar.extractfile(mmdb_member)
            with open(db_path, 'wb') as out:
                out.write(f.read())

        self.stdout.write(self.style.SUCCESS(f'GeoLite2-Country database saved to: {db_path}'))
        self.stdout.write(
            self.style.SUCCESS(f'Set GEOIP2_DB_PATH={db_path!r} in your environment to activate geo-blocking.')
        )
