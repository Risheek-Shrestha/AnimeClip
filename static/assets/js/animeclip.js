/**
 * animeclip.js — shared utilities for AnimeClip
 * Handles: CSRF token, Watch Later toggle, Playlist modal population,
 * password visibility toggles, header live search, preloader, banner
 * slider/countdown, profile-select avatar picker, browse filters,
 * comment likes, star ratings, follow button, video resume/progress
 * tracking, and the autoplay-next-episode overlay.
 *
 * Loaded globally via base.html — do NOT duplicate in individual
 * templates. Every block below guards on the presence of its target
 * element(s), so it is always safe to include on every page.
 */

function getCSRF() {
  return document.cookie.split('; ').find(r => r.startsWith('csrftoken'))?.split('=')[1];
}

// ── Avatar image fallback (profile tiles + avatar picker) ────────────────────
// 'error' does not bubble, so this must be registered on the capture phase.
document.addEventListener('error', function (e) {
  const img = e.target;
  if (img.tagName !== 'IMG') return;
  const frame = img.closest('.profile-avatar-frame, .account-avatar');
  if (frame) { img.style.display = 'none'; frame.classList.add('avatar-fallback'); return; }
  const opt = img.closest('.avatar-opt');
  if (opt) opt.classList.add('avatar-broken');
}, true);

// ── Generic "are you sure?" guard for delete forms ────────────────────────────
// Add data-confirm="message" to any <form> instead of an inline onsubmit.
document.addEventListener('submit', function (e) {
  const form = e.target;
  if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
    e.preventDefault();
  }
});

// ── Header search form: navigation is handled by JS, never a real GET submit ─
document.querySelector('.header-search-form')?.addEventListener('submit', function (e) {
  e.preventDefault();
});

