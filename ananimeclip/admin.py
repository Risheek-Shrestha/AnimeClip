import os

from django import forms
from django.contrib import admin

from .models import (
    Anime,
    Comment,
    CommentLike,
    Episode,
    Genre,
    MediaImage,
    Movie,
    MovieSource,
    Profile,
    Recommendation,
    Season,
    Subtitle,
    VideoSource,
)
from .widgets import CloudinaryVideoWidget

# ── Subtitle (inlined under VideoSource / MovieSource) ─────────────────────────


class SubtitleInline(admin.TabularInline):
    model = Subtitle
    extra = 0
    fields = ('label', 'language_code', 'file_url', 'is_default')


# ── VideoSource ────────────────────────────────────────────────────────────────


class VideoSourceForm(forms.ModelForm):
    class Meta:
        model = VideoSource
        fields = ['episode', 'label', 'type', 'video_url', 'poster']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_url'].widget = CloudinaryVideoWidget(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
            upload_preset='anime_videos_unsigned',
        )


@admin.register(VideoSource)
class VideoSourceAdmin(admin.ModelAdmin):
    form = VideoSourceForm
    inlines = [SubtitleInline]


# ── MovieSource ────────────────────────────────────────────────────────────────


class MovieSourceForm(forms.ModelForm):
    class Meta:
        model = MovieSource
        fields = ['movie', 'label', 'type', 'video_url', 'poster']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_url'].widget = CloudinaryVideoWidget(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
            upload_preset='anime_videos_unsigned',
        )


@admin.register(MovieSource)
class MovieSourceAdmin(admin.ModelAdmin):
    form = MovieSourceForm
    inlines = [SubtitleInline]


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


@admin.register(Subtitle)
class SubtitleAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'language_code', 'is_default')
    list_filter = ('language_code', 'is_default')
    search_fields = ('label', 'video_source__episode__season__anime__title', 'movie_source__movie__title')


# ============================================================
# Transcoding admin actions
# ============================================================


def trigger_transcoding_action(modeladmin, request, queryset):
    """
    Admin action: queue eager Cloudinary transcoding for all selected
    VideoSource / MovieSource rows that have a Cloudinary video URL.

    This is useful to manually re-trigger transcoding after a new video is
    uploaded via the Cloudinary upload widget, or if a previous transcoding
    job failed silently.
    """
    from .transcoding import request_eager_transcoding

    queued = 0
    skipped = 0
    for source in queryset:
        if source.video_url:
            ok = request_eager_transcoding(source.video_url)
            if ok:
                queued += 1
            else:
                skipped += 1
        else:
            skipped += 1

    modeladmin.message_user(
        request,
        f'Queued eager transcoding for {queued} source(s). {skipped} skipped (no URL or non-Cloudinary URL).',
    )


trigger_transcoding_action.short_description = 'Queue eager Cloudinary transcoding (1080p / 720p / 480p / 360p + HLS)'


# Attach the action to the existing VideoSource and MovieSource admins.
# We look up the registered ModelAdmin instances at module load time so we
# don't have to subclass them.
def _patch_admin_actions(model, action):
    """Add *action* to an already-registered ModelAdmin for *model*."""
    try:
        ma = admin.site._registry[model]
        if not hasattr(ma, 'actions') or ma.actions is None:
            ma.actions = [action]
        elif action not in ma.actions:
            ma.actions = list(ma.actions) + [action]
    except KeyError:
        pass  # model not registered — nothing to patch


from .models import MovieSource as _MS  # noqa: E402
from .models import VideoSource as _VS  # noqa: E402

_patch_admin_actions(_VS, trigger_transcoding_action)
_patch_admin_actions(_MS, trigger_transcoding_action)


# ── Content Reports ─────────────────────────────────────────────────────────

from .models import ContentReport, WatchParty, WatchPartyMember  # noqa: E402


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'reason', 'episode', 'movie', 'resolved', 'created_at')
    list_filter = ('reason', 'resolved')
    search_fields = ('user__username', 'detail')
    list_editable = ('resolved',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('user', 'episode', 'movie', 'reason', 'detail', 'created_at')

    actions = ['mark_resolved']

    @admin.action(description='Mark selected reports as resolved')
    def mark_resolved(self, request, queryset):
        updated = queryset.update(resolved=True)
        self.message_user(request, f'{updated} report(s) marked as resolved.')


# ── Watch Party ─────────────────────────────────────────────────────────────


class WatchPartyMemberInline(admin.TabularInline):
    model = WatchPartyMember
    extra = 0
    readonly_fields = ('user', 'joined_at')


@admin.register(WatchParty)
class WatchPartyAdmin(admin.ModelAdmin):
    list_display = ('room_code', 'host', 'episode', 'movie', 'is_active', 'is_playing', 'created_at')
    list_filter = ('is_active', 'is_playing')
    search_fields = ('room_code', 'host__username')
    readonly_fields = ('room_code', 'created_at', 'updated_at')
    inlines = [WatchPartyMemberInline]
