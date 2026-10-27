// server.js — Zero-dependency local development server for Blue Visual Teacher
// Serves the static app, the bundled fonts and the cached lessons, and routes / to the web UI.
// Mirrors the mounts in exporter/app.py so the browser behaves the same against either server.

const http = require('http');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname);
const PORT = parseInt(process.env.PORT, 10) || 3000;
const HOST = process.env.HOST || '0.0.0.0';

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
  '.wav': 'audio/wav',
  '.mp4': 'video/mp4',
  '.svg': 'image/svg+xml'
};

const ROOT_REDIRECT = '/web/index.html?mock=1';

// URL prefixes that map onto a directory outside their own URL path, mirroring the mounts in
// exporter/app.py: player.html asks for assets/fonts relative to itself, and cached lessons live
// in cache/artifacts while being served under /artifacts.
const ALIASES = [
  ['/renderer/assets/fonts/', path.join(REPO_ROOT, 'assets', 'fonts')],
  ['/assets/fonts/', path.join(REPO_ROOT, 'assets', 'fonts')],
  ['/artifacts/', path.join(REPO_ROOT, 'cache', 'artifacts')],
  ['/cache/plans/', path.join(REPO_ROOT, 'cache', 'plans')],
  ['/cache/artifacts/', path.join(REPO_ROOT, 'cache', 'artifacts')]
];

function resolveFile(pathname) {
  for (const [prefix, folder] of ALIASES) {
    if (pathname.startsWith(prefix)) {
      return path.join(folder, pathname.slice(prefix.length));
    }
  }
  return path.join(REPO_ROOT, pathname);
}

function isInside(root, target) {
  const base = root.endsWith(path.sep) ? root : root + path.sep;
  return target === root || target.startsWith(base);
}

function sendText(res, status, message) {
  res.writeHead(status, { 'Content-Type': 'text/plain' });
  res.end(message);
}

// Resolves a "bytes=" header against the file size. Returns {start, end} when the client asked for
// a slice that exists, and null for a malformed or unsatisfiable request (the caller answers 416).
function parseByteRange(header, size) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(String(header).trim());
  if (!match || (match[1] === '' && match[2] === '')) return null;

  let start;
  let end;
  if (match[1] === '') {                       // suffix form: "bytes=-500" means the last 500 bytes
    start = Math.max(0, size - parseInt(match[2], 10));
    end = size - 1;
  } else {
    start = parseInt(match[1], 10);
    end = match[2] === '' ? size - 1 : Math.min(parseInt(match[2], 10), size - 1);
  }
  return start > end || start >= size ? null : { start, end };
}

// Writes a file and returns false when there is nothing to serve, so the caller can answer 404.
// Byte ranges are required for <audio>/<video> seeking and for the browser to report a real
// duration; without them a WAV served here shows duration NaN.
function sendFile(req, res, filePath) {
  let stat;
  try {
    stat = fs.statSync(filePath);
  } catch (err) {
    return false;
  }
  if (!stat.isFile()) return false;

  const size = stat.size;
  const headers = {
    'Content-Type': MIME_TYPES[path.extname(filePath).toLowerCase()] || 'application/octet-stream',
    'Accept-Ranges': 'bytes',
    'Access-Control-Allow-Origin': '*',
    'Cache-Control': 'no-cache'
  };

  if (req.headers.range) {
    const range = parseByteRange(req.headers.range, size);
    if (!range) {
      res.writeHead(416, { ...headers, 'Content-Range': `bytes */${size}` });
      res.end();
      return true;
    }
    res.writeHead(206, {
      ...headers,
      'Content-Range': `bytes ${range.start}-${range.end}/${size}`,
      'Content-Length': String(range.end - range.start + 1)
    });
    if (req.method === 'HEAD') res.end();
    else fs.createReadStream(filePath, range).pipe(res);
    return true;
  }

  res.writeHead(200, { ...headers, 'Content-Length': String(size) });
  if (req.method === 'HEAD') res.end();
  else fs.createReadStream(filePath).pipe(res);
  return true;
}

function handle(req, res) {
  try {
    const pathname = decodeURIComponent(new URL(req.url, `http://127.0.0.1:${PORT}`).pathname);

    if (pathname === '/') {
      res.writeHead(302, { 'Location': ROOT_REDIRECT });
      return res.end();
    }
    if (pathname === '/favicon.ico') {
      res.writeHead(204);
      return res.end();
    }

    const filePath = path.normalize(resolveFile(pathname));
    if (!isInside(REPO_ROOT, filePath)) {
      return sendText(res, 403, '403 Forbidden: Access outside repository root is denied.');
    }
    if (!sendFile(req, res, filePath)) {
      return sendText(res, 404, `404 Not Found: ${pathname}`);
    }
  } catch (err) {
    // Headers are already on the wire when a stream fails mid-file, so only report what we still can.
    if (res.headersSent) return res.destroy();
    return sendText(res, 500, `500 Internal Server Error: ${err.message}`);
  }
}

function createServer() {
  return http.createServer(handle);
}

if (require.main === module) {
  const server = createServer();
  server.listen(PORT, HOST, () => {
    console.log('====================================================');
    console.log(' Blue Visual Teacher — Local Development Server');
    console.log('====================================================');
    console.log(` ✓ Running at:        http://localhost:${PORT}`);
    console.log(` ✓ Local IP:          http://127.0.0.1:${PORT}`);
    console.log(` ✓ Web UI:            http://localhost:${PORT}/`);
    console.log(` ✓ Direct Player:     http://localhost:${PORT}/renderer/player.html?debug=1`);
    console.log(` ✓ Offline Fixture:   http://localhost:${PORT}/fixtures/golden_manifest_en.json`);
    console.log('====================================================');
    console.log('Server is running continuously in the background.\n');
  });

  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.error(`\n[ERROR] Port ${PORT} is already in use.`);
      console.error(`Try specifying another port: $env:PORT="3001"; npm start\n`);
    } else {
      console.error(`\n[ERROR] Server error: ${err.message}\n`);
    }
    process.exit(1);
  });
}

module.exports = { createServer, PORT, HOST, MIME_TYPES };
