// web/app.js — Blue Visual Teacher Frontend Logic (FARHAN_BLUEPRINT.md §7)
// Pure vanilla JS, offline-first, WCAG compliant, zero external CDNs or network calls.

(function () {
  'use strict';

  // DOM Elements
  const topicInput = document.getElementById('topic-input');
  const generateBtn = document.getElementById('generate-btn');
  const validationMsg = document.getElementById('validation-msg');
  const langChipsContainer = document.getElementById('lang-chips');
  const exampleChips = document.querySelectorAll('.example-chip');
  const progressCard = document.getElementById('progress-card');
  const progressBar = document.getElementById('progress-bar');
  const playPauseBtn = document.getElementById('play-pause-btn');
  const playBtnIcon = document.getElementById('play-btn-icon');
  const playBtnText = document.getElementById('play-btn-text');
  const scrubber = document.getElementById('lesson-scrubber');
  const timeDisplay = document.getElementById('time-display');
  const captionsBtn = document.getElementById('captions-btn');
  const muteBtn = document.getElementById('mute-btn');
  const downloadMp4Btn = document.getElementById('download-mp4-btn');
  const copyPlanBtn = document.getElementById('copy-plan-btn');
  const toggleTimingsBtn = document.getElementById('toggle-timings-btn');
  const timingsDrawer = document.getElementById('timings-drawer');
  const errorToast = document.getElementById('error-toast');
  const toastMessage = document.getElementById('toast-message');
  const toastRetryBtn = document.getElementById('toast-retry-btn');
  const audio = document.getElementById('audio-player');
  const offlineBadge = document.getElementById('offline-badge');
  const offlineText = document.getElementById('offline-text');

  // State
  let currentLang = 'en';
  let currentManifest = null;
  let isGenerating = false;
  let isPlaying = false;
  let playStartTime = null;
  let pauseOffset = 0;
  let animId = null;
  let captionsEnabled = true;
  let activeJobId = null;
  let pollTimer = null;
  let lastTopic = "Ohm's Law";

  // Stage mapping
  const STAGE_ORDER = ['plan', 'translate', 'tts', 'render', 'encode'];

  // 1. Initialize
  async function init() {
    setupOfflineBadge();
    loadStoredPreferences();
    setupEventListeners();
    // Captions start enabled and are drawn from the first frame: reflect that in the button
    captionsBtn.classList.toggle('active', captionsEnabled);
    captionsBtn.setAttribute('aria-pressed', String(captionsEnabled));
    await fetchAvailableLanguages();

    // If loaded with ?mock=1 or default, automatically warm up with golden manifest
    if (window.location.search.includes('mock=1') || window.location.search.includes('load=1')) {
      loadDefaultLesson();
    }
  }

  // Live offline indicator
  function setupOfflineBadge() {
    function updateOnlineStatus() {
      if (navigator.onLine === false) {
        offlineText.textContent = 'Running fully offline';
        offlineBadge.style.color = 'var(--good)';
      } else {
        offlineText.textContent = 'Offline Engine Ready';
      }
    }
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();
  }

  // Load and save localStorage safely wrapped in try/catch
  function loadStoredPreferences() {
    try {
      const storedTopic = localStorage.getItem('bvt_last_topic');
      const storedLang = localStorage.getItem('bvt_last_lang');
      if (storedTopic) topicInput.value = storedTopic;
      if (storedLang) setLanguage(storedLang);
    } catch (e) {
      console.warn('[Storage] localStorage not accessible:', e);
    }
  }

  function savePreferences(topic, lang) {
    try {
      localStorage.setItem('bvt_last_topic', topic);
      localStorage.setItem('bvt_last_lang', lang);
    } catch (e) {
      console.warn('[Storage] Failed to save localStorage:', e);
    }
  }

  // Fetch available languages from backend
  async function fetchAvailableLanguages() {
    try {
      const res = await fetch('/api/languages');
      if (res.ok) {
        const langs = await res.json();
        const chips = langChipsContainer.querySelectorAll('.chip-btn');
        chips.forEach(chip => {
          const l = chip.getAttribute('data-lang');
          if (langs.includes(l)) {
            chip.style.display = 'inline-block';
          } else {
            chip.style.display = 'none';
          }
        });
      }
    } catch (err) {
      console.warn('[API] /api/languages unreachable:', err);
    }
  }

  // Set active language
  function setLanguage(lang) {
    currentLang = lang;
    const chips = langChipsContainer.querySelectorAll('.chip-btn');
    chips.forEach(chip => {
      const active = chip.getAttribute('data-lang') === lang;
      chip.classList.toggle('active', active);
      chip.setAttribute('aria-checked', active ? 'true' : 'false');
    });
  }

  // 2. Event Listeners
  function setupEventListeners() {
    // Generate Button & Enter Key
    generateBtn.addEventListener('click', handleGenerate);
    topicInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleGenerate();
      }
    });

    // Spacebar to Play/Pause (only when focus is not on a control that handles Space itself,
    // otherwise the button's own click and this toggle both fire)
    window.addEventListener('keydown', (e) => {
      const tag = document.activeElement && document.activeElement.tagName;
      const isControl = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || tag === 'BUTTON' || tag === 'A';
      if (e.code === 'Space' && !isControl) {
        e.preventDefault();
        togglePlayPause();
      }
    });

    // Language chips
    langChipsContainer.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip-btn');
      if (chip) {
        const selectedLang = chip.getAttribute('data-lang');
        if (selectedLang !== currentLang) {
          setLanguage(selectedLang);
          if (currentManifest && topicInput.value.trim()) {
            handleGenerate(); // re-generate with cached plan
          }
        }
      }
    });

    // Example topics
    exampleChips.forEach(chip => {
      chip.addEventListener('click', () => {
        topicInput.value = chip.textContent.trim();
        validationMsg.style.display = 'none';
        handleGenerate();
      });
    });

    // Player Controls
    playPauseBtn.addEventListener('click', togglePlayPause);
    scrubber.addEventListener('input', handleScrub);

    captionsBtn.addEventListener('click', () => {
      captionsEnabled = !captionsEnabled;
      captionsBtn.classList.toggle('active', captionsEnabled);
      captionsBtn.setAttribute('aria-pressed', String(captionsEnabled));
      // Re-render current frame with updated caption flag
      const t = parseFloat(scrubber.value || 0);
      window.renderAtTime(t);
    });

    muteBtn.addEventListener('click', () => {
      if (!audio) return;
      audio.muted = !audio.muted;
      // Keep the icon element: writing textContent here would delete the span the markup provides.
      const icon = document.getElementById('mute-icon');
      if (icon) icon.textContent = audio.muted ? '🔇' : '🔊';
      muteBtn.setAttribute('aria-pressed', String(audio.muted));
    });

    // Action buttons
    copyPlanBtn.addEventListener('click', () => {
      if (!currentManifest) return;
      navigator.clipboard.writeText(JSON.stringify(currentManifest, null, 2)).then(() => {
        const originalText = copyPlanBtn.textContent;
        copyPlanBtn.textContent = '✓ Copied!';
        setTimeout(() => { copyPlanBtn.textContent = originalText; }, 2000);
      });
    });

    toggleTimingsBtn.addEventListener('click', () => {
      timingsDrawer.classList.toggle('open');
      const isOpen = timingsDrawer.classList.contains('open');
      toggleTimingsBtn.textContent = isOpen ? '⏱ Hide Timings & Telemetry' : '⏱ Show Timings & Telemetry';
    });

    toastRetryBtn.addEventListener('click', () => {
      hideToast();
      handleGenerate();
    });
  }

  // 3. Validation & Generation Flow
  function validateInput(topic) {
    if (!topic || topic.length < 2 || topic.length > 120) {
      validationMsg.style.display = 'block';
      topicInput.setAttribute('aria-invalid', 'true');
      return false;
    }
    validationMsg.style.display = 'none';
    topicInput.removeAttribute('aria-invalid');
    return true;
  }

  async function handleGenerate() {
    const topic = topicInput.value.trim();
    if (!validateInput(topic)) return;

    hideToast();
    lastTopic = topic;
    savePreferences(topic, currentLang);

    // Reset UI state
    isGenerating = true;
    generateBtn.disabled = true;
    progressCard.style.display = 'flex';
    resetStepper();
    pausePlayback();
    setDownloadLink(null);

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, lang: currentLang })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      activeJobId = data.job_id;
      startPolling(activeJobId);
    } catch (err) {
      console.error('[Generation] Request failed:', err);
      showToast('Server not reachable, is run_demo running? You can also test with ?mock=1.');
      isGenerating = false;
      generateBtn.disabled = false;
      progressCard.style.display = 'none';
    }
  }

  // 4. Polling Job Status every 400ms
  function startPolling(jobId) {
    if (pollTimer) clearInterval(pollTimer);

    pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/status/${jobId}`);
        if (!res.ok) {
          throw new Error(`Status check HTTP ${res.status}`);
        }
        const status = await res.json();
        updateProgress(status);

        if (status.stage === 'done') {
          clearInterval(pollTimer);
          await finishGeneration(status);
        } else if (status.stage === 'error' || status.error) {
          clearInterval(pollTimer);
          throw new Error(status.error || 'Generation encountered an error');
        }
      } catch (err) {
        clearInterval(pollTimer);
        console.error('[Polling] Error:', err);
        showToast('Generation halted: ' + (err.message || 'Server connection lost'));
        isGenerating = false;
        generateBtn.disabled = false;
      }
    }, 400);
  }

  function updateProgress(status) {
    const { stage, pct, stage_times } = status;

    // Update progress bar
    progressBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;

    // Update stepper
    const currentIdx = STAGE_ORDER.indexOf(stage);
    STAGE_ORDER.forEach((s, idx) => {
      const el = document.getElementById(`step-${s}`);
      const timeEl = document.getElementById(`time-${s}`);
      if (!el) return;

      if (idx < currentIdx || stage === 'done') {
        el.className = 'step-item done';
        if (stage_times && stage_times[s]) {
          timeEl.textContent = `${stage_times[s].toFixed(1)}s`;
        }
      } else if (idx === currentIdx) {
        el.className = 'step-item active';
        timeEl.textContent = '...';
      } else {
        el.className = 'step-item';
        timeEl.textContent = '';
      }
    });

    // Populate telemetry
    if (status.telemetry) {
      updateTelemetry(status.telemetry, stage_times);
    }
  }

  function updateTelemetry(tel, stage_times) {
    if (stage_times) {
      if (stage_times.plan) document.getElementById('telemetry-plan').textContent = `${stage_times.plan.toFixed(2)}s`;
      if (stage_times.translate) document.getElementById('telemetry-translate').textContent = `${stage_times.translate.toFixed(2)}s`;
      if (stage_times.tts) document.getElementById('telemetry-tts').textContent = `${stage_times.tts.toFixed(2)}s`;
      if (stage_times.render) document.getElementById('telemetry-render').textContent = `${stage_times.render.toFixed(2)}s`;
      if (stage_times.encode) document.getElementById('telemetry-encode').textContent = `${stage_times.encode.toFixed(2)}s`;
    }
    if (tel) {
      if (tel.model) document.getElementById('telemetry-model').textContent = tel.model;
      if (tel.tokens) document.getElementById('telemetry-tokens').textContent = tel.tokens;
      if (typeof tel.fallback_used !== 'undefined') {
        document.getElementById('telemetry-fallback').textContent = tel.fallback_used ? 'True' : 'False';
      }
    }
  }

  function resetStepper() {
    STAGE_ORDER.forEach(s => {
      const el = document.getElementById(`step-${s}`);
      const timeEl = document.getElementById(`time-${s}`);
      if (el) el.className = 'step-item';
      if (timeEl) timeEl.textContent = '';
    });
    progressBar.style.width = '0%';
  }

  // 5. Completion and Player Wiring
  async function finishGeneration(status) {
    isGenerating = false;
    generateBtn.disabled = false;

    try {
      const manifestUrl = status.manifest_url || '/fixtures/golden_manifest_en.json';
      const res = await fetch(manifestUrl);
      currentManifest = await res.json();

      // Initialize the in-app player directly using engine.js
      await window.initLesson(currentManifest.title, currentManifest.scenes, currentManifest.lang || currentLang);

      // Setup audio clock. A manifest can name a narration file that was never rendered, so confirm
      // it is really served before wiring it up: otherwise the element 404s and the previous
      // lesson's audio can linger behind the new one.
      if (audio) {
        let audioSrc = status.audio_url || null;
        if (!audioSrc && currentManifest.audio) {
          audioSrc = manifestUrl.substring(0, manifestUrl.lastIndexOf('/') + 1) + currentManifest.audio;
        }
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
        if (audioSrc) {
          try {
            const head = await fetch(audioSrc, { method: 'HEAD' });
            if (head.ok) {
              audio.src = audioSrc;
              audio.load();
            }
          } catch (e) {
            console.warn('[Playback] Narration audio unavailable, playing silent:', audioSrc);
          }
        }
      }

      // Configure scrubber
      scrubber.max = window.totalDuration;
      scrubber.value = 0;
      updateTimeDisplay(0, window.totalDuration);

      // Enable MP4 download only when the file really exists (an advertised URL can 404)
      await setDownloadLink(status.mp4_url);

      // Render initial frame
      window.renderAtTime(0);

      // Autoplay
      startPlayback();
    } catch (err) {
      console.error('[Playback] Failed to initialize lesson:', err);
      showToast('Generated, but lesson manifest failed to load.');
    }
  }

  // Enable/disable the MP4 download button after confirming the file is really served
  async function setDownloadLink(url) {
    const apply = (usable) => {
      downloadMp4Btn.href = usable ? url : '#';
      downloadMp4Btn.style.pointerEvents = usable ? 'auto' : 'none';
      downloadMp4Btn.style.opacity = usable ? '1' : '0.6';
      downloadMp4Btn.title = usable ? 'Download the rendered MP4' : 'No MP4 has been rendered for this lesson yet';
    };
    if (!url) {
      apply(false);
      return;
    }
    try {
      const head = await fetch(url, { method: 'HEAD' });
      apply(head.ok);
    } catch (e) {
      apply(false);
    }
  }

  // Load default Ohm's law lesson on boot
  async function loadDefaultLesson() {
    try {
      const res = await fetch('/fixtures/golden_manifest_en.json');
      currentManifest = await res.json();
      await window.initLesson(currentManifest.title, currentManifest.scenes, currentManifest.lang || 'en');
      scrubber.max = window.totalDuration;
      scrubber.value = 0;
      updateTimeDisplay(0, window.totalDuration);
      window.renderAtTime(0);
    } catch (e) {
      console.warn('[Init] Golden lesson fallback notice:', e);
    }
  }

  // 6. Playback and Scrubber Logic
  function togglePlayPause() {
    if (isPlaying) {
      pausePlayback();
    } else {
      startPlayback();
    }
  }

  function startPlayback() {
    if (parseFloat(scrubber.value) >= window.totalDuration) {
      pauseOffset = 0;
      scrubber.value = 0;
    } else {
      pauseOffset = parseFloat(scrubber.value || 0);
    }

    isPlaying = true;
    playBtnIcon.textContent = '⏸';
    playBtnText.textContent = 'Pause';
    playStartTime = null;

    if (audio && audio.src && !audio.ended) {
      audio.currentTime = pauseOffset;
      audio.play().catch(() => {});
    }

    animId = requestAnimationFrame(animationLoop);
  }

  function pausePlayback() {
    isPlaying = false;
    playBtnIcon.textContent = '▶';
    playBtnText.textContent = 'Play';
    if (animId) cancelAnimationFrame(animId);
    if (audio) audio.pause();
    pauseOffset = parseFloat(scrubber.value || 0);
  }

  function animationLoop(now) {
    if (!playStartTime) playStartTime = now - (pauseOffset * 1000);
    const elapsed = (now - playStartTime) / 1000;

    if (elapsed <= window.totalDuration) {
      window.renderAtTime(elapsed);
      scrubber.value = elapsed;
      updateTimeDisplay(elapsed, window.totalDuration);
      animId = requestAnimationFrame(animationLoop);
    } else {
      window.renderAtTime(window.totalDuration);
      scrubber.value = window.totalDuration;
      updateTimeDisplay(window.totalDuration, window.totalDuration);
      pausePlayback();
    }
  }

  function handleScrub(e) {
    const t = parseFloat(e.target.value);
    window.renderAtTime(t);
    updateTimeDisplay(t, window.totalDuration);
    if (isPlaying) {
      pauseOffset = t;
      playStartTime = performance.now() - (t * 1000);
      if (audio && audio.src) audio.currentTime = t;
    } else {
      pauseOffset = t;
    }
  }

  function updateTimeDisplay(current, total) {
    timeDisplay.textContent = `${current.toFixed(2)}s / ${(total || 54.79).toFixed(2)}s`;
  }

  // 7. Error Toast Helpers
  function showToast(message) {
    toastMessage.textContent = message;
    errorToast.classList.add('show');
  }

  function hideToast() {
    errorToast.classList.remove('show');
  }

  // Auto-init on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
