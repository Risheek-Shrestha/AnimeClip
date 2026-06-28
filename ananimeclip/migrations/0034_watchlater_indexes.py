from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ananimeclip', '0033_anime_slug_episode_thumbnail'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='watchlater',
            index=models.Index(
                fields=['subprofile', '-added_at'],
                name='wl_subprofile_added_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='watchlater',
            index=models.Index(
                fields=['user', '-added_at'],
                name='wl_user_added_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='playlistitem',
            index=models.Index(
                fields=['playlist', 'added_at'],
                name='playlist_item_playlist_added_idx',
            ),
        ),
    ]
