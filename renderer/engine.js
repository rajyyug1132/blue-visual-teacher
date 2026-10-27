// renderer/engine.js — timeline + frame drawing. Public API (PLAN 4.4, frozen):
//   window.initLesson(title, scenes, lang?) -> Promise   scenes = manifest scenes (start_sec, end_sec, narration, visual)
//   window.renderAtTime(t)                               sync, pure function of t: same t -> same pixels
//   window.totalDuration                                 seconds
//   window.ready                                         true once initLesson resolved (the exporter waits on it)
// No Date.now, no setInterval, no unseeded randomness in here.
(function () {
  "use strict";

  const T0 = window.Theme;
  const TAIL = 0.35;  // silent tail TTS appends to every scene: used for the transition
  let lesson = null;

  function canvas() { return document.getElementById("stage"); }

  function normalizeScenes(scenes) {
    let cursor = 0;
    return (scenes || []).map((s, i) => {
      const dur = Number(s.duration_sec) || Math.max(0.5, (Number(s.end_sec) || 0) - (Number(s.start_sec) || 0)) || 5;
      const start = s.start_sec != null ? Number(s.start_sec) : cursor;
      const end = s.end_sec != null ? Number(s.end_sec) : start + dur;
      cursor = end;
      const visual = s.visual || { type: "bullets", params: { labels: [], steps: [] } };
      return { id: s.id != null ? s.id : i + 1, start, end, dur: Math.max(0.1, end - start),
               narration: String(s.narration || ""), type: visual.type,
               params: Object.assign({ labels: [], steps: [] }, visual.params || {}) };
    });
  }

  async function loadFonts(family) {
    if (!document.fonts) return;
    const first = family.split(",")[0].trim();
    try {
      await Promise.all([document.fonts.load(`600 32px ${first}`), document.fonts.load(`800 32px ${first}`),
                         document.fonts.load('600 32px "Noto Sans"')]);
      await document.fonts.ready;
    } catch (e) { /* fall back to the system font in the stack; never block the render */ }
  }

  window.initLesson = async function (title, scenes, lang) {
    window.ready = false;
    const all = (title || "") + " " + (scenes || []).map((s) => s.narration || "").join(" ");
    const code = lang || T0.detectLang(all);
    const family = T0.families[code] || T0.families.en;
    await loadFonts(family);
    const list = normalizeScenes(scenes);
    lesson = { title: String(title || ""), lang: code, family, scenes: list,
               total: list.length ? list[list.length - 1].end : 0 };
    window.totalDuration = lesson.total;
    window.renderAtTime(0);
    window.ready = true;
    return lesson.total;
  };

  function sceneAt(t) {
    const list = lesson.scenes;
    for (let i = 0; i < list.length; i++) if (t < list[i].end) return i;
    return list.length - 1;
  }

  function drawBackground(ctx, scene) {
    const P = T0.palette;
    ctx.fillStyle = P.bg;
    ctx.fillRect(0, 0, T0.W, T0.H);
    // Seeded decorative dots: same scene -> same dots, every frame.
    const r = T0.rng(1000 + (scene ? scene.id : 0));
    ctx.save();
    ctx.fillStyle = P.line;
    for (let k = 0; k < 24; k++) {
      ctx.globalAlpha = 0.25 + r() * 0.35;
      ctx.beginPath(); ctx.arc(r() * T0.W, 80 + r() * 500, 1.5 + r() * 2.5, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }

  function drawHeader(ctx) {
    const P = T0.palette;
    ctx.fillStyle = P.panel;
    ctx.fillRect(0, 0, T0.W, T0.safe.headerH);
    ctx.fillStyle = P.accent;
    ctx.fillRect(0, T0.safe.headerH - 3, T0.W, 3);
    T0.drawText(ctx, lesson.title, { x: 32, y: 12, w: T0.W - 64, h: 48 },
      { family: lesson.family, maxPx: 28, minPx: 18, maxLines: 1, valign: "middle", weight: 700, color: P.muted });
  }

  // Word-by-word highlight: word k becomes active at start + 0.15 + frac_k * (dur - 0.5), weighted by length.
  function drawCaption(ctx, scene, lt) {
    const P = T0.palette, box = { x: 48, y: T0.safe.captionY, w: T0.W - 96, h: T0.safe.captionH - 8 };
    T0.panel(ctx, box.x - 16, box.y - 6, box.w + 32, box.h + 8, { fill: "rgba(19,34,74,0.92)", stroke: null, r: 16 });
    const words = scene.narration.split(/\s+/).filter(Boolean);
    if (!words.length) return;
    const lay = T0.fitText(ctx, scene.narration, { x: box.x, y: box.y, w: box.w, h: box.h },
      { family: lesson.family, maxPx: T0.type.caption, minPx: T0.type.captionMin, maxLines: 2, weight: 600 });
    const lens = words.map((w) => Array.from(w).length), total = lens.reduce((a, b) => a + b, 0) || 1;
    const span = Math.max(0.1, scene.dur - 0.5);
    let acc = 0, active = -1;
    words.forEach((w, k) => { if (lt >= 0.15 + (acc / total) * span) active = k; acc += lens[k]; });
    ctx.save();
    ctx.font = lay.font; ctx.textBaseline = "top"; ctx.textAlign = "left";
    let k = 0, y = box.y + (box.h - lay.height) / 2;
    for (const line of lay.lines) {
      const lineWords = line.split(" ");
      let x = box.x + (box.w - ctx.measureText(line).width) / 2;
      for (const w of lineWords) {
        ctx.fillStyle = k === active ? P.accent2 : k < active ? P.text : P.muted;
        ctx.fillText(w, x, y);
        x += ctx.measureText(w + " ").width;
        k++;
      }
      y += lay.lineHeight;
    }
    ctx.restore();
  }

  function drawDots(ctx, idx) {
    const n = lesson.scenes.length, gap = 22, x0 = T0.W - 48 - (n - 1) * gap;
    for (let i = 0; i < n; i++) {
      ctx.fillStyle = i === idx ? T0.palette.accent : T0.palette.line;
      ctx.beginPath(); ctx.arc(x0 + i * gap, 44, i === idx ? 7 : 5, 0, Math.PI * 2); ctx.fill();
    }
  }

  function drawTemplate(ctx, scene, lt, alpha, dy) {
    const T = Object.assign({}, T0, { family: lesson.family, accent: T0.accents[(scene.id - 1) % 3], lang: lesson.lang });
    const fn = window.Templates[scene.type] || window.Templates.bullets;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(0, dy);
    try {
      fn(ctx, scene.params, lt, scene.dur, T, lesson.lang);
    } catch (e) {
      // Never throw, never blank: fall back to bullets with the same params, then to plain labels.
      ctx.restore(); ctx.save(); ctx.globalAlpha = alpha; ctx.translate(0, dy);
      try { window.Templates.bullets(ctx, scene.params, lt, scene.dur, T, lesson.lang); }
      catch (e2) {
        T0.drawText(ctx, (scene.params.labels || []).join(" · "), { x: 64, y: 200, w: T0.W - 128, h: 200 },
          { family: lesson.family, maxPx: 40, minPx: 20, maxLines: 4, align: "center" });
      }
    }
    ctx.restore();
  }

  window.renderAtTime = function (t) {
    const ctx = canvas().getContext("2d");
    if (!lesson || !lesson.scenes.length) {
      ctx.fillStyle = T0.palette.bg; ctx.fillRect(0, 0, T0.W, T0.H);
      return;
    }
    t = T0.clamp(Number(t) || 0, 0, lesson.total);
    const idx = sceneAt(t), scene = lesson.scenes[idx], lt = t - scene.start;
    // Fade/slide in over the first TAIL seconds (not for scene 1 at t=0's very first frame), out over the last TAIL.
    const tin = idx === 0 ? 1 : T0.easeOutCubic(lt / TAIL);
    const isLast = idx === lesson.scenes.length - 1;
    const tout = isLast ? 1 : T0.easeInOutCubic((scene.end - t) / TAIL);
    const alpha = Math.min(tin, tout);
    drawBackground(ctx, scene);
    drawHeader(ctx);
    drawTemplate(ctx, scene, lt, alpha, (1 - tin) * 24 - (1 - tout) * 24);
    drawCaption(ctx, scene, lt);
    drawDots(ctx, idx);
  };

  window.totalDuration = 0;
  window.ready = false;
})();
