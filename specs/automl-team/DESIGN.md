# DESIGN — Multi-Agent AutoML Team

The drawn architecture behind [`spec.md`](spec.md). The *why* lives here; the *what* lives there.

## 1. The pipeline (sequential handoff)

```
                       ┌────────────────────────────────────────────────────────────┐
                       │            ORCHESTRATOR (no brain: plumbing + logging)     │
                       └────────────────────────────────────────────────────────────┘
 data/IT_Salary_….csv         │                  │                   │              │
        │                     ▼                  ▼                   ▼              ▼
        │              ┌────────────┐     ┌──────────────┐    ┌────────────┐  ┌──────────┐
        └─ snapshot ──▶│ ① CLEANER  │     │ ② FEATURE    │    │ ③ TRAINER  │  │ ④ REPORT │
           00_raw_data │ "Auditor"  │     │   ENGINEER   │    │  "Coder"   │  │ (1 LLM   │
                       │            │     │ "Architect"  │    │            │  │  call)   │
                       └─────┬──────┘     └──────┬───────┘    └─────┬──────┘  └────┬─────┘
                             │ handoff           │ handoff          │              │
                             ▼                   ▼                  ▼              ▼
                      01_clean_data.csv   02_engineered_data.csv   03_metrics_   report.md
                    + 01_cleaner_report.md + 02_strategy_report.md  history.json
                             └───────────────────┴──────────────────┴──── all events ──▶ events.jsonl
```

**Handoff contract** (assignment: "Structured Reports" = CSV + text summary):

```
┌──────────────────────────────────────────────────────────────┐
│ HANDOFF n = { csv_path, report_markdown }                    │
│  • next agent's prompt embeds the report_markdown verbatim   │
│  • next agent's tools operate on a dataframe loaded from csv │
└──────────────────────────────────────────────────────────────┘
```

The report is *load-bearing*: agent n+1 is prompted to read it and may rely on it
("Cleaner already removed salary outliers → ratios against salary are safe").

## 2. The generic agent loop (one implementation, three agents)

Raw `google-genai` function-calling — no framework. Same ~50-line loop for every agent;
only (system prompt, toolset, input context) differ.

```
        ┌─────────────────────────────────────────────────────────────┐
        │  history = [system prompt + task + upstream report]         │
        │                                                             │
        │  ┌──────────► Gemini (history, tool declarations)           │
        │  │                       │                                  │
        │  │                       ▼                                  │
        │  │            response: text part?  ──────▶ log: reasoning  │
        │  │                      function_call part?                 │
        │  │                       │                                  │
        │  │              ┌────────┴─────────┐                        │
        │  │        call = finish(report)?   no                       │
        │  │              │ yes              │                        │
        │  │              ▼                  ▼                        │
        │  │        write handoff      execute tool on df             │
        │  │        log: handoff       log: tool_call + tool_result   │
        │  │        ── exit loop       append result to history       │
        │  └─────────────────────────────────┘                        │
        └─────────────────────────────────────────────────────────────┘
```

Why raw SDK: every arrow above is a line of *our* code, so every arrow can emit an event —
`SHOW-WORK` falls out of the architecture instead of being bolted on via framework callbacks.

**`NO-HARDCODE` by construction:** tools are generic verbs (`impute_missing(column, strategy)`);
the *nouns* (which column, which strategy) only ever arrive as LLM-chosen arguments. The harness
source never names a dataset column. The dataset enforces this structurally: its `Сontract
duration` column starts with a Cyrillic С — hand-typed harness references crash; agents that copy
names from tool output never notice.

## 3. The Trainer's feedback loop (the graded centerpiece)

