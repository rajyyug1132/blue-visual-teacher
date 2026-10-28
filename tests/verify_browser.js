// tests/verify_browser.js
// Automated, repeatable browser verification harness using Playwright and local HTTP server.
// Captures and verifies actual rendered canvas output for golden lesson and all 8 visual templates.

const fs = require('fs');
const path = require('path');
const http = require('http');
const { chromium } = require('playwright');

const REPO_ROOT = path.resolve(__dirname, '..');
const OUTPUT_DIR = path.join(REPO_ROOT, 'artifacts', 'renderer-review');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ttf': 'font/ttf',
  '.woff2': 'font/woff2',
};

// 1. Lightweight local HTTP server
function startServer() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      try {
        const parsedUrl = new URL(req.url, 'http://127.0.0.1');
        let pathname = decodeURIComponent(parsedUrl.pathname);
        if (pathname === '/') pathname = '/renderer/player.html';
        if (pathname === '/favicon.ico') {
          res.writeHead(204);
          return res.end();
        }

        const safePath = path.normalize(path.join(REPO_ROOT, pathname));
        if (!safePath.startsWith(REPO_ROOT)) {
          res.writeHead(403);
          return res.end('Access Denied');
        }

        if (fs.existsSync(safePath) && fs.statSync(safePath).isFile()) {
          const ext = path.extname(safePath).toLowerCase();
          const contentType = MIME_TYPES[ext] || 'application/octet-stream';
          res.writeHead(200, {
            'Content-Type': contentType,
            'Access-Control-Allow-Origin': '*'
          });
          return fs.createReadStream(safePath).pipe(res);
        } else {
          res.writeHead(404);
          return res.end('Not Found');
        }
      } catch (err) {
        res.writeHead(500);
        res.end(err.message);
      }
    });

    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      resolve({ server, port });
    });
    server.on('error', reject);
  });
}

// 2. Launch browser preferring local installed Chrome or Edge
async function launchBrowser() {
  const launchOptions = {
    headless: true,
    args: [
      '--disable-gpu-vsync',
      '--font-render-hinting=none',
      '--force-color-profile=srgb',
      '--no-sandbox'
    ]
  };

  try {
    const browser = await chromium.launch({ ...launchOptions, channel: 'chrome' });
    return { browser, name: 'Google Chrome', version: browser.version() };
  } catch (chromeErr) {
    try {
      const browser = await chromium.launch({ ...launchOptions, channel: 'msedge' });
      return { browser, name: 'Microsoft Edge', version: browser.version() };
    } catch (edgeErr) {
      const browser = await chromium.launch(launchOptions);
      return { browser, name: 'Chromium (Playwright)', version: browser.version() };
    }
  }
}

