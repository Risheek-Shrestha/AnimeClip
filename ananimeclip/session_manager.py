"""
Device/Session Management & Concurrent-Stream Limiter
======================================================
Tracks active sessions in Redis and enforces per-account stream limits.

Redis key schema:
  sessions:<user_id>          HASH  sid -> JSON{device,ip,ua,created_at,last_seen}
  streams:<user_id>           ZSET  sid -> epoch (score = last heartbeat)

Usage:
  - SessionManagerMiddleware  — keeps session registry in sync
  - register_session(request) — called on login
  - revoke_session(request, sid) — "log out this device"
  - revoke_all_other_sessions(request) — "log out other devices"
  - enforce_stream_limit(request, max_streams=2) — call from streaming views
"""

from __future__ import annotations

import json
import time

from django.contrib.auth import logout
from django.core.cache import cache  # django-redis
from django.http import JsonResponse
from django.utils import timezone

SESSION_HASH_PREFIX = "sessions:"
STREAM_ZSET_PREFIX = "streams:"
SESSION_TTL = 60 * 60 * 24 * 30  # 30 days
STREAM_HEARTBEAT_TTL = 60 * 5    # 5 min — stream considered stale after this


# ---------------------------------------------------------------------------
# Low-level helpers (use raw redis client for HASH/ZSET ops)
# ---------------------------------------------------------------------------

def _redis():
    """Return the raw Redis client from django-redis."""
    from django_redis import get_redis_connection
    return get_redis_connection("default")


def register_session(request):
    """
    Call after a successful login to store session metadata in Redis.
    """
    if not request.user.is_authenticated:
        return
    uid = request.user.pk
    sid = request.session.session_key or "nosid"
    r = _redis()
    payload = json.dumps({
        "sid": sid,
        "ip": _get_ip(request),
        "ua": request.META.get("HTTP_USER_AGENT", "")[:200],
        "created_at": timezone.now().isoformat(),
        "last_seen": time.time(),
    })
    r.hset(f"{SESSION_HASH_PREFIX}{uid}", sid, payload)
    r.expire(f"{SESSION_HASH_PREFIX}{uid}", SESSION_TTL)


def revoke_session(request, sid: str):
    """
    Remove a specific session from the registry.
    Does NOT force-expire the actual Django session (would need SessionStore).
    Returns True on success.
    """
    if not request.user.is_authenticated:
        return False
    uid = request.user.pk
    r = _redis()
    r.hdel(f"{SESSION_HASH_PREFIX}{uid}", sid)
    r.zrem(f"{STREAM_ZSET_PREFIX}{uid}", sid)
    return True


def revoke_all_other_sessions(request):
    """Log out every device except the current one."""
    if not request.user.is_authenticated:
        return 0
    uid = request.user.pk
    current_sid = request.session.session_key
    r = _redis()
    key = f"{SESSION_HASH_PREFIX}{uid}"
    all_sids = r.hkeys(key)
    removed = 0
    for sid in all_sids:
        sid_str = sid.decode() if isinstance(sid, bytes) else sid
        if sid_str != current_sid:
            r.hdel(key, sid_str)
            r.zrem(f"{STREAM_ZSET_PREFIX}{uid}", sid_str)
            removed += 1
    return removed


def list_sessions(request) -> list[dict]:
    """Return metadata for all active sessions for the current user."""
    if not request.user.is_authenticated:
        return []
    uid = request.user.pk
    r = _redis()
    raw = r.hvals(f"{SESSION_HASH_PREFIX}{uid}")
    sessions = []
    current_sid = request.session.session_key
    for v in raw:
        try:
            d = json.loads(v)
            d["is_current"] = d.get("sid") == current_sid
            sessions.append(d)
        except Exception:
            pass
    return sorted(sessions, key=lambda x: x.get("last_seen", 0), reverse=True)


# ---------------------------------------------------------------------------
# Concurrent-stream enforcement
# ---------------------------------------------------------------------------

MAX_CONCURRENT_STREAMS = 2  # default; override per-call


def stream_heartbeat(request):
    """
    Call periodically (every ~60 s) from the video player via AJAX.
    Bumps the score in the ZSET so the stream is considered alive.
    """
    if not request.user.is_authenticated:
        return
    uid = request.user.pk
    sid = request.session.session_key or "nosid"
    r = _redis()
    now = time.time()
    r.zadd(f"{STREAM_ZSET_PREFIX}{uid}", {sid: now})
    r.expire(f"{STREAM_ZSET_PREFIX}{uid}", STREAM_HEARTBEAT_TTL * 3)


def enforce_stream_limit(request, max_streams: int = MAX_CONCURRENT_STREAMS) -> bool:
    """
    Returns True if the request is allowed to start/continue a stream.
    Evicts stale heartbeats first, then counts live sessions.
    Should be called at the top of streaming views; if False, return 429.
    """
    if not request.user.is_authenticated:
        return True  # anonymous — handle elsewhere
    uid = request.user.pk
    sid = request.session.session_key or "nosid"
    r = _redis()
    zkey = f"{STREAM_ZSET_PREFIX}{uid}"
    cutoff = time.time() - STREAM_HEARTBEAT_TTL
    # Remove stale entries
    r.zremrangebyscore(zkey, "-inf", cutoff)
    # Count remaining live streams
    live_count = r.zcard(zkey)
    # Allow if under limit OR if this sid is already in the set (continuing stream)
    already_streaming = r.zscore(zkey, sid) is not None
    if already_streaming or live_count < max_streams:
        stream_heartbeat(request)
        return True
    return False


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


# ---------------------------------------------------------------------------
# Middleware — keep last_seen fresh on every request
# ---------------------------------------------------------------------------

class SessionManagerMiddleware:
    """
    Lightweight: only touches Redis when user is authenticated and session exists.
    Add to MIDDLEWARE after AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and request.session.session_key:
            uid = request.user.pk
            sid = request.session.session_key
            r = _redis()
            hkey = f"{SESSION_HASH_PREFIX}{uid}"
            raw = r.hget(hkey, sid)
            if raw:
                try:
                    d = json.loads(raw)
                    d["last_seen"] = time.time()
                    r.hset(hkey, sid, json.dumps(d))
                except Exception:
                    pass
        return response
