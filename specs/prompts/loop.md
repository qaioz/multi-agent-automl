# The Loop prompt (phase 3)

> Reusable. Replace `<feature>` with the feature folder name. Run it on a loop — the static prompt
> is always `read specs/<feature>/INDEX.md and continue`. One unit per iteration; the files carry
> the state, so a fresh agent each iteration is fine (and intended).

---

**Read `specs/<feature>/INDEX.md` and continue the build. One unit per iteration.**

Each iteration:

1. **Understand the full state.** Read `INDEX.md` → `plan.md` → `DESIGN.md` → `spec.md` → the latest
   `units/*.md`. A cold agent must be able to reconstruct everything from these — trust them, and if
   anything is unclear or stale, fix the docs as part of the work.

2. **Pivot if needed — don't drift.** If you see a better decomposition, or the plan contradicts
   reality, update `plan.md`'s units **and** `INDEX.md` *first*, then proceed. If implementation
   would contradict `spec.md`, update the spec (→ `In review`) and **nag** — never silently diverge
   (PRINCIPLES).

3. **Take the current unit** — the first not-`verified` in the INDEX. Write/confirm its concrete
   plan in `specs/<feature>/units/<id>.md`.

4. **Implement** — minimal and in scope (PRINCIPLES). Honour the graded constraints: **`NO-HARDCODE`**
   (tools + orchestration in the harness; every data-science *decision* comes from an LLM agent
   reasoning over tool output) and **`SHOW-WORK`** (every decision, tool call, and the Trainer's
   read-stdout-react cycle lands in the execution logs).

5. **Self-test up the ladder** — via any interface you can *drive and observe*: run the unit's code
   directly (`python …` / `pytest`), run the **pipeline end-to-end on the sample dataset**, execute
   agent-generated code in the sandbox, then **inspect the artifacts**: `clean_data.csv` /
   `engineered_data.csv` (shapes, dtypes, the promised transformations actually applied), the
   transcripts (real reasoning over real tool output — not boilerplate), the Trainer's metrics and
   its iteration decisions, the final `report.md`. Assert against the spec's acceptance criteria.
   **Never fake or skip a test.** Mind LLM cost: small sample data for loop iterations; full runs at
   milestones.

6. **Nag for the human-only parts** — whatever no tool can do (an LLM API key / billing limits,
   choosing the official dataset, judging the *quality* of the reasoning or the final report): fire
   a `PushNotification`, print a **"🔔 USER ACTION REQUIRED"** block with exact steps, **and run
   `./nag.sh "<short message>"`** (repeats until `./stop-nag.sh`). Then **stop and wait.** Never
   mark a human-gated check passed yourself.

7. **Record + update state.** In `units/<id>.md`: what was done, how it was tested, the result. In
   `INDEX.md`: the unit's status, a short dated log line, and the unit-file reference. In `plan.md`:
   any unit changes.

A unit is **done** only at `verified`. End the iteration when the current unit is `verified`, or
`blocked-on-user` with a nag pending. When the **whole build** finishes, nag:
`./nag.sh -n 3 "<feature> build done"`.
