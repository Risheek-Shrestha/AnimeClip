"""
Stripe billing
==============
Wires real payments up to the gating layer in subscription.py.

subscription.py already defines `profile.plan` ('free' / 'premium') and the
`premium_required` decorator. This module is the missing piece: it creates a
Stripe Checkout session, verifies the webhook Stripe sends back, and flips
`profile.plan` when a payment succeeds or a subscription ends.

Required settings (read from environment — see Hello/settings.py):
    STRIPE_SECRET_KEY        sk_live_... / sk_test_...
    STRIPE_PUBLISHABLE_KEY   pk_live_... / pk_test_...   (used in templates)
    STRIPE_PRICE_ID          price_... for the Premium monthly plan
    STRIPE_WEBHOOK_SECRET    whsec_...

If STRIPE_SECRET_KEY isn't set, checkout_view fails gracefully with a 503
instead of crashing, so the app still runs in environments without billing
configured (e.g. local dev, CI).
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _stripe():
    """Lazily import + configure the stripe SDK so the app can boot without it installed."""
    import stripe

    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '') or ''
    return stripe


def _checkout_idempotency_key(user_id) -> str:
    """
    Dedupe retried checkout submissions (double-click, network retry) within a
    short window without permanently blocking the user from checking out
    again later.
    """
    import time

    window = int(time.time() // 60)  # 1-minute bucket
    return f'checkout-{user_id}-{window}'


def billing_configured() -> bool:
    return bool(
        getattr(settings, 'STRIPE_SECRET_KEY', None)
        and getattr(settings, 'STRIPE_PRICE_ID', None)
        and getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    )


@login_required
@require_POST
def create_checkout_session(request):
    if not billing_configured():
        return HttpResponseServerError('Billing is not configured on this server.')

    stripe = _stripe()
    profile = request.user.profile

    try:
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            line_items=[{'price': settings.STRIPE_PRICE_ID, 'quantity': 1}],
            customer=profile.stripe_customer_id or None,
            customer_email=request.user.email if not profile.stripe_customer_id else None,
            client_reference_id=str(request.user.id),
            success_url=request.build_absolute_uri(reverse('billing_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('billing_cancel')),
            metadata={'user_id': str(request.user.id)},
            idempotency_key=_checkout_idempotency_key(request.user.id),
        )
    except stripe.error.StripeError:
        logger.exception('Stripe checkout session creation failed for user %s', request.user.id)
        return HttpResponseServerError('Could not start checkout. Please try again shortly.')
    except Exception:
        logger.exception('Unexpected error creating checkout session for user %s', request.user.id)
        return HttpResponseServerError('Could not start checkout. Please try again shortly.')

    return redirect(session.url, permanent=False)


@login_required
def billing_success(request):
    return render(request, 'billing_success.html')


@login_required
def billing_cancel(request):
    return render(request, 'billing_cancel.html')


@login_required
@require_POST
def create_customer_portal_session(request):
    """Lets an existing Premium subscriber manage/cancel their plan via Stripe's hosted portal."""
    if not billing_configured():
        return HttpResponseServerError('Billing is not configured on this server.')

    profile = request.user.profile
    if not profile.stripe_customer_id:
        return redirect('upgrade')

    stripe = _stripe()
    try:
        session = stripe.billing_portal.Session.create(
            customer=profile.stripe_customer_id,
            return_url=request.build_absolute_uri(reverse('profile')),
        )
    except stripe.error.StripeError:
        logger.exception('Stripe portal session creation failed for user %s', request.user.id)
        return HttpResponseServerError('Could not open the billing portal. Please try again shortly.')
    except Exception:
        logger.exception('Unexpected error creating billing portal session for user %s', request.user.id)
        return HttpResponseServerError('Could not open the billing portal. Please try again shortly.')

    return redirect(session.url, permanent=False)


def _set_plan_for_customer(stripe_customer_id: str, plan: str) -> None:
    from .models import Profile

    updated = Profile.objects.filter(stripe_customer_id=stripe_customer_id).update(plan=plan)
    if not updated:
        logger.warning('Stripe webhook: no Profile found for customer %s (plan=%s)', stripe_customer_id, plan)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook endpoint. Must stay CSRF-exempt (Stripe doesn't send a CSRF
    token) — request authenticity is instead verified via the signed
    Stripe-Signature header below, which is the standard/required approach.
    """
    if not billing_configured():
        return HttpResponseServerError('Billing is not configured on this server.')

    stripe = _stripe()
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        logger.warning('Stripe webhook signature verification failed: %s', exc)
        return HttpResponseBadRequest('Invalid payload or signature.')

    # Guard against Stripe retrying the same event (network hiccup, timeout,
    # etc.) so we don't double-apply plan changes.
    event_id = event.get('id')
    if event_id:
        from django.core.cache import cache

        cache_key = f'stripe-webhook-processed:{event_id}'
        if not cache.add(cache_key, True, timeout=60 * 60 * 24):
            logger.info('Stripe webhook: duplicate event %s ignored', event_id)
            return HttpResponse(status=200)

    event_type = event['type']
    data = event['data']['object']

    if event_type == 'checkout.session.completed':
        from .models import Profile

        user_id = data.get('client_reference_id') or (data.get('metadata') or {}).get('user_id')
        customer_id = data.get('customer')
        if user_id and customer_id:
            Profile.objects.filter(user_id=user_id).update(
                plan='premium',
                stripe_customer_id=customer_id,
            )
        else:
            logger.warning('checkout.session.completed missing user_id/customer: %s', data.get('id'))

    elif event_type in ('customer.subscription.deleted', 'customer.subscription.paused'):
        customer_id = data.get('customer')
        if customer_id:
            _set_plan_for_customer(customer_id, 'free')

    elif event_type == 'customer.subscription.updated':
        customer_id = data.get('customer')
        status = data.get('status')
        if customer_id and status in ('active', 'trialing'):
            _set_plan_for_customer(customer_id, 'premium')
        elif customer_id and status in ('canceled', 'unpaid', 'incomplete_expired'):
            _set_plan_for_customer(customer_id, 'free')

    elif event_type == 'invoice.payment_failed':
        # Don't immediately downgrade on a single failed payment — Stripe will
        # retry per its dunning settings, and `customer.subscription.updated`
        # fires with status='past_due'/'unpaid' if it ultimately fails for good.
        logger.info('Stripe invoice.payment_failed for customer %s', data.get('customer'))

    return HttpResponse(status=200)
