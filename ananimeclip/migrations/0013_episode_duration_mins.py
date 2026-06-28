from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ananimeclip', '0012_playlist_playlistitem_watchlater_watchhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='episode',
            name='duration_mins',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
