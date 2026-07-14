// Movie streaming page: delete comment, watch-party controls.

// ── Delete Comment ────────────────────────────────────────────────────────────
document.querySelectorAll('.delete-comment-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
        if (!confirm('Delete this comment?')) return;
        fetch(btn.dataset.url, {
            method: 'POST',
            headers: { 'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '' },
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.deleted) {
                var row = btn.closest('.row.mb-4');
                if (row) row.remove();
            }
        });
    });
});

// ── Watch Party + Share (movie) ───────────────────────────────────────────────
(function () {
  const startBtn = document.getElementById('start-watch-party');
  const joinBtn  = document.getElementById('join-watch-party');
  const shareBtn = document.getElementById('share-btn');
  const msg      = document.getElementById('party-created-msg');
  if (startBtn) {
    startBtn.addEventListener('click', () => {
      const fd = new FormData();
      fd.append('movie_id', startBtn.dataset.movieId);
      fetch('/watch-party/create/', { method: 'POST', body: fd,
        headers: { 'X-CSRFToken': startBtn.dataset.csrf } })
        .then(r => r.json())
        .then(data => {
          if (data.room_code) {
            const url = '/watch-party/' + data.room_code + '/';
            msg.innerHTML = '🎉 Party created! <a href="' + url + '" class="btn btn-primary btn-sm ms-2">Open Room ' + data.room_code + '</a>';
            msg.classList.remove('d-none');
          }
        });
    });
  }
  if (joinBtn) {
    joinBtn.addEventListener('click', () => {
      const code = document.getElementById('join-code-input').value.trim().toUpperCase();
      if (code) window.location.href = '/watch-party/' + code + '/';
    });
  }
  if (shareBtn) {
    shareBtn.addEventListener('click', () => {
      const url = shareBtn.dataset.url;
      if (navigator.share) navigator.share({ title: document.title, url });
      else navigator.clipboard.writeText(url).then(() => {
        shareBtn.textContent = '✅ Copied!';
        setTimeout(() => { shareBtn.textContent = '📤 Share'; }, 2000);
      });
    });
  }
})();
