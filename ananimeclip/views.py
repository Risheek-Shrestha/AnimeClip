from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.core.cache import cache
from django.http import JsonResponse
from .models import (
    Profile, Anime, Episode, Comment, CommentLike,
    Season, MediaImage, Movie, Genre,
    WatchHistory, WatchLater, Playlist, PlaylistItem, UserRating, Notification, Follow,
)
from .recommendation_service import get_recommendations
from django.db.models import Max, Prefetch, Q
from django.utils import timezone
from datetime import timedelta


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
        return None


def safe_cache_set(key, value, timeout=300):
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        pass


def safe_cache_delete(key):
    try:
        cache.delete(key)
    except Exception:
        pass


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
        week_days.append({
            'day': d.strftime('%A'),
            'date': d.strftime('%B ') + str(d.day),
            'id': d.strftime('%A').lower(),
            'is_today': d == today,
        })
    day_names = [d['day'] for d in week_days]

    featured_animes = list(
        Anime.objects.filter(is_featured=True).prefetch_related(
            'media_images', 'genres',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
    )
    attach_episode_info(featured_animes)

    recent_animes = list(
        Anime.objects.annotate(
            latest_update=Max('seasons__episodes__updated_at')
        ).order_by('-latest_update')[:8].prefetch_related(
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
        Anime.objects.filter(seasons__release_day__in=day_names).prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        ).distinct()
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
        Anime.objects.annotate(
            latest_update=Max('seasons__episodes__updated_at')
        ).order_by('-latest_update')[:5].prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes')),
        )
    )
    attach_episode_info(new_animes)

    completed_animes = list(
        Anime.objects.filter(seasons__status='completed').prefetch_related(
            'media_images',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes')),
        ).distinct()[:5]
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
    ctx = _get_public_index_context()

    user_history = []
    user_watch_later = []
    recommended_animes = []
    recommended_movies = []

    if request.user.is_authenticated:
        user_history = list(
            WatchHistory.objects.filter(user=request.user)
            .select_related('episode__season__anime', 'movie')
            .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
            .order_by('-updated_at')[:8]
        )
        user_watch_later = list(
            WatchLater.objects.filter(user=request.user)
            .select_related('episode__season__anime', 'movie')
            .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
            .order_by('-added_at')[:8]
        )

        # Recommendations now come from the persisted Recommendation table
        # (filled by `warm_recommendations` / RecommendationEngine), with an
        # on-the-fly compute-and-persist fallback for never-warmed users.
        recs = get_recommendations(request.user, limit=8)
        recommended_animes = attach_episode_info(list(recs['animes']))
        recommended_movies = recs['movies']

    return render(request, 'index.html', {
        'title': 'Animeloop',
        **ctx,
        'user_history': user_history,
        'user_watch_later': user_watch_later,
        'recommended_animes': recommended_animes,
        'recommended_movies': recommended_movies,
    })


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
                Movie.objects.filter(is_featured=True)
                .prefetch_related('media_images', 'sources', 'genres')[:3]
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
                Movie.objects.order_by('-rating')[:6]
                .prefetch_related('media_images', 'sources', 'genres')
            ),
            'popular_movies': list(
                Movie.objects.filter(is_popular=True)
                .prefetch_related('media_images', 'sources', 'genres')
            ),
        }
        safe_cache_set(CACHE_KEY, public, timeout=300)

    user_history = []
    user_watch_later = []
    if request.user.is_authenticated:
        user_history = list(
            WatchHistory.objects.filter(user=request.user, movie__isnull=False)
            .select_related('movie').prefetch_related('movie__media_images')
            .order_by('-updated_at')[:8]
        )
        user_watch_later = list(
            WatchLater.objects.filter(user=request.user, movie__isnull=False)
            .select_related('movie').prefetch_related('movie__media_images')
            .order_by('-added_at')[:8]
        )

    return render(request, 'movies.html', {
        'title': 'Animeloop - Movies',
        **public,
        'user_history': user_history,
        'user_watch_later': user_watch_later,
    })


# ============================================================
# PROFILE
# ============================================================

