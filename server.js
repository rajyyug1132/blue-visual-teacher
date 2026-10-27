// server.js — Zero-dependency local development server for Blue Visual Teacher
// Serves static assets, routes root / to player.html, and enables local offline browser usage.

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

// URL prefixes that map onto a directory outside their own URL path, mirroring the mounts in
// exporter/app.py so the static dev server behaves like the FastAPI backend:
//   /renderer/assets/fonts/*  ->  assets/fonts/*   (player.html asks for assets/fonts relative to itself)
//   /artifacts/*              ->  cache/artifacts/* (tier-2 cached lessons: manifest, wav, mp4)
const ALIASES = [
  ['/renderer/assets/fonts/', path.join(REPO_ROOT, 'assets', 'fonts')],
  ['/assets/fonts/', path.join(REPO_ROOT, 'assets', 'fonts')],
  ['/artifacts/', path.join(REPO_ROOT, 'cache', 'artifacts')]
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

function createServer() {
  return http.createServer((req, res) => {
    try {
      const parsedUrl = new URL(req.url, `http://127.0.0.1:${PORT}`);
      let pathname = decodeURIComponent(parsedUrl.pathname);

      // Route root to the web UI (FARHAN_BLUEPRINT.md §7 / AYUSH_BLUEPRINT.md §4)
      if (pathname === '/') {
        res.writeHead(302, {
          'Location': '/web/index.html?mock=1'
        });
        return res.end();
      }

      if (pathname === '/favicon.ico') {
        res.writeHead(204);
        return res.end();
      }

      const safePath = path.normalize(resolveFile(pathname));
      if (!isInside(REPO_ROOT, safePath)) {
        res.writeHead(403, { 'Content-Type': 'text/plain' });
        return res.end('403 Forbidden: Access outside repository root is denied.');
      }

      let stat = null;
      try {
        stat = fs.statSync(safePath);
      } catch (e) {
        stat = null;
      }

      if (!stat || !stat.isFile()) {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        return res.end(`404 Not Found: ${pathname}`);
      }

      const ext = path.extname(safePath).toLowerCase();
      const contentType = MIME_TYPES[ext] || 'application/octet-stream';
      const size = stat.size;
      const headers = {
        'Content-Type': contentType,
        'Accept-Ranges': 'bytes',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache'
      };

      // Byte ranges are required for <audio>/<video> seeking and for Safari/Chromium to report
      // a real duration; without them a WAV served over this server shows duration NaN.
      const range = req.headers.range;
      if (range) {
        const match = /^bytes=(\d*)-(\d*)$/.exec(String(range).trim());
        let start = match && match[1] !== '' ? parseInt(match[1], 10) : null;
        let end = match && match[2] !== '' ? parseInt(match[2], 10) : null;

        if (!match || (start === null && end === null)) {
          res.writeHead(416, { ...headers, 'Content-Range': `bytes */${size}` });
          return res.end();
        }
        if (start === null) {              // suffix range: last N bytes
          start = Math.max(0, size - end);
          end = size - 1;
        } else if (end === null || end >= size) {
          end = size - 1;
        }
        if (start > end || start >= size) {
          res.writeHead(416, { ...headers, 'Content-Range': `bytes */${size}` });
          return res.end();
        }

        res.writeHead(206, {
          ...headers,
          'Content-Range': `bytes ${start}-${end}/${size}`,
          'Content-Length': String(end - start + 1)
        });
        if (req.method === 'HEAD') return res.end();
        return fs.createReadStream(safePath, { start, end }).pipe(res);
      }

      res.writeHead(200, { ...headers, 'Content-Length': String(size) });
      if (req.method === 'HEAD') return res.end();
      return fs.createReadStream(safePath).pipe(res);
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      return res.end(`500 Internal Server Error: ${err.message}`);
    }
  });
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
