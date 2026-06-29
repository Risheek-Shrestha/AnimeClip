"""
Trending page — surfaces anime and movies with the most watch-history
updates in the last 7 days, with Redis caching (5 min TTL).
"""

from datetime import timedelta

from django.db.models import Count, Prefetch
from django.shortcuts import render
from django.utils import timezone

from .content_access import filter_list_age_appropriate
from .models import Anime, Movie, Season, WatchHistory
from .views import safe_cache_get, safe_cache_set


def trending(request):
    CACHE_KEY = 'trending:page'
    ctx = safe_cache_get(CACHE_KEY)
    if ctx is None:
        since = timezone.now() - timedelta(days=7)

        # Top 12 trending anime by watch events in the last 7 days
        anime_ids = (
            WatchHistory.objects.filter(
                updated_at__gte=since,
                episode__isnull=False,
            )
            .values('episode__season__anime_id')
            .annotate(views=Count('id'))
            .order_by('-views')[:12]
        )
        anime_id_list = [r['episode__season__anime_id'] for r in anime_ids]

        trending_anime = list(
            Anime.objects.filter(pk__in=anime_id_list).prefetch_related(
                'media_images',
                'genres',
                Prefetch('seasons', queryset=Season.objects.prefetch_related('episodes__sources')),
            )
        )
        # Preserve order from annotation
        order_map = {aid: i for i, aid in enumerate(anime_id_list)}
        trending_anime.sort(key=lambda a: order_map.get(a.pk, 99))

        # Top 12 trending movies
        movie_ids = (
            WatchHistory.objects.filter(
                updated_at__gte=since,
                movie__isnull=False,
            )
            .values('movie_id')
            .annotate(views=Count('id'))
            .order_by('-views')[:12]
        )
        movie_id_list = [r['movie_id'] for r in movie_ids]
        trending_movies = list(
            Movie.objects.filter(pk__in=movie_id_list).prefetch_related('media_images', 'genres', 'sources')
        )
        movie_order_map = {mid: i for i, mid in enumerate(movie_id_list)}
        trending_movies.sort(key=lambda m: movie_order_map.get(m.pk, 99))

        ctx = {
            'trending_anime': trending_anime,
            'trending_movies': trending_movies,
        }
        safe_cache_set(CACHE_KEY, ctx, timeout=300)

    return render(
        request,
        'trending.html',
        {
            'title': 'Trending Now',
            'trending_anime': filter_list_age_appropriate(ctx['trending_anime'], request),
            'trending_movies': filter_list_age_appropriate(ctx['trending_movies'], request),
        },
    )
