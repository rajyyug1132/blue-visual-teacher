// renderer/templates.js
// Visual templates for lesson rendering with deterministic animations and graceful fallbacks.

(function (root) {
  const TEMPLATES = {
    // 1. TITLE TEMPLATE
    title(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      // Intro animation progress (staggered, completed by dur * 0.5, with minimum base visibility to avoid blank frames)
      const pTitle = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.6)));
      const pSubtitle = Math.max(0.15, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.25) / 0.6))));
      const pUnderline = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.4) / 0.7)));

      const centerX = 1280 / 2;
      const centerY = 300;

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
        const textWidth = ctx.measureText(fit.lines[0] || '').width;
        const underlineWidth = Math.min(640, textWidth + 40) * pUnderline;
        ctx.fillStyle = theme.colors.accent;
        ctx.fillRect(centerX - underlineWidth / 2, titleY + fit.lines.length * fit.lineHeight - 6, underlineWidth, 4);
      }

      // Subtitle (steps[0] or secondary label)
      const subtitle = steps[0] || labels[1] || '';
      if (subtitle && pSubtitle > 0) {
        ctx.globalAlpha = pSubtitle;
        const fitSub = theme.fitText(ctx, subtitle, { width: 1000, height: 60 }, 28, 20, 500, lang);
        ctx.font = `500 ${fitSub.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        fitSub.lines.forEach((line, idx) => {
          ctx.fillText(line, centerX, centerY + 76 + idx * fitSub.lineHeight);
        });
      }

      // Additional chips / badges
      const extraChips = labels.slice(1);
      if (extraChips.length > 0 && pSubtitle > 0) {
        ctx.globalAlpha = pSubtitle;
        const chipCount = Math.min(4, extraChips.length);
        const gap = 20;
        ctx.font = `600 17px ${font}`;
        const chipWidths = [];
        for (let i = 0; i < chipCount; i++) {
          const w = ctx.measureText(extraChips[i]).width + 44;
          chipWidths.push(Math.min(340, Math.max(160, w)));
        }
        const totalChipW = chipWidths.reduce((a, b) => a + b, 0) + (chipCount - 1) * gap;
        let curChipX = centerX - totalChipW / 2;

        for (let i = 0; i < chipCount; i++) {
          const chipW = chipWidths[i];
          const chipY = centerY + 144;
          theme.drawRoundedRect(ctx, curChipX, chipY, chipW, 40, 20, theme.colors.panel, theme.colors.panelBorder);

          const fitChip = theme.fitText(ctx, extraChips[i], { width: chipW - 24, height: 32 }, 18, 14, 600, lang);
          ctx.font = `600 ${fitChip.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.accent2;
          ctx.fillText(fitChip.lines[0] || extraChips[i], curChipX + chipW / 2, chipY + 20);
          curChipX += chipW + gap;
        }
      }
      ctx.restore();
    },

    // 2. BULLETS TEMPLATE
    bullets(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      // Heading top-left (with base presence)
      const heading = labels[0] || 'Key Points';
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pHeader;

      const fitHeading = theme.fitText(ctx, heading, { width: 1120, height: 50 }, 40, 28, 700, lang);
      ctx.font = `700 ${fitHeading.fontSize}px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText(fitHeading.lines[0] || heading, 80, 106);

      // Underline
      ctx.fillStyle = theme.colors.accent;
      const headWidth = Math.min(300, ctx.measureText(fitHeading.lines[0] || heading).width + 20);
      ctx.fillRect(80, 156, headWidth * pHeader, 4);

      // Bullet items
      const startY = 184;
      const stepCount = Math.min(5, steps.length);
      const rowGap = stepCount > 4 ? 66 : 74;
      const cardHeight = stepCount > 4 ? 54 : 60;

      for (let idx = 0; idx < stepCount; idx++) {
        const step = steps[idx];
        const itemDelay = 0.15 + idx * 0.18;
        const pItem = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - itemDelay) / 0.5)));
        if (pItem <= 0) continue;

        ctx.globalAlpha = pItem;
        const currentY = startY + idx * rowGap;
        const slideOffset = (1 - pItem) * 40;
        const cardWidth = 1120 - slideOffset;

        // Panel pill
        theme.drawRoundedRect(
          ctx,
          80 + slideOffset,
          currentY,
          cardWidth,
          cardHeight,
          10,
          theme.colors.panel,
          theme.colors.panelBorder
        );

        // Dot indicator
        ctx.beginPath();
        ctx.arc(114 + slideOffset, currentY + cardHeight / 2, 7, 0, Math.PI * 2);
        ctx.fillStyle = idx % 2 === 0 ? theme.colors.accent : theme.colors.accent2;
        ctx.fill();

        // Step text fitting (prevents overflow off the 1280 canvas)
        const textBoxWidth = cardWidth - 80;
        const fitStep = theme.fitText(ctx, step, { width: textBoxWidth, height: cardHeight - 12 }, 24, 16, 500, lang);
        ctx.font = `500 ${fitStep.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';

        if (fitStep.lines.length === 1) {
          ctx.fillText(fitStep.lines[0], 144 + slideOffset, currentY + cardHeight / 2);
        } else {
          const lHeight = fitStep.lineHeight;
          const textStartY = currentY + (cardHeight / 2) - ((fitStep.lines.length - 1) * lHeight / 2);
          fitStep.lines.forEach((line, lIdx) => {
            ctx.fillText(line, 144 + slideOffset, textStartY + lIdx * lHeight);
          });
        }
      }

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
      const gap = cols === 2 ? 40 : 24;
      const totalWidth = cols * colWidth + (cols - 1) * gap;
      const startX = (1280 - totalWidth) / 2;
      const startY = 120;
      const colHeight = 440;

      for (let i = 0; i < cols; i++) {
        const pCol = Math.max(i === 0 ? 0.25 : 0, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.15) / 0.55))));
        if (pCol <= 0) continue;

        ctx.globalAlpha = pCol;
        const colX = startX + i * (colWidth + gap);
        const colY = startY + (1 - pCol) * 26;

        // Column card
        theme.drawRoundedRect(ctx, colX, colY, colWidth, colHeight, 14, theme.colors.panel, theme.colors.panelBorder);

        // Column header
        const labelText = labels[i] || `Aspect ${i + 1}`;
        const fitHeader = theme.fitText(ctx, labelText, { width: colWidth - 36, height: 74 }, 26, 18, 700, lang);
        ctx.font = `700 ${fitHeader.fontSize}px ${font}`;
        ctx.fillStyle = i === 0 ? theme.colors.accent : i === 1 ? theme.colors.accent2 : theme.colors.good;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        const headerStartY = colY + 20;
        fitHeader.lines.forEach((line, lineIdx) => {
          ctx.fillText(line, colX + colWidth / 2, headerStartY + lineIdx * fitHeader.lineHeight);
        });

        // Divider
        const dividerY = headerStartY + fitHeader.lines.length * fitHeader.lineHeight + 14;
        ctx.fillStyle = theme.colors.panelBorder;
        ctx.fillRect(colX + 20, dividerY, colWidth - 40, 2);

        // Column content (only render steps[i] if it specifically exists for this column)
        const stepText = (i < steps.length) ? steps[i] : '';
        if (stepText) {
          const fitStep = theme.fitText(ctx, stepText, { width: colWidth - 40, height: colHeight - (dividerY - colY) - 30 }, 22, 16, 500, lang);
          ctx.font = `500 ${fitStep.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';
          fitStep.lines.forEach((line, sIdx) => {
            ctx.fillText(line, colX + 24, dividerY + 18 + sIdx * fitStep.lineHeight);
          });
        }

        // Draw "vs" badge between columns
        if (i < cols - 1) {
          const badgeX = colX + colWidth + gap / 2;
          const badgeY = colY + colHeight / 2;
          ctx.fillStyle = theme.colors.panel;
          ctx.beginPath();
          ctx.arc(badgeX, badgeY, 16, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = theme.colors.accent;
          ctx.lineWidth = 2;
          ctx.stroke();

          ctx.font = `700 13px ${font}`;
          ctx.fillStyle = theme.colors.accent;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText('VS', badgeX, badgeY);
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
      const pFormula = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.6)));
      ctx.globalAlpha = pFormula;

      // Central prominent equation panel
      const formula = labels[0] || 'V = I × R';
      const eqBoxY = 120;
      theme.drawRoundedRect(ctx, 160, eqBoxY, 960, 130, 16, theme.colors.panel, theme.colors.accent, 2);

      // Formula text with subtle deterministic pulse
      const pulse = 1 + 0.015 * Math.sin((lt / 1.5) * Math.PI * 2);
      const fitEq = theme.fitText(ctx, formula, { width: 900, height: 90 }, 62, 34, 700, lang);
      const pulseSize = Math.round(fitEq.fontSize * pulse);

      ctx.font = `700 ${pulseSize}px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(fitEq.lines[0] || formula, 640, eqBoxY + 65);

      // Legend items (labels[1..])
      const legendItems = labels.slice(1);
      legendItems.forEach((item, idx) => {
        const pItem = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.2 - idx * 0.15) / 0.5)));
        if (pItem <= 0) return;

        ctx.globalAlpha = pItem;
        const itemY = 285 + idx * 46;
        const fitLegend = theme.fitText(ctx, '• ' + item, { width: 480, height: 40 }, 22, 16, 600, lang);
        ctx.font = `600 ${fitLegend.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.accent2;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(fitLegend.lines[0] || item, 180, itemY);
      });

      // Derived steps on right side
      steps.forEach((step, idx) => {
        const pStep = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.45 - idx * 0.15) / 0.5)));
        if (pStep <= 0) return;

        ctx.globalAlpha = pStep;
        const stepX = 720;
        const stepY = 295 + idx * 56;
        const stepWidth = 400;
        const stepHeight = 46;

        theme.drawRoundedRect(ctx, stepX, stepY - stepHeight / 2, stepWidth, stepHeight, 8, theme.colors.panel, theme.colors.panelBorder);
        const fitStep = theme.fitText(ctx, step, { width: stepWidth - 24, height: stepHeight - 10 }, 22, 15, 600, lang);
        ctx.font = `600 ${fitStep.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.good;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(fitStep.lines[0] || step, stepX + stepWidth / 2, stepY);
      });

      ctx.restore();
    },

    // 5. FLOW TEMPLATE
    flow(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const nodeCount = Math.min(6, Math.max(2, labels.length));

      // Determine single-row vs 2-row layout
      const isTwoRows = nodeCount > 4;
      const topCount = isTwoRows ? Math.ceil(nodeCount / 2) : nodeCount;
      const botCount = isTwoRows ? (nodeCount - topCount) : 0;

      const boxWidth = isTwoRows ? 240 : (nodeCount === 4 ? 220 : 250);
      const boxHeight = 100;
      const rowGap = isTwoRows ? 70 : 0;
      const startY = isTwoRows ? 150 : 220;

      function drawNodeRow(startIndex, count, yPos) {
        const gap = (1000 - count * boxWidth) / Math.max(1, count - 1);
        const startX = 140;

        for (let i = 0; i < count; i++) {
          const globalIdx = startIndex + i;
          const pNode = Math.max(globalIdx === 0 ? 0.25 : 0, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - globalIdx * 0.15) / 0.5))));
          if (pNode <= 0) continue;

          ctx.globalAlpha = pNode;
          const curX = startX + i * (boxWidth + gap);
          const curY = yPos + (1 - pNode) * 18;

          theme.drawRoundedRect(ctx, curX, curY, boxWidth, boxHeight, 12, theme.colors.panel, theme.colors.panelBorder);

          const labelText = labels[globalIdx] || `Node ${globalIdx + 1}`;
          const fit = theme.fitText(ctx, labelText, { width: boxWidth - 20, height: boxHeight - 20 }, 22, 14, 600, lang);
          ctx.font = `600 ${fit.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';

          const textCenterY = curY + boxHeight / 2 - ((fit.lines.length - 1) * fit.lineHeight) / 2;
          fit.lines.forEach((line, lIdx) => {
            ctx.fillText(line, curX + boxWidth / 2, textCenterY + lIdx * fit.lineHeight);
          });

          // Draw connector arrow with arrowhead to next node in row
          if (i < count - 1) {
            const pArrow = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - (globalIdx * 0.15 + 0.12)) / 0.4)));
            if (pArrow > 0) {
              ctx.globalAlpha = pArrow;
              ctx.fillStyle = theme.colors.accent;
              const arrowStartX = curX + boxWidth + 8;
              const fullArrowLen = gap - 16;
              const arrowEndX = arrowStartX + fullArrowLen * pArrow;
              const midY = curY + boxHeight / 2;

              // Line
              ctx.fillRect(arrowStartX, midY - 2, Math.max(0, arrowEndX - arrowStartX), 4);

              // Arrowhead
              if (pArrow > 0.4 && typeof ctx.lineTo === 'function') {
                ctx.beginPath();
                ctx.moveTo(arrowEndX, midY);
                ctx.lineTo(arrowEndX - 10, midY - 6);
                ctx.lineTo(arrowEndX - 10, midY + 6);
                ctx.closePath();
                ctx.fill();
              }
            }
          }
        }
      }

      drawNodeRow(0, topCount, startY);
      if (isTwoRows) {
        drawNodeRow(topCount, botCount, startY + boxHeight + rowGap);
      }

      // Steps result strip at bottom
      if (steps[0]) {
        const pResult = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.7) / 0.5)));
        if (pResult > 0) {
          ctx.globalAlpha = pResult;
          const stripY = isTwoRows ? 460 : 410;
          theme.drawRoundedRect(ctx, 200, stripY, 880, 64, 10, theme.colors.panel, theme.colors.good);

          const fitRes = theme.fitText(ctx, steps[0], { width: 840, height: 48 }, 24, 16, 600, lang);
          ctx.font = `600 ${fitRes.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.good;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(fitRes.lines[0] || steps[0], 640, stripY + 32);
        }
      }

      ctx.restore();
    },

    // 6. LABELED DIAGRAM TEMPLATE
    // Central concept with peripheral callouts connected by leader lines, plus bottom summary chips
    labeled_diagram(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pCenter = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pCenter;

      const centerX = 640;
      const centerY = 240;
      const centerW = 280;
      const centerH = 100;

      // 1. Central Core System Card
      theme.drawRoundedRect(
        ctx,
        centerX - centerW / 2,
        centerY - centerH / 2,
        centerW,
        centerH,
        16,
        theme.colors.panel,
        theme.colors.accent,
        2
      );

      const mainLabel = labels[0] || 'System Diagram';
      const fitCenter = theme.fitText(ctx, mainLabel, { width: centerW - 28, height: centerH - 20 }, 26, 17, 700, lang);
      ctx.font = `700 ${fitCenter.fontSize}px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      const centerTextStartY = centerY - ((fitCenter.lines.length - 1) * fitCenter.lineHeight) / 2;
      fitCenter.lines.forEach((line, idx) => {
        ctx.fillText(line, centerX, centerTextStartY + idx * fitCenter.lineHeight);
      });

      // 2. Peripheral Callout Nodes (labels[1..])
      const calloutLabels = labels.slice(1);
      const calloutCount = Math.min(5, calloutLabels.length);

      // Predefined balanced anchor coordinates for up to 5 callout positions
      const layoutPositions = [
        // 1 callout: Right
        [{ x: 920, y: 240, ax: centerX + centerW / 2, ay: centerY }],
        // 2 callouts: Left, Right
        [
          { x: 180, y: 240, ax: centerX - centerW / 2, ay: centerY },
          { x: 860, y: 240, ax: centerX + centerW / 2, ay: centerY }
        ],
        // 3 callouts: Left, Top, Right
        [
          { x: 180, y: 240, ax: centerX - centerW / 2, ay: centerY },
          { x: 520, y: 110, ax: centerX, ay: centerY - centerH / 2 },
          { x: 860, y: 240, ax: centerX + centerW / 2, ay: centerY }
        ],
        // 4 callouts: Quadrants
        [
          { x: 180, y: 140, ax: centerX - centerW / 2, ay: centerY - 25 },
          { x: 860, y: 140, ax: centerX + centerW / 2, ay: centerY - 25 },
          { x: 180, y: 340, ax: centerX - centerW / 2, ay: centerY + 25 },
          { x: 860, y: 340, ax: centerX + centerW / 2, ay: centerY + 25 }
        ],
        // 5 callouts: Top-L, Top, Top-R, Bottom-L, Bottom-R
        [
          { x: 180, y: 130, ax: centerX - centerW / 2, ay: centerY - 25 },
          { x: 520, y: 100, ax: centerX, ay: centerY - centerH / 2 },
          { x: 860, y: 130, ax: centerX + centerW / 2, ay: centerY - 25 },
          { x: 180, y: 340, ax: centerX - centerW / 2, ay: centerY + 25 },
          { x: 860, y: 340, ax: centerX + centerW / 2, ay: centerY + 25 }
        ]
      ];

      const activeLayout = calloutCount > 0 ? layoutPositions[calloutCount - 1] : [];
      const calloutW = 240;
      const calloutH = 56;

      for (let i = 0; i < calloutCount; i++) {
        const pos = activeLayout[i];
        const pCallout = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - (0.2 + i * 0.12)) / 0.45)));
        if (pCallout <= 0) continue;

        ctx.globalAlpha = pCallout;

        // Draw leader line from center anchor to callout edge
        const isTopNode = (pos.x < centerX && (pos.x + calloutW) > centerX);
        const calloutEdgeX = isTopNode ? centerX : (pos.x > centerX ? pos.x : pos.x + calloutW);
        const calloutEdgeY = isTopNode ? (pos.y + calloutH) : (pos.y + calloutH / 2);

        ctx.strokeStyle = theme.colors.accent2;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(pos.ax, pos.ay);
        const curLineX = pos.ax + (calloutEdgeX - pos.ax) * pCallout;
        const curLineY = pos.ay + (calloutEdgeY - pos.ay) * pCallout;
        ctx.lineTo(curLineX, curLineY);
        ctx.stroke();

        // Terminal anchor dot
        ctx.fillStyle = theme.colors.accent2;
        ctx.beginPath();
        ctx.arc(pos.ax, pos.ay, 4, 0, Math.PI * 2);
        ctx.fill();

        // Callout card
        theme.drawRoundedRect(ctx, pos.x, pos.y, calloutW, calloutH, 10, theme.colors.panel, theme.colors.panelBorder);

        const fitLabel = theme.fitText(ctx, calloutLabels[i], { width: calloutW - 20, height: calloutH - 12 }, 19, 14, 600, lang);
        ctx.font = `600 ${fitLabel.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.accent2;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(fitLabel.lines[0] || calloutLabels[i], pos.x + calloutW / 2, pos.y + calloutH / 2);
      }

      // 3. Bottom Numbered Step Chips
      if (steps.length > 0) {
        const stepCount = Math.min(4, steps.length);
        const pStepBlock = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.5) / 0.5)));
        if (pStepBlock > 0) {
          ctx.globalAlpha = pStepBlock;
          const chipW = Math.min(270, (1120 - (stepCount - 1) * 20) / stepCount);
          const totalChipsW = stepCount * chipW + (stepCount - 1) * 20;
          const startChipX = (1280 - totalChipsW) / 2;
          const chipY = 460;
          const chipH = 50;

          for (let sIdx = 0; sIdx < stepCount; sIdx++) {
            const curChipX = startChipX + sIdx * (chipW + 20);
            theme.drawRoundedRect(ctx, curChipX, chipY, chipW, chipH, 8, theme.colors.panel, theme.colors.panelBorder);

            // Number badge
            ctx.fillStyle = theme.colors.accent;
            ctx.beginPath();
            ctx.arc(curChipX + 22, chipY + chipH / 2, 12, 0, Math.PI * 2);
            ctx.fill();

            ctx.font = `700 13px ${font}`;
            ctx.fillStyle = theme.colors.bg;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(String(sIdx + 1), curChipX + 22, chipY + chipH / 2);

            // Step text
            const fitChip = theme.fitText(ctx, steps[sIdx], { width: chipW - 48, height: chipH - 10 }, 17, 13, 500, lang);
            ctx.font = `500 ${fitChip.fontSize}px ${font}`;
            ctx.fillStyle = theme.colors.text;
            ctx.textAlign = 'left';
            ctx.fillText(fitChip.lines[0] || steps[sIdx], curChipX + 42, chipY + chipH / 2);
          }
        }
      }

      ctx.restore();
    },

    // 7. TIMELINE TEMPLATE
    // Horizontal chronological progression with milestone nodes, labels above, and steps below
    timeline(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const nodeCount = Math.min(6, Math.max(1, labels.length));
      const startX = 140;
      const endX = 1140;
      const timelineY = 290;

      // Track progress line animated over the scene duration
      const effectiveDur = Math.max(0.5, dur * 0.75);
      const pTimeline = theme.easeOutCubic(Math.min(1, lt / effectiveDur));

      // Draw base track
      ctx.fillStyle = theme.colors.progressTrack;
      ctx.fillRect(startX, timelineY - 3, endX - startX, 6);

      // Draw active progress fill line
      const activeLineW = (endX - startX) * pTimeline;
      ctx.fillStyle = theme.colors.accent;
      ctx.fillRect(startX, timelineY - 3, activeLineW, 6);

      // Draw moving glow marker
      const markerX = startX + activeLineW;
      ctx.fillStyle = theme.colors.accent2;
      ctx.beginPath();
      ctx.arc(markerX, timelineY, 8, 0, Math.PI * 2);
      ctx.fill();

      // Nodes spacing
      const spacing = nodeCount === 1 ? 0 : (endX - startX) / (nodeCount - 1);
      const cardWidth = Math.min(190, nodeCount > 4 ? 160 : 200);

      for (let i = 0; i < nodeCount; i++) {
        const nodeX = nodeCount === 1 ? 640 : startX + i * spacing;
        const nodeFrac = nodeCount === 1 ? 0.1 : i / (nodeCount - 1);
        const nodeDelay = 0.1 + nodeFrac * 0.45;
        const pNode = Math.max(i === 0 ? 0.25 : 0, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - nodeDelay) / 0.4))));
        if (pNode <= 0) continue;

        ctx.globalAlpha = pNode;
        const isReached = pTimeline >= (nodeCount === 1 ? 0.5 : nodeFrac);

        // Vertical tick connector to top card
        ctx.strokeStyle = isReached ? theme.colors.accent : theme.colors.panelBorder;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(nodeX, timelineY - 14);
        ctx.lineTo(nodeX, timelineY - 45);
        ctx.stroke();

        // Milestone Node Circle
        ctx.fillStyle = isReached ? theme.colors.accent : theme.colors.panel;
        ctx.beginPath();
        ctx.arc(nodeX, timelineY, 15, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = isReached ? theme.colors.text : theme.colors.panelBorder;
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.font = `700 14px ${font}`;
        ctx.fillStyle = isReached ? theme.colors.bg : theme.colors.muted;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(i + 1), nodeX, timelineY);

        // Top Card: Stage Label (labels[i])
        const topCardH = 68;
        const topCardY = timelineY - 45 - topCardH;
        theme.drawRoundedRect(
          ctx,
          nodeX - cardWidth / 2,
          topCardY,
          cardWidth,
          topCardH,
          10,
          theme.colors.panel,
          isReached ? theme.colors.accent : theme.colors.panelBorder
        );

        const stageLabel = labels[i] || `Stage ${i + 1}`;
        const fitLabel = theme.fitText(ctx, stageLabel, { width: cardWidth - 16, height: topCardH - 14 }, 18, 13, 600, lang);
        ctx.font = `600 ${fitLabel.fontSize}px ${font}`;
        ctx.fillStyle = isReached ? theme.colors.text : theme.colors.muted;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const labelStartY = topCardY + topCardH / 2 - ((fitLabel.lines.length - 1) * fitLabel.lineHeight) / 2;
        fitLabel.lines.forEach((line, lIdx) => {
          ctx.fillText(line, nodeX, labelStartY + lIdx * fitLabel.lineHeight);
        });

        // Bottom Card: Step Detail (steps[i] if available)
        const stepText = (i < steps.length) ? steps[i] : '';
        if (stepText) {
          // Vertical tick connector to bottom card
          ctx.strokeStyle = isReached ? theme.colors.good : theme.colors.panelBorder;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(nodeX, timelineY + 14);
          ctx.lineTo(nodeX, timelineY + 45);
          ctx.stroke();

          const botCardH = 74;
          const botCardY = timelineY + 45;
          theme.drawRoundedRect(
            ctx,
            nodeX - cardWidth / 2,
            botCardY,
            cardWidth,
            botCardH,
            10,
            theme.colors.panel,
            theme.colors.panelBorder
          );

          const fitStep = theme.fitText(ctx, stepText, { width: cardWidth - 18, height: botCardH - 14 }, 16, 12, 500, lang);
          ctx.font = `500 ${fitStep.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.muted;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';

          const stepStartY = botCardY + botCardH / 2 - ((fitStep.lines.length - 1) * fitStep.lineHeight) / 2;
          fitStep.lines.forEach((line, sIdx) => {
            ctx.fillText(line, nodeX, stepStartY + sIdx * fitStep.lineHeight);
          });
        }
      }

      ctx.restore();
    },

    // 8. GRAPH TEMPLATE
    // Calibrated bar chart ONLY for unambiguously structured numeric data (e.g. "Category: 12").
    // When numeric data is absent or ambiguous, renders a clean conceptual parameter framework
    // without fabricating unverified curves, trends, or numerical values.
    graph(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pAnim = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / Math.max(0.6, dur * 0.7))));
      ctx.globalAlpha = pAnim;

      // Strict parser: only unambiguous "Category: Value [units]" or "Category = Value"
      // Rejects prose sentences, multi-clause text, or random numbers in running paragraphs.
      function parseStructuredNumericDataset(inputSteps) {
        if (!Array.isArray(inputSteps) || inputSteps.length < 2) return null;
        const parsed = [];
        for (const step of inputSteps) {
          const trimmed = String(step || '').trim();
          // Reject full prose sentences (more than 5 words before the number)
          if (trimmed.split(/\s+/).length > 6) return null;
          // Match strict "Label : Value" or "Label = Value" with optional unit at end
          const m = trimmed.match(/^([A-Za-z0-9\s\-]+?)\s*[:=]\s*(-?\d+(?:\.\d+)?)\s*([A-Za-zΩ%°\/\^]*)$/);
          if (!m) return null;
          const name = m[1].trim();
          const val = parseFloat(m[2]);
          const unit = m[3] ? m[3].trim() : '';
          if (!name || isNaN(val)) return null;
          parsed.push({ name, val, unit });
        }
        return parsed.length >= 2 ? parsed : null;
      }

      const numericDataset = parseStructuredNumericDataset(steps);

      // Axis labels
      const xLabel = labels[0] || 'Parameter (X)';
      const yLabel = labels[1] || 'Parameter (Y)';

      // ---------------------------------------------------------------
      // CASE A: Unambiguous Structured Numeric Data Available (Bar Chart)
      // ---------------------------------------------------------------
      if (numericDataset) {
        const originX = 180;
        const originY = 480;
        const plotWidth = 740;
        const plotHeight = 320;
        const topY = originY - plotHeight;
        const rightX = originX + plotWidth;

        // Subtle horizontal gridlines
        ctx.strokeStyle = theme.colors.panelBorder;
        ctx.lineWidth = 1;
        for (let g = 1; g <= 4; g++) {
          const gridY = originY - (plotHeight / 4) * g;
          ctx.beginPath();
          ctx.moveTo(originX, gridY);
          ctx.lineTo(rightX, gridY);
          ctx.stroke();
        }

        // Draw Axes
        ctx.strokeStyle = theme.colors.muted;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(originX, topY - 10);
        ctx.lineTo(originX, originY);
        ctx.lineTo(rightX + 20, originY);
        ctx.stroke();

        // Axis Arrowheads
        if (typeof ctx.lineTo === 'function') {
          ctx.fillStyle = theme.colors.muted;
          // Y-axis arrow
          ctx.beginPath();
          ctx.moveTo(originX, topY - 14);
          ctx.lineTo(originX - 5, topY - 2);
          ctx.lineTo(originX + 5, topY - 2);
          ctx.closePath();
          ctx.fill();

          // X-axis arrow
          ctx.beginPath();
          ctx.moveTo(rightX + 26, originY);
          ctx.lineTo(rightX + 14, originY - 5);
          ctx.lineTo(rightX + 14, originY + 5);
          ctx.closePath();
          ctx.fill();
        }

        // Axis Labels
        const fitX = theme.fitText(ctx, xLabel, { width: 440, height: 40 }, 22, 15, 600, lang);
        ctx.font = `600 ${fitX.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(fitX.lines[0] || xLabel, originX + plotWidth / 2, originY + 22);

        const fitY = theme.fitText(ctx, yLabel, { width: 360, height: 40 }, 22, 15, 600, lang);
        ctx.font = `600 ${fitY.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'bottom';
        ctx.fillText(fitY.lines[0] || yLabel, originX, topY - 20);

        // Bars
        const maxVal = Math.max(...numericDataset.map(p => p.val), 1);
        const count = numericDataset.length;
        const barSlotWidth = plotWidth / count;
        const barWidth = Math.min(90, barSlotWidth * 0.6);

        numericDataset.forEach((pt, pIdx) => {
          const barH = (pt.val / maxVal) * (plotHeight - 40) * pAnim;
          const barX = originX + pIdx * barSlotWidth + (barSlotWidth - barWidth) / 2;
          const barY = originY - barH;

          // Bar Rectangle
          const barColor = pIdx % 2 === 0 ? theme.colors.accent : theme.colors.accent2;
          theme.drawRoundedRect(ctx, barX, barY, barWidth, Math.max(2, barH), 6, barColor);

          // Bar Value
          if (pAnim > 0.4) {
            ctx.font = `700 16px ${font}`;
            ctx.fillStyle = theme.colors.text;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            const valueText = pt.unit ? `${pt.val} ${pt.unit}` : String(pt.val);
            ctx.fillText(valueText, barX + barWidth / 2, barY - 6);
          }

          // Bar Label on X Axis
          const fitBarLabel = theme.fitText(ctx, pt.name, { width: barSlotWidth - 8, height: 32 }, 15, 12, 500, lang);
          ctx.font = `500 ${fitBarLabel.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.muted;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillText(fitBarLabel.lines[0] || pt.name, barX + barWidth / 2, originY + 6);
        });

      } else {
        // ---------------------------------------------------------------
        // CASE B: Conceptual / Explanatory Visual (No Arbitrary Trend Curve)
        // ---------------------------------------------------------------
        // Renders parameter axes defining the concept space, accompanied by
        // structured explanatory principle cards derived from the lesson steps.
        const originX = 140;
        const originY = 510;
        const plotWidth = 980;
        const plotHeight = 360;
        const topY = originY - plotHeight;
        const rightX = originX + plotWidth;

        // Subtle coordinate quadrant grid
        ctx.strokeStyle = theme.colors.panelBorder;
        ctx.lineWidth = 1;
        for (let g = 1; g <= 3; g++) {
          const gridY = originY - (plotHeight / 3) * g;
          ctx.beginPath();
          ctx.moveTo(originX, gridY);
          ctx.lineTo(rightX, gridY);
          ctx.stroke();
        }

        // Parameter Axes
        ctx.strokeStyle = theme.colors.muted;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(originX, topY - 10);
        ctx.lineTo(originX, originY);
        ctx.lineTo(rightX + 20, originY);
        ctx.stroke();

        // Arrowheads
        if (typeof ctx.lineTo === 'function') {
          ctx.fillStyle = theme.colors.muted;
          // Y-axis arrow
          ctx.beginPath();
          ctx.moveTo(originX, topY - 14);
          ctx.lineTo(originX - 5, topY - 2);
          ctx.lineTo(originX + 5, topY - 2);
          ctx.closePath();
          ctx.fill();

          // X-axis arrow
          ctx.beginPath();
          ctx.moveTo(rightX + 26, originY);
          ctx.lineTo(rightX + 14, originY - 5);
          ctx.lineTo(rightX + 14, originY + 5);
          ctx.closePath();
          ctx.fill();
        }

        // Axis Parameter Labels
        const fitX = theme.fitText(ctx, xLabel, { width: 500, height: 36 }, 22, 15, 600, lang);
        ctx.font = `600 ${fitX.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(fitX.lines[0] || xLabel, originX + plotWidth / 2, originY + 16);

        const fitY = theme.fitText(ctx, yLabel, { width: 400, height: 36 }, 22, 15, 600, lang);
        ctx.font = `600 ${fitY.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'bottom';
        ctx.fillText(fitY.lines[0] || yLabel, originX, topY - 16);

        // Header Badge: Explicitly stating this is a Conceptual Analysis (not empirical curve)
        const badgeW = 220;
        const badgeH = 34;
        const badgeX = rightX - badgeW;
        const badgeY = topY - 10;
        theme.drawRoundedRect(ctx, badgeX, badgeY, badgeW, badgeH, 6, theme.colors.panel, theme.colors.panelBorder);
        ctx.font = `700 12px ${font}`;
        ctx.fillStyle = theme.colors.accent2;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('CONCEPTUAL ANALYSIS', badgeX + badgeW / 2, badgeY + badgeH / 2);

        // Render Explanatory Step Cards inside the quadrant
        // Displays the actual lesson steps without fabricating mathematical functions
        const stepItems = steps.length > 0 ? steps : [`Relationship between ${xLabel} and ${yLabel}`];
        const cardCount = Math.min(3, stepItems.length);
        const cardW = 860;
        const cardH = cardCount === 1 ? 120 : (cardCount === 2 ? 80 : 64);
        const cardGap = 16;
        const totalCardsH = cardCount * cardH + (cardCount - 1) * cardGap;
        const startCardsY = originY - (plotHeight / 2) - (totalCardsH / 2) + 10;
        const cardX = originX + 50;

        for (let sIdx = 0; sIdx < cardCount; sIdx++) {
          const pCard = theme.easeOutCubic(Math.max(0, Math.min(1, (lt - (0.15 + sIdx * 0.18)) / 0.5)));
          if (pCard <= 0) continue;

          ctx.globalAlpha = pCard;
          const curCardY = startCardsY + sIdx * (cardH + cardGap);

          // Card Background
          theme.drawRoundedRect(
            ctx,
            cardX,
            curCardY,
            cardW,
            cardH,
            10,
            theme.colors.panel,
            sIdx === 0 ? theme.colors.accent : theme.colors.panelBorder
          );

          // Left indicator badge / bullet
          ctx.fillStyle = sIdx === 0 ? theme.colors.accent : theme.colors.good;
          ctx.beginPath();
          ctx.arc(cardX + 24, curCardY + cardH / 2, 7, 0, Math.PI * 2);
          ctx.fill();

          // Card Text fitted to boundaries
          const textMaxW = cardW - 64;
          const fitTextItem = theme.fitText(ctx, stepItems[sIdx], { width: textMaxW, height: cardH - 16 }, 20, 14, 500, lang);
          ctx.font = `500 ${fitTextItem.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';

          const cardTextStartY = curCardY + (cardH / 2) - ((fitTextItem.lines.length - 1) * fitTextItem.lineHeight / 2);
          fitTextItem.lines.forEach((line, lIdx) => {
            ctx.fillText(line, cardX + 44, cardTextStartY + lIdx * fitTextItem.lineHeight);
          });
        }
      }

      ctx.restore();
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
        try {
          this.bullets(ctx, params, lt, dur, theme, lang);
        } catch (innerErr) {
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
