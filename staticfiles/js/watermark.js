/**
 * AnimeClip Canvas Watermark
 * Renders a tiled, semi-transparent user label over the video element.
 * Repeats every TILE_W x TILE_H pixels at a slight angle.
 *
 * Usage:
 *   AnimeClipWatermark.init(label, canvasEl);
 *   Call again on fullscreen change with updated canvas dimensions.
 */
const AnimeClipWatermark = (() => {
  const TILE_W = 280;
  const TILE_H = 120;
  const ANGLE = -20 * (Math.PI / 180);
  const FONT = "13px monospace";
  const FILL = "rgba(255,255,255,0.12)";

  function draw(label, canvas) {
    const video = canvas.closest(".player-wrapper")?.querySelector("video");
    const w = video ? video.offsetWidth : canvas.parentElement.offsetWidth;
    const h = video ? video.offsetHeight : canvas.parentElement.offsetHeight;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, w, h);
    ctx.save();
    ctx.font = FONT;
    ctx.fillStyle = FILL;
    ctx.translate(w / 2, h / 2);
    ctx.rotate(ANGLE);
    ctx.translate(-w, -h);
    for (let y = -h; y < h * 2; y += TILE_H) {
      for (let x = -w; x < w * 2; x += TILE_W) {
        ctx.fillText(label, x, y);
      }
    }
    ctx.restore();
  }

  function init(label, canvas) {
    if (!label || !canvas) return;
    draw(label, canvas);
    window.addEventListener("resize", () => draw(label, canvas));
    document.addEventListener("fullscreenchange", () => draw(label, canvas));
  }

  return { init };
})();
