"""
Recommendation service
=======================
Read/write layer between views and the persisted `Recommendation` table.

The table is the source of truth for "what should we show this user":
  - `warm_recommendations` (re)builds it on a schedule for active users.
  - `get_recommendations()` reads it directly (a plain indexed DB query) as
    long as it's fresh enough (see STALE_AFTER). If a user has never been
    warmed, or their rows are too old, it computes once on the spot and
    persists the result so the next request is a pure read again.
  - If the engine itself fails for any reason, we fall back to globally
    popular content so the page never breaks.

Each returned Anime/Movie object also gets a `.recommend_reason` attribute
attached (e.g. "Because you watch Action, Fantasy" or "Popular right now")
for templates that want to explain *why* something was recommended.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import Anime, Movie, Recommendation
from .recommendations import RecommendationEngine

logger = logging.getLogger(__name__)

# How long persisted recommendations are trusted before we recompute.
# Matches the old Redis cache TTL from the original cache-based design.
STALE_AFTER = timedelta(hours=6)


def get_recommendations(user, limit: int = 20) -> dict:
    """Returns {"animes": [...], "movies": [...]} for the given user."""
    rows = list(
        Recommendation.objects.filter(user=user)
        .order_by('rank')
        .values_list('anime_id', 'movie_id', 'reason', 'generated_at')
    )

    is_fresh = bool(rows) and (timezone.now() - max(r[3] for r in rows) < STALE_AFTER)

    if is_fresh:
        anime_entries = [(a, reason) for a, m, reason, _ in rows if a][:limit]
        movie_entries = [(m, reason) for a, m, reason, _ in rows if m][:limit]
        anime_ids = [pk for pk, _ in anime_entries]
        movie_ids = [pk for pk, _ in movie_entries]
        anime_reasons = dict(anime_entries)
        movie_reasons = dict(movie_entries)

        animes = list(
            Anime.objects.filter(pk__in=anime_ids).prefetch_related('genres', 'media_images', 'seasons__episodes')
        )
        movies = list(Movie.objects.filter(pk__in=movie_ids).prefetch_related('genres', 'media_images'))

        anime_order = {pk: i for i, pk in enumerate(anime_ids)}
        movie_order = {pk: i for i, pk in enumerate(movie_ids)}
        animes.sort(key=lambda a: anime_order.get(a.pk, 9999))
        movies.sort(key=lambda m: movie_order.get(m.pk, 9999))

        _attach_reasons(animes, anime_reasons)
        _attach_reasons(movies, movie_reasons)
        return {'animes': animes, 'movies': movies}

    # Cold start, or stale: compute fresh and persist.
    try:
        engine = RecommendationEngine(user)
        results = engine.recommend(limit=limit)
        save_recommendations(user, results)
        _attach_reasons(results['animes'], results.get('anime_reasons', {}))
        _attach_reasons(results['movies'], results.get('movie_reasons', {}))
        return {'animes': results['animes'], 'movies': results['movies']}
    except Exception:
        logger.exception('RecommendationEngine failed for user %s', user.pk)
        return _popular_fallback(limit)


def save_recommendations(user, results: dict) -> None:
    """
    Atomically replace a user's Recommendation rows with a freshly computed
    set. `results` is whatever RecommendationEngine.recommend() returns:
    {"animes": [...], "movies": [...],
     "anime_scores": {pk: score}, "movie_scores": {pk: score},
     "anime_reasons": {pk: str}, "movie_reasons": {pk: str}}
    Anime and movies are ranked independently (rank 1 = best anime pick,
    rank 1 = best movie pick — they don't compete against each other).
    """
    anime_scores = results.get('anime_scores', {})
    movie_scores = results.get('movie_scores', {})
    anime_reasons = results.get('anime_reasons', {})
    movie_reasons = results.get('movie_reasons', {})

    rows = [
        Recommendation(
            user=user,
            anime=anime,
            rank=i,
            score=anime_scores.get(anime.pk, 0.0),
            reason=anime_reasons.get(anime.pk, ''),
        )
        for i, anime in enumerate(results.get('animes', []), start=1)
    ] + [
        Recommendation(
            user=user,
            movie=movie,
            rank=i,
            score=movie_scores.get(movie.pk, 0.0),
            reason=movie_reasons.get(movie.pk, ''),
        )
        for i, movie in enumerate(results.get('movies', []), start=1)
    ]

    with transaction.atomic():
        Recommendation.objects.filter(user=user).delete()
        if rows:
            Recommendation.objects.bulk_create(rows)


def _attach_reasons(items, reasons: dict) -> None:
    for item in items:
        item.recommend_reason = reasons.get(item.pk, '')


def _popular_fallback(limit: int) -> dict:
    """Last-resort: return highest-rated content when everything else fails."""
    animes = list(
        Anime.objects.order_by('-rating', '-is_popular')[:limit].prefetch_related(
            'genres', 'media_images', 'seasons__episodes'
        )
    )
    movies = list(Movie.objects.order_by('-rating', '-is_popular')[:limit].prefetch_related('genres', 'media_images'))
    for a in animes:
        a.recommend_reason = 'Popular right now'
    for m in movies:
        m.recommend_reason = 'Popular right now'
    return {'animes': animes, 'movies': movies}


def get_similar(item, limit: int = 6):
    """
    Return up to `limit` Anime or Movie objects that share the most genres
    with `item`. Works for both Anime and Movie instances.
    Returns a list with a .recommend_reason attribute set on each result.
    """
    genre_ids = list(item.genres.values_list('pk', flat=True))
    is_anime = isinstance(item, Anime)

    if not genre_ids:
        # No genres — fall back to popular of the same type
        if is_anime:
            results = list(
                Anime.objects.exclude(pk=item.pk)
                .order_by('-rating', '-is_popular')
                .prefetch_related('genres', 'media_images', 'seasons__episodes')[:limit]
            )
        else:
            results = list(
                Movie.objects.exclude(pk=item.pk)
                .order_by('-rating', '-is_popular')
                .prefetch_related('genres', 'media_images')[:limit]
            )
        for r in results:
            r.recommend_reason = 'Popular right now'
        return results

    if is_anime:
        qs = (
            Anime.objects.exclude(pk=item.pk)
            .filter(genres__pk__in=genre_ids)
            .annotate(shared=Count('genres', filter=Q(genres__pk__in=genre_ids)))
            .order_by('-shared', '-rating')
            .prefetch_related('genres', 'media_images', 'seasons__episodes')
            .distinct()[:limit]
        )
    else:
        qs = (
            Movie.objects.exclude(pk=item.pk)
            .filter(genres__pk__in=genre_ids)
            .annotate(shared=Count('genres', filter=Q(genres__pk__in=genre_ids)))
            .order_by('-shared', '-rating')
            .prefetch_related('genres', 'media_images')
            .distinct()[:limit]
        )

    results = list(qs)
    genre_names = list(item.genres.values_list('name', flat=True)[:3])
    reason = 'Because you like ' + ', '.join(genre_names) if genre_names else 'Similar title'
    for r in results:
        r.recommend_reason = reason
    return results
