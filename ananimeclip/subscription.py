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

from django.http import HttpResponseForbidden
from django.shortcuts import redirect


PLAN_FREE = "free"
PLAN_PREMIUM = "premium"


def get_plan(request) -> str:
    """Return the user's current plan slug, defaulting to 'free'."""
    if not request.user.is_authenticated:
        return PLAN_FREE
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return PLAN_FREE
    return getattr(profile, "plan", PLAN_FREE)


def is_premium(request) -> bool:
    return get_plan(request) == PLAN_PREMIUM


def can_access_premium_content(request) -> bool:
    """
    Returns True if the request is allowed to access premium-only content.
    Staff/superusers always get access (useful for QA).
    """
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return True
    return is_premium(request)


def premium_required(view_func):
    """
    Decorator: redirect free-tier users to the upgrade page.
    Usage:
        @login_required
        @premium_required
        def watch_premium_episode(request, ...): ...
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not can_access_premium_content(request):
            return redirect("upgrade")  # add 'upgrade' url in urls.py
        return view_func(request, *args, **kwargs)
    return _wrapped


def filter_premium_content(qs, request, premium_field: str = "is_premium_only"):
    """
    Exclude premium-only items from a queryset for free-tier users.
    Requires the model to have an `is_premium_only` BooleanField.
    """
    if can_access_premium_content(request):
        return qs
    return qs.filter(**{premium_field: False})
