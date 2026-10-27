// tests/test_renderer.js
// Lightweight test suite for renderer foundation without browser/external dependencies.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const theme = require('../renderer/theme');
const templates = require('../renderer/templates');
const engine = require('../renderer/engine');

console.log('--- RUNNING RENDERER UNIT TESTS ---');

// 1. Test Theme helpers
console.log('Test 1: Theme helpers and PRNG determinism');
const rng1 = theme.rng(42);
const seq1 = [rng1(), rng1(), rng1()];
const rng2 = theme.rng(42);
const seq2 = [rng2(), rng2(), rng2()];
assert.deepStrictEqual(seq1, seq2, 'PRNG must be strictly deterministic given same seed');
assert.strictEqual(theme.easeOutCubic(0), 0);
assert.strictEqual(theme.easeOutCubic(1), 1);
console.log('✓ Theme helpers and PRNG passed.');

// 2. Test Golden Manifest structure
console.log('Test 2: Golden manifest loading & scene timeline');
const manifestPath = path.join(__dirname, '../fixtures/golden_manifest_en.json');
assert(fs.existsSync(manifestPath), 'golden_manifest_en.json must exist');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

assert.strictEqual(manifest.scenes.length, 5);
assert.strictEqual(manifest.total_sec, 54.79);
assert.strictEqual(manifest.scenes[0].start_sec, 0.0);
assert.strictEqual(manifest.scenes[0].duration_sec, 9.92);
console.log('✓ Golden manifest verified.');

// 3. Test Scene boundary logic
console.log('Test 3: Scene boundary detection');
const s0 = engine.getActiveScene(manifest.scenes, 0.0);
assert.strictEqual(s0.id, 1);

const sMid = engine.getActiveScene(manifest.scenes, 15.0);
assert.strictEqual(sMid.id, 2);

const sBoundary = engine.getActiveScene(manifest.scenes, 9.92);
assert.strictEqual(sBoundary.id, 2);

const sEnd = engine.getActiveScene(manifest.scenes, 54.79);
assert.strictEqual(sEnd.id, 5);

const sBeyond = engine.getActiveScene(manifest.scenes, 100.0);
assert.strictEqual(sBeyond.id, 5);
console.log('✓ Scene boundary detection passed.');

// 4. Test Mock Canvas Rendering & Determinism
console.log('Test 4: Mock Canvas Rendering & Determinism across timestamps');

class MockContext {
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
  arcTo(x1, y1, x2, y2, r) { this.ops.push(`arcTo(${x1.toFixed(1)},${y1.toFixed(1)},${x2.toFixed(1)},${y2.toFixed(1)},${r})`); }
  arc(x, y, r, sa, ea) { this.ops.push(`arc(${x.toFixed(1)},${y.toFixed(1)},${r.toFixed(1)})`); }
  fillRect(x, y, w, h) { this.ops.push(`fillRect(${x.toFixed(1)},${y.toFixed(1)},${w.toFixed(1)},${h.toFixed(1)})`); }
  fillText(text, x, y) { this.ops.push(`fillText("${text}",${x.toFixed(1)},${y.toFixed(1)})`); }
  stroke() { this.ops.push('stroke'); }
  fill() { this.ops.push('fill'); }
  measureText(text) { return { width: (text ? text.length * 10 : 0) }; }
}

const mockCanvas = { width: 1280, height: 720 };
const mockCtx1 = new MockContext();
engine.setCanvas(mockCanvas, mockCtx1);

// Initialize engine
engine.initLesson(manifest.title, manifest.scenes, manifest.lang).then(() => {
  assert.strictEqual(globalThis.totalDuration, 54.79);
  assert.strictEqual(globalThis.ready, true);

  // Render at t = 5.0
  engine.renderAtTime(5.0);
  const ops1 = [...mockCtx1.ops];

  // Render again at t = 5.0 on a fresh context
  const mockCtx2 = new MockContext();
  engine.setCanvas(mockCanvas, mockCtx2);
  engine.renderAtTime(5.0);
  const ops2 = [...mockCtx2.ops];

  assert.deepStrictEqual(ops1, ops2, 'Rendering at the exact same timestamp must produce identical draw operations (deterministic)');
  console.log('✓ Deterministic rendering verified.');

  // Test full scrubber loop in steps of 0.25s
  console.log('Test 5: Full timeline scrubbing');
  let frameCount = 0;
  for (let t = 0; t <= manifest.total_sec; t += 0.25) {
    const rendered = engine.renderAtTime(t);
    assert(rendered, `Frame must render successfully at t = ${t}`);
    frameCount++;
  }
  console.log(`✓ Successfully rendered ${frameCount} frames without errors.`);

  // Test unknown template graceful fallback
  console.log('Test 6: Graceful fallback for unknown template');
  const fallbackCtx = new MockContext();
  templates.draw(fallbackCtx, 'unknown_exotic_template', { labels: ['Heading'], steps: ['Item 1'] }, 1.0, 5.0, theme, 'en');
  const hasHeading = fallbackCtx.ops.some(op => op.includes('fillText("Heading"'));
  assert(hasHeading, 'Unknown template must degrade safely to bullets without crashing');
  console.log('✓ Graceful fallback verified.');

  console.log('\n--- ALL RENDERER TESTS PASSED ---');
}).catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
