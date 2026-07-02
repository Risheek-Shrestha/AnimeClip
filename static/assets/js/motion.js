/* ═══════════════════════════════════════════════════════════
   ANIMELOOP — 3D MOTION ENGINE  v5.0
   Full physics-based motion system with WebGL-inspired depth
═══════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── CONFIG ─────────────────────────────────────────── */
  const CFG = {
    tilt:       { max: 14, scale: 1.06, speed: 400 },
    magnetic:   { strength: 0.35, radius: 120 },
    particle:   { count: 55, speed: 0.4 },
    ripple:     { duration: 800 },
    reveal:     { threshold: 0.08, stagger: 90 },
    parallax:   { depth: 18 },
    wipe:       { duration: 680 }
  };

  /* ── 3D CANVAS BACKGROUND ───────────────────────────── */
  function initCanvasBg() {
    const canvas = document.getElementById('space-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H, stars = [], nebulas = [];
    let mouseX = 0.5, mouseY = 0.5;

    function resize() {
      W = canvas.width  = window.innerWidth;
      H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < 200; i++) {
      stars.push({
        x: Math.random(), y: Math.random(),
        z: Math.random() * 3 + 0.2,
        size: Math.random() * 1.8 + 0.3,
        pulse: Math.random() * Math.PI * 2,
        speed: 0.001 + Math.random() * 0.003,
        color: Math.random() > 0.85
          ? `hsl(${280 + Math.random() * 60},80%,75%)`
          : `hsl(${40 + Math.random() * 20},90%,80%)`
      });
    }

    for (let i = 0; i < 4; i++) {
      nebulas.push({
        x: Math.random(), y: Math.random(),
        rx: 0.15 + Math.random() * 0.25,
        ry: 0.12 + Math.random() * 0.18,
        hue: i % 2 === 0 ? 270 : 45,
        alpha: 0.025 + Math.random() * 0.03
      });
    }

    let raf, t = 0;
    function draw() {
      raf = requestAnimationFrame(draw);
      t += 0.008;

      ctx.clearRect(0, 0, W, H);

      /* Deep space gradient */
      const bg = ctx.createRadialGradient(W * 0.5, H * 0.4, 0, W * 0.5, H * 0.5, W * 0.8);
      bg.addColorStop(0, 'rgba(18,8,35,1)');
      bg.addColorStop(0.5, 'rgba(8,5,20,1)');
      bg.addColorStop(1, 'rgba(4,3,12,1)');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);

      /* Nebula clouds */
      nebulas.forEach(n => {
        const ox = (mouseX - 0.5) * 30 * n.rx;
        const oy = (mouseY - 0.5) * 20 * n.ry;
        const grd = ctx.createRadialGradient(
          (n.x + ox / W) * W, (n.y + oy / H) * H, 0,
          (n.x + ox / W) * W, (n.y + oy / H) * H,
          Math.max(n.rx * W, n.ry * H)
        );
        grd.addColorStop(0, `hsla(${n.hue},70%,45%,${n.alpha * 2})`);
        grd.addColorStop(0.5, `hsla(${n.hue},60%,30%,${n.alpha})`);
        grd.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = grd;
        ctx.fillRect(0, 0, W, H);
      });

      /* Stars with parallax */
      stars.forEach(s => {
        s.pulse += s.speed;
        const px = mouseX - 0.5;
        const py = mouseY - 0.5;
        const ox = px * s.z * CFG.parallax.depth;
        const oy = py * s.z * CFG.parallax.depth;
        const sx = (s.x * W + ox + W) % W;
        const sy = (s.y * H + oy + H) % H;
        const twinkle = 0.6 + 0.4 * Math.sin(s.pulse);
        const r = s.size * twinkle;

        ctx.beginPath();
        ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.fillStyle = s.color;
        ctx.globalAlpha = twinkle * 0.9;
        ctx.fill();

        if (r > 1.2) {
          const glow = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 5);
          glow.addColorStop(0, s.color.replace(')', ',0.3)').replace('hsl', 'hsla'));
          glow.addColorStop(1, 'rgba(0,0,0,0)');
          ctx.fillStyle = glow;
          ctx.globalAlpha = 0.5 * twinkle;
          ctx.beginPath();
          ctx.arc(sx, sy, r * 5, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = 1;
      });

      /* Shooting star */
      if (Math.random() < 0.002) {
        const sx = Math.random() * W;
        const sy = Math.random() * H * 0.4;
        const grad = ctx.createLinearGradient(sx, sy, sx + 120, sy + 40);
        grad.addColorStop(0, 'rgba(255,230,100,0.9)');
        grad.addColorStop(1, 'rgba(255,230,100,0)');
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(sx + 120, sy + 40);
        ctx.stroke();
      }
    }
    draw();

    document.addEventListener('mousemove', e => {
      mouseX += (e.clientX / window.innerWidth  - mouseX) * 0.05;
      mouseY += (e.clientY / window.innerHeight - mouseY) * 0.05;
    });
  }

  /* ── CURSOR SYSTEM ──────────────────────────────────── */
  function initCursor() {
    const ring  = document.getElementById('cursor-ring');
    const dot   = document.getElementById('cursor-dot');
    const glow  = document.getElementById('cursor-glow');
    if (!ring) return;

    let mx = 0, my = 0, rx = 0, ry = 0;
    let hovering = false;

    document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });

    document.querySelectorAll('a,button,.anime-blog,.play-butn').forEach(el => {
      if (el.closest('.navbar-brand')) return;
      el.addEventListener('mouseenter', () => { hovering = true; });
      el.addEventListener('mouseleave', () => { hovering = false; });
    });

    function animateCursor() {
      rx += (mx - rx) * 0.12;
      ry += (my - ry) * 0.12;
      const scale = hovering ? 2.2 : 1;
      ring.style.transform  = `translate(${rx - 20}px, ${ry - 20}px) scale(${scale})`;
      dot.style.transform   = `translate(${mx - 3}px, ${my - 3}px)`;
      if (glow) glow.style.cssText = `left:${mx}px;top:${my}px;`;
      requestAnimationFrame(animateCursor);
    }
    animateCursor();
  }

  /* ── 3D CARD TILT ───────────────────────────────────── */
  function initCardTilt() {
    document.querySelectorAll('.anime-blog').forEach(card => {
      const block = card.querySelector('.img-block');
      const shine = card.querySelector('.card-shine');
      const edge  = card.querySelector('.card-glow-edge');
      if (!block) return;

      let cx = 0, cy = 0, targeted = false;
      let animId;

      card.addEventListener('mouseenter', () => { targeted = true; });
      card.addEventListener('mouseleave', () => {
        targeted = false;
        const ease = () => {
          cx *= 0.85; cy *= 0.85;
          block.style.transform = `perspective(800px) rotateX(${cy}deg) rotateY(${cx}deg) translateZ(${Math.abs(cx)+Math.abs(cy) > 0.5 ? 20 : 0}px)`;
          if (Math.abs(cx) > 0.05 || Math.abs(cy) > 0.05) requestAnimationFrame(ease);
          else block.style.transform = '';
        };
        requestAnimationFrame(ease);
        if (shine) shine.style.opacity = '0';
        if (edge)  edge.style.opacity  = '0';
      });

      card.addEventListener('mousemove', e => {
        const r  = block.getBoundingClientRect();
        const x  = (e.clientX - r.left) / r.width;
        const y  = (e.clientY - r.top)  / r.height;
        cx = (x - 0.5) * CFG.tilt.max * 2;
        cy = (y - 0.5) * CFG.tilt.max * -1;

        block.style.transform = `perspective(800px) rotateX(${cy}deg) rotateY(${cx}deg) translateZ(20px) scale(${CFG.tilt.scale})`;
        block.style.transition = 'none';

        if (shine) {
          shine.style.setProperty('--sx', x * 100 + '%');
          shine.style.setProperty('--sy', y * 100 + '%');
          shine.style.opacity = '1';
        }
        if (edge) edge.style.opacity = '1';
      });
    });
  }

  /* ── MAGNETIC BUTTONS ───────────────────────────────── */
  function initMagnetic() {
    document.querySelectorAll('.play-butn,.anime-btn,.anime-btn2,.comment-btn').forEach(btn => {
      let ox = 0, oy = 0;

      btn.addEventListener('mousemove', e => {
        const r  = btn.getBoundingClientRect();
        const dx = (e.clientX - r.left - r.width / 2);
        const dy = (e.clientY - r.top  - r.height / 2);
        const dist = Math.sqrt(dx * dx + dy * dy);
        const pull = Math.max(0, 1 - dist / CFG.magnetic.radius);
        ox = dx * CFG.magnetic.strength * pull;
        oy = dy * CFG.magnetic.strength * pull;
        btn.style.transform = `translate(${ox}px,${oy}px) scale(${1 + pull * 0.08})`;
      });

      btn.addEventListener('mouseleave', () => {
        btn.style.transition = 'transform 0.5s cubic-bezier(0.23,1,0.32,1)';
        btn.style.transform  = '';
        setTimeout(() => { btn.style.transition = ''; }, 500);
      });
    });
  }

  /* ── RIPPLE ─────────────────────────────────────────── */
  function initRipple() {
    const sel = '.play-butn,.anime-btn,.anime-btn2,.comment-btn,.ripple-host,.watch-later-btn,.add-to-playlist-btn';
    document.querySelectorAll(sel).forEach(el => {
      if (el.dataset.ripple) return;
      el.dataset.ripple = '1';
      if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
      el.style.overflow = 'hidden';
      el.addEventListener('click', e => {
        const r = el.getBoundingClientRect();
        const w = document.createElement('div');
        w.className = 'ripple-circle';
        w.style.left = (e.clientX - r.left) + 'px';
        w.style.top  = (e.clientY - r.top)  + 'px';
        el.appendChild(w);
        setTimeout(() => w.remove(), CFG.ripple.duration);
      });
    });
  }

  /* ── SCROLL REVEAL ──────────────────────────────────── */
  function initScrollReveal() {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        obs.unobserve(entry.target);
      });
    }, { threshold: CFG.reveal.threshold });
    document.querySelectorAll('[data-reveal]').forEach(el => obs.observe(el));
  }

  /* ── CARD STAGGER ───────────────────────────────────── */
  function initCardStagger() {
    document.querySelectorAll('.recent .row, .popular .row').forEach(row => {
      const cols = row.querySelectorAll('.col-xl-3,.col-lg-4,.col-sm-6');
      if (!cols.length) return;
      const rowObs = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          cols.forEach((col, i) => {
            setTimeout(() => col.classList.add('is-visible'), i * CFG.reveal.stagger);
          });
          rowObs.disconnect();
        });
      }, { threshold: 0.06 });
      rowObs.observe(row);
    });
  }

  /* ── BANNER PARALLAX ────────────────────────────────── */
  function initBannerParallax() {
    document.querySelectorAll('.banner-block').forEach(block => {
      const img   = block.querySelector('.col-lg-7 img');
      const layer = block.querySelector('.banner-depth-layer');
      let tx = 0, ty = 0, itx = 0, ity = 0;
      let ticking = false;

      block.addEventListener('mousemove', e => {
        if (!ticking) {
          requestAnimationFrame(() => {
            const r  = block.getBoundingClientRect();
            const cx = (e.clientX - r.left - r.width  / 2) / r.width;
            const cy = (e.clientY - r.top  - r.height / 2) / r.height;
            tx  = cx * CFG.parallax.depth;
            ty  = cy * CFG.parallax.depth * 0.6;
            itx = cx * -CFG.parallax.depth * 1.4;
            ity = cy * -CFG.parallax.depth;
            if (img)   img.style.transform   = `scale(1.08) translate(${tx}px,${ty}px)`;
            if (layer) layer.style.transform = `translate(${itx}px,${ity}px)`;
            ticking = false;
          });
          ticking = true;
        }
      });
      block.addEventListener('mouseleave', () => {
        if (img)   img.style.transform   = '';
        if (layer) layer.style.transform = '';
      });
    });
  }

  /* ── BANNER PARTICLES ───────────────────────────────── */
  function initBannerParticles() {
    const container = document.getElementById('banner-particles');
    if (!container) return;
    for (let i = 0; i < CFG.particle.count; i++) {
      const p   = document.createElement('div');
      p.className = 'b-particle';
      const hue = Math.random() > 0.5 ? `40,90%,65%` : `280,80%,70%`;
      const tx  = (Math.random() - .5) * 70;
      const ty  = -30 - Math.random() * 80;
      const sz  = 1.5 + Math.random() * 2;
      p.style.cssText = [
        `left:${Math.random()*100}%`,
        `top:${Math.random()*100}%`,
        `width:${sz}px`,`height:${sz}px`,
        `background:hsl(${hue})`,
        `--tx:${tx}px`,`--ty:${ty}px`,
        `animation:b-float ${4+Math.random()*6}s ${Math.random()*4}s ease-in-out infinite`
      ].join(';');
      container.appendChild(p);
    }
  }

  /* ── SCHEDULE STAGGER ───────────────────────────────── */
  function initScheduleStagger() {
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
      tab.addEventListener('shown.bs.tab', e => {
        const paneId = e.target.getAttribute('href');
        const pane   = document.querySelector(paneId);
        if (!pane) return;
        pane.querySelectorAll('.row-wrap').forEach((row, i) => {
          row.style.cssText = 'opacity:0;transform:translateX(-24px)';
          setTimeout(() => {
            row.style.cssText = 'transition:opacity .45s ease,transform .45s ease;opacity:1;transform:none';
          }, i * 65);
        });
      });
    });
  }

  /* ── COUNTERS ───────────────────────────────────────── */
  function initCounters() {
    document.querySelectorAll('[data-count]').forEach(el => {
      const target = +el.dataset.count;
      const io = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          io.disconnect();
          const start = performance.now();
          (function tick(now) {
            const p    = Math.min((now - start) / 1600, 1);
            const ease = 1 - Math.pow(1 - p, 4);
            el.textContent = Math.round(ease * target).toLocaleString();
            if (p < 1) requestAnimationFrame(tick);
          })(start);
        });
      }, { threshold: 0.4 });
      io.observe(el);
    });
  }

  /* ── TOAST ──────────────────────────────────────────── */
  let toastContainer;
  function initToastContainer() {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    document.body.appendChild(toastContainer);
  }

  window.showToast = function (msg, variant) {
    if (!toastContainer) initToastContainer();
    const t  = document.createElement('div');
    t.className = 'toast-item';
    const col = variant === 'purple'
      ? 'var(--c-accent)' : 'var(--c-gold)';
    t.innerHTML = `<span class="toast-dot" style="background:${col}"></span>${msg}`;
    toastContainer.appendChild(t);
    setTimeout(() => {
      t.classList.add('leaving');
      setTimeout(() => t.remove(), 350);
    }, 3000);
  };

  /* ── PAGE WIPE ──────────────────────────────────────── */
  function initPageWipe() {
    document.addEventListener('click', e => {
      const link = e.target.closest('a[href]');
      if (!link) return;
      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript') ||
          e.ctrlKey || e.metaKey || link.target === '_blank') return;
      if (link.hasAttribute('data-bs-toggle') || link.hasAttribute('data-bs-dismiss')) return;
      e.preventDefault();
      const wipe = document.createElement('div');
      wipe.id = 'page-wipe';
      document.body.appendChild(wipe);
      setTimeout(() => { window.location.href = href; }, CFG.wipe.duration);
    });
  }

  /* ── WATCH LATER / PLAYLIST TOASTS ─────────────────── */
  function initActionToasts() {
    document.addEventListener('click', e => {
      if (e.target.closest('.watch-later-btn'))    showToast('Added to Watch Later');
      if (e.target.closest('.add-to-playlist-btn')) showToast('Choose a playlist', 'purple');
    });
  }

  /* ── SECTION DEPTH TILT (scroll parallax) ──────────── */
  function initSectionParallax() {
    const sections = document.querySelectorAll('.sec-mar');
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) e.target.classList.add('in-view');
      });
    }, { threshold: 0.05 });
    sections.forEach(s => io.observe(s));

    let lastY = 0;
    window.addEventListener('scroll', () => {
      const scrollY = window.scrollY;
      const delta = scrollY - lastY;
      lastY = scrollY;
      sections.forEach(s => {
        if (!s.classList.contains('in-view')) return;
        const rect  = s.getBoundingClientRect();
        const rel   = (rect.top + rect.height / 2 - window.innerHeight / 2) / window.innerHeight;
        s.style.transform = `translateY(${rel * 8}px)`;
      });
    }, { passive: true });
  }

  /* ── ANIME BOX 3D HOVER ─────────────────────────────── */
  function initAnimeBoxHover() {
    document.querySelectorAll('.anime-box').forEach(box => {
      box.addEventListener('mousemove', e => {
        const r  = box.getBoundingClientRect();
        const x  = (e.clientX - r.left) / r.width;
        const y  = (e.clientY - r.top)  / r.height;
        const rx = (y - 0.5) * -6;
        const ry = (x - 0.5) * 8;
        box.style.transform = `perspective(600px) rotateX(${rx}deg) rotateY(${ry}deg) translateX(6px) scale(1.02)`;
        box.style.transition = 'none';
      });
      box.addEventListener('mouseleave', () => {
        box.style.transition = 'transform 0.4s cubic-bezier(0.23,1,0.32,1)';
        box.style.transform  = '';
      });
    });
  }

  /* ── PROGRESS BARS ──────────────────────────────────── */
  function initProgressBars() {
    document.querySelectorAll('.genre-bar-fill').forEach(bar => {
      const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (!e.isIntersecting) return;
          bar.classList.add('animate');
          io.disconnect();
        });
      }, { threshold: 0.3 });
      io.observe(bar);
    });
  }

  /* ── PRELOADER ──────────────────────────────────────── */
  function initPreloader() {
    const preloader = document.getElementById('preloader');
    if (!preloader) return;
    const bar = document.getElementById('preloader-bar');

    function hide() {
      if (bar) bar.style.width = '100%';
      // Small delay so the bar's final width is visible before the fade.
      setTimeout(() => {
        preloader.classList.add('hide');
        document.body.classList.remove('loading');
        preloader.addEventListener('transitionend', () => preloader.remove(), { once: true });
      }, 250);
    }

    if (document.readyState === 'complete') {
      hide();
    } else {
      window.addEventListener('load', hide);
      // Fallback in case some resource (e.g. a 404'd image) keeps the
      // load event from firing in a reasonable time.
      setTimeout(hide, 4000);
    }
  }

  /* ── INIT ───────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    initPreloader();
    initCanvasBg();
    initCursor();
    initCardTilt();
    initMagnetic();
    initRipple();
    initScrollReveal();
    initCardStagger();
    initBannerParallax();
    initBannerParticles();
    initScheduleStagger();
    initCounters();
    initToastContainer();
    initPageWipe();
    initActionToasts();
    initSectionParallax();
    initAnimeBoxHover();
    initProgressBars();
  });


})();