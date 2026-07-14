/**
 * Chromecast (Google Cast Web Sender) + AirPlay support for the
 * <video id="main-player"> element on the streaming pages.
 *
 * No API keys or developer registration required:
 *  - Chromecast uses the default media receiver app
 *    (chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID), which Google
 *    hosts for free for any site.
 *  - AirPlay uses Safari/WebKit's built-in target-picker API.
 *
 * Both buttons stay hidden until their respective platform/API is
 * actually available, so this is a silent no-op on browsers that
 * support neither (e.g. desktop Firefox/Chrome without a cast device).
 */
(function () {
  'use strict';

  var video = document.getElementById('main-player');
  if (!video) return;

  var castBtn = document.getElementById('cast-btn');
  var airplayBtn = document.getElementById('airplay-btn');

  // ---------------------------------------------------------------
  // Shared helper: figure out what we're actually playing right now
  // ---------------------------------------------------------------
  function getCurrentMediaInfo() {
    var src = video.currentSrc || video.src;
    var isHls = /\.m3u8(\?|$)/i.test(src);
    return {
      url: src,
      contentType: isHls ? 'application/x-mpegurl' : 'video/mp4',
      title: video.dataset.animeTitle || document.title,
      poster: video.poster || ''
    };
  }

  // ---------------------------------------------------------------
  // AirPlay (Safari / WebKit)
  // ---------------------------------------------------------------
  function initAirplay() {
    if (!window.WebKitPlaybackTargetAvailabilityEvent ||
        typeof video.webkitShowPlaybackTargetPicker !== 'function') {
      return; // Not Safari/WebKit — no AirPlay API at all.
    }

    video.addEventListener('webkitplaybacktargetavailabilitychanged', function (event) {
      if (!airplayBtn) return;
      airplayBtn.style.display = (event.availability === 'available') ? 'flex' : 'none';
    });

    if (airplayBtn) {
      airplayBtn.addEventListener('click', function () {
        video.webkitShowPlaybackTargetPicker();
      });
    }
  }

  // ---------------------------------------------------------------
  // Chromecast (Google Cast Web Sender SDK)
  // ---------------------------------------------------------------
  function initChromecast() {
    if (!castBtn) return;

    window['__onGCastApiAvailable'] = function (isAvailable) {
      if (!isAvailable || !window.cast || !window.chrome) return;

      var context = cast.framework.CastContext.getInstance();
      context.setOptions({
        receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
        autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED
      });

      castBtn.style.display = 'flex';

      context.addEventListener(
        cast.framework.CastContextEventType.CAST_STATE_CHANGED,
        function (event) {
          var connected = event.castState === cast.framework.CastState.CONNECTED;
          castBtn.classList.toggle('is-active', connected);
        }
      );

      castBtn.addEventListener('click', function () {
        var castState = context.getCastState();

        // Already connected — clicking again disconnects.
        if (castState === cast.framework.CastState.CONNECTED) {
          context.endCurrentSession(true);
          return;
        }

        context.requestSession().then(function () {
          var media = getCurrentMediaInfo();
          var mediaInfo = new chrome.cast.media.MediaInfo(media.url, media.contentType);
          mediaInfo.metadata = new chrome.cast.media.GenericMediaMetadata();
          mediaInfo.metadata.title = media.title;
          if (media.poster) {
            mediaInfo.metadata.images = [new chrome.cast.Image(media.poster)];
          }
          mediaInfo.currentTime = video.currentTime || 0;

          var request = new chrome.cast.media.LoadRequest(mediaInfo);
          var session = context.getCurrentSession();
          if (!session) return;

          session.loadMedia(request).then(
            function () {
              // Loaded on the receiver — pause local playback so audio
              // doesn't play from both the TV and this device at once.
              video.pause();
            },
            function (err) {
              console.error('Cast loadMedia failed', err);
            }
          );
        }).catch(function (err) {
          // User cancelled the device picker, or no devices on the network.
          if (err !== 'cancel') console.error('Cast session request failed', err);
        });
      });
    };

    var script = document.createElement('script');
    script.src = 'https://www.gstatic.com/cv/js/sender/v1/cast_sender.js';
    script.async = true;
    document.head.appendChild(script);
  }

  initAirplay();
  initChromecast();
})();
