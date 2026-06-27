/**
 * analytics_tracker.js
 *
 * Include on any page with a video player.
 * Wrap your <video> in a div with id="ac-player-wrapper" and data-* attrs:
 *
 *   <div id="ac-player-wrapper"
 *        data-anime-slug="naruto"
 *        data-anime-title="Naruto"
 *        data-episode="1"
 *        data-genre="Action">
 *     <video src="..." controls></video>
 *   </div>
 */
(function () {
  "use strict";

  var wrapper = document.getElementById("ac-player-wrapper");
  if (!wrapper) return;

  var meta = {
    anime_slug: wrapper.dataset.animeSlug || "",
    anime_title: wrapper.dataset.animeTitle || "",
    episode_number: parseInt(wrapper.dataset.episode, 10) || null,
    genre: wrapper.dataset.genre || "",
  };

  var video = wrapper.querySelector("video");
  if (!video) return;

  var startTime = null;
  var sent = false;

  video.addEventListener("play", function () {
    if (startTime === null) startTime = Date.now();
  });

  function sendEvent(completed) {
    if (sent) return;
    sent = true;
    var duration = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;
    var payload = JSON.stringify(
      Object.assign({}, meta, { watch_duration_seconds: duration, completed: completed })
    );
    navigator.sendBeacon("/analytics/api/watch/", payload);
  }

  video.addEventListener("ended", function () { sendEvent(true); });
  window.addEventListener("beforeunload", function () { sendEvent(false); });

  // Search tracking helper — call after your search resolves:
  //   window.ACAnalytics.trackSearch("naruto", 24);
  window.ACAnalytics = {
    trackSearch: function (query, resultsCount) {
      fetch("/analytics/api/search/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, results_count: resultsCount }),
      }).catch(function () {});
    },
  };
}());
