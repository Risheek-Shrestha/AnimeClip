import django.utils.text
from django.db import migrations, models


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


def add_slug_unique_index(apps, schema_editor):
    """
    Manually create the unique index + like index only if they don't already
    exist.  Django's AlterField would unconditionally CREATE INDEX which
    raises DuplicateTable if a previous migration already created them.
    """
    conn = schema_editor.connection
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'ananimeclip_anime'
              AND indexname = 'ananimeclip_anime_slug_f9e727b2_like'
        """)
        like_exists = cur.fetchone() is not None

        cur.execute("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'ananimeclip_anime'
              AND indexname = 'ananimeclip_anime_slug_key'
        """)
        unique_exists = cur.fetchone() is not None

    if not unique_exists:
        schema_editor.execute(
            'ALTER TABLE "ananimeclip_anime" ADD CONSTRAINT "ananimeclip_anime_slug_key" UNIQUE ("slug")'
        )
    if not like_exists:
        schema_editor.execute(
            'CREATE INDEX "ananimeclip_anime_slug_f9e727b2_like" ON "ananimeclip_anime" ("slug" varchar_pattern_ops)'
        )


def drop_slug_unique_index(apps, schema_editor):
    schema_editor.execute('DROP INDEX IF EXISTS "ananimeclip_anime_slug_f9e727b2_like"')
    schema_editor.execute('ALTER TABLE "ananimeclip_anime" DROP CONSTRAINT IF EXISTS "ananimeclip_anime_slug_key"')


class Migration(migrations.Migration):
    dependencies = [
        ('ananimeclip', '0032_add_is_featured_is_popular_indexes'),
    ]

    operations = [
        # 1. Add Anime.slug column (non-unique first so existing rows don't break).
        #    db_index=False is required here: SlugField defaults to db_index=True,
        #    which makes Django queue a deferred "CREATE INDEX ..._like" statement
        #    that only runs when this migration's schema_editor block exits --
        #    i.e. *after* every operation below, including step 3's manual,
        #    idempotent creation of that exact same index. Without this, step 3
        #    creates the index first (finding it "doesn't exist yet" since
        #    Django's copy is still queued, not applied) and Django's own
        #    deferred SQL then fails with DuplicateTable on the same name.
        migrations.AddField(
            model_name='anime',
            name='slug',
            field=models.SlugField(
                max_length=120,
                blank=True,
                default='',
                db_index=False,
                help_text='URL-safe identifier; auto-populated from title on save.',
            ),
        ),
        # 2. Back-fill slugs for existing rows
        migrations.RunPython(populate_anime_slugs, migrations.RunPython.noop),
        # 3. Add unique constraint + like index — idempotent (skips if already exists)
        migrations.RunPython(add_slug_unique_index, drop_slug_unique_index),
        # 4. Tell Django's state machine the field is now unique (no DDL emitted;
        #    the real DDL was handled by the RunPython above)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='anime',
                    name='slug',
                    field=models.SlugField(
                        max_length=120,
                        unique=True,
                        help_text='URL-safe identifier; auto-populated from title on save.',
                    ),
                ),
            ],
            database_operations=[],  # already done above
        ),
        # 5. Episode thumbnail URL
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
