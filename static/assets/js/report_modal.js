// Report-an-issue modal submit handler.
// Shared by streaming.html (episode reports) and streaming_movie.html
// (movie reports) via _report_modal.html. The target URL is read from
// #reportModal's data-report-url attribute, set per-page by the template
// that includes the modal.
(function () {
  const form = document.getElementById('report-form');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const modal = document.getElementById('reportModal');
    const reportUrl = modal ? modal.dataset.reportUrl : '';
    if (!reportUrl) return;
    const fd = new FormData(form);
    fetch(reportUrl, { method: 'POST', body: fd,
      headers: { 'X-CSRFToken': fd.get('csrfmiddlewaretoken') }
    })
    .then(r => r.json())
    .then(data => {
      const fb = document.getElementById('report-feedback');
      fb.className = 'alert alert-success';
      fb.textContent = 'Report submitted. Thank you!';
      fb.classList.remove('d-none');
      setTimeout(() => {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) modalInstance.hide();
        fb.classList.add('d-none');
        form.reset();
      }, 2000);
    })
    .catch(() => {
      const fb = document.getElementById('report-feedback');
      fb.className = 'alert alert-danger';
      fb.textContent = 'Failed to submit report. Try again.';
      fb.classList.remove('d-none');
    });
  });
})();
