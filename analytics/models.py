from django.db import models
from django.conf import settings


class WatchEvent(models.Model):
    """Tracks every watch/play event for analytics."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="watch_events",
    )
    anime_slug = models.SlugField(max_length=200)
    anime_title = models.CharField(max_length=200)
    episode_number = models.PositiveIntegerField(null=True, blank=True)
    genre = models.CharField(max_length=100, blank=True)
    watched_at = models.DateTimeField(auto_now_add=True)
    watch_duration_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["watched_at"]),
            models.Index(fields=["anime_slug"]),
            models.Index(fields=["user", "watched_at"]),
        ]
        ordering = ["-watched_at"]

    def __str__(self):
        return f"{self.anime_title} – ep{self.episode_number} @ {self.watched_at:%Y-%m-%d}"


class SearchEvent(models.Model):
    """Tracks search queries for discovery analytics."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    query = models.CharField(max_length=300)
    results_count = models.PositiveIntegerField(default=0)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["searched_at"])]
        ordering = ["-searched_at"]
