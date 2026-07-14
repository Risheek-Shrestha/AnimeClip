// Anime detail page: follow toggle, star rating, trailer modal cleanup.
(function () {
  // ── Follow toggle ────────────────────────────────────────────────────────
  const followBtn = document.getElementById('follow-btn');
  if (followBtn) {
    followBtn.addEventListener('click', () => {
      const animeId = followBtn.dataset.animeId;
      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
      fetch(`/anime/${animeId}/follow/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
      })
      .then(r => r.json())
      .then(data => {
        const isFollowing = data.following;
        followBtn.innerHTML = isFollowing
          ? '<i class="fa fa-heart"></i> Following'
          : '<i class="fa fa-heart-o"></i> Follow';
        followBtn.dataset.following = isFollowing;
        const counter = document.getElementById('follower-count');
        if (counter) counter.textContent = data.follower_count;
      });
    });
  }

  // ── Rating ───────────────────────────────────────────────────────────────
  const ratingStars = document.getElementById('rating-stars');
  const animeId = ratingStars ? ratingStars.dataset.animeId : null;
  document.querySelectorAll('.rate-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (!animeId) return;
      const score = btn.dataset.score;
      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
      fetch(`/anime/${animeId}/rate/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `score=${score}`,
      })
      .then(r => r.json())
      .then(data => {
        document.querySelectorAll('.rate-btn').forEach((b, i) => {
          b.className = `btn btn-sm rate-btn ${i < data.score ? 'btn-warning' : 'btn-outline-secondary'}`;
        });
        const fb = document.getElementById('rating-feedback');
        if (fb) fb.textContent = `Your rating: ${data.score}/10  ·  Community avg: ${data.avg}/10`;
      });
    });
  });

  // ── Stop trailer when modal closes ─────────────────────────────────────
  // #trailerModal only renders server-side when the anime has a trailer_url,
  // so checking for its presence here does the same job as the old
  // {% if anime.trailer_url %} template guard.
  const trailerModal = document.getElementById('trailerModal');
  if (trailerModal) {
    trailerModal.addEventListener('hide.bs.modal', () => {
      const iframe = document.getElementById('trailer-iframe');
      if (iframe) { const src = iframe.src; iframe.src = ''; iframe.src = src; }
    });
  }
})();
