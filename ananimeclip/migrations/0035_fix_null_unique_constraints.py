"""
Replace unique_together on WatchHistory and WatchLater (which silently allows
multiple NULL rows in PostgreSQL) with conditional UniqueConstraints that
correctly enforce uniqueness for both the sub-profile case (subprofile IS NOT
NULL) and the legacy / no-sub-profile case (subprofile IS NULL).

Also adds a legacy-user constraint so a user without a sub-profile can't have
two rows for the same episode or movie.
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ananimeclip', '0034_watchlater_indexes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── WatchHistory ────────────────────────────────────────────────────
        migrations.AlterUniqueTogether(
            name='watchhistory',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='watchhistory',
            constraint=models.UniqueConstraint(
                condition=models.Q(subprofile__isnull=False, episode__isnull=False),
                fields=['subprofile', 'episode'],
                name='wh_unique_subprofile_episode',
            ),
        ),
        migrations.AddConstraint(
            model_name='watchhistory',
            constraint=models.UniqueConstraint(
                condition=models.Q(subprofile__isnull=False, movie__isnull=False),
                fields=['subprofile', 'movie'],
                name='wh_unique_subprofile_movie',
            ),
        ),
        migrations.AddConstraint(
            model_name='watchhistory',
            constraint=models.UniqueConstraint(
                condition=models.Q(subprofile__isnull=True, episode__isnull=False),
                fields=['user', 'episode'],
                name='wh_unique_user_episode_no_sp',
            ),
        ),
        migrations.AddConstraint(
            model_name='watchhistory',
            constraint=models.UniqueConstraint(
                condition=models.Q(subprofile__isnull=True, movie__isnull=False),
                fields=['user', 'movie'],
                name='wh_unique_user_movie_no_sp',
            ),
        ),
        # ── WatchLater ──────────────────────────────────────────────────────
        migrations.AlterUniqueTogether(
            name='watchlater',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='watchlater',
            constraint=models.UniqueConstraint(
                condition=models.Q(subprofile__isnull=False, episode__isnull=False),
                fields=['subprofile', 'episode'],
                name='wl_unique_subprofile_episode',
            ),
        ),
        migrations.AddConstraint(
            model_name='watchlater',
            constraint=models.UniqueConstraint(
                condition=models.Q(subprofile__isnull=False, movie__isnull=False),
                fields=['subprofile', 'movie'],
                name='wl_unique_subprofile_movie',
            ),
        ),
        migrations.AddConstraint(
            model_name='watchlater',
            constraint=models.UniqueConstraint(
                condition=models.Q(subprofile__isnull=True, episode__isnull=False),
                fields=['user', 'episode'],
                name='wl_unique_user_episode_no_sp',
            ),
        ),
        migrations.AddConstraint(
            model_name='watchlater',
            constraint=models.UniqueConstraint(
                condition=models.Q(subprofile__isnull=True, movie__isnull=False),
                fields=['user', 'movie'],
                name='wl_unique_user_movie_no_sp',
            ),
        ),
    ]