@login_required
def profile(request):
    history = (
        WatchHistory.objects.filter(user=request.user)
        .select_related('episode__season__anime', 'movie')
        .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
        .order_by('-updated_at')[:20]
    )
    watch_later_count = WatchLater.objects.filter(user=request.user).count()
    follow_count = Follow.objects.filter(user=request.user).count()
    playlists = Playlist.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'profile.html', {
        'title': f'{request.user.first_name} - Profile',
        'history': history,
        'watch_later_count': watch_later_count,
        'follow_count': follow_count,
        'playlists': playlists,
    })


@login_required
def edit_profile(request):
    if request.method == 'POST':
        first_name       = request.POST.get('first_name', '').strip()
        last_name        = request.POST.get('last_name', '').strip()
        age              = request.POST.get('age', '').strip()
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if new_password and new_password != confirm_password:
            return render(request, 'edit_profile.html', {
                'title': 'Edit Profile',
                'error': 'Passwords do not match.',
            })

        if age:
            try:
                age_int = int(age)
                if not (10 <= age_int <= 80):
                    raise ValueError
            except ValueError:
                return render(request, 'edit_profile.html', {
                    'title': 'Edit Profile',
                    'error': 'Age must be a number between 10 and 80.',
                })
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

        return render(request, 'edit_profile.html', {
            'title': 'Edit Profile',
            'success': True,
        })

    return render(request, 'edit_profile.html', {'title': 'Edit Profile'})



# ============================================================
# AUTH
# ============================================================

@never_cache
def login_view(request):
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            from django.utils.http import url_has_allowed_host_and_scheme
            next_url = request.POST.get('next') or request.GET.get('next') or ''
            if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                next_url = 'index'
            return redirect(next_url)
        return render(request, 'login.html', {
            'title': 'ananimeclip',
            'error': 'Invalid email or password',
        })
    return render(request, 'login.html', {'title': 'ananimeclip'})


@never_cache
def signup(request):
    if request.method == 'POST':
        name             = request.POST.get('name', '').strip()
        age              = request.POST.get('age')
        email            = request.POST.get('email', '').strip()
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            return render(request, 'signup.html', {
                'title': 'ananimeclip', 'error': 'Passwords do not match'
            })
        if User.objects.filter(username=email).exists():
            return render(request, 'signup.html', {
                'title': 'ananimeclip', 'error': 'Email already registered'
            })

        try:
            age_int = int(age)
            if not (10 <= age_int <= 80):
                raise ValueError
        except (TypeError, ValueError):
            return render(request, 'signup.html', {
                'title': 'ananimeclip', 'error': 'Age must be a number between 10 and 80.'
            })

        user = User.objects.create_user(
            username=email, email=email, password=password, first_name=name,
        )
        Profile.objects.create(user=user, age=age_int)
        login(request, user)
        return redirect('index')

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
        anime_id_c   = cached['anime_id']
    else:
        episode_id_c = episode_id
        anime_id_c   = None

    episode = get_object_or_404(
        Episode.objects.select_related('season__anime').prefetch_related('sources'),
        id=episode_id_c,
    )
    anime = get_object_or_404(
        Anime.objects.prefetch_related(
            'media_images', 'genres',
            Prefetch(
                'seasons',
                queryset=Season.objects.prefetch_related(
                    Prefetch('episodes', queryset=Episode.objects.prefetch_related('sources'))
                ),
            ),
        ),
        pk=anime_id_c if anime_id_c else episode.season.anime_id,
    )

    if cached is None:
        safe_cache_set(CACHE_KEY, {
            'episode_id': episode.pk,
            'anime_id': anime.pk,
        }, timeout=600)

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
        next_season = Season.objects.filter(
            anime=anime, number__gt=current_season.number
        ).order_by('number').first()
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
        try:
            history_entry = WatchHistory.objects.get(user=request.user, episode=episode)
            resume_seconds = history_entry.progress_seconds
        except WatchHistory.DoesNotExist:
            pass

    return render(request, 'streaming.html', {
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
    })


