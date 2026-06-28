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

import math

from django.contrib.auth.decorators import login_required
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
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    total = qs.count()
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, total_pages)
    offset = (page - 1) * PAGE_SIZE
    objects = list(qs[offset: offset + PAGE_SIZE])
    return objects, {
        'page': page,
        'page_size': PAGE_SIZE,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
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
    sources = list(ep.sources.all()) if hasattr(ep, '_prefetched_objects_cache') else list(ep.sources.all())
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
    return JsonResponse({
        'pagination': meta,
        'results': [_anime_summary(a) for a in items],
    })


@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def api_anime_detail(request, slug):
    """GET /api/v1/anime/<slug>/"""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Too many requests'}, status=429)
    from django.shortcuts import get_object_or_404
    from django.db.models import Prefetch

    anime = get_object_or_404(
        Anime.objects.prefetch_related(
            'media_images',
            'genres',
            Prefetch('seasons', queryset=Season.objects.prefetch_related(
                Prefetch('episodes', queryset=Episode.objects.prefetch_related('sources__subtitles'))
            )),
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
    return JsonResponse({
        'pagination': meta,
        'results': [_movie_summary(m) for m in items],
    })


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
    return JsonResponse({
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
        } if sp else None,
    })


@login_required
def api_watch_history(request):
    """GET /api/v1/me/watch-history/"""
    sp = get_active_subprofile(request)
    wh_filter = {'subprofile': sp} if sp else {'user': request.user}
    qs = (
        WatchHistory.objects
        .filter(**wh_filter)
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
        WatchLater.objects
        .filter(**wl_filter)
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
    return JsonResponse({
        'animes': [_anime_summary(a) for a in recs.get('animes', [])],
        'movies': [_movie_summary(m) for m in recs.get('movies', [])],
    })
