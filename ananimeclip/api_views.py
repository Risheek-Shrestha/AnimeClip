"""
REST API views for AnimeClip.

All endpoints live under /api/v1/ and return JSON.  No DRF dependency —
pure Django JsonResponse to keep the dep footprint minimal.

Authenticated endpoints require a valid session cookie (same as the HTML
views).  Public read endpoints are rate-limited by IP.

Endpoints
---------
Public (no auth required):
  GET  /api/v1/anime/                  – paginated catalog
  GET  /api/v1/anime/<slug>/           – single anime + seasons/episodes
  GET  /api/v1/movies/                 – paginated movie catalog
  GET  /api/v1/movies/<id>/            – single movie
  GET  /api/v1/genres/                 – genre list

Authenticated:
  GET  /api/v1/me/                     – current user profile
  GET  /api/v1/me/watch-history/       – paginated watch history
  DELETE /api/v1/me/watch-history/<id>/ – remove a history entry
  GET  /api/v1/me/watch-later/         – watch-later queue
  GET  /api/v1/me/recommendations/     – personalised recommendations
"""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from .content_access import filter_age_appropriate
from .models import (
    Anime,
    Episode,
    Genre,
    Movie,
    Season,
    WatchHistory,
    WatchLater,
)
from .recommendation_service import get_recommendations
from .views import get_active_subprofile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PAGE_SIZE = 20


def _paginate(qs, request):
    """Return (page_objects, pagination_meta_dict)."""
    paginator = Paginator(qs, PAGE_SIZE)
    try:
        page_num = max(1, min(int(request.GET.get('page', 1)), paginator.num_pages or 1))
    except (TypeError, ValueError):
        page_num = 1
    page = paginator.page(page_num)
    return list(page.object_list), {
        'page': page_num,
        'page_size': PAGE_SIZE,
        'total': paginator.count,
        'total_pages': paginator.num_pages,
        'has_next': page.has_next(),
        'has_prev': page.has_previous(),
    }


def _image_url(media_images, img_type):
    for img in media_images:
        if img.type == img_type and img.image:
            return img.image.url
    return None


def _source_dict(src):
    return {
        'id': src.pk,
        'label': src.label,
        'type': src.type,
        'subtitles': [
            {
                'language_code': s.language_code,
                'label': s.label,
                'file_url': s.file_url,
                'is_default': s.is_default,
            }
            for s in src.subtitles.all()
        ],
    }


def _episode_dict(ep):
    sources = list(ep.sources.all())
    return {
        'id': ep.pk,
        'number': ep.number,
        'title': ep.title,
        'duration_mins': ep.duration_mins,
        'thumbnail_url': ep.thumbnail_url or None,
        'intro_start_seconds': ep.intro_start_seconds,
        'intro_end_seconds': ep.intro_end_seconds,
        'release_date': ep.release_date.isoformat() if ep.release_date else None,
        'sources': [_source_dict(s) for s in sources],
    }


def _season_dict(season):
    episodes = list(season.episodes.all())
    return {
        'id': season.pk,
        'number': season.number,
        'title': season.title,
        'status': season.status,
        'release_date': season.release_date.isoformat() if season.release_date else None,
        'episodes': [_episode_dict(ep) for ep in episodes],
    }


def _anime_summary(anime):
    images = list(anime.media_images.all())
    return {
        'id': anime.pk,
        'slug': anime.slug,
        'title': anime.title,
        'description': anime.description,
        'studio': anime.studio,
        'country': anime.country,
        'rating': float(anime.rating),
        'age_rating': anime.age_rating,
        'genres': [g.name for g in anime.genres.all()],
        'is_featured': anime.is_featured,
        'is_popular': anime.is_popular,
        'trailer_url': anime.trailer_url or None,
        'thumbnail': _image_url(images, 'thumbnail'),
        'banner': _image_url(images, 'banner'),
        'poster': _image_url(images, 'poster'),
    }


def _anime_detail(anime):
    d = _anime_summary(anime)
    d['seasons'] = [_season_dict(s) for s in anime.seasons.all()]
    return d


