# multi-agent-automl

**Assignment 2: The Multi-Agent AutoML Team** — an autonomous AI data-science team of three LLM
agents (Cleaner → Feature Engineer → Model Trainer) that collaborate on a dataset via structured
handoffs, with the Trainer running a self-correcting generate→execute→evaluate loop. **Read
[`Assignment.md`](Assignment.md) first** — it is the graded contract.

## Repo map

| Path | What it is |
|---|---|
| `Assignment.md` | The assignment — requirements, constraints, deliverables, checklist. |
| `specs/` | **Spec-driven development** (the source of truth). See [`specs/PROCESS.md`](specs/PROCESS.md). |
| `specs/PROCESS.md` | The working process: Discuss→Spec → Plan → Build loop (fresh agents, files are the memory). |
| `specs/PRINCIPLES.md` | The engineering constitution — incl. the graded `NO-HARDCODE` + `SHOW-WORK` rules. |
| `specs/TEMPLATE.md` | Spec template for phase 1. |
| `specs/prompts/` | The reusable Plan + Loop prompts. |
| `nag.sh` / `stop-nag.sh` | Audible human-attention alerts (used by the build loop for human-only gates). |

## Conventions

- **Spec-driven**: new work starts as a spec under `specs/<feature>/` (use `TEMPLATE.md`). **No
  implementation before the spec is `Status: Approved`.** Build via the Plan → Loop relay
  (`specs/prompts/`); resume any time with *"read `specs/<feature>/INDEX.md` and continue."*
- **Python.** Keep the dependency footprint small and pinned (one `pyproject.toml`/`requirements.txt`
  — decided in the spec/plan). Secrets (LLM API keys) live in `.env`, **never committed**.
- **Generated artifacts** (datasets, `clean_data.csv`, `engineered_data.csv`, run logs/transcripts,
  `report.md`) go under a gitignored `runs/` dir — except deliverable examples the assignment wants
  checked in (decide in the spec).
- **Verification = run it.** A thing works when the pipeline ran on a real sample dataset and the
  artifacts/logs/metrics prove it — never on hope. Mind LLM cost: iterate on a small sample, full
  runs at milestones.

## The graded constraints (always in force — see PRINCIPLES 8–9)

- **`NO-HARDCODE`** — the harness provides tools + orchestration only; every data-science decision
  (imputation strategy, drops, features, hyperparameters) is made by an LLM agent reasoning over
  actual tool output.
- **`SHOW-WORK`** — agent reasoning/transcripts are a deliverable; the Trainer must visibly read its
  own execution stdout/stderr and react (the required feedback loop).
- **Deliverables:** system code · execution logs (thought processes) · final Markdown report
  (raw data → transformations → model metrics).

## Start here

Phase 1: discuss the architecture with the owner → write `specs/automl-team/spec.md` (+ `DESIGN.md`
with the drawn pipeline/handoff/loop) → owner approves → clear context → run
`specs/prompts/plan.md` → then the build loop.
