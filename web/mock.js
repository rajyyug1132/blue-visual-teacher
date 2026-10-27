// web/mock.js — Offline Mock API for Blue Visual Teacher (FARHAN_BLUEPRINT.md §7)
// Simulates FastAPI backend endpoints with realistic 6s staged progress when ?mock=1 is set.

(function (root) {
  const isMockParam = new URLSearchParams(root.location.search).get('mock') === '1';

  const mockJobs = new Map();
  let jobCounter = 1000;

  const EXAMPLE_TOPICS = [
    "Ohm's Law",
    "Photosynthesis",
    "Binary Search",
    "Pythagoras Theorem",
    "Water Cycle",
    "Supply and Demand",
    "Newton's Third Law",
    "Monsoon",
    "DNA Replication",
    "GST"
  ];

  function installMockInterceptor() {
    const originalFetch = root.fetch;

    root.fetch = async function (resource, options = {}) {
      const urlStr = typeof resource === 'string' ? resource : resource.url;
      const url = new URL(urlStr, root.location.origin);
      const method = (options.method || 'GET').toUpperCase();

      // 1. GET /api/languages
      if (url.pathname === '/api/languages') {
        return new Response(JSON.stringify(['en', 'hi', 'kn']), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // 2. GET /api/examples
      if (url.pathname === '/api/examples') {
        return new Response(JSON.stringify(EXAMPLE_TOPICS), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // 3. GET /api/health
      if (url.pathname === '/api/health') {
        return new Response(JSON.stringify({
          ollama: true,
          ffmpeg: true,
          chromium: true,
          models_loaded: true,
          offline_flags: true
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // 4. POST /api/generate
      if (url.pathname === '/api/generate' && method === 'POST') {
        let body = {};
        try {
          body = typeof options.body === 'string' ? JSON.parse(options.body) : {};
        } catch (e) {
          body = {};
        }

        const jobId = 'mock_job_' + (++jobCounter);
        const startTime = Date.now();

        mockJobs.set(jobId, {
          jobId,
          topic: body.topic || "Ohm's Law",
          lang: body.lang || 'en',
          startTime
        });

        return new Response(JSON.stringify({ job_id: jobId }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // 5. GET /api/status/:id
      if (url.pathname.startsWith('/api/status/')) {
        const jobId = url.pathname.replace('/api/status/', '');
        const job = mockJobs.get(jobId);

        if (!job) {
          return new Response(JSON.stringify({ error: 'Job not found' }), {
            status: 404,
            headers: { 'Content-Type': 'application/json' }
          });
        }

        const elapsed = (Date.now() - job.startTime) / 1000;
        let stage = 'plan';
        let pct = 15;
        const stage_times = {};

        if (elapsed < 1.2) {
          stage = 'plan';
          pct = Math.round((elapsed / 1.2) * 20);
        } else if (elapsed < 2.5) {
          stage = 'translate';
          stage_times.plan = 1.18;
          pct = 20 + Math.round(((elapsed - 1.2) / 1.3) * 20);
        } else if (elapsed < 4.0) {
          stage = 'tts';
          stage_times.plan = 1.18;
          stage_times.translate = 1.24;
          pct = 40 + Math.round(((elapsed - 2.5) / 1.5) * 25);
        } else if (elapsed < 5.0) {
          stage = 'render';
          stage_times.plan = 1.18;
          stage_times.translate = 1.24;
          stage_times.tts = 1.48;
          pct = 65 + Math.round(((elapsed - 4.0) / 1.0) * 20);
        } else if (elapsed < 5.8) {
          stage = 'encode';
          stage_times.plan = 1.18;
          stage_times.translate = 1.24;
          stage_times.tts = 1.48;
          stage_times.render = 0.96;
          pct = 85 + Math.round(((elapsed - 5.0) / 0.8) * 12);
        } else {
          stage = 'done';
          pct = 100;
          stage_times.plan = 1.18;
          stage_times.translate = 1.24;
          stage_times.tts = 1.48;
          stage_times.render = 0.96;
          stage_times.encode = 0.78;
        }

        const statusResponse = {
          job_id: jobId,
          topic: job.topic,
          lang: job.lang,
          stage,
          pct,
          stage_times,
          telemetry: {
            model: 'qwen2.5:3b',
            tokens: 576,
            num_scenes: 5,
            fallback_used: false,
            device: 'cuda'
          },
          error: null,
          manifest_url: stage === 'done' ? '/fixtures/golden_manifest_en.json' : null,
          mp4_url: stage === 'done' ? '/artifacts/ohms_law_en/lesson.mp4' : null
        };

        return new Response(JSON.stringify(statusResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Delegate all other requests to original fetch
      return originalFetch.apply(this, arguments);
    };

    console.log('[Mock API] Offline Mock Interceptor active (?mock=1)');
  }

  root.MockAPI = {
    isMock: isMockParam,
    install: installMockInterceptor,
    topics: EXAMPLE_TOPICS
  };

  if (isMockParam) {
    installMockInterceptor();
  }
})(typeof window !== 'undefined' ? window : globalThis);