def _movie_summary(movie):
    images = list(movie.media_images.all())
    return {
        'id': movie.pk,
        'title': movie.title,
        'description': movie.description,
        'studio': movie.studio,
        'country': movie.country,
        'rating': float(movie.rating),
        'age_rating': movie.age_rating,
        'genres': [g.name for g in movie.genres.all()],
        'duration_mins': movie.duration_mins,
        'release_date': movie.release_date.isoformat() if movie.release_date else None,
        'is_featured': movie.is_featured,
        'is_popular': movie.is_popular,
        'trailer_url': movie.trailer_url or None,
        'thumbnail': _image_url(images, 'thumbnail'),
        'banner': _image_url(images, 'banner'),
        'poster': _image_url(images, 'poster'),
    }


def _movie_detail(movie):
    d = _movie_summary(movie)
    d['sources'] = [_source_dict(s) for s in movie.sources.all()]
    return d


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def api_anime_list(request):
    """GET /api/v1/anime/  ?page=1 &genre= &sort=recent|rating|a-z"""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests'}, status=429)

    qs = filter_age_appropriate(
        Anime.objects.prefetch_related('media_images', 'genres'),
        request,
    )

    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'rating')
    if genre:
        qs = qs.filter(genres__name__iexact=genre)
    sort_map = {'rating': '-rating', 'a-z': 'title', 'z-a': '-title', 'recent': '-id'}
    qs = qs.order_by(sort_map.get(sort, '-rating')).distinct()

    items, meta = _paginate(qs, request)
    return JsonResponse(
        {
            'pagination': meta,
            'results': [_anime_summary(a) for a in items],
        }
    )


@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def api_anime_detail(request, slug):
    """GET /api/v1/anime/<slug>/"""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests'}, status=429)
    from django.db.models import Prefetch
    from django.shortcuts import get_object_or_404

    anime = get_object_or_404(
        Anime.objects.prefetch_related(
            'media_images',
            'genres',
            Prefetch(
                'seasons',
                queryset=Season.objects.prefetch_related(
                    Prefetch('episodes', queryset=Episode.objects.prefetch_related('sources__subtitles'))
                ),
            ),
        ),
        slug=slug,
    )
    if not filter_age_appropriate(Anime.objects.filter(pk=anime.pk), request).exists():
        return JsonResponse({'error': 'Not available on this profile.'}, status=403)
    return JsonResponse(_anime_detail(anime))


@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def api_movie_list(request):
    """GET /api/v1/movies/  ?page=1 &genre= &sort="""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests'}, status=429)

    qs = filter_age_appropriate(
        Movie.objects.prefetch_related('media_images', 'genres'),
        request,
    )
    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'rating')
    if genre:
        qs = qs.filter(genres__name__iexact=genre)
    sort_map = {'rating': '-rating', 'a-z': 'title', 'z-a': '-title', 'recent': '-release_date'}
    qs = qs.order_by(sort_map.get(sort, '-rating')).distinct()

    items, meta = _paginate(qs, request)
    return JsonResponse(
        {
            'pagination': meta,
            'results': [_movie_summary(m) for m in items],
        }
    )


@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def api_movie_detail(request, movie_id):
    """GET /api/v1/movies/<id>/"""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests'}, status=429)
    from django.shortcuts import get_object_or_404

    movie = get_object_or_404(
        Movie.objects.prefetch_related('media_images', 'genres', 'sources__subtitles'),
        pk=movie_id,
    )
    if not filter_age_appropriate(Movie.objects.filter(pk=movie.pk), request).exists():
        return JsonResponse({'error': 'Not available on this profile.'}, status=403)
    return JsonResponse(_movie_detail(movie))


@ratelimit(key='ip', rate='30/m', method='GET', block=False)
def api_genre_list(request):
    """GET /api/v1/genres/"""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests'}, status=429)
    genres = list(Genre.objects.values('id', 'name').order_by('name'))
    return JsonResponse({'results': genres})


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@login_required
def api_me(request):
    """GET /api/v1/me/"""
    u = request.user
    profile = getattr(u, 'profile', None)
    sp = get_active_subprofile(request)
    return JsonResponse(
        {
            'id': u.pk,
            'username': u.username,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'date_joined': u.date_joined.isoformat(),
            'age': profile.age if profile else None,
            'email_verified': profile.email_verified if profile else False,
            'active_subprofile': {
                'id': sp.pk,
                'name': sp.name,
                'avatar': sp.avatar,
                'kids_mode': sp.kids_mode,
            }
            if sp
            else None,
        }
    )


