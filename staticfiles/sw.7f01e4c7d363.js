/**
 * AnimeClip Service Worker
 * Strategy: Cache-first for static assets, network-first for pages,
 * offline fallback for navigation.
 */

const CACHE_NAME = 'animeclip-v1';
const OFFLINE_URL = '/offline/';

const PRECACHE_ASSETS = [
  '/',
  '/offline/',
  '/static/assets/css/bootstrap.min.css',
  '/static/assets/css/style-3d.css',
  '/static/css/player_enhancements.css',
  '/static/manifest.json',
];

// ── Install: pre-cache critical assets ───────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_ASSETS))
  );
  self.skipWaiting();
});

// ── Activate: purge old caches ───────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Fetch strategy ───────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, cross-origin, admin, API
  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/admin/') ||
      url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/analytics/')) return;

  // Static assets → cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(request, clone));
        }
        return resp;
      }))
    );
    return;
  }

  // HTML navigation → network-first with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }
});