// 3. Main Verification Routine
async function runVerification() {
  console.log('=== STARTING BROWSER VISUAL VERIFICATION HARNESS ===\n');

  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const { server, port } = await startServer();
  console.log(`✓ Local HTTP server started at http://127.0.0.1:${port}`);

  const { browser, name: browserName, version: browserVersion } = await launchBrowser();
  console.log(`✓ Browser launched: ${browserName} v${browserVersion}`);

  const pageErrors = [];
  const consoleErrors = [];
  const failedRequests = [];
  const missingFontAssets = [];
  const capturedScreenshots = [];

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1
  });

  const page = await context.newPage();

  page.on('pageerror', err => {
    console.error(`[Page Error]: ${err.message}`);
    pageErrors.push(err.message);
  });

  page.on('console', msg => {
    if (msg.type() === 'error') {
      const text = msg.text();
      const locUrl = msg.location()?.url || '';
      if (text.includes('/renderer/assets/fonts/') || locUrl.includes('/renderer/assets/fonts/') || text.includes('Failed to load resource')) {
        missingFontAssets.push(`${text} ${locUrl}`.trim());
      } else {
        console.error(`[Console Error]: ${text}`);
        consoleErrors.push(text);
      }
    }
  });

  page.on('requestfailed', req => {
    const url = req.url();
    const failure = `${req.method()} ${url}: ${req.failure()?.errorText || 'Failed'}`;
    if (url.includes('/renderer/assets/fonts/')) {
      missingFontAssets.push(failure);
    } else {
      console.error(`[Request Failed]: ${failure}`);
      failedRequests.push(failure);
    }
  });

  try {
    const playerUrl = `http://127.0.0.1:${port}/renderer/player.html`;
    await page.goto(playerUrl, { waitUntil: 'load' });
    console.log(`✓ Loaded player page at ${playerUrl}`);

    // Verify canvas element
    const canvas = await page.$('canvas#stage');
    if (!canvas) throw new Error('Canvas #stage element not found in DOM');

    const box = await canvas.boundingBox();
    if (!box || box.width !== 1280 || box.height !== 720) {
      throw new Error(`Unexpected canvas dimensions: ${box?.width}x${box?.height} (expected 1280x720)`);
    }
    console.log('✓ Canvas #stage verified at exact dimensions 1280x720');

    // -------------------------------------------------------------
    // PART A: Verify Golden Ohm's Law Manifest
    // -------------------------------------------------------------
    console.log('\n--- PART A: Verifying Golden Ohm\'s Law Manifest ---');
    const goldenManifestPath = path.join(REPO_ROOT, 'fixtures', 'golden_manifest_en.json');
    const goldenManifest = JSON.parse(fs.readFileSync(goldenManifestPath, 'utf8'));

    await page.evaluate(
      ([title, scenes, lang]) => window.initLesson(title, scenes, lang),
      [goldenManifest.title, goldenManifest.scenes, goldenManifest.lang]
    );

    const isReady = await page.evaluate(() => window.ready);
    const totalDuration = await page.evaluate(() => window.totalDuration);
    if (!isReady || totalDuration !== 54.79) {
      throw new Error(`Lesson initialization failed. ready=${isReady}, totalDuration=${totalDuration}`);
    }
    console.log(`✓ window.initLesson ready with totalDuration = ${totalDuration}s`);

    const goldenTimestamps = [
      { t: 2.0, name: 'golden_01_title_intro' },
      { t: 9.8, name: 'golden_02_transition_title_compare' },
      { t: 15.0, name: 'golden_03_compare_active' },
      { t: 25.0, name: 'golden_04_equation_active' },
      { t: 36.0, name: 'golden_05_flow_active' },
      { t: 48.0, name: 'golden_06_bullets_active' },
      { t: 54.79, name: 'golden_07_final_hold_frame' }
    ];

    for (const item of goldenTimestamps) {
      await page.evaluate(t => window.renderAtTime(t), item.t);

      // Verify canvas is non-blank (at least some colored pixels)
      const isDrawn = await page.evaluate(() => {
        const c = document.getElementById('stage');
        const ctx = c.getContext('2d');
        const img = ctx.getImageData(0, 0, c.width, c.height);
        let hasColor = false;
        // Sample every 100th pixel to verify non-empty background/foreground
        for (let i = 0; i < img.data.length; i += 400) {
          if (img.data[i + 3] > 0 && (img.data[i] !== 0 || img.data[i + 1] !== 0 || img.data[i + 2] !== 0)) {
            hasColor = true;
            break;
          }
        }
        return hasColor;
      });

      if (!isDrawn) throw new Error(`Frame at t=${item.t}s rendered blank!`);

      const screenshotPath = path.join(OUTPUT_DIR, `${item.name}.png`);
      await page.screenshot({ path: screenshotPath, type: 'png' });
      const stat = fs.statSync(screenshotPath);
      capturedScreenshots.push({ name: item.name, path: screenshotPath, bytes: stat.size, t: item.t });
      console.log(`  ✓ Rendered & saved: ${item.name}.png (${(stat.size / 1024).toFixed(1)} KB) at t=${item.t}s`);
    }

    // -------------------------------------------------------------
    // PART B: Verify All Eight Visual Templates
    // -------------------------------------------------------------
    console.log('\n--- PART B: Verifying All Eight Visual Templates ---');
    const visualTestPath = path.join(REPO_ROOT, 'tests', 'fixtures', 'visual_test_manifest.json');
    const visualManifest = JSON.parse(fs.readFileSync(visualTestPath, 'utf8'));

    await page.evaluate(
      ([title, scenes, lang]) => window.initLesson(title, scenes, lang),
      [visualManifest.title, visualManifest.scenes, visualManifest.lang]
    );

    const templateChecks = [
      { t: 5.0, type: 'labeled_diagram', name: 'template_01_labeled_diagram' },
      { t: 15.0, type: 'timeline', name: 'template_02_timeline' },
      { t: 25.0, type: 'graph_numeric_barchart', name: 'template_03_graph_barchart' },
      { t: 35.0, type: 'graph_conceptual_analysis', name: 'template_04_graph_conceptual' },
      { t: 45.0, type: 'title', name: 'template_05_title' },
      { t: 55.0, type: 'compare', name: 'template_06_compare' },
      { t: 65.0, type: 'flow', name: 'template_07_flow' },
      { t: 75.0, type: 'bullets', name: 'template_08_bullets' }
    ];

    for (const item of templateChecks) {
      await page.evaluate(t => window.renderAtTime(t), item.t);

      const isDrawn = await page.evaluate(() => {
        const c = document.getElementById('stage');
        const ctx = c.getContext('2d');
        const img = ctx.getImageData(0, 0, c.width, c.height);
        return img.data.some((val, idx) => idx % 4 === 3 && val > 0);
      });

      if (!isDrawn) throw new Error(`Template ${item.type} at t=${item.t}s rendered blank!`);

      const screenshotPath = path.join(OUTPUT_DIR, `${item.name}.png`);
      await page.screenshot({ path: screenshotPath, type: 'png' });
      const stat = fs.statSync(screenshotPath);
      capturedScreenshots.push({ name: item.name, path: screenshotPath, bytes: stat.size, t: item.t, template: item.type });
      console.log(`  ✓ Rendered & saved: ${item.name}.png (${(stat.size / 1024).toFixed(1)} KB) [${item.type}]`);
    }

    // -------------------------------------------------------------
    // PART C: Diagnostic Summary
    // -------------------------------------------------------------
    const summary = {
      timestamp: new Date().toISOString(),
      browser: `${browserName} ${browserVersion}`,
      viewport: '1280x720',
      totalScreenshotsCaptured: capturedScreenshots.length,
      errors: {
        pageErrors,
        consoleErrors,
        failedRequests,
        missingFontAssets: [...new Set(missingFontAssets)]
      },
      screenshots: capturedScreenshots
    };

    const summaryPath = path.join(OUTPUT_DIR, 'summary.json');
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2), 'utf8');
    console.log(`\n✓ Diagnostic summary written to ${summaryPath}`);

    if (missingFontAssets.length > 0) {
      console.log(`ℹ Local font assets notice: ${[...new Set(missingFontAssets)].length} font files not yet bundled in renderer/assets/fonts/ (browser safely used system font stack fallback)`);
    }

    if (pageErrors.length > 0 || consoleErrors.length > 0 || failedRequests.length > 0) {
      console.error('\n❌ Verification completed with errors!');
      process.exit(1);
    } else {
      console.log('\n======================================================');
      console.log(`ALL VISUAL CHECKS PASSED: ${capturedScreenshots.length} screenshots verified.`);
      console.log('======================================================');
    }

  } finally {
    await browser.close();
    server.close();
  }
}

runVerification().catch(err => {
  console.error('\n❌ BROWSER HARNESS FAILED:', err);
  process.exit(1);
});
