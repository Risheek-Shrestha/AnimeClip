import logging
import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.db.models import Max, Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from analytics.models import SearchEvent

from .content_access import (
    can_view,
    filter_age_appropriate,
    filter_index_context,
    filter_list_age_appropriate,
    filter_movies_context,
    restricted_to_pg13,
)
from .models import (
    Anime,
    Comment,
    CommentLike,
    Episode,
    Follow,
    Genre,
    Movie,
    Notification,
    Playlist,
    PlaylistItem,
    Profile,
    Season,
    SubProfile,
    UserRating,
    WatchHistory,
    WatchLater,
)
from .offline_downloads import (
    QUALITY_OPTIONS,
    build_download_url,
    generate_download_token,
    validate_download_token,
)
from .recommendation_service import get_recommendations, get_similar
from .video_access import sign_video_url, to_hls_url, unsign_video_url

logger = logging.getLogger('ananimeclip')


# ============================================================
# HELPERS
# ============================================================


def attach_episode_info(anime_list):
    for anime in anime_list:
        seasons = list(anime.seasons.all())
        first_season = seasons[0] if seasons else None
        if first_season:
            episodes = list(first_season.episodes.all())
            first_episode = episodes[0] if episodes else None
        else:
            first_episode = None
        anime.first_season = first_season
        anime.first_episode = first_episode
    return anime_list


def safe_cache_get(key):
    try:
        return cache.get(key)
    except Exception:
        logger.warning('Cache GET failed for key: %s', key, exc_info=True)
        return None


def safe_cache_set(key, value, timeout=300):
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        logger.warning('Cache SET failed for key: %s', key, exc_info=True)


def safe_cache_delete(key):
    try:
        cache.delete(key)
    except Exception:
        logger.warning('Cache DELETE failed for key: %s', key, exc_info=True)




def get_active_subprofile(request):
    """
    Return the SubProfile currently active in the session, or None.

    Used to scope WatchHistory / WatchLater queries so each sub-profile on an
    account has independent watch progress — exactly like Netflix profiles.
    Falls back gracefully when no sub-profile is active (e.g. the user hasn't
    selected one yet, or they're on a legacy session).
    """
    if not request.user.is_authenticated:
        return None
    sp_id = request.session.get('active_subprofile_id')
    if not sp_id:
        return None
    try:
        return SubProfile.objects.get(pk=sp_id, user=request.user)
    except SubProfile.DoesNotExist:
        return None

# ============================================================
# INDEX
# ============================================================


def _get_public_index_context():
    CACHE_KEY = 'index:public_context'
    ctx = safe_cache_get(CACHE_KEY)
    if ctx is not None:
        return ctx

    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())

    week_days = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        week_days.append(
            {
                'day': d.strftime('%A'),
                'date': d.strftime('%B ') + str(d.day),
                'id': d.strftime('%A').lower(),
                'is_today': d == today,
            }
        )
    day_names = [d['day'] for d in week_days]

    featured_animes = list(
        Anime.objects.filter(is_featured=True).prefetch_related(
            'media_images',
            'genres',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
    )
    attach_episode_info(featured_animes)

    recent_animes = list(
        Anime.objects.annotate(latest_update=Max('seasons__episodes__updated_at'))
        .order_by('-latest_update')[:8]
        .prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
    )
    attach_episode_info(recent_animes)

    coming_soon_season = (
        Season.objects.filter(status='upcoming', release_date__isnull=False)
        .select_related('anime')
        .prefetch_related('anime__media_images', 'anime__genres', 'episodes__sources')
        .order_by('release_date')
        .first()
    )

    popular_animes = list(
        Anime.objects.filter(is_popular=True).prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
    )
    attach_episode_info(popular_animes)

    scheduled_animes = list(
        Anime.objects.filter(seasons__release_day__in=day_names)
        .prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
        .distinct()
    )
    attach_episode_info(scheduled_animes)

    schedule_map = {}
    for anime in scheduled_animes:
        for season in anime.seasons.all():
            if season.release_day in day_names:
                schedule_map.setdefault(season.release_day, [])
                if anime not in schedule_map[season.release_day]:
                    schedule_map[season.release_day].append(anime)

    for day in week_days:
        day['animes'] = schedule_map.get(day['day'], [])

    top_animes = list(
        Anime.objects.order_by('-rating')[:5].prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes')),
        )
    )
    attach_episode_info(top_animes)

    new_animes = list(
        Anime.objects.annotate(latest_update=Max('seasons__episodes__updated_at'))
        .order_by('-latest_update')[:5]
        .prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes')),
        )
    )
    attach_episode_info(new_animes)

    completed_animes = list(
        Anime.objects.filter(seasons__status='completed')
        .prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes')),
        )
        .distinct()[:5]
    )
    attach_episode_info(completed_animes)

    ctx = {
        'today': today,
        'week_days': week_days,
        'featured_animes': featured_animes,
        'Recent_animes': recent_animes,
        'coming_soon_season': coming_soon_season,
        'Popular_animes': popular_animes,
        'top_animes': top_animes,
        'new_animes': new_animes,
        'completed_animes': completed_animes,
    }
    safe_cache_set(CACHE_KEY, ctx, timeout=300)
    return ctx


def index(request):
    ctx = filter_index_context(_get_public_index_context(), request)

    user_history = []
    user_watch_later = []
    recommended_animes = []

    if request.user.is_authenticated:
        _sp = get_active_subprofile(request)
        _wh_filter = {'subprofile': _sp} if _sp else {'user': request.user}
        user_history = list(
            WatchHistory.objects.filter(**_wh_filter)
            .select_related('episode__season__anime', 'movie')
            .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
            .order_by('-updated_at')[:8]
        )
        user_watch_later = list(
            WatchLater.objects.filter(**_wh_filter)
            .select_related('episode__season__anime', 'movie')
            .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
            .order_by('-added_at')[:8]
        )

        # Recommendations now come from the persisted Recommendation table
        # (filled by `warm_recommendations` / RecommendationEngine), with an
        # on-the-fly compute-and-persist fallback for never-warmed users.
        # Movie recommendations are shown on the Movies page instead, not here.
        recs = get_recommendations(request.user, limit=8)
        recommended_animes = attach_episode_info(list(recs['animes']))

    return render(
        request,
        'index.html',
        {
            'title': 'Animeloop',
            **ctx,
            'user_history': user_history,
            'user_watch_later': user_watch_later,
            'recommended_animes': recommended_animes,
        },
    )


# ============================================================
# MOVIES
# ============================================================


