from django.db import migrations, models
import django.utils.text


def populate_anime_slugs(apps, schema_editor):
    Anime = apps.get_model('ananimeclip', 'Anime')
    seen = {}
    for anime in Anime.objects.order_by('id'):
        base = django.utils.text.slugify(anime.title) or f'anime-{anime.pk}'
        slug = base
        n = 1
        while slug in seen:
            slug = f'{base}-{n}'
            n += 1
        seen[slug] = True
        anime.slug = slug
        anime.save(update_fields=['slug'])


class Migration(migrations.Migration):
    dependencies = [
        ('ananimeclip', '0032_add_is_featured_is_popular_indexes'),
    ]

    operations = [
        # 1. Add Anime.slug (nullable first so existing rows don't break)
        migrations.AddField(
            model_name='anime',
            name='slug',
            field=models.SlugField(
                max_length=120,
                blank=True,
                default='',
                help_text='URL-safe identifier; auto-populated from title on save.',
            ),
        ),
        # 2. Back-fill slugs for existing rows
        migrations.RunPython(populate_anime_slugs, migrations.RunPython.noop),
        # 3. Now enforce uniqueness
        migrations.AlterField(
            model_name='anime',
            name='slug',
            field=models.SlugField(
                max_length=120,
                unique=True,
                help_text='URL-safe identifier; auto-populated from title on save.',
            ),
        ),
        # 4. Episode thumbnail URL (Cloudinary or CDN still frame URL)
        migrations.AddField(
            model_name='episode',
            name='thumbnail_url',
            field=models.URLField(
                max_length=500,
                blank=True,
                default='',
                help_text='Still-frame thumbnail shown in episode lists and hover preview.',
            ),
        ),
    ]
