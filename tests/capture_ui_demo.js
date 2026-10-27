// tests/capture_ui_demo.js
// Runs an end-to-end browser walkthrough of the Web UI and captures screenshots at each stage.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { createServer } = require('../server.js');

const ARTIFACT_BRAIN_DIR = 'C:\\Users\\farha\\.gemini\\antigravity\\brain\\22af160a-8ebc-48bd-8219-3bb5abc0dfbf\\demo_screenshots';
const LOCAL_OUTPUT_DIR = path.join(__dirname, '..', 'artifacts', 'ui-walkthrough');

async function captureDemo() {
  console.log('=== STARTING BROWSER WALKTHROUGH TEST ===\n');

  if (!fs.existsSync(LOCAL_OUTPUT_DIR)) {
    fs.mkdirSync(LOCAL_OUTPUT_DIR, { recursive: true });
  }
  if (!fs.existsSync(ARTIFACT_BRAIN_DIR)) {
    fs.mkdirSync(ARTIFACT_BRAIN_DIR, { recursive: true });
  }

  // 1. Start server
  const server = createServer();
  await new Promise((resolve, reject) => {
    server.listen(0, '127.0.0.1', resolve);
    server.on('error', reject);
  });
  const port = server.address().port;
  const baseUrl = `http://127.0.0.1:${port}`;
  console.log(`✓ Local server running at ${baseUrl}`);

  // 2. Launch browser
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      channel: 'chrome',
      args: ['--disable-gpu-vsync', '--font-render-hinting=none', '--no-sandbox']
    });
    console.log(`✓ Browser launched: Google Chrome (${browser.version()})`);
  } catch (e) {
    browser = await chromium.launch({
      headless: true,
      args: ['--disable-gpu-vsync', '--font-render-hinting=none', '--no-sandbox']
    });
    console.log(`✓ Browser launched: Playwright Chromium (${browser.version()})`);
  }

  const page = await browser.newPage({
    viewport: { width: 1366, height: 820 },
    deviceScaleFactor: 1
  });

  async function saveShot(filename, caption) {
    const localPath = path.join(LOCAL_OUTPUT_DIR, filename);
    const brainPath = path.join(ARTIFACT_BRAIN_DIR, filename);
    await page.screenshot({ path: localPath, fullPage: false });
    fs.copyFileSync(localPath, brainPath);
    console.log(`  📸 Captured: ${filename} — ${caption}`);
  }

  try {
    // Stage 1: Initial Landing View
    console.log('\n[Stage 1] Loading Web UI...');
    await page.goto(baseUrl, { waitUntil: 'networkidle' });
    await page.waitForTimeout(400);
    await saveShot('01_web_ui_landing.png', 'Web UI Initial Landing View (Offline badge, topic search, example chips, player card)');

    // Stage 2: Trigger Generation on Example Chip "Ohm's Law"
    console.log('\n[Stage 2] Triggering generation via "Ohm\'s Law" example chip...');
    await page.click('button.example-chip:has-text("Ohm\'s Law")');
    await page.waitForTimeout(2200); // Capture mid-pipeline
    await saveShot('02_generation_progress_stepper.png', '5-Step Stepper in action with real-time stage elapsed seconds');

    // Stage 3: Wait for generation completion and player initial frame
    console.log('\n[Stage 3] Awaiting generation completion...');
    await page.waitForSelector('.step-item#step-encode.done', { timeout: 15000 });
    await page.waitForTimeout(500);
    await saveShot('03_player_scene1_title.png', 'Generation Complete: In-app Player playing Scene 1 (Title & Bengaluru voltage drop)');

    // Stage 4: Scrub to Scene 2 (Compare: Water Tank Analogy)
    console.log('\n[Stage 4] Seeking to Scene 2: Compare template...');
    await page.evaluate(() => {
      const scrubber = document.getElementById('lesson-scrubber');
      scrubber.value = 15.0;
      scrubber.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await page.waitForTimeout(300);
    await saveShot('04_player_scene2_compare.png', 'Scene 2: Water Tank Comparison (Voltage, Current, Resistance columns)');

    // Stage 5: Scrub to Scene 3 (Equation: V = I x R)
    console.log('\n[Stage 5] Seeking to Scene 3: Equation template...');
    await page.evaluate(() => {
      const scrubber = document.getElementById('lesson-scrubber');
      scrubber.value = 25.0;
      scrubber.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await page.waitForTimeout(300);
    await saveShot('05_player_scene3_equation.png', 'Scene 3: Ohm\'s Equation (V = I × R formula glow & derived formulas)');

    // Stage 6: Scrub to Scene 4 (Flow: 230V Indian Socket Calculation)
    console.log('\n[Stage 6] Seeking to Scene 4: Flow template...');
    await page.evaluate(() => {
      const scrubber = document.getElementById('lesson-scrubber');
      scrubber.value = 36.0;
      scrubber.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await page.waitForTimeout(300);
    await saveShot('06_player_scene4_flow.png', 'Scene 4: Flow Diagram (230V Indian socket -> 46Ω heater -> 5A current)');

    // Stage 7: Scrub to Scene 5 (Recap Bullets)
    console.log('\n[Stage 7] Seeking to Scene 5: Bullets template...');
    await page.evaluate(() => {
      const scrubber = document.getElementById('lesson-scrubber');
      scrubber.value = 50.0;
      scrubber.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await page.waitForTimeout(300);
    await saveShot('07_player_scene5_bullets.png', 'Scene 5: Recap Bullets holding frame');

    // Stage 8: Open Timings & Telemetry Drawer
    console.log('\n[Stage 8] Opening Timings & Telemetry Drawer...');
    await page.click('#toggle-timings-btn');
    await page.waitForTimeout(300);
    await saveShot('08_timings_and_download.png', 'Timings & Telemetry Drawer open with MP4 Download button ready');

    console.log('\n====================================================');
    console.log(' ALL 8 BROWSER WALKTHROUGH SCREENSHOTS CAPTURED');
    console.log('====================================================\n');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

captureDemo().catch(err => {
  console.error('\nFatal capture error:', err);
  process.exit(1);
});
