"""
Device/Session Management & Concurrent-Stream Limiter
======================================================
Tracks active sessions in Redis and enforces per-account stream limits.

Redis key schema:
  sessions:<user_id>  HASH  sid -> JSON{device,ip,ua,created_at,last_seen}
  streams:<user_id>   ZSET  sid -> epoch (score = last heartbeat)

Usage:
  - SessionManagerMiddleware  — keeps session registry in sync
  - register_session(request) — called on login
  - revoke_session(request, sid) — "log out this device"
  - revoke_all_other_sessions(request) — "log out other devices"
  - enforce_stream_limit(request, max_streams=2) — call from streaming views
"""

from __future__ import annotations

import json
import logging
import time

from django.utils import timezone

logger = logging.getLogger(__name__)

SESSION_HASH_PREFIX = "sessions:"
STREAM_ZSET_PREFIX = "streams:"
SESSION_TTL = 60 * 60 * 24 * 30  # 30 days
STREAM_HEARTBEAT_TTL = 60 * 5    # 5 min — stream considered stale after this


def _redis():
    from django_redis import get_redis_connection
    return get_redis_connection("default")


def register_session(request):
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
    if not request.user.is_authenticated:
        return False
    uid = request.user.pk
    r = _redis()
    r.hdel(f"{SESSION_HASH_PREFIX}{uid}", sid)
    r.zrem(f"{STREAM_ZSET_PREFIX}{uid}", sid)
    return True


def revoke_all_other_sessions(request):
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
            logger.debug("Could not parse session payload", exc_info=True)
    return sorted(sessions, key=lambda x: x.get("last_seen", 0), reverse=True)


MAX_CONCURRENT_STREAMS = 2


def stream_heartbeat(request):
    if not request.user.is_authenticated:
        return
    uid = request.user.pk
    sid = request.session.session_key or "nosid"
    r = _redis()
    now = time.time()
    r.zadd(f"{STREAM_ZSET_PREFIX}{uid}", {sid: now})
    r.expire(f"{STREAM_ZSET_PREFIX}{uid}", STREAM_HEARTBEAT_TTL * 3)


def enforce_stream_limit(request, max_streams: int = MAX_CONCURRENT_STREAMS) -> bool:
    if not request.user.is_authenticated:
        return True
    uid = request.user.pk
    sid = request.session.session_key or "nosid"
    r = _redis()
    zkey = f"{STREAM_ZSET_PREFIX}{uid}"
    cutoff = time.time() - STREAM_HEARTBEAT_TTL
    r.zremrangebyscore(zkey, "-inf", cutoff)
    live_count = r.zcard(zkey)
    already_streaming = r.zscore(zkey, sid) is not None
    if already_streaming or live_count < max_streams:
        stream_heartbeat(request)
        return True
    return False


def _get_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class SessionManagerMiddleware:
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
                    logger.debug("Could not update session last_seen", exc_info=True)
        return response
