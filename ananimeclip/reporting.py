"""Content reporting views."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .models import ContentReport, Episode, Movie


@login_required
@ratelimit(key='user', rate='10/h', method='POST', block=True)
@require_POST
def report_episode(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)
    reason = request.POST.get('reason', '')
    detail = request.POST.get('detail', '')[:500]

    valid_reasons = [r[0] for r in ContentReport.REASON_CHOICES]
    if reason not in valid_reasons:
        return JsonResponse({'error': 'Invalid reason'}, status=400)

    # one pending report per user per episode per reason
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
@require_POST
def report_movie(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    reason = request.POST.get('reason', '')
    detail = request.POST.get('detail', '')[:500]

    valid_reasons = [r[0] for r in ContentReport.REASON_CHOICES]
    if reason not in valid_reasons:
        return JsonResponse({'error': 'Invalid reason'}, status=400)

    ContentReport.objects.get_or_create(
        user=request.user,
        movie=movie,
        reason=reason,
        resolved=False,
        defaults={'detail': detail},
    )
    return JsonResponse({'status': 'reported'})
