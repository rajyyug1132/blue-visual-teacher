# LEARNINGS.md

Things that cost time once. Read before each pass of the DONE loop; add a line when something surprises you.

- Ollama `keep_alive` must be the number -1; the string "-1" returns HTTP 400 ("missing unit in duration").
- A different `num_ctx` between calls makes Ollama reload the model; every planner call uses NUM_CTX=4096.
- qwen2.5:7b on the RTX 3050 runs 18% on CPU: P50 42 s per plan. Use it only as the escalation rung.
- Small models copy any sample words in a retry message verbatim ("heavy rain of water"). Retry messages say only
  what to remove and where.
- The Ollama grammar enforces the schema's maxLength, so an overlong narration arrives cut mid-word; trim it at a
  clause break instead of retrying.
- Python's `\d` does not match "²" or "₂"; NFKC turns them into plain digits, so superscript powers must be handled
  before NFKC ("6²" would become "62").
- The project `.venv` was rebuilt on Python 3.11 without the test deps; tests here run from a scratch venv
  (Python 3.13 with system site-packages + ollama). Don't overwrite the shared `.venv`.
- `ls ~/.cache/huggingface/hub` showing a model folder is not proof the weights are there: IndicTrans2 was 4.8 MB
  (config and tokenizer only). Check sizes.
- D1 counts are the CC-1 ones, [22,27,24,29,21] (scene 4 spelled out in words), agreed by YYUG on 2026-10-27.
- D2 run 1 (ladder, 2026-10-27 14:30): 19/20 valid, P50 39.1 s, P90 113.6 s. 12/20 topics needed more than one rung;
  8 first-attempt failures were numbers in descriptive narration. Each costs a full re-plan (~850 tokens) and often
  a 7b escalation (~45 s). Next lever: patch only the offending field with a short call instead of re-planning.
  3b classified Pythagoras and Acid-Base Titration as descriptive (lost their worked examples): add a keyword prior.
  Timings were inflated by a concurrent pip install (classify 7-33 s on some topics); re-measure on a quiet machine.
- Runtime is Python 3.11 (scratch venv `rt`): spaCy (Kokoro -> misaki -> spaCy) has no Windows wheels for 3.13.
- IndicTrans2 custom code needs transformers 4.46.3; on 4.5x generate() dies with
  "'NoneType' object has no attribute 'shape'" (past_key_values cache API change).
- IndicTransToolkit 1.1.1 is Cython and needs MSVC; there is no C compiler here. A typed-stripped pure-Python copy of
  processor.pyx works (script: scratchpad depyx.py). Each postprocess_batch must follow its own preprocess_batch
  (shared queue), or it blocks forever.
- Hugging Face cache symlinks fail on Windows without Developer Mode (WinError 1314); download to a staging dir and
  copy into hub/models--org--name/snapshots/<sha>/ with refs/main = <sha>.
- Kokoro Hindi works with the espeak-ng bundled by espeakng_loader; no system espeak-ng install is needed. Checking
  only `shutil.which("espeak-ng")` wrongly disables Hindi.
- Without Kokoro-HI or MMS-HI, OfflineTTSEngine silently returns a sine tone for Hindi; available_languages() must
  hide such languages.
- FFmpeg from MJPEG frames gives yuvj420p even with -pix_fmt yuv420p; convert with
  `scale=in_range=pc:out_range=tv,format=yuv420p`.
- Golden 55.2 s lesson exports in 11.2 s with toDataURL capture (target < 60 s).
- IndicTrans2 via Tarun's translator: one 32-string batch for the whole lesson plus about 8 one- or two-string
  repair calls for protected spans.
- v1 merge (2026-10-27): the full suite with Tarun's new tests takes 15-30 min. One full run had 5 extra TTS
  failures that passed alone: the Kokoro-Hindi mock test in test_localization_l1_to_l8.py leaked a patched
  np/KPipeline into later tests (fixed in 090a08b with patch.object), plus an int() vs round() sample-count bug.
  Order-dependent failures -> look for module-level mocks first. RAM is also tight (~2 GB free of 16 GB).
- Tarun's run_pipeline.py uses the BLUEPRINT 5.1 exporter call shape; it now goes through
  exporter.export_mp4.export_from_manifest, which keeps the existing manifest fields (lang, sample_rate).
