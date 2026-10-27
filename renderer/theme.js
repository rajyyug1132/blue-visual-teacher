// renderer/theme.js — palette, type scale, easing, seeded PRNG and text-fitting helpers.
// Everything here is a pure function: the renderer must draw the same pixels for the same t.
(function () {
  "use strict";

  const W = 1280, H = 720;

  const palette = {
    bg: "#0B1530", panel: "#13224A", panel2: "#1A2D5E", text: "#F4F7FF", muted: "#9FB0D6",
    accent: "#3DA5FF", accent2: "#FFC53D", good: "#4ADE80", warn: "#FB7185", line: "#2A3F78",
  };
  const accents = [palette.accent, palette.accent2, palette.good];

  const type = { title: 56, headline: 44, label: 34, labelMin: 28, step: 30, stepMin: 24, caption: 30, captionMin: 24 };
  const safe = { x: 64, y: 88, w: W - 128, h: 600 - 88 - 16, captionY: 600, captionH: 104, headerH: 72 };

  const families = {
    en: '"Noto Sans", "Segoe UI", sans-serif',
    hi: '"Noto Sans Devanagari", "Nirmala UI", "Noto Sans", sans-serif',
    kn: '"Noto Sans Kannada", "Nirmala UI", "Noto Sans", sans-serif',
    ta: '"Noto Sans Tamil", "Nirmala UI", "Noto Sans", sans-serif',
    te: '"Noto Sans Telugu", "Nirmala UI", "Noto Sans", sans-serif',
  };

  // Script detection for callers that pass no lang (BLUEPRINT 5.1 calls initLesson(title, scenes)).
  function detectLang(text) {
    if (/[ಀ-೿]/.test(text)) return "kn";
    if (/[ऀ-ॿ]/.test(text)) return "hi";
    if (/[஀-௿]/.test(text)) return "ta";
    if (/[ఀ-౿]/.test(text)) return "te";
    return "en";
  }

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const lerp = (a, b, p) => a + (b - a) * p;
  const easeOutCubic = (p) => 1 - Math.pow(1 - clamp(p, 0, 1), 3);
  const easeInOutCubic = (p) => { p = clamp(p, 0, 1); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
  const easeOutBack = (p) => { p = clamp(p, 0, 1); const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };

  // Item k of a scene appears after 0.2 s + k * 0.18 s and takes 0.5 s; everything is in by dur * 0.6 at the latest.
  function appear(lt, dur, k, n) {
    const stagger = Math.min(0.18, n > 1 ? (dur * 0.6 - 0.7) / Math.max(1, n - 1) : 0.18);
    const start = 0.2 + k * Math.max(0.05, stagger);
    return easeOutCubic((lt - start) / 0.5);
  }

  // mulberry32: deterministic decorative randomness, seeded by scene id.
  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function font(px, family, weight) { return `${weight || 600} ${Math.round(px)}px ${family}`; }

  // Wrap by words (Indic scripts are space-separated too); a single over-long word is split by characters.
  function wrapText(ctx, text, maxWidth) {
    const words = String(text).split(/\s+/).filter(Boolean);
    const lines = [];
    let line = "";
    for (const word of words) {
      const trial = line ? line + " " + word : word;
      if (ctx.measureText(trial).width <= maxWidth) { line = trial; continue; }
      if (line) lines.push(line);
      if (ctx.measureText(word).width <= maxWidth) { line = word; continue; }
      let chunk = "";
      for (const ch of Array.from(word)) {
        if (ctx.measureText(chunk + ch).width > maxWidth && chunk) { lines.push(chunk); chunk = ch; } else chunk += ch;
      }
      line = chunk;
    }
    if (line) lines.push(line);
    return lines.length ? lines : [""];
  }

  function truncate(ctx, text, maxWidth) {
    if (ctx.measureText(text).width <= maxWidth) return text;
    const chars = Array.from(text);
    while (chars.length && ctx.measureText(chars.join("") + "…").width > maxWidth) chars.pop();
    return chars.join("") + "…";
  }

  // Shrink from maxPx to minPx until the wrapped text fits the box; then truncate the last line as a last resort.
  // Returns the layout without drawing, so callers can position other things around it.
  function fitText(ctx, text, box, opts) {
    const o = Object.assign({ maxPx: type.label, minPx: type.labelMin, family: families.en, weight: 600,
                              maxLines: 3, lineHeight: 1.22 }, opts || {});
    let px = o.maxPx, lines = [];
    for (; px >= o.minPx; px -= 2) {
      ctx.font = font(px, o.family, o.weight);
      lines = wrapText(ctx, text, box.w);
      if (lines.length <= o.maxLines && lines.length * px * o.lineHeight <= box.h) break;
    }
    px = Math.max(px, o.minPx);
    ctx.font = font(px, o.family, o.weight);
    lines = wrapText(ctx, text, box.w);
    const fitLines = Math.max(1, Math.min(o.maxLines, Math.floor(box.h / (px * o.lineHeight))));
    if (lines.length > fitLines) {
      lines = lines.slice(0, fitLines);
      lines[fitLines - 1] = truncate(ctx, lines[fitLines - 1] + " …", box.w);
    }
    return { lines, px, lineHeight: px * o.lineHeight, font: ctx.font,
             height: lines.length * px * o.lineHeight, width: Math.max(...lines.map((l) => ctx.measureText(l).width)) };
  }

  // Every text draw goes through here. align: left|center|right; valign: top|middle.
  function drawText(ctx, text, box, opts) {
    const o = Object.assign({ color: palette.text, align: "left", valign: "top", alpha: 1 }, opts || {});
    const lay = fitText(ctx, text, box, o);
    ctx.save();
    ctx.globalAlpha *= o.alpha;
    ctx.font = lay.font;
    ctx.fillStyle = o.color;
    ctx.textAlign = o.align;
    ctx.textBaseline = "top";
    const x = o.align === "center" ? box.x + box.w / 2 : o.align === "right" ? box.x + box.w : box.x;
    let y = o.valign === "middle" ? box.y + (box.h - lay.height) / 2 : box.y;
    for (const line of lay.lines) { ctx.fillText(line, x, y + (lay.lineHeight - lay.px) / 2); y += lay.lineHeight; }
    ctx.restore();
    return lay;
  }

  function roundRect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function panel(ctx, x, y, w, h, opts) {
    const o = Object.assign({ fill: palette.panel, stroke: palette.line, r: 18, alpha: 1 }, opts || {});
    ctx.save();
    ctx.globalAlpha *= o.alpha;
    roundRect(ctx, x, y, w, h, o.r);
    ctx.fillStyle = o.fill;
    ctx.fill();
    if (o.stroke) { ctx.lineWidth = 2; ctx.strokeStyle = o.stroke; ctx.stroke(); }
    ctx.restore();
  }

  function arrow(ctx, x1, y1, x2, y2, p, color, width) {
    p = clamp(p, 0, 1);
    if (p <= 0) return;
    const x = lerp(x1, x2, p), y = lerp(y1, y2, p);
    ctx.save();
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width || 4; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x, y); ctx.stroke();
    if (p > 0.6) {
      const a = Math.atan2(y2 - y1, x2 - x1), s = 14;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x - s * Math.cos(a - 0.45), y - s * Math.sin(a - 0.45));
      ctx.lineTo(x - s * Math.cos(a + 0.45), y - s * Math.sin(a + 0.45));
      ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  }

  window.Theme = { W, H, palette, accents, type, safe, families, detectLang, clamp, lerp, easeOutCubic,
                   easeInOutCubic, easeOutBack, appear, rng, font, wrapText, truncate, fitText, drawText,
                   roundRect, panel, arrow };
})();
