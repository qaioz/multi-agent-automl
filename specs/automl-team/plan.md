# Plan — Multi-Agent AutoML Team

- **Status:** Planned (no unit started)
- **Inputs:** [`spec.md`](spec.md) (Approved) · [`DESIGN.md`](DESIGN.md) · [`../../Assignment.md`](../../Assignment.md)
- **Process:** [`../PROCESS.md`](../PROCESS.md) · constitution [`../PRINCIPLES.md`](../PRINCIPLES.md)

## Implementation insights (the map)

**Repo reality (explored 2026-06-06):** greenfield. No product code, no `data/`, no `.gitignore`
(must exist *before* `.env` or the dataset land), README is empty. The only reusable assets are
`nag.sh`/`stop-nag.sh` (human gates). Nothing constrains us but the docs.

**Toolchain:** system Python is 3.9 (too old to pin against); **`uv` 0.9.15 is installed** — use a
uv-managed project: one `pyproject.toml`, `requires-python >= 3.11`, pinned deps
(`google-genai`, `pandas`, `xgboost`, `scikit-learn`, `streamlit`, `python-dotenv`), `uv.lock`
committed. Everything runs as `uv run …`. Spec's walkthrough fixes the two entrypoint names:
top-level `run_pipeline.py` and `ui.py`.

**Proposed layout** (small, flat package; entrypoints where the spec shows them):

```
run_pipeline.py            # CLI: python run_pipeline.py --data <csv>
ui.py                      # streamlit run ui.py  (live + replay)
automl_team/
  events.py                # EventLog: append-only events.jsonl writer + the 9 event types
  console.py               # console renderer of events (headless runs)
  llm.py                   # .env loading, google-genai client, GEMINI_MODEL config
  agent.py                 # the ONE generic function-calling loop (system prompt + tools + finish)
  orchestrator.py          # run-dir, raw snapshot + fingerprint, stage sequencing — no brain
  handoff.py               # Handoff = {csv_path, report_markdown}
  tools/cleaner.py         # generic verbs over the stage's working dataframe
  tools/features.py
  tools/sandbox.py         # execute_python_code: subprocess, 120 s, verbatim capture
  prompts/                 # the three agent system prompts + report prompt (plain .md/.py strings)
  report.py                # stage 4: one LLM call → report.md
data/IT_Salary_Survey_EU_2020.csv   # committed official dataset
examples/                  # the committed exhibit run
runs/                      # gitignored
```

**Load-bearing decisions** (all from spec/DESIGN — restated as build guidance):

1. **One agent loop, three configurations.** `agent.py` is a raw `google-genai` function-calling
   loop (~50 lines): history → model → (text parts ⇒ `reasoning` events; function calls ⇒ execute,
   log `tool_call`+`tool_result`, append result) → repeat until `finish(report_markdown)`. Per-agent
   turn cap (cost guardrail). Malformed/unknown calls are returned *as the tool result* so the agent
   self-corrects — same feedback principle as the Trainer. **Verify the current `google-genai`
   function-calling API against its docs while building u05 — do not code it from memory**
   (PRINCIPLES 4; SDK has changed shape before).
2. **`NO-HARDCODE` lives in the tool signatures.** Tools are generic verbs taking column/strategy/
   params as arguments; harness source never names a dataset column or strategy default. The
   dataset's Cyrillic-`С` column (`Сontract duration`) structurally punishes violations. Acceptance
   grep (`salary`, `Kurzarbeit`, `median` absent from harness) is a checked unit (u17), and the
   second-CSV smoke (u16) is the behavioural proof.
3. **`SHOW-WORK` falls out of `events.jsonl`.** The `EventLog` is built first (u03) and threaded
   through everything; console, live UI, and replay UI are three renderers of the same bytes. Event
   types fixed by the spec: `run_meta`, `stage_start/end`, `tool_call`, `tool_result`, `reasoning`,
   `execution`, `iteration_metrics`, `handoff`, `error`.
4. **Sandbox = subprocess, fresh interpreter, run dir as cwd, 120 s timeout**, stdout/stderr
   captured and returned verbatim (and logged as an `execution` event). Use the project venv's
   interpreter so generated code sees pandas/xgboost. Timeout text is returned *as stderr* so the
   Trainer reacts to it.
