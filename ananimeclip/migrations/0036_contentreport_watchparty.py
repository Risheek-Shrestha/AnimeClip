import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ananimeclip', '0035_fix_null_unique_constraints'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'reason',
                    models.CharField(
                        max_length=30,
                        choices=[
                            ('broken_video', 'Broken / unplayable video'),
                            ('wrong_audio', 'Wrong audio track'),
                            ('wrong_subtitles', 'Wrong or missing subtitles'),
                            ('wrong_episode', 'Wrong episode content'),
                            ('copyright', 'Copyright violation'),
                            ('inappropriate', 'Inappropriate content'),
                            ('other', 'Other'),
                        ],
                    ),
                ),
                ('detail', models.TextField(blank=True, max_length=500)),
                ('resolved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='content_reports',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'episode',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='reports',
                        to='ananimeclip.episode',
                    ),
                ),
                (
                    'movie',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='reports',
                        to='ananimeclip.movie',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['resolved', '-created_at'], name='report_resolved_created_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='WatchParty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_code', models.CharField(max_length=8, unique=True, db_index=True)),
                ('is_active', models.BooleanField(default=True)),
                ('playback_position', models.FloatField(default=0.0, help_text='Seconds into the content')),
                ('is_playing', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'host',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='hosted_parties',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'episode',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='watch_parties',
                        to='ananimeclip.episode',
                    ),
                ),
                (
                    'movie',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='watch_parties',
                        to='ananimeclip.movie',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WatchPartyMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                (
                    'party',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='members',
                        to='ananimeclip.watchparty',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='watch_party_memberships',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'unique_together': {('party', 'user')},
            },
        ),
    ]
