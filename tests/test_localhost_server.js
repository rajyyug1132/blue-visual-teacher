// tests/test_localhost_server.js
// Automated verification that server.js runs on localhost and properly renders the application in a real browser.

const http = require('http');
const path = require('path');
const { chromium } = require('playwright');
const { createServer } = require('../server.js');

async function verifyLocalhost() {
  console.log('=== VERIFYING LOCALHOST SERVER AND BROWSER INTEGRATION ===\n');

  // 1. Start server on ephemeral port or 3000
  const server = createServer();
  await new Promise((resolve, reject) => {
    server.listen(0, '127.0.0.1', resolve);
    server.on('error', reject);
  });

  const port = server.address().port;
  const baseUrl = `http://127.0.0.1:${port}`;
  console.log(`✓ Local server running at ${baseUrl}`);

  let browser;
  try {
    // 2. Test HTTP GET / returns 302 redirect
    const redirectRes = await new Promise((resolve) => {
      http.get(`${baseUrl}/`, (res) => {
        resolve({
          statusCode: res.statusCode,
          location: res.headers.location
        });
      });
    });

    if (redirectRes.statusCode !== 302 || (!redirectRes.location.includes('/web/index.html') && !redirectRes.location.includes('/renderer/player.html'))) {
      throw new Error(`Expected 302 redirect from /, got ${redirectRes.statusCode} to ${redirectRes.location}`);
    }
    console.log(`✓ GET / correctly redirects (302) to ${redirectRes.location}`);

    // 3. Launch browser
    browser = await chromium.launch({
      headless: true,
      channel: 'chrome',
      args: ['--disable-gpu-vsync', '--font-render-hinting=none', '--no-sandbox']
    }).catch(async () => {
      return await chromium.launch({
        headless: true,
        args: ['--disable-gpu-vsync', '--font-render-hinting=none', '--no-sandbox']
      });
    });

    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        const loc = msg.location()?.url || '';
        if (text.includes('/renderer/assets/fonts/') || loc.includes('/renderer/assets/fonts/') || loc.includes('.ttf')) {
          // Expected notice for local font files not yet bundled
        } else {
          errors.push(`${text} (${loc})`);
        }
      }
    });

    // 4. Navigate to direct player URL with debug and golden manifest
    const playerUrl = `${baseUrl}/renderer/player.html?debug=1&manifest=/fixtures/golden_manifest_en.json`;
    await page.goto(playerUrl, { waitUntil: 'load' });
    console.log(`✓ Navigated to ${playerUrl} -> loaded ${page.url()}`);

    // 5. Verify stage canvas
    const canvas = await page.$('canvas#stage');
    if (!canvas) throw new Error('canvas#stage not found');
    const box = await canvas.boundingBox();
    if (box.width !== 1280 || box.height !== 720) {
      throw new Error(`Unexpected canvas size: ${box.width}x${box.height}`);
    }
    console.log('✓ Stage canvas verified at 1280x720');

    // 6. Wait for window.ready and golden lesson total duration
    await page.waitForFunction(() => window.ready === true, { timeout: 5000 });
    const duration = await page.evaluate(() => window.totalDuration);
    if (duration !== 54.79) {
      throw new Error(`Expected totalDuration 54.79s, got ${duration}`);
    }
    console.log(`✓ Lesson automatically initialized with duration = ${duration}s`);

    // 7. Verify debug controls and play button are visible
    const debugControls = await page.$('#debug-controls');
    const isVisible = await debugControls.isVisible();
    if (!isVisible) throw new Error('#debug-controls should be visible in debug mode');
    console.log('✓ Interactive debug scrubber controls are visible');

    const playBtn = await page.$('#debug-play-btn');
    if (!playBtn) throw new Error('#debug-play-btn not found');
    console.log('✓ Play/Pause button verified');

    // 8. Test canvas non-blank at t = 0
    const hasDrawn = await page.evaluate(() => {
      const c = document.getElementById('stage');
      const ctx = c.getContext('2d');
      const imgData = ctx.getImageData(0, 0, 1280, 720).data;
      for (let i = 0; i < imgData.length; i += 16) {
        if (imgData[i] > 20 || imgData[i + 1] > 30 || imgData[i + 2] > 60) return true;
      }
      return false;
    });
    if (!hasDrawn) throw new Error('Canvas is blank at initial render');
    console.log('✓ Initial frame rendered cleanly on canvas');

    // 9. Test scrubbing via input slider
    await page.evaluate(() => {
      const scrubber = document.getElementById('debug-scrubber');
      scrubber.value = 25.0;
      scrubber.dispatchEvent(new Event('input', { bubbles: true }));
    });
    const scrubTime = await page.$eval('#debug-time', el => el.textContent);
    if (scrubTime !== '25.00s') {
      throw new Error(`Expected debug time 25.00s after scrub, got ${scrubTime}`);
    }
    console.log('✓ Scrubber slider tested: successfully sought to 25.00s (Equation scene)');

    // 10. Test Play button
    await playBtn.click();
    const btnTextDuringPlay = await playBtn.textContent();
    if (!btnTextDuringPlay.includes('Pause')) {
      throw new Error(`Expected button text to show Pause, got ${btnTextDuringPlay}`);
    }
    await page.waitForTimeout(400); // let it animate slightly
    const advancedTime = await page.evaluate(() => parseFloat(document.getElementById('debug-scrubber').value));
    if (advancedTime <= 25.0) {
      throw new Error(`Playback did not advance time: ${advancedTime}`);
    }
    console.log(`✓ Playback animation verified: time advanced to ${advancedTime.toFixed(2)}s`);

    // Pause again
    await playBtn.click();
    const btnTextAfterPause = await playBtn.textContent();
    if (!btnTextAfterPause.includes('Play')) {
      throw new Error(`Expected button text to revert to Play, got ${btnTextAfterPause}`);
    }
    console.log('✓ Pause functionality verified');

    if (errors.length > 0) {
      throw new Error(`Encountered page errors: ${errors.join(', ')}`);
    }

    console.log('\n======================================================');
    console.log(' ALL LOCALHOST SERVER & BROWSER CHECKS PASSED CLEANLY');
    console.log('======================================================');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

verifyLocalhost().catch(err => {
  console.error('\nFAILED:', err);
  process.exit(1);
});
