"""
Editorial / Merchandising Tools
=================================
Admin-driven "Top 10" lists, manual row ordering, and curation flags.
All content is hand-picked by editors via Django admin.
"""

from django.contrib.auth.models import User
from django.db import models

from ananimeclip.models import Anime, Movie


class CuratedRow(models.Model):
    """
    A named editorial row (e.g. "Top 10 This Week", "Staff Picks").
    Items are ordered manually by the `order` field on CuratedRowItem.
    """
    CONTENT_TYPE_CHOICES = [
        ("anime", "Anime"),
        ("movie", "Movie"),
        ("mixed", "Mixed"),
    ]
    name = models.CharField(max_length=100, help_text='Displayed as the row heading, e.g. "Top 10 This Week"')
    slug = models.SlugField(unique=True)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES, default="anime")
    is_active = models.BooleanField(default=True)
    show_rank_numbers = models.BooleanField(default=False, help_text="Show 1–10 rank badges on cards")
    order = models.PositiveIntegerField(default=0, help_text="Sort order on the homepage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["order", "name"]
        app_label = "ananimeclip"

    def __str__(self):
        return self.name

    def items_ordered(self):
        return self.items.select_related("anime", "movie").order_by("order")


class CuratedRowItem(models.Model):
    """One slot in a CuratedRow — points to either an Anime or a Movie."""
    row = models.ForeignKey(CuratedRow, on_delete=models.CASCADE, related_name="items")
    anime = models.ForeignKey(Anime, null=True, blank=True, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, null=True, blank=True, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    badge_text = models.CharField(max_length=30, blank=True, help_text='Optional badge, e.g. "New" or "Exclusive"')

    class Meta:
        ordering = ["order"]
        app_label = "ananimeclip"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(anime__isnull=False, movie__isnull=True)
                    | models.Q(anime__isnull=True, movie__isnull=False)
                ),
                name="curated_item_exactly_one",
            )
        ]

    def __str__(self):
        content = self.anime or self.movie
        return f"{self.row.name} #{self.order}: {content}"

    @property
    def content(self):
        return self.anime or self.movie
