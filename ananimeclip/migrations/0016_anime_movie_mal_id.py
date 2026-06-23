# Generated manually (split from the auto-generated combined migration for clarity)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ananimeclip', '0015_recommendation_reason_and_constraint'),
    ]

    operations = [
        migrations.AddField(
            model_name='anime',
            name='mal_id',
            field=models.PositiveIntegerField(
                blank=True, null=True, unique=True,
                help_text='MyAnimeList ID — set when this row was imported from an external API, used to avoid duplicate imports.',
            ),
        ),
        migrations.AddField(
            model_name='movie',
            name='mal_id',
            field=models.PositiveIntegerField(
                blank=True, null=True, unique=True,
                help_text='MyAnimeList ID — set when this row was imported from an external API, used to avoid duplicate imports.',
            ),
        ),
    ]