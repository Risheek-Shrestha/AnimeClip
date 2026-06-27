/**
 * analytics_tracker.js
 *
 * Include on any streaming page after the player markup. Add data-* attrs
 * directly to the <video id="main-player"> element (the same one used by
 * the watch-progress-save logic in animeclip.js):
 *
 *   <video id="main-player"
 *          data-anime-slug="naruto"
 *          data-anime-title="Naruto"
 *          data-episode="1"
 *          data-genre="Action">
 *     ...
 *   </video>
 */
(function () {
  "use strict";

  var video = document.getElementById("main-player");
  if (!video) return;

  var meta = {
    anime_slug: video.dataset.animeSlug || "",
    anime_title: video.dataset.animeTitle || "",
    episode_number: parseInt(video.dataset.episode, 10) || null,
    genre: video.dataset.genre || "",
  };

  // Nothing to attribute the event to — skip silently.
  if (!meta.anime_slug && !meta.anime_title) return;

  var startTime = null;
  var sent = false;

  video.addEventListener("play", function () {
    if (startTime === null) startTime = Date.now();
  });

  function sendEvent(completed) {
    if (sent) return;
    if (startTime === null) return; // never actually played
    sent = true;
    var duration = Math.round((Date.now() - startTime) / 1000);
    var payload = JSON.stringify(
      Object.assign({}, meta, { watch_duration_seconds: duration, completed: completed })
    );
    navigator.sendBeacon("/analytics/api/watch/", payload);
  }

  video.addEventListener("ended", function () { sendEvent(true); });
  // beforeunload doesn't fire reliably on mobile (bfcache/backgrounding),
  // so also flush on pagehide — sendEvent() is idempotent via the `sent` flag.
  window.addEventListener("pagehide", function () { sendEvent(false); });
  window.addEventListener("beforeunload", function () { sendEvent(false); });
}());