@login_required
def api_watch_history(request):
    """GET /api/v1/me/watch-history/"""
    sp = get_active_subprofile(request)
    wh_filter = {'subprofile': sp} if sp else {'user': request.user}
    qs = (
        WatchHistory.objects.filter(**wh_filter)
        .select_related('episode__season__anime', 'movie')
        .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
        .order_by('-updated_at')
    )
    items, meta = _paginate(qs, request)

    results = []
    for entry in items:
        d = {
            'id': entry.pk,
            'progress_seconds': entry.progress_seconds,
            'updated_at': entry.updated_at.isoformat(),
            'episode': None,
            'movie': None,
        }
        if entry.episode:
            ep = entry.episode
            anime = ep.season.anime
            d['episode'] = {
                'id': ep.pk,
                'number': ep.number,
                'title': ep.title,
                'thumbnail_url': ep.thumbnail_url or None,
                'anime_id': anime.pk,
                'anime_slug': anime.slug,
                'anime_title': anime.title,
                'season_number': ep.season.number,
                'duration_mins': ep.duration_mins,
                'thumbnail': _image_url(list(anime.media_images.all()), 'thumbnail'),
            }
        elif entry.movie:
            m = entry.movie
            d['movie'] = {
                'id': m.pk,
                'title': m.title,
                'duration_mins': m.duration_mins,
                'thumbnail': _image_url(list(m.media_images.all()), 'thumbnail'),
            }
        results.append(d)

    return JsonResponse({'pagination': meta, 'results': results})


@login_required
@require_http_methods(['DELETE'])
def api_delete_watch_history(request, history_id):
    """DELETE /api/v1/me/watch-history/<id>/"""
    sp = get_active_subprofile(request)
    wh_filter = {'subprofile': sp} if sp else {'user': request.user}
    deleted, _ = WatchHistory.objects.filter(pk=history_id, **wh_filter).delete()
    if not deleted:
        return JsonResponse({'error': 'Not found.'}, status=404)
    return JsonResponse({'deleted': True})


@login_required
def api_watch_later(request):
    """GET /api/v1/me/watch-later/"""
    sp = get_active_subprofile(request)
    wl_filter = {'subprofile': sp} if sp else {'user': request.user}
    qs = (
        WatchLater.objects.filter(**wl_filter)
        .select_related('episode__season__anime', 'movie')
        .prefetch_related('episode__season__anime__media_images', 'movie__media_images')
        .order_by('-added_at')
    )
    items, meta = _paginate(qs, request)

    results = []
    for entry in items:
        d = {
            'id': entry.pk,
            'added_at': entry.added_at.isoformat(),
            'episode': None,
            'movie': None,
        }
        if entry.episode:
            ep = entry.episode
            anime = ep.season.anime
            d['episode'] = {
                'id': ep.pk,
                'number': ep.number,
                'title': ep.title,
                'thumbnail_url': ep.thumbnail_url or None,
                'anime_id': anime.pk,
                'anime_slug': anime.slug,
                'anime_title': anime.title,
                'season_number': ep.season.number,
            }
        elif entry.movie:
            m = entry.movie
            d['movie'] = {
                'id': m.pk,
                'title': m.title,
                'thumbnail': _image_url(list(m.media_images.all()), 'thumbnail'),
            }
        results.append(d)

    return JsonResponse({'pagination': meta, 'results': results})


@login_required
def api_recommendations(request):
    """GET /api/v1/me/recommendations/"""
    recs = get_recommendations(request.user, limit=20)
    return JsonResponse(
        {
            'animes': [_anime_summary(a) for a in recs.get('animes', [])],
            'movies': [_movie_summary(m) for m in recs.get('movies', [])],
        }
    )