@login_required
def streaming_movie(request, movie_id):
    # Cache only the movie ID, not the ORM object, to avoid stale pickled state.
    CACHE_KEY = f'streaming:movie:{movie_id}'
    cached = safe_cache_get(CACHE_KEY)

    movie = get_object_or_404(
        Movie.objects.prefetch_related('media_images', 'sources', 'genres'),
        id=movie_id,
    )

    if cached is None:
        safe_cache_set(CACHE_KEY, {'movie_id': movie.pk}, timeout=600)

    # Comments always fetched fresh — too volatile to cache safely.
    comments = list(
        movie.comments.filter(parent=None)
        .select_related('user')
        .prefetch_related('replies__user', 'likes', 'replies__likes')
    )

    user_rating = None
    resume_seconds = 0
    if request.user.is_authenticated:
        try:
            user_rating = UserRating.objects.get(user=request.user, movie=movie)
        except UserRating.DoesNotExist:
            pass
        try:
            history_entry = WatchHistory.objects.get(user=request.user, movie=movie)
            resume_seconds = history_entry.progress_seconds
        except WatchHistory.DoesNotExist:
            pass

    return render(request, 'streaming_movie.html', {
        'title': movie.title,
        'movie': movie,
        'comments': comments,
        'user_rating': user_rating,
        'resume_seconds': resume_seconds,
    })



# ============================================================
# RATINGS
# ============================================================

@login_required
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
        user=request.user, anime=anime,
        defaults={'score': score, 'movie': None},
    )
    avg = UserRating.objects.filter(anime=anime).aggregate(avg=Avg('score'))['avg'] or 0
    return JsonResponse({'score': score, 'avg': round(avg, 1)})


@login_required
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
        user=request.user, movie=movie,
        defaults={'score': score, 'anime': None},
    )
    avg = UserRating.objects.filter(movie=movie).aggregate(avg=Avg('score'))['avg'] or 0
    return JsonResponse({'score': score, 'avg': round(avg, 1)})


# ============================================================
# COMMENTS
# ============================================================

@login_required
@require_POST
def add_comment(request, episode_id):
    episode   = get_object_or_404(Episode, id=episode_id)
    body      = request.POST.get('body', '').strip()
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
def add_movie_comment(request, movie_id):
    movie     = get_object_or_404(Movie, id=movie_id)
    body      = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id')
    if body:
        comment = Comment(movie=movie, user=request.user, body=body)
        if parent_id:
            comment.parent = get_object_or_404(Comment, id=parent_id)
        comment.save()
        safe_cache_delete(f'streaming:movie:{movie_id}')
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
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
@require_POST
def toggle_follow(request, anime_id):
    anime = get_object_or_404(Anime, id=anime_id)
    obj, created = Follow.objects.get_or_create(user=request.user, anime=anime)
    if not created:
        obj.delete()
        following = False
    else:
        following = True
    return JsonResponse({
        'following': following,
        'follower_count': anime.followers.count(),
    })


@login_required
@never_cache
def favourites(request):
    follows = Follow.objects.filter(user=request.user).select_related('anime').prefetch_related(
        'anime__media_images',
        'anime__seasons__episodes',
    )
    anime_list = []
    for f in follows:
        anime = f.anime
        seasons = list(anime.seasons.all())
        anime.first_season = seasons[0] if seasons else None
        anime.first_episode = seasons[0].episodes.first() if anime.first_season else None
        anime_list.append(anime)
    return render(request, 'favourites.html', {
        'title': 'My Favourites',
        'anime_list': anime_list,
    })


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
    notifs = Notification.objects.filter(user=request.user).select_related(
        'anime', 'episode', 'movie'
    )[:50]
    # Mark all as read on page visit
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'notifications.html', {
        'title': 'Notifications',
        'notifications': notifs,
        'unread_count': unread_count,
    })


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

    cache_key = f'search:live:{query.lower()[:50]}'
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return JsonResponse({'results': cached})

    results = []
    for movie in Movie.objects.filter(title__icontains=query)[:5]:
        results.append({'id': movie.id, 'title': movie.title, 'type': 'movie'})

    anime_qs = (
        Anime.objects.filter(title__icontains=query)
        .prefetch_related(
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes'))
        )[:5]
    )
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
        movies_qs = list(
            Movie.objects.filter(genres__name__iexact=genre)
            .prefetch_related('media_images', 'sources')
        )
        anime_list = list(
            Anime.objects.filter(genres__name__iexact=genre).prefetch_related(
                'media_images',
                Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
            )
        )
        attach_episode_info(anime_list)
        ctx = {'movies': movies_qs, 'anime': anime_list}
        safe_cache_set(cache_key, ctx, timeout=600)
    return render(request, 'category.html', {'genre': genre, **ctx})