def movies(request):
    today = timezone.now().date()
    CACHE_KEY = 'movies:public_context'
    public = safe_cache_get(CACHE_KEY)

    if public is None:
        public = {
            'featured_movies': list(
                Movie.objects.filter(is_featured=True).prefetch_related('media_images', 'sources', 'genres')[:3]
            ),
            'recent_movies': list(
                Movie.objects.filter(release_date__isnull=False)
                .prefetch_related('media_images', 'sources', 'genres')
                .order_by('-release_date')[:8]
            ),
            'coming_soon_movie': (
                Movie.objects.filter(release_date__gt=today)
                .prefetch_related('media_images', 'sources', 'genres')
                .order_by('release_date')
                .first()
            ),
            'top_rated_movies': list(
                Movie.objects.order_by('-rating')[:6].prefetch_related('media_images', 'sources', 'genres')
            ),
            'popular_movies': list(
                Movie.objects.filter(is_popular=True).prefetch_related('media_images', 'sources', 'genres')
            ),
        }
        safe_cache_set(CACHE_KEY, public, timeout=300)

    public = filter_movies_context(public, request)

    user_history = []
    user_watch_later = []
    recommended_movies = []
    if request.user.is_authenticated:
        _sp = get_active_subprofile(request)
        _wh_filter = {'subprofile': _sp} if _sp else {'user': request.user}
        user_history = list(
            WatchHistory.objects.filter(**_wh_filter, movie__isnull=False)
            .select_related('movie')
            .prefetch_related('movie__media_images')
            .order_by('-updated_at')[:8]
        )
        user_watch_later = list(
            WatchLater.objects.filter(**_wh_filter, movie__isnull=False)
            .select_related('movie')
            .prefetch_related('movie__media_images')
            .order_by('-added_at')[:8]
        )

        # Personalised movie picks live here on the Movies page (anime picks
        # live on the home/Anime page) — see get_recommendations().
        recs = get_recommendations(request.user, limit=8)
        recommended_movies = recs['movies']

    return render(
        request,
        'movies.html',
        {
            'title': 'Animeloop - Movies',
            **public,
            'user_history': user_history,
            'user_watch_later': user_watch_later,
            'recommended_movies': recommended_movies,
        },
    )


# ============================================================
# PROFILE
# ============================================================


@login_required
def profile(request):
    _sp = get_active_subprofile(request)
    _wh_filter = {'subprofile': _sp} if _sp else {'user': request.user}
    history = (
        WatchHistory.objects.filter(**_wh_filter)
        .select_related('episode__season__anime', 'movie')
        .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
        .order_by('-updated_at')[:20]
    )
    watch_later_count = WatchLater.objects.filter(**_wh_filter).count()
    follow_count = Follow.objects.filter(user=request.user).count()
    playlists = Playlist.objects.filter(user=request.user).prefetch_related('items')
    return render(
        request,
        'profile.html',
        {
            'title': f'{request.user.first_name} - Profile',
            'history': history,
            'watch_later_count': watch_later_count,
            'follow_count': follow_count,
            'playlists': playlists,
        },
    )


