/**
 * AnimeClip Offline Playback — Service Worker Cache
 * ==================================================
 * Caches video blobs in the Cache Storage API via the service worker
 * so saved episodes play without a network connection.
 *
 * This supplements the existing sw.js; paste the INSTALL and FETCH handlers
 * below into your sw.js, and call OfflineVideo.save() / OfflineVideo.list()
 * from the episode/movie pages.
 *
 * Limitations:
 *   - Cache Storage has no DRM — this is convenience offline, not protected DL.
 *   - Mobile browsers cap storage; large video files may be evicted.
 *   - Chrome: ~unlimited (until disk quota); Firefox/Safari: more restricted.
 *
 * ── Service Worker additions (paste into sw.js) ───────────────────────────
 *
 * const OFFLINE_VIDEO_CACHE = 'animeclip-offline-videos-v1';
 *
 * // In the fetch handler, intercept video requests:
 * self.addEventListener('fetch', (event) => {
 *   const url = new URL(event.request.url);
 *   if (url.pathname.startsWith('/offline-video/')) {
 *     event.respondWith(
 *       caches.open(OFFLINE_VIDEO_CACHE).then(cache =>
 *         cache.match(event.request).then(r => r || fetch(event.request))
 *       )
 *     );
 *     return;
 *   }
 *   // ... rest of your existing fetch handler
 * });
 *
 * // Message handler to cache a video URL on demand:
 * self.addEventListener('message', (event) => {
 *   if (event.data && event.data.type === 'CACHE_VIDEO') {
 *     const { url, key } = event.data;
 *     caches.open(OFFLINE_VIDEO_CACHE).then(cache => {
 *       fetch(url).then(response => {
 *         cache.put(key, response);
 *         event.source && event.source.postMessage({ type: 'CACHED', key });
 *       }).catch(err => {
 *         event.source && event.source.postMessage({ type: 'CACHE_ERROR', key, err: String(err) });
 *       });
 *     });
 *   }
 *   if (event.data && event.data.type === 'DELETE_VIDEO') {
 *     caches.open(OFFLINE_VIDEO_CACHE).then(cache => cache.delete(event.data.key));
 *   }
 * });
 *
 * ── Page-side API ─────────────────────────────────────────────────────────
 */
const OfflineVideo = (() => {
  const CACHE_NAME = 'animeclip-offline-videos-v1';

  function swReady() {
    return navigator.serviceWorker && navigator.serviceWorker.ready;
  }

  /**
   * Save a video for offline playback.
   * @param {string} videoUrl  - The actual video stream URL.
   * @param {string} cacheKey  - A stable key, e.g. '/offline-video/ep-42'.
   * @param {function} onProgress - Optional callback(percent).
   */
  async function save(videoUrl, cacheKey, onProgress) {
    if (!swReady()) throw new Error('Service worker not available');
    const sw = await navigator.serviceWorker.ready;
    return new Promise((resolve, reject) => {
      const channel = new MessageChannel();
      channel.port1.onmessage = (e) => {
        if (e.data.type === 'CACHED') resolve(cacheKey);
        else reject(new Error(e.data.err || 'cache failed'));
      };
      sw.active.postMessage(
        { type: 'CACHE_VIDEO', url: videoUrl, key: cacheKey },
        [channel.port2]
      );
    });
  }

  /** Remove a saved episode. */
  async function remove(cacheKey) {
    if (!swReady()) return;
    const sw = await navigator.serviceWorker.ready;
    sw.active.postMessage({ type: 'DELETE_VIDEO', key: cacheKey });
  }

  /** List all cached video keys. */
  async function list() {
    if (!('caches' in window)) return [];
    const cache = await caches.open(CACHE_NAME);
    const keys = await cache.keys();
    return keys.map(r => r.url);
  }

  return { save, remove, list };
})();
