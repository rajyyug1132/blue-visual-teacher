# DONE checks · 2026-10-27 16:46

| D# | check | state | owner | detail | evidence |
|---|---|---|---|---|---|
| D1 | schema + golden fixture | PASS | YYUG | words [22, 27, 24, 29, 21] | logs/D1.log |
| D2 | planner ladder, 20 topics | PASS | YYUG | valid 19/20, P50 15.6s, final failures 0, unspoken answers 0 | logs/D2.log |
| D3 | plan + artifact cache | FAIL | YYUG | 1 failed, 1 passed, 169 deselected, 3 warnings in 8.81s | logs/D3.log |
| D4 | IndicTrans2 + IndicProcessor | BLOCKED | TARUN | translation tests all skipped: 2 skipped, 169 deselected, 1 warning in 6.28s | logs/D4.log |
| D5 | TTS 24 kHz, deterministic | PASS | TARUN | 3 passed, 168 deselected, 6 warnings in 35.11s | logs/D5.log |
| D6 | renderer 8 templates | PASS | FARHAN | 1 passed, 6 skipped, 164 deselected, 1 warning in 7.58s | logs/D6.log |
| D7 | export 20 topics x en/hi/kn | BLOCKED | AYUSH | export tests all skipped: 2 failed, 3 skipped, 166 deselected, 3 warnings in 8.03s | logs/D7.log |
| D8 | web UI | FAIL | AYUSH | 167 deselected, 3 warnings, 4 errors in 9.65s | logs/D8.log |
| D9 | pytest incl. offline e2e | FAIL | ALL | 3 failed, 153 passed, 11 skipped, 12 warnings, 4 errors in 59.92s | logs/D9.log |
| D10 | README, run_demo.sh, pre-cache | PASS | AYUSH | ok | logs/D10.log |
