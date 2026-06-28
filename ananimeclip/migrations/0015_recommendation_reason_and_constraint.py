# Generated manually (split from the auto-generated combined migration for clarity)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ananimeclip', '0014_recommendation'),
    ]

    operations = [
        migrations.AddField(
            model_name='recommendation',
            name='reason',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddConstraint(
            model_name='recommendation',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(('anime__isnull', False), ('movie__isnull', True)),
                    models.Q(('anime__isnull', True), ('movie__isnull', False)),
                    _connector='OR',
                ),
                name='recommendation_exactly_one_of_anime_or_movie',
            ),
        ),
    ]