```
            ┌─────────────────────────────────────────────────────────┐
            │ context: engineered CSV path + strategy report          │
            ▼                                                         │
   ┌─ GENERATE code (XGBoost train/eval, prints metrics) ─┐           │
   │                                                      │           │
   │       execute_python_code(code)                      │           │
   │                │                                     │           │
   │                ▼  subprocess, 120 s timeout          │           │
   │     ┌─────────────────────────┐                      │           │
   │     │ fresh python, run dir   │                      │           │
   │     │ stdout/stderr captured  │                      │           │
   │     └───────────┬─────────────┘                      │           │
   │                 ▼                                    │           │
   │   log: execution {stdout, stderr}  ◄─ verbatim       │           │
   │                 │                                    │           │
   │                 ▼                                    │           │
   │   READ own output (must quote/reference it)          │           │
   │                 │                                    │           │
   │      ┌──────────┴───────────┬───────────────┐        │           │
   │      ▼                      ▼               ▼        │           │
   │   error in stderr      metrics weak     metrics OK   │           │
   │   → diagnose, fix      → adjust hyper-  → justify    │           │
   │     code               params           stop         │           │
   │      │                      │               │        │           │
   │      └──────► iterate ◄─────┘               ▼        │           │
   └──────────────────│────────────────── finish(report) ─┘           │
                      └───────────────────────────────────────────────┘
   guardrails (orchestration, not data-science): min 2, max 6 executions
   every iteration → 03_metrics_history.json {iter, params, metrics}
```

Expected organic drama on this dataset (verified by profiling): iter 1 often dies on a surviving
string column (`ValueError` in stderr → diagnose → encode); 1.2 K rows overfit readily
(train-AUC ≈ 1.0 vs test ≈ 0.78 → depth/regularization reaction). Either path demonstrates the
required reactive loop on *real* output.

## 4. events.jsonl — one log, three renderers

```
   pipeline ──append──▶ runs/<ts>/events.jsonl ──┬──▶ console renderer (headless runs)
                                                 ├──▶ Streamlit live mode (tail ~2×/s)
   {ts, agent, type, payload}                    └──▶ Streamlit replay mode (any past run,
   types: run_meta · stage_start/end ·                no API key — incl. the committed
   tool_call · tool_result · reasoning ·              examples/ run a grader watches)
   execution · iteration_metrics ·
   handoff · error
```

Why: the pretty view and the graded transcript are *the same bytes* — the UI can never drift from
the truth, and replay-without-key makes the exhibit run demonstrable anywhere.

## 5. Streamlit UI (read-only window)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🤖 Multi-Agent AutoML Team        run: 2026-06-06_14-32   ▶ live ⟳      │
│  ① Cleaner ✅ ────▶ ② Feature Engineer ⚙️ ────▶ ③ Trainer ⬜ ──▶ ④ 📄     │
├───────────────────────────────────────────┬──────────────────────────────┤
│  TRANSCRIPT (chat-style)                  │  DATA [Raw][Clean][Engineered]│
│  🧰 tool_call → ↩ tool_result             │  dataframe preview            │
│  💭 reasoning bubble                      │  TRAINER LOOP                 │
│  ❗ execution stderr block                │  test-AUC per iteration chart │
├───────────────────────────────────────────┴──────────────────────────────┤
│  [📜 Transcript][🧹 Cleaner report][🏗 Strategy][📊 Metrics][📄 Report]   │
└──────────────────────────────────────────────────────────────────────────┘
```

No controls that influence agents — autonomy is a graded property; a read-only UI cannot
compromise it. Streamlit's rerun-and-redraw model matches "poll the file, redraw" exactly.

## 6. What could break & why it won't

| Risk | Mitigation |
|---|---|
| Agent ignores tools / acts without evidence | Prompts require citing tool output before any action; acceptance criteria check every mutation has a preceding tool_call in the log; re-run until exhibit-quality (never doctor logs) |
| Gemini function-calling returns malformed/unknown calls | Harness validates args, returns the error *as the tool result* — the agent sees and corrects (same feedback principle as the Trainer loop) |
| Trainer code hangs / infinite loop | 120 s subprocess timeout → timeout message returned as stderr → agent reacts |
| Trainer never converges | Max 6 executions cap (orchestration guardrail); finish forced with best-so-far |
| Runaway LLM loop burns money | Per-agent turn cap; flash model default; 1.2 K-row dataset keeps tokens small |
| Harness accidentally hardcodes | Acceptance grep (`salary`, `Kurzarbeit`, `median` absent from harness); second-CSV smoke test must pass stages 1–2 untouched |
| UI drifts from logs | Impossible by construction — UI renders events.jsonl only |
| Secrets leak | `.env` gitignored; example-run events scrubbed of nothing *but* checked to contain no key material (keys never enter prompts anyway) |
| Non-determinism makes grading flaky | Replay mode: the committed run is watchable without any API call |
