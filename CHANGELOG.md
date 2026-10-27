# CHANGELOG

Refactor passes over the demo-facing code. Behaviour is unchanged in every pass; each line names the
characterization test that pins it. Run them with `npm run test:units`.

- pass 1 — `server.js` — request handler split into `sendText`, `parseByteRange`, `sendFile` and `handle`; pinned by `tests/test_server_behavior.js` (12 checks).
