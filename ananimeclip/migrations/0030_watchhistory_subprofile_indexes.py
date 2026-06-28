# Hand-written migration.
#
# What this does
# --------------
# 1. Adds a nullable SubProfile FK to WatchHistory and WatchLater so each
#    sub-profile on an account can have independent watch progress — previously
#    both models were scoped to User, meaning all sub-profiles shared one
#    history list.
#
# 2. Drops the old (user, episode) / (user, movie) unique_together constraints
#    on both models and replaces them with (subprofile, episode) /
#    (subprofile, movie) so two profiles can each track the same episode.
#
# 3. Adds performance indexes on:
#    - WatchHistory  (subprofile, -updated_at) and (user, -updated_at)
#    - Comment       (episode, created_at) and (movie, created_at)
#    - Notification  (user, is_read, -created_at)  ← hit on every page load

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ananimeclip', '0029_subtitle_and_more'),
    ]

    operations = [
        # ── WatchHistory ─────────────────────────────────────────────────────

        # Drop old user-scoped unique constraints first (can't alter while they exist)
        migrations.AlterUniqueTogether(
            name='watchhistory',
            unique_together=set(),
        ),

        # Add nullable subprofile FK
        migrations.AddField(
            model_name='watchhistory',
            name='subprofile',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='watch_history',
                to='ananimeclip.subprofile',
            ),
        ),

        # New unique constraints scoped to sub-profile
        migrations.AlterUniqueTogether(
            name='watchhistory',
            unique_together={('subprofile', 'episode'), ('subprofile', 'movie')},
        ),

        # Performance indexes
        migrations.AddIndex(
            model_name='watchhistory',
            index=models.Index(fields=['subprofile', '-updated_at'], name='wh_subprofile_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='watchhistory',
            index=models.Index(fields=['user', '-updated_at'], name='wh_user_updated_idx'),
        ),

        # ── WatchLater ───────────────────────────────────────────────────────

        migrations.AlterUniqueTogether(
            name='watchlater',
            unique_together=set(),
        ),

        migrations.AddField(
            model_name='watchlater',
            name='subprofile',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='watch_later',
                to='ananimeclip.subprofile',
            ),
        ),

        migrations.AlterUniqueTogether(
            name='watchlater',
            unique_together={('subprofile', 'episode'), ('subprofile', 'movie')},
        ),

        # ── Comment indexes ──────────────────────────────────────────────────

        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['episode', 'created_at'], name='comment_episode_created_idx'),
        ),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['movie', 'created_at'], name='comment_movie_created_idx'),
        ),

        # ── Notification index ───────────────────────────────────────────────
        # The unread-count badge is fetched via context_processors.py on every
        # single page load.  Without this index PostgreSQL does a sequential
        # scan of the entire notification table per request.

        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['user', 'is_read', '-created_at'],
                name='notif_user_read_created_idx',
            ),
        ),
    ]