def search_results(request):
    query = request.GET.get('q', '').strip()
    movies = []
    anime_list = []
    if query:
        movies = list(
            Movie.objects.filter(title__icontains=query).prefetch_related('media_images')
        )
        anime_list = list(
            Anime.objects.filter(title__icontains=query).prefetch_related(
                'media_images',
                Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes')),
            )
        )
        attach_episode_info(anime_list)
    return render(request, 'search_results.html', {
        'query': query, 'movies': movies, 'anime_list': anime_list,
    })


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
    movie_id   = request.POST.get('movie_id')
    try:
        progress = int(request.POST.get('progress_seconds', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid progress_seconds value'}, status=400)

    if episode_id:
        episode = get_object_or_404(Episode, id=episode_id)
        WatchHistory.objects.update_or_create(
            user=request.user, episode=episode,
            defaults={'progress_seconds': progress, 'movie': None},
        )
    elif movie_id:
        movie = get_object_or_404(Movie, id=movie_id)
        WatchHistory.objects.update_or_create(
            user=request.user, movie=movie,
            defaults={'progress_seconds': progress, 'episode': None},
        )
    else:
        return JsonResponse({'error': 'No episode or movie id'}, status=400)
    return JsonResponse({'saved': True, 'progress': progress})


@login_required
@never_cache
def continue_watching(request):
    history = list(
        WatchHistory.objects.filter(user=request.user)
        .order_by('-updated_at')
        .select_related('episode__season__anime', 'movie')
        .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
        [:20]
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
    return render(request, 'continue_watching.html', {'history': history})


# ============================================================
# WATCH LATER
# ============================================================

@login_required
@require_POST
@never_cache
def toggle_watch_later(request):
    episode_id = request.POST.get('episode_id')
    movie_id   = request.POST.get('movie_id')

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
        'episode__season__anime__media_images', 'movie__media_images',
    )
    return render(request, 'playlist_detail.html', {'playlist': pl, 'items': items})


@login_required
@require_POST
def add_to_playlist(request):
    pl = get_object_or_404(Playlist, id=request.POST.get('playlist_id'), user=request.user)
    episode_id = request.POST.get('episode_id')
    movie_id   = request.POST.get('movie_id')
    if episode_id:
        PlaylistItem.objects.get_or_create(playlist=pl, episode=get_object_or_404(Episode, id=episode_id))
    elif movie_id:
        PlaylistItem.objects.get_or_create(playlist=pl, movie=get_object_or_404(Movie, id=movie_id))
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
    'recent':    ('-latest_update', 'Recently Updated'),
    'rating':    ('-rating',        'Highest Rated'),
    'a-z':       ('title',          'A → Z'),
    'z-a':       ('-title',         'Z → A'),
}

MOVIE_SORT_OPTIONS = {
    'recent':    ('-release_date',  'Recently Updated'),
    'rating':    ('-rating',        'Highest Rated'),
    'a-z':       ('title',          'A → Z'),
    'z-a':       ('-title',         'Z → A'),
}


def _apply_anime_filters(qs, request):
    """Apply ?sort= and ?genre= params to an Anime queryset."""
    genre = request.GET.get('genre', '').strip()
    sort  = request.GET.get('sort', 'recent')
    if genre:
        qs = qs.filter(genres__name__iexact=genre)
    order = ANIME_SORT_OPTIONS.get(sort, ANIME_SORT_OPTIONS['recent'])[0]
    if sort == 'recent':
        qs = qs.annotate(latest_update=Max('seasons__episodes__updated_at'))
    return qs.order_by(order).distinct(), genre, sort


def _apply_movie_filters(qs, request):
    """Apply ?sort= and ?genre= params to a Movie queryset."""
    genre = request.GET.get('genre', '').strip()
    sort  = request.GET.get('sort', 'recent')
    if genre:
        qs = qs.filter(genres__name__iexact=genre)
    order = MOVIE_SORT_OPTIONS.get(sort, MOVIE_SORT_OPTIONS['recent'])[0]
    return qs.order_by(order).distinct(), genre, sort


def _all_genre_names():
    return list(Genre.objects.values_list('name', flat=True).order_by('name'))


# ── Browse views ─────────────────────────────────────────────────────────────

def all_recent_movies(request):
    genre = request.GET.get('genre', '').strip()
    sort  = request.GET.get('sort', 'recent')
    is_filtered = bool(genre or sort != 'recent')

    cache_key = 'all_recent_movies'
    movies = None if is_filtered else safe_cache_get(cache_key)

    if movies is None:
        qs = Movie.objects.filter(release_date__isnull=False).prefetch_related('media_images', 'sources', 'genres')
        movies, genre, sort = _apply_movie_filters(qs, request)
        movies = list(movies)
        if not is_filtered:
            safe_cache_set(cache_key, movies, timeout=300)

    return render(request, 'all_recent_movies.html', {
        'title': 'Recently Updated Movies', 'movies': movies,
        'genres': _all_genre_names(), 'active_genre': genre,
        'active_sort': sort, 'sort_options': MOVIE_SORT_OPTIONS,
    })


def all_popular_movies(request):
    genre = request.GET.get('genre', '').strip()
    sort  = request.GET.get('sort', 'recent')
    is_filtered = bool(genre or sort != 'recent')

    cache_key = 'all_popular_movies'
    movies = None if is_filtered else safe_cache_get(cache_key)

    if movies is None:
        qs = Movie.objects.filter(is_popular=True).prefetch_related('media_images', 'sources', 'genres')
        movies, genre, sort = _apply_movie_filters(qs, request)
        movies = list(movies)
        if not is_filtered:
            safe_cache_set(cache_key, movies, timeout=300)

    return render(request, 'all_popular_movies.html', {
        'title': 'Popular Movies', 'movies': movies,
        'genres': _all_genre_names(), 'active_genre': genre,
        'active_sort': sort, 'sort_options': MOVIE_SORT_OPTIONS,
    })


def all_recent_anime(request):
    genre = request.GET.get('genre', '').strip()
    sort  = request.GET.get('sort', 'recent')
    is_filtered = bool(genre or sort != 'recent')

    cache_key = 'all_recent_anime'
    anime_list = None if is_filtered else safe_cache_get(cache_key)

    if anime_list is None:
        qs = Anime.objects.prefetch_related(
            'media_images', 'genres',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
        anime_list, genre, sort = _apply_anime_filters(qs, request)
        anime_list = list(anime_list)
        attach_episode_info(anime_list)
        if not is_filtered:
            safe_cache_set(cache_key, anime_list, timeout=300)

    return render(request, 'all_recent_anime.html', {
        'title': 'Recently Updated Anime', 'anime_list': anime_list,
        'genres': _all_genre_names(), 'active_genre': genre,
        'active_sort': sort, 'sort_options': ANIME_SORT_OPTIONS,
    })


def all_popular_anime(request):
    genre = request.GET.get('genre', '').strip()
    sort  = request.GET.get('sort', 'recent')
    is_filtered = bool(genre or sort != 'recent')

    cache_key = 'all_popular_anime'
    anime_list = None if is_filtered else safe_cache_get(cache_key)

    if anime_list is None:
        qs = Anime.objects.filter(is_popular=True).prefetch_related(
            'media_images', 'genres',
            Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
        )
        anime_list, genre, sort = _apply_anime_filters(qs, request)
        anime_list = list(anime_list)
        attach_episode_info(anime_list)
        if not is_filtered:
            safe_cache_set(cache_key, anime_list, timeout=300)

    return render(request, 'all_popular_anime.html', {
        'title': 'Popular Anime', 'anime_list': anime_list,
        'genres': _all_genre_names(), 'active_genre': genre,
        'active_sort': sort, 'sort_options': ANIME_SORT_OPTIONS,
    })