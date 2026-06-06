# INDEX — Multi-Agent AutoML Team (living state)

> **The** entry point. Reading this file alone = knowing where the build stands.
> Resume command: **`read specs/automl-team/INDEX.md and continue`** (the loop prompt:
> [`../prompts/loop.md`](../prompts/loop.md); the method: [`../PROCESS.md`](../PROCESS.md)).

## Context

Assignment 2: an autonomous AI data-science team — **Cleaner → Feature Engineer → Trainer** (three
Gemini agents on one generic function-calling loop) — processes the committed IT Salary Survey EU
2020 dataset end-to-end with zero human input after launch. Every data-science decision is the
LLM's, reasoned over tool output (**`NO-HARDCODE`**); every decision lands in `events.jsonl` with
its evidence (**`SHOW-WORK`**); the Trainer runs a generate → execute → read-own-output → react
loop (the graded centerpiece). Deliverables: pipeline code, transcripts, a generated `report.md`,
and a Streamlit live/replay viewer; one exhibit run committed under `examples/`.

## Documents

- [`spec.md`](spec.md) — WHAT/WHY, acceptance criteria (**Status: Approved**)
- [`DESIGN.md`](DESIGN.md) — drawn architecture, handoff contract, Trainer loop, risks
- [`plan.md`](plan.md) — implementation insights + the work-unit decomposition
- [`../../Assignment.md`](../../Assignment.md) — the graded requirements
- [`../PRINCIPLES.md`](../PRINCIPLES.md) — the constitution (incl. graded `NO-HARDCODE` / `SHOW-WORK`)
- `units/<id>.md` — per-unit plan/test/result records (created as each unit is taken)

## Unit table

Status: `planned → implemented → verified` · or `blocked-on-user` (nag pending). A unit is done
only at `verified`. Work top-to-bottom: **the current unit is the first not-`verified` row.**

| id | Title | Done when | Graded | Status | Unit file |
|---|---|---|---|---|---|
| u01 | Project scaffold (uv `pyproject.toml`, `.gitignore`, `.env.example`, package skeleton) | `uv sync` ok; `import automl_team` ok; `runs/`/`.env` ignored | — | verified | [u01](units/u01.md) |
| u02 | Fetch + commit official dataset with fingerprint check | CSV committed; 1246×23 + known dirt markers confirmed | — | verified | [u02](units/u02.md) |
| u03 | `EventLog` (`events.jsonl` writer, 9 event types) + console renderer | pytest round-trips all event types; readable console lines | `SHOW-WORK` | verified | [u03](units/u03.md) |
| u04 | Orchestrator skeleton (run-dir, raw snapshot, stage sequencing) | dummy no-LLM run creates `runs/<ts>/` with snapshot + ordered events | — | verified | [u04](units/u04.md) |
| u05 | Gemini wiring + generic agent loop (**nag: API key**) | toy agent: call → result → `finish`, fully logged, real API | `NO-HARDCODE` `SHOW-WORK` | verified | [u05](units/u05.md) |
| u06 | Cleaner toolset (generic verbs) | pytest drives every tool on the real CSV, no LLM | `NO-HARDCODE` | verified | [u06](units/u06.md) |
| u07 | Cleaner stage green on real dataset | `01_clean_data.csv` + decisions-table report; transcript traceable | `NO-HARDCODE` `SHOW-WORK` | verified | [u07](units/u07.md) |
| u08 | Feature-Engineer toolset | pytest drives every FE tool, no LLM | `NO-HARDCODE` | verified | [u08](units/u08.md) |
| u09 | Feature-Engineer stage green | `02_engineered_data.csv` with ≥1 justified domain feature | `NO-HARDCODE` `SHOW-WORK` | verified | [u09](units/u09.md) |
| u10 | Sandboxed `execute_python_code` (120 s, verbatim capture) | pytest: ok / crash / timeout cases return verbatim output | `SHOW-WORK` | verified | [u10](units/u10.md) |
| u11 | **Trainer stage green (feedback loop — centerpiece)** | ≥2 executions, each followed by reasoning quoting the output; history ≥2 iters; min-2/max-6 enforced | `NO-HARDCODE` `SHOW-WORK` | verified | [u11](units/u11.md) |
| u12 | Report stage (one LLM call → `report.md`) | report covers raw → transformations → iteration metrics → limitations | `SHOW-WORK` | planned | — |
| u13 | One-command headless run (milestone) | `run_pipeline.py --data …` completes all stages, full artifact set | — | planned | — |
| u14 | Streamlit replay mode (no API key) | past run renders: stepper, transcript, df tabs, metrics chart, reports | `SHOW-WORK` | planned | — |
| u15 | Streamlit live mode (~2×/s tail) | a live run visibly progresses in the UI; no agent-influencing controls | — | planned | — |
| u16 | Second-CSV smoke test (stages 1–2, zero code changes) | different-schema CSV completes Cleaner + FE untouched | `NO-HARDCODE` | planned | — |
| u17 | Exhibit + hardening (**nag: human quality judgment**) | hardcode-grep clean; exhibit run committed to `examples/` + replayable; README done; human approved | `NO-HARDCODE` `SHOW-WORK` | planned | — |

