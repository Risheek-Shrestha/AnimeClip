from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ananimeclip', '0017_userrating'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notif_type', models.CharField(choices=[('new_episode', 'New Episode'), ('new_movie', 'New Movie'), ('watch_later_available', 'Watch Later Available')], max_length=30)),
                ('message', models.CharField(max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('anime', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ananimeclip.anime')),
                ('episode', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ananimeclip.episode')),
                ('movie', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ananimeclip.movie')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]