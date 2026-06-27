from django.contrib import admin
from .models import WatchEvent, SearchEvent


@admin.register(WatchEvent)
class WatchEventAdmin(admin.ModelAdmin):
    list_display = ("anime_title", "episode_number", "user", "watched_at", "completed")
    list_filter = ("completed", "genre")
    search_fields = ("anime_title", "anime_slug")


@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = ("query", "results_count", "user", "searched_at")
    search_fields = ("query",)
