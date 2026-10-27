// web/app.js — the page judges touch first. Vanilla JS, same-origin API only (AYUSH_BLUEPRINT 4).
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const LANG_NAMES = { en: "English", hi: "हिन्दी", kn: "ಕನ್ನಡ", ta: "தமிழ்", te: "తెలుగు" };
  const STAGES = ["plan", "translate", "tts", "render", "encode"];
  const STAGE_TEXT = { queued: "Waiting for the previous lesson to finish…", plan: "Planning the lesson", translate: "Translating",
                       tts: "Recording the voice", render: "Drawing the video", encode: "Exporting the MP4", done: "Ready" };
  const ui = { lang: "en", polling: null, last: null, playing: false };

  function store(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } }
  function recall(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }

  async function api(path, opts) {
    let res;
    try { res = await fetch(path, opts); }
    catch (e) { throw new Error("Server not reachable. Is run_demo running?"); }
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Please check the topic and try again.");
    return body;
  }

  function toast(message) {
    $("toast-text").textContent = message;
    $("toast").hidden = false;
  }

  function chip(label, checked, onClick, extra) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.textContent = label;
    if (checked !== null) { b.setAttribute("role", "radio"); b.setAttribute("aria-checked", String(checked)); }
    if (extra) { const s = document.createElement("span"); s.className = "cached"; s.textContent = extra; b.appendChild(s); }
    b.onclick = onClick;
    return b;
  }

  function renderLangs(langs) {
    const box = $("langs");
    box.innerHTML = "";
    if (!langs.includes(ui.lang)) ui.lang = langs[0] || "en";
    langs.forEach((code) => {
      const c = chip(LANG_NAMES[code] || code, code === ui.lang, () => {
        ui.lang = code; store("bvt.lang", code); renderLangs(langs);
        if (ui.last && ui.last.topic) generate(ui.last.topic);  // switching language re-uses the cached plan
      });
      c.dataset.lang = code;
      box.appendChild(c);
    });
  }

  async function loadExamples() {
    try {
      const list = await api("/api/examples");
      const box = $("examples");
      box.innerHTML = "";
      list.forEach((ex) => box.appendChild(chip(ex.topic, null, () => { $("topic").value = ex.topic; generate(ex.topic); },
                                                ex.cached.length ? "● " + ex.cached.join(" ") : "")));
    } catch (e) { /* examples are optional */ }
  }

  function setProgress(st) {
    $("progress").hidden = false;
    const idx = STAGES.indexOf(st.stage);
    document.querySelectorAll("#stepper li").forEach((li, i) => {
      const s = li.dataset.stage, secs = st.stage_times && st.stage_times[s];
      li.className = st.stage === "done" || (idx >= 0 && i < idx) ? "done" : i === idx ? "active" : "";
      li.querySelector("small")?.remove();
      if (secs != null) { const sm = document.createElement("small"); sm.textContent = secs.toFixed(1) + " s"; li.appendChild(sm); }
    });
    const overall = st.stage === "done" ? 100 : idx < 0 ? 0 : Math.round((idx * 100 + (st.pct || 0)) / STAGES.length);
    $("bar-fill").style.width = overall + "%";
    $("progress-text").textContent = (STAGE_TEXT[st.stage] || st.stage) + (st.cached ? " · cached lesson" : "") + ` · ${overall}%`;
  }

  async function generate(topicArg) {
    const topic = (topicArg || $("topic").value).trim();
    $("hint").textContent = "";
    $("toast").hidden = true;
    if (topic.length < 2) { $("hint").textContent = "Please type a topic (at least 2 characters)."; return; }
    if (topic.length > 120) { $("hint").textContent = "Please keep the topic under 120 characters."; return; }
    store("bvt.topic", topic);
    ui.last = { topic };
    $("go").disabled = true;
    clearInterval(ui.polling);
    try {
      const { job_id } = await api("/api/generate", { method: "POST", headers: { "Content-Type": "application/json" },
                                                      body: JSON.stringify({ topic, lang: ui.lang }) });
      ui.polling = setInterval(() => poll(job_id), 400);
      poll(job_id);
    } catch (e) { toast(e.message); $("go").disabled = false; }
  }

  async function poll(jobId) {
    let st;
    try { st = await api("/api/status/" + jobId); }
    catch (e) { clearInterval(ui.polling); toast(e.message); $("go").disabled = false; return; }
    setProgress(st);
    if (st.stage === "error") { clearInterval(ui.polling); toast(st.error || "Something went wrong."); $("go").disabled = false; }
    if (st.stage === "done") { clearInterval(ui.polling); $("go").disabled = false; await showLesson(st); }
  }

  async function showLesson(st) {
    const manifest = await api(st.manifest_url);
    await window.initLesson(manifest.title, manifest.scenes, manifest.lang);
    $("player").hidden = false;
    $("download").href = st.mp4_url;
    $("download").setAttribute("download", (st.topic || "lesson").replace(/\W+/g, "_") + "_" + st.lang + ".mp4");
    $("timings").textContent = JSON.stringify({ stage_times: st.stage_times, cached: st.cached, telemetry: st.telemetry }, null, 2);
    const audio = $("audio");
    audio.src = st.audio_url;
    audio.currentTime = 0;
    window.renderAtTime(0);
    audio.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
  }

  function setPlaying(on) { ui.playing = on; $("play").textContent = on ? "Pause" : "Play"; if (on) requestAnimationFrame(tick); }

  // Playback clock lives here, never inside renderAtTime: the audio drives the frame.
  function tick() {
    const audio = $("audio"), t = audio.currentTime || 0, total = window.totalDuration || 1;
    window.renderAtTime(t);
    $("scrub").value = Math.round((t / total) * 1000);
    $("time").textContent = `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
    if (ui.playing && !audio.ended) requestAnimationFrame(tick); else if (audio.ended) setPlaying(false);
  }

  function init() {
    ui.lang = recall("bvt.lang") || "en";
    $("topic").value = recall("bvt.topic") || "";
    $("go").onclick = () => generate();
    $("topic").addEventListener("keydown", (e) => { if (e.key === "Enter") generate(); });
    $("retry").onclick = () => generate(ui.last && ui.last.topic);
    $("play").onclick = () => { const a = $("audio"); if (a.paused) a.play().then(() => setPlaying(true)); else { a.pause(); setPlaying(false); } };
    $("scrub").oninput = () => { const a = $("audio"); a.currentTime = ($("scrub").value / 1000) * (window.totalDuration || 0); window.renderAtTime(a.currentTime); };
    $("timings-btn").onclick = () => { const t = $("timings"); t.hidden = !t.hidden; $("timings-btn").setAttribute("aria-expanded", String(!t.hidden)); };
    document.addEventListener("keydown", (e) => {
      if (e.code === "Space" && document.activeElement !== $("topic") && !$("player").hidden) { e.preventDefault(); $("play").click(); }
    });
    if (navigator.onLine === false) $("offline-text").textContent = "Running fully offline";
    api("/api/languages").then(renderLangs).catch((e) => { renderLangs(["en"]); toast(e.message); });
    loadExamples();
  }

  init();
})();
