"""
Recommendation service
=======================
Read/write layer between views and the persisted `Recommendation` table.

The table is the source of truth for "what should we show this user":
  - `warm_recommendations` (re)builds it on a schedule for active users.
  - `get_recommendations()` reads it directly (a plain indexed DB query —
    no separate cache layer needed). If a user has never been warmed
    (e.g. brand new account), it computes once on the spot and persists
    the result so every subsequent request is a pure read.
  - If the engine itself fails for any reason, we fall back to globally
    popular content so the page never breaks.
"""

import logging

from django.db import transaction

from .models import Anime, Movie, Recommendation
from .recommendations import RecommendationEngine

logger = logging.getLogger(__name__)


def get_recommendations(user, limit: int = 20) -> dict:
    """Returns {"animes": [...], "movies": [...]} for the given user."""
    persisted = list(
        Recommendation.objects
        .filter(user=user)
        .order_by('rank')
        .values_list('anime_id', 'movie_id')
    )
    if persisted:
        anime_ids = [a for a, m in persisted if a][:limit]
        movie_ids = [m for a, m in persisted if m][:limit]

        animes = list(
            Anime.objects.filter(pk__in=anime_ids)
            .prefetch_related('genres', 'media_images', 'seasons__episodes')
        )
        movies = list(
            Movie.objects.filter(pk__in=movie_ids)
            .prefetch_related('genres', 'media_images')
        )

        anime_order = {pk: i for i, pk in enumerate(anime_ids)}
        movie_order = {pk: i for i, pk in enumerate(movie_ids)}
        animes.sort(key=lambda a: anime_order.get(a.pk, 9999))
        movies.sort(key=lambda m: movie_order.get(m.pk, 9999))

        return {"animes": animes, "movies": movies}

    # Cold start: nothing warmed yet for this user — compute now and persist.
    try:
        engine = RecommendationEngine(user)
        results = engine.recommend(limit=limit)
        save_recommendations(user, results)
        return {"animes": results["animes"], "movies": results["movies"]}
    except Exception:
        logger.exception("RecommendationEngine failed for user %s", user.pk)
        return _popular_fallback(limit)


def save_recommendations(user, results: dict) -> None:
    """
    Atomically replace a user's Recommendation rows with a freshly computed
    set. `results` is whatever RecommendationEngine.recommend() returns:
    {"animes": [...], "movies": [...], "anime_scores": {pk: score}, "movie_scores": {pk: score}}
    Anime and movies are ranked independently (rank 1 = best anime pick,
    rank 1 = best movie pick — they don't compete against each other).
    """
    anime_scores = results.get("anime_scores", {})
    movie_scores = results.get("movie_scores", {})

    rows = [
        Recommendation(user=user, anime=anime, rank=i, score=anime_scores.get(anime.pk, 0.0))
        for i, anime in enumerate(results.get("animes", []), start=1)
    ] + [
        Recommendation(user=user, movie=movie, rank=i, score=movie_scores.get(movie.pk, 0.0))
        for i, movie in enumerate(results.get("movies", []), start=1)
    ]

    with transaction.atomic():
        Recommendation.objects.filter(user=user).delete()
        if rows:
            Recommendation.objects.bulk_create(rows)


def _popular_fallback(limit: int) -> dict:
    """Last-resort: return highest-rated content when everything else fails."""
    return {
        "animes": list(
            Anime.objects.order_by("-rating", "-is_popular")[:limit]
            .prefetch_related("genres", "media_images", "seasons__episodes")
        ),
        "movies": list(
            Movie.objects.order_by("-rating", "-is_popular")[:limit]
            .prefetch_related("genres", "media_images")
        ),
    }