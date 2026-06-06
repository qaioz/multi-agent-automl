# Multi-Agent AutoML Team

- **Status:** Approved <!-- Draft | In review | Approved | In progress | Done -->
- **Owner:** Gaioz Tabatadze
- **Updated:** 2026-06-06
- **Implementation:** — (fill in once it exists)

## 1. Goal / problem

Assignment 2 ([`Assignment.md`](../../Assignment.md)): an autonomous AI data-science team of three
LLM agents — **Cleaner → Feature Engineer → Trainer** — that processes a real, messy dataset end to
end with **zero human input after launch**. Agents make every data-science decision themselves by
reasoning over tool output (`NO-HARDCODE`), and every decision lands in the logs with its evidence
(`SHOW-WORK`). One command produces: cleaned/engineered CSVs, a trained XGBoost model with an
iteration history proving a self-correcting feedback loop, full reasoning transcripts, and a
generated Markdown report — all watchable live (or replayable) in a Streamlit UI.

## 2. Scope

- **In:**
  - The three-agent sequential pipeline with structured handoffs (CSV + markdown report each).
  - Per-agent toolsets (assignment's lists + minimal justified extensions — see §5).
  - The Trainer's generate → execute → evaluate → decide loop via a sandboxed
    `execute_python_code`.
  - Canonical event log (`events.jsonl`) per run — the "execution logs" deliverable.
  - LLM-generated final `report.md` (raw data → transformations → model metrics).
  - Streamlit viewer with **live** and **replay** modes (read-only window onto a run).
  - The official dataset: **IT Salary Survey EU 2020** (1,246 × 23), committed under `data/`.
  - One polished, real example run committed under `examples/` as the graded exhibit.
- **Out:**
  - Human-in-the-loop steering, UI controls that influence agents (UI is a viewer, period).
  - Provider abstraction (Gemini only), multi-dataset benchmarking, model persistence/serving,
    hyperparameter search frameworks, Docker, parallel agents.

## 3. Behaviour / walkthrough

```
$ python run_pipeline.py --data data/IT_Salary_Survey_EU_2020.csv      # headless
$ streamlit run ui.py                                                  # watch live or replay
```

1. **Orchestrator (no brain):** creates `runs/<ts>/`, snapshots raw data + stats fingerprint,
   then runs the stages in order. It makes **zero** data decisions — plumbing and logging only.
2. **Stage 1 — Cleaner:** inspects metadata/column stats via tools, decides and executes fixes
   (drops, imputations, outlier-row removal, category normalization — *its* choices), hands off
   `01_clean_data.csv` + `01_cleaner_report.md` (decisions table: column → issue → action → why).
3. **Stage 2 — Feature Engineer:** receives the Cleaner's report text + clean CSV; runs
   correlation analysis, creates ≥1 domain-logic feature (assignment checklist), encodes
   categoricals, removes collinear/weak features; hands off `02_engineered_data.csv` +
   `02_strategy_report.md` (feature → rationale).
4. **Stage 3 — Trainer:** chooses the target framing (regression vs. classification — its call,
   logged), then loops: generate Python (XGBoost) → `execute_python_code` → read verbatim
   stdout/stderr → react (fix errors, adjust hyperparameters) or justify stopping.
   Guardrails (orchestration, not data-science): min 2, max 6 executions, 120 s timeout each.
   Produces `03_metrics_history.json` (per-iteration params + metrics).
5. **Stage 4 — Report:** one LLM call composes `report.md` from the two handoff reports +
   metrics history: raw-data inventory → transformations (with reasons) → iteration-by-iteration
   metrics → final model + feature importances → honest limitations.
6. **UI:** tails `runs/<ts>/events.jsonl` ~2×/s. Pipeline stepper (stage status), chat-style
   transcript (tool call → result → 💭 reasoning), tabbed dataframe previews (raw/clean/
   engineered), Trainer metrics-per-iteration chart + raw stdout/stderr, rendered reports.
   Replay mode renders any past run dir — including the committed example — **without an API key**.

## 4. Design notes

Key decisions (drawn flows in [`DESIGN.md`](DESIGN.md)):

- **LLM:** Google **Gemini** via the `google-genai` SDK. Model **configurable** via `.env`
  (`GEMINI_MODEL`, default `gemini-2.5-flash`; use a stronger model for milestone runs).
  `GEMINI_API_KEY` in `.env`, never committed.
- **Agent loop = raw SDK function-calling loop** (~50 lines): send history + tool declarations →
  model returns function calls → harness executes, logs events, appends results → repeat until the
  agent calls its `finish(report)` tool. No agent framework — full control of logging
  (`SHOW-WORK`) and visible machinery.
- **`events.jsonl` is the single source of truth** for what happened; console output and the UI
  are both renderers of it. Event types: `run_meta`, `stage_start/end`, `tool_call`,
  `tool_result`, `reasoning`, `execution` (verbatim stdout/stderr), `iteration_metrics`,
  `handoff`, `error`.
- **Sandbox:** `subprocess` running a fresh Python in the run dir, 120 s timeout, stdout/stderr
  captured and returned to the Trainer verbatim (accepted risk: runs as local user; our prompts,
  our machine).
- **`NO-HARDCODE` enforcement by construction:** the harness never references dataset-specific
  column names or strategies; tools take the column/strategy as *arguments chosen by the agent*.
  (The dataset's Cyrillic-`С` column name structurally punishes hardcoding.)
- **Toolset extensions** beyond the assignment's example lists (it says "Tools:", we read as
  minimum): the dataset *requires* row-level outlier handling and category normalization —
  documented in §5, decisions still 100 % the agent's.
- **Deps** (single `pyproject.toml`, pinned): `google-genai`, `pandas`, `xgboost`,
  `scikit-learn`, `streamlit`, `python-dotenv`.
- **Cost control:** dataset is small (1,246 rows); default flash model for loop iterations;
  full/strong-model runs at milestones only.

## 5. Data / API

**Dataset (committed):** `data/IT_Salary_Survey_EU_2020.csv` — IT Salary Survey EU/Germany 2020,
1,246 × 23, public ([source mirror](https://raw.githubusercontent.com/leahsaurus/IT-Salary-Europe-2020/main/IT_Salary_Survey_EU_2020.csv),
original: Kaggle `parulpandey/2020-it-salary-survey-for-eu-region`). Verified dirt: €1e11/€500M
salary outliers; 70 %/63 % missing skip-logic columns (Kurzarbeit/WFH); trailing-space column name
(`Position `); Cyrillic-С column name (`Сontract duration`); 23-value `Seniority level`;
case/space-noisy categories (`Stuttgart `, `python `); 365-day vacation claims; free-text
`Employment status`.

**Agent toolsets** (assignment tools ✓, extensions ★ — all operate on the stage's working
dataframe; every call + result + the agent's stated reason is logged):

| Agent | Tools |
|---|---|
| Cleaner | ✓ `inspect_metadata()` · ✓ `get_column_stats(column)` · ✓ `impute_missing(column, strategy[, value])` · ✓ `drop_column(column)` · ★ `drop_rows(column, condition)` (outliers/invalid rows) · ★ `normalize_categories(column, mapping \| strip+casefold)` · `finish(report_markdown)` |
| Feature Engineer | ✓ `create_interaction(col_a, col_b, op, new_name)` · ✓ `encode_categorical(column, method[, order])` · ✓ `correlation_analysis([target])` · ✓ `select_top_features(k \| threshold)` · ★ `count_items(column, sep, new_name)` (packed lists) · ★ `bucketize(column, rule, new_name)` · `inspect_metadata()` · `drop_column(column)` · `finish(report_markdown)` |
| Trainer | ✓ `execute_python_code(code_string)` (gets the engineered CSV path) · `finish(report_markdown)` |

**Handoff contract (per assignment):** processed CSV + markdown summary report; the next agent
receives the report text in its prompt and the CSV path for its tools.

**Run-dir layout:** `runs/<ts>/{events.jsonl, 00_raw_data.csv, 01_clean_data.csv,
01_cleaner_report.md, 02_engineered_data.csv, 02_strategy_report.md, 03_metrics_history.json,
report.md}`.

## 6. Acceptance criteria

Mechanisms are mandated, not specific decisions (LLM behaviour isn't fully deterministic; we
re-run until an example run is exhibit-quality, never doctor logs).

- [ ] One command runs the full pipeline on the committed dataset with zero human input;
      all run-dir artifacts above are produced.
- [ ] **Assignment checklist 1:** Cleaner produces `01_clean_data.csv` + a decisions table where
      every action is traceable to a logged tool call that preceded it.
- [ ] **Assignment checklist 2:** ≥1 new domain-logic feature exists in
      `02_engineered_data.csv`, named and justified in the strategy report.
- [ ] **Assignment checklist 3+4:** Trainer's `events.jsonl` shows ≥2 `execution` events with
      verbatim stdout/stderr, each followed by a `reasoning` event that *quotes or references*
      the output before changing parameters or justifying termination;
      `03_metrics_history.json` has ≥2 iterations.
- [ ] **`NO-HARDCODE`:** harness source contains no dataset-specific column names, imputation
      strategies, feature definitions, or hyperparameter values; all arrive as LLM-chosen tool
      arguments. (Spot-check: grep the harness for `salary`, `Kurzarbeit`, `median`.)
- [ ] **`SHOW-WORK`:** every mutation of the dataframe appears in `events.jsonl` as
      tool_call + tool_result + an adjacent reasoning event explaining why.
- [ ] `report.md` is generated (not hand-written), covers raw data → transformations → metrics
      with the iteration table, and a non-author can follow it in ~5 minutes.
- [ ] Streamlit UI renders a **live** run and **replays** the committed example run without an
      API key: stepper, transcript bubbles, dataframe tabs, metrics chart, reports.
- [ ] A real, un-doctored example run is committed under `examples/` (transcripts + artifacts +
      its `report.md`); `runs/` is gitignored; `.env` is gitignored.
- [ ] Pipeline re-run on a *second* CSV with different schema completes stages 1–2 without code
      changes (smoke-proof that nothing is hardcoded; model quality not asserted).

## 7. Build order

1. Skeleton: `pyproject.toml`, `.env` handling, run-dir + `events.jsonl` writer, orchestrator.
2. Gemini agent loop (generic: system prompt + tools + finish) with full event logging.
3. Cleaner tools + prompt → stage 1 green on the real dataset.
4. Feature Engineer tools + prompt → stage 2 green.
5. Sandbox + Trainer prompt + loop guardrails → stage 3 green with ≥2 iterations.
6. Report generation stage.
7. Streamlit viewer (replay mode first — needs only a finished run dir; then live tailing).
8. Second-CSV smoke test; polish prompts; produce + commit the example run; README.
