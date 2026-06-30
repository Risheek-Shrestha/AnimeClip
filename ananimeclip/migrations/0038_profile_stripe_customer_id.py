from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ananimeclip', '0037_feature_pack'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='stripe_customer_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Stripe Customer ID, set on first checkout. Used to match webhook events back to a Profile.',
                max_length=64,
            ),
        ),
    ]
