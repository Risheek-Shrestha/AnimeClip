"""
Subscription Tier Mechanics
=============================
Adds Free/Premium plan gating using the existing content_access pattern.
The `plan` field lives on Profile (added in migration 0037).

To gate a view for Premium-only:
    from .subscription import premium_required
    @premium_required
    def my_view(request): ...

To gate content objects:
    from .subscription import can_access_premium_content
    if not can_access_premium_content(request):
        return redirect('upgrade')

Actual billing is intentionally out of scope — this is the gating layer only.
Wire up Stripe/Paddle webhooks to flip profile.plan when a payment succeeds.
"""

from __future__ import annotations

from functools import wraps

from django.shortcuts import redirect

PLAN_FREE = 'free'
PLAN_PREMIUM = 'premium'


def get_plan(request) -> str:
    if not request.user.is_authenticated:
        return PLAN_FREE
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return PLAN_FREE
    return getattr(profile, 'plan', PLAN_FREE)


def is_premium(request) -> bool:
    return get_plan(request) == PLAN_PREMIUM


def can_access_premium_content(request) -> bool:
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return True
    return is_premium(request)


def premium_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not can_access_premium_content(request):
            return redirect('upgrade')
        return view_func(request, *args, **kwargs)

    return _wrapped


def filter_premium_content(qs, request, premium_field: str = 'is_premium_only'):
    if can_access_premium_content(request):
        return qs
    return qs.filter(**{premium_field: False})
