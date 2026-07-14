// Watch party sync: WebSocket connection, host state push, invite-link copy.
(function () {
  const video = document.getElementById('party-player');
  if (!video) return;

  const isHost = video.dataset.isHost === 'true';
  const pushUrl = video.dataset.pushUrl;   // kept as HTTP fallback for end-party
  const csrf = video.dataset.csrftoken;
  const DRIFT_THRESHOLD = 5;    // seek if >5 s out of sync
  const roomCode = video.dataset.roomCode || window.location.pathname.split('/').filter(Boolean).pop();

  // ── WebSocket connection ──────────────────────────────────────────────────
  const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${wsScheme}://${window.location.host}/ws/watch-party/${roomCode}/`;
  let ws = null;
  let wsReady = false;

  function connectWS() {
    ws = new WebSocket(wsUrl);
    ws.onopen = function () { wsReady = true; };
    ws.onclose = function () {
      wsReady = false;
      // Fall back to polling every 3 s if WS closes unexpectedly
      setTimeout(connectWS, 3000);
    };
    ws.onerror = function () { wsReady = false; };
    ws.onmessage = function (evt) {
      let data;
      try { data = JSON.parse(evt.data); } catch (e) { return; }
      if (data.type !== 'state') return;
      const state = data;
      // Update member list
      const membersList = document.getElementById('party-members');
      if (membersList && state.members) {
        membersList.innerHTML = state.members
          .map(m => `<li class="list-group-item bg-dark text-light">${m}</li>`)
          .join('');
      }
      if (!isHost) {
        const drift = Math.abs(video.currentTime - state.position);
        if (drift > DRIFT_THRESHOLD) video.currentTime = state.position;
        if (state.is_playing && video.paused) video.play().catch(() => {});
        if (!state.is_playing && !video.paused) video.pause();
      }
    };
  }
  connectWS();

  // ── Host: push state on play/pause/seek ──────────────────────────────────
  function pushState() {
    if (!isHost) return;
    const msg = JSON.stringify({
      type: 'sync',
      position: video.currentTime,
      is_playing: !video.paused,
    });
    if (wsReady) {
      ws.send(msg);
    } else {
      // HTTP fallback while WS reconnects
      const fd = new FormData();
      fd.append('position', video.currentTime);
      fd.append('is_playing', video.paused ? 'false' : 'true');
      fetch(pushUrl, { method: 'POST', headers: { 'X-CSRFToken': csrf }, body: fd }).catch(() => {});
    }
  }
  if (isHost) {
    video.addEventListener('play', pushState);
    video.addEventListener('pause', pushState);
    video.addEventListener('seeked', pushState);
  }

  // ── Copy invite link ─────────────────────────────────────────────────────
  const copyBtn = document.getElementById('copy-room-code');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const url = window.location.origin + '/watch-party/' + copyBtn.dataset.code + '/';
      navigator.clipboard.writeText(url).then(() => {
        copyBtn.textContent = '✅ Copied!';
        setTimeout(() => { copyBtn.textContent = '📋 Copy Invite Link'; }, 2000);
      });
    });
  }
})();
