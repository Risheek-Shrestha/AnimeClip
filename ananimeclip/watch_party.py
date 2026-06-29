"""
Watch Party — lightweight polling-based sync (no Django Channels required).

The host's player state (position + playing) is stored in the DB row.
Guests poll /watch-party/<code>/state/ every 3 seconds and seek if they
drift more than 5 seconds from the host.

For a production upgrade path, replace the polling endpoints with a
Django Channels WebSocket consumer — the JS client already emits the
same JSON shape.
"""

import secrets

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Episode, Movie, WatchParty, WatchPartyMember

# ── Helpers ──────────────────────────────────────────────────────────────────


def _generate_room_code():
    """8-char uppercase alphanumeric code, collision-safe."""
    while True:
        code = secrets.token_urlsafe(6)[:8].upper().replace('-', 'X').replace('_', 'Y')
        if not WatchParty.objects.filter(room_code=code).exists():
            return code


def _party_state(party):
    member_names = list(party.members.select_related('user').values_list('user__username', flat=True))
    return {
        'room_code': party.room_code,
        'host': party.host.username,
        'is_playing': party.is_playing,
        'playback_position': party.playback_position,
        'members': member_names,
        'member_count': len(member_names),
        'is_active': party.is_active,
    }


# ── Views ─────────────────────────────────────────────────────────────────────


@login_required
@require_POST
def create_watch_party(request):
    """POST /watch-party/create/  body: episode_id or movie_id"""
    episode_id = request.POST.get('episode_id')
    movie_id = request.POST.get('movie_id')

    episode = get_object_or_404(Episode, pk=episode_id) if episode_id else None
    movie = get_object_or_404(Movie, pk=movie_id) if movie_id else None

    if not episode and not movie:
        return JsonResponse({'error': 'episode_id or movie_id required'}, status=400)

    # Deactivate any existing active parties by this host for same content
    WatchParty.objects.filter(host=request.user, is_active=True).update(is_active=False)

    party = WatchParty.objects.create(
        host=request.user,
        episode=episode,
        movie=movie,
        room_code=_generate_room_code(),
    )
    WatchPartyMember.objects.create(party=party, user=request.user)

    return JsonResponse({'room_code': party.room_code, 'state': _party_state(party)})


@login_required
@require_POST
def join_watch_party(request, room_code):
    """POST /watch-party/<code>/join/"""
    party = get_object_or_404(WatchParty, room_code=room_code, is_active=True)
    WatchPartyMember.objects.get_or_create(party=party, user=request.user)
    return JsonResponse({'state': _party_state(party)})


@login_required
@require_GET
def watch_party_state(request, room_code):
    """GET /watch-party/<code>/state/  — polling endpoint for guests"""
    party = get_object_or_404(WatchParty, room_code=room_code, is_active=True)
    # Auto-join passive viewers
    WatchPartyMember.objects.get_or_create(party=party, user=request.user)
    return JsonResponse({'state': _party_state(party)})


@login_required
@require_POST
def sync_watch_party(request, room_code):
    """POST /watch-party/<code>/sync/  — host pushes player state"""
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

    return JsonResponse({'state': _party_state(party)})


@login_required
@require_POST
def end_watch_party(request, room_code):
    """POST /watch-party/<code>/end/  — host closes the party"""
    party = get_object_or_404(WatchParty, room_code=room_code, host=request.user)
    party.is_active = False
    party.save(update_fields=['is_active'])
    return JsonResponse({'status': 'ended'})


@login_required
def watch_party_room(request, room_code):
    """GET /watch-party/<code>/  — renders the Watch Party player page"""
    party = get_object_or_404(WatchParty, room_code=room_code, is_active=True)
    WatchPartyMember.objects.get_or_create(party=party, user=request.user)

    is_host = party.host == request.user
    content = party.episode or party.movie
    content_type = 'episode' if party.episode else 'movie'

    return render(
        request,
        'watch_party.html',
        {
            'party': party,
            'is_host': is_host,
            'content': content,
            'content_type': content_type,
            'title': f'Watch Party — {getattr(content, "title", str(content))}',
        },
    )
