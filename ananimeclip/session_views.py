"""
Views for device/session management.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .session_manager import (
    list_sessions,
    revoke_all_other_sessions,
    revoke_session,
    stream_heartbeat,
)


@login_required
def device_list(request):
    sessions = list_sessions(request)
    return render(request, 'device_list.html', {'sessions': sessions})


@login_required
@require_POST
def revoke_device(request):
    sid = request.POST.get('sid', '')
    if not sid:
        return JsonResponse({'error': 'missing sid'}, status=400)
    revoke_session(request, sid)
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def revoke_other_devices(request):
    count = revoke_all_other_sessions(request)
    return JsonResponse({'status': 'ok', 'revoked': count})


@login_required
@require_POST
def stream_heartbeat_view(request):
    """Called by the video player every ~60 s via AJAX to keep the stream slot alive."""
    stream_heartbeat(request)
    return JsonResponse({'status': 'ok'})
