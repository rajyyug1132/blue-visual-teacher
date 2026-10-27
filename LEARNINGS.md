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
