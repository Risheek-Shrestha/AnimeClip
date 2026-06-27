from .models import Notification


def notification_count(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
    else:
        count = 0
    return {'unread_notification_count': count}


def active_subprofile(request):
    """Inject the active SubProfile into every template context."""
    if not request.user.is_authenticated:
        return {'active_subprofile': None}
    from .models import SubProfile
    if not hasattr(request, 'session'):
        return {'active_subprofile': None}
    sp_id = request.session.get('active_subprofile_id')
    sp = None
    if sp_id:
        try:
            sp = SubProfile.objects.get(pk=sp_id, user=request.user)
        except SubProfile.DoesNotExist:
            # Profile was deleted (e.g. in another tab/session) — drop the
            # stale reference so we don't keep re-querying for it.
            del request.session['active_subprofile_id']
    return {'active_subprofile': sp}