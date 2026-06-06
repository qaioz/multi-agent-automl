# Multi-Agent AutoML Team

**Assignment 2** — an autonomous AI data-science team of three LLM agents
(**Cleaner → Feature Engineer → Model Trainer**, + a report composer) that processes a real,
messy dataset end-to-end with **zero human input after launch**.

- Every data-science decision (imputation strategies, drops, features, hyperparameters) is made
  by an LLM agent reasoning over actual tool output — the harness provides only generic tools and
  orchestration (**no hardcoding**).
- Every decision, tool call, and the Trainer's read-own-output-and-react cycle lands in
  `events.jsonl` with its evidence (**show your work**).
- The Trainer runs the graded **generate → execute → read stdout/stderr → react** loop in a
  sandboxed `execute_python_code` (min 2 / max 6 executions, 120 s timeout), producing
  `03_metrics_history.json`.

## Quickstart

```bash
# prerequisites: uv (https://docs.astral.sh/uv/), and on macOS: brew install libomp (for xgboost)
uv sync

cp .env.example .env        # put your GEMINI_API_KEY in .env (never committed)

# run the whole pipeline headless on the committed dataset (zero human input):
uv run python run_pipeline.py --data data/IT_Salary_Survey_EU_2020.csv

# watch it live, or replay any past run (replay needs NO API key):
uv run streamlit run ui.py
```

## The committed example run (graded exhibit)

`examples/full-run-2026-06-06/` is a **real, un-doctored** full pipeline run on the official
dataset (IT Salary Survey EU 2020, 1246×23). Open it in the UI (`uv run streamlit run ui.py` →
pick the `examples/…` run — no API key needed) and watch:

- the **Cleaner** inspect every column and justify each fix (outlier drops, imputation choices,
  category normalization — including the trap column `Сontract duration`, whose first letter is
  a Cyrillic С);
- the **Feature Engineer** invent domain features and encode categoricals with stated rationale;
- the **Trainer** ship a catastrophically bad first model (**R² −5.17**), *read its own output*,
  diagnose and fix errors across iterations, and land at **R² 0.48**
  (`03_metrics_history.json`) — the feedback loop in action, including a quoted error line
  before every reaction;
- the generated **`report.md`** tell the whole story: raw data → transformations → per-iteration
  metrics → limitations.

## Architecture (short)

```
run_pipeline.py            CLI entrypoint (one command, headless)
ui.py                      Streamlit viewer: live tail (~2×/s) + keyless replay
automl_team/
  agent.py                 ONE generic Gemini function-calling loop (all three agents)
  orchestrator.py          run dir, raw snapshot + fingerprint, stage sequencing — no brain
  stages.py                stage wiring incl. the Trainer guardrails (min 2 / max 6)
  events.py / console.py   events.jsonl writer + console renderer (UI renders the same bytes)
  tools/                   generic verbs: cleaner.py, features.py, sandbox.py (120 s subprocess)
  prompts/                 the agent system prompts (generic — no dataset nouns)
  report.py                stage 4: one LLM call → report.md
data/IT_Salary_Survey_EU_2020.csv   the committed official dataset
examples/                  the committed exhibit run
runs/                      generated runs (gitignored)
```

Design docs and the full build log: [`specs/automl-team/`](specs/automl-team/) (spec → DESIGN →
plan → per-unit records). Tests: `uv run pytest` (74 tests; LLM-touching tests auto-skip without
a key).

**Anti-hardcoding proof:** tools take every column/strategy/parameter as agent-chosen arguments
(`grep -riE "salary|kurzarbeit" automl_team/` finds nothing in harness logic), and the identical
code ran the Titanic dataset (completely different schema) through stages 1–2 with zero changes
(`specs/automl-team/units/u16.md`).

## Configuration

`.env` (see `.env.example`): `GEMINI_API_KEY` (required to run the pipeline; not needed for
replay) · `GEMINI_MODEL` (default `gemini-2.5-flash`).
