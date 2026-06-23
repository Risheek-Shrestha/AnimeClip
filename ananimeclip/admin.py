from django.contrib import admin
from django import forms
from .models import (
    Profile, Anime, Movie, Genre, Season, Episode,
    VideoSource, MovieSource, Comment, CommentLike, MediaImage,
    Recommendation
)
from .widgets import CloudinaryVideoWidget
import os


# ── VideoSource ────────────────────────────────────────────────────────────────

class VideoSourceForm(forms.ModelForm):
    class Meta:
        model = VideoSource
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_url'].widget = CloudinaryVideoWidget(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
            upload_preset='anime_videos_unsigned',
        )


@admin.register(VideoSource)
class VideoSourceAdmin(admin.ModelAdmin):
    form = VideoSourceForm


# ── MovieSource ────────────────────────────────────────────────────────────────

class MovieSourceForm(forms.ModelForm):
    class Meta:
        model = MovieSource
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_url'].widget = CloudinaryVideoWidget(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
            upload_preset='anime_videos_unsigned',
        )


@admin.register(MovieSource)
class MovieSourceAdmin(admin.ModelAdmin):
    form = MovieSourceForm


# ── Recommendation (machine-generated — view only, don't hand-edit) ───────────

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'movie', 'score', 'rank', 'generated_at')
    list_filter = ('generated_at',)
    search_fields = ('user__username', 'anime__title', 'movie__title')
    ordering = ('user', 'rank')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ── Everything else ────────────────────────────────────────────────────────────

admin.site.register(Genre)
admin.site.register(Anime)
admin.site.register(Movie)
admin.site.register(Season)
admin.site.register(Episode)
admin.site.register(Comment)
admin.site.register(CommentLike)
admin.site.register(Profile)
admin.site.register(MediaImage)