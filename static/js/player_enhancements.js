/**
 * player_enhancements.js
 *
 * Adds keyboard shortcuts, playback speed control, and Picture-in-Picture
 * to the <video id="main-player"> element on streaming pages.
 *
 * Include AFTER the main player markup.  All features are opt-in / gracefully
 * degraded — nothing here breaks playback if unsupported.
 */
(function () {
  'use strict';

  var video = document.getElementById('main-player');
  if (!video) return;

  // ─── Playback Speed ───────────────────────────────────────────────────────

  var SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];
  var DEFAULT_SPEED = 1;
  var SPEED_KEY = 'animeclip_playback_speed';

  function applySpeed(rate) {
    video.playbackRate = rate;
    try { localStorage.setItem(SPEED_KEY, String(rate)); } catch (_) {}
    updateSpeedUI(rate);
  }

  function updateSpeedUI(rate) {
    document.querySelectorAll('[data-speed]').forEach(function (btn) {
      var active = parseFloat(btn.dataset.speed) === rate;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-checked', active ? 'true' : 'false');
    });
    var label = document.getElementById('speed-label');
    if (label) label.textContent = rate + 'x';
  }

  // Restore saved speed
  try {
    var saved = parseFloat(localStorage.getItem(SPEED_KEY));
    if (SPEEDS.indexOf(saved) !== -1) DEFAULT_SPEED = saved;
  } catch (_) {}

  video.addEventListener('loadedmetadata', function () {
    applySpeed(DEFAULT_SPEED);
  });

  // Wire speed buttons (rendered by the template)
  document.querySelectorAll('[data-speed]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      applySpeed(parseFloat(btn.dataset.speed));
    });
  });

  // ─── Picture-in-Picture ──────────────────────────────────────────────────

  var pipBtn = document.getElementById('pip-btn');
  if (pipBtn) {
    if (!document.pictureInPictureEnabled) {
      pipBtn.style.display = 'none';
    } else {
      pipBtn.addEventListener('click', function () {
        if (document.pictureInPictureElement) {
          document.exitPictureInPicture().catch(function () {});
        } else {
          video.requestPictureInPicture().catch(function () {});
        }
      });
      video.addEventListener('enterpictureinpicture', function () {
        pipBtn.classList.add('is-active');
        pipBtn.setAttribute('aria-label', 'Exit Picture-in-Picture');
      });
      video.addEventListener('leavepictureinpicture', function () {
        pipBtn.classList.remove('is-active');
        pipBtn.setAttribute('aria-label', 'Picture-in-Picture');
      });
    }
  }

  // ─── Keyboard Shortcuts ───────────────────────────────────────────────────
  //
  // Standard shortcuts matching Crunchyroll / Netflix / YouTube:
  //   Space / K   – play/pause
  //   ← / J       – seek back 10 s
  //   → / L       – seek forward 10 s
  //   ↑           – volume up 10 %
  //   ↓           – volume down 10 %
  //   M           – mute/unmute
  //   F           – fullscreen toggle
  //   C           – captions/subtitles cycle
  //   >           – speed up
  //   <           – speed down
  //   P           – Picture-in-Picture
  //   0-9         – jump to 0–90% of duration

  function seekBy(seconds) {
    video.currentTime = Math.max(0, Math.min(video.duration || 0, video.currentTime + seconds));
  }

  function changeSpeed(direction) {
    var idx = SPEEDS.indexOf(video.playbackRate);
    if (idx === -1) idx = SPEEDS.indexOf(1);
    idx = Math.max(0, Math.min(SPEEDS.length - 1, idx + direction));
    applySpeed(SPEEDS[idx]);
  }

  function showOsd(msg) {
    var osd = document.getElementById('player-osd');
    if (!osd) return;
    osd.textContent = msg;
    osd.classList.add('visible');
    clearTimeout(osd._hideTimer);
    osd._hideTimer = setTimeout(function () {
      osd.classList.remove('visible');
    }, 1200);
  }

  function cycleCaptions() {
    var tracks = Array.from(video.textTracks);
    if (!tracks.length) return;
    var activeIdx = tracks.findIndex(function (t) { return t.mode === 'showing'; });
    if (activeIdx >= 0) tracks[activeIdx].mode = 'hidden';
    var nextIdx = (activeIdx + 1) % (tracks.length + 1); // +1 = off
    if (nextIdx < tracks.length) {
      tracks[nextIdx].mode = 'showing';
      showOsd('CC: ' + (tracks[nextIdx].label || tracks[nextIdx].language));
    } else {
      showOsd('CC: Off');
    }
  }

  document.addEventListener('keydown', function (e) {
    // Don't intercept shortcuts when focus is inside a text input / textarea
    var tag = (document.activeElement || {}).tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (document.activeElement && document.activeElement.isContentEditable) return;

    var handled = true;
    switch (e.key) {
      case ' ':
      case 'k':
      case 'K':
        if (video.paused) { video.play(); showOsd('▶'); } else { video.pause(); showOsd('⏸'); }
        break;
      case 'ArrowLeft':
      case 'j':
      case 'J':
        seekBy(-10); showOsd('◀ 10s');
        break;
      case 'ArrowRight':
      case 'l':
      case 'L':
        seekBy(+10); showOsd('▶ 10s');
        break;
      case 'ArrowUp':
        video.volume = Math.min(1, video.volume + 0.1);
        showOsd('Vol ' + Math.round(video.volume * 100) + '%');
        break;
      case 'ArrowDown':
        video.volume = Math.max(0, video.volume - 0.1);
        showOsd('Vol ' + Math.round(video.volume * 100) + '%');
        break;
      case 'm':
      case 'M':
        video.muted = !video.muted;
        showOsd(video.muted ? '🔇' : '🔊');
        break;
      case 'f':
      case 'F':
        if (!document.fullscreenElement) {
          (video.closest('.player-wrapper') || video).requestFullscreen().catch(function () {});
        } else {
          document.exitFullscreen().catch(function () {});
        }
        break;
      case 'c':
      case 'C':
        cycleCaptions();
        break;
      case '>':
        changeSpeed(+1); showOsd(video.playbackRate + 'x');
        break;
      case '<':
        changeSpeed(-1); showOsd(video.playbackRate + 'x');
        break;
      case 'p':
      case 'P':
        if (document.pictureInPictureEnabled) {
          if (document.pictureInPictureElement) {
            document.exitPictureInPicture().catch(function () {});
          } else {
            video.requestPictureInPicture().catch(function () {});
          }
        }
        break;
      default:
        // 0–9: jump to percentage of video
        if (e.key >= '0' && e.key <= '9' && !e.ctrlKey && !e.metaKey && !e.altKey) {
          var pct = parseInt(e.key, 10) / 10;
          video.currentTime = (video.duration || 0) * pct;
          showOsd(Math.round(pct * 100) + '%');
        } else {
          handled = false;
        }
    }
    if (handled) e.preventDefault();
  });

})();
