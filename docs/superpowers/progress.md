# SDD ledger — plan: docs/superpowers/plans/2026-10-24-mill-floor-copilot.md
Pre-flight: Task1 produces data.*/ml.risk consumed by Task2 (match); Task2 run() consumed by Task3 (match).
Ruling: no git repo — skip worktree, commits, task-start/task-done scripts; ledger by hand — cost if wrong: no per-task diff history.
Task 1: complete (tests: python check.py → test_ml ok)
Task 2: Ruling: regex machine fallback when Gemma extraction fails or returns unknown id — test needs evidence while Gemma is down — cost if wrong: may match a machine Gemma would not.
Task 2: complete (tests: python check.py → 5/5 ok; python check.py live → ok, 159s, repeat_pattern true, Roman Urdu reply)
Task 3: Ruling: add demo cache (last good result per note, labelled "cached") — network here resets connections, 1-call latency 18-64s — cost if wrong: judges see a cached answer, labelled honestly.
Task 3: complete (tests: AppTest headless with faked Gemma → vague note asks for machine, full run shows repeat banner + metrics, Gemma-down shows cached result; README rewritten)
Final review: fresh reviewer (opus) — 1 Critical, 3 Important, 3 Minor.
Final: Ruling: re-graded #6 (null symptom crash) and #7 (stale result on example click) Minor→Important — crash/confusion in front of judges — cost if wrong: two tiny extra fixes.
Final: fixed non-list steps/parts + null symptom — test_bad_list_fields_and_null_symptom RED→GREEN, suite 7/7
Final: fixed healthy machine blamed/logged — test_healthy_machine_not_blamed_or_logged RED→GREEN, suite 7/7
Final: Ruling: llm timeout 90→40s, 3→2 retry rounds, no test (config values) — worst-case hang ~3 min instead of ~9 — cost if wrong: a slow-but-working call fails over to cache.
Final: fixed stale result after example click — AppTest example-click check, verified
Final: minor (deferred): Urdu note + Gemma down + no cache shows "which machine?" and hides the error.
Note: HISTORY lives in memory; restart Streamlit before the demo so loom-14 shows exactly 2 past faults.
Ruling: tests are a single assert-based check.py (ponytail rule), no pytest — cost if wrong: none for a demo.
