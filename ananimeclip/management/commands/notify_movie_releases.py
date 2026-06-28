"""
Management command: notify_movie_releases
===========================================
Notifies users who Followed a movie while it was upcoming, once its
release_date has arrived. Run this periodically (e.g. daily via cron
or Celery beat) — the same way warm_recommendations is scheduled.

    python manage.py notify_movie_releases

Idempotent: a movie's Follow-ers are only notified once, tracked via
Movie.release_notified.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import Follow, Movie, Notification


class Command(BaseCommand):
    help = 'Notify followers of movies whose release date has arrived.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        released = Movie.objects.filter(
            release_date__isnull=False,
            release_date__lte=today,
            release_notified=False,
        )

        total = released.count()
        self.stdout.write(f'Checking {total} newly-released movie(s) …')

        notified_movies = 0
        for movie in released.iterator():
            follower_ids = list(Follow.objects.filter(movie=movie).values_list('user_id', flat=True))
            if follower_ids:
                Notification.objects.bulk_create(
                    [
                        Notification(
                            user_id=user_id,
                            notif_type='new_movie',
                            movie=movie,
                            message=f'Now available: {movie.title}',
                        )
                        for user_id in follower_ids
                    ],
                    ignore_conflicts=True,
                )
            movie.release_notified = True
            movie.save(update_fields=['release_notified'])
            notified_movies += 1

        self.stdout.write(self.style.SUCCESS(f'Done — processed {notified_movies} movie(s).'))
