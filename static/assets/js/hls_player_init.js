// HLS.js player initialization. Only runs if #main-player has a
// data-hls-src attribute (i.e. the page passed an hls_url). Shared by
// streaming.html and streaming_movie.html.
(function () {
    var video = document.getElementById('main-player');
    if (!video) return;
    var hlsSrc = video.dataset.hlsSrc;
    if (!hlsSrc) return;

    if (video.canPlayType('application/vnd.apple.mpegurl')) {
        // Safari / iOS already speak HLS natively — no library needed.
        video.src = hlsSrc;
    } else if (window.Hls && window.Hls.isSupported()) {
        var hls = new Hls();
        hls.loadSource(hlsSrc);
        hls.attachMedia(video);
        hls.on(Hls.Events.ERROR, function (event, data) {
            if (data && data.fatal) {
                // Adaptive stream failed (e.g. still transcoding on
                // Cloudinary's side) — fall back to the plain MP4
                // <source> already present in the markup.
                hls.destroy();
                video.load();
            }
        });
    }
    // Any other browser: the plain MP4 <source> in the markup just plays.
})();