## Log

- **2026-06-06** — Phase 2 complete: `plan.md` + this INDEX written from the Approved spec.
  Repo is greenfield (no product code yet). No unit started.
- **2026-06-06** — **u01 verified.** Scaffold up: `.gitignore` (`.env` was exposed — now ignored),
  `pyproject.toml` + `uv sync` green, package skeleton imports, `.env.example`. macOS prereq found:
  `brew install libomp` for xgboost (→ README in u17). A real `GEMINI_API_KEY` already sits in
  `.env` — u05 should verify it before nagging. Next: **u02** (dataset fetch + fingerprint).
- **2026-06-06** — **u02 verified.** Dataset committed (`data/IT_Salary_Survey_EU_2020.csv`,
  1246×23) + `tests/test_dataset_fingerprint.py` 6/6 green (all dirt markers confirmed). Commits
  `306c4bb` (u01) / `b77989d` (u02). Real header recorded in u02.md. Next: **u03** (EventLog).
- **2026-06-06** — **u03 verified.** `events.py` (EventLog + read_events) + `console.py` renderer;
  9 round-trip tests, suite 15-green. pytest needed `pythonpath = ["."]` in pyproject (flat
  layout). Next: **u04** (orchestrator skeleton).
- **2026-06-06** — **u04 verified.** `handoff.py` + `orchestrator.py` (run-dir, snapshot, generic
  fingerprint, stage sequencing, failure path); 4 tests, suite 19-green; real-CSV dummy run OK.
  Next: **u05** (Gemini wiring — key already present in `.env`, verify before nagging).
- **2026-06-06** — **u05 verified, no nag needed** (the `.env` key works — live-tested before
  nagging). `llm.py` + `agent.py` (generic loop, finish_guard hook, malformed-call feedback);
  SDK surface verified against installed google-genai 2.8.0; 3 tests (2 live), suite 22-green;
  live toy transcript eyeballed. Next: **u06** (Cleaner toolset, no LLM).
- **2026-06-06** — **u06 verified.** `tools/cleaner.py` (6 generic verbs), 16 real-CSV tests,
  suite 38-green. Two insights → plan.md: pandas-3 `str` dtype; flash needs an explicit per-call
  rationale demand or it skips text parts (u05 toy test was flaky — hardened, 5/5 stable). All
  stage prompts must carry the rationale clause. Next: **u07** (Cleaner stage green, real LLM).
- **2026-06-06** — **u07 verified** (2 real runs). Run 1 hit the 40-turn cap (thorough, not
  stuck) → batching clause + generic 5-turns-left warning (`agent.py`) + cap 60. Run 2 finished:
  1227×23 clean CSV, 25 KB decisions-table report, 29 mutations / 0 traceability violations
  (programmatic events.jsonl check). Transcript shows live self-correction off tool errors.
  Next: **u08** (FE toolset, no LLM).
- **2026-06-06** — **u08 verified.** `tools/base.py` extracted (shared verbs; u06 tests green
  untouched) + `tools/features.py` (6 FE verbs, numeric coercion, /0 guard). 16 real-CSV tests;
  suite 54-green. Next: **u09** (FE stage green, real LLM).
- **2026-06-06** — **u09 verified.** Full 2-stage run, zero errors: 5 agent-invented domain
  features (compensation total, raise/bonus ratios, DE-experience ratio, tech count), principled
  encodings, collinear intermediates self-removed. Traceability checker made batch-aware → 0
  violations. Next: **u10** (sandbox, no LLM).
- **2026-06-06** — **u10 verified.** `tools/sandbox.py` (venv interpreter, run-dir cwd,
  timeout→stderr, verbatim events + truncated agent view, `code_iter_n.py` artifacts); 7 tests
  green first run; suite 61-green. Next: **u11 — the Trainer centerpiece.**
- **2026-06-06** — **u11 verified — the centerpiece is green.** Found+fixed flash's
  `MALFORMED_FUNCTION_CALL` on big code args (forced calling + reserved `reasoning` arg →
  plan insight). Real run: 5 executions rc `[0,1,1,1,0]`, every reaction quotes output
  (SyntaxError/XGBoostError/R² verbatim), history 2 iters R² 0.9706→0.9800, leakage
  self-detected, guardrails pytest-proven. Suite 70-green. Next: **u12** (report stage).

## Resume here

1. Read [`plan.md`](plan.md) (insights first), then [`DESIGN.md`](DESIGN.md) + [`spec.md`](spec.md).
2. Take the first not-`verified` unit above (**currently: u01**); write `units/<id>.md`; implement;
   self-test; update this table + the log.
3. Nag (`./nag.sh`) at every human-only gate (u05 API key, u17 exhibit judgment) and when the whole
   build finishes.
