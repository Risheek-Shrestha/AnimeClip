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

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)


class SeasonInline(admin.TabularInline):
    model = Season
    extra = 0
    show_change_link = True
    fields = ('number', 'title', 'status', 'release_date')


class MediaImageInline(admin.TabularInline):
    model = MediaImage
    extra = 0
    fields = ('type', 'image')


@admin.register(Anime)
class AnimeAdmin(admin.ModelAdmin):
    list_display = ('title', 'rating', 'age_rating', 'is_featured', 'is_popular', 'studio')
    list_filter = ('is_featured', 'is_popular', 'age_rating', 'genres')
    search_fields = ('title', 'studio', 'country')
    filter_horizontal = ('genres',)
    list_editable = ('is_featured', 'is_popular')
    inlines = [SeasonInline, MediaImageInline]


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'rating', 'age_rating', 'is_featured', 'is_popular', 'duration_mins', 'release_date')
    list_filter = ('is_featured', 'is_popular', 'age_rating', 'genres', 'release_notified')
    search_fields = ('title', 'studio', 'country')
    filter_horizontal = ('genres',)
    list_editable = ('is_featured', 'is_popular')
    inlines = [MediaImageInline]


class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 0
    show_change_link = True
    fields = ('number', 'title', 'duration_mins', 'release_date')


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'release_date', 'release_day')
    list_filter = ('status', 'release_day')
    search_fields = ('anime__title', 'title')
    inlines = [EpisodeInline]


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'duration_mins', 'release_date', 'updated_at')
    list_filter = ('release_day',)
    search_fields = ('season__anime__title', 'title')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'body_preview', 'created_at', 'episode', 'movie')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'body')
    readonly_fields = ('created_at',)

    def body_preview(self, obj):
        return obj.body[:60] + ('…' if len(obj.body) > 60 else '')
    body_preview.short_description = 'Body'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment')
    search_fields = ('user__username',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'age', 'email_verified')
    list_filter = ('email_verified',)
    search_fields = ('user__username', 'user__email')


@admin.register(MediaImage)
class MediaImageAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'type')
    list_filter = ('type',)
    search_fields = ('anime__title', 'movie__title')