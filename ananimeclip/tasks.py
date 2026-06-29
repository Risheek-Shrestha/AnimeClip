"""
Celery tasks for AnimeClip.

These thin wrappers call the existing management-command logic so the same
code can be run both manually (`python manage.py <cmd>`) and automatically
via Celery beat on the schedule defined in settings.CELERY_BEAT_SCHEDULE.
"""

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, name='ananimeclip.tasks.warm_recommendations', max_retries=2)
def warm_recommendations(self):
    """
    Pre-compute collaborative-filter recommendations for all active users
    and persist them to the Recommendation table.

    Equivalent to: python manage.py warm_recommendations
    """
    try:
        from django.core.management import call_command

        call_command('warm_recommendations')
        logger.info('warm_recommendations task completed successfully.')
    except Exception as exc:
        logger.exception('warm_recommendations task failed: %s', exc)
        raise self.retry(exc=exc, countdown=60 * 10) from None  # retry in 10 min


@shared_task(bind=True, name='ananimeclip.tasks.notify_movie_releases', max_retries=2)
def notify_movie_releases(self):
    """
    Notify followers of movies whose release date has arrived today.

    Equivalent to: python manage.py notify_movie_releases
    """
    try:
        from django.core.management import call_command

        call_command('notify_movie_releases')
        logger.info('notify_movie_releases task completed successfully.')
    except Exception as exc:
        logger.exception('notify_movie_releases task failed: %s', exc)
        raise self.retry(exc=exc, countdown=60 * 5) from None  # retry in 5 min


@shared_task(bind=True, name='ananimeclip.tasks.warm_trending_cache', max_retries=1)
def warm_trending_cache(self):
    """
    Pre-warm the trending page cache so the first visitor after expiry
    never hits a slow DB query. Runs every 5 minutes via Celery beat.
    """
    try:
        from django.test import RequestFactory

        from ananimeclip.trending import trending as trending_view

        rf = RequestFactory()
        req = rf.get('/trending/')
        # Use an AnonymousUser so age-filtering uses the public path
        from django.contrib.auth.models import AnonymousUser

        req.user = AnonymousUser()
        trending_view(req)
        logger.info('warm_trending_cache completed.')
    except Exception as exc:
        logger.exception('warm_trending_cache failed: %s', exc)
        raise self.retry(exc=exc, countdown=60) from None
