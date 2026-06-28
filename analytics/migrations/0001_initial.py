import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WatchEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anime_slug', models.SlugField(max_length=200)),
                ('anime_title', models.CharField(max_length=200)),
                ('episode_number', models.PositiveIntegerField(blank=True, null=True)),
                ('genre', models.CharField(blank=True, max_length=100)),
                ('watched_at', models.DateTimeField(auto_now_add=True)),
                ('watch_duration_seconds', models.PositiveIntegerField(default=0)),
                ('completed', models.BooleanField(default=False)),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='watch_events',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={'ordering': ['-watched_at']},
        ),
        migrations.CreateModel(
            name='SearchEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=300)),
                ('results_count', models.PositiveIntegerField(default=0)),
                ('searched_at', models.DateTimeField(auto_now_add=True)),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={'ordering': ['-searched_at']},
        ),
        migrations.AddIndex(
            model_name='watchevent',
            index=models.Index(fields=['watched_at'], name='analytics_w_watched_idx'),
        ),
        migrations.AddIndex(
            model_name='watchevent',
            index=models.Index(fields=['anime_slug'], name='analytics_w_slug_idx'),
        ),
        migrations.AddIndex(
            model_name='watchevent',
            index=models.Index(fields=['user', 'watched_at'], name='analytics_w_user_idx'),
        ),
        migrations.AddIndex(
            model_name='searchevent',
            index=models.Index(fields=['searched_at'], name='analytics_s_searched_idx'),
        ),
    ]