# ---------------------------------------------------------------------------
# Comments API
# ---------------------------------------------------------------------------


def _comment_dict(c):
    return {
        'id': c.pk,
        'user': c.user.get_full_name() or c.user.username,
        'body': c.body,
        'created_at': c.created_at.isoformat(),
        'total_likes': c.total_likes(),
        'replies': [
            {
                'id': r.pk,
                'user': r.user.get_full_name() or r.user.username,
                'body': r.body,
                'created_at': r.created_at.isoformat(),
                'total_likes': r.total_likes(),
            }
            for r in c.replies.all()
        ],
    }


@login_required
@require_http_methods(['GET'])
def api_episode_comments(request, episode_id):
    """GET /api/v1/episodes/<id>/comments/"""
    from django.shortcuts import get_object_or_404

    from .models import Comment, Episode

    episode = get_object_or_404(Episode, pk=episode_id)
    qs = (
        Comment.objects.filter(episode=episode, parent=None)
        .select_related('user')
        .prefetch_related('replies__user', 'likes', 'replies__likes')
        .order_by('created_at')
    )
    items, meta = _paginate(qs, request)

    return JsonResponse({'pagination': meta, 'results': [_comment_dict(c) for c in items]})


@login_required
@require_http_methods(['GET'])
def api_movie_comments(request, movie_id):
    """GET /api/v1/movies/<id>/comments/"""
    from django.shortcuts import get_object_or_404

    from .models import Comment, Movie

    movie = get_object_or_404(Movie, pk=movie_id)
    qs = (
        Comment.objects.filter(movie=movie, parent=None)
        .select_related('user')
        .prefetch_related('replies__user', 'likes', 'replies__likes')
        .order_by('created_at')
    )
    items, meta = _paginate(qs, request)

    return JsonResponse({'pagination': meta, 'results': [_comment_dict(c) for c in items]})


@login_required
@ratelimit(key='user', rate='20/10m', method='POST', block=False)
@require_http_methods(['POST'])
def api_post_episode_comment(request, episode_id):
    """POST /api/v1/episodes/<id>/comments/"""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests. Slow down.'}, status=429)
    import json

    from django.shortcuts import get_object_or_404

    from .models import Comment, Episode

    episode = get_object_or_404(Episode, pk=episode_id)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    body = (data.get('body') or '').strip()
    if not body:
        return JsonResponse({'error': 'body is required'}, status=400)
    parent_id = data.get('parent_id')
    comment = Comment(episode=episode, user=request.user, body=body)
    if parent_id:
        comment.parent = get_object_or_404(Comment, pk=parent_id)
    comment.save()
    return JsonResponse(
        {'id': comment.pk, 'body': comment.body, 'created_at': comment.created_at.isoformat()}, status=201
    )


@login_required
@ratelimit(key='user', rate='20/10m', method='POST', block=False)
@require_http_methods(['POST'])
def api_post_movie_comment(request, movie_id):
    """POST /api/v1/movies/<id>/comments/"""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests. Slow down.'}, status=429)
    import json

    from django.shortcuts import get_object_or_404

    from .models import Comment, Movie

    movie = get_object_or_404(Movie, pk=movie_id)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    body = (data.get('body') or '').strip()
    if not body:
        return JsonResponse({'error': 'body is required'}, status=400)
    parent_id = data.get('parent_id')
    comment = Comment(movie=movie, user=request.user, body=body)
    if parent_id:
        comment.parent = get_object_or_404(Comment, pk=parent_id)
    comment.save()
    return JsonResponse(
        {'id': comment.pk, 'body': comment.body, 'created_at': comment.created_at.isoformat()}, status=201
    )


