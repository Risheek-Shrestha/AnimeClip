"""
Migration 0037: Feature Pack
Adds:
  - Profile.totp_secret, totp_enabled (2FA)
  - Profile.plan  (subscription tier)
  - PushSubscription model  (web push)
  - Support models: FAQCategory, FAQ, SupportTicket, TicketReply
  - Editorial models: CuratedRow, CuratedRowItem
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ananimeclip", "0036_contentreport_watchparty"),
    ]

    operations = [
        # ── 2FA fields on Profile ──────────────────────────────────────────
        migrations.AddField(
            model_name="profile",
            name="totp_secret",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Base32 TOTP seed. Empty = 2FA not configured.",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="totp_enabled",
            field=models.BooleanField(
                default=False,
                help_text="True once the user has verified their first TOTP code.",
            ),
        ),
        # ── Subscription plan on Profile ───────────────────────────────────
        migrations.AddField(
            model_name="profile",
            name="plan",
            field=models.CharField(
                choices=[("free", "Free"), ("premium", "Premium")],
                default="free",
                max_length=10,
                help_text="Subscription tier. Gated by content_access.py.",
            ),
        ),
        # ── PushSubscription ───────────────────────────────────────────────
        migrations.CreateModel(
            name="PushSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("endpoint", models.URLField(max_length=500, unique=True)),
                ("p256dh", models.TextField()),
                ("auth", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="push_subscriptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"app_label": "ananimeclip"},
        ),
        # ── FAQCategory ────────────────────────────────────────────────────
        migrations.CreateModel(
            name="FAQCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["order", "name"], "verbose_name": "FAQ Category", "verbose_name_plural": "FAQ Categories", "app_label": "ananimeclip"},
        ),
        # ── FAQ ────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="FAQ",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.CharField(max_length=300)),
                ("answer", models.TextField()),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_published", models.BooleanField(default=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="faqs",
                        to="ananimeclip.faqcategory",
                    ),
                ),
            ],
            options={"ordering": ["order"], "app_label": "ananimeclip"},
        ),
        # ── SupportTicket ──────────────────────────────────────────────────
        migrations.CreateModel(
            name="SupportTicket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(max_length=200)),
                ("category", models.CharField(choices=[("billing","Billing"),("playback","Playback Issue"),("account","Account"),("content","Content Request"),("bug","Bug Report"),("other","Other")], default="other", max_length=20)),
                ("body", models.TextField()),
                ("status", models.CharField(choices=[("open","Open"),("in_progress","In Progress"),("resolved","Resolved"),("closed","Closed")], default="open", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_tickets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"], "app_label": "ananimeclip"},
        ),
        # ── TicketReply ────────────────────────────────────────────────────
        migrations.CreateModel(
            name="TicketReply",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("is_staff_reply", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
                ),
                (
                    "ticket",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="replies",
                        to="ananimeclip.supportticket",
                    ),
                ),
            ],
            options={"ordering": ["created_at"], "app_label": "ananimeclip"},
        ),
        # ── CuratedRow ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name="CuratedRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("content_type", models.CharField(choices=[("anime","Anime"),("movie","Movie"),("mixed","Mixed")], default="anime", max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("show_rank_numbers", models.BooleanField(default=False)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["order", "name"], "app_label": "ananimeclip"},
        ),
        # ── CuratedRowItem ─────────────────────────────────────────────────
        migrations.CreateModel(
            name="CuratedRowItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=0)),
                ("badge_text", models.CharField(blank=True, max_length=30)),
                (
                    "anime",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="ananimeclip.anime"),
                ),
                (
                    "movie",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="ananimeclip.movie"),
                ),
                (
                    "row",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="ananimeclip.curatedrow"),
                ),
            ],
            options={"ordering": ["order"], "app_label": "ananimeclip"},
        ),
        migrations.AddConstraint(
            model_name="curatedrowitem",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(anime__isnull=False, movie__isnull=True)
                    | models.Q(anime__isnull=True, movie__isnull=False)
                ),
                name="curated_item_exactly_one",
            ),
        ),
    ]

