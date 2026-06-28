"""
Centralised age-rating / Kids Mode enforcement.

Before this module existed, 18+ ("r") content was only ever excluded
inside the recommendation engine's candidate pool — it was never
checked on the actual streaming, search, category, or browse
endpoints, so a minor account (or a Kids Mode sub-profile) could
still open an 18+ episode by visiting its URL directly. This module
is the single place that decides "is this viewer allowed to see this
content?", so every entry point enforces the same rule.
"""

from .models import SubProfile

ADULT_RATING = 'r'


def viewer_age(request):
    """Account-level age from the logged-in user's Profile, or None."""
    if not request.user.is_authenticated:
        return None
    profile = getattr(request.user, 'profile', None)
    return profile.age if profile else None


def kids_mode_active(request):
    """Whether the currently active sub-profile has Kids Mode enabled."""
    if not request.user.is_authenticated:
        return False
    sp_id = request.session.get('active_subprofile_id')
    if not sp_id:
        return False
    try:
        sp = SubProfile.objects.get(pk=sp_id, user=request.user)
    except SubProfile.DoesNotExist:
        return False
    return bool(sp.kids_mode)


def restricted_to_pg13(request):
    """
    True if 18+ content must be hidden/blocked for this request — either
    because the account's own age is under 18 (or unset), or because the
    active Kids Mode sub-profile requires it.
    """
    age = viewer_age(request)
    if age is None or age < 18:
        return True
    return kids_mode_active(request)


def can_view(request, age_rating):
    """Whether this request is allowed to view content rated `age_rating`."""
    if age_rating != ADULT_RATING:
        return True
    return not restricted_to_pg13(request)


def filter_age_appropriate(qs, request):
    """Exclude 18+ rows from an Anime/Movie queryset when restricted."""
    if restricted_to_pg13(request):
        return qs.exclude(age_rating=ADULT_RATING)
    return qs


def _drop_adult(items):
    return [i for i in items if getattr(i, 'age_rating', None) != ADULT_RATING]


def filter_list_age_appropriate(items, request):
    """Same idea as filter_age_appropriate(), but for an already-materialized
    list rather than a queryset — used for views whose cache is shared across
    all users and therefore must be re-filtered per-request after the read,
    not filtered before the cache write."""
    if restricted_to_pg13(request):
        return _drop_adult(items)
    return list(items)


def filter_index_context(ctx, request):
    """
    Re-filter the (shared, cached) homepage context for this specific
    request. The cache itself stays unfiltered and shared across every
    viewer — only the per-request view of it changes — otherwise the
    first viewer's restriction level would get baked into the cache
    and served to every other viewer afterwards.
    """
    if not restricted_to_pg13(request):
        return ctx
    ctx = dict(ctx)
    for key in ('featured_animes', 'Recent_animes', 'Popular_animes', 'top_animes', 'new_animes', 'completed_animes'):
        if key in ctx:
            ctx[key] = _drop_adult(ctx[key])
    if ctx.get('coming_soon_season') is not None:
        if getattr(ctx['coming_soon_season'].anime, 'age_rating', None) == ADULT_RATING:
            ctx['coming_soon_season'] = None
    if 'week_days' in ctx:
        ctx['week_days'] = [{**day, 'animes': _drop_adult(day.get('animes', []))} for day in ctx['week_days']]
    return ctx


def filter_movies_context(ctx, request):
    """Same idea as filter_index_context(), for the Movies page cache."""
    if not restricted_to_pg13(request):
        return ctx
    ctx = dict(ctx)
    for key in ('featured_movies', 'recent_movies', 'top_rated_movies', 'popular_movies'):
        if key in ctx:
            ctx[key] = _drop_adult(ctx[key])
    if ctx.get('coming_soon_movie') is not None:
        if getattr(ctx['coming_soon_movie'], 'age_rating', None) == ADULT_RATING:
            ctx['coming_soon_movie'] = None
    return ctx
