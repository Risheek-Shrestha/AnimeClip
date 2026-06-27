import json
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import WatchEvent, SearchEvent

User = get_user_model()


# ── Public API: record events ────────────────────────────────────────────────

@csrf_exempt
@require_POST
def record_watch(request):
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({"error": "bad payload"}, status=400)

    WatchEvent.objects.create(
        user=request.user if request.user.is_authenticated else None,
        anime_slug=data.get("anime_slug", ""),
        anime_title=data.get("anime_title", ""),
        episode_number=data.get("episode_number"),
        genre=data.get("genre", ""),
        watch_duration_seconds=data.get("watch_duration_seconds", 0),
        completed=data.get("completed", False),
    )
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def record_search(request):
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({"error": "bad payload"}, status=400)

    SearchEvent.objects.create(
        user=request.user if request.user.is_authenticated else None,
        query=data.get("query", "")[:300],
        results_count=data.get("results_count", 0),
    )
    return JsonResponse({"status": "ok"})


# ── Staff-only dashboard ─────────────────────────────────────────────────────

@staff_member_required
def dashboard(request):
    now = timezone.now()
    days = int(request.GET.get("days", 30))
    since = now - timedelta(days=days)

    watches = WatchEvent.objects.filter(watched_at__gte=since)
    searches = SearchEvent.objects.filter(searched_at__gte=since)

    total_plays = watches.count()
    unique_viewers = (
        watches.filter(user__isnull=False).values("user").distinct().count()
    )
    completion_rate = (
        watches.filter(completed=True).count() / total_plays * 100
        if total_plays else 0
    )
    avg_watch_seconds = watches.aggregate(avg=Avg("watch_duration_seconds"))["avg"] or 0
    total_searches = searches.count()

    plays_by_day = (
        watches.annotate(day=TruncDate("watched_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    plays_by_day_labels = [str(r["day"]) for r in plays_by_day]
    plays_by_day_data = [r["count"] for r in plays_by_day]

    top_anime = (
        watches.values("anime_title", "anime_slug")
        .annotate(plays=Count("id"))
        .order_by("-plays")[:10]
    )

    genre_dist = (
        watches.exclude(genre="")
        .values("genre")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )
    genre_labels = [r["genre"] for r in genre_dist]
    genre_data = [r["count"] for r in genre_dist]

    top_searches = (
        searches.values("query")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    new_users_qs = (
        User.objects.filter(date_joined__gte=since)
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    new_users_labels = [str(r["day"]) for r in new_users_qs]
    new_users_data = [r["count"] for r in new_users_qs]

    ctx = {
        "days": days,
        "total_plays": total_plays,
        "unique_viewers": unique_viewers,
        "completion_rate": round(completion_rate, 1),
        "avg_watch_minutes": round(avg_watch_seconds / 60, 1),
        "total_searches": total_searches,
        "plays_by_day_labels": json.dumps(plays_by_day_labels),
        "plays_by_day_data": json.dumps(plays_by_day_data),
        "top_anime": list(top_anime),
        "genre_labels": json.dumps(genre_labels),
        "genre_data": json.dumps(genre_data),
        "top_searches": list(top_searches),
        "new_users_labels": json.dumps(new_users_labels),
        "new_users_data": json.dumps(new_users_data),
    }
    return render(request, "analytics/dashboard.html", ctx)
