from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add indexes on columns that appear frequently in WHERE / ORDER BY clauses
    but had no index:

    - Anime.is_featured, Anime.is_popular  (homepage filters)
    - Movie.is_featured, Movie.is_popular  (homepage filters)
    - Movie.release_date                   (notify_movie_releases command)
    - Season.status                        (ongoing / upcoming filters)
    - WatchHistory.updated_at              (continue-watching ordering)
    - Notification.is_read + user          (unread count query)
    """

    dependencies = [
        ('ananimeclip', '0026_profile_verification_sent_at'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='anime',
            index=models.Index(fields=['is_featured'], name='anime_is_featured_idx'),
        ),
        migrations.AddIndex(
            model_name='anime',
            index=models.Index(fields=['is_popular'], name='anime_is_popular_idx'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['is_featured'], name='movie_is_featured_idx'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['is_popular'], name='movie_is_popular_idx'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['release_date'], name='movie_release_date_idx'),
        ),
        migrations.AddIndex(
            model_name='season',
            index=models.Index(fields=['status'], name='season_status_idx'),
        ),
        migrations.AddIndex(
            model_name='watchhistory',
            index=models.Index(fields=['user', '-updated_at'], name='watchhistory_user_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'is_read'], name='notification_user_is_read_idx'),
        ),
    ]