// ── Watch Later ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.watch-later-btn').forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const body = new URLSearchParams();
      if (this.dataset.episodeId) body.append('episode_id', this.dataset.episodeId);
      if (this.dataset.movieId)   body.append('movie_id',   this.dataset.movieId);
      fetch('/watch-later/toggle/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRF() },
        body,
      })
        .then(r => r.json())
        .then(data => {
          const added = data.status === 'added';
          this.innerHTML = added
            ? '<i class="fa fa-clock me-2"></i> Added to Watch Later'
            : '<i class="fa fa-clock me-2"></i> Watch Later';
          if (typeof showToast === 'function') {
            showToast(
              added ? 'Added to Watch Later' : 'Removed from Watch Later',
              added ? 'gold' : 'muted'
            );
          }
        });
    });
  });

  // ── Playlist modal ──────────────────────────────────────────────────────────
  document.getElementById('playlistModal')?.addEventListener('show.bs.modal', function (e) {
    const trigger   = e.relatedTarget;
    const episodeId = trigger?.dataset.episodeId || '';
    const movieId   = trigger?.dataset.movieId   || '';

    fetch('/playlists/json/')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('playlist-list');
        if (!data.playlists.length) {
          container.innerHTML = '<p class="playlist-empty">No playlists yet. <a href="/playlists/">Create one</a>.</p>';
          return;
        }
        container.innerHTML = data.playlists.map(p => `
          <form method="POST" action="/playlists/add-item/" class="mb-2">
            <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRF()}">
            <input type="hidden" name="playlist_id" value="${p.id}">
            ${episodeId ? `<input type="hidden" name="episode_id" value="${episodeId}">` : ''}
            ${movieId   ? `<input type="hidden" name="movie_id"   value="${movieId}">` : ''}
            <div class="d-flex justify-content-between align-items-center">
              <span class="playlist-name">${p.name}</span>
              <button type="submit" class="comment-btn active">Add</button>
            </div>
          </form>
        `).join('');
      });
  });

  // ── Password visibility toggle (login / signup / edit profile) ────────────
  document.querySelectorAll('.toggle-password').forEach(function (toggle) {
    toggle.addEventListener('click', function () {
      const input = document.querySelector(this.getAttribute('toggle'));
      const icon  = this.querySelector('i');
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
      } else {
        input.type = 'password';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
      }
    });
  });

  // ── Profile-select: highlight chosen avatar in the "new profile" form ─────
  document.querySelectorAll('.avatar-radio').forEach(function (radio) {
    radio.addEventListener('change', function () {
      document.querySelectorAll('.avatar-opt').forEach(function (el) {
        el.classList.remove('selected');
      });
      this.nextElementSibling.classList.add('selected');
    });
  });
  const firstAvatarChecked = document.querySelector('.avatar-radio:checked');
  if (firstAvatarChecked) firstAvatarChecked.nextElementSibling.classList.add('selected');

  // ── Profile-select: "+ Add Profile" tile opens the new-profile form ───────
  const addBtn    = document.getElementById('add-profile-btn');
  const addForm   = document.getElementById('add-form');
  const cancelBtn = document.getElementById('cancel-add-profile');
  addBtn?.addEventListener('click', function () {
    addForm.classList.remove('d-none');
    addBtn.classList.add('d-none');
  });
  cancelBtn?.addEventListener('click', function () {
    addForm.classList.add('d-none');
    addBtn.classList.remove('d-none');
  });

  // ── Browse filters: genre select auto-submits, sort buttons keep genre ────
  const browseForm = document.getElementById('browse-filter-form');
  if (browseForm) {
    const genreSelect = browseForm.querySelector('[name=genre]');
    genreSelect?.addEventListener('change', function () { browseForm.submit(); });
    browseForm.querySelectorAll('.sort-btn[data-keep-genre]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (genreSelect) genreSelect.value = this.dataset.keepGenre;
      });
    });
  }

  // ── Comment like button (streaming + streaming_movie) ─────────────────────
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.like-btn');
    if (!btn) return;
    const id = btn.dataset.id;
    fetch(`/comment/${id}/like/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCSRF() },
    })
      .then(res => {
        if (!res.ok) throw new Error('Request failed');
        return res.json();
      })
      .then(data => {
        document.getElementById(`like-count-${id}`).innerText = data.total_likes;
      })
      .catch(err => console.error(err));
  });

  // ── Star rating widget (streaming + streaming_movie) ───────────────────────
  (function () {
    const wrap = document.querySelector('.star-rating');
    if (!wrap) return;
    const stars = wrap.querySelectorAll('.star');
    const label = document.getElementById('your-rating-label');
    const avgEl = document.getElementById('avg-rating');

    stars.forEach(star => {
      star.addEventListener('mouseenter', () => {
        const val = +star.dataset.val;
        stars.forEach(s => s.classList.toggle('hover', +s.dataset.val <= val));
      });
      star.addEventListener('mouseleave', () => {
        stars.forEach(s => s.classList.remove('hover'));
      });
      star.addEventListener('click', () => {
        const val = +star.dataset.val;
        fetch(wrap.dataset.url, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCSRF(), 'Content-Type': 'application/x-www-form-urlencoded' },
          body: 'score=' + val,
        })
          .then(r => r.json())
          .then(data => {
            stars.forEach(s => s.classList.toggle('active', +s.dataset.val <= data.score));
            if (label) label.innerHTML = 'YOUR RATING: <b>' + data.score + '/10</b>';
            if (avgEl) avgEl.textContent = data.avg;
          })
          .catch(err => console.error(err));
      });
    });
  })();

  // ── Follow button (streaming) ───────────────────────────────────────────────
  (function () {
    const btn = document.querySelector('.follow-btn');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      fetch(btn.dataset.url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRF() },
      })
        .then(r => r.json())
        .then(data => {
          const icon    = btn.querySelector('i');
          const label   = document.getElementById('follow-label');
          const counter = document.getElementById('follower-count');
          if (data.following) {
            icon.className = 'fa fa-heart';
            label.textContent = 'Following';
          } else {
            icon.className = 'fa fa-heart-o';
            label.textContent = 'Follow';
          }
          if (counter) counter.textContent = data.follower_count;
        })
        .catch(err => console.error(err));
    });
  })();

  // ── Video resume position + periodic progress save ─────────────────────────
  (function () {
    const player = document.getElementById('main-player');
    if (!player || !player.dataset.saveUrl) return;

    const resumeAt   = parseFloat(player.dataset.resumeSeconds || '0');
    const contentId  = player.dataset.contentId;
    const idField    = player.dataset.idField || 'episode_id'; // 'episode_id' or 'movie_id'
    const saveUrl    = player.dataset.saveUrl;

    if (resumeAt > 0) {
      player.addEventListener('loadedmetadata', function () {
        if (resumeAt < player.duration - 10) {
          player.currentTime = resumeAt;
        }
      }, { once: true });
    }

    let saveTimer = null;
    function saveProgress(seconds) {
      const secs = seconds !== undefined ? seconds : Math.floor(player.currentTime);
      if (seconds === undefined && secs < 1) return;
      fetch(saveUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCSRF(),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: idField + '=' + contentId + '&progress_seconds=' + secs,
      }).catch(() => {});
    }

    player.addEventListener('play', function () {
      if (!saveTimer) saveTimer = setInterval(function () { saveProgress(); }, 10000);
    });
    player.addEventListener('pause', function () {
      clearInterval(saveTimer);
      saveTimer = null;
      saveProgress();
    });
    player.addEventListener('ended', function () {
      clearInterval(saveTimer);
      saveTimer = null;
      saveProgress(0); // reset so "resume" doesn't re-trigger next visit
    });
  })();

  // ── Autoplay-next-episode overlay (streaming) ───────────────────────────────
  (function () {
    const player    = document.getElementById('main-player');
    const overlay   = document.getElementById('autoplay-overlay');
    const countEl   = document.getElementById('autoplay-countdown');
    const cancelBtn = document.getElementById('autoplay-cancel');
    const nowLink   = document.getElementById('autoplay-now');
    if (!player || !overlay) return;

    let timer = null;

    player.addEventListener('ended', function () {
      overlay.classList.add('show');
      let secs = 10;
      countEl.textContent = secs;
      timer = setInterval(function () {
        secs -= 1;
        countEl.textContent = secs;
        if (secs <= 0) {
          clearInterval(timer);
          window.location.href = nowLink.href;
        }
      }, 1000);
    });

    cancelBtn?.addEventListener('click', function () {
      clearInterval(timer);
      overlay.classList.remove('show');
    });
  })();
});

// ── Header live search ────────────────────────────────────────────────────────
(function () {
  const searchInput   = document.getElementById('searchInput');
  const searchResults = document.getElementById('searchResults');
  if (!searchInput) return;

  searchInput.addEventListener('keyup', function (e) {
    const q = this.value.trim();
    if (e.key === 'Enter' && q.length > 0) {
      window.location.href = '/search/?q=' + encodeURIComponent(q);
      return;
    }
    if (!q) { searchResults.innerHTML = ''; searchResults.style.display = 'none'; return; }
    fetch('/live-search/?q=' + encodeURIComponent(q))
      .then(r => r.json())
      .then(data => {
        let html = data.results.map(item =>
          '<div class="search-item" onclick="goToItem(' + item.id + ',\'' + item.type + '\')">' +
            item.title + ' <small>(' + item.type + ')</small></div>'
        ).join('');
        if (data.results.length > 0) {
          html += '<div class="search-item search-item-all" onclick="window.location.href=\'/search/?q=' +
                  encodeURIComponent(q) + '\'">' +
                  '<i class="fas fa-search me-2"></i>See all results for "' + q + '"</div>';
        }
        searchResults.innerHTML = html;
        searchResults.style.display = html ? 'block' : 'none';
      });
  });

  document.addEventListener('click', function (e) {
    if (!e.target.closest('.header-search-box')) searchResults.style.display = 'none';
  });
})();

function goToItem(id, type) {
  window.location.href = type === 'movie'
    ? '/streaming_movie/' + id + '/'
    : '/streaming/'       + id + '/';
}

// ── Preloader progress bar ────────────────────────────────────────────────────
(function () {
  const preloader = document.getElementById('preloader');
  const bar       = document.getElementById('preloader-bar');
  if (!preloader || !bar) return;
  let progress = 0;
  const interval = setInterval(function () {
    progress += Math.random() * 20;
    if (progress >= 100) {
      progress = 100;
      clearInterval(interval);
      bar.style.width = '100%';
      setTimeout(function () {
        preloader.classList.add('hide');
        preloader.addEventListener('transitionend', function () { preloader.remove(); }, { once: true });
      }, 200);
    }
    bar.style.width = progress + '%';
  }, 80);
  setTimeout(function () { clearInterval(interval); preloader.classList.add('hide'); }, 1200);
})();

// ── Banner slider (home / movies hero) + coming-soon countdown ───────────────
window.addEventListener('load', function () {
  if (typeof jQuery === 'undefined') return;

  jQuery('.banner-slider').on('init', function () {
    jQuery('.banner-slider').css('visibility', 'visible');
  }).slick({
    autoplay      : true,
    autoplaySpeed : 4500,
    arrows        : true,
    dots          : false,
    fade          : true,
    speed         : 800,
    cssEase       : 'cubic-bezier(0.22,1,0.36,1)',
    infinite      : true,
    lazyLoad      : 'ondemand',
  });

  const block = document.getElementById('coming-out-block');
  if (!block) return;
  const releaseDate = block.dataset.release;
  const streamUrl   = block.dataset.streamUrl;
  jQuery('.countdown').countdown(releaseDate, function (event) {
    if (event.offset.totalSeconds <= 0) {
      jQuery('#coming-label').hide();
      jQuery('#countdown-timer').hide();
      jQuery('#play-now-btn').attr('href', streamUrl).show();
    } else {
      jQuery(this).html(
        '<li>' + event.offset.totalDays + '<small>d</small></li>' +
        '<li>' + event.offset.hours     + '<small>h</small></li>' +
        '<li>' + event.offset.minutes   + '<small>m</small></li>' +
        '<li>' + event.offset.seconds   + '<small>s</small></li>'
      );
    }
  });
});