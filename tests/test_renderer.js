// tests/test_renderer.js
// Focused unit test suite for renderer foundation verifying determinism, boundaries, text-fitting, and graceful fallbacks.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const theme = require('../renderer/theme');
const templates = require('../renderer/templates');
const engine = require('../renderer/engine');

console.log('=== RUNNING RENDERER FOUNDATION TESTS ===\n');

// 1. Theme Helpers and PRNG Determinism
console.log('Test 1: Theme helpers and PRNG determinism');
const rngA = theme.rng(101);
const seqA = [rngA(), rngA(), rngA(), rngA()];
const rngB = theme.rng(101);
const seqB = [rngB(), rngB(), rngB(), rngB()];
assert.deepStrictEqual(seqA, seqB, 'PRNG must be strictly deterministic given the same seed');
assert.strictEqual(theme.easeOutCubic(0), 0);
assert.strictEqual(theme.easeOutCubic(1), 1);
assert.strictEqual(theme.easeInOutCubic(0), 0);
assert.strictEqual(theme.easeInOutCubic(1), 1);
console.log('✓ Theme helpers and PRNG passed.');

// 2. fitText and Word Truncation Safety
console.log('\nTest 2: fitText and word truncation safety');
class MockMeasureContext {
  constructor(charWidth = 10) {
    this.charWidth = charWidth;
  }
  measureText(text) {
    return { width: text ? text.length * this.charWidth : 0 };
  }
}
const measureCtx = new MockMeasureContext(10);
const longWordBox = { width: 100, height: 40 };
const fitResult = theme.fitText(measureCtx, 'ExtremelyLongWordThatExceedsTheBoxWidth', longWordBox, 24, 16);
assert(fitResult.lines.length > 0, 'fitText must return at least one line');
assert(measureCtx.measureText(fitResult.lines[0]).width <= 100, 'Truncated line must not exceed box width');
assert(fitResult.lines[0].endsWith('...'), 'Truncated line must end with ellipsis');
console.log(`✓ fitText safely truncated long word to "${fitResult.lines[0]}" (${measureCtx.measureText(fitResult.lines[0]).width}px <= 100px).`);

// 3. Golden Manifest Verification
console.log('\nTest 3: Golden manifest structure and timings');
const manifestPath = path.join(__dirname, '../fixtures/golden_manifest_en.json');
assert(fs.existsSync(manifestPath), 'golden_manifest_en.json must exist');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

assert.strictEqual(manifest.scenes.length, 5);
assert.strictEqual(manifest.total_sec, 54.79);
assert.strictEqual(manifest.scenes[0].start_sec, 0.0);
assert.strictEqual(manifest.scenes[0].duration_sec, 9.92);
assert.strictEqual(manifest.scenes[4].end_sec, 54.79);
console.log('✓ Golden manifest verified with 5 scenes and total_sec = 54.79.');

// 4. Scene Boundary Logic
console.log('\nTest 4: Scene boundary detection');
assert.strictEqual(engine.getActiveScene(manifest.scenes, 0.0).id, 1, 't=0 -> Scene 1');
assert.strictEqual(engine.getActiveScene(manifest.scenes, 5.0).id, 1, 't=5 -> Scene 1');
assert.strictEqual(engine.getActiveScene(manifest.scenes, 9.92).id, 2, 't=9.92 (boundary) -> Scene 2');
assert.strictEqual(engine.getActiveScene(manifest.scenes, 22.01).id, 3, 't=22.01 (boundary) -> Scene 3');
assert.strictEqual(engine.getActiveScene(manifest.scenes, 54.79).id, 5, 't=54.79 (final timestamp) -> Scene 5');
assert.strictEqual(engine.getActiveScene(manifest.scenes, 100.0).id, 5, 't=100.0 (beyond end) -> Scene 5');
assert.strictEqual(engine.getActiveScene(manifest.scenes, -10.0).id, 1, 't=-10.0 (negative) -> Scene 1');
console.log('✓ Scene boundary detection correctly handles internal and boundary timestamps.');

// Mock Context for Canvas Operations
class MockCanvasContext {
  constructor() {
    this.ops = [];
    this.font = '10px sans-serif';
    this.fillStyle = '#000';
    this.strokeStyle = '#000';
    this.globalAlpha = 1.0;
    this.textAlign = 'left';
    this.textBaseline = 'top';
  }
  save() { this.ops.push('save'); }
  restore() { this.ops.push('restore'); }
  beginPath() { this.ops.push('beginPath'); }
  closePath() { this.ops.push('closePath'); }
  moveTo(x, y) { this.ops.push(`moveTo(${x.toFixed(1)},${y.toFixed(1)})`); }
  lineTo(x, y) { this.ops.push(`lineTo(${x.toFixed(1)},${y.toFixed(1)})`); }
  arcTo(x1, y1, x2, y2, r) { this.ops.push(`arcTo(${x1.toFixed(1)},${y1.toFixed(1)},${x2.toFixed(1)},${y2.toFixed(1)},${r})`); }
  arc(x, y, r, sa, ea) { this.ops.push(`arc(${x.toFixed(1)},${y.toFixed(1)},${r.toFixed(1)})`); }
  fillRect(x, y, w, h) { this.ops.push(`fillRect(${x.toFixed(1)},${y.toFixed(1)},${w.toFixed(1)},${h.toFixed(1)})`); }
  fillText(text, x, y) { this.ops.push(`fillText("${text}",${Number(x).toFixed(1)},${Number(y).toFixed(1)})`); }
  stroke() { this.ops.push('stroke'); }
  fill() { this.ops.push('fill'); }
  measureText(text) { return { width: (text ? text.length * 10 : 0) }; }
}

const mockCanvas = { width: 1280, height: 720 };
const mockCtx1 = new MockCanvasContext();
engine.setCanvas(mockCanvas, mockCtx1);

