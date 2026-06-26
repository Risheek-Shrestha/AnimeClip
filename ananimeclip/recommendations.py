"""
Hybrid Recommendation Engine
==============================
Combines:
  1. Content-based filtering  — genre/attribute similarity (TF-IDF + cosine)
  2. Collaborative filtering  — user-item implicit feedback matrix (SVD)
  3. Popularity boost          — globally trending / highly-rated content
  4. Age-gate enforcement      — never surfaces 18+ to users under 18

Usage (in any view or management command):
    from .recommendations import RecommendationEngine

    engine = RecommendationEngine(user)
    results = engine.recommend(limit=20)
    # returns {"animes": [...], "movies": [...],
    #          "anime_scores": {pk: score}, "movie_scores": {pk: score}}
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q, QuerySet
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from .models import Anime, Genre, Movie, Profile, WatchHistory

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuneable weights
# ---------------------------------------------------------------------------
CONTENT_WEIGHT = 0.45       # content-based score contribution
COLLAB_WEIGHT  = 0.40       # collaborative score contribution
POPULAR_WEIGHT = 0.15       # global popularity score contribution

MIN_WATCH_SECONDS = 60      # ignore sessions shorter than this (accidental plays)
SVD_COMPONENTS    = 20      # latent factors; raise for larger datasets
HISTORY_LIMIT     = 200     # cap history rows pulled per user (performance)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _age_filter(qs: QuerySet, user_age: int | None) -> QuerySet:
    """Remove 18+ content for users under 18 (or unknown age)."""
    if user_age is None or user_age < 18:
        qs = qs.exclude(age_rating="r")
    return qs


def _build_anime_feature_string(anime: Anime) -> str:
    """Combine textual signals into one string for TF-IDF."""
    genres = " ".join(g.name.lower().replace(" ", "_") for g in anime.genres.all())
    studio  = (anime.studio  or "").lower().replace(" ", "_")
    country = (anime.country or "").lower().replace(" ", "_")
    # Repeat genres to give them more weight relative to studio/country
    return f"{genres} {genres} {studio} {country}".strip()


def _build_movie_feature_string(movie: Movie) -> str:
    genres  = " ".join(g.name.lower().replace(" ", "_") for g in movie.genres.all())
    studio  = (movie.studio  or "").lower().replace(" ", "_")
    country = (movie.country or "").lower().replace(" ", "_")
    return f"{genres} {genres} {studio} {country}".strip()


# ---------------------------------------------------------------------------
# Content-Based Scorer
# ---------------------------------------------------------------------------

class ContentBasedScorer:
    """
    Builds a TF-IDF matrix over all Anime (or Movie) feature strings and
    returns cosine similarity scores against the user's watched items.
    """

    def __init__(self, items: list, feature_fn):
        self.ids      = [item.pk for item in items]
        self.id_index = {pk: i for i, pk in enumerate(self.ids)}
        strings       = [feature_fn(item) for item in items]

        vectorizer  = TfidfVectorizer(token_pattern=r"[^\s]+")
        self.matrix = vectorizer.fit_transform(strings)  # sparse (n_items, n_features)

    def score(self, watched_ids: list[int], exclude_ids: set[int]) -> dict[int, float]:
        """
        Average cosine similarity of every candidate to the user's watched set.
        Returns {item_pk: score} sorted descending, excluding watched items.
        """
        if not watched_ids:
            return {}

        watched_indices = [
            self.id_index[wid] for wid in watched_ids if wid in self.id_index
        ]
        if not watched_indices:
            return {}

        watched_vectors = self.matrix[watched_indices]           # (n_watched, n_feat)
        sims = cosine_similarity(watched_vectors, self.matrix)   # (n_watched, n_items)
        avg_sims = sims.mean(axis=0)                             # (n_items,)

        scores = {}
        for pk, idx in self.id_index.items():
            if pk not in exclude_ids:
                scores[pk] = float(avg_sims[idx])
        return scores


# ---------------------------------------------------------------------------
# Collaborative Filtering Scorer
# ---------------------------------------------------------------------------

class CollaborativeScorer:
    """
    Builds a user-item implicit feedback matrix from WatchHistory.
    Applies Truncated SVD and returns dot-product scores for the target user.

    Implicit confidence = log(1 + progress_seconds / 60)
    (so finishing a 20-min episode ≈ confidence 4.1; a 2-sec skip ≈ 0.16)
    """

    def __init__(self, media_type: str):
        """
        media_type: 'anime' | 'movie'
        """
        assert media_type in ("anime", "movie")
        self.media_type = media_type
        self._build_matrix()

    def _build_matrix(self):
        if self.media_type == "anime":
            # Roll up episode watch history → anime level
            qs = (
                WatchHistory.objects
                .filter(
                    episode__isnull=False,
                    progress_seconds__gte=MIN_WATCH_SECONDS,
                )
                .values("user_id", "episode__season__anime_id", "progress_seconds")
            )
            item_key = "episode__season__anime_id"
        else:
            qs = (
                WatchHistory.objects
                .filter(
                    movie__isnull=False,
                    progress_seconds__gte=MIN_WATCH_SECONDS,
                )
                .values("user_id", "movie_id", "progress_seconds")
            )
            item_key = "movie_id"

        # Aggregate confidence per (user, item) pair
        user_item: dict[tuple, float] = defaultdict(float)
        for row in qs:
            key = (row["user_id"], row[item_key])
            confidence = np.log1p(row["progress_seconds"] / 60.0)
            user_item[key] = max(user_item[key], confidence)

        if not user_item:
            self.user_index  = {}
            self.item_index  = {}
            self.user_matrix = None
            return

        all_users = sorted({k[0] for k in user_item})
        all_items = sorted({k[1] for k in user_item})
        self.user_index = {u: i for i, u in enumerate(all_users)}
        self.item_index = {it: i for i, it in enumerate(all_items)}

        R = np.zeros((len(all_users), len(all_items)), dtype=np.float32)
        for (uid, iid), conf in user_item.items():
            R[self.user_index[uid], self.item_index[iid]] = conf

        n_components = min(SVD_COMPONENTS, R.shape[0] - 1, R.shape[1] - 1)
        if n_components < 1:
            self.user_matrix = None
            return

        svd = TruncatedSVD(n_components=n_components, random_state=42)
        U   = svd.fit_transform(R)               # (n_users, k)
        Vt  = svd.components_                    # (k, n_items)

        U_norm = normalize(U, norm="l2")
        self.user_matrix  = U_norm               # (n_users, k)
        self.item_vectors = Vt.T                  # (n_items, k)
        self.item_ids     = all_items

    def score(self, user_id: int, exclude_ids: set[int]) -> dict[int, float]:
        if self.user_matrix is None or user_id not in self.user_index:
            return {}

        u_vec  = self.user_matrix[self.user_index[user_id]]  # (k,)
        scores = self.item_vectors @ u_vec                    # (n_items,)

        return {
            item_id: float(scores[i])
            for i, item_id in enumerate(self.item_ids)
            if item_id not in exclude_ids
        }


# ---------------------------------------------------------------------------
# Popularity Scorer
# ---------------------------------------------------------------------------

def _popularity_scores(model_cls, exclude_ids: set[int]) -> dict[int, float]:
    """
    Normalised [0, 1] popularity score.
    Formula: 0.6 * normalised_rating + 0.4 * normalised_watch_count
    """
    if model_cls is Anime:
        watch_count_field = "seasons__episodes__watchhistory"
    else:
        watch_count_field = "watchhistory"

    qs = (
        model_cls.objects
        .exclude(pk__in=exclude_ids)
        .annotate(
            avg_rating=Avg("rating"),
            watch_count=Count(watch_count_field, distinct=True),
        )
        .values("pk", "avg_rating", "watch_count")
    )

    rows = list(qs)
    if not rows:
        return {}

    for row in rows:
        row["avg_rating"] = float(row["avg_rating"]) if row["avg_rating"] is not None else 0.0

    max_rating = max(r["avg_rating"] for r in rows) or 1
    max_count  = max((r["watch_count"] or 0) for r in rows) or 1

    return {
        row["pk"]: (
            0.6 * row["avg_rating"] / max_rating
            + 0.4 * (row["watch_count"] or 0) / max_count
        )
        for row in rows
    }


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """
    Entry point.  Instantiate per-request with the target User object.

    engine  = RecommendationEngine(request.user)
    results = engine.recommend(limit=20)
    # → {"animes": [...], "movies": [...],
    #    "anime_scores": {pk: score}, "movie_scores": {pk: score}}
    """

    def __init__(self, user: User):
        self.user    = user
        self.user_id = user.pk
        self.user_age: int | None = self._get_user_age()

    def _get_user_age(self) -> int | None:
        try:
            return Profile.objects.get(user=self.user).age
        except Profile.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend(self, limit: int = 20) -> dict:
        anime_ranked = self._recommend_for("anime", limit)   # [(pk, score, reason), ...]
        movie_ranked = self._recommend_for("movie", limit)

        anime_ids = [pk for pk, _, _ in anime_ranked]
        movie_ids = [pk for pk, _, _ in movie_ranked]
        anime_scores  = {pk: s for pk, s, _ in anime_ranked}
        movie_scores  = {pk: s for pk, s, _ in movie_ranked}
        anime_reasons = {pk: r for pk, _, r in anime_ranked}
        movie_reasons = {pk: r for pk, _, r in movie_ranked}

        animes = (
            Anime.objects
            .filter(pk__in=anime_ids)
            .prefetch_related("genres", "media_images", "seasons__episodes")
        )
        movies = (
            Movie.objects
            .filter(pk__in=movie_ids)
            .prefetch_related("genres", "media_images")
        )

        # Preserve the ranked order from our scorer
        anime_order = {pk: i for i, pk in enumerate(anime_ids)}
        movie_order = {pk: i for i, pk in enumerate(movie_ids)}

        animes = sorted(animes, key=lambda a: anime_order.get(a.pk, 9999))
        movies = sorted(movies, key=lambda m: movie_order.get(m.pk, 9999))

        return {
            "animes": animes,
            "movies": movies,
            "anime_scores": anime_scores,
            "movie_scores": movie_scores,
            "anime_reasons": anime_reasons,
            "movie_reasons": movie_reasons,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _recommend_for(self, media_type: str, limit: int) -> list[tuple[int, float, str]]:
        assert media_type in ("anime", "movie")
        model_cls = Anime if media_type == "anime" else Movie

        # 1. Gather items the user has already meaningfully watched
        watched_ids, genre_ids = self._get_user_signals(media_type)
        exclude_ids = set(watched_ids)

        # 2. Candidate pool — filtered by age rating (both Anime and Movie
        #    carry age_rating, so 18+ titles are excluded the same way).
        candidate_qs = _age_filter(model_cls.objects.all(), self.user_age)
        all_items = list(candidate_qs.prefetch_related("genres").all())

        if not all_items:
            return []

        all_ids = {item.pk for item in all_items}
        exclude_ids &= all_ids  # only exclude what's actually in the pool

        # 3. Content-based scores
        feature_fn = _build_anime_feature_string if media_type == "anime" \
                     else _build_movie_feature_string
        try:
            cb_scorer = ContentBasedScorer(all_items, feature_fn)
            cb_scores = cb_scorer.score(watched_ids, exclude_ids)
        except Exception:
            logger.exception("Content-based scorer failed")
            cb_scores = {}

        # 4. Collaborative scores
        try:
            cf_scorer = CollaborativeScorer(media_type)
            cf_scores = cf_scorer.score(self.user_id, exclude_ids)
        except Exception:
            logger.exception("Collaborative scorer failed")
            cf_scores = {}

        # 5. Popularity scores
        try:
            pop_scores = _popularity_scores(model_cls, exclude_ids)
        except Exception:
            logger.exception("Popularity scorer failed")
            pop_scores = {}

        # 6. Blend
        candidates = {item.pk for item in all_items} - exclude_ids
        combined: dict[int, float] = {}

        for pk in candidates:
            cb  = cb_scores.get(pk,  0.0)
            cf  = cf_scores.get(pk,  0.0)
            pop = pop_scores.get(pk, 0.0)
            combined[pk] = (
                CONTENT_WEIGHT * cb
                + COLLAB_WEIGHT  * cf
                + POPULAR_WEIGHT * pop
            )

        # 7. Genre affinity boost (+15% for genres user loves) + reason tagging
        reasons: dict[int, str] = {}
        if genre_ids:
            for item in all_items:
                if item.pk in combined:
                    item_genres = list(item.genres.all())
                    overlap_genres = [g for g in item_genres if g.pk in genre_ids]
                    if overlap_genres:
                        combined[item.pk] *= 1.15
                        names = [g.name for g in overlap_genres[:2]]
                        reasons[item.pk] = f"Because you watch {', '.join(names)}"

        # 8. Global popularity fallback for cold-start users
        if not watched_ids:
            for pk in candidates:
                combined[pk] = pop_scores.get(pk, 0.0)
                reasons.setdefault(pk, "Popular right now")

        ranked = sorted(combined, key=combined.__getitem__, reverse=True)[:limit]
        return [(pk, combined[pk], reasons.get(pk, "Recommended for you")) for pk in ranked]

    def _get_user_signals(self, media_type: str) -> tuple[list[int], set[int]]:
        """
        Returns:
          watched_ids — PKs of Anime/Movie the user meaningfully watched
          genre_ids   — PKs of genres the user watches most
        """
        if media_type == "anime":
            qs = (
                WatchHistory.objects
                .filter(
                    user=self.user,
                    episode__isnull=False,
                    progress_seconds__gte=MIN_WATCH_SECONDS,
                )
                .select_related("episode__season__anime")
                .prefetch_related("episode__season__anime__genres")
                .order_by("-updated_at")[:HISTORY_LIMIT]
            )
            watched_ids = list(
                dict.fromkeys(  # preserve order, deduplicate
                    h.episode.season.anime_id for h in qs
                )
            )
            all_genres: list[Genre] = []
            for h in qs:
                all_genres.extend(h.episode.season.anime.genres.all())
        else:
            qs = (
                WatchHistory.objects
                .filter(
                    user=self.user,
                    movie__isnull=False,
                    progress_seconds__gte=MIN_WATCH_SECONDS,
                )
                .select_related("movie")
                .prefetch_related("movie__genres")
                .order_by("-updated_at")[:HISTORY_LIMIT]
            )
            watched_ids = list(dict.fromkeys(h.movie_id for h in qs))
            all_genres = []
            for h in qs:
                all_genres.extend(h.movie.genres.all())

        # Top genres by frequency
        genre_freq: dict[int, int] = defaultdict(int)
        for g in all_genres:
            genre_freq[g.pk] += 1

        # Keep genres that appear in at least 2 watched items (or top-3)
        genre_ids = {
            gid for gid, count in genre_freq.items()
            if count >= 2
        }
        if not genre_ids and genre_freq:
            genre_ids = set(
                sorted(genre_freq, key=genre_freq.__getitem__, reverse=True)[:3]
            )

        return watched_ids, genre_ids