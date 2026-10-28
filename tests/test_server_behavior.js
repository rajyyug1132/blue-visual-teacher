// tests/test_server_behavior.js — characterization tests for server.js (no dependencies).
//
// Pins the behaviour judges and the browser actually depend on: the dev-server routes, byte ranges
// (audio seeking and duration), HEAD without a body, and the path-escape guard. Run with: node tests/test_server_behavior.js

const http = require('http');
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { createServer } = require('../server.js');

const ROOT = path.resolve(__dirname, '..');
let server;
let port;
let passed = 0;

function request(method, urlPath, headers = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port, method, path: urlPath, headers }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
    });
    req.on('error', reject);
    req.end();
  });
}

async function test(name, fn) {
  try {
    await fn();
    passed += 1;
    console.log(`  ok   ${name}`);
  } catch (err) {
    console.error(`  FAIL ${name}\n       ${err.message}`);
    process.exitCode = 1;
  }
}

(async () => {
  console.log('server.js behaviour');
  server = createServer();
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  port = server.address().port;

  const appJs = fs.statSync(path.join(ROOT, 'web', 'app.js')).size;

  await test('root redirects to the web UI with the offline mock', async () => {
    const res = await request('GET', '/');
    assert.strictEqual(res.status, 302);
    assert.ok(res.headers.location.includes('/web/index.html?mock=1'), res.headers.location);
  });

  await test('a static asset is served with its length and range support', async () => {
    const res = await request('GET', '/web/app.js');
    assert.strictEqual(res.status, 200);
    assert.match(res.headers['content-type'], /application\/javascript/);
    assert.strictEqual(Number(res.headers['content-length']), appJs);
    assert.strictEqual(res.headers['accept-ranges'], 'bytes');
    assert.strictEqual(res.body.length, appJs);
  });

  await test('HEAD returns the headers of the file and no body', async () => {
    const res = await request('HEAD', '/web/app.js');
    assert.strictEqual(res.status, 200);
    assert.strictEqual(Number(res.headers['content-length']), appJs);
    assert.strictEqual(res.body.length, 0);
  });

  await test('a byte range answers 206 with the requested slice', async () => {
    const res = await request('GET', '/web/app.js', { Range: 'bytes=0-99' });
    assert.strictEqual(res.status, 206);
    assert.strictEqual(res.headers['content-range'], `bytes 0-99/${appJs}`);
    assert.strictEqual(res.body.length, 100);
  });

  await test('a suffix range answers the last bytes of the file', async () => {
    const res = await request('GET', '/web/app.js', { Range: 'bytes=-50' });
    assert.strictEqual(res.status, 206);
    assert.strictEqual(res.headers['content-range'], `bytes ${appJs - 50}-${appJs - 1}/${appJs}`);
    assert.strictEqual(res.body.length, 50);
  });

  await test('an unsatisfiable range answers 416 with the file size', async () => {
    const res = await request('GET', '/web/app.js', { Range: 'bytes=99999999-' });
    assert.strictEqual(res.status, 416);
    assert.strictEqual(res.headers['content-range'], `bytes */${appJs}`);
  });

  await test('a malformed range answers 416 instead of crashing', async () => {
    const res = await request('GET', '/web/app.js', { Range: 'bytes=abc' });
    assert.strictEqual(res.status, 416);
  });

  await test('a missing path answers 404', async () => {
    const res = await request('GET', '/definitely-not-here.js');
    assert.strictEqual(res.status, 404);
  });

  await test('path traversal outside the repository answers 403', async () => {
    const res = await request('GET', '/..%2f..%2fWindows/win.ini');
    assert.strictEqual(res.status, 403);
  });

  await test('the bundled Indic fonts are reachable at the URL the pages use', async () => {
    const res = await request('GET', '/renderer/assets/fonts/NotoSansKannada-Regular.ttf');
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.headers['content-type'], 'font/ttf');
    assert.ok(Number(res.headers['content-length']) > 100000);
  });

  await test('/artifacts is served from cache/artifacts so cached lessons download', async () => {
    const dir = path.join(ROOT, 'cache', 'artifacts', '__range_test__');
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'manifest.json'), '{"probe":true}');
    try {
      const res = await request('GET', '/artifacts/__range_test__/manifest.json');
      assert.strictEqual(res.status, 200);
      assert.strictEqual(res.body.toString(), '{"probe":true}');
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  await test('favicon asks are answered with 204', async () => {
    const res = await request('GET', '/favicon.ico');
    assert.strictEqual(res.status, 204);
  });

  server.close();
  console.log(`\n${passed} checks passed${process.exitCode ? ' (with failures)' : ''}`);
})();
