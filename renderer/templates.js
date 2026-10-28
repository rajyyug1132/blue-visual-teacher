// renderer/templates.js
// Editorial Warm Ivory Visual Templates for Blue Visual Teacher.
// Deterministic 2D Canvas rendering matching approved reference designs.

(function (root) {
  // Helper to draw standard editorial header with amber kicker pill and blue square brand accent
  function drawEditorialHeader(ctx, kicker, title, theme, lang, x = 64, y = 72, maxWidth = 1152) {
    const font = theme.getFont(lang);

    // 1. Amber Kicker Pill: [ KICKER TITLE ]
    const kickerText = (kicker || 'CONCEPT').toUpperCase();
    const pillWidth = theme.drawPill(ctx, kickerText, x, y, {
      bg: theme.colors.kickerBg,
      color: theme.colors.text,
      border: theme.colors.border,
      lineWidth: 1.5,
      height: 26,
      fontSize: 12,
      weight: 700,
      font,
      bracketed: true
    });

    // 2. Bold Headline: [ TITLE . ] ■
    const rawTitle = (title || 'Lesson Title').trim();
    const bracketedTitle = rawTitle.startsWith('[') ? rawTitle : `[ ${rawTitle} . ]`;
    const fit = theme.fitText(ctx, bracketedTitle, { width: maxWidth - 36, height: 75 }, 38, 20, 800, lang, { label: 'header.title' });

    const titleY = y + 36;
    ctx.font = `800 ${fit.fontSize}px ${font}`;
    ctx.fillStyle = theme.colors.text;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';

    theme.drawFittedLines(ctx, fit, x, titleY);

    // Draw small electric blue square brand accent (■) after last title line
    const lastLine = fit.lines[fit.lines.length - 1] || bracketedTitle;
    const textWidth = ctx.measureText(lastLine).width;
    const lastLineY = titleY + (fit.lines.length - 1) * fit.lineHeight;
    theme.drawBrandAccent(ctx, x + textWidth + 8, lastLineY + fit.fontSize - 4, Math.round(fit.fontSize * 0.28));

    return {
      bottomY: lastLineY + fit.lineHeight + 10,
      fontSize: fit.fontSize
    };
  }

  // Reusable helper to draw compact vector concept icon
  function drawConceptIcon(ctx, x, y, size, typeIndex, theme) {
    ctx.save();
    theme.drawCard(ctx, x, y, size, size, 8, '#FAF7EE', theme.colors.border, 1.5);

    const pad = Math.round(size * 0.2);
    const innerW = size - pad * 2;
    const cx = x + size / 2;
    const cy = y + size / 2;

    ctx.strokeStyle = theme.colors.border;
    ctx.lineWidth = 1.75;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    const t = typeIndex % 6;
    if (t === 0) {
      // Conductor / Resistor / Length icon (horizontal wire with zigzag resistor)
      ctx.beginPath();
      ctx.moveTo(x + pad, cy);
      ctx.lineTo(cx - 10, cy);
      ctx.lineTo(cx - 6, cy - 6);
      ctx.lineTo(cx - 2, cy + 6);
      ctx.lineTo(cx + 2, cy - 6);
      ctx.lineTo(cx + 6, cy + 6);
      ctx.lineTo(cx + 10, cy);
      ctx.lineTo(x + size - pad, cy);
      ctx.stroke();
    } else if (t === 1) {
      // Cross-sectional Area / Circle gauge (double concentric circles)
      ctx.beginPath();
      ctx.arc(cx, cy, innerW / 2 - 2, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = theme.colors.amber;
      ctx.beginPath();
      ctx.arc(cx, cy, Math.max(2, innerW / 4), 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    } else if (t === 2) {
      // Material property / Atom / Lattice (nucleus and orbital loop)
      ctx.fillStyle = theme.colors.coral;
      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      if (typeof ctx.ellipse === 'function') {
        ctx.beginPath();
        ctx.ellipse(cx, cy, innerW / 2 - 1, innerW / 4, Math.PI / 4, 0, Math.PI * 2);
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(cx, cy, innerW / 2 - 2, 0, Math.PI * 2);
        ctx.stroke();
      }
    } else if (t === 3) {
      // Temperature / Sun / Energy (sun with short rays)
      ctx.fillStyle = theme.colors.amber;
      ctx.beginPath();
      ctx.arc(cx, cy, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      for (let i = 0; i < 4; i++) {
        const ang = (i * Math.PI) / 2;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(ang) * 9, cy + Math.sin(ang) * 9);
        ctx.lineTo(cx + Math.cos(ang) * 14, cy + Math.sin(ang) * 14);
        ctx.stroke();
      }
    } else if (t === 4) {
      // Process / Arrow flow / Cycle
      ctx.beginPath();
      ctx.arc(cx, cy, innerW / 2 - 2, Math.PI * 0.2, Math.PI * 1.6);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx - 3, cy - innerW / 2 + 1);
      ctx.lineTo(cx + 4, cy - innerW / 2 - 2);
      ctx.lineTo(cx + 1, cy - innerW / 2 + 5);
      ctx.stroke();
    } else {
      // Geometric Block / Measurement
      if (typeof ctx.strokeRect === 'function') {
        ctx.strokeRect(cx - innerW / 2 + 2, cy - innerW / 2 + 2, innerW - 4, innerW - 4);
      }
      ctx.beginPath();
      ctx.moveTo(cx - innerW / 2 + 2, cy);
      ctx.lineTo(cx + innerW / 2 - 2, cy);
      ctx.stroke();
    }
    ctx.restore();
  }

  // Templates draw only the lesson's own words. Every string a template draws must be made of words that appear in
// the scene's labels, steps or code; anything else is invented chrome or filler ("BUS-L", "PROPERTY SET A",
// "[ SCIENTIFIC SCHEMATIC ]") and is dropped, in every language. topic_en is a hint for picking illustrations and is
// never drawn. Numbers, symbols and words under three letters always pass.
function lessonWords(params) {
  const words = new Set();
  const sources = [].concat(params.labels || [], params.steps || [], params.code || []);
  (params.trace || []).forEach(step => (step.vars || []).forEach(v => sources.push(v.name, v.value)));
  sources.forEach(text => (String(text).toLowerCase().match(/[a-z]{3,}/g) || []).forEach(w => words.add(w)));
  return words;
}

function onlyLessonText(ctx, words) {
  return new Proxy(ctx, {
    get(target, prop) {
      if (prop === 'lessonText') {
        return text => !(String(text).toLowerCase().match(/[a-z]{3,}/g) || []).some(w => !words.has(w));
      }
      if (prop === 'fillText') {
        return (text, x, y, maxWidth) => {
          const used = String(text).toLowerCase().match(/[a-z]{3,}/g) || [];
          if (used.some(w => !words.has(w))) return;
          return maxWidth === undefined ? target.fillText(text, x, y) : target.fillText(text, x, y, maxWidth);
        };
      }
      const value = target[prop];
      return typeof value === 'function' ? value.bind(target) : value;
    },
    set(target, prop, value) { target[prop] = value; return true; }
  });
}

const TEMPLATES = {
    // -------------------------------------------------------------------------
    // 1. TITLE TEMPLATE (Cover layout: Left editorial text & key takeaway, Right vector illustration)
    // -------------------------------------------------------------------------
    title(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      // Deterministic staggered entry animations
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      const pLeft = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.1) / 0.6))));
      const pRight = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.2) / 0.6))));

      const mainTitle = labels[0] || 'Lesson Title';
      const kicker = labels[1] || 'SECTION KICKER';
      const explanation = steps[0] || 'Dynamic supporting explanation paragraph. Adapts cleanly across English, Hindi, and Kannada translation length.';
      const takeaway = steps[1] || steps[0] || 'Core takeaway principle and summary of the phenomenon.';

      ctx.save();
      ctx.globalAlpha = pHeader;

      // 1. Top Section Kicker & Main Headline
      const kickerText = kicker.toUpperCase();
      theme.drawPill(ctx, kickerText, 64, 76, {
        bg: theme.colors.kickerBg,
        color: theme.colors.text,
        border: theme.colors.border,
        lineWidth: 1.5,
        height: 26,
        fontSize: 12,
        weight: 700,
        font,
        bracketed: true
      });

      const bracketedTitle = mainTitle.startsWith('[') ? mainTitle : `[ ${mainTitle} . ]`;
      const fitTitle = theme.fitText(ctx, bracketedTitle, { width: 580, height: 125 }, 42, 22, 800, lang, { label: 'title.headline' });
      ctx.font = `800 ${fitTitle.fontSize}px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';

      theme.drawFittedLines(ctx, fitTitle, 64, 114);
      const lastLine = fitTitle.lines[fitTitle.lines.length - 1] || bracketedTitle;
      const textW = ctx.measureText(lastLine).width;
      const lastY = 114 + (fitTitle.lines.length - 1) * fitTitle.lineHeight;
      theme.drawBrandAccent(ctx, 64 + textW + 8, lastY + fitTitle.fontSize - 4, Math.round(fitTitle.fontSize * 0.28));

      // 2. Left Column: Supporting Explanation
      ctx.globalAlpha = pLeft;
      const explY = lastY + fitTitle.lineHeight + 14;
      const fitExpl = theme.fitText(ctx, explanation, { width: 570, height: Math.max(120, 440 - explY) }, 20, 14, 500, lang, { label: 'title.explanation' });
      ctx.font = `500 ${fitExpl.fontSize}px ${font}`;
      ctx.fillStyle = theme.colors.text;
      theme.drawFittedLines(ctx, fitExpl, 64, explY);

      // 3. Left Column: Key Takeaway Box (Electric Blue Card with large white 01 numeral)
      const takeawayY = 430;
      theme.drawCard(ctx, 64, takeawayY, 570, 140, 16, theme.colors.accent, theme.colors.border, 2.5);

      // Large '01' numeral on left
      ctx.font = `800 68px ${font}`;
      ctx.fillStyle = '#FFFFFF';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('01', 124, takeawayY + 70);

      // Takeaway text block on right
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.font = `800 15px ${font}`;
      ctx.fillText('[ KEY TAKEAWAY ]', 190, takeawayY + 22);

      const fitTakeaway = theme.fitText(ctx, takeaway, { width: 420, height: 80 }, 17, 12, 600, lang, { label: 'title.takeaway' });
      ctx.font = `600 ${fitTakeaway.fontSize}px ${font}`;
      theme.drawFittedLines(ctx, fitTakeaway, 190, takeawayY + 50);

      // 4. Right Column: Flat Vector Scientific Illustration Card
      ctx.globalAlpha = pRight;
      const rightX = 674;
      const rightY = 76;
      const rightW = 542;
      const rightH = 494;

      theme.drawCard(ctx, rightX, rightY, rightW, rightH, 18, '#FFFFFF', theme.colors.border, 2.5);

      // Card Header Tag
      ctx.font = `700 12px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('[ SCIENTIFIC SCHEMATIC ]', rightX + rightW / 2, rightY + 24);

      // Content-aware vector illustration selection (precise phrase matching; collision exclusions)
      const topicStr = ((params.topic_en || '') + ' ' + mainTitle + ' ' + kicker + ' ' + explanation).toLowerCase();

      // Explicit exclusions for known ambiguous collisions (route to neutral scientific composition)
      const isElectrochem = topicStr.includes('electrochemical') || topicStr.includes('galvanic') || topicStr.includes('electrolyte') || topicStr.includes('electrochemistry');
      const isOrganicChem = topicStr.includes('organic chem') || topicStr.includes('organic molecule') || topicStr.includes('organic compound');
      const isNonWaterCycle = topicStr.includes('carnot cycle') || topicStr.includes('krebs cycle') || topicStr.includes('calvin cycle') || topicStr.includes('cell cycle') || topicStr.includes('carbon cycle') || topicStr.includes('nitrogen cycle') || topicStr.includes('life cycle') || topicStr.includes('thermodynamic cycle');

      // 1. Precise Electrical Circuit check
      const isCircuitTopic = !isElectrochem && (
        topicStr.includes('circuit') ||
        topicStr.includes('ohm') ||
        topicStr.includes('resistor') ||
        topicStr.includes('resistance') ||
        topicStr.includes('ammeter') ||
        /\b(dc|ac)\b/.test(topicStr) ||
        topicStr.includes('electric current') ||
        topicStr.includes('voltage drop') ||
        topicStr.includes('potential difference') ||
        (topicStr.includes('volt') && !topicStr.includes('revolt')) ||
        (topicStr.includes('electric') && !topicStr.includes('electrochemical') && !topicStr.includes('dielectric'))
      );

      // 2. Precise Water / Hydrological Cycle check
      const isWaterOrCycleTopic = !isNonWaterCycle && (
        topicStr.includes('water cycle') ||
        topicStr.includes('hydrolog') ||
        topicStr.includes('evaporation') ||
        topicStr.includes('precipitation') ||
        (topicStr.includes('water') && (topicStr.includes('rain') || topicStr.includes('cloud') || topicStr.includes('vapour') || topicStr.includes('vapor') || topicStr.includes('sea') || topicStr.includes('ocean')))
      );

      // 3. Precise Cellular Biology check
      const isBioTopic = !isOrganicChem && (
        topicStr.includes('plant cell') ||
        topicStr.includes('animal cell') ||
        topicStr.includes('cell wall') ||
        topicStr.includes('cell membrane') ||
        topicStr.includes('cytoplasm') ||
        topicStr.includes('organelle') ||
        topicStr.includes('cellular biology') ||
        topicStr.includes('cellular structure') ||
        topicStr.includes('photosynthesis') ||
        topicStr.includes('dna replication') ||
        topicStr.includes('mitochondria') ||
        topicStr.includes('chloroplast')
      );

      ctx.save();
      const isDataTopic = !isCircuitTopic && !isWaterOrCycleTopic && !isBioTopic &&
        /regression|statistic|machine learning|\baiml\b|\bml\b|data ?set|dataset|predict|correlation|best fit|trend line|scatter|linear model/.test(topicStr);
      this.lastIllustration = isCircuitTopic ? 'circuit' : isWaterOrCycleTopic ? 'water' : isBioTopic ? 'cell' : isDataTopic ? 'data' : 'neutral';
      if (isCircuitTopic) {
        // Circuit Diagram Illustration
        const cLeft = rightX + 60;
        const cRight = rightX + rightW - 60;
        const cTop = rightY + 90;
        const cBottom = rightY + rightH - 80;

        // Wire loop
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 3;
        ctx.lineJoin = 'round';
        ctx.beginPath();
        ctx.moveTo(cLeft, cTop);
        ctx.lineTo(cRight, cTop);
        ctx.lineTo(cRight, cBottom);
        ctx.lineTo(cLeft, cBottom);
        ctx.closePath();
        ctx.stroke();

        // 1. DC Voltage Source / Battery on left wire
        const batY = (cTop + cBottom) / 2;
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(cLeft - 10, batY - 30, 20, 60);

        // Long plate (+)
        ctx.strokeStyle = theme.colors.accent;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(cLeft - 18, batY - 18);
        ctx.lineTo(cLeft + 18, batY - 18);
        ctx.stroke();

        // Short plate (-)
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(cLeft - 10, batY + 18);
        ctx.lineTo(cLeft + 10, batY + 18);
        ctx.stroke();

        // + and - labels
        ctx.font = `800 14px ${font}`;
        ctx.fillStyle = theme.colors.accent;
        ctx.textAlign = 'right';
        ctx.fillText('+ V', cLeft - 24, batY - 18);
        ctx.fillStyle = theme.colors.text;
        ctx.fillText('- GND', cLeft - 24, batY + 18);

        // 2. Toggle Switch on top wire
        const swX = cLeft + (cRight - cLeft) * 0.35;
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(swX - 18, cTop - 12, 36, 24);
        ctx.fillStyle = theme.colors.border;
        ctx.beginPath();
        ctx.arc(swX - 14, cTop, 4, 0, Math.PI * 2);
        ctx.arc(swX + 14, cTop, 4, 0, Math.PI * 2);
        ctx.fill();
        // Closed switch blade
        ctx.strokeStyle = theme.colors.amber;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(swX - 14, cTop);
        ctx.lineTo(swX + 14, cTop);
        ctx.stroke();

        // Switch label
        ctx.font = `700 11px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        ctx.textAlign = 'center';
        ctx.fillText('SWITCH (CLOSED)', swX, cTop - 16);

        // 3. Load Resistor on bottom wire
        const resX = cLeft + (cRight - cLeft) * 0.5;
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(resX - 45, cBottom - 18, 90, 36);
        theme.drawCard(ctx, resX - 40, cBottom - 15, 80, 30, 6, theme.colors.kickerBg, theme.colors.border, 2);
        // Zigzag inside resistor
        ctx.strokeStyle = theme.colors.coral;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(resX - 30, cBottom);
        ctx.lineTo(resX - 20, cBottom - 8);
        ctx.lineTo(resX - 10, cBottom + 8);
        ctx.lineTo(resX, cBottom - 8);
        ctx.lineTo(resX + 10, cBottom + 8);
        ctx.lineTo(resX + 20, cBottom - 8);
        ctx.lineTo(resX + 30, cBottom);
        ctx.stroke();

        // Resistor label
        ctx.font = `800 12px ${font}`;
        ctx.fillStyle = theme.colors.coral;
        ctx.textAlign = 'center';
        ctx.fillText('RESISTOR ( R )', resX, cBottom + 26);

        // 4. Ammeter Gauge on right wire
        const amX = cRight;
        const amY = (cTop + cBottom) / 2;
        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(amX, amY, 32, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.font = `800 20px ${font}`;
        ctx.fillStyle = theme.colors.accent;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('A', amX, amY);

        ctx.font = `700 11px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        ctx.fillText('CURRENT ( I )', amX, amY + 44);

        // 5. Current Flow Direction Arrows with subtle deterministic progress
        const arrow1X = cLeft + (cRight - cLeft) * 0.75;
        theme.drawOutlinedArrow(ctx, arrow1X - 15, cTop, arrow1X + 15, cTop, 10, theme.colors.accent, theme.colors.border, 2);

        const arrow2Y = amY + 50;
        theme.drawOutlinedArrow(ctx, cRight, arrow2Y - 15, cRight, arrow2Y + 15, 10, theme.colors.accent, theme.colors.border, 2);

        // Center badge: CLOSED CIRCUIT LOOP
        theme.drawPill(ctx, 'CLOSED CIRCUIT LOOP', rightX + rightW / 2 - 75, (cTop + cBottom) / 2 - 14, {
          bg: theme.colors.kickerBg,
          color: theme.colors.text,
          border: theme.colors.border,
          lineWidth: 1.5,
          height: 28,
          fontSize: 11,
          weight: 700,
          font,
          bracketed: true
        });
      } else if (isWaterOrCycleTopic) {
        // Natural cycle / environmental scientific illustration (Sun, Clouds, Shore, Water, Evaporation)
        const sunX = rightX + 110;
        const sunY = rightY + 115;
        ctx.fillStyle = theme.colors.amber;
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(sunX, sunY, 34, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Sun rays
        for (let r = 0; r < 8; r++) {
          const ang = (r * Math.PI) / 4;
          ctx.beginPath();
          ctx.moveTo(sunX + Math.cos(ang) * 42, sunY + Math.sin(ang) * 42);
          ctx.lineTo(sunX + Math.cos(ang) * 52, sunY + Math.sin(ang) * 52);
          ctx.stroke();
        }

        // Clouds top-right
        const cloudX = rightX + 370;
        const cloudY = rightY + 140;
        ctx.fillStyle = theme.colors.accent;
        ctx.beginPath();
        ctx.arc(cloudX - 30, cloudY, 26, 0, Math.PI * 2);
        ctx.arc(cloudX + 10, cloudY - 14, 34, 0, Math.PI * 2);
        ctx.arc(cloudX + 46, cloudY, 24, 0, Math.PI * 2);
        ctx.fillRect(cloudX - 30, cloudY + 4, 80, 20);
        ctx.fill();
        ctx.stroke();

        // Shore hill left
        ctx.fillStyle = theme.colors.amber;
        ctx.beginPath();
        ctx.moveTo(rightX + 10, rightY + rightH - 12);
        ctx.lineTo(rightX + 10, rightY + 360);
        if (typeof ctx.quadraticCurveTo === 'function') {
          ctx.quadraticCurveTo(rightX + 110, rightY + 360, rightX + 170, rightY + rightH - 12);
        } else {
          ctx.lineTo(rightX + 170, rightY + rightH - 12);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Hill right
        ctx.fillStyle = theme.colors.coral;
        ctx.beginPath();
        ctx.moveTo(rightX + rightW - 10, rightY + rightH - 12);
        ctx.lineTo(rightX + rightW - 10, rightY + 370);
        if (typeof ctx.quadraticCurveTo === 'function') {
          ctx.quadraticCurveTo(rightX + rightW - 110, rightY + 380, rightX + rightW - 160, rightY + rightH - 12);
        } else {
          ctx.lineTo(rightX + rightW - 160, rightY + rightH - 12);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Sea water at base
        ctx.fillStyle = theme.colors.accent;
        ctx.beginPath();
        ctx.moveTo(rightX + 10, rightY + 410);
        if (typeof ctx.quadraticCurveTo === 'function') {
          ctx.quadraticCurveTo(rightX + 140, rightY + 395, rightX + 270, rightY + 410);
          ctx.quadraticCurveTo(rightX + 400, rightY + 425, rightX + rightW - 10, rightY + 410);
        } else {
          ctx.lineTo(rightX + 270, rightY + 410);
          ctx.lineTo(rightX + rightW - 10, rightY + 410);
        }
        ctx.lineTo(rightX + rightW - 10, rightY + rightH - 10);
        ctx.lineTo(rightX + 10, rightY + rightH - 10);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Evaporation arrows rising
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2.5;
        const arrowXs = [rightX + 230, rightX + 280, rightX + 330];
        arrowXs.forEach(ax => {
          theme.drawOutlinedArrow(ctx, ax, rightY + 390, ax, rightY + 280, 14, theme.colors.accent, theme.colors.border, 2);
        });

        // Curved convection dashed loop
        if (typeof ctx.setLineDash === 'function') ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.arc(rightX + 240, rightY + 160, 60, Math.PI * 0.9, Math.PI * 1.8);
        ctx.stroke();
        if (typeof ctx.setLineDash === 'function') ctx.setLineDash([]);
      } else if (isBioTopic) {
        // Biological cell / molecular composition
        const cellX = rightX + rightW / 2;
        const cellY = rightY + rightH / 2;

        // Outer membrane
        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 3;
        ctx.beginPath();
        if (typeof ctx.ellipse === 'function') {
          ctx.ellipse(cellX, cellY, 190, 140, 0, 0, Math.PI * 2);
        } else {
          ctx.arc(cellX, cellY, 140, 0, Math.PI * 2);
        }
        ctx.fill();
        ctx.stroke();

        // Cytoplasm zone
        ctx.fillStyle = '#FAF7EE';
        ctx.beginPath();
        if (typeof ctx.ellipse === 'function') {
          ctx.ellipse(cellX, cellY, 175, 125, 0, 0, Math.PI * 2);
        } else {
          ctx.arc(cellX, cellY, 125, 0, Math.PI * 2);
        }
        ctx.fill();

        // Prominent nucleus
        ctx.fillStyle = theme.colors.accent;
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(cellX - 35, cellY - 10, 48, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Nucleolus
        ctx.fillStyle = '#0F172A';
        ctx.beginPath();
        ctx.arc(cellX - 30, cellY - 8, 18, 0, Math.PI * 2);
        ctx.fill();

        // Organelles (Mitochondria / chloroplasts)
        const orgs = [
          { x: cellX + 75, y: cellY - 45, col: theme.colors.amber, label: 'ORGANELLE' },
          { x: cellX + 65, y: cellY + 50, col: theme.colors.coral, label: 'VESICLE' },
          { x: cellX - 85, y: cellY + 65, col: theme.colors.green, label: 'RIBOSOME' }
        ];
        orgs.forEach(org => {
          ctx.fillStyle = org.col;
          ctx.strokeStyle = theme.colors.border;
          ctx.lineWidth = 2;
          ctx.beginPath();
          if (typeof ctx.ellipse === 'function') {
            ctx.ellipse(org.x, org.y, 28, 16, Math.PI / 4, 0, Math.PI * 2);
          } else {
            ctx.arc(org.x, org.y, 20, 0, Math.PI * 2);
          }
          ctx.fill();
          ctx.stroke();
        });

        // Center badge
        theme.drawPill(ctx, 'CELLULAR BIOLOGY MODEL', rightX + rightW / 2 - 80, rightY + rightH - 42, {
          bg: theme.colors.kickerBg,
          color: theme.colors.text,
          border: theme.colors.border,
          lineWidth: 1.5,
          height: 26,
          fontSize: 11,
          weight: 700,
          font,
          bracketed: true
        });
      } else if (isDataTopic) {
        // Data topic: scattered observations and the line that fits them, drawn in from the left as the scene plays
        const ox = rightX + 70, oy = rightY + rightH - 70, w = rightW - 120, h = rightH - 150;
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(ox, rightY + 60);
        ctx.lineTo(ox, oy);
        ctx.lineTo(ox + w, oy);
        ctx.stroke();
        theme.drawOutlinedArrow(ctx, ox + w - 4, oy, ox + w + 14, oy, 8, theme.colors.border, theme.colors.border, 1);
        theme.drawOutlinedArrow(ctx, ox, rightY + 64, ox, rightY + 46, 8, theme.colors.border, theme.colors.border, 1);

        // fixed residuals: deterministic, never Math.random
        const noise = [18, -22, 9, -14, 26, -8, -24, 12, -4, 20, -16, 6, -10, 15];
        const fitY = u => oy - 30 - u * (h - 60);
        noise.forEach((dy, i) => {
          const u = (i + 0.5) / noise.length;
          const px = ox + 20 + u * (w - 40);
          const py = fitY(u) + dy;
          const appear = Math.max(0, Math.min(1, (lt - 0.2 - i * 0.06) / 0.25));
          if (appear <= 0) return;
          ctx.globalAlpha = pRight * appear;
          ctx.strokeStyle = '#94A3B8';
          ctx.lineWidth = 1.5;
          if (typeof ctx.setLineDash === 'function') ctx.setLineDash([3, 3]);
          ctx.beginPath();
          ctx.moveTo(px, py);
          ctx.lineTo(px, fitY(u));
          ctx.stroke();
          if (typeof ctx.setLineDash === 'function') ctx.setLineDash([]);
          ctx.fillStyle = i % 3 === 0 ? theme.colors.amber : theme.colors.accent;
          ctx.strokeStyle = theme.colors.border;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(px, py, 7, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        });

        const pLine = Math.max(0, Math.min(1, (lt - 1.2) / 0.8));
        if (pLine > 0) {
          ctx.globalAlpha = pRight;
          ctx.strokeStyle = theme.colors.coral;
          ctx.lineWidth = 4;
          ctx.lineCap = 'round';
          ctx.beginPath();
          ctx.moveTo(ox + 10, fitY(0));
          ctx.lineTo(ox + 10 + (w - 20) * pLine, fitY(pLine));
          ctx.stroke();
        }
        ctx.globalAlpha = pRight;
      } else {
        // Any other topic: a concept map of the lesson's own terms around its title, no invented imagery
        const hub = String(labels[0] || mainTitle || '');
        const terms = [];
        labels.slice(1).concat(steps).forEach(t => {
          const v = String(t || '').trim();
          if (v && v !== hub && !terms.includes(v) && terms.length < 5) terms.push(v);
        });
        const cx = rightX + rightW / 2;
        const cy = rightY + rightH / 2 + 6;
        const nodeW = 170, nodeH = 64;
        const spots = [[-1, -1], [1, -1], [1, 1], [-1, 1], [0, 1.25]].slice(0, terms.length);
        const colours = [theme.colors.kickerBg, '#E0F2FE', '#DCFCE7', '#FFE4E6', '#F1F5F9'];

        spots.forEach(([sx, sy], i) => {
          const appear = Math.max(0, Math.min(1, (lt - 0.3 - i * 0.25) / 0.4));
          if (appear <= 0) return;
          const nx = cx + sx * 150, ny = cy + sy * 140;
          ctx.globalAlpha = pRight * appear;
          ctx.strokeStyle = theme.colors.border;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(cx, cy);
          ctx.lineTo(nx, ny);
          ctx.stroke();
          theme.drawCard(ctx, nx - nodeW / 2, ny - nodeH / 2, nodeW, nodeH, 12, colours[i], theme.colors.border, 2);
          const fit = theme.fitText(ctx, terms[i], { width: nodeW - 20, height: nodeH - 12 }, 16, 10, 700, lang, { label: 'title.map' });
          ctx.font = `700 ${fit.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          const top = ny - (fit.lines.length * fit.lineHeight) / 2;
          fit.lines.forEach((line, k) => ctx.fillText(line, nx, top + k * fit.lineHeight));
        });

        ctx.globalAlpha = pRight;
        const hubW = 210, hubH = 84;
        theme.drawCard(ctx, cx - hubW / 2, cy - hubH / 2, hubW, hubH, 16, theme.colors.accent, theme.colors.border, 2.5);
        const fitHub = theme.fitText(ctx, hub, { width: hubW - 24, height: hubH - 14 }, 20, 11, 800, lang, { label: 'title.hub' });
        ctx.font = `800 ${fitHub.fontSize}px ${font}`;
        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        const hubTop = cy - (fitHub.lines.length * fitHub.lineHeight) / 2;
        fitHub.lines.forEach((line, k) => ctx.fillText(line, cx, hubTop + k * fitHub.lineHeight));
      }
      ctx.restore();

      ctx.restore();
    },

    // -------------------------------------------------------------------------
    // 2. BULLETS TEMPLATE (Adaptable 1 to 6 visual concept cards with numeral badges)
    // -------------------------------------------------------------------------
    bullets(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      const heading = labels[0] || 'Key Points';
      const kicker = labels[1] || 'KEY CONCEPTS';

      ctx.save();
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pHeader;

      const headerInfo = drawEditorialHeader(ctx, kicker, heading, theme, lang, 64, 70, 1152);

      const items = steps.length > 0 ? steps : (labels.slice(1).length > 0 ? labels.slice(1) : [heading]);
      if (items.length > 6) {
        theme.reportCapacityViolation('bullets', 'bullet_items', items.length, 6);
      }
      const count = Math.min(6, Math.max(1, items.length));

      const cardColors = [
        theme.colors.accent,
        theme.colors.amber,
        theme.colors.coral,
        theme.colors.green,
        theme.colors.indigo,
        '#475569'
      ];

      const startY = headerInfo.bottomY + 14;
      const availH = 590 - startY;

      if (count <= 3) {
        // Horizontal row of 1-3 cards (matches approved reference image)
        const gap = count === 1 ? 0 : (count === 2 ? 36 : 24);
        const cardW = count === 1 ? 760 : Math.round((1152 - (count - 1) * gap) / count);
        const cardH = Math.min(340, availH);
        const startX = count === 1 ? 64 + Math.round((1152 - cardW) / 2) : 64;

        for (let i = 0; i < count; i++) {
          const pCard = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.12) / 0.5))));
          ctx.globalAlpha = pCard;

          const cx = startX + i * (cardW + gap);
          const cy = startY + Math.round((availH - cardH) / 2);

          theme.drawCard(ctx, cx, cy, cardW, cardH, 16, '#FFFFFF', theme.colors.border, 2);

          // Numeral Pill Badge at top
          const badgeColor = cardColors[i % cardColors.length];
          const badgeText = `0${i + 1}`;
          theme.drawPill(ctx, badgeText, cx + 20, cy + 20, {
            bg: badgeColor,
            color: '#FFFFFF',
            border: theme.colors.border,
            lineWidth: 1.5,
            height: 32,
            fontSize: 16,
            weight: 800,
            font,
            bracketed: false
          });

          // Dedicated Vector Icon Box next to badge
          drawConceptIcon(ctx, cx + 76, cy + 18, 36, i, theme);

          // Text content
          const rawItem = items[i];
          const parts = rawItem.split(/:\s*|—\s*|-\s*/);
          const itemTitle = parts.length > 1 ? parts[0] : (labels[i + 1] || `Concept 0${i + 1}`);
          const itemDesc = parts.length > 1 ? parts.slice(1).join(': ') : parts[0];

          ctx.font = `700 20px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';

          const fitTitle = theme.fitText(ctx, itemTitle, { width: cardW - 40, height: 50 }, 22, 15, 700, lang, { label: 'bullets.title' });
          theme.drawFittedLines(ctx, fitTitle, cx + 20, cy + 70);

          const descY = cy + 70 + fitTitle.lines.length * fitTitle.lineHeight + 10;
          const fitDesc = theme.fitText(ctx, itemDesc, { width: cardW - 40, height: Math.max(50, cardH - (descY - cy) - 16) }, 17, 12, 500, lang, { label: 'bullets.desc' });
          ctx.font = `500 ${fitDesc.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.muted;
          theme.drawFittedLines(ctx, fitDesc, cx + 20, descY);
        }
      } else {
        // 2-column grid for 4 to 6 cards
        const cols = 2;
        const rows = Math.ceil(count / cols);
        const gapX = 28;
        const gapY = 18;
        const cardW = Math.round((1152 - gapX) / cols);
        const cardH = Math.round((availH - (rows - 1) * gapY) / rows);

        for (let i = 0; i < count; i++) {
          const colIdx = i % cols;
          const rowIdx = Math.floor(i / cols);
          const pCard = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.1) / 0.5))));
          ctx.globalAlpha = pCard;

          const cx = 64 + colIdx * (cardW + gapX);
          const cy = startY + rowIdx * (cardH + gapY);

          theme.drawCard(ctx, cx, cy, cardW, cardH, 14, '#FFFFFF', theme.colors.border, 2);

          // Numeral circle / badge
          const badgeColor = cardColors[i % cardColors.length];
          const badgeText = `0${i + 1}`;
          theme.drawPill(ctx, badgeText, cx + 16, cy + Math.round((cardH - 32) / 2), {
            bg: badgeColor,
            color: '#FFFFFF',
            border: theme.colors.border,
            lineWidth: 1.5,
            height: 32,
            fontSize: 14,
            weight: 800,
            font,
            bracketed: false
          });

          // Dedicated Vector Icon Box
          drawConceptIcon(ctx, cx + 64, cy + Math.round((cardH - 34) / 2), 34, i, theme);

          const rawItem = items[i];
          const fitItem = theme.fitText(ctx, rawItem, { width: cardW - 120, height: cardH - 20 }, 17, 13, 600, lang);
          ctx.font = `600 ${fitItem.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';

          const textBlockH = fitItem.lines.length * fitItem.lineHeight;
          const topY = cy + (cardH - textBlockH) / 2;
          theme.drawFittedLines(ctx, fitItem, cx + 110, topY);
        }
      }

      ctx.restore();
    },

    // -------------------------------------------------------------------------
    // 3. COMPARE TEMPLATE (Reference image: Concept A with left illustration, Concept B with right illustration, center VS badge)
    // -------------------------------------------------------------------------
    compare(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pHeader;

      const heading = labels[0] || 'Concept Comparison';
      const kicker = labels[1] || 'CONCEPT COMPARISON';
      const headerInfo = drawEditorialHeader(ctx, kicker, heading, theme, lang, 64, 70, 1152);

      const colCount = Math.min(3, Math.max(2, labels.length >= 2 ? (labels.length === 3 ? 3 : 2) : 2));
      const colLabels = labels.length >= 2 ? labels.slice(0, colCount) : ['Concept A', 'Concept B'];

      const startY = headerInfo.bottomY + 12;
      const totalH = 585 - startY;

      const gap = colCount === 2 ? 48 : 32;
      const colW = Math.round((1152 - (colCount - 1) * gap) / colCount);

      const headerColors = [theme.colors.accent, theme.colors.amber, theme.colors.coral];

      // Draw Comparison Columns
      for (let c = 0; c < colCount; c++) {
        const pCol = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - c * 0.15) / 0.5))));
        ctx.globalAlpha = pCol;

        const cx = 64 + c * (colW + gap);
        theme.drawCard(ctx, cx, startY, colW, totalH, 16, '#FFFFFF', theme.colors.border, 2);

        // Header Banner: [ 01 ] CONCEPT TITLE
        const colColor = headerColors[c % headerColors.length];
        theme.drawRoundedRect(ctx, cx, startY, colW, 54, 16, colColor, theme.colors.border, 2);
        ctx.fillStyle = colColor;
        ctx.fillRect(cx + 2, startY + 30, colW - 4, 24);

        const bannerText = `[ 0${c + 1} ] ${colLabels[c].toUpperCase()}`;
        const fitColTitle = theme.fitText(ctx, bannerText, { width: colW - 32, height: 40 }, 18, 13, 800, lang);
        ctx.font = `800 ${fitColTitle.fontSize}px ${font}`;
        ctx.fillStyle = c === 1 ? '#0F172A' : '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(fitColTitle.lines[0] || bannerText, cx + colW / 2, startY + 27);

        // Isolate steps per column without cross-duplication (fixes Test 10)
        const relevantSteps = steps.filter((_, idx) => (colCount === 2 ? idx % 2 === c : idx % colCount === c));
        const colSteps = relevantSteps.length > 0 ? relevantSteps : (steps[c] ? [steps[c]] : []);

        if (colCount === 2) {
          // 2-Column layout matching approved reference image:
          // Left card: Illustration box on left, bullets on right
          // Right card: Bullets on left, illustration box on right
          const isLeftCard = c === 0;
          const illusW = 160;
          const illusH = totalH - 80;
          const illusX = isLeftCard ? cx + 18 : cx + colW - illusW - 18;
          const illusY = startY + 66;

          const textX = isLeftCard ? cx + illusW + 32 : cx + 20;
          const textW = colW - illusW - 50;

          // Vector Illustration Container Box
          theme.drawCard(ctx, illusX, illusY, illusW, illusH, 12, isLeftCard ? '#F1F5F9' : '#FEF3C7', theme.colors.border, 1.5);

          // Topic-sensitive illustration selection
          const compareContext = ((params.topic_en || '') + ' ' + heading + ' ' + kicker + ' ' + colLabels.join(' ') + ' ' + colSteps.join(' ')).toLowerCase();
          const isDCAC = (compareContext.includes('direct current') || compareContext.includes('alternating current') ||
                         (compareContext.includes('dc') && compareContext.includes('ac')) ||
                         (colLabels[0].toLowerCase().includes('dc') && colLabels[1].toLowerCase().includes('ac')));
          const isPlantAnimal = compareContext.includes('cell') && (
            (colLabels[0].toLowerCase().includes('plant') || colLabels[1].toLowerCase().includes('animal')) ||
            (colLabels[0].toLowerCase().includes('animal') || colLabels[1].toLowerCase().includes('plant'))
          );
          const isSpeedVelocity = (compareContext.includes('speed') && compareContext.includes('velocity')) ||
                                  (compareContext.includes('scalar') && compareContext.includes('vector'));
          const isMitosisMeiosis = compareContext.includes('mitosis') || compareContext.includes('meiosis');

          let pillLabel = isLeftCard ? 'CONCEPT 01' : 'CONCEPT 02';
          if (isDCAC) pillLabel = isLeftCard ? 'DIRECT CURRENT' : 'ALTERNATING';
          else if (isPlantAnimal) pillLabel = isLeftCard ? 'PLANT CELL' : 'ANIMAL CELL';
          else if (isSpeedVelocity) pillLabel = isLeftCard ? 'SCALAR SPEED' : 'VECTOR VELOCITY';
          else if (isMitosisMeiosis) pillLabel = isLeftCard ? 'MITOSIS (2N)' : 'MEIOSIS (N)';

          theme.drawPill(ctx, pillLabel, illusX + 10, illusY + 12, {
            bg: '#FFFFFF',
            color: theme.colors.text,
            border: theme.colors.border,
            lineWidth: 1.5,
            height: 22,
            fontSize: 9,
            weight: 700,
            font,
            bracketed: true
          });

          // Draw semantic vector visual inside illustration box
          ctx.save();
          const iCenterX = illusX + illusW / 2;
          const iCenterY = illusY + illusH / 2 + 10;

          if (isDCAC) {
            // Case A: DC vs AC Electrical Waveforms
            if (isLeftCard) {
              ctx.fillStyle = theme.colors.accent;
              ctx.strokeStyle = theme.colors.border;
              ctx.lineWidth = 2;
              ctx.beginPath();
              ctx.arc(iCenterX, iCenterY - 30, 28, 0, Math.PI * 2);
              ctx.fill();
              ctx.stroke();

              ctx.font = `800 24px ${font}`;
              ctx.fillStyle = '#FFFFFF';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText('DC', iCenterX, iCenterY - 30);

              ctx.strokeStyle = theme.colors.border;
              ctx.lineWidth = 2.5;
              ctx.beginPath();
              ctx.moveTo(illusX + 24, iCenterY + 36);
              ctx.lineTo(illusX + illusW - 24, iCenterY + 36);
              ctx.stroke();
              theme.drawOutlinedArrow(ctx, illusX + illusW - 40, iCenterY + 36, illusX + illusW - 20, iCenterY + 36, 8, theme.colors.accent, theme.colors.border, 2);
            } else {
              ctx.fillStyle = theme.colors.amber;
              ctx.strokeStyle = theme.colors.border;
              ctx.lineWidth = 2;
              ctx.beginPath();
              ctx.arc(iCenterX, iCenterY - 30, 28, 0, Math.PI * 2);
              ctx.fill();
              ctx.stroke();

              ctx.font = `800 24px ${font}`;
              ctx.fillStyle = '#0F172A';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText('AC', iCenterX, iCenterY - 30);

              ctx.strokeStyle = theme.colors.border;
              ctx.lineWidth = 2.5;
              ctx.beginPath();
              for (let px = 0; px <= illusW - 48; px++) {
                const rad = (px / (illusW - 48)) * Math.PI * 2;
                const py = Math.sin(rad) * 16;
                if (px === 0) ctx.moveTo(illusX + 24 + px, iCenterY + 36 + py);
                else ctx.lineTo(illusX + 24 + px, iCenterY + 36 + py);
              }
              ctx.stroke();
            }
          } else if (isPlantAnimal) {
            // Case B1: Plant Cell vs Animal Cell
            const isPlant = colLabels[c].toLowerCase().includes('plant') || isLeftCard;
            if (isPlant) {
              // Plant Cell: Rigid cell wall rectangle with green fill, large central vacuole, chloroplast dots
              ctx.fillStyle = '#D1FAE5';
              ctx.strokeStyle = theme.colors.good;
              ctx.lineWidth = 3;
              ctx.beginPath();
              ctx.moveTo(iCenterX - 45, iCenterY - 45);
              ctx.lineTo(iCenterX + 45, iCenterY - 45);
              ctx.lineTo(iCenterX + 45, iCenterY + 35);
              ctx.lineTo(iCenterX - 45, iCenterY + 35);
              ctx.closePath();
              ctx.stroke();
              ctx.fillRect(iCenterX - 43, iCenterY - 43, 86, 76);

              // Central vacuole
              ctx.fillStyle = '#A7F3D0';
              ctx.strokeStyle = theme.colors.border;
              ctx.lineWidth = 1.5;
              ctx.beginPath();
              if (typeof ctx.ellipse === 'function') {
                ctx.ellipse(iCenterX, iCenterY - 5, 24, 18, 0, 0, Math.PI * 2);
              } else {
                ctx.arc(iCenterX, iCenterY - 5, 20, 0, Math.PI * 2);
              }
              ctx.fill();
              ctx.stroke();

              // Chloroplast dots
              ctx.fillStyle = theme.colors.good;
              [[-26, -26], [26, -26], [-26, 16], [26, 16]].forEach(([dx, dy]) => {
                ctx.beginPath();
                ctx.arc(iCenterX + dx, iCenterY + dy, 4, 0, Math.PI * 2);
                ctx.fill();
              });

              ctx.font = `700 11px ${font}`;
              ctx.fillStyle = theme.colors.text;
              ctx.textAlign = 'center';
              ctx.fillText('CELL WALL', iCenterX, iCenterY + 48);
            } else {
              // Animal Cell: Flexible rounded membrane with nucleus and mitochondria
              ctx.fillStyle = '#FEE2E2';
              ctx.strokeStyle = theme.colors.coral;
              ctx.lineWidth = 2.5;
              ctx.beginPath();
              ctx.arc(iCenterX, iCenterY - 5, 42, 0, Math.PI * 2);
              ctx.fill();
              ctx.stroke();

              // Nucleus
              ctx.fillStyle = theme.colors.indigo;
              ctx.beginPath();
              ctx.arc(iCenterX - 6, iCenterY - 8, 16, 0, Math.PI * 2);
              ctx.fill();

              // Nucleolus
              ctx.fillStyle = '#FFFFFF';
              ctx.beginPath();
              ctx.arc(iCenterX - 6, iCenterY - 8, 6, 0, Math.PI * 2);
              ctx.fill();

              ctx.font = `700 11px ${font}`;
              ctx.fillStyle = theme.colors.text;
              ctx.textAlign = 'center';
              ctx.fillText('CELL MEMBRANE', iCenterX, iCenterY + 48);
            }
          } else if (isSpeedVelocity) {
            // Case B2: Speed (Scalar) vs Velocity (Vector)
            const isSpeed = colLabels[c].toLowerCase().includes('speed') || colLabels[c].toLowerCase().includes('scalar') || isLeftCard;
            if (isSpeed) {
              // Odometer / Speedometer arc
              ctx.strokeStyle = theme.colors.accent;
              ctx.lineWidth = 3;
              ctx.beginPath();
              ctx.arc(iCenterX, iCenterY, 32, Math.PI * 0.8, Math.PI * 2.2);
              ctx.stroke();

              // Needle
              ctx.strokeStyle = theme.colors.border;
              ctx.lineWidth = 2.5;
              ctx.beginPath();
              ctx.moveTo(iCenterX, iCenterY);
              ctx.lineTo(iCenterX + 18, iCenterY - 18);
              ctx.stroke();

              ctx.font = `800 14px ${font}`;
              ctx.fillStyle = theme.colors.text;
              ctx.textAlign = 'center';
              ctx.fillText('| v |', iCenterX, iCenterY + 20);
              ctx.font = `700 11px ${font}`;
              ctx.fillStyle = theme.colors.muted;
              ctx.fillText('MAGNITUDE ONLY', iCenterX, iCenterY + 48);
            } else {
              // Vector with direction coordinate arrows
              ctx.strokeStyle = theme.colors.border;
              ctx.lineWidth = 1.5;
              // X and Y axes
              ctx.beginPath();
              ctx.moveTo(iCenterX - 36, iCenterY + 16);
              ctx.lineTo(iCenterX + 36, iCenterY + 16);
              ctx.moveTo(iCenterX - 24, iCenterY + 28);
              ctx.lineTo(iCenterX - 24, iCenterY - 36);
              ctx.stroke();

              // Directed vector arrow
              theme.drawOutlinedArrow(ctx, iCenterX - 24, iCenterY + 16, iCenterX + 28, iCenterY - 26, 10, theme.colors.coral, theme.colors.border, 2);

              ctx.font = `800 14px ${font}`;
              ctx.fillStyle = theme.colors.coral;
              ctx.textAlign = 'center';
              ctx.fillText('v\u20D7 (VECTOR)', iCenterX, iCenterY + 34);
              ctx.font = `700 11px ${font}`;
              ctx.fillStyle = theme.colors.muted;
              ctx.fillText('MAGNITUDE + DIR', iCenterX, iCenterY + 48);
            }
          } else {
            // Case C: no matching picture, so the box carries the side's own name instead of a stock emblem
            const side = String(colLabels[c] || '');
            const fitSide = theme.fitText(ctx, side, { width: illusW - 24, height: illusH - 40 }, 26, 13, 800, lang, { label: 'compare.side' });
            ctx.font = `800 ${fitSide.fontSize}px ${font}`;
            ctx.fillStyle = isLeftCard ? theme.colors.accent : '#92400E';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            const sideTop = iCenterY - 10 - (fitSide.lines.length * fitSide.lineHeight) / 2;
            fitSide.lines.forEach((line, k) => ctx.fillText(line, iCenterX, sideTop + k * fitSide.lineHeight));
          }
          ctx.restore();

          // Render structured bullet points
          let curStepY = startY + 68;
          colSteps.forEach((st, sIdx) => {
            const pointTag = `POINT 0${sIdx + 1} ${isLeftCard ? 'A' : 'B'}`;
            const tagW = theme.drawPill(ctx, pointTag, textX, curStepY, {
              bg: isLeftCard ? '#DBEAFE' : '#FEF3C7',
              color: theme.colors.text,
              border: theme.colors.border,
              lineWidth: 1.25,
              height: 22,
              fontSize: 10,
              weight: 800,
              font,
              bracketed: true
            });

            const fitStep = theme.fitText(ctx, st, { width: textW, height: 75 }, 15, 12, 500, lang, { label: 'compare.step' });
            ctx.font = `500 ${fitStep.fontSize}px ${font}`;
            ctx.fillStyle = theme.colors.text;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';

            const tagGap = tagW ? 28 : 0;
            theme.drawFittedLines(ctx, fitStep, textX, curStepY + tagGap);
            curStepY += tagGap + fitStep.lines.length * fitStep.lineHeight + 14;
          });
        } else {
          // 3-Column layout
          let curStepY = startY + 74;
          colSteps.forEach((st, sIdx) => {
            ctx.fillStyle = colColor;
            ctx.beginPath();
            ctx.arc(cx + 26, curStepY + 10, 5, 0, Math.PI * 2);
            ctx.fill();

            const fitStep = theme.fitText(ctx, st, { width: colW - 56, height: 75 }, 16, 12, 500, lang);
            ctx.font = `500 ${fitStep.fontSize}px ${font}`;
            ctx.fillStyle = theme.colors.text;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';

            theme.drawFittedLines(ctx, fitStep, cx + 40, curStepY);
            curStepY += fitStep.lines.length * fitStep.lineHeight + 16;
          });
        }
      }

      // Draw central circular "VS" badges between columns
      ctx.globalAlpha = pHeader;
      for (let c = 0; c < colCount - 1; c++) {
        const vsX = 64 + (c + 1) * colW + c * gap + gap / 2;
        const vsY = startY + totalH / 2;

        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(vsX - gap / 2, vsY);
        ctx.lineTo(vsX + gap / 2, vsY);
        ctx.stroke();

        ctx.fillStyle = theme.colors.border;
        ctx.beginPath();
        ctx.arc(vsX, vsY, 24, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = `800 16px ${font}`;
        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('VS', vsX, vsY);
      }

      ctx.restore();
    },

    // -------------------------------------------------------------------------
    // 4. EQUATION TEMPLATE (Dynamic formula, variable definitions, and contextual derivation)
    // -------------------------------------------------------------------------
    equation(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pHeader;

      const formula = labels[0] || 'I = V / R';
      const kicker = (labels[1] && !labels[1].includes(':')) ? labels[1] : 'MATHEMATICAL LAW';
      const headerInfo = drawEditorialHeader(ctx, kicker, `Formula: ${formula}`, theme, lang, 64, 70, 1152);

      const startY = headerInfo.bottomY + 12;

      // Split layout: Left (Formula + Variable Definitions, 640px), Right (Worked Steps / Principles, 484px)
      const leftW = 640;
      const rightW = 484;
      const rightX = 64 + leftW + 28;

      // 1. Left Top: Formula Container Box
      const pFormula = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.6)));
      ctx.globalAlpha = pFormula;

      const boxH = 148;
      theme.drawCard(ctx, 64, startY, leftW, boxH, 16, '#FFFFFF', theme.colors.border, 2.5);

      theme.drawPill(ctx, 'MATHEMATICAL RELATIONSHIP', 84, startY + 14, {
        bg: theme.colors.kickerBg,
        color: theme.colors.text,
        border: theme.colors.border,
        lineWidth: 1.5,
        height: 24,
        fontSize: 11,
        weight: 700,
        font,
        bracketed: true
      });

      // Operator-aware equation tokenization (supports implicit multiplication, exponents, fractions, parentheses, operators)
      function parseFormula(str) {
        if (!str) return [];
        let clean = str.replace(/²/g, '^2').replace(/³/g, '^3').trim();
        const raw = clean.split(/(\s+|[=+\-×*\/÷()])/).map(t => t.trim()).filter(Boolean);
        const tokens = [];

        function splitImplicitMultiplication(tokenStr, expVal = null) {
          // Preserve indexed variables like m1, r2, v0 as atomic
          if (/^[A-Za-z\u0370-\u03FF]\d+$/.test(tokenStr)) {
            return [{ type: 'variable', text: tokenStr, exp: expVal }];
          }
          // Preserve math function names
          if (/^(sin|cos|tan|log|ln|exp|sqrt)$/i.test(tokenStr)) {
            return [{ type: 'operator', text: tokenStr }];
          }
          // Split contiguous single-letter variables in implicit products (e.g. 'ma', 'mc', 'IR', 'mg', 'qv')
          if (/^[A-Za-z\u0370-\u03FF]+$/.test(tokenStr) && tokenStr.length > 1) {
            const letters = tokenStr.split('');
            return letters.map((ch, idx) => {
              const isLast = idx === letters.length - 1;
              return {
                type: 'variable',
                text: ch,
                exp: isLast ? expVal : null
              };
            });
          }
          return [{ type: 'variable', text: tokenStr, exp: expVal }];
        }

        for (let i = 0; i < raw.length; i++) {
          const t = raw[i];
          if (t.includes('^')) {
            const parts = t.split('^');
            const subTokens = splitImplicitMultiplication(parts[0], parts[1]);
            tokens.push(...subTokens);
          } else if (i + 2 < raw.length && raw[i + 1] === '^') {
            const subTokens = splitImplicitMultiplication(t, raw[i + 2]);
            tokens.push(...subTokens);
            i += 2;
          } else if (['=', '+', '-', '*', '×', '/', '÷', '(', ')'].includes(t)) {
            tokens.push({ type: 'operator', text: t === '*' ? '×' : (t === '/' ? '÷' : t) });
          } else if (/^\d+(\.\d+)?$/.test(t)) {
            if (i + 2 < raw.length && (raw[i + 1] === '/' || raw[i + 1] === '÷') && /^\d+$/.test(raw[i + 2])) {
              tokens.push({ type: 'number', text: t + '/' + raw[i + 2] });
              i += 2;
            } else {
              tokens.push({ type: 'number', text: t });
            }
          } else {
            const subTokens = splitImplicitMultiplication(t, null);
            tokens.push(...subTokens);
          }
        }
        return tokens;
      }

      const formulaTokens = parseFormula(formula);
      const tokenColors = [theme.colors.accent, theme.colors.coral, theme.colors.amber, theme.colors.green, theme.colors.indigo];

      // Estimate total width to auto-scale if formula is long
      const availableW = leftW - 44;
      let estW = 0;
      formulaTokens.forEach(tok => {
        if (tok.type === 'operator') {
          estW += tok.text === '(' || tok.text === ')' ? 18 : 28;
        } else if (tok.type === 'number') {
          estW += Math.max(38, tok.text.length * 14 + 18);
        } else {
          estW += Math.max(48, tok.text.length * 16 + 24 + (tok.exp ? 16 : 0));
        }
        estW += 8;
      });

      const eqScale = estW > availableW ? Math.max(0.68, availableW / estW) : 1.0;
      const baseFontSize = Math.round(28 * eqScale);
      const expFontSize = Math.round(18 * eqScale);
      const tokH = Math.round(58 * eqScale);
      const tokY = startY + 52 + Math.round((58 - tokH) / 2);

      let tokX = 84;
      let varTokenCount = 0;

      formulaTokens.forEach((tok) => {
        if (tok.type === 'operator') {
          const opW = Math.round((tok.text === '(' || tok.text === ')' ? 18 : 28) * eqScale);
          ctx.font = `800 ${Math.round(30 * eqScale)}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(tok.text, tokX + opW / 2, tokY + tokH / 2);
          tokX += opW + Math.round(6 * eqScale);
        } else if (tok.type === 'number') {
          ctx.font = `800 ${baseFontSize}px ${font}`;
          const numW = Math.max(Math.round(36 * eqScale), ctx.measureText(tok.text).width + Math.round(18 * eqScale));
          theme.drawCard(ctx, tokX, tokY, numW, tokH, 10, '#F1F5F9', theme.colors.border, 2);
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(tok.text, tokX + numW / 2, tokY + tokH / 2);
          tokX += numW + Math.round(8 * eqScale);
        } else {
          const col = tokenColors[varTokenCount % tokenColors.length];
          const isAmber = col === theme.colors.amber;
          varTokenCount++;

          ctx.font = `800 ${baseFontSize}px ${font}`;
          const baseW = ctx.measureText(tok.text).width;
          let expW = 0;
          if (tok.exp) {
            ctx.font = `800 ${expFontSize}px ${font}`;
            expW = ctx.measureText(tok.exp).width;
          }
          const tokW = Math.max(Math.round(46 * eqScale), baseW + expW + Math.round(22 * eqScale));

          theme.drawCard(ctx, tokX, tokY, tokW, tokH, 12, col, theme.colors.border, 2);
          ctx.fillStyle = isAmber ? '#0F172A' : '#FFFFFF';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';

          if (tok.exp) {
            const contentW = baseW + expW + 2;
            const startContentX = tokX + (tokW - contentW) / 2;
            ctx.font = `800 ${baseFontSize}px ${font}`;
            ctx.textAlign = 'left';
            ctx.fillText(tok.text, startContentX, tokY + tokH / 2);
            ctx.font = `800 ${expFontSize}px ${font}`;
            ctx.fillText(tok.exp, startContentX + baseW + 2, tokY + tokH / 2 - Math.round(8 * eqScale));
          } else {
            ctx.font = `800 ${baseFontSize}px ${font}`;
            ctx.fillText(tok.text, tokX + tokW / 2, tokY + tokH / 2);
          }
          tokX += tokW + Math.round(8 * eqScale);
        }
      });

      // 2. Extract Variable Definitions dynamically from labels and steps
      const varDefs = [];
      const nonDefSteps = [];

      function parseDefinition(str) {
        if (!str) return null;
        const m = str.match(/^([A-Za-z0-9_'\u0370-\u03FF]+)\s*[:—\-]\s*(.+)$/);
        if (m) {
          return { symbol: m[1].trim(), desc: m[2].trim() };
        }
        return null;
      }

      // Check labels (slice 1) for variable definitions
      for (let i = 1; i < labels.length; i++) {
        const parsed = parseDefinition(labels[i]);
        if (parsed) {
          varDefs.push(parsed);
        }
      }

      // Check steps for definitions vs explanatory steps
      const nonVarPrefixes = ['step', 'given', 'result', 'formula', 'equation', 'calc', 'calculation', 'sub', 'substitution', 'conclusion', 'solution', 'rule'];
      steps.forEach(st => {
        const parsed = parseDefinition(st);
        const isExplanatoryPrefix = nonVarPrefixes.some(p => st.toLowerCase().startsWith(p));
        if (parsed && parsed.symbol.length <= 3 && !isExplanatoryPrefix) {
          varDefs.push(parsed);
        } else {
          nonDefSteps.push(st);
        }
      });

      // 3. Left Bottom: Variable Definitions Card
      const pDefs = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.15) / 0.6))));
      ctx.globalAlpha = pDefs;

      const defsY = startY + boxH + 16;
      const defsH = 585 - defsY;
      theme.drawCard(ctx, 64, defsY, leftW, defsH, 16, '#FFFFFF', theme.colors.border, 2);

      if (varDefs.length > 5) {
        theme.reportCapacityViolation('equation', 'variable_definitions', varDefs.length, 5);
      }
      if (nonDefSteps.length > 5) {
        theme.reportCapacityViolation('equation', 'worked_steps', nonDefSteps.length, 5);
      }
      const hasDefs = varDefs.length > 0;
      theme.drawPill(ctx, hasDefs ? 'VARIABLE DEFINITIONS' : 'FORMULA SPECIFICATION', 84, defsY + 14, {
        bg: '#F1F5F9',
        color: theme.colors.text,
        border: theme.colors.border,
        lineWidth: 1.5,
        height: 24,
        fontSize: 11,
        weight: 700,
        font,
        bracketed: true
      });

      if (hasDefs) {
        const displayDefs = varDefs.slice(0, 5);
        const defCount = displayDefs.length;
        const availH = defsH - 52;
        const rowH = Math.min(48, Math.floor(availH / defCount));
        const pillH = defCount >= 5 ? 26 : (defCount === 4 ? 28 : 32);
        const pillFont = defCount >= 5 ? 12 : (defCount === 4 ? 13 : 14);

        displayDefs.forEach((vd, vIdx) => {
          const vy = defsY + 44 + vIdx * rowH;
          const color = tokenColors[vIdx % tokenColors.length];
          const isAmber = color === theme.colors.amber;

          // Colored Variable Pill
          theme.drawPill(ctx, vd.symbol, 84, vy, {
            bg: color,
            color: isAmber ? '#0F172A' : '#FFFFFF',
            border: theme.colors.border,
            lineWidth: 1.5,
            height: pillH,
            fontSize: pillFont,
            weight: 800,
            font,
            bracketed: false
          });

          // Definition Text (minimum 12px)
          const fitDef = theme.fitText(ctx, vd.desc, { width: leftW - 170, height: rowH - 4 }, defCount >= 5 ? 14 : 16, 12, 600, lang);
          ctx.font = `600 ${fitDef.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';
          const defTopY = vy + Math.max(2, Math.round((pillH - fitDef.lines.length * fitDef.lineHeight) / 2));
          theme.drawFittedLines(ctx, fitDef, 148, defTopY);
        });
      } else {
        // Fallback: Formula Overview when definitions are not provided
        ctx.font = `600 16px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        const fallbackDesc = `Core mathematical equation governing relationships between physical quantities in this domain.`;
        const fitFDesc = theme.fitText(ctx, fallbackDesc, { width: leftW - 40, height: defsH - 60 }, 16, 13, 500, lang);
        theme.drawFittedLines(ctx, fitFDesc, 84, defsY + 54);
      }

      // 4. Right Column: Dynamic Worked Steps or Principles (Zero fabricated Ohm's Law numbers)
      const pRight = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.25) / 0.6))));
      ctx.globalAlpha = pRight;

      const rightH = 585 - startY;
      theme.drawCard(ctx, rightX, startY, rightW, rightH, 16, '#FFFFFF', theme.colors.border, 2.5);

      // Determine Right Column Mode:
      // Mode 1: Genuine Worked Example (if steps contain numerical or calculation stages)
      // Mode 2: Derived Equations (if steps contain equations like "I = V / R", "R = V / I")
      // Mode 3: Conceptual Principles (if steps contain physical principles)
      // Mode 4: Formula Insight Fallback

      const hasCalculation = nonDefSteps.some(s => {
        const sl = s.toLowerCase();
        return sl.includes('given') || sl.includes('substitut') || sl.includes('result') || sl.includes('answer') || sl.includes('calc') || /=\s*[0-9]/.test(s);
      });
      const hasDerivedEquations = nonDefSteps.length > 0 && nonDefSteps.every(s => s.includes('='));

      if (hasCalculation) {
        // Mode 1: Genuine Worked Steps
        theme.drawPill(ctx, 'WORKED CALCULATION', rightX + 20, startY + 16, {
          bg: theme.colors.kickerBg,
          color: theme.colors.text,
          border: theme.colors.border,
          lineWidth: 1.5,
          height: 26,
          fontSize: 12,
          weight: 800,
          font,
          bracketed: true
        });

        let curStepY = startY + 54;
        const displaySteps = nonDefSteps.slice(0, 5);
        const sCount = displaySteps.length;
        const stepGap = sCount >= 5 ? 8 : (sCount === 4 ? 10 : 12);

        displaySteps.forEach((st, sIdx) => {
          const thisCardH = sCount >= 5 ? 46 : (sCount === 4 ? 52 : (sIdx === sCount - 1 && sCount > 1 ? 70 : 58));
          const bgCol = sIdx === 2 ? '#FEF3C7' : '#F8FAFC';
          theme.drawCard(ctx, rightX + 20, curStepY, rightW - 40, thisCardH, 10, bgCol, theme.colors.border, 1.5);

          const stepLabel = `STEP 0${sIdx + 1}`;
          ctx.font = `800 ${sCount >= 5 ? 10 : 11}px ${font}`;
          ctx.fillStyle = theme.colors.muted;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';
          ctx.fillText(stepLabel, rightX + 34, curStepY + (sCount >= 5 ? 6 : 8));

          const fitStep = theme.fitText(ctx, st, { width: rightW - 68, height: thisCardH - (sCount >= 5 ? 20 : 24) }, sCount >= 5 ? 13 : 15, 12, 700, lang);
          ctx.font = `700 ${fitStep.fontSize}px ${font}`;
          ctx.fillStyle = sIdx === 2 ? theme.colors.coral : theme.colors.text;
          theme.drawFittedLines(ctx, fitStep, rightX + 34, curStepY + (sCount >= 5 ? 20 : 24));

          curStepY += thisCardH + stepGap;
        });

        const pillH = sCount >= 5 ? 38 : 46;
        const pillY = Math.min(curStepY + 4, startY + rightH - (pillH + 8));
        theme.drawCard(ctx, rightX + 20, pillY, rightW - 40, pillH, 10, theme.colors.accent, theme.colors.border, 2);
        ctx.font = `800 ${sCount >= 5 ? 12 : 13}px ${font}`;
        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Mathematical solution verified through direct substitution.', rightX + rightW / 2, pillY + Math.round(pillH / 2));

      } else if (hasDerivedEquations) {
        // Mode 2: Derived Forms (e.g. golden Ohm's Law fixture steps: "I = V / R", "R = V / I")
        theme.drawPill(ctx, 'DERIVED FORMS & APPLICATIONS', rightX + 20, startY + 16, {
          bg: theme.colors.kickerBg,
          color: theme.colors.text,
          border: theme.colors.border,
          lineWidth: 1.5,
          height: 26,
          fontSize: 12,
          weight: 800,
          font,
          bracketed: true
        });

        let curStepY = startY + 54;
        const displayDF = nonDefSteps.slice(0, 4);
        const dfCardH = displayDF.length >= 4 ? 48 : 64;
        displayDF.forEach((df, dIdx) => {
          theme.drawCard(ctx, rightX + 20, curStepY, rightW - 40, dfCardH, 10, '#F8FAFC', theme.colors.border, 1.5);

          const fitDF = theme.fitText(ctx, df, { width: rightW - 68, height: 44 }, 18, 14, 800, lang);
          ctx.font = `800 ${fitDF.fontSize}px ${font}`;
          ctx.fillStyle = dIdx === 0 ? theme.colors.accent : theme.colors.coral;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(df, rightX + rightW / 2, curStepY + 32);

          curStepY += dfCardH + 10;
        });

        const pillY = Math.min(curStepY + 12, startY + rightH - 58);
        theme.drawCard(ctx, rightX + 20, pillY, rightW - 40, 46, 10, theme.colors.accent, theme.colors.border, 2);
        const noteText = lang === 'hi'
          ? 'अज्ञात मान के लिए सूत्र को पुनर्व्यवस्थित करें।'
          : (lang === 'kn' ? 'ಅಜ್ಞಾತ ಮೌಲ್ಯಕ್ಕಾಗಿ ಸೂತ್ರವನ್ನು ಮರುಹೊಂದಿಸಿ.' : 'Rearrange formula to solve for any parameter.');
        const fitNote = theme.fitText(ctx, noteText, { width: rightW - 64, height: 38 }, 12, 10, 700, lang);
        ctx.font = `700 ${fitNote.fontSize}px ${font}`;
        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        const totalNoteH = fitNote.lines.length * fitNote.lineHeight;
        const noteStartY = pillY + (46 - totalNoteH) / 2;
        theme.drawFittedLines(ctx, fitNote, rightX + rightW / 2, noteStartY, { align: 'center' });

      } else if (nonDefSteps.length > 0) {
        // Mode 3: Key Principles / Explanations
        theme.drawPill(ctx, 'KEY PRINCIPLES & APPLICATIONS', rightX + 20, startY + 16, {
          bg: theme.colors.kickerBg,
          color: theme.colors.text,
          border: theme.colors.border,
          lineWidth: 1.5,
          height: 26,
          fontSize: 12,
          weight: 800,
          font,
          bracketed: true
        });

        let curStepY = startY + 54;
        const displayPSteps = nonDefSteps.slice(0, 4);
        const pCardH = displayPSteps.length >= 4 ? 50 : 66;
        displayPSteps.forEach((st, sIdx) => {
          theme.drawCard(ctx, rightX + 20, curStepY, rightW - 40, pCardH, 10, '#F8FAFC', theme.colors.border, 1.5);

          const fitSt = theme.fitText(ctx, st, { width: rightW - 68, height: 50 }, 15, 12, 600, lang);
          ctx.font = `600 ${fitSt.fontSize}px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';
          theme.drawFittedLines(ctx, fitSt, rightX + 34, curStepY + 20);

          curStepY += pCardH + 10;
        });

        const pillY = Math.min(curStepY + 10, startY + rightH - 58);
        theme.drawCard(ctx, rightX + 20, pillY, rightW - 40, 46, 10, theme.colors.accent, theme.colors.border, 2);
        ctx.font = `800 13px ${font}`;
        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Direct physical consequence of the underlying scientific law.', rightX + rightW / 2, pillY + 23);

      } else {
        // Mode 4: Formula Overview (when no steps supplied)
        theme.drawPill(ctx, 'FORMULA DETAILS & USAGE', rightX + 20, startY + 16, {
          bg: theme.colors.kickerBg,
          color: theme.colors.text,
          border: theme.colors.border,
          lineWidth: 1.5,
          height: 26,
          fontSize: 12,
          weight: 800,
          font,
          bracketed: true
        });

        theme.drawCard(ctx, rightX + 20, startY + 54, rightW - 40, 100, 10, '#F8FAFC', theme.colors.border, 1.5);
        ctx.font = `800 24px ${font}`;
        ctx.fillStyle = theme.colors.accent;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(formula, rightX + rightW / 2, startY + 104);

        const pillY = startY + rightH - 58;
        theme.drawCard(ctx, rightX + 20, pillY, rightW - 40, 46, 10, theme.colors.accent, theme.colors.border, 2);
        ctx.font = `800 13px ${font}`;
        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Apply with consistent SI units to compute unknown values.', rightX + rightW / 2, pillY + 23);
      }

      ctx.restore();
    },

    // -------------------------------------------------------------------------
    // 5. FLOW TEMPLATE (Reference 1: Horizontal colored cards with numerals & connecting chevrons)
    // -------------------------------------------------------------------------
    flow(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pHeader;

      const isStageString = (s) => /^(?:step|stage|phase|node|\d+[\.\:\)\-]|#\d+)/i.test(String(s).trim()) || String(s).includes(':') || String(s).includes('=') || String(s).includes('→') || String(s).includes('->');

      let mainTitle = 'Process Workflow';
      let kicker = 'PROCESS PIPELINE';
      let rawNodes = [];
      let outcomeText = '';

      if (steps && steps.length >= 2) {
        // Case 1: steps array explicitly contains the workflow stages
        rawNodes = steps;
        if (labels && labels.length > 0) mainTitle = labels[0];
        if (labels && labels.length > 1) kicker = labels[1];
        outcomeText = steps.length > 5 ? steps[steps.length - 1] : (labels[2] || '');
      } else {
        // Case 2: labels array contains the workflow stages (or title + stages)
        if (steps && steps.length === 1) {
          outcomeText = steps[0];
        }

        if (labels && labels.length > 0) {
          if (labels.length === 1) {
            rawNodes = labels;
          } else {
            const firstIsStage = isStageString(labels[0]);
            const secondIsStage = isStageString(labels[1]);

            if (!firstIsStage && secondIsStage && labels.length > 2) {
              // labels[0] is title, labels[1..] are stages
              mainTitle = labels[0];
              kicker = 'STEP-BY-STEP';
              rawNodes = labels.slice(1);
            } else {
              // All items in labels are stages
              rawNodes = labels.slice();
              mainTitle = 'Process Workflow';
              kicker = 'PROCESS EXECUTION';
            }
          }
        } else if (steps && steps.length > 0) {
          rawNodes = steps;
        } else {
          rawNodes = ['Step 1', 'Step 2', 'Step 3', 'Step 4'];
        }
      }

      if (!outcomeText) {
        outcomeText = steps && steps.length > 0 ? steps[steps.length - 1] : 'Deterministic transformation through sequential stages.';
      }

      const headerInfo = drawEditorialHeader(ctx, kicker, mainTitle, theme, lang, 64, 70, 1152);

      // Support up to 6 nodes without dropping content
      if (rawNodes.length > 6) {
        theme.reportCapacityViolation('flow', 'flow_nodes', rawNodes.length, 6);
      }
      const count = Math.min(6, Math.max(1, rawNodes.length));

      const cardColors = [
        theme.colors.accent, // 01 Blue (#2563EB)
        theme.colors.amber,  // 02 Amber (#F59E0B)
        theme.colors.coral,  // 03 Coral (#EF4444)
        theme.colors.green,  // 04 Green (#10B981)
        theme.colors.indigo, // 05 Indigo (#6366F1)
        '#0D9488'            // 06 Teal (#0D9488)
      ];

      const startY = headerInfo.bottomY + 14;
      const totalAvailableW = 1152;

      let gap, cardW;
      if (count === 6) {
        gap = 14;
        cardW = Math.floor((totalAvailableW - (count - 1) * gap) / count); // 180
      } else if (count === 5) {
        gap = 18;
        cardW = Math.floor((totalAvailableW - (count - 1) * gap) / count); // 216
      } else if (count === 4) {
        gap = 24;
        cardW = Math.floor((totalAvailableW - (count - 1) * gap) / count); // 270
      } else if (count === 3) {
        gap = 32;
        cardW = Math.floor((totalAvailableW - (count - 1) * gap) / count); // 362
      } else if (count === 2) {
        gap = 40;
        cardW = Math.floor((totalAvailableW - (count - 1) * gap) / count); // 556
      } else {
        gap = 0;
        cardW = 540;
      }

      const cardH = count >= 5 ? 230 : 240;

      for (let i = 0; i < count; i++) {
        const pCard = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.12) / 0.5))));
        ctx.globalAlpha = pCard;

        const cx = 64 + i * (cardW + gap);
        const cy = startY;
        const color = cardColors[i % cardColors.length];
        const isLight = color === theme.colors.amber || color === '#FEF3C7';
        const textColor = isLight ? '#0F172A' : '#FFFFFF';

        // Colored Process Card
        theme.drawCard(ctx, cx, cy, cardW, cardH, 16, color, theme.colors.border, 2.5);

        // Big numeral: 01, 02, ...
        const numeralSize = count >= 5 ? 36 : 48;
        ctx.font = `800 ${numeralSize}px ${font}`;
        ctx.fillStyle = textColor;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(`0${i + 1}`, cx + (count >= 5 ? 14 : 18), cy + (count >= 5 ? 16 : 18));

        // Icon placeholder square in top right of card
        const iconSize = count >= 5 ? 28 : 34;
        const iconX = cx + cardW - iconSize - (count >= 5 ? 14 : 18);
        const iconY = cy + (count >= 5 ? 16 : 20);
        theme.drawCard(ctx, iconX, iconY, iconSize, iconSize, 8, '#FFFFFF', theme.colors.border, 1.5);

        // Mini vector icon inside icon box
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2;
        ctx.beginPath();
        const midX = iconX + iconSize / 2;
        const midY = iconY + iconSize / 2;
        if (i === 0) {
          // Circle / node
          ctx.arc(midX, midY, iconSize >= 34 ? 7 : 6, 0, Math.PI * 2);
        } else if (i === 1) {
          // Book/rect
          const rHalf = (iconSize >= 34 ? 16 : 12) / 2;
          ctx.moveTo(midX - rHalf, midY - rHalf);
          ctx.lineTo(midX + rHalf, midY - rHalf);
          ctx.lineTo(midX + rHalf, midY + rHalf);
          ctx.lineTo(midX - rHalf, midY + rHalf);
          ctx.closePath();
        } else if (i === 2) {
          // Gears circle
          ctx.arc(midX, midY, iconSize >= 34 ? 8 : 6, 0, Math.PI * 2);
        } else if (i === 3) {
          // Checkmark
          ctx.moveTo(midX - 7, midY);
          ctx.lineTo(midX - 2, midY + 5);
          ctx.lineTo(midX + 7, midY - 5);
        } else if (i === 4) {
          // Diamond
          ctx.moveTo(midX, midY - 6);
          ctx.lineTo(midX + 6, midY);
          ctx.lineTo(midX, midY + 6);
          ctx.lineTo(midX - 6, midY);
          ctx.closePath();
        } else {
          // Target concentric
          ctx.arc(midX, midY, 5, 0, Math.PI * 2);
        }
        ctx.stroke();

        // Step title & description extraction
        const rawItem = String(rawNodes[i] || `Step ${i + 1}`);
        let stepTitle = `[ STEP 0${i + 1} ]`;
        let stepDesc = rawItem;

        const colonIdx = rawItem.indexOf(':');
        const dashIdx = rawItem.search(/\s+[-—]\s+/);

        if (colonIdx !== -1) {
          stepTitle = `[ ${rawItem.substring(0, colonIdx).trim()} ]`;
          stepDesc = rawItem.substring(colonIdx + 1).trim();
        } else if (dashIdx !== -1) {
          stepTitle = `[ ${rawItem.substring(0, dashIdx).trim()} ]`;
          stepDesc = rawItem.substring(dashIdx).replace(/^[-—\s]+/, '').trim();
        } else {
          const numMatch = rawItem.match(/^(\d+[\.\)]|\w+\s+\d+)\s*(.*)/i);
          if (numMatch && numMatch[2]) {
            stepTitle = `[ STEP 0${i + 1} ]`;
            stepDesc = numMatch[2].trim();
          }
        }

        const padX = count >= 5 ? 14 : 18;
        const innerW = cardW - padX * 2;
        const titleTop = count >= 5 ? 68 : 82;
        const maxTitleFont = count >= 5 ? 15 : 18;
        const minTitleFont = count >= 5 ? 12 : 14;

        const fitTitle = theme.fitText(ctx, stepTitle, { width: innerW, height: 42 }, maxTitleFont, minTitleFont, 800, lang);
        ctx.font = `800 ${fitTitle.fontSize}px ${font}`;
        ctx.fillStyle = textColor;
        theme.drawFittedLines(ctx, fitTitle, cx + padX, cy + titleTop);

        const descY = cy + titleTop + fitTitle.lines.length * fitTitle.lineHeight + 6;
        const maxDescFont = count >= 5 ? 13 : 15;
        const minDescFont = 12;
        const fitDesc = theme.fitText(ctx, stepDesc, { width: innerW, height: cardH - (descY - cy) - 12 }, maxDescFont, minDescFont, 500, lang);
        ctx.font = `500 ${fitDesc.fontSize}px ${font}`;
        ctx.fillStyle = textColor;
        theme.drawFittedLines(ctx, fitDesc, cx + padX, descY);

        // Connecting chevron arrows between cards
        if (i < count - 1) {
          const arrowX1 = cx + cardW + 2;
          const arrowX2 = cx + cardW + gap - 2;
          const arrowY = cy + cardH / 2;
          const arrowSize = count >= 5 ? 10 : 14;
          theme.drawOutlinedArrow(ctx, arrowX1, arrowY, arrowX2, arrowY, arrowSize, '#FAF7EE', theme.colors.border, 2);
        }
      }

      // Bottom: [ RESULT OR OUTCOME ] Box
      const pOutcome = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.3) / 0.5))));
      ctx.globalAlpha = pOutcome;

      const outY = startY + cardH + 16;
      const outH = Math.min(120, 585 - outY);
      const outW = Math.min(1152, count * (cardW + gap) - gap);

      theme.drawCard(ctx, 64, outY, outW, outH, 14, '#FFFFFF', theme.colors.border, 1.5);
      ctx.font = `800 13px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText('[ RESULT OR OUTCOME ]', 84, outY + 12);

      const fitOutcome = theme.fitText(ctx, outcomeText, { width: outW - 40, height: outH - 34 }, 16, 12, 500, lang);
      ctx.font = `500 ${fitOutcome.fontSize}px ${font}`;
      ctx.fillStyle = theme.colors.muted;
      theme.drawFittedLines(ctx, fitOutcome, 84, outY + 34);

      ctx.restore();
    },

    // -------------------------------------------------------------------------
    // 6. LABELED DIAGRAM TEMPLATE (Reference 2: Central system diagram with leader lines to callout cards)
    // -------------------------------------------------------------------------
    labeled_diagram(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pHeader;

      const sysName = labels[0] || 'Central System';
      const kicker = labels[1] || 'DIAGRAM TYPE';
      const headerInfo = drawEditorialHeader(ctx, kicker, sysName, theme, lang, 64, 70, 1152);

      const rawCallouts = labels.slice(1).length > 0 ? labels.slice(1) : steps.slice(0, 5);
      if (rawCallouts.length > 6) {
        theme.reportCapacityViolation('labeled_diagram', 'callout_nodes', rawCallouts.length, 6);
      }
      const callouts = rawCallouts;
      const calloutCount = Math.min(6, Math.max(1, callouts.length));

      const startY = headerInfo.bottomY + 8;

      // 1. Central Diagram Schematic Placeholder
      const pCenter = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.6)));
      ctx.globalAlpha = pCenter;

      const centerAreaX = 490;
      const centerAreaY = startY + 10;
      const centerAreaW = 300;
      const centerAreaH = 360;

      // Dynamic Schematic System Header
      const centerTitle = (labels[0] || 'SYSTEM SCHEMATIC').toUpperCase();
      theme.drawPill(ctx, `[ ${centerTitle} ]`, centerAreaX + 15, centerAreaY, {
        bg: '#FFFFFF',
        color: theme.colors.text,
        border: theme.colors.border,
        lineWidth: 1.5,
        height: 26,
        fontSize: 12,
        weight: 800,
        font,
        bracketed: false
      });

      // Topic-Neutral High-Precision System Schematic (Core Nexus, Telemetry Grid, Buses)
      const nodeColors = [theme.colors.accent, theme.colors.amber, theme.colors.coral];
      const nodeYs = [centerAreaY + 70, centerAreaY + 160, centerAreaY + 250];
      const nodeCenterX = centerAreaX + centerAreaW / 2;

      // Coordinate telemetry grid crosshairs
      ctx.strokeStyle = '#E2E8F0';
      ctx.lineWidth = 1.5;
      if (typeof ctx.setLineDash === 'function') ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(nodeCenterX, centerAreaY + 40);
      ctx.lineTo(nodeCenterX, centerAreaY + 320);
      ctx.moveTo(centerAreaX, centerAreaY + 160);
      ctx.lineTo(centerAreaX + centerAreaW, centerAreaY + 160);
      ctx.stroke();
      if (typeof ctx.setLineDash === 'function') ctx.setLineDash([]);

      // 3 Concentric Nodes stacked vertically with core nexus
      nodeYs.forEach((ny, nIdx) => {
        const col = nodeColors[nIdx];
        // Outer telemetry ring
        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(nodeCenterX, ny, 32, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Inner solid colored circle
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.arc(nodeCenterX, ny, 22, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Core reticle point
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(nodeCenterX, ny, 6, 0, Math.PI * 2);
        ctx.fill();
      });

      // Orbital dashed flow lines between nodes
      ctx.strokeStyle = theme.colors.border;
      ctx.lineWidth = 2;
      if (typeof ctx.setLineDash === 'function') ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(nodeCenterX, centerAreaY + 160, 68, Math.PI * 0.3, Math.PI * 1.7);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(nodeCenterX, centerAreaY + 160, 68, Math.PI * 1.8, Math.PI * 0.2);
      ctx.stroke();
      if (typeof ctx.setLineDash === 'function') ctx.setLineDash([]);

      // Central stage interface blocks connecting buses
      const loopBoxes = [];  // the BUS-L / BUS-R / NEXUS schematic was invented chrome, not lesson content
      loopBoxes.forEach(b => {
        theme.drawCard(ctx, b.x, b.y, b.w, b.h, 8, '#FFFFFF', theme.colors.border, 1.5);
        ctx.font = `700 10px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(b.label, b.x + b.w / 2, b.y + b.h / 2);
      });

      // 2. Peripheral Callout Cards (Left side: 1..3, Right side: 4..6)
      const leftCount = Math.min(3, Math.ceil(calloutCount / 2));
      const rightCount = calloutCount - leftCount;
      const calloutColors = [theme.colors.accent, theme.colors.amber, theme.colors.coral, theme.colors.green, theme.colors.indigo];

      // Left Callout Cards
      const cardW = 330;
      const cardH = 76;
      const cardGap = 16;

      for (let i = 0; i < leftCount; i++) {
        const pCall = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.1) / 0.5))));
        ctx.globalAlpha = pCall;

        const cy = startY + 20 + i * (cardH + cardGap);
        const col = calloutColors[i % calloutColors.length];

        theme.drawCard(ctx, 64, cy, cardW, cardH, 12, '#FFFFFF', theme.colors.border, 1.5);

        // Header label
        const rawLabel = callouts[i] || `Component 0${i + 1}`;
        ctx.font = `700 14px ${font}`;
        ctx.fillStyle = col;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(`[0${i + 1}] [ ${rawLabel} ]`, 78, cy + 12);

        // Function / description
        const desc = steps[i] || 'Component function and subsystem details.';
        const fitDesc = theme.fitText(ctx, desc, { width: cardW - 30, height: 38 }, 14, 12, 500, lang);
        ctx.font = `500 ${fitDesc.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        theme.drawFittedLines(ctx, fitDesc, 78, cy + 34);

        // Anchor Bullet Dot on card right edge
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.arc(64 + cardW, cy + cardH / 2, 5, 0, Math.PI * 2);
        ctx.fill();

        // Orthogonal Leader Line connecting to central schematic (satisfies Test 13 lineTo)
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(64 + cardW, cy + cardH / 2);
        ctx.lineTo(centerAreaX - 60, cy + cardH / 2);
        ctx.stroke();
      }

      // Right Callout Cards
      for (let i = 0; i < rightCount; i++) {
        const idx = leftCount + i;
        const pCall = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - idx * 0.1) / 0.5))));
        ctx.globalAlpha = pCall;

        const cy = startY + 20 + i * (cardH + cardGap);
        const col = calloutColors[idx % calloutColors.length];
        const rx = 1216 - cardW;

        theme.drawCard(ctx, rx, cy, cardW, cardH, 12, '#FFFFFF', theme.colors.border, 1.5);

        // Header label
        const rawLabel = callouts[idx] || `Component 0${idx + 1}`;
        ctx.font = `700 14px ${font}`;
        ctx.fillStyle = col;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(`[0${idx + 1}] [ ${rawLabel} ]`, rx + 14, cy + 12);

        const desc = steps[idx] || 'Component function and subsystem details.';
        const fitDesc = theme.fitText(ctx, desc, { width: cardW - 30, height: 38 }, 14, 12, 500, lang);
        ctx.font = `500 ${fitDesc.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        theme.drawFittedLines(ctx, fitDesc, rx + 14, cy + 34);

        // Anchor Bullet Dot on card left edge
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.arc(rx, cy + cardH / 2, 5, 0, Math.PI * 2);
        ctx.fill();

        // Leader Line connecting to central area
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(rx, cy + cardH / 2);
        ctx.lineTo(centerAreaX + centerAreaW + 15, cy + cardH / 2);
        ctx.stroke();
      }

      // 3. Bottom [ KEY RELATIONSHIP OR PROCESS ] Box
      const pBot = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.3) / 0.5))));
      ctx.globalAlpha = pBot;

      const botY = 485;
      const botW = 480;
      const botH = 96;
      theme.drawCard(ctx, 64, botY, botW, botH, 14, '#FFFFFF', theme.colors.border, 1.5);

      ctx.font = `800 13px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText('[ KEY RELATIONSHIP OR PROCESS ]', 84, botY + 14);

      const relDesc = steps[0] || 'Connecting process flow or architectural relationship explanation.';
      if (steps.length > 1) {
        const chipCount = Math.min(4, steps.length);
        const chipW = Math.round((botW - 40 - (chipCount - 1) * 10) / chipCount);
        for (let s = 0; s < chipCount; s++) {
          const scX = 84 + s * (chipW + 10);
          const scY = botY + 44;
          theme.drawCard(ctx, scX, scY, chipW, 36, 8, theme.colors.kickerBg, theme.colors.border, 1.5);
          ctx.font = `700 12px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(steps[s], scX + chipW / 2, scY + 18);
        }
      } else {
        const fitRel = theme.fitText(ctx, relDesc, { width: botW - 40, height: 48 }, 15, 12, 500, lang);
        ctx.font = `500 ${fitRel.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        theme.drawFittedLines(ctx, fitRel, 84, botY + 36);
      }

      ctx.restore();
    },

    // -------------------------------------------------------------------------
    // 7. TIMELINE TEMPLATE (Reference 3: Horizontal axis with double chevron start, alternating top/bottom cards)
    // -------------------------------------------------------------------------
    timeline(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pHeader;

      const hasSeparateTitle = labels.length > 0 && steps.length > 0 && labels.length !== steps.length && !labels[0].toLowerCase().includes('stage') && !labels[0].toLowerCase().includes('milestone');
      const mainTitle = hasSeparateTitle ? labels[0] : (labels.length === 1 ? labels[0] : 'Historical Timeline');
      const kicker = 'TIMELINE';
      drawEditorialHeader(ctx, kicker, mainTitle, theme, lang, 64, 70, 1152);

      const milestones = hasSeparateTitle && labels.length > 1 ? labels.slice(1) : (labels.length > 0 ? labels : steps);
      const count = Math.min(6, Math.max(1, milestones.length));

      // 1. Horizontal Timeline Axis at y = 356 (satisfies Test 14 fillRect)
      const axisY = 356;
      ctx.fillStyle = theme.colors.border;
      ctx.fillRect(64, axisY - 1.5, 1152, 3);

      // Left Double Chevron start (>>)
      ctx.font = `800 18px ${font}`;
      ctx.fillStyle = theme.colors.border;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('>>', 56, axisY);

      // Right Arrow terminus (>)
      ctx.fillText('>', 1224, axisY);

      // Milestone card parameters (expanded cardH 192px for full Indic text retention)
      const gap = count >= 6 ? 12 : 16;
      const colW = Math.round((1152 - (count - 1) * gap) / count);
      const cardH = 192;

      // Capacity validation: max 6 milestone stages supported
      if (milestones.length > 6) {
        theme.reportCapacityViolation('timeline', 'milestones', milestones.length, 6);
      }

      const headerColors = [
        theme.colors.accent,
        theme.colors.amber,
        theme.colors.coral,
        theme.colors.green,
        theme.colors.indigo,
        '#475569'
      ];

      for (let i = 0; i < count; i++) {
        const isTop = i % 2 === 0;
        const pMilestone = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.12) / 0.5))));
        ctx.globalAlpha = pMilestone;

        const cx = 64 + i * (colW + gap);
        const cy = isTop ? axisY - cardH - 18 : axisY + 18;
        const nodeX = cx + colW / 2;
        const col = headerColors[i % headerColors.length];
        const isAmber = col === theme.colors.amber;

        // Vertical dashed leader line between axis and card
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 1.5;
        if (typeof ctx.setLineDash === 'function') ctx.setLineDash([4, 4]);
        ctx.beginPath();
        if (isTop) {
          ctx.moveTo(nodeX, axisY);
          ctx.lineTo(nodeX, cy + cardH);
        } else {
          ctx.moveTo(nodeX, axisY);
          ctx.lineTo(nodeX, cy);
        }
        ctx.stroke();
        if (typeof ctx.setLineDash === 'function') ctx.setLineDash([]);

        // Milestone Node on axis line
        ctx.fillStyle = col;
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(nodeX, axisY, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Milestone Card Container
        theme.drawCard(ctx, cx, cy, colW, cardH, 14, '#FFFFFF', theme.colors.border, 2);

        // Colored Header Strip: MILESTONE 0X
        theme.drawRoundedRect(ctx, cx, cy, colW, 36, 14, col, theme.colors.border, 2);
        ctx.fillStyle = col;
        ctx.fillRect(cx + 2, cy + 18, colW - 4, 18);

        ctx.font = `800 13px ${font}`;
        ctx.fillStyle = isAmber ? '#0F172A' : '#FFFFFF';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(`MILESTONE 0${i + 1}`, cx + 14, cy + 18);

        // Milestone Content
        const rawM = milestones[i] || `Milestone ${i + 1}`;
        const parts = rawM.split(/:\s*|—\s*|-\s*/);
        const dateTag = parts.length > 1 ? `[ ${parts[0]} ]` : `[ 0${i + 1} ]`;
        const eventTitle = parts.length > 1 ? parts.slice(1).join(': ') : rawM;
        const eventDesc = steps[i] || 'Event description and chronological significance.';

        ctx.font = `800 12px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(dateTag, cx + 12, cy + 42);

        const fitEvent = theme.fitText(ctx, eventTitle, { width: colW - 20, height: 42 }, 15, 12, 700, lang, { label: 'timeline.title' });
        ctx.font = `700 ${fitEvent.fontSize}px ${font}`;
        theme.drawFittedLines(ctx, fitEvent, cx + 12, cy + 58);

        const descY = cy + 54 + fitEvent.lines.length * fitEvent.lineHeight + 4;
        const availDescH = Math.max(65, cardH - (descY - cy) - 4);
        const fitDesc = theme.fitText(ctx, eventDesc, { width: colW - 20, height: availDescH }, 14, 12, 500, lang, { label: 'timeline.desc', breakWords: true });
        ctx.font = `500 ${fitDesc.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        theme.drawFittedLines(ctx, fitDesc, cx + 12, descY);
      }

      ctx.restore();
    },

    // -------------------------------------------------------------------------
    // 8. GRAPH TEMPLATE (Reference 4: Calibrated Bar Chart left, Insight card & Conceptual mode right)
    // -------------------------------------------------------------------------
    graph(ctx, params, lt, dur, theme, lang) {
      const labels = params.labels || [];
      const steps = params.steps || [];
      const font = theme.getFont(lang);

      ctx.save();
      const pHeader = Math.max(0.25, theme.easeOutCubic(Math.min(1, lt / 0.5)));
      ctx.globalAlpha = pHeader;

      const mainTitle = labels[0] || 'Scientific Trend Analysis';
      const kicker = labels[1] || 'GRAPH TYPE';
      const headerInfo = drawEditorialHeader(ctx, kicker, mainTitle, theme, lang, 64, 70, 1152);

      // Check whether structured numerical data is unambiguously available
      const parsedNumericData = [];
      for (const st of steps) {
        const m = String(st).match(/^([^:\(\)]+?)\s*[:\(=]\s*([\d\.]+)\s*(?:[A-Za-zΩ°%]*)\)?$/);
        if (m) {
          const val = parseFloat(m[2]);
          if (!isNaN(val)) parsedNumericData.push({ label: m[1].trim(), value: val });
        }
      }

      const hasStructuredNumeric = parsedNumericData.length >= 2;
      const startY = headerInfo.bottomY + 12;

      if (hasStructuredNumeric) {
        // -------------------------------------------------------------
        // NUMERIC BAR CHART MODE (Reference 4 Left ~65%)
        // -------------------------------------------------------------
        const chartX = 130;
        const chartY = startY + 30;
        const chartW = 650;
        const chartH = 340;
        const chartBottom = chartY + chartH;

        const maxVal = Math.max(...parsedNumericData.map(d => d.value), 1);
        const yAxisLabel = labels[1] || 'Current (A)';
        const xAxisLabel = labels[0] || 'Resistor Type';

        // Y-Axis line
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(chartX, chartY - 10);
        ctx.lineTo(chartX, chartBottom);
        ctx.lineTo(chartX + chartW, chartBottom);
        ctx.stroke();

        // Y-Axis tick marks and subtle grid
        const ticks = 4;
        for (let t = 0; t <= ticks; t++) {
          const ty = chartBottom - (t / ticks) * chartH;
          const tickVal = Math.round((t / ticks) * maxVal);

          ctx.strokeStyle = theme.colors.border;
          ctx.beginPath();
          ctx.moveTo(chartX - 6, ty);
          ctx.lineTo(chartX, ty);
          ctx.stroke();

          // Subtle horizontal grid line
          ctx.strokeStyle = theme.colors.gridLine;
          ctx.beginPath();
          ctx.moveTo(chartX, ty);
          ctx.lineTo(chartX + chartW, ty);
          ctx.stroke();

          ctx.font = `600 12px ${font}`;
          ctx.fillStyle = theme.colors.muted;
          ctx.textAlign = 'right';
          ctx.textBaseline = 'middle';
          ctx.fillText(String(tickVal), chartX - 10, ty);
        }

        // Y-Axis Label rotated
        if (typeof ctx.translate === 'function' && typeof ctx.rotate === 'function') {
          ctx.save();
          ctx.translate(chartX - 52, chartY + chartH / 2);
          ctx.rotate(-Math.PI / 2);
          ctx.font = `700 13px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.fillText(`[ ${yAxisLabel} ]`, 0, 0);
          ctx.restore();
        } else {
          ctx.font = `700 13px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.fillText(`[ ${yAxisLabel} ]`, chartX - 52, chartY + chartH / 2);
        }

        // X-Axis Label bottom
        ctx.font = `700 14px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(`[ ${xAxisLabel} ]`, chartX + chartW / 2, chartBottom + 40);

        // Bars
        const barColors = [theme.colors.accent, theme.colors.amber, theme.colors.coral, theme.colors.green];
        const barCount = parsedNumericData.length;
        const barGap = 40;
        const barWidth = Math.min(100, Math.round((chartW - (barCount + 1) * barGap) / barCount));

        for (let i = 0; i < barCount; i++) {
          const item = parsedNumericData[i];
          const pBar = Math.max(0.1, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - i * 0.12) / 0.5))));
          const targetH = (item.value / maxVal) * (chartH - 20);
          const currentH = targetH * pBar;

          const bx = chartX + barGap + i * (barWidth + barGap);
          const by = chartBottom - currentH;
          const col = barColors[i % barColors.length];

          // Draw outlined solid bar
          theme.drawCard(ctx, bx, by, barWidth, currentH, 6, col, theme.colors.border, 2);

          // Value tag above bar: [ VALUE ]
          ctx.font = `800 13px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'bottom';
          ctx.fillText(`[ ${item.value} ]`, bx + barWidth / 2, by - 6);

          // Category label below axis: [ CATEGORY ]
          ctx.font = `700 13px ${font}`;
          ctx.textBaseline = 'top';
          const fitCat = theme.fitText(ctx, `[ ${item.label} ]`, { width: barWidth + 24, height: 32 }, 13, 11, 700, lang);
          fitCat.lines.forEach((l, lIdx) => {
            ctx.fillText(l, bx + barWidth / 2, chartBottom + 10 + lIdx * fitCat.lineHeight);
          });
        }
      } else {
        // -------------------------------------------------------------
        // CONCEPTUAL MODE (Reference 4 Left ~65%) - Avoids arbitrary curves or fake curves
        // -------------------------------------------------------------
        const chartX = 130;
        const chartY = startY + 30;
        const chartW = 650;
        const chartH = 340;
        const chartBottom = chartY + chartH;

        const yAxisLabel = labels[1] || 'Current (I)';
        const xAxisLabel = labels[0] || 'Voltage (V)';

        // Clean axes
        ctx.strokeStyle = theme.colors.border;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(chartX, chartY - 10);
        ctx.lineTo(chartX, chartBottom);
        ctx.lineTo(chartX + chartW, chartBottom);
        ctx.stroke();

        // Y and X Axis labels
        if (typeof ctx.translate === 'function' && typeof ctx.rotate === 'function') {
          ctx.save();
          ctx.translate(chartX - 52, chartY + chartH / 2);
          ctx.rotate(-Math.PI / 2);
          ctx.font = `700 13px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.fillText(`[ ${yAxisLabel} ]`, 0, 0);
          ctx.restore();
        } else {
          ctx.font = `700 13px ${font}`;
          ctx.fillStyle = theme.colors.text;
          ctx.textAlign = 'center';
          ctx.fillText(`[ ${yAxisLabel} ]`, chartX - 52, chartY + chartH / 2);
        }

        ctx.font = `700 14px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(`[ ${xAxisLabel} ]`, chartX + chartW / 2, chartBottom + 40);

        // Conceptual analysis cards instead of arbitrary 40-step curve
        const pCards = Math.max(0.2, theme.easeOutCubic(Math.min(1, lt / 0.6)));
        ctx.globalAlpha = pCards;

        const conceptH = 100;
        const conceptW = 580;
        theme.drawCard(ctx, chartX + 30, chartY + 30, conceptW, conceptH, 14, '#FFFFFF', theme.colors.border, 2);

        theme.drawPill(ctx, 'CONCEPTUAL ANALYSIS', chartX + 50, chartY + 44, {
          bg: theme.colors.kickerBg,
          color: theme.colors.text,
          border: theme.colors.border,
          lineWidth: 1.5,
          height: 26,
          fontSize: 12,
          weight: 700,
          font,
          bracketed: true
        });

        const conceptDesc = steps[0] || `${xAxisLabel} and ${yAxisLabel} exhibit a direct proportional relationship.`;
        const fitDesc = theme.fitText(ctx, conceptDesc, { width: conceptW - 36, height: 50 }, 16, 12, 600, lang, { label: 'graph.desc' });
        ctx.font = `600 ${fitDesc.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        theme.drawFittedLines(ctx, fitDesc, chartX + 50, chartY + 80);

        // Comparative parameter range indicators
        const paramW = Math.round((conceptW - 20) / 2);
        theme.drawCard(ctx, chartX + 30, chartY + 150, paramW, 110, 12, '#FFFFFF', theme.colors.border, 1.5);
        theme.drawCard(ctx, chartX + 30 + paramW + 20, chartY + 150, paramW, 110, 12, '#FFFFFF', theme.colors.border, 1.5);

        ctx.font = `700 13px ${font}`;
        ctx.fillStyle = theme.colors.accent;
        ctx.fillText(`[ PARAMETER 1: ${xAxisLabel} ]`, chartX + 46, chartY + 166);
        ctx.fillStyle = theme.colors.coral;
        ctx.fillText(`[ PARAMETER 2: ${yAxisLabel} ]`, chartX + 56 + paramW, chartY + 166);

        const subP1 = steps[1] || 'Independent experimental variable input.';
        const fitP1 = theme.fitText(ctx, subP1, { width: paramW - 32, height: 50 }, 14, 12, 500, lang);
        ctx.font = `500 ${fitP1.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        theme.drawFittedLines(ctx, fitP1, chartX + 46, chartY + 194);

        const subP2 = steps[2] || steps[0] || 'Measured physical response in closed circuit.';
        const fitP2 = theme.fitText(ctx, subP2, { width: paramW - 32, height: 50 }, 14, 12, 500, lang);
        ctx.font = `500 ${fitP2.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        theme.drawFittedLines(ctx, fitP2, chartX + 56 + paramW, chartY + 194);
      }

      // -------------------------------------------------------------
      // RIGHT AREA (~35% width: x = 850..1216)
      // -------------------------------------------------------------
      const pRight = Math.max(0.2, theme.easeOutCubic(Math.max(0, Math.min(1, (lt - 0.15) / 0.5))));
      ctx.globalAlpha = pRight;

      const rx = 840;
      const rw = 376;

      // Card 1: INSIGHT / विश्लेषण Card (Satisfies Test 16 & 17 CONCEPTUAL ANALYSIS requirement)
      const insightH = 260;
      theme.drawCard(ctx, rx, startY, rw, insightH, 16, '#FFFFFF', theme.colors.border, 2);

      // Pill: INSIGHT / विश्लेषण / CONCEPTUAL ANALYSIS
      theme.drawPill(ctx, 'INSIGHT / CONCEPTUAL ANALYSIS', rx + 20, startY + 18, {
        bg: theme.colors.kickerBg,
        color: theme.colors.text,
        border: theme.colors.border,
        lineWidth: 1.5,
        height: 26,
        fontSize: 11,
        weight: 700,
        font,
        bracketed: false
      });

      // Key Observation Headline / Data Summary
      const obsTitle = labels[2] || (hasStructuredNumeric ? (labels[1] ? `${labels[1]} Summary` : 'Data Summary') : '');
      let curInsightY = startY + 54;
      if (obsTitle) {
        ctx.font = `800 16px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        const fitObs = theme.fitText(ctx, obsTitle, { width: rw - 40, height: 26 }, 16, 12, 800, lang);
        ctx.fillText(fitObs.lines[0] || obsTitle, rx + 20, curInsightY);
        curInsightY += 28;
      }

      // Trend or takeaway description
      const takeawayText = !hasStructuredNumeric
        ? (steps[0] || '')
        : (steps.length > 0 ? (steps.length > 2 ? `Range: ${steps[0]} to ${steps[steps.length - 1]}` : steps.join(', ')) : '');

      if (takeawayText) {
        const fitTakeaway = theme.fitText(ctx, takeawayText, { width: rw - 36, height: 60 }, 15, 12, 500, lang, { label: 'graph.takeaway' });
        ctx.font = `500 ${fitTakeaway.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        theme.drawFittedLines(ctx, fitTakeaway, rx + 20, curInsightY);
        curInsightY += fitTakeaway.lines.length * fitTakeaway.lineHeight + 14;
      }

      // Why It Matters (render only when meaningful non-numeric explanation is provided)
      const whyText = !hasStructuredNumeric ? (steps[1] || '') : '';
      if (whyText) {
        ctx.font = `800 13px ${font}`;
        ctx.fillStyle = theme.colors.text;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText('[ WHY IT MATTERS ]', rx + 20, curInsightY);

        const fitWhy = theme.fitText(ctx, whyText, { width: rw - 40, height: 50 }, 14, 12, 500, lang);
        ctx.font = `500 ${fitWhy.fontSize}px ${font}`;
        ctx.fillStyle = theme.colors.muted;
        theme.drawFittedLines(ctx, fitWhy, rx + 20, curInsightY + 22);
      }

      // Card 2: Conceptual Mode Indicator Box with curved dashed arrow
      const modeY = startY + insightH + 16;
      const modeH = 585 - modeY;
      ctx.save();
      ctx.strokeStyle = theme.colors.border;
      ctx.lineWidth = 1.5;
      if (typeof ctx.setLineDash === 'function') ctx.setLineDash([5, 5]);
      theme.drawCard(ctx, rx, modeY, rw, modeH, 12, '#FFFFFF', theme.colors.border, 1.5);
      if (typeof ctx.setLineDash === 'function') ctx.setLineDash([]);

      ctx.font = `800 12px ${font}`;
      ctx.fillStyle = theme.colors.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText('[ CONCEPTUAL MODE ]', rx + rw / 2, modeY + 16);

      const varX = labels[0] || 'VARIABLE X';
      const varY = labels[1] || 'VARIABLE Y';
      ctx.font = `700 14px ${font}`;
      ctx.fillStyle = theme.colors.accent;
      ctx.fillText(`[ ${varX} ]  vs  [ ${varY} ]`, rx + rw / 2, modeY + 44);

      // Curved indicator arrow (positioned with margin below the vs text)
      if (typeof ctx.setLineDash === 'function') ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(rx + rw / 2, modeY + 76, 16, Math.PI * 0.9, Math.PI * 1.9);
      ctx.stroke();
      if (typeof ctx.setLineDash === 'function') ctx.setLineDash([]);
      ctx.restore();

      ctx.restore();
    },

    // Code lines and the trace are data. Draw the strings; never eval them.
    code_walkthrough(ctx, params, lt, dur, theme, lang) {
      const rawCode = Array.isArray(params.code) ? params.code : [];
      const rawTrace = Array.isArray(params.trace) ? params.trace : [];
      if (rawCode.length > 12) theme.reportCapacityViolation('code_walkthrough', 'code_lines', rawCode.length, 12);
      if (rawTrace.length > 6) theme.reportCapacityViolation('code_walkthrough', 'trace_steps', rawTrace.length, 6);

      const code = rawCode.slice(0, 12).map(line => String(line).slice(0, 80));
      const trace = rawTrace.slice(0, 6).map(step => ({
        line: Number(step && step.line) || 0,
        vars: (Array.isArray(step && step.vars) ? step.vars : []).slice(0, 4).map(pair => ({
          name: String(pair && pair.name != null ? pair.name : '').slice(0, 24),
          value: String(pair && pair.value != null ? pair.value : '').slice(0, 24)
        }))
      }));

      const span = dur > 0 ? dur : 1;
      const u = Math.max(0, Math.min(Number(lt) || 0, span)) / span;
      const stepIdx = trace.length <= 1 ? 0 : Math.min(trace.length - 1, Math.floor(u * trace.length));
      const step = trace[stepIdx] || { line: 0, vars: [] };
      const labelFont = theme.getFont(lang);
      const codeFont = '"Noto Sans", ui-monospace, Consolas, monospace';
      const cardY = 68;
      const cardH = 516;
      const codeX = 64;
      const codeW = 760;
      const varX = 840;
      const varW = 376;

      ctx.save();
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      theme.drawCard(ctx, codeX, cardY, codeW, cardH, 14);
      theme.drawCard(ctx, varX, cardY, varW, cardH, 14);

      const title = (params.labels && params.labels[0]) || 'Code';
      const titleFit = theme.fitText(ctx, String(title), { width: codeW - 32, height: 28 }, 18, 14, 700, lang, { label: 'code_walkthrough.title' });
      ctx.font = `700 ${titleFit.fontSize}px ${labelFont}`;
      ctx.fillStyle = theme.colors.text;
      theme.drawFittedLines(ctx, titleFit, codeX + 16, cardY + 14);

      const lineH = 36;
      const lineTop = cardY + 52;
      const textX = codeX + 56;
      const textW = codeW - 72;
      code.forEach((line, i) => {
        const rowY = lineTop + i * lineH;
        const active = step.line === i + 1;
        if (active) {
          ctx.fillStyle = '#DBEAFE';
          ctx.fillRect(codeX + 12, rowY - 6, codeW - 24, 32);
        }
        ctx.font = `700 16px ${codeFont}`;
        ctx.fillStyle = active ? theme.colors.accent : theme.colors.muted;
        ctx.fillText(String(i + 1), codeX + 20, rowY);
        ctx.fillStyle = theme.colors.text;
        ctx.font = `600 16px ${codeFont}`;
        if (ctx.measureText(line).width > textW) {
          const fit = theme.fitText(ctx, line, { width: textW, height: 22 }, 16, 12, 600, 'en', { label: 'code_walkthrough.line' });
          ctx.font = `600 ${fit.fontSize}px ${codeFont}`;
          theme.drawFittedLines(ctx, fit, textX, rowY);
        } else {
          ctx.fillText(line, textX, rowY);
        }
      });

      const varTitle = (params.labels && params.labels[1]) || 'Variables';
      const varFit = theme.fitText(ctx, String(varTitle), { width: varW - 32, height: 28 }, 18, 14, 700, lang, { label: 'code_walkthrough.vars' });
      ctx.font = `700 ${varFit.fontSize}px ${labelFont}`;
      ctx.fillStyle = theme.colors.text;
      theme.drawFittedLines(ctx, varFit, varX + 16, cardY + 14);
      ctx.font = `700 14px ${codeFont}`;
      ctx.fillStyle = theme.colors.muted;
      ctx.fillText(trace.length ? (stepIdx + 1) + '/' + trace.length : '0/0', varX + 16, cardY + 48);

      step.vars.forEach((pair, i) => {
        const y = cardY + 84 + i * 48;
        ctx.font = `700 16px ${codeFont}`;
        ctx.fillStyle = theme.colors.accent;
        ctx.fillText(pair.name, varX + 16, y);
        ctx.font = `600 16px ${codeFont}`;
        ctx.fillStyle = theme.colors.text;
        ctx.fillText(pair.value, varX + 16, y + 22);
      });
      ctx.restore();
    },

    quizBoxes() {
      const gap = 16;
      const cardW = (1152 - gap) / 2;
      const cardH = 156;
      const top = 200;
      const left = 64;
      const boxes = [];
      for (let i = 0; i < 4; i++) {
        boxes.push({
          x: left + (i % 2) * (cardW + gap),
          y: top + Math.floor(i / 2) * (cardH + gap),
          w: cardW,
          h: cardH
        });
      }
      return boxes;
    },

    // Question and options are strings. The correct index is data, never executed.
    quiz(ctx, params, lt, dur, theme, lang) {
      const labels = Array.isArray(params.labels) ? params.labels : [];
      const steps = Array.isArray(params.steps) ? params.steps : [];
      const question = labels[0] != null ? String(labels[0]) : '';
      const options = steps.slice(0, 4).map(step => String(step));
      let correctIdx = parseInt(labels[1] != null && labels[1] !== '' ? labels[1] : '0', 10);
      if (!Number.isFinite(correctIdx)) correctIdx = 0;
      if (options.length) correctIdx = Math.max(0, Math.min(options.length - 1, correctIdx));
      const p = dur > 0 ? Math.min(1, Math.max(0, (Number(lt) || 0) / dur)) : 1;
      const tapped = Number.isInteger(params.selectedQuizOption) ? params.selectedQuizOption : null;
      const reveal = tapped == null && p >= 0.65;
      const font = theme.getFont(lang);
      const boxes = this.quizBoxes();

      ctx.save();
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';

      if (tapped == null && p < 0.65) {
        const barW = 1152;
        ctx.fillStyle = '#334155';
        ctx.fillRect(64, 64, barW, 8);
        ctx.fillStyle = '#38BDF8';
        ctx.fillRect(64, 64, barW * (p / 0.65), 8);
      }

      theme.drawCard(ctx, 64, 80, 1152, 104, 14, '#0F172A', '#334155', 2);
      const qFit = theme.fitText(ctx, question, { width: 1100, height: 72 }, 28, 16, 700, lang, { label: 'quiz.question' });
      ctx.font = `700 ${qFit.fontSize}px ${font}`;
      ctx.fillStyle = '#F8FAFC';
      theme.drawFittedLines(ctx, qFit, 84, 96);

      options.forEach((text, i) => {
        const box = boxes[i];
        const showCorrect = (tapped != null && i === correctIdx) || (reveal && i === correctIdx);
        const showWrong = tapped != null && tapped === i && i !== correctIdx;
        const dim = (reveal || tapped != null) && !showCorrect && !showWrong;
        ctx.save();
        if (dim) ctx.globalAlpha = 0.45;
        let fill = '#1E293B';
        let stroke = '#334155';
        if (showCorrect) {
          fill = '#064E3B';
          stroke = '#34D399';
        }
        if (showWrong) {
          fill = '#450A0A';
          stroke = '#F87171';
        }
        theme.drawCard(ctx, box.x, box.y, box.w, box.h, 14, fill, stroke, showCorrect || showWrong ? 3 : 1.5);
        ctx.fillStyle = '#F8FAFC';
        ctx.font = `800 18px ${font}`;
        ctx.fillText(String.fromCharCode(65 + i), box.x + 18, box.y + 16);
        if (showCorrect) ctx.fillText('✓', box.x + box.w - 36, box.y + 16);
        if (showWrong) ctx.fillText('✗', box.x + box.w - 36, box.y + 16);
        const fit = theme.fitText(ctx, text, { width: box.w - 36, height: 72 }, 22, 14, 600, lang, { label: 'quiz.option' });
        ctx.font = `600 ${fit.fontSize}px ${font}`;
        ctx.fillStyle = '#F8FAFC';
        theme.drawFittedLines(ctx, fit, box.x + 18, box.y + 48);
        if (showCorrect) {
          ctx.font = `700 14px ${font}`;
          ctx.fillStyle = '#6EE7B7';
          ctx.fillText('✓ Correct Answer', box.x + 18, box.y + box.h - 28);
        }
        ctx.restore();
      });
      ctx.restore();
    },

    // -------------------------------------------------------------------------
    // Universal Dispatcher with Graceful Fallback to Bullets
    // -------------------------------------------------------------------------
    draw(ctx, type, params, lt, dur, theme, lang) {
      const source = params || {};
      const deduped = type === 'quiz' ? source : Object.assign({}, source, {
        labels: Array.isArray(source.labels) ? [...new Set(source.labels)] : source.labels,
        steps: Array.isArray(source.steps) ? [...new Set(source.steps)] : source.steps
      });
      const lessonCtx = onlyLessonText(ctx, lessonWords(deduped));
      if (typeof this[type] === 'function') {
        try {
          this[type](lessonCtx, deduped, lt, dur, theme, lang);
          return;
        } catch (err) {
          console.warn(`[Templates] Exception in template "${type}", falling back to bullets:`, err);
        }
      }
      this.bullets(lessonCtx, deduped, lt, dur, theme, lang);
    }
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = TEMPLATES;
  } else {
    root.TEMPLATES = TEMPLATES;
  }
})(typeof window !== 'undefined' ? window : globalThis);
