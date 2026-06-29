"""
TOTP Two-Factor Authentication
================================
Uses pyotp for TOTP generation/verification and qrcode for QR image output.

All TOTP state is stored on the user's Profile via two new fields:
  totp_secret   — base32 TOTP seed (blank = 2FA not enabled)
  totp_enabled  — gating flag; set True only after user verifies the first code

Views wired in urls.py:
  /account/2fa/setup/    — show QR code, confirm first code
  /account/2fa/disable/  — turn off 2FA (requires current password)
  /account/2fa/verify/   — post-login second step

Middleware:
  TwoFactorMiddleware — redirects authenticated users who haven't completed
  the second step to /account/2fa/verify/.
"""

from __future__ import annotations

import base64
import io

import pyotp
import qrcode
from django.contrib import messages as django_messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

TOTP_SESSION_KEY = "totp_verified"
TOTP_ISSUER = "AnimeClip"


def get_or_create_secret(profile) -> str:
    if not profile.totp_secret:
        profile.totp_secret = pyotp.random_base32()
        profile.save(update_fields=["totp_secret"])
    return profile.totp_secret


def verify_totp_code(profile, code: str) -> bool:
    if not profile.totp_secret:
        return False
    totp = pyotp.TOTP(profile.totp_secret)
    return totp.verify(code, valid_window=1)


def totp_uri(profile, user) -> str:
    totp = pyotp.TOTP(profile.totp_secret)
    return totp.provisioning_uri(name=user.email or user.username, issuer_name=TOTP_ISSUER)


def qr_png_b64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@login_required
@require_http_methods(["GET", "POST"])
def totp_setup(request):
    profile = request.user.profile
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        if verify_totp_code(profile, code):
            profile.totp_enabled = True
            profile.save(update_fields=["totp_enabled"])
            request.session[TOTP_SESSION_KEY] = True
            django_messages.success(request, "Two-factor authentication enabled.")
            return redirect("profile")
        else:
            django_messages.error(request, "Invalid code — please try again.")

    secret = get_or_create_secret(profile)
    uri = totp_uri(profile, request.user)
    qr_b64 = qr_png_b64(uri)
    return render(request, "totp_setup.html", {"secret": secret, "qr_b64": qr_b64})


@login_required
@require_POST
def totp_disable(request):
    password = request.POST.get("password", "")
    user = authenticate(request, username=request.user.username, password=password)
    if user is None:
        django_messages.error(request, "Incorrect password.")
        return redirect("profile")
    profile = user.profile
    profile.totp_secret = ""
    profile.totp_enabled = False
    profile.save(update_fields=["totp_secret", "totp_enabled"])
    request.session.pop(TOTP_SESSION_KEY, None)
    django_messages.success(request, "Two-factor authentication disabled.")
    return redirect("profile")


@require_http_methods(["GET", "POST"])
def totp_verify(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.session.get(TOTP_SESSION_KEY):
        return redirect(request.GET.get("next", "index"))

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        profile = getattr(request.user, "profile", None)
        if profile and verify_totp_code(profile, code):
            request.session[TOTP_SESSION_KEY] = True
            return HttpResponseRedirect(request.POST.get("next", reverse("index")))
        django_messages.error(request, "Invalid code.")

    return render(request, "totp_verify.html", {"next": request.GET.get("next", reverse("index"))})


TOTP_EXEMPT_PATHS = {"/account/2fa/verify/", "/logout/", "/healthz/"}


class TwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.path not in TOTP_EXEMPT_PATHS
            and not request.path.startswith("/admin/")
        ):
            profile = getattr(request.user, "profile", None)
            if profile and getattr(profile, "totp_enabled", False):
                if not request.session.get(TOTP_SESSION_KEY):
                    return HttpResponseRedirect(
                        f"{reverse('totp_verify')}?next={request.path}"
                    )
        return self.get_response(request)