@login_required
def edit_profile(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        age = request.POST.get('age', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if new_password and new_password != confirm_password:
            return render(
                request,
                'edit_profile.html',
                {
                    'title': 'Edit Profile',
                    'error': 'Passwords do not match.',
                },
            )

        if age:
            try:
                age_int = int(age)
                if not (10 <= age_int <= 80):
                    raise ValueError
            except ValueError:
                return render(
                    request,
                    'edit_profile.html',
                    {
                        'title': 'Edit Profile',
                        'error': 'Age must be a number between 10 and 80.',
                    },
                )
            request.user.profile.age = age_int
            request.user.profile.save()

        request.user.first_name = first_name
        request.user.last_name = last_name
        if new_password:
            request.user.set_password(new_password)
        request.user.save()

        if new_password:
            # Re-authenticate so the session isn't invalidated after password change
            from django.contrib.auth import update_session_auth_hash

            update_session_auth_hash(request, request.user)

        return render(
            request,
            'edit_profile.html',
            {
                'title': 'Edit Profile',
                'success': True,
            },
        )

    return render(request, 'edit_profile.html', {'title': 'Edit Profile'})


# ============================================================
# AUTH
# ============================================================


@never_cache
@ratelimit(key='ip', rate='10/5m', method='POST', block=False)
def login_view(request):
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            return render(
                request,
                'login.html',
                {
                    'title': 'ananimeclip',
                    'error': 'Too many login attempts. Please wait a few minutes and try again.',
                },
            )
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            from django.utils.http import url_has_allowed_host_and_scheme

            next_url = request.POST.get('next') or request.GET.get('next') or ''
            if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                next_url = 'index'
            return redirect(next_url)
        return render(
            request,
            'login.html',
            {
                'title': 'ananimeclip',
                'error': 'Invalid email or password',
            },
        )
    return render(request, 'login.html', {'title': 'ananimeclip'})


@never_cache
@ratelimit(key='ip', rate='5/h', method='POST', block=False)
def signup(request):
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            return render(
                request,
                'signup.html',
                {
                    'title': 'ananimeclip',
                    'error': 'Too many sign-up attempts. Please wait an hour and try again.',
                },
            )
        name = request.POST.get('name', '').strip()
        age = request.POST.get('age')
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            return render(request, 'signup.html', {'title': 'ananimeclip', 'error': 'Passwords do not match'})
        if User.objects.filter(username=email).exists():
            return render(request, 'signup.html', {'title': 'ananimeclip', 'error': 'Email already registered'})

        try:
            age_int = int(age)
            if not (10 <= age_int <= 80):
                raise ValueError
        except (TypeError, ValueError):
            return render(
                request, 'signup.html', {'title': 'ananimeclip', 'error': 'Age must be a number between 10 and 80.'}
            )

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
            is_active=False,
        )
        token = secrets.token_urlsafe(32)
        Profile.objects.create(
            user=user,
            age=age_int,
            verification_token=token,
            verification_sent_at=timezone.now(),
        )

        # Send verification email
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.urls import reverse

        verify_url = request.build_absolute_uri(reverse('verify_email', args=[token]))
        body = render_to_string(
            'verify_email.txt',
            {
                'name': name,
                'verify_url': verify_url,
            },
        )
        send_mail(
            subject='Verify your AnimeClip account',
            message=body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[email],
            fail_silently=True,
        )
        return render(
            request,
            'verify_pending.html',
            {
                'title': 'Check your email',
                'email': email,
            },
        )

    return render(request, 'signup.html', {'title': 'ananimeclip'})


# ============================================================
# STREAMING
# ============================================================


@login_required
def streaming(request, episode_id):
    # Cache only safe primitives (IDs), not live ORM objects.
    # Caching model instances can serve stale related data (e.g. comments) if
    # two users post simultaneously and one write races past the cache-delete.
    CACHE_KEY = f'streaming:episode:{episode_id}'
    cached = safe_cache_get(CACHE_KEY)

    if cached is not None:
        episode_id_c = cached['episode_id']
        anime_id_c = cached['anime_id']
    else:
        episode_id_c = episode_id
        anime_id_c = None

    episode = get_object_or_404(
        Episode.objects.select_related('season__anime').prefetch_related('sources__subtitles'),
        id=episode_id_c,
    )
    anime = get_object_or_404(
        Anime.objects.prefetch_related(
            'media_images',
            'genres',
            Prefetch(
                'seasons',
                queryset=Season.objects.prefetch_related(
                    Prefetch('episodes', queryset=Episode.objects.prefetch_related('sources'))
                ),
            ),
        ),
        pk=anime_id_c if anime_id_c else episode.season.anime_id,
    )

    if not can_view(request, anime.age_rating):
        messages.error(request, "This title is age-restricted and isn't available on this profile.")
        return redirect('index')

    if cached is None:
        safe_cache_set(
            CACHE_KEY,
            {
                'episode_id': episode.pk,
                'anime_id': anime.pk,
            },
            timeout=600,
        )

    seasons = list(anime.seasons.all())
    # Comments are always fetched fresh — they change too frequently to cache
    # and add_comment already invalidates by key, but there's still a race window.
    comments = list(
        episode.comments.filter(parent=None)
        .select_related('user')
        .prefetch_related('replies__user', 'likes', 'replies__likes')
    )

    # Compute next episode across seasons for auto-play
    next_episode = None
    current_season = episode.season
    all_eps_in_season = list(current_season.episodes.order_by('number'))
    current_idx = next((i for i, e in enumerate(all_eps_in_season) if e.pk == episode.pk), None)
    if current_idx is not None and current_idx + 1 < len(all_eps_in_season):
        next_episode = all_eps_in_season[current_idx + 1]
    else:
        # Try the first episode of the next season
        next_season = Season.objects.filter(anime=anime, number__gt=current_season.number).order_by('number').first()
        if next_season:
            next_episode = next_season.episodes.order_by('number').first()

    user_rating = None
    is_following = False
    resume_seconds = 0
    if request.user.is_authenticated:
        try:
            user_rating = UserRating.objects.get(user=request.user, anime=anime)
        except UserRating.DoesNotExist:
            pass
        is_following = Follow.objects.filter(user=request.user, anime=anime).exists()
        _sp = get_active_subprofile(request)
        _wh_lookup = {'subprofile': _sp, 'episode': episode} if _sp else {'user': request.user, 'episode': episode}
        try:
            history_entry = WatchHistory.objects.get(**_wh_lookup)
            resume_seconds = history_entry.progress_seconds
        except WatchHistory.DoesNotExist:
            pass

    similar = get_similar(anime, limit=6)

    # Pick which VideoSource to play. ?source=<id> lets the SUB/DUB/server
    # buttons in the sidebar actually switch sources instead of all pointing
    # at the same default playback. Falls back to the first source if the
    # param is missing, invalid, or doesn't belong to this episode.
    sources = list(episode.sources.all())
    requested_source_id = request.GET.get('source')
    current_source = None
    if requested_source_id:
        current_source = next((s for s in sources if str(s.pk) == requested_source_id), None)
    if current_source is None:
        current_source = sources[0] if sources else None

    # Never put the raw, permanent Cloudinary/video URL in the rendered
    # page — hand out a short-lived signed link instead (see video_access.py).
    playable_url = None
    hls_url = None
    if current_source and current_source.video_url:
        playable_url = reverse('stream_redirect', args=[sign_video_url(current_source.video_url)])
        if to_hls_url(current_source.video_url):
            hls_url = playable_url + '?format=hls'

    return render(
        request,
        'streaming.html',
        {
            'title': anime.title,
            'episode': episode,
            'anime': anime,
            'seasons': seasons,
            'comments': comments,
            'user_rating': user_rating,
            'is_following': is_following,
            'follower_count': anime.followers.count(),
            'resume_seconds': resume_seconds,
            'next_episode': next_episode,
            'current_source': current_source,
            'playable_url': playable_url,
            'hls_url': hls_url,
            'similar': similar,
            'quality_options': QUALITY_OPTIONS,
            # Open Graph / social sharing
            'og_title': f'{anime.title} — Episode {episode.number}' + (f': {episode.title}' if episode.title else ''),
            'og_description': (anime.description or '')[:200],
            'og_type': 'video.episode',
            'og_image': next((img.image.url for img in anime.media_images.all() if img.image), None),
        },
    )


@login_required
def streaming_movie(request, movie_id):
    # Cache only the movie ID, not the ORM object, to avoid stale pickled state.
    CACHE_KEY = f'streaming:movie:{movie_id}'
    cached = safe_cache_get(CACHE_KEY)

    movie = get_object_or_404(
        Movie.objects.prefetch_related('media_images', 'sources__subtitles', 'genres'),
        id=movie_id,
    )

    if not can_view(request, movie.age_rating):
        messages.error(request, "This title is age-restricted and isn't available on this profile.")
        return redirect('index')

    if cached is None:
        safe_cache_set(CACHE_KEY, {'movie_id': movie.pk}, timeout=600)

    # Comments always fetched fresh — too volatile to cache safely.
    comments = list(
        movie.comments.filter(parent=None)
        .select_related('user')
        .prefetch_related('replies__user', 'likes', 'replies__likes')
    )

    user_rating = None
    is_following = False
    resume_seconds = 0
    if request.user.is_authenticated:
        try:
            user_rating = UserRating.objects.get(user=request.user, movie=movie)
        except UserRating.DoesNotExist:
            pass
        is_following = Follow.objects.filter(user=request.user, movie=movie).exists()
        _sp = get_active_subprofile(request)
        _wh_lookup = {'subprofile': _sp, 'movie': movie} if _sp else {'user': request.user, 'movie': movie}
        try:
            history_entry = WatchHistory.objects.get(**_wh_lookup)
            resume_seconds = history_entry.progress_seconds
        except WatchHistory.DoesNotExist:
            pass

    similar = get_similar(movie, limit=6)

    # Same source-switching + signed-URL treatment as streaming() above.
    sources = list(movie.sources.all())
    requested_source_id = request.GET.get('source')
    current_source = None
    if requested_source_id:
        current_source = next((s for s in sources if str(s.pk) == requested_source_id), None)
    if current_source is None:
        current_source = sources[0] if sources else None

    playable_url = None
    hls_url = None
    if current_source and current_source.video_url:
        playable_url = reverse('stream_redirect', args=[sign_video_url(current_source.video_url)])
        if to_hls_url(current_source.video_url):
            hls_url = playable_url + '?format=hls'

    return render(
        request,
        'streaming_movie.html',
        {
            'title': movie.title,
            'movie': movie,
            'comments': comments,
            'user_rating': user_rating,
            'is_following': is_following,
            'follower_count': movie.followers.count(),
            'resume_seconds': resume_seconds,
            'current_source': current_source,
            'playable_url': playable_url,
            'hls_url': hls_url,
            'similar': similar,
            'quality_options': QUALITY_OPTIONS,
        },
    )


@login_required
def stream_redirect(request, token):
    """
    Resolve a short-lived signed playback token (see video_access.py) to
    the real video URL and redirect there. Tokens expire — a copied or
    leaked link stops working instead of granting permanent access.
    Still requires login, same as the streaming pages that hand these out.

    ?format=hls redirects to the same source's adaptive-bitrate HLS
    manifest instead of the plain MP4, when the source is hosted on
    Cloudinary (see video_access.to_hls_url). Anything else falls back to
    the plain MP4 link — same token, same access checks either way.
    """
    raw_url = unsign_video_url(token)
    if not raw_url:
        raise Http404('This playback link has expired or is invalid.')
    if request.GET.get('format') == 'hls':
        hls_url = to_hls_url(raw_url)
        if hls_url:
            return redirect(hls_url)
    return redirect(raw_url)


# ============================================================
# RATINGS
# ============================================================


@login_required
@ratelimit(key='user', rate='30/h', method='POST', block=False)
@require_POST
def rate_anime(request, anime_id):
    from django.db.models import Avg

    anime = get_object_or_404(Anime, id=anime_id)
    try:
        score = int(request.POST.get('score', 0))
        if not (1 <= score <= 10):
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid score'}, status=400)

    UserRating.objects.update_or_create(
        user=request.user,
        anime=anime,
        defaults={'score': score, 'movie': None},
    )
    avg = UserRating.objects.filter(anime=anime).aggregate(avg=Avg('score'))['avg'] or 0
    return JsonResponse({'score': score, 'avg': round(avg, 1)})


@login_required
@ratelimit(key='user', rate='30/h', method='POST', block=False)
@require_POST
def rate_movie(request, movie_id):
    from django.db.models import Avg

    movie = get_object_or_404(Movie, id=movie_id)
    try:
        score = int(request.POST.get('score', 0))
        if not (1 <= score <= 10):
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid score'}, status=400)

    UserRating.objects.update_or_create(
        user=request.user,
        movie=movie,
        defaults={'score': score, 'anime': None},
    )
    avg = UserRating.objects.filter(movie=movie).aggregate(avg=Avg('score'))['avg'] or 0
    return JsonResponse({'score': score, 'avg': round(avg, 1)})


# ============================================================
# COMMENTS
# ============================================================


@login_required
@require_POST
@ratelimit(key='user', rate='20/10m', method='POST', block=False)
def add_comment(request, episode_id):
    if getattr(request, 'limited', False):
        messages.error(request, 'You are posting too fast. Slow down and try again in a bit.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    episode = get_object_or_404(Episode, id=episode_id)
    body = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id')
    if body:
        comment = Comment(episode=episode, user=request.user, body=body)
        if parent_id:
            comment.parent = get_object_or_404(Comment, id=parent_id)
        comment.save()
        safe_cache_delete(f'streaming:episode:{episode_id}')
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
@ratelimit(key='user', rate='20/10m', method='POST', block=False)
def add_movie_comment(request, movie_id):
    if getattr(request, 'limited', False):
        messages.error(request, 'You are posting too fast. Slow down and try again in a bit.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    movie = get_object_or_404(Movie, id=movie_id)
    body = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id')
    if body:
        comment = Comment(movie=movie, user=request.user, body=body)
        if parent_id:
            comment.parent = get_object_or_404(Comment, id=parent_id)
        comment.save()
        safe_cache_delete(f'streaming:movie:{movie_id}')
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@ratelimit(key='user', rate='60/10m', method='POST', block=False)
@require_POST
def like_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    like, created = CommentLike.objects.get_or_create(user=request.user, comment=comment)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({'liked': liked, 'total_likes': comment.total_likes()})


# ============================================================
# FOLLOW / FAVOURITES
# ============================================================


@login_required
@ratelimit(key='user', rate='60/h', method='POST', block=False)
@require_POST
def toggle_follow(request, anime_id):
    anime = get_object_or_404(Anime, id=anime_id)
    obj, created = Follow.objects.get_or_create(user=request.user, anime=anime)
    if not created:
        obj.delete()
        following = False
    else:
        following = True
    return JsonResponse(
        {
            'following': following,
            'follower_count': anime.followers.count(),
        }
    )


@login_required
@ratelimit(key='user', rate='60/h', method='POST', block=False)
@require_POST
def toggle_follow_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    obj, created = Follow.objects.get_or_create(user=request.user, movie=movie)
    if not created:
        obj.delete()
        following = False
    else:
        following = True
    return JsonResponse(
        {
            'following': following,
            'follower_count': movie.followers.count(),
        }
    )


@login_required
@never_cache
def favourites(request):
    follows = (
        Follow.objects.filter(user=request.user, anime__isnull=False)
        .select_related('anime')
        .prefetch_related(
            'anime__media_images',
            'anime__seasons__episodes',
        )
    )
    anime_list = []
    for f in follows:
        anime = f.anime
        seasons = list(anime.seasons.all())
        anime.first_season = seasons[0] if seasons else None
        anime.first_episode = seasons[0].episodes.first() if anime.first_season else None
        anime_list.append(anime)

    movie_follows = (
        Follow.objects.filter(user=request.user, movie__isnull=False)
        .select_related('movie')
        .prefetch_related(
            'movie__media_images',
        )
    )
    movie_list = [f.movie for f in movie_follows]

    return render(
        request,
        'favourites.html',
        {
            'title': 'My Favourites',
            'anime_list': anime_list,
            'movie_list': movie_list,
        },
    )


# ============================================================
# NOTIFICATIONS
# ============================================================


def get_unread_count(user):
    if not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, is_read=False).count()


@login_required
@never_cache
def notifications(request):
    # Count unread BEFORE slicing — Django raises TypeError if you call
    # .filter() on a queryset that has already been sliced with [:n].
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    notifs = Notification.objects.filter(user=request.user).select_related('anime', 'episode', 'movie')[:50]
    # Mark all as read on page visit
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(
        request,
        'notifications.html',
        {
            'title': 'Notifications',
            'notifications': notifs,
            'unread_count': unread_count,
        },
    )


@login_required
@require_POST
def mark_notification_read(request, notif_id):
    Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
    return JsonResponse({'status': 'ok'})


@login_required
def unread_notification_count(request):
    count = get_unread_count(request.user)
    return JsonResponse({'count': count})


# ============================================================
# SEARCH & DISCOVERY
# ============================================================


def live_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    restricted = restricted_to_pg13(request)
    cache_key = f'search:live:{query.lower()[:50]}:{"sfw" if restricted else "all"}'
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return JsonResponse({'results': cached})

    results = []
    # Use PostgreSQL full-text search for relevance ranking; fall back to
    # icontains if the pg extension isn't available (e.g. SQLite in tests).
    try:
        title_vec = SearchVector('title', weight='A')
        sq = SearchQuery(query)
        movie_qs = filter_age_appropriate(
            Movie.objects.annotate(rank=SearchRank(title_vec, sq)).filter(rank__gt=0).order_by('-rank'),
            request,
        )
    except Exception:
        movie_qs = filter_age_appropriate(Movie.objects.filter(title__icontains=query), request)

    for movie in movie_qs[:5]:
        results.append({'id': movie.id, 'title': movie.title, 'type': 'movie'})

    try:
        anime_qs = filter_age_appropriate(
            Anime.objects.annotate(rank=SearchRank(SearchVector('title', weight='A'), SearchQuery(query)))
            .filter(rank__gt=0)
            .order_by('-rank')
            .prefetch_related(Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes'))),
            request,
        )[:5]
    except Exception:
        anime_qs = filter_age_appropriate(Anime.objects.filter(title__icontains=query), request).prefetch_related(
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes'))
        )[:5]
    for a in anime_qs:
        seasons = list(a.seasons.all())
        first_episode = None
        if seasons:
            episodes = list(seasons[0].episodes.all())
            first_episode = episodes[0] if episodes else None
        if first_episode:
            results.append({'id': first_episode.id, 'title': a.title, 'type': 'anime'})

    safe_cache_set(cache_key, results, timeout=60)
    return JsonResponse({'results': results})


def category_page(request, genre):
    cache_key = f'category:{genre.lower()}'
    ctx = safe_cache_get(cache_key)
    if ctx is None:
        movies_qs = list(Movie.objects.filter(genres__name__iexact=genre).prefetch_related('media_images', 'sources'))
        anime_list = list(
            Anime.objects.filter(genres__name__iexact=genre).prefetch_related(
                'media_images',
                Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
            )
        )
        attach_episode_info(anime_list)
        ctx = {'movies': movies_qs, 'anime': anime_list}
        safe_cache_set(cache_key, ctx, timeout=600)

    if restricted_to_pg13(request):
        ctx = {
            'movies': filter_list_age_appropriate(ctx['movies'], request),
            'anime': filter_list_age_appropriate(ctx['anime'], request),
        }
    return render(request, 'category.html', {'title': genre, 'genre': genre, **ctx})


def search_results(request):
    query = request.GET.get('q', '').strip()
    genre = request.GET.get('genre', '').strip()
    year_from = request.GET.get('year_from', '').strip()
    year_to = request.GET.get('year_to', '').strip()
    sort = request.GET.get('sort', 'relevance')  # relevance | rating | newest | oldest
    lang = request.GET.get('lang', '')  # sub | dub | ''

    movies = []
    anime_list = []
    if query:
        movie_qs = filter_age_appropriate(Movie.objects.all(), request)
        anime_qs = filter_age_appropriate(Anime.objects.all(), request)

        # ── Text search ─────────────────────────────────────────────────────
        # PostgreSQL full-text search with title (A) weighted above description
        # (B) so a title match ranks higher than a description-only match.
        # Falls back to icontains for non-PostgreSQL environments (e.g. tests).
        try:
            fts_vector = SearchVector('title', weight='A') + SearchVector('description', weight='B')
            fts_query = SearchQuery(query)
            movie_qs = movie_qs.annotate(rank=SearchRank(fts_vector, fts_query)).filter(rank__gt=0)
            anime_qs = anime_qs.annotate(rank=SearchRank(fts_vector, fts_query)).filter(rank__gt=0)
        except Exception:
            movie_qs = movie_qs.filter(Q(title__icontains=query) | Q(description__icontains=query))
            anime_qs = anime_qs.filter(Q(title__icontains=query) | Q(description__icontains=query))

        # ── Genre filter ─────────────────────────────────────────────────────
        if genre:
            movie_qs = movie_qs.filter(genres__name__iexact=genre)
            anime_qs = anime_qs.filter(genres__name__iexact=genre)

        # ── Year range ───────────────────────────────────────────────────────
        if year_from.isdigit():
            movie_qs = movie_qs.filter(release_date__year__gte=int(year_from))
            anime_qs = anime_qs.filter(release_date__year__gte=int(year_from))
        if year_to.isdigit():
            movie_qs = movie_qs.filter(release_date__year__lte=int(year_to))
            anime_qs = anime_qs.filter(release_date__year__lte=int(year_to))

        # ── Dub / Sub filter (anime only — checks VideoSource.language) ──────
        if lang == 'dub':
            anime_qs = anime_qs.filter(seasons__episodes__sources__language__iexact='dub')
        elif lang == 'sub':
            anime_qs = anime_qs.filter(seasons__episodes__sources__language__iexact='sub')

        # ── Sort — 'relevance' uses FTS rank when available ─────────────────────
        sort_map = {
            'rating': '-average_rating',
            'newest': '-release_date',
            'oldest': 'release_date',
            'relevance': 'title',
        }
        order_field = sort_map.get(sort, 'title')
        movie_qs = movie_qs.order_by(order_field)
        anime_qs = anime_qs.order_by(order_field)

        movies = list(movie_qs.prefetch_related('media_images').distinct())
        anime_list = list(
            anime_qs.prefetch_related(
                'media_images',
                Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes')),
            ).distinct()
        )
        attach_episode_info(anime_list)

        try:
            SearchEvent.objects.create(
                user=request.user if request.user.is_authenticated else None,
                query=query[:300],
                results_count=len(movies) + len(anime_list),
            )
        except Exception:
            logger.warning('Failed to record SearchEvent for query: %s', query, exc_info=True)

    return render(
        request,
        'search_results.html',
        {
            'title': f'Search results for "{query}"' if query else 'Search',
            'query': query,
            'movies': movies,
            'anime_list': anime_list,
            # Filter state — passed back so the template can re-populate the form
            'filter_genre': genre,
            'filter_year_from': year_from,
            'filter_year_to': year_to,
            'filter_sort': sort,
            'filter_lang': lang,
            'all_genres': _all_genre_names(),
        },
    )


def all_categories(request):
    cache_key = 'all_categories'
    genres = safe_cache_get(cache_key)
    if genres is None:
        genres = list(Genre.objects.all())
        safe_cache_set(cache_key, genres, timeout=3600)
    return render(request, 'all_categories.html', {'genres': genres})


# ============================================================
# WATCH HISTORY
# ============================================================


@login_required
@require_POST
@never_cache
def update_watch_history(request):
    episode_id = request.POST.get('episode_id')
    movie_id = request.POST.get('movie_id')
    try:
        progress = int(request.POST.get('progress_seconds', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid progress_seconds value'}, status=400)

    _sp = get_active_subprofile(request)
    if episode_id:
        episode = get_object_or_404(Episode, id=episode_id)
        lookup = {'subprofile': _sp, 'episode': episode} if _sp else {'user': request.user, 'episode': episode}
        WatchHistory.objects.update_or_create(
            **lookup,
            defaults={'user': request.user, 'progress_seconds': progress, 'movie': None},
        )
    elif movie_id:
        movie = get_object_or_404(Movie, id=movie_id)
        lookup = {'subprofile': _sp, 'movie': movie} if _sp else {'user': request.user, 'movie': movie}
        WatchHistory.objects.update_or_create(
            **lookup,
            defaults={'user': request.user, 'progress_seconds': progress, 'episode': None},
        )
    else:
        return JsonResponse({'error': 'No episode or movie id'}, status=400)
    return JsonResponse({'saved': True, 'progress': progress})


@login_required
@never_cache
def continue_watching(request):
    _sp = get_active_subprofile(request)
    _wh_filter = {'subprofile': _sp} if _sp else {'user': request.user}
    history = list(
        WatchHistory.objects.filter(**_wh_filter)
        .order_by('-updated_at')
        .select_related('episode__season__anime', 'movie')
        .prefetch_related('episode__season__anime__media_images', 'movie__media_images')[:20]
    )
    for entry in history:
        if entry.episode and entry.episode.duration_mins:
            total_secs = entry.episode.duration_mins * 60
            entry.progress_pct = min(round(entry.progress_seconds / total_secs * 100), 100)
        elif entry.movie and entry.movie.duration_mins:
            total_secs = entry.movie.duration_mins * 60
            entry.progress_pct = min(round(entry.progress_seconds / total_secs * 100), 100)
        else:
            entry.progress_pct = 0
    return render(request, 'continue_watching.html', {'title': 'Continue Watching', 'history': history})


# ============================================================
# WATCH LATER
# ============================================================


@login_required
@ratelimit(key='user', rate='60/h', method='POST', block=False)
@require_POST
@never_cache
def toggle_watch_later(request):
    episode_id = request.POST.get('episode_id')
    movie_id = request.POST.get('movie_id')

    if episode_id:
        episode = get_object_or_404(Episode, id=episode_id)
        obj, created = WatchLater.objects.get_or_create(user=request.user, episode=episode)
    elif movie_id:
        movie = get_object_or_404(Movie, id=movie_id)
        obj, created = WatchLater.objects.get_or_create(user=request.user, movie=movie)
    else:
        return JsonResponse({'error': 'No id provided'}, status=400)

    if not created:
        obj.delete()
        return JsonResponse({'status': 'removed'})
    return JsonResponse({'status': 'added'})


@login_required
@never_cache
def watch_later(request):
    items = (
        WatchLater.objects.filter(user=request.user)
        .select_related('episode__season__anime', 'movie')
        .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
    )
    return render(request, 'watch_later.html', {'items': items})


# ============================================================
# PLAYLISTS
# ============================================================


@login_required
@never_cache
def playlists(request):
    user_playlists = Playlist.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'playlists.html', {'playlists': user_playlists})


@login_required
@require_POST
def create_playlist(request):
    name = request.POST.get('name', '').strip()
    if name:
        Playlist.objects.create(user=request.user, name=name)
    return redirect('playlists')


@login_required
@never_cache
def playlist_detail(request, playlist_id):
    pl = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    items = pl.items.select_related('episode__season__anime', 'movie').prefetch_related(
        'episode__season__anime__media_images',
        'movie__media_images',
    )
    return render(request, 'playlist_detail.html', {'playlist': pl, 'items': items})


@login_required
@require_POST
def add_to_playlist(request):
    pl = get_object_or_404(Playlist, id=request.POST.get('playlist_id'), user=request.user)
    episode_id = request.POST.get('episode_id')
    movie_id = request.POST.get('movie_id')
    if episode_id:
        PlaylistItem.objects.get_or_create(playlist=pl, episode=get_object_or_404(Episode, id=episode_id))
    elif movie_id:
        PlaylistItem.objects.get_or_create(playlist=pl, movie=get_object_or_404(Movie, id=movie_id))
    else:
        return JsonResponse({'status': 'error', 'message': 'No episode_id or movie_id provided.'}, status=400)
    return JsonResponse({'status': 'added', 'playlist': pl.name})


@login_required
@require_POST
def remove_from_playlist(request, item_id):
    item = get_object_or_404(PlaylistItem, id=item_id, playlist__user=request.user)
    item.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def delete_playlist(request, playlist_id):
    pl = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    pl.delete()
    return redirect('playlists')


@login_required
def get_user_playlists(request):
    data = list(Playlist.objects.filter(user=request.user).values('id', 'name'))
    return JsonResponse({'playlists': data})


# ============================================================
# LIST / BROWSE VIEWS
# ============================================================

# ── Browse sort/filter helpers ───────────────────────────────────────────────

ANIME_SORT_OPTIONS = {
    'recent': ('-latest_update', 'Recently Updated'),
    'rating': ('-rating', 'Highest Rated'),
    'a-z': ('title', 'A → Z'),
    'z-a': ('-title', 'Z → A'),
}

MOVIE_SORT_OPTIONS = {
    'recent': ('-release_date', 'Recently Updated'),
    'rating': ('-rating', 'Highest Rated'),
    'a-z': ('title', 'A → Z'),
    'z-a': ('-title', 'Z → A'),
}


def _apply_anime_filters(qs, request):
    """Apply ?sort= and ?genre= params to an Anime queryset."""
    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'recent')
    if genre:
        qs = qs.filter(genres__name__iexact=genre)
    order = ANIME_SORT_OPTIONS.get(sort, ANIME_SORT_OPTIONS['recent'])[0]
    if sort == 'recent':
        qs = qs.annotate(latest_update=Max('seasons__episodes__updated_at'))
    return qs.order_by(order).distinct(), genre, sort


def _apply_movie_filters(qs, request):
    """Apply ?sort= and ?genre= params to a Movie queryset."""
    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'recent')
    if genre:
        qs = qs.filter(genres__name__iexact=genre)
    order = MOVIE_SORT_OPTIONS.get(sort, MOVIE_SORT_OPTIONS['recent'])[0]
    return qs.order_by(order).distinct(), genre, sort


def _all_genre_names():
    return list(Genre.objects.values_list('name', flat=True).order_by('name'))


# ── Browse views ─────────────────────────────────────────────────────────────


def all_recent_movies(request):
    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'recent')
    is_filtered = bool(genre or sort != 'recent')

    cache_key = 'all_recent_movies'
    movies = None if is_filtered else safe_cache_get(cache_key)

    if movies is None:
        qs = Movie.objects.filter(release_date__isnull=False).prefetch_related('media_images', 'sources', 'genres')
        movies, genre, sort = _apply_movie_filters(qs, request)
        movies = list(movies)
        if not is_filtered:
            safe_cache_set(cache_key, movies, timeout=300)

    return render(
        request,
        'all_recent_movies.html',
        {
            'title': 'Recently Updated Movies',
            'movies': filter_list_age_appropriate(movies, request),
            'genres': _all_genre_names(),
            'active_genre': genre,
            'active_sort': sort,
            'sort_options': MOVIE_SORT_OPTIONS,
        },
    )


def all_popular_movies(request):
    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'recent')
    is_filtered = bool(genre or sort != 'recent')

    cache_key = 'all_popular_movies'
    movies = None if is_filtered else safe_cache_get(cache_key)

    if movies is None:
        qs = Movie.objects.filter(is_popular=True).prefetch_related('media_images', 'sources', 'genres')
        movies, genre, sort = _apply_movie_filters(qs, request)
        movies = list(movies)
        if not is_filtered:
            safe_cache_set(cache_key, movies, timeout=300)

    return render(
        request,
        'all_popular_movies.html',
        {
            'title': 'Popular Movies',
            'movies': filter_list_age_appropriate(movies, request),
            'genres': _all_genre_names(),
            'active_genre': genre,
            'active_sort': sort,
            'sort_options': MOVIE_SORT_OPTIONS,
        },
    )


