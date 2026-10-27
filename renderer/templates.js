// renderer/templates.js
// Visual templates for lesson rendering with deterministic animations and graceful fallbacks.

(function (root) {
  const TEMPLATES = {
    // 1. TITLE TEMPLATE
    title(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      // Intro animation progress (staggered, completed by dur * 0.5)
      const pTitle = theme.easeOutCubic(Math.min(1, lt / 0.6));
      const pSubtitle = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.25) / 0.6)));
      const pUnderline = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.4) / 0.7)));

      const centerX = 1280 / 2;
      const centerY = 310;

      // Draw Main Headline (labels[0])
      const mainTitle = labels[0] || 'Lesson';
      const fit = theme.fitText(ctx, mainTitle, { width: 1040, height: 140 }, 54, 32, 700, lang);
      ctx.save();
      ctx.font = `700 ${fit.fontSize}px ${font}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = theme.colors.text;
      ctx.globalAlpha = pTitle;

      const titleY = centerY - (fit.lines.length - 1) * (fit.lineHeight / 2) - 20;
      fit.lines.forEach((line, idx) => {
        ctx.fillText(line, centerX, titleY + idx * fit.lineHeight);
      });

      // Animated Accent Underline
      if (pUnderline > 0) {
        const underlineWidth = Math.min(600, (ctx.measureText(fit.lines[0] || '').width + 40)) * pUnderline;
        ctx.fillStyle = theme.colors.accent;
        ctx.fillRect(centerX - underlineWidth / 2, titleY + fit.lines.length * fit.lineHeight - 8, underlineWidth, 4);
      }

      // Subtitle (steps[0] or secondary label)
      const subtitle = steps[0] || labels[1] || '';
      if (subtitle && pSubtitle > 0) {
        ctx.globalAlpha = pSubtitle;
        ctx.font = `500 28px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        ctx.fillText(subtitle, centerX, centerY + 80);
      }

      // Additional chips / badges
      const extraChips = labels.slice(1);
      if (extraChips.length > 0 && pSubtitle > 0) {
        ctx.globalAlpha = pSubtitle;
        let startX = centerX - ((extraChips.length - 1) * 160) / 2;
        extraChips.forEach((chip, i) => {
          const chipX = startX + i * 160;
          const chipY = centerY + 140;
          theme.drawRoundedRect(ctx, chipX - 70, chipY - 18, 140, 36, 18, theme.colors.panel, theme.colors.panelBorder);
          ctx.font = `600 18px ${font}`;
          ctx.fillStyle = theme.colors.accent2;
          ctx.fillText(chip, chipX, chipY);
        });
      }
      ctx.restore();
    },

    // 2. BULLETS TEMPLATE
    bullets(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      // Heading top-left
      const heading = labels[0] || 'Key Points';
      const pHeader = theme.easeOutCubic(Math.min(1, lt / 0.5));
      ctx.globalAlpha = pHeader;
      ctx.font = `700 40px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText(heading, 80, 110);

      // Underline
      ctx.fillStyle = theme.colors.accent;
      ctx.fillRect(80, 160, 120 * pHeader, 4);

      // Bullet items
      const startY = 190;
      const rowGap = 74;

      steps.forEach((step, idx) => {
        const itemDelay = 0.15 + idx * 0.18;
        const pItem = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - itemDelay) / 0.5)));
        if (pItem <= 0) return;

        ctx.globalAlpha = pItem;
        const currentY = startY + idx * rowGap;
        const slideOffset = (1 - pItem) * 40;

        // Panel pill
        theme.drawRoundedRect(
          ctx,
          80 + slideOffset,
          currentY,
          1120 - slideOffset,
          60,
          10,
          theme.colors.panel,
          theme.colors.panelBorder
        );

        // Dot indicator
        ctx.beginPath();
        ctx.arc(114 + slideOffset, currentY + 30, 8, 0, Math.PI * 2);
        ctx.fillStyle = idx % 2 === 0 ? theme.colors.accent : theme.colors.accent2;
        ctx.fill();

        // Step text
        ctx.font = `500 24px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textBaseline = 'middle';
        ctx.fillText(step, 144 + slideOffset, currentY + 30);
      });

      ctx.restore();
    },

    // 3. COMPARE TEMPLATE
    compare(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);
      const cols = Math.min(3, Math.max(2, labels.length));

      ctx.save();
      const colWidth = cols === 2 ? 520 : 340;
      const totalWidth = cols * colWidth + (cols - 1) * 30;
      const startX = (1280 - totalWidth) / 2;
      const startY = 130;
      const colHeight = 420;

      for (let i = 0; i < cols; i++) {
        const pCol = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.15) / 0.55)));
        if (pCol <= 0) continue;

        ctx.globalAlpha = pCol;
        const colX = startX + i * (colWidth + 30);
        const colY = startY + (1 - pCol) * 30;

        // Column card
        theme.drawRoundedRect(ctx, colX, colY, colWidth, colHeight, 14, theme.colors.panel, theme.colors.panelBorder);

        // Column header
        const labelText = labels[i] || `Aspect ${i + 1}`;
        const fitHeader = theme.fitText(ctx, labelText, { width: colWidth - 40, height: 70 }, 28, 20, 700, lang);
        ctx.font = `700 ${fitHeader.fontSize}px ${font}`;
        ctx.fillStyle = i === 0 ? theme.colors.accent : i === 1 ? theme.colors.accent2 : theme.colors.good;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        fitHeader.lines.forEach((line, lineIdx) => {
          ctx.fillText(line, colX + colWidth / 2, colY + 24 + lineIdx * fitHeader.lineHeight);
        });

        // Divider
        ctx.fillStyle = theme.colors.panelBorder;
        ctx.fillRect(colX + 20, colY + 110, colWidth - 40, 2);

        // Column content (steps or derived info)
        const stepText = steps[i] || steps[0] || '';
        if (stepText) {
          const fitStep = theme.fitText(ctx, stepText, { width: colWidth - 40, height: 260 }, 22, 16, 500, lang);
          ctx.font = `500 ${fitStep.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';
          fitStep.lines.forEach((line, sIdx) => {
            ctx.fillText(line, colX + 24, colY + 130 + sIdx * fitStep.lineHeight);
          });
        }
      }

      ctx.restore();
    },

    // 4. EQUATION TEMPLATE
    equation(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pFormula = theme.easeOutCubic(Math.min(1, lt / 0.6));
      ctx.globalAlpha = pFormula;

      // Central prominent equation panel
      const formula = labels[0] || 'E = mc²';
      const eqBoxY = 130;
      theme.drawRoundedRect(ctx, 160, eqBoxY, 960, 140, 16, theme.colors.panel, theme.colors.accent, 2);

      // Formula text with subtle pulse
      const pulse = 1 + 0.02 * Math.sin((lt / 1.5) * Math.PI * 2);
      ctx.font = `700 64px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(formula, 640, eqBoxY + 70);

      // Legend items (labels[1..])
      const legendItems = labels.slice(1);
      legendItems.forEach((item, idx) => {
        const pItem = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.2 - idx * 0.15) / 0.5)));
        if (pItem <= 0) return;

        ctx.globalAlpha = pItem;
        const itemY = 300 + idx * 48;
        ctx.font = `600 24px ${font}`;
        ctx.fillStyle = theme.colors.accent2;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText('• ' + item, 200, itemY);
      });

      // Derived steps below
      steps.forEach((step, idx) => {
        const pStep = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.5 - idx * 0.15) / 0.5)));
        if (pStep <= 0) return;

        ctx.globalAlpha = pStep;
        const stepX = 740;
        const stepY = 320 + idx * 60;
        theme.drawRoundedRect(ctx, stepX, stepY - 24, 380, 48, 8, theme.colors.panel, theme.colors.panelBorder);
        ctx.font = `600 22px ${font}`;
        ctx.fillStyle = theme.colors.good;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(step, stepX + 190, stepY);
      });

      ctx.restore();
    },

    // 5. FLOW TEMPLATE
    flow(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const nodeCount = Math.min(4, Math.max(2, labels.length));
      const boxWidth = 220;
      const boxHeight = 110;
      const gap = (960 - nodeCount * boxWidth) / (nodeCount - 1);
      const startX = 160;
      const startY = 220;

      for (let i = 0; i < nodeCount; i++) {
        const pNode = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.18) / 0.5)));
        if (pNode <= 0) continue;

        ctx.globalAlpha = pNode;
        const curX = startX + i * (boxWidth + gap);
        const curY = startY + (1 - pNode) * 20;

        theme.drawRoundedRect(ctx, curX, curY, boxWidth, boxHeight, 12, theme.colors.panel, theme.colors.panelBorder);

        const labelText = labels[i] || `Node ${i + 1}`;
        const fit = theme.fitText(ctx, labelText, { width: boxWidth - 24, height: boxHeight - 24 }, 22, 15, 600, lang);
        ctx.font = `600 ${fit.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const textCenterY = curY + boxHeight / 2 - ((fit.lines.length - 1) * fit.lineHeight) / 2;
        fit.lines.forEach((line, lIdx) => {
          ctx.fillText(line, curX + boxWidth / 2, textCenterY + lIdx * fit.lineHeight);
        });

        // Arrow to next node
        if (i < nodeCount - 1) {
          const pArrow = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - (i * 0.18 + 0.15)) / 0.4)));
          if (pArrow > 0) {
            ctx.globalAlpha = pArrow;
            ctx.fillStyle = theme.colors.accent;
            const arrowStartX = curX + boxWidth + 10;
            const arrowEndX = arrowStartX + (gap - 20) * pArrow;
            ctx.fillRect(arrowStartX, startY + boxHeight / 2 - 2, Math.max(0, arrowEndX - arrowStartX), 4);
          }
        }
      }

      // Steps result strip at bottom
      if (steps[0]) {
        const pResult = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.7) / 0.5)));
        if (pResult > 0) {
          ctx.globalAlpha = pResult;
          theme.drawRoundedRect(ctx, 240, 420, 800, 70, 10, theme.colors.panel, theme.colors.good);
          ctx.font = `600 24px ${font}`;
          ctx.fillStyle = theme.colors.good;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(steps[0], 640, 455);
        }
      }

      ctx.restore();
    },

    // 6. LABELED DIAGRAM, 7. TIMELINE, 8. GRAPH (Graceful implementations for Phase 1)
    labeled_diagram(ctx, params, lt, dur, theme, lang) {
      // Phase 1 implementation uses flow/compare hybrid or degrades safely
      return this.compare(ctx, params, lt, dur, theme, lang);
    },

    timeline(ctx, params, lt, dur, theme, lang) {
      return this.flow(ctx, params, lt, dur, theme, lang);
    },

    graph(ctx, params, lt, dur, theme, lang) {
      return this.bullets(ctx, params, lt, dur, theme, lang);
    },

    // Master draw dispatch with error guard
    draw(ctx, type, params, lt, dur, theme, lang) {
      try {
        const renderer = this[type];
        if (typeof renderer === 'function') {
          renderer.call(this, ctx, params, lt, dur, theme, lang);
        } else {
          // Fallback to bullets for unknown type
          this.bullets(ctx, params, lt, dur, theme, lang);
        }
      } catch (err) {
        console.error(`[Template Error in ${type}]:`, err);
        // Fallback to bullets to never leave canvas blank
        try {
          this.bullets(ctx, params, lt, dur, theme, lang);
        } catch (innerErr) {
          // Last resort: simple title fill
          ctx.fillStyle = theme.colors.text;
          ctx.font = '24px sans-serif';
          ctx.fillText('Visual rendering error', 100, 200);
        }
      }
    }
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = TEMPLATES;
  } else {
    root.TEMPLATES = TEMPLATES;
  }
})(typeof window !== 'undefined' ? window : globalThis);
