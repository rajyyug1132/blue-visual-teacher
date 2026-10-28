// tests/test_mock_api.js — characterization tests for web/mock.js (?mock=1 offline API).
//
// The mock drives the judge-facing demo: the stepper, the progress bar and which lesson is played.
// These tests pin its exact timeline and URL choices so the code inside can be reorganised without
// changing what the browser sees. Run with: node tests/test_mock_api.js

const path = require('path');
const assert = require('assert');

const MOCK_PATH = path.join(__dirname, '..', 'web', 'mock.js');
let passed = 0;

// Load a fresh copy of mock.js over a stubbed environment: deterministic clock, no network.
function loadMock({ artifactStatus = 404 } = {}) {
  let now = 1_000_000;
  const realNow = Date.now;
  Date.now = () => now;
  globalThis.location = { search: '?mock=1', origin: 'http://127.0.0.1:3000' };
  globalThis.fetch = async () => new Response('probe', { status: artifactStatus });
  delete require.cache[require.resolve(MOCK_PATH)];
  require(MOCK_PATH);
  const fetchMock = globalThis.fetch;
  return {
    fetchMock,
    at: (ms) => { now = 1_000_000 + ms; },
    restore: () => { Date.now = realNow; },
  };
}

async function startJob(fetchMock, body = {}) {
  const res = await fetchMock('/api/generate', { method: 'POST', body: JSON.stringify(body) });
  const { job_id } = await res.json();
  return job_id;
}

async function statusAt(fetchMock, jobId, ms, env) {
  env.at(ms);
  const res = await fetchMock('/api/status/' + jobId);
  return res.json();
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
  console.log('web/mock.js timeline');

  await test('an uncached lesson walks plan -> translate -> tts -> render -> encode -> done', async () => {
    const env = loadMock({ artifactStatus: 404 });
    try {
      const jobId = await startJob(env.fetchMock, { topic: "Ohm's Law", lang: 'en' });
      const expected = [
        [0, 'plan', 0, {}],
        [500, 'plan', 8, {}],
        [1199, 'plan', 20, {}],
        [1200, 'translate', 20, { plan: 1.18 }],
        [2499, 'translate', 40, { plan: 1.18 }],
        [2500, 'tts', 40, { plan: 1.18, translate: 1.24 }],
        [3999, 'tts', 65, { plan: 1.18, translate: 1.24 }],
        [4000, 'render', 65, { plan: 1.18, translate: 1.24, tts: 1.48 }],
        [4999, 'render', 85, { plan: 1.18, translate: 1.24, tts: 1.48 }],
        [5000, 'encode', 85, { plan: 1.18, translate: 1.24, tts: 1.48, render: 0.96 }],
        [5799, 'encode', 97, { plan: 1.18, translate: 1.24, tts: 1.48, render: 0.96 }],
        [5800, 'done', 100, { plan: 1.18, translate: 1.24, tts: 1.48, render: 0.96, encode: 0.78 }],
        [6000, 'done', 100, { plan: 1.18, translate: 1.24, tts: 1.48, render: 0.96, encode: 0.78 }],
      ];
      for (const [ms, stage, pct, times] of expected) {
        const status = await statusAt(env.fetchMock, jobId, ms, env);
        assert.strictEqual(status.stage, stage, `stage at ${ms}ms`);
        assert.strictEqual(status.pct, pct, `pct at ${ms}ms`);
        assert.deepStrictEqual(status.stage_times, times, `stage_times at ${ms}ms`);
      }
    } finally {
      env.restore();
    }
  });

  await test('a finished uncached lesson points at a locale fixture and offers no MP4', async () => {
    const env = loadMock({ artifactStatus: 404 });
    try {
      const cases = [
        ['en', '/fixtures/golden_manifest_en.json'],
        ['hi', '/fixtures/golden_manifest_hi.json'],
        ['kn', '/fixtures/golden_manifest_kn.json'],
        ['ta', '/fixtures/golden_manifest_en.json'],
      ];
      for (const [lang, manifest] of cases) {
        env.at(0);
        const jobId = await startJob(env.fetchMock, { topic: 'Water Cycle', lang });
        const status = await statusAt(env.fetchMock, jobId, 6000, env);
        assert.strictEqual(status.manifest_url, manifest, `manifest for ${lang}`);
        assert.strictEqual(status.mp4_url, null, `mp4 for ${lang}`);
        assert.strictEqual(status.audio_url, null, `audio for ${lang}`);
        assert.strictEqual(status.cached, false, `cached flag for ${lang}`);
      }
    } finally {
      env.restore();
    }
  });

  await test('a cached lesson is reported done with its own manifest, audio and MP4', async () => {
    const env = loadMock({ artifactStatus: 200 });
    try {
      const jobId = await startJob(env.fetchMock, { topic: "Ohm's Law", lang: 'hi' });
      const early = await statusAt(env.fetchMock, jobId, 300, env);
      assert.strictEqual(early.stage, 'plan');
      assert.strictEqual(early.pct, 55);
      assert.strictEqual(early.manifest_url, null);

      const done = await statusAt(env.fetchMock, jobId, 600, env);
      const base = '/artifacts/ohm-s-law_hi';
      assert.strictEqual(done.stage, 'done');
      assert.strictEqual(done.pct, 100);
      assert.deepStrictEqual(done.stage_times, { plan: 0.01 });
      assert.strictEqual(done.cached, true);
      assert.strictEqual(done.manifest_url, base + '/manifest.json');
      assert.strictEqual(done.audio_url, base + '/lesson_audio.wav');
      assert.strictEqual(done.mp4_url, base + '/lesson.mp4');
    } finally {
      env.restore();
    }
  });

  await test('the topic is slugged the same way as orchestrator.cache.topic_slug', async () => {
    const env = loadMock({ artifactStatus: 200 });
    try {
      const jobId = await startJob(env.fetchMock, { topic: "  Newton's Third Law!  ", lang: 'kn' });
      const done = await statusAt(env.fetchMock, jobId, 600, env);
      assert.strictEqual(done.manifest_url, '/artifacts/newton-s-third-law_kn/manifest.json');
    } finally {
      env.restore();
    }
  });

  await test('language list and example topics are served for the UI chrome', async () => {
    const env = loadMock();
    try {
      const langs = await (await env.fetchMock('/api/languages')).json();
      assert.deepStrictEqual(langs, ['en', 'hi', 'kn']);
      const examples = await (await env.fetchMock('/api/examples')).json();
      assert.strictEqual(examples.length, 10);
      assert.strictEqual(examples[0], "Ohm's Law");
    } finally {
      env.restore();
    }
  });

  console.log(`\n${passed} checks passed${process.exitCode ? ' (with failures)' : ''}`);
})();