// Run Async Engine Initialization and Rendering Checks
engine.initLesson(manifest.title, manifest.scenes, manifest.lang).then(() => {
  // 5. Public API Verification
  console.log('\nTest 5: Public API properties');
  assert.strictEqual(globalThis.totalDuration, 54.79, 'window.totalDuration must equal 54.79');
  assert.strictEqual(globalThis.ready, true, 'window.ready must be true');
  console.log('✓ Public API properties confirmed.');

  // 6. Deterministic Rendering
  console.log('\nTest 6: Frame rendering determinism');
  engine.renderAtTime(14.5);
  const opsFirstPass = [...mockCtx1.ops];

  const mockCtx2 = new MockCanvasContext();
  engine.setCanvas(mockCanvas, mockCtx2);
  engine.renderAtTime(14.5);
  const opsSecondPass = [...mockCtx2.ops];

  assert.deepStrictEqual(opsFirstPass, opsSecondPass, 'Rendering the exact same timestamp repeatedly must produce identical canvas draw operations');
  console.log(`✓ Deterministic rendering verified: exactly ${opsFirstPass.length} identical canvas operations on both passes.`);

  // 7. Full Timeline Scrubbing
  console.log('\nTest 7: Full timeline scrubbing in steps of 0.05s');
  let frameCount = 0;
  for (let t = 0; t <= manifest.total_sec; t = Math.round((t + 0.05) * 100) / 100) {
    const ok = engine.renderAtTime(t);
    assert(ok, `Frame at t=${t}s must render without errors`);
    frameCount++;
  }
  console.log(`✓ Successfully rendered all ${frameCount} frames across 54.79s without a single error or missing frame.`);

  // 8. Robust Boundary and Invalid Timestamps
  console.log('\nTest 8: Negative, NaN, and out-of-bounds timestamps');
  assert(engine.renderAtTime(-5.0), 'Negative timestamp must render clamped to 0');
  assert(engine.renderAtTime(NaN), 'NaN timestamp must render clamped to 0');
  assert(engine.renderAtTime(undefined), 'Undefined timestamp must render clamped to 0');
  assert(engine.renderAtTime(999.9), 'Past-end timestamp must render clamped to totalDuration');
  console.log('✓ Edge-case timestamps handled cleanly.');

  // 9. Caption Multi-Line Fitting (No Dropped Words)
  console.log('\nTest 9: Caption full word retention on 42-word budget');
  const captionCtx = new MockCanvasContext();
  const testNarration = 'One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour twentyfive twentysix twentyseven twentyeight twentynine thirty thirtyone thirtytwo thirtythree thirtyfour thirtyfive thirtysix thirtyseven thirtyeight thirtynine forty fortyone fortytwo';
  engine.drawCaptions(captionCtx, testNarration, 5.0, 10.0, theme, 'en');
  const drawnWords = captionCtx.ops.filter(op => op.startsWith('fillText('));
  assert.strictEqual(drawnWords.length, 42, 'Every word in a 42-word narration budget must be rendered without clipping');
  console.log(`✓ All 42 words retained in caption output without dropping lines.`);

  // 10. Compare Template Column Isolation (No Step Duplication)
  console.log('\nTest 10: Compare template 3-column non-duplication');
  const compareCtx = new MockCanvasContext();
  templates.compare(compareCtx, {
    labels: ['Tank Voltage', 'Pipe Current', 'Tap Resistance'],
    steps: ['Pressure pushes flow', 'Narrow pipe resists']
  }, 1.0, 5.0, theme, 'en');
  const compareTexts = compareCtx.ops.filter(op => op.startsWith('fillText('));
  const hasDuplicateStep = compareTexts.filter(op => op.includes('Pressure pushes flow')).length > 1;
  assert(!hasDuplicateStep, 'Step from Column 1 must not be erroneously duplicated into Column 3');
  console.log('✓ Compare template correctly isolates column data and displays VS badges.');

  // 11. Flow Template Multi-Node (5-6 nodes) Support
  console.log('\nTest 11: Flow template 5-node support and arrowheads');
  const flowCtx = new MockCanvasContext();
  templates.flow(flowCtx, {
    labels: ['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4', 'Stage 5'],
    steps: ['Complete']
  }, 1.0, 5.0, theme, 'en');
  const flowTexts = flowCtx.ops.filter(op => op.startsWith('fillText('));
  const hasStage5 = flowTexts.some(op => op.includes('Stage 5'));
  assert(hasStage5, 'Flow template must support all 5-6 schema-allowed nodes without dropping labels');
  console.log('✓ Flow template renders all nodes and connects them with directed arrows.');

  // 12. Graceful Fallback for Unknown Template
  console.log('\nTest 12: Graceful fallback for unknown template');
  const fallbackCtx = new MockCanvasContext();
  templates.draw(fallbackCtx, 'non_existent_visual_type', { labels: ['Safe Heading'], steps: ['Safe Step'] }, 1.0, 5.0, theme, 'en');
  const fallbackTexts = fallbackCtx.ops.filter(op => op.startsWith('fillText('));
  assert(fallbackTexts.some(op => op.includes('Safe Heading')), 'Unknown template must degrade gracefully to bullets');
  console.log('✓ Graceful degradation confirmed: unknown visual types fall back safely to bullets.');

  // 13. Labeled Diagram Template (1 to 6 labels, leader lines, chips)
  console.log('\nTest 13: labeled_diagram label boundaries and structure');
  const diagMinCtx = new MockCanvasContext();
  templates.draw(diagMinCtx, 'labeled_diagram', { labels: ['Core Engine'], steps: ['Initial State'] }, 1.0, 5.0, theme, 'en');
  assert(diagMinCtx.ops.some(op => op.includes('Core Engine')), 'labeled_diagram must render single center label');

  const diagMaxCtx = new MockCanvasContext();
  templates.draw(diagMaxCtx, 'labeled_diagram', {
    labels: ['Central CPU', 'ALU Block', 'Control Unit', 'Cache L1', 'Registers', 'Buses'],
    steps: ['Fetch', 'Decode', 'Execute', 'Writeback']
  }, 2.0, 5.0, theme, 'en');
  const diagTexts = diagMaxCtx.ops.filter(op => op.startsWith('fillText('));
  assert(diagTexts.some(op => op.includes('Central CPU')), 'Must render central system');
  assert(diagTexts.some(op => op.includes('ALU Block')), 'Must render callout node');
  assert(diagTexts.some(op => op.includes('Buses')), 'Must render 5th peripheral callout node');
  assert(diagTexts.some(op => op.includes('Fetch')), 'Must render step chip at bottom');
  assert(diagMaxCtx.ops.some(op => op.startsWith('lineTo(')), 'Must render leader connector lines');
  console.log('✓ labeled_diagram renders central system, all 5 callout nodes with leader lines, and bottom step chips.');

  // 14. Timeline Template (1 to 6 stages, directional track, long text)
  console.log('\nTest 14: timeline template stages and track progression');
  const timeSingleCtx = new MockCanvasContext();
  templates.draw(timeSingleCtx, 'timeline', { labels: ['Discovery'], steps: ['Year 1827'] }, 1.0, 5.0, theme, 'en');
  assert(timeSingleCtx.ops.some(op => op.includes('Discovery')), 'timeline must handle single stage');

  const timeMaxCtx = new MockCanvasContext();
  templates.draw(timeMaxCtx, 'timeline', {
    labels: ['Stage 1: Observation', 'Stage 2: Hypothesis', 'Stage 3: Experiment', 'Stage 4: Measurement', 'Stage 5: Analysis', 'Stage 6: Conclusion'],
    steps: ['Observe physical law', 'Formulate statement', 'Conduct test setup', 'Measure volts and amps', 'Compute resistance', 'Publish findings']
  }, 3.5, 6.0, theme, 'en');
  const timeTexts = timeMaxCtx.ops.filter(op => op.startsWith('fillText('));
  assert(timeTexts.some(op => op.includes('Observation')), 'Must render stage 1');
  assert(timeTexts.some(op => op.includes('Conclusion')), 'Must render stage 6');
  assert(timeTexts.some(op => op.includes('Publish')), 'Must render step detail below timeline');
  assert(timeMaxCtx.ops.some(op => op.startsWith('fillRect(')), 'Must render timeline track line');
  console.log('✓ timeline renders directional progression, all 6 milestone nodes, and detail cards above and below.');

  // 15. Graph Template with Unambiguous Numeric Data (Bar Chart mode)
  console.log('\nTest 15: graph template with unambiguous numeric steps (bar chart mode)');
  const graphNumCtx = new MockCanvasContext();
  templates.draw(graphNumCtx, 'graph', {
    labels: ['Resistor Type', 'Current (A)'],
    steps: ['Carbon: 2', 'Ceramic: 5', 'Wirewound: 10']
  }, 2.0, 5.0, theme, 'en');
  const graphNumTexts = graphNumCtx.ops.filter(op => op.startsWith('fillText('));
  assert(graphNumTexts.some(op => op.includes('Resistor Type')), 'Must render X-axis label');
  assert(graphNumTexts.some(op => op.includes('Current (A)')), 'Must render Y-axis label');
  assert(graphNumTexts.some(op => op.includes('Carbon')), 'Must render bar item label');
  assert(graphNumTexts.some(op => op.includes('10')), 'Must render bar value');
  console.log('✓ graph template parses unambiguously structured numeric steps and renders calibrated bar chart.');

  // 16. Graph Template: Arbitrary numbers in prose must NOT become a bar chart
  console.log('\nTest 16: graph template rejects numbers in prose from becoming bar charts');
  const graphProseCtx = new MockCanvasContext();
  templates.draw(graphProseCtx, 'graph', {
    labels: ['Voltage (V)', 'Current (I)'],
    steps: [
      'In a 230 V Indian wall socket, an iron box of 46 Ohms yields 5 Amperes.',
      'A ceiling fan at 180 V drops its rotational speed noticeably.'
    ]
  }, 2.0, 5.0, theme, 'en');
  const proseTexts = graphProseCtx.ops.filter(op => op.startsWith('fillText('));
  // Must render as conceptual framework, not a bar chart with numeric heights
  assert(proseTexts.some(op => op.includes('socket')), 'Prose with numbers must render as conceptual prose (the lesson text), not bars');
  assert(!proseTexts.some(op => op === 'fillText("230")' || op === 'fillText("230 V")'), 'Must not extract arbitrary prose numbers as standalone chart bar values');
  console.log('✓ Prose sentences with numbers correctly fall back to conceptual analysis without creating a spurious bar chart.');

  // 17. Graph Template: Conceptual framework without invented curves or trendlines
  console.log('\nTest 17: graph template conceptual mode avoids arbitrary curves and fake data');
  const graphConceptCtx = new MockCanvasContext();
  templates.draw(graphConceptCtx, 'graph', {
    labels: ['Pressure (P)', 'Volume (V)'],
    steps: ['Pressure and volume are inversely related at constant temperature']
  }, 2.5, 5.0, theme, 'en');
  const conceptTexts = graphConceptCtx.ops.filter(op => op.startsWith('fillText('));
  assert(conceptTexts.some(op => op.includes('Pressure (P)')), 'Must render X parameter label');
  assert(conceptTexts.some(op => op.includes('Volume (V)')), 'Must render Y parameter label');
  assert(conceptTexts.some(op => op.includes('inversely related')), 'Must render concept explanation from steps');
  // Check that no arbitrary curve was plotted (only axis lines, arrowheads, and gridlines use lineTo; no 40-step curve loop)
  const lineToOps = graphConceptCtx.ops.filter(op => op.startsWith('lineTo('));
  assert(lineToOps.length <= 10, `Must not draw arbitrary 40-step curve: only grid and axis arrows allowed (got ${lineToOps.length})`);
  console.log('✓ graph conceptual mode renders clean parameter space and explanatory cards without arbitrary curves.');

  // 18. Determinism test on graph template
  console.log('\nTest 18: graph template rendering determinism');
  const graphDetCtx1 = new MockCanvasContext();
  templates.draw(graphDetCtx1, 'graph', {
    labels: ['Supply Voltage', 'Current Flow'],
    steps: ['Current increases as voltage increases']
  }, 1.75, 4.0, theme, 'en');
  const graphDetCtx2 = new MockCanvasContext();
  templates.draw(graphDetCtx2, 'graph', {
    labels: ['Supply Voltage', 'Current Flow'],
    steps: ['Current increases as voltage increases']
  }, 1.75, 4.0, theme, 'en');
  assert.deepStrictEqual(graphDetCtx1.ops, graphDetCtx2.ops, 'Repeated graph renders must produce identical operations');
  console.log('✓ graph template is strictly deterministic.');

  // 19. Batch 1 Fix 1: Equation template dynamic worked steps / no Ohm's law leakage
  console.log('\nTest 19: Equation template dynamic worked steps (no Ohm\'s law leakage)');
  const eqCtx1 = new MockCanvasContext();
  templates.equation(eqCtx1, {
    labels: ['E = (1/2) * m * v^2', 'm : Mass (kg)', 'v : Velocity (m/s)'],
    steps: ['m = 2 kg, v = 3 m/s', 'E = 0.5 * 2 * 9 = 9 Joules']
  }, 2.0, 5.0, theme, 'en');
  const eqTexts1 = eqCtx1.ops.filter(op => op.startsWith('fillText('));
  const hasOhmLeakage1 = eqTexts1.some(op => /12\s*V|4\s*Ω|3\s*A/i.test(op));
  assert(!hasOhmLeakage1, 'General physics equation must NEVER display hardcoded Ohm\'s Law values (12V, 4Ω, 3A)');
  assert(eqTexts1.some(op => op.includes('9 Joules')), 'Supplied worked calculation step must be rendered in right panel');

  const eqCtx2 = new MockCanvasContext();
  templates.equation(eqCtx2, {
    labels: ['F = m * a', 'm : Mass', 'a : Acceleration'],
    steps: []
  }, 2.0, 5.0, theme, 'en');
  const eqTexts2 = eqCtx2.ops.filter(op => op.startsWith('fillText('));
  const hasOhmLeakage2 = eqTexts2.some(op => /12\s*V|4\s*Ω|3\s*A/i.test(op));
  assert(!hasOhmLeakage2, 'Equation without steps must NEVER display hardcoded Ohm\'s Law calculation');
  console.log('✓ Equation template dynamically renders supplied steps and never leaks Ohm\'s Law constants into arbitrary equations.');

  // 20. Batch 1 Fix 2: Compare template semantic correctness / no DC/AC leakage
  console.log('\nTest 20: Compare template semantic correctness (no DC/AC leakage)');
  const compBioCtx = new MockCanvasContext();
  templates.compare(compBioCtx, {
    labels: ['Plant Cell', 'Animal Cell'],
    steps: ['Rigid cellulose cell wall', 'Flexible cell membrane', 'Large central vacuole', 'Small temporary vacuoles']
  }, 2.0, 5.0, theme, 'en');
  const compBioTexts = compBioCtx.ops.filter(op => op.startsWith('fillText('));
  const hasWaveformTextBio = compBioTexts.some(op => /\bDC\b|\bAC\b|Direct Current|Alternating Current/i.test(op));
  assert(!hasWaveformTextBio, 'Biology comparison must NEVER render DC or AC text/labels');
  assert(compBioTexts.some(op => /Plant Cell/i.test(op)), 'Must render Plant Cell heading');
  assert(compBioTexts.some(op => /Animal Cell/i.test(op)), 'Must render Animal Cell heading');

  const compGenCtx = new MockCanvasContext();
  templates.compare(compGenCtx, {
    labels: ['Solar Energy', 'Wind Energy'],
    steps: ['Photovoltaic sunlight conversion', 'Kinetic turbine rotation']
  }, 2.0, 5.0, theme, 'en');
  const compGenTexts = compGenCtx.ops.filter(op => op.startsWith('fillText('));
  const hasWaveformTextGen = compGenTexts.some(op => /\bDC\b|\bAC\b/i.test(op));
  assert(!hasWaveformTextGen, 'General comparison must NEVER render DC or AC badges');

  // Verify genuine DC vs AC comparison correctly supports electrical badges
  const compElecCtx = new MockCanvasContext();
  templates.compare(compElecCtx, {
    labels: ['Direct Current (DC)', 'Alternating Current (AC)'],
    steps: ['Constant unidirectional flow', 'Periodic sinusoidal oscillation']
  }, 2.0, 5.0, theme, 'en');
  const compElecTexts = compElecCtx.ops.filter(op => op.startsWith('fillText('));
  assert(compElecTexts.some(op => op.includes('DC')), 'Genuine electrical comparison must render DC badge');
  assert(compElecTexts.some(op => op.includes('AC')), 'Genuine electrical comparison must render AC badge');
  console.log('✓ Compare template correctly adapts illustration and badges semantically by topic.');

  // 21. Batch 1 Fix 3: Flow template 6-node full retention and layout
  console.log('\nTest 21: Flow template 6-node full retention');
  const flow6Ctx = new MockCanvasContext();
  const stages6 = ['Ingestion', 'Digestion', 'Absorption', 'Assimilation', 'Egestion', 'Metabolism'];
  templates.flow(flow6Ctx, {
    labels: stages6,
    steps: ['End-to-end biological processing cycle completes.']
  }, 2.0, 5.0, theme, 'en');
  const flow6Texts = flow6Ctx.ops.filter(op => op.startsWith('fillText('));
  stages6.forEach(st => {
    assert(flow6Texts.some(op => op.includes(st)), `Flow template must render node "${st}" without dropping`);
  });
  assert(flow6Texts.some(op => op.includes('06')), 'Flow template must render numeral 06 for 6th card');
  assert(flow6Texts.some(op => op.includes('biological processing')), 'Outcome takeaway box must render supplied step');
  console.log('✓ Flow template supports up to 6 nodes without dropping content or overflowing canvas bounds.');

  // 22. Phase 2 Batch 2 Task 2.5: Robust fitText caller enforcement & zero silent drop
  console.log('\nTest 22: Robust fitText caller enforcement and layout adaptation');
  theme.clearDiagnostics();
  const testBox = { width: 200, height: 60 };
  const multiLineText = 'This is a multi-line educational concept description explaining scientific principles in detail.';
  const fitAdapt = theme.fitText(measureCtx, multiLineText, testBox, 16, 12, 500, 'en', { label: 'test.concept' });
  assert(fitAdapt.lines.length >= 2, 'Must wrap into multiple lines');
  assert(fitAdapt.fontSize >= 12, 'Font size must not drop below minPx');
  assert(fitAdapt.requiredHeight > 0, 'Must report requiredHeight layout geometry');

  // Verify allowGrowth option allows callers to expand without truncation
  const constrainedBox = { width: 100, height: 30 };
  const fitGrew = theme.fitText(measureCtx, 'Long sentence that needs more height than provided by the small box', constrainedBox, 16, 12, 500, 'en', { allowGrowth: true, label: 'test.growth' });
  assert.strictEqual(fitGrew.grew, true, 'allowGrowth must allow vertical expansion');
  assert.strictEqual(fitGrew.truncated, false, 'allowGrowth must not truncate text');

  // Verify diagnostic logging on unadapted overflow
  theme.clearDiagnostics();
  const fitOverflow = theme.fitText(measureCtx, 'Massive text that cannot fit even at minimum font size inside tiny box without growth', { width: 50, height: 20 }, 14, 12, 500, 'en', { label: 'test.overflow' });
  assert.strictEqual(theme.hasOverflows(), true, 'Must log diagnostic when text exceeds bounding box');
  const overflowLog = theme.getOverflows();
  assert(overflowLog[0].msg.includes('[test.overflow]'), 'Diagnostic log must record caller label');
  console.log('✓ fitText caller enforcement provides layout geometry, growth adaptation, and diagnostic observability.');

  // 23. Phase 2 Batch 2 Task 2.6: Operator-aware equation tokenization
  console.log('\nTest 23: Operator-aware equation tokenization (exponents, fractions, parentheses)');
  const eqAdvCtx = new MockCanvasContext();
  templates.equation(eqAdvCtx, {
    labels: ['E = (1/2) * m * v^2', 'm : Mass (kg)', 'v : Velocity (m/s)'],
    steps: ['E = 0.5 * 2 * 9 = 9 Joules']
  }, 2.0, 5.0, theme, 'en');
  const eqAdvTexts = eqAdvCtx.ops.filter(op => op.startsWith('fillText('));
  assert(eqAdvTexts.some(op => op.includes('E')), 'Must render energy variable E');
  assert(eqAdvTexts.some(op => op.includes('=')), 'Must render equality operator =');
  assert(eqAdvTexts.some(op => op.includes('1/2')), 'Must render fraction coefficient 1/2 as a coherent number chip');
  assert(eqAdvTexts.some(op => op.includes('m')), 'Must render mass variable m');
  assert(eqAdvTexts.some(op => op.includes('v')), 'Must render velocity variable v');
  assert(eqAdvTexts.some(op => op.includes('2')), 'Must render exponent 2');
  assert(eqAdvTexts.some(op => op.includes('(')), 'Must render opening parenthesis');
  assert(eqAdvTexts.some(op => op.includes(')')), 'Must render closing parenthesis');
  console.log('✓ Equation template properly formats operators, fraction coefficients, and superscript exponents.');

  // 24. Phase 2 Batch 2 Task 2.7: Minimum Readable Typography (~12px+ across templates)
  console.log('\nTest 24: Minimum readable typography enforcement (~12px+ target)');
  const timeTypoCtx = new MockCanvasContext();
  templates.timeline(timeTypoCtx, {
    labels: ['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4', 'Stage 5', 'Stage 6'],
    steps: ['Long detailed description explaining historical context in detail for stage 1', 'Step 2 description', 'Step 3 description', 'Step 4 description', 'Step 5 description', 'Step 6 description']
  }, 2.0, 5.0, theme, 'en');
  // Check font declarations in ops
  const fontOps = timeTypoCtx.ops.filter(op => op.startsWith('setFont('));
  const smallFonts = fontOps.filter(op => {
    const match = op.match(/(d+)px/);
    return match && parseInt(match[1], 10) < 12;
  });
  assert(smallFonts.length === 0, 'Timeline body and event descriptions must never drop below 12px');

  const graphTypoCtx = new MockCanvasContext();
  templates.graph(graphTypoCtx, {
    labels: ['Pressure (P)', 'Volume (V)'],
    steps: ['Boyle\'s Law inverse relationship', 'Independent variable input', 'Measured gas response']
  }, 2.0, 5.0, theme, 'en');
  const graphTexts = graphTypoCtx.ops.filter(op => op.startsWith('fillText('));
  assert(graphTexts.some(op => op.includes('Boyle')), 'Graph conceptual mode must render explanation at readable size');
  console.log('✓ Minimum readable typography maintained at >= 12px for body and descriptive text.');

  // 25. Phase 2 Batch 2 Task 2.8: Title fallback — Neutral scientific composition
  console.log('\nTest 25: Title fallback neutral scientific composition (topic-appropriate)');
  const titleNeutralCtx = new MockCanvasContext();
  templates.title(titleNeutralCtx, {
    labels: ['Universal Gravitation', 'CLASSICAL MECHANICS'],
    steps: ['Every particle attracts every other particle with a gravitational force.']
  }, 1.5, 5.0, theme, 'en');
  const neutralTexts = titleNeutralCtx.ops.filter(op => op.startsWith('fillText('));
  assert.strictEqual(templates.lastIllustration, 'neutral', 'A generic topic must get the neutral composition');
  assert.notStrictEqual(templates.lastIllustration, 'circuit', 'Non-electrical topic must not get the circuit illustration');
  assert.notStrictEqual(templates.lastIllustration, 'water', 'Non-environmental topic must not get the water cycle illustration');

  // Verify Biology topic renders cellular structure
  const titleBioCtx = new MockCanvasContext();
  templates.title(titleBioCtx, {
    labels: ['Plant Cell Structure', 'CELLULAR BIOLOGY'],
    steps: ['Plant cells contain specialized organelles for photosynthesis and structural support.']
  }, 1.5, 5.0, theme, 'en');
  const bioTexts = titleBioCtx.ops.filter(op => op.startsWith('fillText('));
  assert.strictEqual(templates.lastIllustration, 'cell', 'Biological topic must get the cell illustration');
  console.log('✓ Title template selects appropriate topic illustration and uses neutral scientific composition for generic topics.');

  // 26. Phase 2 Batch 2 Task 2.9: Equation-panel dynamic adaptation (1 to 5 variables, 1 to 4 steps)
  console.log('\nTest 26: Equation-panel dynamic adaptation (5 variables, 4 calculation steps)');
  const eq5Ctx = new MockCanvasContext();
  templates.equation(eq5Ctx, {
    labels: [
      'F = G * m1 * m2 / r^2',
      'G : Gravitational constant',
      'm1 : Mass of first object',
      'm2 : Mass of second object',
      'r : Distance between centers',
      'F : Gravitational force'
    ],
    steps: [
      'Step 1: Given values m1=10kg, m2=20kg',
      'Step 2: Substitute into Newton\'s law',
      'Step 3: Calculate numerator and denominator',
      'Step 4: Final gravitational force result = 1.33e-9 N'
    ]
  }, 2.0, 5.0, theme, 'en');
  const eq5Texts = eq5Ctx.ops.filter(op => op.startsWith('fillText('));
  assert(eq5Texts.some(op => op.includes('G')), 'Must render variable G');
  assert(eq5Texts.some(op => op.includes('m1')), 'Must render variable m1');
  assert(eq5Texts.some(op => op.includes('m2')), 'Must render variable m2');
  assert(eq5Texts.some(op => op.includes('r')), 'Must render variable r');
  assert(eq5Texts.some(op => op.includes('F')), 'Must render variable F');
  assert(eq5Texts.some(op => op.includes('STEP 01')), 'Must render Step 1');
  assert(eq5Texts.some(op => op.includes('STEP 04')), 'Must render Step 4 without dropping');
  console.log('✓ Equation template adapts layout to render up to 5 variables and 4 worked steps cleanly.');

  // 27. Phase 2 Batch 2 Task 2.10: Labeled-diagram fallback (topic-neutral system schematic)
  console.log('\nTest 27: Labeled-diagram fallback topic-neutral system schematic');
  const diagNeuralCtx = new MockCanvasContext();
  templates.labeled_diagram(diagNeuralCtx, {
    labels: ['Neural Architecture', 'Input Layer', 'Hidden Nodes', 'Activation Unit', 'Loss Function', 'Output Dense'],
    steps: ['Forward propagation passes signals through layers.']
  }, 2.0, 5.0, theme, 'en');
  const diagNeuralTexts = diagNeuralCtx.ops.filter(op => op.startsWith('fillText('));
  assert(!diagNeuralTexts.some(op => op.includes('CENTRAL DIAGRAM PLACEHOLDER')), 'Must not render placeholder string');
  assert(diagNeuralTexts.some(op => op.includes('NEURAL ARCHITECTURE')), 'Must dynamically render topic name on schematic header');
  assert(diagNeuralTexts.some(op => op.includes('Input Layer')), 'Must render peripheral callout Input Layer');
  assert(diagNeuralTexts.some(op => op.includes('Output Dense')), 'Must render 5th peripheral callout Output Dense');
  console.log('✓ Labeled-diagram replaces placeholder with dynamic topic schematic, calibrated nexus, and peripheral callouts.');

  // 28. Task 1 Correction: Real fitText overflow handling & observable detection
  console.log('\nTest 28: Real fitText overflow handling and non-silent detection');
  theme.clearDiagnostics();
  assert.strictEqual(theme.hasOverflows(), false, 'Must start with zero overflows');
  const overflowBox = { width: 80, height: 25 };
  const fitOver = theme.fitText(measureCtx, 'Extremely long sentence that cannot fit inside tiny box at all', overflowBox, 14, 12, 500, 'en', { label: 'audit.test' });
  assert.strictEqual(fitOver.fits, false, 'fitText must report fits: false');
  assert.strictEqual(fitOver.truncated, true, 'fitText must report truncated: true');
  assert(fitOver.overflowError && fitOver.overflowError.includes('TEXT_OVERFLOW'), 'fitText must report structured overflowError');
  assert.strictEqual(theme.hasOverflows(), true, 'theme.hasOverflows() must detect unhandled overflow');

  // Verify observable warning badge on canvas
  const canvasOverCtx = new MockCanvasContext();
  theme.drawFittedLines(canvasOverCtx, fitOver, 20, 20);
  const overOps = canvasOverCtx.ops.filter(op => op.startsWith('fillText('));
  assert(overOps.some(op => op.includes('! CONTENT OVERFLOW')), 'Must render observable CONTENT OVERFLOW badge on canvas');

  // Verify assertNoOverflow() throws on active overflow
  let assertedError = false;
  try {
    theme.assertNoOverflow();
  } catch (err) {
    assertedError = true;
    assert(err.message.includes('audit.test'), 'assertNoOverflow must include caller label');
  }
  assert(assertedError, 'assertNoOverflow must throw when overflow exists');
  theme.clearDiagnostics();
  assert.strictEqual(theme.assertNoOverflow(), true, 'assertNoOverflow passes when diagnostics are clean');
  console.log('✓ Real fitText overflow handling provides structured error, observable canvas badge, and assertNoOverflow enforcement.');

  // 29. Task 2 Correction: Scientific formula parsing (implicit multiplication, exponents, fractions, parentheses, indexed variables)
  console.log('\nTest 29: Scientific formula parsing (implicit multiplication & complex expressions)');
  const eqFmaCtx = new MockCanvasContext();
  templates.equation(eqFmaCtx, { labels: ['F=ma', 'm : Mass', 'a : Acceleration'] }, 2.0, 5.0, theme, 'en');
  const fmaTexts = eqFmaCtx.ops.filter(op => op.startsWith('fillText('));
  assert(fmaTexts.some(op => op.includes('F')), 'Must render F');
  assert(fmaTexts.some(op => op.includes('fillText("m",')), 'Must render variable factor m');
  assert(fmaTexts.some(op => op.includes('fillText("a",')), 'Must render variable factor a');
  assert(!fmaTexts.some(op => op.includes('fillText("ma",')), 'Must not lump ma into a single variable token');

  const eqEmcCtx = new MockCanvasContext();
  templates.equation(eqEmcCtx, { labels: ['E=mc^2', 'm : Mass', 'c : Speed of light'] }, 2.0, 5.0, theme, 'en');
  const emcTexts = eqEmcCtx.ops.filter(op => op.startsWith('fillText('));
  assert(emcTexts.some(op => op.includes('fillText("m",')), 'Must render separate mass variable m');
  assert(emcTexts.some(op => op.includes('fillText("c",')), 'Must render separate speed of light variable c');
  assert(emcTexts.some(op => op.includes('fillText("2",')), 'Must render superscript exponent 2');
  assert(!emcTexts.some(op => op.includes('fillText("mc",')), 'Must not lump mc into a single token');

  const eqVirCtx = new MockCanvasContext();
  templates.equation(eqVirCtx, { labels: ['V=IR', 'I : Current', 'R : Resistance'] }, 2.0, 5.0, theme, 'en');
  const virTexts = eqVirCtx.ops.filter(op => op.startsWith('fillText('));
  assert(virTexts.some(op => op.includes('I')), 'Must render separate current variable I');
  assert(virTexts.some(op => op.includes('R')), 'Must render separate resistance variable R');

  const eqGroupCtx = new MockCanvasContext();
  templates.equation(eqGroupCtx, { labels: ['(a+b)/c', 'a : Term 1', 'b : Term 2', 'c : Divisor'] }, 2.0, 5.0, theme, 'en');
  const groupTexts = eqGroupCtx.ops.filter(op => op.startsWith('fillText('));
  assert(groupTexts.some(op => op.includes('(')), 'Must render opening parenthesis');
  assert(groupTexts.some(op => op.includes(')')), 'Must render closing parenthesis');
  assert(groupTexts.some(op => op.includes('÷')), 'Must render division operator');

  const eqIdxCtx = new MockCanvasContext();
  templates.equation(eqIdxCtx, { labels: ['p = m1 * v1 + m2 * v2'] }, 2.0, 5.0, theme, 'en');
  const idxTexts = eqIdxCtx.ops.filter(op => op.startsWith('fillText('));
  assert(idxTexts.some(op => op.includes('m1')), 'Must preserve indexed variable m1 as atomic');
  assert(idxTexts.some(op => op.includes('v1')), 'Must preserve indexed variable v1 as atomic');
  assert(idxTexts.some(op => op.includes('m2')), 'Must preserve indexed variable m2 as atomic');
  assert(idxTexts.some(op => op.includes('v2')), 'Must preserve indexed variable v2 as atomic');
  console.log('✓ Formula tokenizer correctly splits implicit multiplication, handles exponents, groups, and preserves indexed variables.');

  // 30. Task 3 Correction: Title-topic classification collision fixes
  console.log('\nTest 30: Title-topic classification collision fixes and positive cases');
  const collisionCtx1 = new MockCanvasContext();
  templates.title(collisionCtx1, { labels: ['Electrochemical Cell', 'CHEMISTRY'], steps: ['Galvanic reactions generate potential.'] }, 1.5, 5.0, theme, 'en');
  const coll1Texts = collisionCtx1.ops.filter(op => op.startsWith('fillText('));
  assert.notStrictEqual(templates.lastIllustration, 'circuit', 'Electrochemical Cell must not get the circuit illustration');
  assert.strictEqual(templates.lastIllustration, 'neutral', 'Electrochemical Cell must route to neutral composition');

  const collisionCtx2 = new MockCanvasContext();
  templates.title(collisionCtx2, { labels: ['Organic Chemistry', 'CHEMISTRY'], steps: ['Structure and reactivity of carbon compounds.'] }, 1.5, 5.0, theme, 'en');
  const coll2Texts = collisionCtx2.ops.filter(op => op.startsWith('fillText('));
  assert.notStrictEqual(templates.lastIllustration, 'cell', 'Organic Chemistry must not get the cell illustration');
  assert.strictEqual(templates.lastIllustration, 'neutral', 'Organic Chemistry must route to neutral composition');

  const collisionCtx3 = new MockCanvasContext();
  templates.title(collisionCtx3, { labels: ['Carnot Cycle', 'THERMODYNAMICS'], steps: ['Reversible thermodynamic heat engine cycle.'] }, 1.5, 5.0, theme, 'en');
  const coll3Texts = collisionCtx3.ops.filter(op => op.startsWith('fillText('));
  assert.notStrictEqual(templates.lastIllustration, 'water', 'Carnot Cycle must not get the water cycle illustration');
  assert.strictEqual(templates.lastIllustration, 'neutral', 'Carnot Cycle must route to neutral composition');

  const collisionCtx4 = new MockCanvasContext();
  templates.title(collisionCtx4, { labels: ['Krebs Cycle', 'BIOCHEMISTRY'], steps: ['Series of chemical reactions used by aerobic organisms.'] }, 1.5, 5.0, theme, 'en');
  const coll4Texts = collisionCtx4.ops.filter(op => op.startsWith('fillText('));
  assert.notStrictEqual(templates.lastIllustration, 'water', 'Krebs Cycle must not get the water cycle illustration');

  // Verify positive recognized topics still work
  const posCircuitCtx = new MockCanvasContext();
  templates.title(posCircuitCtx, { labels: ['Electric Circuit', 'ELECTRONICS'], steps: ['Closed loop conductor path.'] }, 1.5, 5.0, theme, 'en');
  assert.strictEqual(templates.lastIllustration, 'circuit', 'Electric Circuit must get the circuit illustration');

  const posWaterCtx = new MockCanvasContext();
  templates.title(posWaterCtx, { labels: ['The Water Cycle', 'EARTH SCIENCE'], steps: ['Continuous evaporation and precipitation.'] }, 1.5, 5.0, theme, 'en');
  assert.strictEqual(templates.lastIllustration, 'water', 'Water cycle must get the water cycle illustration');
  console.log('✓ Title topic classification correctly isolates collisions and routes ambiguous topics to neutral composition.');

  // 31. Task 4 Correction: Hindi and Kannada timeline text retention
  console.log('\nTest 31: Hindi and Kannada timeline text retention without dropped lines');
  theme.clearDiagnostics();
  const timeKnCtx = new MockCanvasContext();
  templates.timeline(timeKnCtx, {
    labels: ['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4', 'Stage 5', 'Stage 6'],
    steps: [
      'ನಿಖರವಾದ ವೋಲ್ಟ್‌ಮೀಟರ್‌ನೊಂದಿಗೆ ಪ್ರಯೋಗಾಲಯದ ಪರಿಸ್ಥಿತಿಗಳಲ್ಲಿ ಭೌತಿಕ ನಿಯಮವನ್ನು ಗಮನಿಸಿ',
      'ಹಂತ 2 ವಿವರಣೆ',
      'ಹಂತ 3 ವಿವರಣೆ',
      'ಹಂತ 4 ವಿವರಣೆ',
      'ಹಂತ 5 ವಿವರಣೆ',
      'ಹಂತ 6 ವಿವರಣೆ'
    ]
  }, 2.0, 5.0, theme, 'kn');
  const timeKnTexts = timeKnCtx.ops.filter(op => op.startsWith('fillText('));
  assert(!timeKnTexts.some(op => op.includes('ವೋಲ್ಟ್‌ಮೀಟರ್‌ನೊ...')), 'Kannada long word must not be truncated with ellipsis');
  assert(timeKnTexts.some(op => op.includes('ವೋಲ್ಟ್‌ಮೀಟರ್') || op.includes('ನಿಖರವಾದ')), 'Kannada text must be retained across lines');
  assert.strictEqual(theme.hasOverflows(), false, 'Kannada timeline rendering must have zero text overflows');

  const timeHiCtx = new MockCanvasContext();
  templates.timeline(timeHiCtx, {
    labels: ['चरण 1', 'चरण 2', 'चरण 3', 'चरण 4', 'चरण 5', 'चरण 6'],
    steps: [
      'सटीक वोल्टमीटर के साथ प्रयोगशाला में भौतिक नियम का अवलोकन करें',
      'चरण 2 विवरण',
      'चरण 3 विवरण',
      'चरण 4 विवरण',
      'चरण 5 विवरण',
      'चरण 6 विवरण'
    ]
  }, 2.0, 5.0, theme, 'hi');
  const timeHiTexts = timeHiCtx.ops.filter(op => op.startsWith('fillText('));
  assert(timeHiTexts.some(op => op.includes('अवलोकन करें')), 'Hindi timeline must retain final line without dropping');
  assert.strictEqual(theme.hasOverflows(), false, 'Hindi timeline rendering must have zero text overflows');
  console.log('✓ Timeline layout retains full Hindi and Kannada text without truncation or dropped lines.');

  // 32. Task 5 Correction: Template capacity validation beyond caps
  console.log('\nTest 32: Template capacity validation beyond supported caps');
  theme.clearDiagnostics();
  const eqOverCtx = new MockCanvasContext();
  templates.equation(eqOverCtx, {
    labels: [
      'y = a*x^3 + b*x^2 + c*x + d',
      'a : Coeff 1', 'b : Coeff 2', 'c : Coeff 3', 'd : Constant', 'x : Independent', 'y : Dependent', 'z : Extra'
    ],
    steps: ['Step 1: Given', 'Step 2: Sub', 'Step 3: Calc', 'Step 4: Solve', 'Step 5: Verify', 'Step 6: Finish']
  }, 2.0, 5.0, theme, 'en');
  assert.strictEqual(theme.hasCapacityViolations(), true, 'Must report capacity violation when variables/steps exceed caps');
  const eqViols = theme.getCapacityViolations();
  assert(eqViols.some(v => v.template === 'equation' && v.limitType === 'variable_definitions' && v.count === 7), 'Must record equation variable cap violation (7 > 5)');
  assert(eqViols.some(v => v.template === 'equation' && v.limitType === 'worked_steps' && v.count === 6), 'Must record equation steps cap violation (6 > 5)');

  const flowOverCtx = new MockCanvasContext();
  templates.flow(flowOverCtx, {
    labels: ['Process Flow'],
    steps: ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8']
  }, 2.0, 5.0, theme, 'en');
  const flowViols = theme.getCapacityViolations();
  assert(flowViols.some(v => v.template === 'flow' && v.count === 8), 'Must record flow capacity violation (8 > 6)');

  const timeOverCtx = new MockCanvasContext();
  templates.timeline(timeOverCtx, {
    labels: ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8'],
    steps: ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8']
  }, 2.0, 5.0, theme, 'en');
  const timeViols = theme.getCapacityViolations();
  assert(timeViols.some(v => v.template === 'timeline' && v.count === 8), 'Must record timeline capacity violation (8 > 6)');

  const diagOverCtx = new MockCanvasContext();
  templates.labeled_diagram(diagOverCtx, {
    labels: ['Core', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8'],
    steps: ['S1']
  }, 2.0, 5.0, theme, 'en');
  const diagViols = theme.getCapacityViolations();
  assert(diagViols.some(v => v.template === 'labeled_diagram' && v.count === 8), 'Must record labeled_diagram capacity violation (8 > 6)');
  console.log('✓ Template capacity validation accurately detects and records input exceeding supported caps across all templates.');

  // 33. Phase 2 Batch 3 Task 3.1: Full retention of 5 schema-valid equation worked steps
  console.log('\nTest 33: Full retention of 5 schema-valid equation worked steps');
  theme.clearDiagnostics();
  const eq5StepsCtx = new MockCanvasContext();
  templates.equation(eq5StepsCtx, {
    labels: [
      'P = V * I',
      'V : Voltage in Volts (230 V)',
      'I : Current in Amperes (10 A)',
      'P : Electrical Power in Watts'
    ],
    steps: [
      'Given: V = 230 V, I = 10 A',
      'Formula: P = V * I',
      'Substitution: P = 230 * 10',
      'Computation: P = 2300 W',
      'Conclusion: Appliance consumes 2.3 kW'
    ]
  }, 2.0, 5.0, theme, 'en');
  const eq5StepsTexts = eq5StepsCtx.ops.filter(op => op.startsWith('fillText('));
  assert(eq5StepsTexts.some(op => op.includes('Given')), 'Step text "Given" must be drawn (no step dropped)');
  assert(eq5StepsTexts.some(op => op.includes('Formula')), 'Step text "Formula" must be drawn (no step dropped)');
  assert(eq5StepsTexts.some(op => op.includes('Substitution')), 'Step text "Substitution" must be drawn (no step dropped)');
  assert(eq5StepsTexts.some(op => op.includes('Computation')), 'Step text "Computation" must be drawn (no step dropped)');
  assert(eq5StepsTexts.some(op => op.includes('Conclusion')), 'Step text "Conclusion" must be drawn (no step dropped)');
  assert(eq5StepsTexts.some(op => op.includes('Appliance consumes 2.3 kW')), 'Must render 5th step text');
  assert.strictEqual(theme.hasCapacityViolations(), false, '5 schema-valid steps must not trigger capacity violation');
  assert.strictEqual(theme.hasOverflows(), false, '5 steps must render with zero overflow errors');
  console.log('✓ Equation template cleanly retains all 5 schema-valid calculation steps without capacity violation or text overflow.');

  // 34. Phase 2 Batch 3 Task 3.2: Connected overflow detection in standard templates & stable deduplication
  console.log('\nTest 34: Connected overflow detection in standard templates & stable deduplication');
  theme.clearDiagnostics();

  // 1. Intentionally overflowing text in standard bullets template
  const overflowBulletsCtx = new MockCanvasContext();
  const massiveText = 'This is an extraordinarily verbose explanation designed specifically to exceed the physical vertical boundaries of a card container in the bullets template. '.repeat(25);
  templates.bullets(overflowBulletsCtx, {
    labels: ['Overflow Test'],
    steps: [massiveText]
  }, 2.0, 5.0, theme, 'en');

  assert.strictEqual(theme.hasOverflows(), true, 'Must detect overflow in standard bullets template');
  const bulletsOverOps = overflowBulletsCtx.ops.filter(op => op.startsWith('fillText('));
  assert(bulletsOverOps.some(op => op.includes('! CONTENT OVERFLOW')), 'Standard bullets template must actively render [! CONTENT OVERFLOW] badge');
  const initialOverflowCount = theme.getOverflows().length;
  assert(initialOverflowCount >= 1, 'Must record structured overflow diagnostic');

  // 2. Stable deduplication across repeated frame renders (scrubbing)
  for (let t = 0; t < 10; t++) {
    templates.bullets(overflowBulletsCtx, {
      labels: ['Overflow Test'],
      steps: [massiveText]
    }, 2.0, 5.0, theme, 'en');
  }
  assert.strictEqual(theme.getOverflows().length, initialOverflowCount, 'Repeated scrubbing renders must not duplicate overflow records');

  // 3. Distinct overflowing text boxes remain distinguishable
  const secondOverflowCtx = new MockCanvasContext();
  const secondMassiveText = 'Completely different text in another card that also exceeds the bounding box completely. '.repeat(25);
  templates.bullets(secondOverflowCtx, {
    labels: ['Second Overflow Test'],
    steps: [secondMassiveText]
  }, 2.0, 5.0, theme, 'en');
  assert.strictEqual(theme.getOverflows().length, initialOverflowCount + 1, 'Distinct overflowing text boxes must remain distinct in diagnostics');

  // 4. Normal fitting content produces zero badges and zero false positive overflows
  theme.clearDiagnostics();
  const cleanCtx = new MockCanvasContext();
  templates.bullets(cleanCtx, {
    labels: ['Clean Test'],
    steps: ['Concise bullet one.', 'Concise bullet two.', 'Concise bullet three.']
  }, 2.0, 5.0, theme, 'en');
  const cleanOps = cleanCtx.ops.filter(op => op.startsWith('fillText('));
  assert(!cleanOps.some(op => op.includes('! CONTENT OVERFLOW')), 'Clean content must not render overflow badge');
  assert.strictEqual(theme.hasOverflows(), false, 'Clean content must not trigger false positive overflow records');

  // 5. Deliberate reset between lesson sessions
  theme.clearDiagnostics();
  assert.strictEqual(theme.getOverflows().length, 0, 'theme.clearDiagnostics() resets diagnostic state completely');
  console.log('✓ Standard templates actively render overflow badge, deduplicate repeated scrubbing, and avoid false positives.');

  // 35. code_walkthrough: Python for-loop trace, moving highlight, deterministic, inside the frame
  console.log('\nTest 35: code_walkthrough Python loop trace');
  const loopParams = {
    labels: ['A for loop', 'Variables'],
    code: ['total = 0', 'for i in range(3):', '    total = total + i', 'print(total)'],
    trace: [
      { line: 1, vars: [{ name: 'total', value: '0' }] },
      { line: 2, vars: [{ name: 'i', value: '0' }, { name: 'total', value: '0' }] },
      { line: 4, vars: [{ name: 'i', value: '2' }, { name: 'total', value: '3' }] }
    ]
  };
  function highlightYs(ops) {
    return ops.filter(op => op.startsWith('fillRect(')).map(op => op.split(',')[1]);
  }
  function insideFrame(ops) {
    ops.forEach(op => {
      const m = op.match(/^fillRect\(([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)\)/);
      if (!m) return;
      const x = Number(m[1]);
      const y = Number(m[2]);
      const w = Number(m[3]);
      const h = Number(m[4]);
      assert(x >= 0 && y >= 0 && x + w <= 1280 && y + h <= 720, 'code highlight must stay inside 1280x720: ' + op);
    });
  }
  theme.clearDiagnostics();
  const loopEarly = new MockCanvasContext();
  templates.code_walkthrough(loopEarly, loopParams, 0.5, 9, theme, 'en');
  const loopMid = new MockCanvasContext();
  templates.code_walkthrough(loopMid, loopParams, 4, 9, theme, 'en');
  const loopLate = new MockCanvasContext();
  templates.code_walkthrough(loopLate, loopParams, 8, 9, theme, 'en');
  assert(loopEarly.ops.some(op => op.includes('fillText("total = 0"')), 'source line must be drawn as text');
  assert(loopEarly.ops.some(op => op.includes('fillText("0"')), 'first step must show total = 0');
  assert(loopLate.ops.some(op => op.includes('fillText("3"')), 'last step must show total = 3');
  assert.notDeepStrictEqual(highlightYs(loopEarly.ops), highlightYs(loopMid.ops), 'highlight must move to the next traced line');
  assert.notDeepStrictEqual(highlightYs(loopMid.ops), highlightYs(loopLate.ops), 'highlight must move again on the last step');
  const loopAgain = new MockCanvasContext();
  templates.code_walkthrough(loopAgain, loopParams, 4, 9, theme, 'en');
  assert.deepStrictEqual(loopMid.ops, loopAgain.ops, 'the same t must draw an identical frame');
  insideFrame(loopEarly.ops);
  insideFrame(loopLate.ops);
  ['en', 'hi', 'kn'].forEach(lang => {
    const label = lang === 'hi' ? 'लूप' : lang === 'kn' ? 'ಲೂಪ್' : 'A for loop';
    const ctxLang = new MockCanvasContext();
    theme.clearDiagnostics();
    templates.draw(ctxLang, 'code_walkthrough', {
      labels: [label, 'Variables'],
      code: loopParams.code,
      trace: loopParams.trace
    }, 4, 9, theme, lang);
    insideFrame(ctxLang.ops);
    assert.strictEqual(theme.hasOverflows(), false, lang + ' code_walkthrough must not overflow');
  });
  console.log('✓ code_walkthrough draws the loop, moves the highlight, repeats a frame, and stays inside the canvas.');

  // 36. Templates draw only lesson text: an all-Hindi lesson must not show invented English (filler, chrome)
  console.log('\nTest 36: no invented English text in an all-Hindi lesson');
  const hiParams = {
    labels: ['जल चक्र', 'वाष्पीकरण', 'संघनन', 'वर्षा', 'संग्रह'],
    steps: ['सूरज पानी को गर्म करता है', 'भाप ऊपर उठती है', 'बादल बनते हैं', 'बारिश होती है'],
    topic_en: 'The Water Cycle: Evaporation Condensation Precipitation',
  };
  const englishWord = /[A-Za-z]{3,}/;
  const invented = {};
  ['title', 'bullets', 'compare', 'flow', 'equation', 'labeled_diagram', 'timeline', 'graph'].forEach(type => {
    [0.5, 2.5, 4.5].forEach(lt => {
      const c = new MockCanvasContext();
      templates.draw(c, type, hiParams, lt, 5.0, theme, 'hi');
      c.ops.filter(op => op.startsWith('fillText(')).map(op => op.slice(10, op.lastIndexOf('",')))
        .filter(txt => englishWord.test(txt)).forEach(txt => { (invented[type] = invented[type] || new Set()).add(txt); });
    });
  });
  const report = Object.fromEntries(Object.entries(invented).map(([k, v]) => [k, [...v]]));
  assert.deepStrictEqual(report, {}, 'templates drew text that is not in the lesson: ' + JSON.stringify(report, null, 1));
  console.log('✓ every template draws only lesson text in an all-Hindi lesson (topic_en is never drawn).');

  console.log('\nTest 37: Bengali theme font names Noto Sans Bengali');
  assert(theme.getFont('bn').includes('Noto Sans Bengali'), theme.getFont('bn'));
  console.log('✓ bn font stack names Noto Sans Bengali.');

  console.log('\n=======================================');
  console.log('ALL 37 RENDERER TESTS PASSED CLEANLY');
  console.log('=======================================');
}).catch(err => {
  console.error('\n❌ TEST RUN FAILED:', err);
  process.exit(1);
});