# ---------------------------------------------------------------------------
# Ratings API
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['POST'])
def api_rate_anime(request, anime_id):
    """POST /api/v1/anime/<id>/rate/  body: {score: 1-10}"""
    import json

    from django.db.models import Avg
    from django.shortcuts import get_object_or_404

    from .models import Anime, UserRating

    anime = get_object_or_404(Anime, pk=anime_id)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    try:
        score = int(data.get('score', 0))
        if not (1 <= score <= 10):
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'error': 'score must be 1–10'}, status=400)
    UserRating.objects.update_or_create(
        user=request.user,
        anime=anime,
        defaults={'score': score, 'movie': None},
    )
    avg = UserRating.objects.filter(anime=anime).aggregate(avg=Avg('score'))['avg'] or 0
    Anime.objects.filter(pk=anime.pk).update(rating=round(avg, 1))
    return JsonResponse({'score': score, 'avg': round(avg, 1)})


@login_required
@require_http_methods(['POST'])
def api_rate_movie(request, movie_id):
    """POST /api/v1/movies/<id>/rate/  body: {score: 1-10}"""
    import json

    from django.db.models import Avg
    from django.shortcuts import get_object_or_404

    from .models import Movie, UserRating

    movie = get_object_or_404(Movie, pk=movie_id)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    try:
        score = int(data.get('score', 0))
        if not (1 <= score <= 10):
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'error': 'score must be 1–10'}, status=400)
    UserRating.objects.update_or_create(
        user=request.user,
        movie=movie,
        defaults={'score': score, 'anime': None},
    )
    avg = UserRating.objects.filter(movie=movie).aggregate(avg=Avg('score'))['avg'] or 0
    Movie.objects.filter(pk=movie.pk).update(rating=round(avg, 1))
    return JsonResponse({'score': score, 'avg': round(avg, 1)})


# ---------------------------------------------------------------------------
# Follows API
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['POST', 'DELETE'])
def api_toggle_follow_anime(request, anime_id):
    """POST /api/v1/anime/<id>/follow/ — toggle follow; returns {following, follower_count}"""
    from django.shortcuts import get_object_or_404

    from .models import Anime, Follow

    anime = get_object_or_404(Anime, pk=anime_id)
    obj, created = Follow.objects.get_or_create(user=request.user, anime=anime)
    if not created:
        obj.delete()
    return JsonResponse({'following': created, 'follower_count': anime.followers.count()})


@login_required
@require_http_methods(['POST', 'DELETE'])
def api_toggle_follow_movie(request, movie_id):
    """POST /api/v1/movies/<id>/follow/ — toggle follow; returns {following, follower_count}"""
    from django.shortcuts import get_object_or_404

    from .models import Follow, Movie

    movie = get_object_or_404(Movie, pk=movie_id)
    obj, created = Follow.objects.get_or_create(user=request.user, movie=movie)
    if not created:
        obj.delete()
    return JsonResponse({'following': created, 'follower_count': movie.followers.count()})


# ---------------------------------------------------------------------------
# Search API
# ---------------------------------------------------------------------------


@ratelimit(key='ip', rate='30/m', method='GET', block=False)
def api_search(request):
    """GET /api/v1/search/?q=<query>&genre=&sort=relevance|rating|newest"""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests'}, status=429)
    from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
    from django.db.models import Max, Q

    query = request.GET.get('q', '').strip()
    genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'relevance')
    if not query:
        return JsonResponse({'error': 'q is required'}, status=400)

    movie_qs = filter_age_appropriate(Movie.objects.prefetch_related('media_images', 'genres'), request)
    anime_qs = filter_age_appropriate(Anime.objects.prefetch_related('media_images', 'genres'), request)

    try:
        vec = SearchVector('title', weight='A') + SearchVector('description', weight='B')
        sq = SearchQuery(query)
        movie_qs = movie_qs.annotate(rank=SearchRank(vec, sq)).filter(rank__gt=0)
        anime_qs = anime_qs.annotate(rank=SearchRank(vec, sq)).filter(rank__gt=0)
    except Exception:
        movie_qs = movie_qs.filter(Q(title__icontains=query) | Q(description__icontains=query))
        anime_qs = anime_qs.filter(Q(title__icontains=query) | Q(description__icontains=query))

    if genre:
        movie_qs = movie_qs.filter(genres__name__iexact=genre)
        anime_qs = anime_qs.filter(genres__name__iexact=genre)

    sort_map = {'rating': '-rating', 'newest': '-release_date', 'relevance': 'title'}
    movie_qs = movie_qs.order_by(sort_map.get(sort, 'title')).distinct()

    anime_sort_map = {'rating': '-rating', 'relevance': 'title'}
    if sort == 'newest':
        anime_qs = anime_qs.annotate(latest_rel=Max('seasons__release_date')).order_by('-latest_rel').distinct()
    else:
        anime_qs = anime_qs.order_by(anime_sort_map.get(sort, 'title')).distinct()

    movies_page, movies_meta = _paginate(movie_qs, request)
    anime_page, anime_meta = _paginate(anime_qs, request)

    return JsonResponse(
        {
            'query': query,
            'movies': {'pagination': movies_meta, 'results': [_movie_summary(m) for m in movies_page]},
            'anime': {'pagination': anime_meta, 'results': [_anime_summary(a) for a in anime_page]},
        }
    )