5. **Trainer guardrails are orchestration, not data-science:** min 2 / max 6 executions, enforced by
   the harness (e.g. `finish` rejected before 2 executions with an explanatory tool result; loop cut
   at 6 with best-so-far). Every iteration appends `{iter, params, metrics}` to
   `03_metrics_history.json` — the agent is prompted to report params/metrics in a parseable way
   (decided precisely in u11; metrics *values* always come from its own stdout, never the harness).
6. **Handoff contract** is a tiny frozen structure `{csv_path, report_markdown}`; the next agent's
   prompt embeds the report verbatim, its tools load the CSV. Stage artifact names are fixed by the
   spec (`01_…`, `02_…`, `03_metrics_history.json`, `report.md`).
7. **UI replay-first** (u14 before u15): replay needs only a finished run dir and no API key —
   it's also exactly what the grader uses on `examples/`. Live mode is then "same renderer, tail
   the file ~2×/s".

**Insights discovered while building** (kept current by the loop):

- **(u06)** `gemini-2.5-flash` readily calls tools with **no text part at all** on simple tasks —
  SHOW-WORK reasoning only appears reliably when the prompt demands it explicitly and per-call,
  in *both* system prompt and task ("in every response that calls a tool, also include a short
  plain-text sentence explaining WHY"). All stage prompts (u07/u09/u11) must carry this clause;
  transcript inspection in those units must check it held.
- **(u06)** pandas 3.0 (`3.0.3` locked): text columns read as dtype `str`, not `object` — dtype
  checks must use `is_string_dtype` *and* `is_object_dtype`.
- **(u11)** flash emits `MALFORMED_FUNCTION_CALL` (empty candidate) near-deterministically when a
  tool argument is a large multi-line code string in free-form (AUTO) mode. Fix: **forced
  function calling (`mode='ANY'`)** = constrained decoding → always-valid calls. Forced mode
  suppresses text parts, so the loop supports a harness-reserved **`reasoning` argument** on any
  tool: logged as a `reasoning` event, stripped before dispatch. The Trainer uses both; the empty-
  parts recovery now also names MALFORMED in its feedback.

**Risks → de-risking in this plan:**

| Risk | Where handled |
|---|---|
| SDK API drift / hallucinated wiring | u05 verifies against live docs + a real round-trip smoke |
| No API key / billing — human-only | u05 starts with a nag gate (`./nag.sh`), `blocked-on-user` until `.env` works |
| Dataset link rot / wrong file | u02 fingerprints (1246×23 + known dirt markers) before committing |
| Agent ignores tools / weak reasoning | every stage unit (u07/u09/u11) self-tests by *inspecting the transcript*, re-run until real; prompt-tuning stays inside the unit |
| Trainer never errors organically (no drama) | acceptance only needs *reaction to output* — weak-metrics → hyperparameter adjustment path counts; verified on real events in u11 |
| Cost runaway | flash default, per-agent turn caps, 1.2 K-row data; full/strong-model runs only at u13/u17 milestones |
| Hardcode creep | u16 second-CSV smoke + u17 grep are explicit gates |

**Testing ladder per unit** (PROCESS §loop): pure units (u01–u04, u06, u08, u10) self-test with
`pytest`/direct runs and **no LLM calls**; LLM-touching units (u05, u07, u09, u11, u12) self-test
with one real flash-model run and transcript inspection; milestones (u13, u17) are full runs.

## Work units (ordered; graded-constraint units marked)

> Status legend: `planned → implemented → verified` (or `blocked-on-user`). Statuses live in
> [`INDEX.md`](INDEX.md); per-unit detail lands in `units/<id>.md` as each is taken.

| id | Title | Done when | Graded |
|---|---|---|---|
| **u01** | Project scaffold: `pyproject.toml` (uv, pinned), `.gitignore`, `.env.example`, package skeleton | `uv sync` succeeds; `uv run python -c "import automl_team"` passes; `runs/`, `.env`, venv gitignored before any secret/artifact exists | — |
| **u02** | Fetch + commit the official dataset with a fingerprint check | `data/IT_Salary_Survey_EU_2020.csv` committed; a check (test or script) confirms 1246×23 and the known dirt markers (Cyrillic-`С` column, trailing-space `Position `, missing-heavy columns) | — |
| **u03** | `EventLog`: append-only `events.jsonl` writer + the 9 event types + console renderer | pytest round-trips every event type; console renderer prints a readable line per event | `SHOW-WORK` |
| **u04** | Orchestrator skeleton: run-dir creation, raw snapshot + stats fingerprint, stage sequencing (dummy stages) | a no-LLM dummy run creates `runs/<ts>/` with `00_raw_data.csv`, `run_meta` + `stage_start/end` events in order | — |
| **u05** | Gemini wiring + the generic agent loop (tool registry, `finish`, turn cap, malformed-call-as-tool-result) — **nag for API key first** | with a real key, a toy agent (trivial tool) completes call → result → `finish`, every arrow logged in `events.jsonl`; reasoning text captured | `NO-HARDCODE` `SHOW-WORK` |
| **u06** | Cleaner toolset: `inspect_metadata`, `get_column_stats`, `impute_missing`, `drop_column`, `drop_rows`, `normalize_categories` — generic verbs, no defaults | pytest drives every tool directly (no LLM) against the real CSV, incl. the Cyrillic-`С` column round-trip | `NO-HARDCODE` |
| **u07** | Cleaner stage green on the real dataset (prompt + stage wiring) | a real run yields `01_clean_data.csv` + `01_cleaner_report.md` with a decisions table; transcript shows every mutation preceded by an inspecting `tool_call` + adjacent `reasoning` | `NO-HARDCODE` `SHOW-WORK` |
| **u08** | Feature-Engineer toolset: `create_interaction`, `encode_categorical`, `correlation_analysis`, `select_top_features`, `count_items`, `bucketize` (+ shared `inspect_metadata`/`drop_column`) | pytest drives every tool directly (no LLM) on cleaned-shape data | `NO-HARDCODE` |
| **u09** | Feature-Engineer stage green (prompt + stage wiring, receives Cleaner handoff) | a real run yields `02_engineered_data.csv` with ≥1 new domain-logic feature, named + justified in `02_strategy_report.md`; transcript real | `NO-HARDCODE` `SHOW-WORK` |
| **u10** | Sandboxed `execute_python_code`: subprocess, fresh interpreter, run-dir cwd, 120 s timeout, verbatim capture | pytest: ok-code, stderr-crash, and timeout cases each return verbatim output; `execution` event logged | `SHOW-WORK` |
| **u11** | Trainer stage green: prompt + min-2/max-6 guardrails + `03_metrics_history.json` | real-run events show ≥2 `execution` events, each followed by `reasoning` that quotes/references the output before acting; history has ≥2 iterations; guardrails enforced | **centerpiece** `NO-HARDCODE` `SHOW-WORK` |
| **u12** | Report stage: one LLM call composes `report.md` from the two handoff reports + metrics history | generated `report.md` covers raw-data inventory → transformations (with reasons) → per-iteration metrics table → final model + limitations | `SHOW-WORK` |
| **u13** | One-command headless run (milestone) | `uv run python run_pipeline.py --data data/IT_Salary_Survey_EU_2020.csv` completes all 4 stages with zero human input; full run-dir artifact set present | — |
| **u14** | Streamlit replay mode: render any finished run dir without an API key | `streamlit run ui.py` on a past run shows stepper, chat-style transcript, raw/clean/engineered tabs, Trainer metrics chart + stdout/stderr, rendered reports | `SHOW-WORK` |
| **u15** | Streamlit live mode: tail `events.jsonl` ~2×/s during a run | a live pipeline run visibly progresses in the UI (stages flip, transcript grows) with no agent-influencing controls | — |
| **u16** | Second-CSV smoke test: different schema through stages 1–2 with zero code changes | a structurally different public CSV completes Cleaner + Feature Engineer untouched; noted in unit file | `NO-HARDCODE` (proof) |
| **u17** | Exhibit + hardening: hardcode grep, strong-model exhibit run committed to `examples/`, README — **nag for human quality judgment** | grep for dataset-specific terms in harness is clean; one un-doctored exhibit run committed under `examples/` and replayable in the UI; README quickstart written; human approved the exhibit | `NO-HARDCODE` `SHOW-WORK` |

**Unit-sizing notes:** u05 is the riskiest (external SDK + human key gate) — it is deliberately
isolated from any real toolset. Tool units (u06/u08/u10) are split from their stage units
(u07/u09/u11) so all dataframe/sandbox machinery is provably correct *before* an LLM drives it —
failures in stage units are then prompt/loop issues, not tool bugs. u13 exists as an explicit
integration milestone even though u12 nearly reaches it: it pins the CLI contract and the complete
artifact set.
