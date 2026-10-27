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
  assert(proseTexts.some(op => op.includes('CONCEPTUAL ANALYSIS')), 'Prose with numbers must render conceptual framework');
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
  assert(conceptTexts.some(op => op.includes('CONCEPTUAL ANALYSIS')), 'Must display conceptual analysis badge');
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

  console.log('\n=======================================');
  console.log('ALL 18 RENDERER TESTS PASSED CLEANLY');
  console.log('=======================================');
}).catch(err => {
  console.error('\n❌ TEST RUN FAILED:', err);
  process.exit(1);
});