# ---------------------------------------------------------------------------
# Notifications API
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['GET'])
def api_notifications(request):
    """GET /api/v1/me/notifications/"""
    from .models import Notification

    qs = (
        Notification.objects.filter(user=request.user)
        .select_related('anime', 'episode', 'movie')
        .order_by('-created_at')
    )
    items, meta = _paginate(qs, request)
    results = [
        {
            'id': n.pk,
            'type': n.notif_type,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'anime_id': n.anime_id,
            'episode_id': n.episode_id,
            'movie_id': n.movie_id,
        }
        for n in items
    ]
    return JsonResponse({'pagination': meta, 'results': results})


@login_required
@require_http_methods(['POST'])
def api_mark_all_notifications_read(request):
    """POST /api/v1/me/notifications/read-all/"""
    from .models import Notification

    updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'marked_read': updated})


# ---------------------------------------------------------------------------
# Sub-profiles API
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['GET'])
def api_subprofiles(request):
    """GET /api/v1/me/profiles/"""
    from .models import SubProfile

    sps = SubProfile.objects.filter(user=request.user)
    active_id = request.session.get('active_subprofile_id')
    return JsonResponse(
        {
            'results': [
                {
                    'id': sp.pk,
                    'name': sp.name,
                    'avatar': sp.avatar,
                    'kids_mode': sp.kids_mode,
                    'is_active': sp.pk == active_id,
                }
                for sp in sps
            ]
        }
    )


# ---------------------------------------------------------------------------
# Trending
# ---------------------------------------------------------------------------

from datetime import timedelta  # noqa: E402

from django.db.models import Count  # noqa: E402


@ratelimit(key='ip', rate='60/m', method='GET', block=True)
@require_http_methods(['GET'])
def api_trending(request):
    from django.core.cache import cache

    ctx = cache.get('api:trending')
    if ctx is None:
        from django.utils import timezone

        since = timezone.now() - timedelta(days=7)
        anime_ids = (
            WatchHistory.objects.filter(updated_at__gte=since, episode__isnull=False)
            .values('episode__season__anime_id')
            .annotate(views=Count('id'))
            .order_by('-views')[:12]
        )
        movie_ids = (
            WatchHistory.objects.filter(updated_at__gte=since, movie__isnull=False)
            .values('movie_id')
            .annotate(views=Count('id'))
            .order_by('-views')[:12]
        )
        from .models import Anime as _Anime
        from .models import Movie as _Movie

        anime_list = list(
            _Anime.objects.filter(pk__in=[r['episode__season__anime_id'] for r in anime_ids]).prefetch_related(
                'media_images', 'genres'
            )
        )
        movie_list = list(
            _Movie.objects.filter(pk__in=[r['movie_id'] for r in movie_ids]).prefetch_related('media_images', 'genres')
        )
        ctx = {
            'anime': [_anime_summary(a) for a in anime_list],
            'movies': [_movie_summary(m) for m in movie_list],
        }
        cache.set('api:trending', ctx, 300)
    return JsonResponse(ctx)


# ---------------------------------------------------------------------------
# Content Reporting
# ---------------------------------------------------------------------------

from .models import ContentReport  # noqa: E402


