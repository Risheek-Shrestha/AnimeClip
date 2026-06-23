from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ananimeclip', '0018_notification'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Follow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('anime', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='followers', to='ananimeclip.anime')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='follows', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-added_at'],
                'unique_together': {('user', 'anime')},
            },
        ),
    ]