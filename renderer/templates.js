// renderer/templates.js — the 8 visual templates. draw(ctx, params, lt, dur, T, lang)
// params = {labels: [...], steps: [...]}; lt = seconds into the scene; T = Theme plus T.family and T.accent.
// Items appear one by one and are all visible by dur * 0.6. Every text draw goes through T.drawText (fitText).
(function () {
  "use strict";

  const S = () => window.Theme.safe;

  function list(a) { return Array.isArray(a) ? a.filter((x) => String(x || "").trim()).map(String) : []; }

  // ---- 1. title -----------------------------------------------------------------------------------------------
  function title(ctx, p, lt, dur, T) {
    const s = S(), labels = list(p.labels), steps = list(p.steps);
    const a0 = T.appear(lt, dur, 0, 3);
    const head = T.drawText(ctx, labels[0] || "", { x: s.x + 40, y: 150, w: s.w - 80, h: 150 },
      { family: T.family, maxPx: 64, minPx: 36, maxLines: 2, align: "center", valign: "middle", weight: 800, alpha: a0 });
    // Accent underline sweeps in under the headline.
    const sweep = T.easeInOutCubic((lt - 0.4) / 0.8);
    const uw = Math.min(head.width, s.w - 80) * sweep;
    ctx.save(); ctx.fillStyle = T.accent; T.roundRect(ctx, T.W / 2 - uw / 2, 312, uw, 8, 4); ctx.fill(); ctx.restore();
    // Other labels as chips.
    const chips = labels.slice(1, 5);
    if (chips.length) {
      const gap = 24, cw = Math.min(360, (s.w - gap * (chips.length - 1)) / chips.length), total = chips.length * cw + gap * (chips.length - 1);
      chips.forEach((c, i) => {
        const a = T.appear(lt, dur, i + 1, chips.length + 2), x = T.W / 2 - total / 2 + i * (cw + gap), y = 360 + (1 - a) * 20;
        T.panel(ctx, x, y, cw, 76, { fill: T.palette.panel2, stroke: T.accent, r: 38, alpha: a });
        T.drawText(ctx, c, { x: x + 18, y: y + 8, w: cw - 36, h: 60 },
          { family: T.family, maxPx: 30, minPx: 20, maxLines: 2, align: "center", valign: "middle", alpha: a });
      });
    }
    if (steps[0]) {
      const a = T.appear(lt, dur, chips.length + 1, chips.length + 2);
      T.drawText(ctx, steps[0], { x: s.x + 80, y: 470, w: s.w - 160, h: 90 },
        { family: T.family, maxPx: 32, minPx: 22, maxLines: 2, align: "center", color: T.palette.muted, weight: 500, alpha: a });
    }
  }

  // ---- 2. bullets ---------------------------------------------------------------------------------------------
  function bullets(ctx, p, lt, dur, T) {
    const s = S(), labels = list(p.labels), rows = list(p.steps).length ? list(p.steps) : labels.slice(1);
    const heading = labels[0] || "";
    const a0 = T.appear(lt, dur, 0, rows.length + 1);
    T.drawText(ctx, heading, { x: s.x, y: s.y + 8, w: s.w, h: 70 },
      { family: T.family, maxPx: 44, minPx: 28, maxLines: 1, weight: 800, alpha: a0 });
    const n = Math.max(1, rows.length), top = s.y + 100, rowH = Math.min(96, (s.y + s.h - top) / n);
    rows.forEach((r, i) => {
      const a = T.appear(lt, dur, i + 1, n + 1), y = top + i * rowH, dx = (1 - a) * -40;
      ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = T.accents[i % 3];
      ctx.beginPath(); ctx.arc(s.x + 18 + dx, y + rowH / 2, 10, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      T.drawText(ctx, r, { x: s.x + 48 + dx, y: y + 4, w: s.w - 60, h: rowH - 8 },
        { family: T.family, maxPx: 34, minPx: 22, maxLines: 2, valign: "middle", alpha: a });
    });
  }

  // ---- 3. compare ---------------------------------------------------------------------------------------------
  function compare(ctx, p, lt, dur, T) {
    const s = S(), labels = list(p.labels).slice(0, 3), steps = list(p.steps);
    const cols = Math.max(2, labels.length), gap = 70, cw = (s.w - gap * (cols - 1)) / cols;
    const top = s.y + 10, ph = steps.length ? 250 : s.h - 20;
    for (let i = 0; i < cols; i++) {
      const a = T.appear(lt, dur, i, cols + steps.length), x = s.x + i * (cw + gap), y = top + (1 - a) * 24;
      T.panel(ctx, x, y, cw, ph, { fill: T.palette.panel, stroke: T.accents[i % 3], alpha: a });
      T.drawText(ctx, labels[i] || "", { x: x + 24, y: y + 20, w: cw - 48, h: ph - 40 },
        { family: T.family, maxPx: 36, minPx: 22, maxLines: 4, align: "center", valign: "middle", weight: 700, alpha: a });
      if (i < cols - 1) {
        const ab = T.appear(lt, dur, i + 1, cols + steps.length), bx = x + cw + gap / 2, by = top + ph / 2;
        ctx.save(); ctx.globalAlpha = ab; ctx.fillStyle = T.palette.accent2;
        ctx.beginPath(); ctx.arc(bx, by, 28, 0, Math.PI * 2); ctx.fill(); ctx.restore();
        T.drawText(ctx, "vs", { x: bx - 26, y: by - 20, w: 52, h: 40 },
          { family: window.Theme.families.en, maxPx: 26, minPx: 18, maxLines: 1, align: "center", valign: "middle",
            color: T.palette.bg, weight: 800, alpha: ab });
      }
    }
    const rowTop = top + ph + 24, rowH = Math.min(70, (s.y + s.h - rowTop) / Math.max(1, steps.length));
    steps.slice(0, 4).forEach((st, k) => {
      const a = T.appear(lt, dur, cols + k, cols + steps.length);
      T.drawText(ctx, st, { x: s.x + 20, y: rowTop + k * rowH, w: s.w - 40, h: rowH - 6 },
        { family: T.family, maxPx: 30, minPx: 20, maxLines: 2, align: "center", valign: "middle", color: T.palette.muted, alpha: a });
    });
  }

  // ---- 4. equation --------------------------------------------------------------------------------------------
  function equation(ctx, p, lt, dur, T) {
    const s = S(), labels = list(p.labels), steps = list(p.steps), legend = labels.slice(1, 5);
    const a0 = T.appear(lt, dur, 0, legend.length + steps.length + 1);
    const glow = 12 + 10 * Math.sin(Math.min(lt, dur * 0.6) * 3);
    ctx.save(); ctx.shadowColor = T.accent; ctx.shadowBlur = glow * a0;
    T.drawText(ctx, labels[0] || "", { x: s.x + 40, y: s.y + 10, w: s.w - 80, h: 130 },
      { family: T.family, maxPx: 76, minPx: 40, maxLines: 1, align: "center", valign: "middle", weight: 800, alpha: a0 });
    ctx.restore();
    const lx = s.x + 40, lw = steps.length ? s.w * 0.55 : s.w - 80, top = s.y + 160;
    const rowH = Math.min(70, (s.y + s.h - top) / Math.max(1, legend.length));
    legend.forEach((l, i) => {
      const a = T.appear(lt, dur, i + 1, legend.length + steps.length + 1);
      T.panel(ctx, lx, top + i * rowH, lw, rowH - 10, { fill: T.palette.panel, stroke: null, r: 12, alpha: a });
      T.drawText(ctx, l, { x: lx + 20, y: top + i * rowH + 4, w: lw - 40, h: rowH - 18 },
        { family: T.family, maxPx: 30, minPx: 20, maxLines: 1, valign: "middle", alpha: a });
    });
    const rx = lx + lw + 40, rw = s.x + s.w - rx;
    steps.slice(0, 4).forEach((st, k) => {
      const a = T.appear(lt, dur, legend.length + 1 + k, legend.length + steps.length + 1);
      const box = steps.length && legend.length ? { x: rx, y: top + k * 80, w: rw, h: 70 }
                                                : { x: s.x + 40, y: top + k * 80, w: s.w - 80, h: 70 };
      T.drawText(ctx, st, box, { family: T.family, maxPx: 36, minPx: 22, maxLines: 1, align: "center",
                                 valign: "middle", color: T.palette.accent2, weight: 700, alpha: a });
    });
  }

  // ---- 5. flow ------------------------------------------------------------------------------------------------
  function flow(ctx, p, lt, dur, T) {
    const s = S(), labels = list(p.labels).slice(0, 6), steps = list(p.steps);
    const n = Math.max(1, labels.length), perRow = n > 3 ? Math.ceil(n / 2) : n, rows = Math.ceil(n / perRow);
    const gap = 70, bw = (s.w - gap * (perRow - 1)) / perRow, bh = rows > 1 ? 140 : 180;
    const areaH = steps.length ? s.h - 110 : s.h, top = s.y + (areaH - (rows * bh + (rows - 1) * 60)) / 2;
    const centers = [];
    labels.forEach((l, i) => {
      const r = Math.floor(i / perRow), c = i % perRow, x = s.x + c * (bw + gap), y = top + r * (bh + 60);
      const a = T.appear(lt, dur, i, n + 1);
      T.panel(ctx, x, y + (1 - a) * 20, bw, bh, { fill: T.palette.panel, stroke: T.accents[i % 3], alpha: a });
      T.drawText(ctx, l, { x: x + 16, y: y + 12, w: bw - 32, h: bh - 24 },
        { family: T.family, maxPx: 32, minPx: 20, maxLines: 3, align: "center", valign: "middle", weight: 700, alpha: a });
      centers.push({ x, y, cx: x + bw / 2, cy: y + bh / 2 });
    });
    for (let i = 0; i + 1 < centers.length; i++) {
      const A = centers[i], B = centers[i + 1], pr = T.clamp((lt - 0.45 - i * 0.18 * 1.2) / 0.5, 0, 1);
      if (A.y === B.y) T.arrow(ctx, A.x + bw + 8, A.cy, B.x - 8, B.cy, pr, T.palette.muted, 4);
      else T.arrow(ctx, A.cx, A.y + bh + 6, B.cx, B.y - 6, pr, T.palette.muted, 4);
    }
    if (centers.length > 1) {  // a dot travels along the path once everything is in
      const q = ((lt - dur * 0.6) / Math.max(0.5, dur * 0.4));
      if (q > 0 && q < 1) {
        const f = q * (centers.length - 1), i = Math.min(centers.length - 2, Math.floor(f)), u = f - i;
        ctx.save(); ctx.fillStyle = T.palette.accent2;
        ctx.beginPath(); ctx.arc(T.lerp(centers[i].cx, centers[i + 1].cx, u), T.lerp(centers[i].cy, centers[i + 1].cy, u), 9, 0, Math.PI * 2);
        ctx.fill(); ctx.restore();
      }
    }
    if (steps[0]) {
      const a = T.appear(lt, dur, n, n + 1), y = s.y + s.h - 90;
      T.panel(ctx, s.x + 80, y, s.w - 160, 80, { fill: T.palette.panel2, stroke: T.palette.accent2, r: 40, alpha: a });
      T.drawText(ctx, steps[0], { x: s.x + 110, y: y + 8, w: s.w - 220, h: 64 },
        { family: T.family, maxPx: 32, minPx: 20, maxLines: 2, align: "center", valign: "middle", color: T.palette.accent2, weight: 700, alpha: a });
    }
  }

  // ---- 6. labeled_diagram -------------------------------------------------------------------------------------
  function labeled_diagram(ctx, p, lt, dur, T) {
    const s = S(), labels = list(p.labels), steps = list(p.steps), callouts = labels.slice(1, 7);
    const chipsH = steps.length ? 80 : 0, cy = s.y + (s.h - chipsH) / 2, cx = T.W / 2;
    const a0 = T.appear(lt, dur, 0, callouts.length + 2), rw = 300, rh = 150;
    T.panel(ctx, cx - rw / 2, cy - rh / 2, rw, rh, { fill: T.palette.panel2, stroke: T.accent, r: 75, alpha: a0 });
    T.drawText(ctx, labels[0] || "", { x: cx - rw / 2 + 24, y: cy - rh / 2 + 14, w: rw - 48, h: rh - 28 },
      { family: T.family, maxPx: 34, minPx: 20, maxLines: 3, align: "center", valign: "middle", weight: 800, alpha: a0 });
    const slots = [[-1, -1], [1, -1], [-1, 1], [1, 1], [-1, 0], [1, 0]];
    callouts.forEach((c, i) => {
      const [sx, sy] = slots[i], a = T.appear(lt, dur, i + 1, callouts.length + 2);
      const bw = 330, bh = 84, bx = sx < 0 ? s.x : s.x + s.w - bw;
      const by = sy === 0 ? cy - bh / 2 : sy < 0 ? s.y + 4 : cy + (s.h - chipsH) / 2 - bh - 8;
      const ex = sx < 0 ? bx + bw : bx, ey = by + bh / 2, tx = cx + sx * rw / 2 * 0.9, ty = cy + sy * rh / 2 * 0.8;
      T.arrow(ctx, ex, ey, tx, ty, a, T.palette.muted, 3);
      T.panel(ctx, bx, by, bw, bh, { fill: T.palette.panel, stroke: T.accents[i % 3], r: 14, alpha: a });
      T.drawText(ctx, c, { x: bx + 14, y: by + 8, w: bw - 28, h: bh - 16 },
        { family: T.family, maxPx: 28, minPx: 18, maxLines: 2, align: "center", valign: "middle", alpha: a });
    });
    if (steps.length) chipsRow(ctx, steps, s.y + s.h - 70, lt, dur, T, callouts.length + 1, callouts.length + 2);
  }

  function chipsRow(ctx, items, y, lt, dur, T, k0, n) {
    const s = S(), shown = items.slice(0, 4), gap = 18, cw = (s.w - gap * (shown.length - 1)) / shown.length;
    shown.forEach((st, k) => {
      const a = T.appear(lt, dur, Math.min(k0 + k, n), n + shown.length), x = s.x + k * (cw + gap);
      T.panel(ctx, x, y, cw, 62, { fill: T.palette.panel2, stroke: null, r: 31, alpha: a });
      T.drawText(ctx, st, { x: x + 16, y: y + 6, w: cw - 32, h: 50 },
        { family: T.family, maxPx: 26, minPx: 16, maxLines: 2, align: "center", valign: "middle", color: T.palette.accent2, alpha: a });
    });
  }

  // ---- 7. timeline --------------------------------------------------------------------------------------------
  function timeline(ctx, p, lt, dur, T) {
    const s = S(), labels = list(p.labels).slice(0, 6), steps = list(p.steps), n = Math.max(1, labels.length);
    const y = s.y + s.h / 2, x0 = s.x + 60, x1 = s.x + s.w - 60;
    const pr = T.easeInOutCubic((lt - 0.2) / Math.max(0.6, dur * 0.5));
    ctx.save(); ctx.strokeStyle = T.palette.line; ctx.lineWidth = 6; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(T.lerp(x0, x1, pr), y); ctx.stroke(); ctx.restore();
    const slot = n > 1 ? (x1 - x0) / (n - 1) : 0, bw = Math.min(260, (x1 - x0) / n + 40);
    labels.forEach((l, i) => {
      const x = n > 1 ? x0 + i * slot : (x0 + x1) / 2, a = T.appear(lt, dur, i, n), r = 14 * T.easeOutBack(a);
      ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = T.accents[i % 3];
      ctx.beginPath(); ctx.arc(x, y, Math.max(0, r), 0, Math.PI * 2); ctx.fill(); ctx.restore();
      const above = { x: T.clamp(x - bw / 2, s.x, s.x + s.w - bw), y: y - 150, w: bw, h: 120 };
      T.drawText(ctx, l, above, { family: T.family, maxPx: 30, minPx: 18, maxLines: 3, align: "center", valign: "middle", weight: 700, alpha: a });
      if (steps[i]) {
        T.drawText(ctx, steps[i], { x: above.x, y: y + 34, w: bw, h: 110 },
          { family: T.family, maxPx: 24, minPx: 16, maxLines: 3, align: "center", color: T.palette.muted, alpha: a });
      }
    });
    const q = T.clamp((lt - dur * 0.6) / Math.max(0.5, dur * 0.4), 0, 1);  // marker sweeps along once all is in
    if (q > 0) {
      ctx.save(); ctx.fillStyle = T.palette.text; ctx.beginPath(); ctx.arc(T.lerp(x0, x1, q), y, 7, 0, Math.PI * 2); ctx.fill(); ctx.restore();
    }
  }

  // ---- 8. graph -----------------------------------------------------------------------------------------------
  function graph(ctx, p, lt, dur, T) {
    const s = S(), labels = list(p.labels), steps = list(p.steps);
    const points = steps.map((st) => {
      const m = st.match(/(-?\d+(?:[.,]\d+)?)/);
      return m ? { name: st.replace(m[0], "").replace(/[:=]\s*$/, "").trim() || m[0], v: parseFloat(m[0].replace(",", "")) } : null;
    }).filter(Boolean);
    const gx = s.x + 90, gy = s.y + 20, gw = s.w - 130, gh = s.h - 110;
    const a0 = T.appear(lt, dur, 0, points.length + 2);
    ctx.save(); ctx.globalAlpha = a0; ctx.strokeStyle = T.palette.muted; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(gx, gy); ctx.lineTo(gx, gy + gh); ctx.lineTo(gx + gw, gy + gh); ctx.stroke(); ctx.restore();
    T.drawText(ctx, labels[0] || "", { x: gx, y: gy + gh + 14, w: gw, h: 44 },
      { family: T.family, maxPx: 26, minPx: 16, maxLines: 1, align: "center", color: T.palette.muted, alpha: a0 });
    if (labels[1]) {
      ctx.save(); ctx.translate(s.x + 20, gy + gh / 2); ctx.rotate(-Math.PI / 2);
      T.drawText(ctx, labels[1], { x: -gh / 2, y: -10, w: gh, h: 40 },
        { family: T.family, maxPx: 26, minPx: 16, maxLines: 1, align: "center", color: T.palette.muted, alpha: a0 });
      ctx.restore();
    }
    if (points.length >= 2) {  // animated bars that grow to their value
      const max = Math.max(...points.map((q) => Math.abs(q.v))) || 1, n = points.length, bw = gw / n * 0.6;
      points.slice(0, 8).forEach((q, i) => {
        const a = T.appear(lt, dur, i + 1, n + 2), h = (Math.abs(q.v) / max) * (gh - 60) * a, x = gx + (i + 0.5) * (gw / n) - bw / 2;
        ctx.save(); ctx.fillStyle = T.accents[i % 3]; T.roundRect(ctx, x, gy + gh - h, bw, h, 8); ctx.fill(); ctx.restore();
        T.drawText(ctx, (Math.round(q.v * a * 100) / 100).toString(), { x: x - 20, y: gy + gh - h - 40, w: bw + 40, h: 34 },
          { family: window.Theme.families.en, maxPx: 24, minPx: 14, maxLines: 1, align: "center", alpha: a });
        T.drawText(ctx, q.name, { x: x - 30, y: gy + gh - 52, w: bw + 60, h: 0 + 48 },
          { family: T.family, maxPx: 18, minPx: 12, maxLines: 2, align: "center", color: T.palette.bg, alpha: a > 0.9 ? 1 : 0 });
      });
    } else {  // not numeric: an illustrative rising curve so the scene is never empty
      const pr = T.easeInOutCubic((lt - 0.3) / Math.max(0.6, dur * 0.5));
      ctx.save(); ctx.strokeStyle = T.accent; ctx.lineWidth = 6; ctx.lineCap = "round"; ctx.beginPath();
      for (let k = 0; k <= 60 * pr; k++) {
        const u = k / 60, x = gx + 20 + u * (gw - 40), y = gy + gh - 20 - (gh - 80) * (u * u * 0.6 + u * 0.4);
        if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke(); ctx.restore();
      steps.slice(0, 3).forEach((st, k) => {
        const a = T.appear(lt, dur, k + 1, 4);
        T.drawText(ctx, st, { x: gx + 40, y: gy + 20 + k * 56, w: gw * 0.55, h: 50 },
          { family: T.family, maxPx: 28, minPx: 18, maxLines: 1, alpha: a });
      });
    }
  }

  window.Templates = { title, bullets, compare, equation, flow, labeled_diagram, timeline, graph };
})();
