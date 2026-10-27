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

      const safePath = path.normalize(path.join(REPO_ROOT, pathname));
      if (!safePath.startsWith(REPO_ROOT)) {
        res.writeHead(403, { 'Content-Type': 'text/plain' });
        return res.end('403 Forbidden: Access outside repository root is denied.');
      }

      if (fs.existsSync(safePath) && fs.statSync(safePath).isFile()) {
        const ext = path.extname(safePath).toLowerCase();
        const contentType = MIME_TYPES[ext] || 'application/octet-stream';
        res.writeHead(200, {
          'Content-Type': contentType,
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'no-cache'
        });
        return fs.createReadStream(safePath).pipe(res);
      } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        return res.end(`404 Not Found: ${pathname}`);
      }
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
