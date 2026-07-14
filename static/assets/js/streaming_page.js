// Episode streaming page: skip intro, scrub-preview thumbnail, delete
// comment, and watch-party controls.

// ── Skip Intro ───────────────────────────────────────────────────────────────
(function () {
    var video = document.getElementById('main-player');
    var btn   = document.getElementById('skip-intro-btn');
    if (!video || !btn) return;
    var introStart = parseInt(video.dataset.introStart || '0', 10);
    var introEnd   = parseInt(video.dataset.introEnd   || '0', 10);
    if (!introEnd) return;

    video.addEventListener('timeupdate', function () {
        var t = video.currentTime;
        btn.style.display = (t >= introStart && t < introEnd) ? 'block' : 'none';
    });
    btn.addEventListener('click', function () {
        video.currentTime = introEnd;
        btn.style.display = 'none';
    });
})();

// ── Scrub Preview Thumbnail ───────────────────────────────────────────────
(function () {
    var video = document.getElementById('main-player');
    var preview = document.getElementById('scrub-preview');
    var previewImg = document.getElementById('scrub-preview-img');
    var previewTime = document.getElementById('scrub-preview-time');
    if (!video || !preview || !previewImg) return;
    var thumbUrl = video.dataset.thumbnailUrl || '';
    if (!thumbUrl) return;

    function fmtTime(s) {
        s = Math.floor(s);
        var h = Math.floor(s / 3600);
        var m = Math.floor((s % 3600) / 60);
        var sec = s % 60;
        if (h > 0) return h + ':' + String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
        return m + ':' + String(sec).padStart(2,'0');
    }

    video.addEventListener('mousemove', function (e) {
        var rect = video.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var ratio = Math.max(0, Math.min(1, x / rect.width));
        var t = ratio * (video.duration || 0);
        if (!video.duration) return;
        previewImg.src = thumbUrl;
        previewTime.textContent = fmtTime(t);
        var previewW = 164;
        var left = Math.max(0, Math.min(x - previewW / 2, rect.width - previewW));
        preview.style.left = left + 'px';
        preview.style.display = 'block';
    });
    video.addEventListener('mouseleave', function () {
        preview.style.display = 'none';
    });
})();

// ── Delete Comment ────────────────────────────────────────────────────────────
document.querySelectorAll('.delete-comment-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
        if (!confirm('Delete this comment?')) return;
        var url = btn.dataset.url;
        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '',
            },
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

// ── Watch Party JS ───────────────────────────────────────────────────────────
(function () {
  const startBtn = document.getElementById('start-watch-party');
  const joinBtn = document.getElementById('join-watch-party');
  const shareBtn = document.getElementById('share-btn');
  const msg = document.getElementById('party-created-msg');

  if (startBtn) {
    startBtn.addEventListener('click', function () {
      const fd = new FormData();
      fd.append('episode_id', startBtn.dataset.episodeId);
      fd.append('csrfmiddlewaretoken', startBtn.dataset.csrf);
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
    joinBtn.addEventListener('click', function () {
      const code = document.getElementById('join-code-input').value.trim().toUpperCase();
      if (code) window.location.href = '/watch-party/' + code + '/';
    });
  }

  if (shareBtn) {
    shareBtn.addEventListener('click', function () {
      const url = shareBtn.dataset.url;
      if (navigator.share) {
        navigator.share({ title: document.title, url });
      } else {
        navigator.clipboard.writeText(url).then(() => {
          shareBtn.textContent = '✅ Link copied!';
          setTimeout(() => { shareBtn.textContent = '📤 Share'; }, 2000);
        });
      }
    });
  }
})();
