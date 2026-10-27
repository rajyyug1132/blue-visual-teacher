// renderer/theme.js
// Dark navy theme, type scale, easing, deterministic PRNG, and text layout helpers.

(function (root) {
  const THEME = {
    colors: {
      bg: '#0B1530',        // Deep navy
      panel: '#13224A',     // Panel fill
      panelBorder: '#233876',
      text: '#F4F7FF',      // High contrast primary text
      muted: '#9FB0D6',     // Secondary/muted text
      accent: '#3DA5FF',    // Primary blue accent
      accent2: '#FFC53D',   // Amber accent
      good: '#4ADE80',      // Green
      warn: '#FB7185',      // Red / warning
      progressTrack: '#1A2C5B',
      progressFill: '#3DA5FF',
    },

    safeArea: {
      width: 1280,
      height: 720,
      margin: 64,
      headerHeight: 72,
      captionY: 604,
      captionHeight: 96,
    },

    fonts: {
      en: '"Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      hi: '"Noto Sans Devanagari", "Nirmala UI", "Noto Sans", sans-serif',
      kn: '"Noto Sans Kannada", "Nirmala UI", "Noto Sans", sans-serif',
      ta: '"Noto Sans Tamil", "Nirmala UI", "Noto Sans", sans-serif',
      te: '"Noto Sans Telugu", "Nirmala UI", "Noto Sans", sans-serif',
    },

    getFont(lang) {
      return this.fonts[lang] || this.fonts.en;
    },

    // Mulberry32 deterministic 32-bit PRNG
    rng(seed) {
      let a = (seed >>> 0) || 123456789;
      return function () {
        a = (a + 0x6D2B79F5) >>> 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    },

    // Easing functions
    easeOutCubic(x) {
      const t = Math.max(0, Math.min(1, x));
      return 1 - Math.pow(1 - t, 3);
    },

    easeInOutCubic(x) {
      const t = Math.max(0, Math.min(1, x));
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    },

    easeOutBack(x) {
      const t = Math.max(0, Math.min(1, x));
      const c1 = 1.70158;
      const c3 = c1 + 1;
      return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    },

    // Word wrap helper (respects spaces for Latin and Indic scripts)
    wrapText(ctx, text, maxWidth) {
      if (!text) return [];
      const words = String(text).trim().split(/\s+/);
      const lines = [];
      let currentLine = words[0] || '';

      for (let i = 1; i < words.length; i++) {
        const candidate = currentLine + ' ' + words[i];
        if (ctx.measureText(candidate).width <= maxWidth) {
          currentLine = candidate;
        } else {
          lines.push(currentLine);
          currentLine = words[i];
        }
      }
      if (currentLine) {
        lines.push(currentLine);
      }
      return lines;
    },

    // Fit text inside a bounding box by scaling font size from maxPx down to minPx
    fitText(ctx, text, box, maxPx, minPx, weight = 600, lang = 'en') {
      const family = this.getFont(lang);
      let fontSize = maxPx;
      ctx.font = `${weight} ${fontSize}px ${family}`;

      while (fontSize > minPx) {
        const lines = this.wrapText(ctx, text, box.width);
        const totalHeight = lines.length * (fontSize * 1.25);
        if (totalHeight <= box.height && lines.every(l => ctx.measureText(l).width <= box.width)) {
          return { fontSize, lines, lineHeight: fontSize * 1.25 };
        }
        fontSize -= 2;
        ctx.font = `${weight} ${fontSize}px ${family}`;
      }

      // Fallback: at minPx, wrap and truncate if necessary
      const lines = this.wrapText(ctx, text, box.width);
      return { fontSize: minPx, lines, lineHeight: minPx * 1.25 };
    },

    // Draw rounded rectangle helper
    drawRoundedRect(ctx, x, y, width, height, radius, fillStyle, strokeStyle, lineWidth = 1) {
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(x + radius, y);
      ctx.arcTo(x + width, y, x + width, y + height, radius);
      ctx.arcTo(x + width, y + height, x, y + height, radius);
      ctx.arcTo(x, y + height, x, y, radius);
      ctx.arcTo(x, y, x + width, y, radius);
      ctx.closePath();
      if (fillStyle) {
        ctx.fillStyle = fillStyle;
        ctx.fill();
      }
      if (strokeStyle) {
        ctx.strokeStyle = strokeStyle;
        ctx.lineWidth = lineWidth;
        ctx.stroke();
      }
      ctx.restore();
    }
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = THEME;
  } else {
    root.THEME = THEME;
  }
})(typeof window !== 'undefined' ? window : globalThis);
