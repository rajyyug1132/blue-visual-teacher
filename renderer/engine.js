// renderer/engine.js
// Core deterministic rendering engine exposing the frozen window API:
// - window.initLesson(title, scenes, lang)
// - window.renderAtTime(t_sec)
// - window.totalDuration
// - window.ready

(function (root) {
  let _canvas = null;
  let _ctx = null;
  let _title = '';
  let _scenes = [];
  let _lang = 'en';
  let _totalDuration = 0;
  let _theme = null;
  let _templates = null;

  function getTheme() {
    if (!_theme) {
      _theme = (typeof root.THEME !== 'undefined') ? root.THEME : (typeof require !== 'undefined' ? require('./theme') : null);
    }
    return _theme;
  }

  function getTemplates() {
    if (!_templates) {
      _templates = (typeof root.TEMPLATES !== 'undefined') ? root.TEMPLATES : (typeof require !== 'undefined' ? require('./templates') : null);
    }
    return _templates;
  }

  // Pure function to find the active scene for a timestamp
  function getActiveScene(scenes, t) {
    if (!scenes || scenes.length === 0) return null;
    if (t <= scenes[0].start_sec) return scenes[0];
    const last = scenes[scenes.length - 1];
    if (t >= last.end_sec) return last;

    for (let i = 0; i < scenes.length; i++) {
      if (t >= scenes[i].start_sec && t < scenes[i].end_sec) {
        return scenes[i];
      }
    }
    return last;
  }

  // Draw header bar
  function drawHeader(ctx, title, sceneIndex, totalScenes, theme, lang) {
    const font = theme.getFont(lang);
    ctx.save();
    // Top bar background
    ctx.fillStyle = theme.colors.bg;
    ctx.fillRect(0, 0, 1280, theme.safeArea.headerHeight);

    // Bottom border line
    ctx.fillStyle = theme.colors.panelBorder;
    ctx.fillRect(64, theme.safeArea.headerHeight - 2, 1152, 2);

    // Title left
    ctx.font = `600 22px ${font}`;
    ctx.fillStyle = theme.colors.muted;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const truncatedTitle = title.length > 60 ? title.substring(0, 57) + '...' : title;
    ctx.fillText(truncatedTitle, 64, theme.safeArea.headerHeight / 2);

    // Scene counter right
    ctx.textAlign = 'right';
    ctx.fillStyle = theme.colors.accent;
    ctx.fillText(`Scene ${sceneIndex + 1} of ${totalScenes}`, 1216, theme.safeArea.headerHeight / 2);
    ctx.restore();
  }

  // Draw caption bar with word-by-word highlight
  function drawCaptions(ctx, narration, lt, dur, theme, lang) {
    if (!narration) return;
    const font = theme.getFont(lang);
    const boxX = 64;
    const boxY = theme.safeArea.captionY;
    const boxW = 1152;
    const boxH = theme.safeArea.captionHeight;

    ctx.save();
    // Caption card background
    theme.drawRoundedRect(ctx, boxX, boxY, boxW, boxH, 12, 'rgba(19, 34, 74, 0.95)', theme.colors.panelBorder);

    // Compute word timings
    const words = narration.trim().split(/\s+/);
    if (words.length === 0) {
      ctx.restore();
      return;
    }

    const totalChars = words.reduce((acc, w) => acc + w.length, 0);
    const effectiveDur = Math.max(0.5, dur - 0.5);
    let charAccum = 0;

    // Determine active word index
    let activeWordIdx = -1;
    for (let i = 0; i < words.length; i++) {
      const fracStart = charAccum / totalChars;
      charAccum += words[i].length;
      const fracEnd = charAccum / totalChars;

      const tStart = 0.15 + fracStart * effectiveDur;
      const tEnd = 0.15 + fracEnd * effectiveDur;

      if (lt >= tStart && lt < tEnd) {
        activeWordIdx = i;
        break;
      } else if (lt >= tEnd && i === words.length - 1) {
        activeWordIdx = words.length - 1;
      }
    }

    // Format text lines
    ctx.font = `500 24px ${font}`;
    ctx.textBaseline = 'middle';

    // Wrap words into lines with layout positions
    const lines = [];
    let currentLine = [];
    let currentWidth = 0;
    const maxLineW = boxW - 60;

    words.forEach((word, idx) => {
      const wordW = ctx.measureText(word + ' ').width;
      if (currentWidth + wordW > maxLineW && currentLine.length > 0) {
        lines.push(currentLine);
        currentLine = [];
        currentWidth = 0;
      }
      currentLine.push({ word, idx, width: wordW });
      currentWidth += wordW;
    });
    if (currentLine.length > 0) lines.push(currentLine);

    // Render lines centered vertically
    const maxVisibleLines = Math.min(2, lines.length);
    const startY = boxY + (boxH / 2) - ((maxVisibleLines - 1) * 16);

    for (let l = 0; l < maxVisibleLines; l++) {
      const lineWords = lines[l];
      const lineWidth = lineWords.reduce((s, w) => s + w.width, 0);
      let curX = boxX + (boxW - lineWidth) / 2;
      const curY = startY + l * 34;

      lineWords.forEach(({ word, idx, width }) => {
        if (idx === activeWordIdx) {
          ctx.fillStyle = theme.colors.accent2; // Highlight color
          ctx.font = `700 25px ${font}`;
        } else if (activeWordIdx >= 0 && idx < activeWordIdx) {
          ctx.fillStyle = theme.colors.text;   // Already spoken
          ctx.font = `500 24px ${font}`;
        } else {
          ctx.fillStyle = theme.colors.muted;  // Upcoming
          ctx.font = `500 24px ${font}`;
        }
        ctx.fillText(word, curX, curY);
        curX += width;
      });
    }
    ctx.restore();
  }

  // Draw scene progress indicator
  function drawProgress(ctx, scenes, t, theme) {
    if (!scenes || scenes.length === 0) return;
    ctx.save();
    const count = scenes.length;
    const dotSpacing = 20;
    const startX = (1280 - (count - 1) * dotSpacing) / 2;
    const y = 708;

    for (let i = 0; i < count; i++) {
      const scene = scenes[i];
      const isPast = t >= scene.end_sec;
      const isCurrent = t >= scene.start_sec && t < scene.end_sec;

      ctx.beginPath();
      ctx.arc(startX + i * dotSpacing, y, isCurrent ? 4 : 3, 0, Math.PI * 2);
      if (isCurrent) {
        ctx.fillStyle = theme.colors.accent;
      } else if (isPast) {
        ctx.fillStyle = theme.colors.good;
      } else {
        ctx.fillStyle = theme.colors.progressTrack;
      }
      ctx.fill();
    }
    ctx.restore();
  }

  // Public API: Initialize lesson
  async function initLesson(title, scenes, lang = 'en') {
    if (!title || !scenes || scenes.length === 0) {
      throw new Error('[Renderer] Invalid arguments to initLesson');
    }

    _title = title;
    _scenes = scenes;
    _lang = lang || 'en';
    _totalDuration = scenes[scenes.length - 1].end_sec;

    // Attach canvas if in browser environment
    if (typeof document !== 'undefined') {
      _canvas = document.getElementById('stage');
      if (_canvas) {
        _ctx = _canvas.getContext('2d');
      }

      // Wait for fonts to be ready
      try {
        if (document.fonts && typeof document.fonts.ready !== 'undefined') {
          await document.fonts.ready;
        }
      } catch (fontErr) {
        console.warn('[Renderer] Font loading notice:', fontErr);
      }
    }

    root.totalDuration = _totalDuration;
    root.ready = true;
    return true;
  }

  // Public API: Render deterministic frame at t_sec
  function renderAtTime(t_sec) {
    const theme = getTheme();
    const templates = getTemplates();

    if (!_canvas && typeof document !== 'undefined') {
      _canvas = document.getElementById('stage');
      if (_canvas) _ctx = _canvas.getContext('2d');
    }

    if (!_ctx || !_scenes || _scenes.length === 0) {
      return false;
    }

    const t = Math.max(0, Math.min(_totalDuration, Number(t_sec) || 0));
    const scene = getActiveScene(_scenes, t);
    if (!scene) return false;

    const sceneIdx = _scenes.indexOf(scene);
    const lt = t - scene.start_sec;
    const dur = scene.duration_sec;

    // Calculate transition fade alpha using 0.35s tail
    const TAIL = 0.35;
    let fadeAlpha = 1.0;
    if (lt < TAIL && sceneIdx > 0) {
      fadeAlpha = Math.max(0.1, lt / TAIL);
    } else if (lt > dur - TAIL && sceneIdx < _scenes.length - 1) {
      fadeAlpha = Math.max(0.1, (dur - lt) / TAIL);
    }

    // 1. Clear background
    _ctx.fillStyle = theme.colors.bg;
    _ctx.fillRect(0, 0, 1280, 720);

    // 2. Draw Header
    drawHeader(_ctx, _title, sceneIdx, _scenes.length, theme, _lang);

    // 3. Draw Scene Template with fade
    _ctx.save();
    _ctx.globalAlpha = fadeAlpha;
    const visual = scene.visual || { type: 'bullets', params: { labels: [], steps: [] } };
    templates.draw(_ctx, visual.type, visual.params, lt, dur, theme, _lang);
    _ctx.restore();

    // 4. Draw Captions
    drawCaptions(_ctx, scene.narration, lt, dur, theme, _lang);

    // 5. Draw Progress indicators
    drawProgress(_ctx, _scenes, t, theme);

    return true;
  }

  // Expose frozen API to root/window
  root.initLesson = initLesson;
  root.renderAtTime = renderAtTime;
  root.totalDuration = 0;
  root.ready = false;

  // Node.js module export if required
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      initLesson,
      renderAtTime,
      getActiveScene,
      drawHeader,
      drawCaptions,
      drawProgress,
      setCanvas(canvas, ctx) {
        _canvas = canvas;
        _ctx = ctx;
      }
    };
  }
})(typeof window !== 'undefined' ? window : globalThis);
