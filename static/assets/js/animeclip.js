/**
 * animeclip.js — shared utilities for AnimeClip
 * Handles: CSRF token, Watch Later toggle, Playlist modal population.
 * Loaded globally via base.html — do NOT duplicate in individual templates.
 */

function getCSRF() {
  return document.cookie.split('; ').find(r => r.startsWith('csrftoken'))?.split('=')[1];
}

// ── Weekly schedule date slider ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  if (window.jQuery && jQuery.fn.slick) {
    const $slider = jQuery('.date-slider');
    if ($slider.length && !$slider.hasClass('slick-initialized')) {
      $slider.slick({
        slidesToShow: 7,
        slidesToScroll: 1,
        infinite: false,
        arrows: true,
        prevArrow: $slider.find('.slick-prev'),
        nextArrow: $slider.find('.slick-next'),
        responsive: [
          { breakpoint: 992, settings: { slidesToShow: 5 } },
          { breakpoint: 576, settings: { slidesToShow: 3 } },
        ],
      });
    }
  }
});

// ── Hero banner slider (featured anime/movies) ────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  if (window.jQuery && jQuery.fn.slick) {
    const $banner = jQuery('.banner-slider');
    // Only initialize when there's more than one slide — a single slide
    // should stay static and skip slick entirely.
    if ($banner.length && !$banner.hasClass('slick-initialized') && $banner.children('.banner-block').length > 1) {
      $banner.slick({
        slidesToShow: 1,
        slidesToScroll: 1,
        infinite: true,
        fade: true,
        speed: 700,
        autoplay: true,
        autoplaySpeed: 6000,
        arrows: true,
        dots: true,
        pauseOnHover: true,
        adaptiveHeight: false,
      });
    }
  }
});

// ── Hero banner slider (featured anime/movies) ────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  if (window.jQuery && jQuery.fn.slick) {
    const $banner = jQuery('.banner-slider');
    // Only initialize when there's more than one slide — a single slide
    // should stay static and skip slick entirely.
    if ($banner.length && !$banner.hasClass('slick-initialized') && $banner.children('.banner-block').length > 1) {
      $banner.slick({
        slidesToShow: 1,
        slidesToScroll: 1,
        infinite: true,
        fade: true,
        speed: 700,
        autoplay: true,
        autoplaySpeed: 6000,
        arrows: true,
        dots: true,
        pauseOnHover: true,
        adaptiveHeight: false,
      });
    }
  }
});

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
});
// Genre gallery scroll buttons
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.genre-scroll-prev, .genre-scroll-next').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var track = document.getElementById(btn.getAttribute('data-target'));
      if (!track) return;
      var amt = track.clientWidth * 0.75;
      track.scrollBy({ left: btn.classList.contains('genre-scroll-next') ? amt : -amt, behavior: 'smooth' });
    });
  });
});
