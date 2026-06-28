"""
Management command: warm_recommendations
=========================================
Pre-computes recommendations for active users and persists them to the
Recommendation table (replacing each user's previous rows). Run this
periodically (e.g. nightly via cron or Celery beat).

    python manage.py warm_recommendations
    python manage.py warm_recommendations --limit 20  # top-N per user, per media type
    python manage.py warm_recommendations --users 1 2 3  # specific users
"""

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from ...recommendation_service import save_recommendations
from ...recommendations import RecommendationEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Pre-compute and persist recommendations for active users.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=20, help='Number of recommendations per user, per media type (default: 20)'
        )
        parser.add_argument(
            '--users',
            nargs='*',
            type=int,
            help='Specific user IDs to warm (default: all active users with watch history)',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        user_ids = options['users']

        if user_ids:
            users = User.objects.filter(pk__in=user_ids, is_active=True)
        else:
            # Active users who have at least one watch history entry
            users = User.objects.filter(
                is_active=True,
                watch_history__isnull=False,
            ).distinct()

        total = users.count()
        self.stdout.write(f'Warming recommendations for {total} users …')

        success = failed = 0
        for user in users.iterator(chunk_size=50):
            try:
                engine = RecommendationEngine(user)
                results = engine.recommend(limit=limit)
                save_recommendations(user, results)
                success += 1
            except Exception:
                logger.exception('Failed to warm recs for user %s', user.pk)
                failed += 1

        self.stdout.write(self.style.SUCCESS(f'Done — {success} succeeded, {failed} failed.'))