@login_required
@ratelimit(key='user', rate='10/h', method='POST', block=True)
@require_http_methods(['POST'])
def api_report_episode(request, episode_id):
    from django.shortcuts import get_object_or_404

    from .models import Episode as _Ep

    episode = get_object_or_404(_Ep, pk=episode_id)
    reason = request.POST.get('reason', '')
    detail = (request.POST.get('detail', '') or '')[:500]
    if reason not in [r[0] for r in ContentReport.REASON_CHOICES]:
        return JsonResponse({'error': 'invalid reason'}, status=400)
    ContentReport.objects.get_or_create(
        user=request.user,
        episode=episode,
        reason=reason,
        resolved=False,
        defaults={'detail': detail},
    )
    return JsonResponse({'status': 'reported'})


@login_required
@ratelimit(key='user', rate='10/h', method='POST', block=True)
@require_http_methods(['POST'])
def api_report_movie(request, movie_id):
    from django.shortcuts import get_object_or_404

    from .models import Movie as _Mv

    movie = get_object_or_404(_Mv, pk=movie_id)
    reason = request.POST.get('reason', '')
    detail = (request.POST.get('detail', '') or '')[:500]
    if reason not in [r[0] for r in ContentReport.REASON_CHOICES]:
        return JsonResponse({'error': 'invalid reason'}, status=400)
    ContentReport.objects.get_or_create(
        user=request.user,
        movie=movie,
        reason=reason,
        resolved=False,
        defaults={'detail': detail},
    )
    return JsonResponse({'status': 'reported'})


# ---------------------------------------------------------------------------
# Watch Party REST shim
# ---------------------------------------------------------------------------

import secrets as _secrets  # noqa: E402

from .models import WatchParty, WatchPartyMember  # noqa: E402


def _wp_state(party):
    members = list(party.members.select_related('user').values_list('user__username', flat=True))
    return {
        'room_code': party.room_code,
        'host': party.host.username,
        'is_playing': party.is_playing,
        'playback_position': party.playback_position,
        'members': members,
        'is_active': party.is_active,
    }


@login_required
@require_http_methods(['POST'])
def api_create_watch_party(request):
    from django.shortcuts import get_object_or_404

    episode_id = request.POST.get('episode_id')
    movie_id = request.POST.get('movie_id')
    episode = get_object_or_404(Episode, pk=episode_id) if episode_id else None
    movie = get_object_or_404(Movie, pk=movie_id) if movie_id else None
    if not episode and not movie:
        return JsonResponse({'error': 'episode_id or movie_id required'}, status=400)
    WatchParty.objects.filter(host=request.user, is_active=True).update(is_active=False)
    # Generate unique room code
    code = None
    for _ in range(10):
        candidate = _secrets.token_urlsafe(6)[:8].upper().replace('-', 'X').replace('_', 'Y')
        if not WatchParty.objects.filter(room_code=candidate).exists():
            code = candidate
            break
    if not code:
        return JsonResponse({'error': 'Could not generate room code'}, status=500)
    party = WatchParty.objects.create(host=request.user, episode=episode, movie=movie, room_code=code)
    WatchPartyMember.objects.create(party=party, user=request.user)
    return JsonResponse({'state': _wp_state(party)})


@login_required
@require_http_methods(['GET'])
def api_watch_party_state(request, room_code):
    from django.shortcuts import get_object_or_404

    party = get_object_or_404(WatchParty, room_code=room_code, is_active=True)
    WatchPartyMember.objects.get_or_create(party=party, user=request.user)
    return JsonResponse({'state': _wp_state(party)})


@login_required
@require_http_methods(['POST'])
def api_sync_watch_party(request, room_code):
    from django.shortcuts import get_object_or_404
    from django.utils import timezone

    party = get_object_or_404(WatchParty, room_code=room_code, host=request.user, is_active=True)
    try:
        position = float(request.POST.get('position', party.playback_position))
        is_playing = request.POST.get('is_playing', 'true').lower() == 'true'
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid position'}, status=400)
    party.playback_position = position
    party.is_playing = is_playing
    party.updated_at = timezone.now()
    party.save(update_fields=['playback_position', 'is_playing', 'updated_at'])
    return JsonResponse({'state': _wp_state(party)})
