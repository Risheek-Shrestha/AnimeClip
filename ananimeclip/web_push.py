"""
Web Push Notifications (VAPID / Web Push API)
==============================================
Sends push notifications to subscribed browsers without FCM/APNs.

Setup:
  1. pip install pywebpush
  2. Generate VAPID keys once:
       from py_vapid import Vapid
       v = Vapid(); v.generate_keys()
       print(v.private_key_urlsafe, v.public_key_urlsafe)
  3. Set in .env:
       VAPID_PRIVATE_KEY=<base64url private key>
       VAPID_PUBLIC_KEY=<base64url public key>
       VAPID_CLAIMS_SUB=mailto:admin@yoursite.com
  4. Service worker: subscribe to push and POST the subscription object to
       /push/subscribe/
"""

from __future__ import annotations

import json
import logging
import os

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST

# PushSubscription now lives in models.py so it gets a proper migration.
from .models import PushSubscription  # noqa: F401 – re-exported for convenience

logger = logging.getLogger(__name__)


def send_push_notification(subscription_info: dict, title: str, body: str, url: str = '/') -> bool:
    try:
        from pywebpush import webpush  # type: ignore[import]
    except ImportError:
        logger.warning('pywebpush not installed — skipping push notification')
        return False

    private_key = os.getenv('VAPID_PRIVATE_KEY', '')
    claims_sub = os.getenv('VAPID_CLAIMS_SUB', 'mailto:admin@example.com')
    if not private_key:
        logger.warning('VAPID_PRIVATE_KEY not set')
        return False

    payload = json.dumps({'title': title, 'body': body, 'url': url})
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims={'sub': claims_sub},
        )
        return True
    except Exception as exc:
        status = getattr(exc, 'response', None)
        if status is not None and getattr(status, 'status_code', 0) in (404, 410):
            endpoint = subscription_info.get('endpoint', '')
            PushSubscription.objects.filter(endpoint=endpoint).delete()
        else:
            logger.exception('Push notification failed: %s', exc)
        return False


def notify_user(user: User, title: str, body: str, url: str = '/'):
    for sub in user.push_subscriptions.all():
        send_push_notification(sub.subscription_info, title, body, url)


@login_required
@require_POST
def push_subscribe(request):
    try:
        data = json.loads(request.body)
        endpoint = data['endpoint']
        p256dh = data['keys']['p256dh']
        auth = data['keys']['auth']
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'invalid payload'}, status=400)
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth},
    )
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def push_unsubscribe(request):
    try:
        data = json.loads(request.body)
        endpoint = data['endpoint']
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'invalid payload'}, status=400)
    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({'status': 'ok'})


def vapid_public_key(request):
    key = os.getenv('VAPID_PUBLIC_KEY', '')
    return JsonResponse({'publicKey': key})
