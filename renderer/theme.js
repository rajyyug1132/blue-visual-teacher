// renderer/theme.js
// Editorial warm ivory design system, type scale, easing, deterministic PRNG, and text layout helpers.

(function (root) {
  const THEME = {
    colors: {
      bg: '#FAF7EE',          // Warm ivory graph-paper background
      gridLine: '#E8E2D2',    // Subtle graph paper grid
      text: '#0F172A',        // Near-black typography
      muted: '#64748B',       // Slate secondary/supporting text
      border: '#0F172A',      // Bold black outline (2px - 2.5px)
      accent: '#2563EB',      // Electric blue primary brand accent
      amber: '#F59E0B',       // Warm amber yellow
      coral: '#EF4444',       // Coral red
      green: '#10B981',       // Muted emerald green
      indigo: '#6366F1',      // Accent indigo
      cardBg: '#FFFFFF',      // Pure white card background
      kickerBg: '#FEF3C7',    // Amber kicker pill background
      kickerBorder: '#0F172A',

      // Backward-compatible keys for existing tests & engine
      panel: '#FFFFFF',
      panelBorder: '#0F172A',
      accent2: '#F59E0B',
      good: '#10B981',
      warn: '#EF4444',
      progressTrack: '#E2E8F0',
      progressFill: '#2563EB',
    },

    safeArea: {
      width: 1280,
      height: 720,
      margin: 64,
      headerHeight: 52,
      captionY: 604,
      captionHeight: 96,
    },

    fonts: {
      en: '"Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      hi: '"Noto Sans Devanagari", "Nirmala UI", "Noto Sans", sans-serif',
      kn: '"Noto Sans Kannada", "Nirmala UI", "Noto Sans", sans-serif',
      ta: '"Noto Sans Tamil", "Nirmala UI", "Noto Sans", sans-serif',
      te: '"Noto Sans Telugu", "Nirmala UI", "Noto Sans", sans-serif',
      bn: '"Noto Sans Bengali", "Noto Sans", sans-serif',
    },

    getFont(lang) {
      return this.fonts[lang] || this.fonts.en;
    },

    // Draw subtle square graph-paper grid across the canvas
    drawGraphGrid(ctx, width = 1280, height = 720, step = 28) {
      ctx.save();
      ctx.strokeStyle = this.colors.gridLine;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x <= width; x += step) {
        ctx.moveTo(x + 0.5, 0);
        ctx.lineTo(x + 0.5, height);
      }
      for (let y = 0; y <= height; y += step) {
        ctx.moveTo(0, y + 0.5);
        ctx.lineTo(width, y + 0.5);
      }
      ctx.stroke();
      ctx.restore();
    },

    // Draw small electric blue square brand accent (■) after headings
    drawBrandAccent(ctx, x, y, size = 11) {
      ctx.save();
      ctx.fillStyle = this.colors.accent;
      ctx.fillRect(Math.round(x), Math.round(y - size), size, size);
      ctx.restore();
    },

    // Draw rounded kicker pill badge: [ KICKER TITLE ]
    drawPill(ctx, text, x, y, options = {}) {
      const {
        bg = this.colors.kickerBg,
        color = this.colors.text,
        border = this.colors.border,
        lineWidth = 1.5,
        height = 28,
        fontSize = 13,
        weight = 700,
        font = this.getFont('en'),
        bracketed = true
      } = options;

      ctx.save();
      ctx.font = `${weight} ${fontSize}px ${font}`;
      const displayText = bracketed && !text.startsWith('[') ? `[ ${text} ]` : text;
      const textWidth = ctx.measureText(displayText).width;
      const width = Math.round(textWidth + 24);
      const radius = Math.round(height / 2);

      this.drawRoundedRect(ctx, x, y, width, height, radius, bg, border, lineWidth);

      ctx.fillStyle = color;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(displayText, x + width / 2, y + height / 2);
      ctx.restore();
      return width;
    },

    // Draw consistent outlined card container
    drawCard(ctx, x, y, w, h, radius = 16, fill = this.colors.cardBg, stroke = this.colors.border, lineWidth = 2) {
      this.drawRoundedRect(ctx, x, y, w, h, radius, fill, stroke, lineWidth);
    },

    // Draw outlined chevron connector arrow
    drawOutlinedArrow(ctx, x1, y1, x2, y2, headSize = 16, fill = '#FAF7EE', stroke = this.colors.border, lineWidth = 2) {
      ctx.save();
      const angle = Math.atan2(y2 - y1, x2 - x1);
      ctx.strokeStyle = stroke;
      ctx.fillStyle = fill;
      ctx.lineWidth = lineWidth;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';

      // Draw shaft
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      // Draw arrowhead
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - headSize * Math.cos(angle - Math.PI / 6), y2 - headSize * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(x2 - headSize * 0.5 * Math.cos(angle), y2 - headSize * 0.5 * Math.sin(angle));
      ctx.lineTo(x2 - headSize * Math.cos(angle + Math.PI / 6), y2 - headSize * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.restore();
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

    // Typography scale presets for layout-safe sizing
    typography: {
      display: { max: 44, min: 28, weight: 800 },
      section: { max: 32, min: 20, weight: 700 },
      cardTitle: { max: 22, min: 14, weight: 700 },
      body: { max: 18, min: 12, weight: 500 },
      kicker: { max: 14, min: 10, weight: 700 },
      chip: { max: 12, min: 9, weight: 700 }
    },

    diagnostics: [],
    overflowErrors: [],
    capacityViolations: [],
    verboseDiagnostics: false,

    clearDiagnostics() {
      this.diagnostics = [];
      this.overflowErrors = [];
      this.capacityViolations = [];
    },

    hasOverflows() {
      return this.overflowErrors.length > 0 || this.diagnostics.some(d => d.type === 'TEXT_OVERFLOW');
    },

    getOverflows() {
      return this.overflowErrors.length > 0 ? this.overflowErrors : this.diagnostics.filter(d => d.type === 'TEXT_OVERFLOW');
    },

    hasCapacityViolations() {
      return this.capacityViolations.length > 0 || this.diagnostics.some(d => d.type === 'CAPACITY_EXCEEDED');
    },

    getCapacityViolations() {
      return this.capacityViolations.length > 0 ? this.capacityViolations : this.diagnostics.filter(d => d.type === 'CAPACITY_EXCEEDED');
    },

    reportCapacityViolation(templateType, limitType, count, maxAllowed, details = {}) {
      const violation = {
        template: templateType,
        limitType,
        count,
        maxAllowed,
        overflowCount: count - maxAllowed,
        details,
        timestamp: 0
      };
      this.capacityViolations.push(violation);
      this.logDiagnostic('CAPACITY_EXCEEDED', `[${templateType}] ${limitType} count (${count}) exceeds maximum supported cap (${maxAllowed})`, violation);
      return violation;
    },

    assertNoOverflow() {
      if (this.hasOverflows()) {
        const first = this.getOverflows()[0];
        throw new Error(`Renderer content overflow error: [${first.tag || 'unknown'}] required ${first.requiredHeight || 'extra'}px > allocated ${first.box ? first.box.height : 'unknown'}px`);
      }
      return true;
    },

    logDiagnostic(type, msg, meta = {}) {
      const record = { type, msg, meta, timestamp: 0 };
      this.diagnostics.push(record);
      if (this.verboseDiagnostics && typeof console !== 'undefined' && console.warn) {
        console.warn(`[Renderer Diagnostic: ${type}] ${msg}`, meta);
      }
      return record;
    },

    // Truncate text with ellipsis if it exceeds maxWidth
    truncate(ctx, text, maxWidth) {
      if (!text) return '';
      if (ctx.measureText(text).width <= maxWidth) return text;
      const ellipsis = '...';
      let low = 0;
      let high = text.length;
      let result = '';
      while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        const candidate = text.substring(0, mid) + ellipsis;
        if (ctx.measureText(candidate).width <= maxWidth) {
          result = candidate;
          low = mid + 1;
        } else {
          high = mid - 1;
        }
      }
      return result || ellipsis;
    },

    // Word wrap helper (respects spaces for Latin and Indic scripts, supports safe word breaking)
    wrapText(ctx, text, maxWidth, options = {}) {
      if (!text) return [];
      const words = String(text).trim().split(/\s+/);
      const lines = [];
      let currentLine = '';

      for (let i = 0; i < words.length; i++) {
        let word = words[i];

        // If a single word exceeds maxWidth
        if (ctx.measureText(word).width > maxWidth) {
          if (options.breakWords) {
            if (currentLine) {
              lines.push(currentLine);
              currentLine = '';
            }
            while (ctx.measureText(word).width > maxWidth && word.length > 2) {
              let splitIdx = Math.floor(word.length * (maxWidth / ctx.measureText(word).width));
              while (splitIdx > 1 && ctx.measureText(word.substring(0, splitIdx) + '-').width > maxWidth) {
                splitIdx--;
              }
              if (splitIdx <= 1) splitIdx = 2;
              lines.push(word.substring(0, splitIdx) + '-');
              word = word.substring(splitIdx);
            }
            currentLine = word;
            continue;
          } else {
            word = this.truncate(ctx, word, maxWidth);
          }
        }

        if (!currentLine) {
          currentLine = word;
        } else {
          const candidate = currentLine + ' ' + word;
          if (ctx.measureText(candidate).width <= maxWidth) {
            currentLine = candidate;
          } else {
            lines.push(currentLine);
            currentLine = word;
          }
        }
      }
      if (currentLine) {
        lines.push(currentLine);
      }
      return lines;
    },

    autoFitText(ctx, text, maxWidth, initialFontSize, minFontSize) {
      const maxPx = initialFontSize || 24;
      const minPx = minFontSize || 12;
      return this.fitText(ctx, String(text || ''), { width: maxWidth, height: Math.ceil(maxPx * 4) }, maxPx, minPx);
    },

    fitText(ctx, text, box, maxPx, minPx, weight = 600, lang = 'en', options = {}) {
      const family = this.getFont(lang);
      const isIndic = lang === 'hi' || lang === 'kn' || lang === 'ta' || lang === 'te' || lang === 'bn';
      const lineMultiplier = isIndic ? 1.35 : 1.25;
      const tag = options.label || 'text';
      const wrapOpts = { breakWords: isIndic || Boolean(options.breakWords) };

      let fontSize = maxPx;
      ctx.font = `${weight} ${fontSize}px ${family}`;

      while (fontSize > minPx) {
        const lines = this.wrapText(ctx, text, box.width, wrapOpts);
        const lineHeight = Math.round(fontSize * lineMultiplier);
        const totalHeight = lines.length * lineHeight;
        if (totalHeight <= box.height && lines.every(l => ctx.measureText(l).width <= box.width)) {
          return {
            fontSize,
            lines,
            lineHeight,
            totalHeight,
            requiredHeight: totalHeight,
            fits: true,
            truncated: false,
            count: lines.length,
            grew: false,
            overflowError: null
          };
        }
        fontSize -= 2;
        ctx.font = `${weight} ${fontSize}px ${family}`;
      }

      // At minPx: wrap and evaluate fit
      ctx.font = `${weight} ${minPx}px ${family}`;
      const lineHeight = Math.round(minPx * lineMultiplier);
      let lines = this.wrapText(ctx, text, box.width, wrapOpts);
      const totalUnclippedHeight = lines.length * lineHeight;
      const maxAllowedLines = Math.max(1, Math.floor(box.height / lineHeight));
      let truncated = false;

      // Caller option: allow vertical expansion if whitespace permits
      if (options.allowGrowth && lines.length > maxAllowedLines) {
        return {
          fontSize: minPx,
          lines,
          lineHeight,
          totalHeight: totalUnclippedHeight,
          requiredHeight: totalUnclippedHeight,
          fits: true,
          truncated: false,
          count: lines.length,
          grew: true,
          overflowError: null
        };
      }

      if (lines.length > maxAllowedLines) {
        truncated = true;
        lines = lines.slice(0, maxAllowedLines);
        lines[maxAllowedLines - 1] = this.truncate(ctx, lines[maxAllowedLines - 1], box.width);
      } else {
        for (let i = 0; i < lines.length; i++) {
          if (ctx.measureText(lines[i]).width > box.width) {
            lines[i] = this.truncate(ctx, lines[i], box.width);
            truncated = true;
          }
        }
      }

      const totalHeight = lines.length * lineHeight;
      const fits = !truncated && totalHeight <= box.height;
      const overflowError = !fits ? `TEXT_OVERFLOW: [${tag}] required ${totalUnclippedHeight}px, available ${box.height}px` : null;

      if (!fits) {
        const msg = `[${tag}] Text exceeded box (${box.width}x${box.height}) at minPx ${minPx}`;
        const eventKey = `${tag}::${box.width}x${box.height}::${String(text).substring(0, 60)}`;
        const exists = this.overflowErrors.some(e => e.key === eventKey);
        if (!exists) {
          const overflowRecord = {
            key: eventKey,
            msg,
            tag,
            text: String(text).substring(0, 80),
            box,
            minPx,
            requiredHeight: totalUnclippedHeight,
            allowedLines: maxAllowedLines,
            neededLines: Math.ceil(totalUnclippedHeight / lineHeight),
            truncated,
            overflowError
          };
          this.overflowErrors.push(overflowRecord);
          this.logDiagnostic('TEXT_OVERFLOW', msg, overflowRecord);
        }
      }

      return {
        fontSize: minPx,
        lines,
        lineHeight,
        totalHeight,
        requiredHeight: totalUnclippedHeight,
        fits,
        truncated,
        count: lines.length,
        grew: false,
        overflowError
      };
    },

    // Draw fitted text lines, rendering an observable visual badge if content was truncated
    drawFittedLines(ctx, fit, x, y, options = {}) {
      if (!fit || !fit.lines) return;
      fit.lines.forEach((l, idx) => {
        ctx.fillText(l, x, y + idx * fit.lineHeight);
      });
      if (fit.truncated && !options.silent) {
        const badgeX = options.badgeX || x;
        const badgeY = options.badgeY || (y + fit.lines.length * fit.lineHeight + 4);
        this.drawPill(ctx, '! CONTENT OVERFLOW', badgeX, badgeY, {
          bg: '#FEE2E2',
          color: '#DC2626',
          border: '#DC2626',
          lineWidth: 1.5,
          height: 20,
          fontSize: 9,
          weight: 800,
          font: this.getFont('en'),
          bracketed: true
        });
      }
    },

    // Draw rounded rectangle helper with fallback for minimal contexts
    drawRoundedRect(ctx, x, y, width, height, radius, fillStyle, strokeStyle, lineWidth = 1) {
      ctx.save();
      ctx.beginPath();
      if (typeof ctx.arcTo === 'function') {
        ctx.moveTo(x + radius, y);
        ctx.arcTo(x + width, y, x + width, y + height, radius);
        ctx.arcTo(x + width, y + height, x, y + height, radius);
        ctx.arcTo(x, y + height, x, y, radius);
        ctx.arcTo(x, y, x + width, y, radius);
        ctx.closePath();
      } else if (typeof ctx.rect === 'function') {
        ctx.rect(x, y, width, height);
      } else if (typeof ctx.fillRect === 'function' && fillStyle) {
        ctx.fillStyle = fillStyle;
        ctx.fillRect(x, y, width, height);
        ctx.restore();
        return;
      }
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