def all_recent_anime(request):
    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'recent')
    is_filtered = bool(genre or sort != 'recent')

    cache_key = 'all_recent_anime'
    anime_list = None if is_filtered else safe_cache_get(cache_key)

    if anime_list is None:
        qs = Anime.objects.prefetch_related(
            'media_images',
            'genres',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
        anime_list, genre, sort = _apply_anime_filters(qs, request)
        anime_list = list(anime_list)
        attach_episode_info(anime_list)
        if not is_filtered:
            safe_cache_set(cache_key, anime_list, timeout=300)

    return render(
        request,
        'all_recent_anime.html',
        {
            'title': 'Recently Updated Anime',
            'anime_list': filter_list_age_appropriate(anime_list, request),
            'genres': _all_genre_names(),
            'active_genre': genre,
            'active_sort': sort,
            'sort_options': ANIME_SORT_OPTIONS,
        },
    )


def all_popular_anime(request):
    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'recent')
    is_filtered = bool(genre or sort != 'recent')

    cache_key = 'all_popular_anime'
    anime_list = None if is_filtered else safe_cache_get(cache_key)

    if anime_list is None:
        qs = Anime.objects.filter(is_popular=True).prefetch_related(
            'media_images',
            'genres',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
        anime_list, genre, sort = _apply_anime_filters(qs, request)
        anime_list = list(anime_list)
        attach_episode_info(anime_list)
        if not is_filtered:
            safe_cache_set(cache_key, anime_list, timeout=300)

    return render(
        request,
        'all_popular_anime.html',
        {
            'title': 'Popular Anime',
            'anime_list': filter_list_age_appropriate(anime_list, request),
            'genres': _all_genre_names(),
            'active_genre': genre,
            'active_sort': sort,
            'sort_options': ANIME_SORT_OPTIONS,
        },
    )


# ============================================================
# EMAIL VERIFICATION
# ============================================================


def verify_email(request, token):
    """Activate account when user clicks the link in their verification email."""
    from .models import Profile

    try:
        profile = Profile.objects.select_related('user').get(verification_token=token)
    except Profile.DoesNotExist:
        return render(
            request,
            'verify_pending.html',
            {
                'title': 'Invalid link',
                'email': '',
                'error': 'This verification link is invalid or has already been used.',
            },
        )

    if profile.verification_sent_at and timezone.now() - profile.verification_sent_at > timedelta(hours=24):
        return render(
            request,
            'verify_pending.html',
            {
                'title': 'Link expired',
                'email': profile.user.email,
                'error': 'This verification link has expired. Please sign up again to get a new one.',
            },
        )

    if not profile.email_verified:
        profile.email_verified = True
        profile.verification_token = ''  # invalidate so link can't be reused
        profile.save(update_fields=['email_verified', 'verification_token'])
        profile.user.is_active = True
        profile.user.save(update_fields=['is_active'])

    return render(request, 'verify_success.html', {'title': 'Email Verified'})


# ============================================================
# SUB-PROFILE SWITCHER  (Netflix-style "Who's watching?")
# ============================================================

SESSION_KEY = 'active_subprofile_id'


@login_required
def profile_select(request):
    """Who's watching? — pick or create a sub-profile."""
    subprofiles = SubProfile.objects.filter(user=request.user)
    return render(
        request,
        'profile_select.html',
        {
            'title': "Who's watching?",
            'subprofiles': subprofiles,
            'max_reached': subprofiles.count() >= SubProfile.MAX_PER_USER,
            'avatar_choices': SubProfile.AVATAR_CHOICES,
        },
    )


@login_required
def profile_switch(request, subprofile_id):
    """Set the active sub-profile in the session and go home."""
    sp = get_object_or_404(SubProfile, pk=subprofile_id, user=request.user)
    request.session[SESSION_KEY] = sp.pk
    return redirect('index')


@login_required
@require_POST
def profile_create(request):
    """Create a new sub-profile (max 4 per user)."""
    subprofiles = SubProfile.objects.filter(user=request.user)
    if subprofiles.count() >= SubProfile.MAX_PER_USER:
        return JsonResponse({'error': 'Maximum 4 profiles allowed.'}, status=400)

    name = request.POST.get('name', '').strip()[:30]
    avatar = request.POST.get('avatars', 'avatar1')
    kids = request.POST.get('kids_mode') == 'on'

    if not name:
        return JsonResponse({'error': 'Name is required.'}, status=400)

    if SubProfile.objects.filter(user=request.user, name=name).exists():
        return JsonResponse({'error': 'You already have a profile with that name.'}, status=400)

    valid_avatars = [k for k, _ in SubProfile.AVATAR_CHOICES]
    if avatar not in valid_avatars:
        avatar = 'avatar1'

    sp = SubProfile.objects.create(user=request.user, name=name, avatar=avatar, kids_mode=kids)
    request.session[SESSION_KEY] = sp.pk
    return redirect('index')


@login_required
@require_POST
def profile_delete(request, subprofile_id):
    """Delete a sub-profile. Cannot delete the last one."""
    sp = get_object_or_404(SubProfile, pk=subprofile_id, user=request.user)
    if SubProfile.objects.filter(user=request.user).count() <= 1:
        return JsonResponse({'error': 'You must keep at least one profile.'}, status=400)
    if request.session.get(SESSION_KEY) == sp.pk:
        del request.session[SESSION_KEY]
    sp.delete()
    return redirect('profile_select')




# ============================================================
# HEALTH CHECK + ROBOTS
# ============================================================


def healthz(request):
    """Minimal liveness probe for Docker / load-balancer health checks."""
    return JsonResponse({'status': 'ok'})


def robots_txt(request):
    """Serve a robots.txt that blocks bots from private / API paths."""
    from django.http import HttpResponse
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /api/',
        'Disallow: /watch/',
        'Disallow: /dl/',
        'Disallow: /download/',
        'Disallow: /watch-history/',
        'Disallow: /profiles/',
        'Allow: /',
        '',
        '# Update this URL to match your real domain before deploying.',
        'Sitemap: https://animeclip.example.com/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


# ============================================================
# ERROR HANDLERS
# ============================================================


# ============================================================
# OFFLINE DOWNLOADS
# ============================================================

import json as _json  # noqa: E402
import re as _re  # noqa: E402

from django.http import HttpResponseRedirect  # noqa: E402


@login_required
@require_POST
def request_episode_download(request, episode_id):
    """
    POST /download/episode/<episode_id>/
    Body (JSON or form): { "source_id": <int>, "height": <360|480|720|1080> }

    Returns JSON: { "url": "/dl/<token>/" }  which the client opens to
    trigger the actual file download.
    """
    episode = get_object_or_404(Episode, pk=episode_id)
    if not can_view(request, episode.season.anime):
        return JsonResponse({'error': 'Access denied.'}, status=403)

    try:
        body = _parse_download_request(request)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    source_id = body.get('source_id')
    height = body.get('height')

    qs = episode.sources.all()
    source = get_object_or_404(qs, pk=source_id) if source_id else (qs.first() if qs.exists() else None)
    if source is None:
        return JsonResponse({'error': 'No video source available for this episode.'}, status=404)

    token = generate_download_token(
        source_pk=source.pk,
        source_type='episode',
        height=height,
        user_pk=request.user.pk,
    )
    if token is None:
        return JsonResponse({'error': f'Unsupported quality: {height}p.'}, status=400)

    return JsonResponse({'url': reverse('serve_download', args=[token])})


@login_required
@require_POST
def request_movie_download(request, movie_id):
    """
    POST /download/movie/<movie_id>/
    Body (JSON or form): { "source_id": <int>, "height": <360|480|720|1080> }

    Returns JSON: { "url": "/dl/<token>/" }
    """
    movie = get_object_or_404(Movie, pk=movie_id)
    if not can_view(request, movie):
        return JsonResponse({'error': 'Access denied.'}, status=403)

    try:
        body = _parse_download_request(request)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    source_id = body.get('source_id')
    height = body.get('height')

    qs = movie.sources.all()
    source = get_object_or_404(qs, pk=source_id) if source_id else (qs.first() if qs.exists() else None)
    if source is None:
        return JsonResponse({'error': 'No video source available for this movie.'}, status=404)

    token = generate_download_token(
        source_pk=source.pk,
        source_type='movie',
        height=height,
        user_pk=request.user.pk,
    )
    if token is None:
        return JsonResponse({'error': f'Unsupported quality: {height}p.'}, status=400)

    return JsonResponse({'url': reverse('serve_download', args=[token])})


@login_required
def serve_download(request, token):
    """
    GET /dl/<token>/

    Validates the signed token and redirects to the Cloudinary mp4 URL
    for the requested quality rendition.  Cloudinary's fl_attachment flag
    ensures the browser pops a Save-As dialog rather than playing inline.
    """
    from .models import MovieSource, VideoSource

    payload = validate_download_token(token, request.user.pk)
    if payload is None:
        raise Http404('Download link is invalid or has expired.')

    source_pk = payload['spk']
    source_type = payload['st']
    height = payload['h']

    if source_type == 'episode':
        source = get_object_or_404(VideoSource, pk=source_pk)
        if not can_view(request, source.episode.season.anime):
            raise Http404
        raw_url = source.video_url
        filename_base = f'{source.episode.season.anime.title}_S{source.episode.season.number}E{source.episode.number}'
    else:
        source = get_object_or_404(MovieSource, pk=source_pk)
        if not can_view(request, source.movie):
            raise Http404
        raw_url = source.video_url
        filename_base = source.movie.title

    if not raw_url:
        raise Http404('No video file is attached to this source.')

    dl_url = build_download_url(raw_url, height)
    if dl_url is None:
        logger.warning('serve_download: non-Cloudinary URL for source pk=%d, falling back to raw', source_pk)
        dl_url = raw_url

    # Insert fl_attachment so Cloudinary adds Content-Disposition: attachment.
    safe_name = ''.join(c if c.isalnum() or c in '-_ ' else '_' for c in filename_base)
    if 'res.cloudinary.com' in dl_url and 'fl_attachment' not in dl_url:
        dl_url = _re.sub(
            r'(/video/upload/)',
            rf'\1fl_attachment:{safe_name}_{height}p/',
            dl_url,
            count=1,
        )

    return HttpResponseRedirect(dl_url)


def _parse_download_request(request):
    """
    Parse JSON or form-encoded body.  Returns dict with 'source_id' (int|None)
    and 'height' (int).  Raises ValueError on bad input.
    """
    content_type = request.content_type or ''
    if 'application/json' in content_type:
        try:
            data = _json.loads(request.body)
        except _json.JSONDecodeError as exc:
            raise ValueError('Request body is not valid JSON.') from exc
    else:
        data = request.POST

    try:
        height = int(data.get('height', 720))
    except (TypeError, ValueError) as exc:
        raise ValueError("'height' must be an integer (360, 480, 720, or 1080).") from exc

    source_id_raw = data.get('source_id')
    source_id = int(source_id_raw) if source_id_raw else None

    return {'source_id': source_id, 'height': height}


# ============================================================
# ERROR HANDLERS
# ============================================================


def handler404(request, exception=None):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)
