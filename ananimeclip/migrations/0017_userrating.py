import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ananimeclip', '0016_anime_movie_mal_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'score',
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(10),
                        ]
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'anime',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='user_ratings',
                        to='ananimeclip.anime',
                    ),
                ),
                (
                    'movie',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='user_ratings',
                        to='ananimeclip.movie',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='ratings',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'unique_together': {('user', 'anime'), ('user', 'movie')},
            },
        ),
        migrations.AddConstraint(
            model_name='userrating',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(anime__isnull=False, movie__isnull=True)
                    | models.Q(anime__isnull=True, movie__isnull=False)
                ),
                name='userrating_exactly_one_of_anime_or_movie',
            ),
        ),
    ]
