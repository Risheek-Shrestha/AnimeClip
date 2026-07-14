// Download panel click handler — self-contained include used by streaming.html and streaming_movie.html.
(function () {
  document.querySelectorAll('.download-panel__btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var dlUrl    = btn.dataset.dlUrl;
      var height   = btn.dataset.height;
      var sourceId = btn.dataset.sourceId;
      var csrf     = btn.dataset.csrf;
      var status   = btn.closest('.download-panel').querySelector('.download-panel__status');

      btn.disabled = true;
      status.hidden = false;
      status.textContent = 'Preparing download…';

      fetch(dlUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf,
        },
        body: JSON.stringify({ height: parseInt(height, 10), source_id: parseInt(sourceId, 10) }),
      })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.url) {
          status.textContent = 'Starting download…';
          // Open in new tab so the user stays on the streaming page
          window.open(data.url, '_blank', 'noopener');
          setTimeout(function () {
            status.hidden = true;
            btn.disabled = false;
          }, 2000);
        } else {
          status.textContent = 'Error: ' + (data.error || 'Unknown error');
          btn.disabled = false;
        }
      })
      .catch(function () {
        status.textContent = 'Network error — please try again.';
        btn.disabled = false;
      });
    });
  });
})();
