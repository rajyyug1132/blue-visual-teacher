// web/mock.js — Offline Mock API for Blue Visual Teacher (FARHAN_BLUEPRINT.md §7)
// Answers the same endpoints as exporter/app.py when the page is opened with ?mock=1, so the UI can
// be demoed without loading the models. A topic that already exists in cache/artifacts is served
// from there (manifest + narration + MP4); anything else walks a scripted progress timeline and
// provides topic-accurate pedagogical scene manifests matching orchestrator standards.

(function (root) {
  const isMockParam = new URLSearchParams(root.location.search).get('mock') === '1';

  const mockJobs = new Map();
  let jobCounter = 1000;
  let originalFetch = root.fetch;

  const FIXTURE_LANGS = ['en', 'hi', 'kn'];

  const EXAMPLES = [
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

  // The scripted demo timeline. Each stage runs until its `until` second, moving the progress bar
  // from `fromPct` to `toPct`; `duration` is the per-stage time the telemetry drawer reports.
  const STAGES = [
    { name: 'plan', until: 1.2, fromPct: 0, toPct: 20, duration: 1.18 },
    { name: 'translate', until: 2.5, fromPct: 20, toPct: 40, duration: 1.24 },
    { name: 'tts', until: 4.0, fromPct: 40, toPct: 65, duration: 1.48 },
    { name: 'render', until: 5.0, fromPct: 65, toPct: 85, duration: 0.96 },
    { name: 'encode', until: 5.8, fromPct: 85, toPct: 97, duration: 0.78 }
  ];

  // A cached lesson only needs a beat of "plan" before the artifact is handed over.
  const CACHED_DONE_SEC = 0.6;

  // Same slug rule as orchestrator.cache.topic_slug, so mock URLs line up with cache/artifacts/<slug>_<lang>/
  function topicSlug(topic) {
    return String(topic || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'untitled';
  }

  function completedStages(index) {
    const times = {};
    for (let i = 0; i < index; i++) times[STAGES[i].name] = STAGES[i].duration;
    return times;
  }

  function scriptedProgress(elapsedSec) {
    for (let i = 0; i < STAGES.length; i++) {
      const stage = STAGES[i];
      if (elapsedSec < stage.until) {
        const startedAt = i === 0 ? 0 : STAGES[i - 1].until;
        const span = (elapsedSec - startedAt) / (stage.until - startedAt);
        return {
          stage: stage.name,
          pct: stage.fromPct + Math.round(span * (stage.toPct - stage.fromPct)),
          stage_times: completedStages(i)
        };
      }
    }
    return { stage: 'done', pct: 100, stage_times: completedStages(STAGES.length) };
  }

  function progressFor(job, elapsedSec) {
    if (!job.cached) return scriptedProgress(elapsedSec);
    return elapsedSec >= CACHED_DONE_SEC
      ? { stage: 'done', pct: 100, stage_times: { plan: 0.01 } }
      : { stage: 'plan', pct: 55, stage_times: {} };
  }

  function json(body, status = 200) {
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  async function artifactExists(base) {
    try {
      const res = await originalFetch.call(root, base + '/manifest.json', { method: 'HEAD' });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  async function checkFileExists(urlPath) {
    try {
      const res = await originalFetch.call(root, urlPath, { method: 'HEAD' });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  // Convert a LessonPlan schema into a player timing manifest
  function planToManifest(plan, lang) {
    let t = 0;
    const scenes = (plan.scenes || []).map((s, idx) => {
      const words = (s.narration || '').trim().split(/\s+/).filter(Boolean).length;
      const dur = Math.max(4.0, Math.min(25.0, Math.round((words / 2.3 + 0.35) * 100) / 100));
      const start = Math.round(t * 100) / 100;
      t += dur;
      const end = Math.round(t * 100) / 100;
      return {
        id: s.id || (idx + 1),
        start_sec: start,
        end_sec: end,
        duration_sec: dur,
        narration: s.narration || '',
        visual: s.visual || { type: 'bullets', params: { labels: ['Summary'], steps: [] } }
      };
    });
    return {
      title: plan.title || 'Educational Lesson',
      lang: lang || 'en',
      total_sec: Math.round(t * 100) / 100,
      audio: null,
      sample_rate: 24000,
      scenes: scenes
    };
  }

  // Safe pedagogical fallback matching orchestrator.fallbacks.build_safe_fallback_lesson
  function buildTopicFallbackManifest(topic, lang) {
    const rawWords = String(topic || '').trim().split(/\s+/).slice(0, 4);
    const c = rawWords.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ') || 'This Topic';
    const title = `Understanding ${c}: Core Principles & Application`;
    const scenes = [
      {
        id: 1,
        narration: `Have you ever wondered how ${c} works in everyday real-world systems and why researchers and educators study it closely?`,
        visual: { type: 'title', params: { labels: [c, 'Core Concept & Intuition', 'Step-by-Step Overview'], steps: [`Mastering ${c} in One Minute`] } }
      },
      {
        id: 2,
        narration: `Think of ${c} like organizing traffic through a systematic intersection: clear principles transform complex inputs into smooth, predictable outcomes.`,
        visual: { type: 'compare', params: { labels: [`Without ${c}`, `With ${c}`], steps: ['Unstructured & inefficient process', 'Systematic & predictable result'] } }
      },
      {
        id: 3,
        narration: `At its core, ${c} operates through three connected stages: receiving the initial input state, applying the governing transformation, and producing the verified outcome.`,
        visual: { type: 'flow', params: { labels: ['1. Initial State', `2. Governing ${c} Rule`, '3. Verified Result'], steps: ['Deterministic progression at each stage'] } }
      },
      {
        id: 4,
        narration: `In a practical example of ${c}, when we observe how components interact under varying conditions, the overall system response follows direct physical balance.`,
        visual: { type: 'labeled_diagram', params: { labels: [`${c} System`, 'Primary Input', 'Control Mechanism', 'Observed Output'], steps: ['Step 1: Measure input parameters', 'Step 2: Observe system adaptation'] } }
      },
      {
        id: 5,
        narration: `To recap ${c}: remember the core intuition, trace how inputs lead to outputs, and apply this mental model when analyzing real-world observations.`,
        visual: { type: 'bullets', params: { labels: [`Key Takeaways: ${c}`], steps: ['Understand the foundational intuition', 'Follow the three-stage progression model', 'Verify outcomes through concrete observation'] } }
      }
    ];
    return planToManifest({ title, scenes }, lang);
  }

  function statusPayload(job, elapsedSec) {
    const { stage, pct, stage_times } = progressFor(job, elapsedSec);
    const done = stage === 'done';
    const fixtureLang = FIXTURE_LANGS.includes(job.lang) ? job.lang : 'en';

    return {
      job_id: job.jobId,
      topic: job.topic,
      lang: job.lang,
      stage,
      pct,
      stage_times,
      telemetry: {
        model: 'qwen2.5:3b',
        tokens: 576,
        num_scenes: (job.manifest && job.manifest.scenes) ? job.manifest.scenes.length : 5,
        fallback_used: Boolean(job.fallback_used),
        device: 'cuda'
      },
      error: null,
      cached: Boolean(job.cached),
      // Deliver topic-accurate manifest directly when available
      manifest: done ? (job.cached ? null : (job.manifest || null)) : null,
      // A cached lesson keeps its manifest, narration and MP4 side by side in cache/artifacts.
      manifest_url: done
        ? (job.cached ? job.base + '/manifest.json' : `/fixtures/golden_manifest_${fixtureLang}.json`)
        : null,
      audio_url: done && job.cached ? job.base + '/lesson_audio.wav' : null,
      // Never advertise an MP4 the server cannot deliver: the download button would 404.
      mp4_url: done && job.cached ? job.base + '/lesson.mp4' : null
    };
  }

  async function createJob(body) {
    const topic = (body.topic || "Ohm's Law").trim();
    const lang = body.lang || 'en';
    const slug = topicSlug(topic);
    const base = '/artifacts/' + slug + '_' + lang;

    // The job and its clock exist before the cache probe, so the probe latency is not demo time.
    const job = {
      jobId: 'mock_job_' + (++jobCounter),
      topic,
      lang,
      slug,
      base,
      startTime: Date.now()
    };
    job.cached = await artifactExists(base);

    // If uncached, resolve topic-accurate plan or pedagogical fallback
    if (!job.cached) {
      const planUrl = '/cache/plans/' + slug + '.json';
      const cachedPlan = await checkFileExists(planUrl);
      if (cachedPlan) {
        try {
          const res = await originalFetch.call(root, planUrl);
          if (res.ok) {
            const planData = await res.json();
            job.manifest = planToManifest(planData, lang);
          }
        } catch (e) {}
      }
      if (!job.manifest) {
        if (slug !== 'ohm-s-law' && slug !== 'ohms-law') {
          job.manifest = buildTopicFallbackManifest(topic, lang);
          job.fallback_used = true;
        }
      }
    }

    mockJobs.set(job.jobId, job);
    return job;
  }

  function installMockInterceptor() {
    originalFetch = root.fetch;

    root.fetch = async function (resource, options = {}) {
      const urlStr = typeof resource === 'string' ? resource : resource.url;
      const url = new URL(urlStr, root.location.origin);
      const method = (options.method || 'GET').toUpperCase();

      if (url.pathname === '/api/languages') return json(['en', 'hi', 'kn']);
      if (url.pathname === '/api/examples') return json(EXAMPLES);

      if (url.pathname === '/api/health') {
        return json({
          ollama: true,
          ffmpeg: true,
          chromium: true,
          models_loaded: true,
          offline_flags: true
        });
      }

      if (url.pathname === '/api/generate' && method === 'POST') {
        let body = {};
        try {
          body = typeof options.body === 'string' ? JSON.parse(options.body) : {};
        } catch (e) {
          body = {};
        }
        const job = await createJob(body);
        return json({ job_id: job.jobId });
      }

      if (url.pathname.startsWith('/api/status/')) {
        const jobId = url.pathname.replace('/api/status/', '');
        const job = mockJobs.get(jobId);
        if (!job) return json({ error: 'Job not found' }, 404);

        const elapsedSec = (Date.now() - job.startTime) / 1000;
        return json(statusPayload(job, elapsedSec));
      }

      // Everything that is not one of the mock endpoints is a real request (fixtures, fonts, media).
      return originalFetch.apply(this, arguments);
    };

    console.log('[Mock API] Offline Mock Interceptor active (?mock=1)');
  }

  root.MockAPI = {
    isMock: isMockParam,
    install: installMockInterceptor,
    topics: EXAMPLES,
    topicSlug,
    planToManifest,
    buildTopicFallbackManifest
  };

  if (isMockParam) {
    installMockInterceptor();
  }
})(typeof window !== 'undefined' ? window : globalThis);
