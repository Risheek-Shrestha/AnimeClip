from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ananimeclip', '0031_add_trailer_url_and_skip_intro'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anime',
            name='is_featured',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='anime',
            name='is_popular',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='movie',
            name='is_featured',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='movie',
            name='is_popular',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
