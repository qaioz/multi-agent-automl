# How we build here (the working process)

Spec-driven development run as a **multi-agent relay**: humans + AI converge on the docs, then
*separate, fresh* agents plan and build through the files — never through one long context. The
**files are the memory**; a cold agent reconstructs full state from them at any time.

## The three phases

| Phase | Who | Reads | Produces | Prompt |
|---|---|---|---|---|
| **1 · Discuss → Spec/Design** | human + AI, in conversation | the problem (`Assignment.md`), the code | `spec.md` (WHAT/WHY) + `DESIGN.md` (drawn flows) → human **Approves** | — (free conversation) |
| **2 · Plan** | a **fresh** agent, cold | the approved `spec.md` + `DESIGN.md` + the code | `plan.md` (insights + small work units) + `INDEX.md` (state) + a **loop prompt** | [`prompts/plan.md`](./prompts/plan.md) |
| **3 · Build loop** | a fresh agent each iteration | `INDEX.md` → everything | one unit implemented + self-tested; `units/<id>.md`, `INDEX.md`, `plan.md` updated | [`prompts/loop.md`](./prompts/loop.md) |

Between phase 1 and 2, **clear context** — the discussion was scaffolding; the approved docs are
the truth. Each phase hands off through the files alone.

## The artifacts (per feature, in `specs/<feature>/`)

- **`spec.md`** — WHAT & WHY (features, behaviour, acceptance). Source of truth. **No code until
  its `Status: Approved`.** Written in phase 1.
- **`DESIGN.md`** — the *drawn* architecture and flows (ASCII diagrams: the agent pipeline, the
  handoff/report formats, the tool interfaces, the Trainer's feedback loop), and "what could break
  & why it won't." The why behind the spec. Phase 1.
- **`plan.md`** — HOW at altitude: the key technical **insights** (seams, critical files,
  load-bearing decisions, risks) + the **work units**. Written in phase 2.
- **`INDEX.md`** — the single source of truth for *state*: the context ("here's what we're building
  / doing"), links to spec + design + plan, the working-process pointer, and **every unit + its
  status**. **Reading it alone = knowing where we are.** The entry point for every resume. Phase 2,
  kept live through phase 3.
- **`units/<id>.md`** — one file per build unit: its concrete plan, what was done, how it was
  tested + the result, status. Written as each unit's turn comes (phase 3).
- **[`PRINCIPLES.md`](./PRINCIPLES.md)** — the engineering constitution every agent obeys
  throughout (incl. the graded `NO-HARDCODE` and `SHOW-WORK` constraints).

## Phase 2 — Plan (the [`prompts/plan.md`](./prompts/plan.md) agent)

A fresh agent, given only the feature name, **reads the approved spec + design, explores the code
hard, stays faithful to what we want to achieve**, and writes `plan.md` + `INDEX.md`. It writes **no
product code** — it ends by emitting the loop prompt. Work units are kept **as small as possible**:
a capable agent can do a lot per unit, but small units mean cleaner logs, safer pivots, and trivial
resume. Each unit is independently **implementable and self-testable**, with a stable id and a
one-line "done when".

## Phase 3 — Build loop (the [`prompts/loop.md`](./prompts/loop.md) agent)

One unit per iteration. A fresh agent each time:

1. **Understand the full state** — `INDEX.md` → `plan.md` → `DESIGN.md` → `spec.md` → the latest
   unit files. Trust the files.
2. **Pivot, don't drift.** If a better decomposition appears (or the plan contradicts reality),
   update `plan.md`'s units + `INDEX.md` **first**, then proceed. If implementation would contradict
   the spec, update `spec.md` (→ `In review`) and **nag** — never silently diverge (PRINCIPLES).
3. **Take the current unit** (first not-`verified`); write its concrete plan in `units/<id>.md`.
4. **Implement** — minimal, in scope (PRINCIPLES — esp. `NO-HARDCODE`: tools + orchestration in the
   harness, *decisions* in the agents).
5. **Self-test up the ladder** — via any interface you can *drive and observe*: run the unit's code
   directly (`python …`/`pytest`), run the **pipeline end-to-end on a sample dataset**, execute
   agent-generated code in the sandbox, then **inspect the artifacts** — `clean_data.csv` /
   `engineered_data.csv` shapes and dtypes, the execution logs (did the agent actually reason over
   tool output? — `SHOW-WORK`), the Trainer's metrics in stdout, the final `report.md`. Assert real
   results against the spec's acceptance criteria. **Never fake or skip a test.** Mind LLM cost:
   prefer one small sample dataset for loop-iterations; full runs at milestones.
6. **Nag for the human-only parts** — what no tool can do (an LLM API key / billing, choosing the
   official dataset, judging the *quality* of agent reasoning or the final report): fire a
   `PushNotification`, print a clear **"🔔 USER ACTION REQUIRED"** block with exact steps, **and run
   `./nag.sh "<short message>"`** (a repeating audible alert — sound + spoken — that pulls the human
   in even if away; they stop it with `./stop-nag.sh`). Then **stop and wait.**
7. **Record** — in `units/<id>.md` (what was done, how tested + result) and in `INDEX.md` (status +
   a short log line + the unit-file reference). Update `plan.md` if the units changed.

> **Always nag** when the loop **finishes** *or* needs **human intervention** — so the human knows
> without watching. Loop-finish nag: `./nag.sh -n 3 "build done"`; intervention nag:
> `./nag.sh "action needed"` (repeats until `./stop-nag.sh`).

## Unit status

`planned → implemented → verified` (self-test passed) — or `blocked-on-user` (a nag is pending). A
unit is **done** only at `verified`.

## Resuming

The loop's static prompt is always *"read `specs/<feature>/INDEX.md` and continue."* The index +
unit files **are** the memory — a fresh agent reconstructs full state from them and picks up the
next unit. Nothing depends on a warm context.

## The principles of the method

- **Files are the memory.** Every handoff is through the docs; no agent relies on a prior agent's
  context. If it isn't written down, it didn't happen.
- **Small units.** Decompose to the smallest independently-testable steps. Capability is not an
  excuse to batch.
- **Pivot, don't drift.** Reality beats the plan — but change the *plan* (and say so), never the
  code silently against the spec.
- **Fresh-agent-resumable.** At any moment, a cold agent reading `INDEX.md` can continue correctly.
- **Spec-first.** No product code before `spec.md` is `Approved`.

---

*The two reusable prompts live in [`prompts/plan.md`](./prompts/plan.md) and
[`prompts/loop.md`](./prompts/loop.md) — parameterised by `<feature>`, copy-paste for any build.*
