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
  let _lastT = 0;
  let _simplifiedSceneId = null;
  let _quizBound = false;
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

  // Draw header bar matching approved reference designs
  function drawHeader(ctx, title, sceneIndex, totalScenes, theme, lang, visualType = '', showSimplified = false) {
    const font = theme.getFont(lang);
    ctx.save();

    // 1. Top Brand Mark Left: BLUE VISUAL TEACHER ■
    ctx.font = `800 14px ${font}`;
    ctx.fillStyle = theme.colors.text;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const brandText = 'BLUE VISUAL TEACHER';
    ctx.fillText(brandText, 64, 28);
    const brandWidth = ctx.measureText(brandText).width;
    theme.drawBrandAccent(ctx, 64 + brandWidth + 8, 33, 11);

    // 2. Right Indicators: Language pill and Step/Process pill
    const stepLabel = `STEP 0${sceneIndex + 1} · ${(visualType || 'SCENE').toUpperCase()}`;
    const stepPillWidth = ctx.measureText(`[ ${stepLabel} ]`).width + 24;
    const stepX = 1216 - stepPillWidth;
    theme.drawPill(ctx, stepLabel, stepX, 15, {
      bg: '#FFFFFF',
      color: theme.colors.text,
      border: theme.colors.border,
      lineWidth: 1.5,
      height: 26,
      fontSize: 12,
      weight: 700,
      font,
      bracketed: true
    });

    // Language selector pill: [ EN | हि | ಕನ್ನಡ ]
    const langLabel = 'EN | हि | ಕನ್ನಡ';
    const langPillWidth = ctx.measureText(`[ ${langLabel} ]`).width + 24;
    const langX = stepX - langPillWidth - 12;
    theme.drawPill(ctx, langLabel, langX, 15, {
      bg: '#FFFFFF',
      color: theme.colors.text,
      border: theme.colors.border,
      lineWidth: 1.5,
      height: 26,
      fontSize: 12,
      weight: 700,
      font,
      bracketed: true
    });

    if (showSimplified) {
      const simple = 'Simplified Explanation';
      const simpleW = ctx.measureText(`[ ${simple} ]`).width + 24;
      theme.drawPill(ctx, simple, langX - simpleW - 12, 15, {
        bg: '#FEF3C7',
        color: theme.colors.text,
        border: theme.colors.border,
        lineWidth: 1.5,
        height: 26,
        fontSize: 11,
        weight: 700,
        font,
        bracketed: true
      });
    }

    // 3. Crisp horizontal separator rule at y = 52
    ctx.strokeStyle = theme.colors.border;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(64, 52);
    ctx.lineTo(1216, 52);
    ctx.stroke();

    ctx.restore();
  }

  // Draw caption bar with responsive font-scaling and word-by-word highlight
  function drawCaptions(ctx, narration, lt, dur, theme, lang) {
    if (!narration) return;
    const font = theme.getFont(lang);
    const boxX = 64;
    const boxY = theme.safeArea.captionY;
    const boxW = 1152;
    const boxH = theme.safeArea.captionHeight;

    ctx.save();
    // Warm ivory / crisp white caption card with bold black outline
    theme.drawCard(ctx, boxX, boxY, boxW, boxH, 14, '#FFFFFF', theme.colors.border, 2);

    const words = narration.trim().split(/\s+/);
    if (words.length === 0) {
      ctx.restore();
      return;
    }

    // Determine active word index based on proportional character timing
    const totalChars = words.reduce((acc, w) => acc + w.length, 0);
    const effectiveDur = Math.max(0.5, dur - 0.5);
    let charAccum = 0;
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

    // Adapt font size dynamically from 24px down to 16px so all words fit within 2 or 3 lines
    const maxLineW = boxW - 64;
    const fontCandidates = [24, 21, 18, 16];
    let chosenFontSize = 16;
    let chosenLines = [];

    for (let f = 0; f < fontCandidates.length; f++) {
      const fs = fontCandidates[f];
      ctx.font = `500 ${fs}px ${font}`;
      const lines = [];
      let currentLine = [];
      let currentWidth = 0;

      for (let wIdx = 0; wIdx < words.length; wIdx++) {
        const word = words[wIdx];
        const wordW = ctx.measureText(word + ' ').width;
        if (currentWidth + wordW > maxLineW && currentLine.length > 0) {
          lines.push(currentLine);
          currentLine = [];
          currentWidth = 0;
        }
        currentLine.push({ word, idx: wIdx, width: wordW });
        currentWidth += wordW;
      }
      if (currentLine.length > 0) lines.push(currentLine);

      const lHeight = fs * 1.35;
      if (lines.length <= 2 || (lines.length === 3 && fs <= 18)) {
        chosenFontSize = fs;
        chosenLines = lines;
        break;
      }
      if (f === fontCandidates.length - 1) {
        chosenFontSize = fs;
        chosenLines = lines;
      }
    }

    // Render all words across the chosen lines with accurate inter-word spacing
    const lineHeight = chosenFontSize * 1.35;
    const totalBlockHeight = chosenLines.length * lineHeight;
    const startY = boxY + (boxH - totalBlockHeight) / 2 + (lineHeight / 2);
    ctx.textBaseline = 'middle';

    for (let l = 0; l < chosenLines.length; l++) {
      const lineWords = chosenLines[l];
      ctx.font = `500 ${chosenFontSize}px ${font}`;
      const spaceWidth = ctx.measureText(' ').width;

      // Calculate exact rendered line width including spaces
      let totalLineWidth = 0;
      for (let w = 0; w < lineWords.length; w++) {
        const { word, idx } = lineWords[w];
        ctx.font = idx === activeWordIdx ? `700 ${chosenFontSize}px ${font}` : `500 ${chosenFontSize}px ${font}`;
        totalLineWidth += ctx.measureText(word).width;
        if (w < lineWords.length - 1) totalLineWidth += spaceWidth;
      }

      let curX = boxX + (boxW - totalLineWidth) / 2;
      const curY = startY + l * lineHeight;

      for (let w = 0; w < lineWords.length; w++) {
        const { word, idx } = lineWords[w];
        if (idx === activeWordIdx) {
          ctx.fillStyle = theme.colors.accent2; // Highlight color
          ctx.font = `700 ${chosenFontSize}px ${font}`;
        } else if (activeWordIdx >= 0 && idx < activeWordIdx) {
          ctx.fillStyle = theme.colors.text;    // Spoken
          ctx.font = `500 ${chosenFontSize}px ${font}`;
        } else {
          ctx.fillStyle = theme.colors.muted;   // Upcoming
          ctx.font = `500 ${chosenFontSize}px ${font}`;
        }
        ctx.fillText(word, curX, curY);
        curX += ctx.measureText(word).width + spaceWidth;
      }
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
  async function initLesson(title, scenesOrManifest, lang = 'en') {
    let scenes = scenesOrManifest;
    let lessonLang = lang || 'en';
    if (scenesOrManifest && !Array.isArray(scenesOrManifest)) {
      scenes = scenesOrManifest.scenes;
      if (scenesOrManifest.lang) lessonLang = scenesOrManifest.lang;
      if (!title && scenesOrManifest.title) title = scenesOrManifest.title;
    }
    if (!title || !scenes || scenes.length === 0) {
      throw new Error('[Renderer] Invalid arguments to initLesson');
    }

    _title = title;
    _scenes = scenes;
    _lang = lessonLang;
    _totalDuration = scenes[scenes.length - 1].end_sec;

    if (typeof document !== 'undefined') {
      _canvas = document.getElementById('stage');
      if (_canvas) {
        _ctx = _canvas.getContext('2d');
      }
      bindQuizPointer();

      try {
        if (document.fonts) {
          const families = ['"Noto Sans"', '"Noto Sans Devanagari"', '"Noto Sans Kannada"', '"Noto Sans Tamil"', '"Noto Sans Bengali"'];
          await Promise.allSettled(families.flatMap((family) => [
            document.fonts.load(`400 24px ${family}`),
            document.fonts.load(`700 32px ${family}`)
          ]));
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

    const numericT = Number(t_sec);
    const validT = isNaN(numericT) ? 0 : numericT;
    const t = Math.max(0, Math.min(_totalDuration, validT));
    _lastT = t;
    const scene = getActiveScene(_scenes, t);
    if (!scene) return false;

    const sceneIdx = _scenes.indexOf(scene);
    const lt = t - scene.start_sec;
    const dur = scene.duration_sec;
    const p = dur > 0 ? Math.min(1, Math.max(0, lt / dur)) : 1;
    const entrance = p <= 0.15 ? theme.easeOutCubic(p / 0.15) : 1;

    // Calculate transition fade alpha using 0.35s tail
    const TAIL = 0.35;
    let fadeAlpha = 1.0;
    if (lt < TAIL && sceneIdx > 0) {
      fadeAlpha = Math.max(0.1, lt / TAIL);
    } else if (lt > dur - TAIL && sceneIdx < _scenes.length - 1) {
      fadeAlpha = Math.max(0.1, (dur - lt) / TAIL);
    }

    // 1. Clear background (warm ivory)
    _ctx.fillStyle = theme.colors.bg;
    _ctx.fillRect(0, 0, 1280, 720);

    // 2. Draw subtle square graph paper grid
    theme.drawGraphGrid(_ctx, 1280, 720, 28);

    // 3. Draw Header
    const visual = scene.visual || { type: 'bullets', params: { labels: [], steps: [] } };
    const showSimplified = _simplifiedSceneId != null && scene.id === _simplifiedSceneId;
    drawHeader(_ctx, _title, sceneIdx, _scenes.length, theme, _lang, visual.type, showSimplified);

    let drawParams = visual.params || {};
    if (visual.type === 'quiz' && Number.isInteger(scene.selectedQuizOption)) {
      drawParams = Object.assign({}, drawParams, { selectedQuizOption: scene.selectedQuizOption });
    }

    // 4. Draw Scene Template with fade
    _ctx.save();
    _ctx.globalAlpha = fadeAlpha * Math.max(entrance, 0.2);
    templates.draw(_ctx, visual.type, drawParams, lt, dur, theme, _lang);
    _ctx.restore();

    // 4. Draw Captions
    drawCaptions(_ctx, scene.narration, lt, dur, theme, _lang);

    // 5. Draw Progress indicators
    drawProgress(_ctx, _scenes, t, theme);

    return true;
  }

  function bindQuizPointer() {
    if (_quizBound || !_canvas || typeof _canvas.addEventListener !== 'function') return;
    _quizBound = true;
    _canvas.addEventListener('pointerdown', onQuizPointer);
  }

  function onQuizPointer(ev) {
    const templates = getTemplates();
    if (!_canvas || !_scenes || !templates || typeof templates.quizBoxes !== 'function') return;
    const rect = _canvas.getBoundingClientRect();
    const x = (ev.clientX - rect.left) * (_canvas.width / (rect.width || _canvas.width));
    const y = (ev.clientY - rect.top) * (_canvas.height / (rect.height || _canvas.height));
    const scene = getActiveScene(_scenes, _lastT);
    if (!scene || !scene.visual || scene.visual.type !== 'quiz') return;
    const hit = templates.quizBoxes().findIndex(box =>
      x >= box.x && x <= box.x + box.w && y >= box.y && y <= box.y + box.h
    );
    if (hit < 0) return;
    scene.selectedQuizOption = hit;
    renderAtTime(_lastT);
  }

  function updateSingleScene(sceneId, updatedScene, newFullManifest, newAudioUrl) {
    const incoming = newFullManifest && Array.isArray(newFullManifest.scenes)
      ? newFullManifest.scenes
      : (Array.isArray(newFullManifest) ? newFullManifest : null);
    if (!incoming || !updatedScene) return false;
    _scenes = incoming.map(scene => (scene && scene.id === sceneId ? updatedScene : scene));
    if (newFullManifest && newFullManifest.title) _title = newFullManifest.title;
    if (newFullManifest && newFullManifest.lang) _lang = newFullManifest.lang;
    _totalDuration = _scenes.length ? (_scenes[_scenes.length - 1].end_sec || 0) : 0;
    root.totalDuration = _totalDuration;
    _simplifiedSceneId = sceneId;
    const start = Number(updatedScene.start_sec) || 0;
    if (typeof document !== 'undefined') {
      const audio = document.getElementById('audio-player');
      if (audio) {
        const seek = () => { try { audio.currentTime = start; } catch (err) { /* metadata not ready */ } };
        if (newAudioUrl) {
          audio.src = newAudioUrl;
          audio.addEventListener('loadedmetadata', seek, { once: true });
          if (typeof audio.load === 'function') audio.load();
        } else {
          seek();
        }
      }
    }
    return renderAtTime(start);
  }

  // Expose frozen API to root/window
  root.initLesson = initLesson;
  root.renderAtTime = renderAtTime;
  root.updateSingleScene = updateSingleScene;
  root.totalDuration = 0;
  root.ready = false;

  // Node.js module export if required
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      initLesson,
      renderAtTime,
      updateSingleScene,
      getActiveScene,
      drawHeader,
      drawCaptions,
      drawProgress,
      setCanvas(canvas, ctx) {
        _canvas = canvas;
        _ctx = ctx;
        bindQuizPointer();
      }
    };
  }
})(typeof window !== 'undefined' ? window : globalThis);
