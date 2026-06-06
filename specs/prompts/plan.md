# The Plan prompt (phase 2)

> Reusable. Replace `<feature>` with the feature folder name (e.g. `automl-team`).
> Give this to a **fresh** agent, cold, after `spec.md` is **Approved** and context is cleared.
> Its whole job is to produce `plan.md` + `INDEX.md` — **no product code.**

---

You are starting a build **cold**. The feature is **`<feature>`**; its docs are in
`specs/<feature>/`. Your only job this phase is to produce the **plan** and the **INDEX**. Write
**no product code.**

1. **Read, in order:**
   - `specs/<feature>/spec.md` — the WHAT/WHY. It **must be `Status: Approved`**; if it isn't, stop
     and say so.
   - `specs/<feature>/DESIGN.md` — the drawn architecture + risks. Any `VISION.md` if present.
   - `Assignment.md` — the graded requirements this must satisfy.
   - `specs/PROCESS.md` (this method) and `specs/PRINCIPLES.md` (the constitution — note the graded
     `NO-HARDCODE` and `SHOW-WORK` constraints).

2. **Explore the real code thoroughly.** Open the files the spec names; learn the surrounding
   conventions; see how similar pieces were built. Stay **hard on what the spec + design actually
   want** — do not invent scope, do not gold-plate.

3. **Write `specs/<feature>/plan.md`:**
   - **Implementation insights** — the technical approach at altitude: the seams to reuse, the
     critical files, the load-bearing decisions (LLM/provider wiring, tool-call plumbing, the
     sandboxed `execute_python_code`, the handoff report format, the Trainer's feedback loop), the
     risks and how the build de-risks each. Approximate is fine — this is a map, not code.
   - **Work units** — the decomposition. Each unit independently **implementable and
     self-testable**, in order. Keep them **as small as possible** (a capable agent can still do a
     lot per unit, but small = clean logs, safe pivots, easy resume). Each unit: a **stable id**, a
     **one-line title**, and a **one-line "done when"**. Mark each unit that touches a graded
     constraint (`NO-HARDCODE` / `SHOW-WORK` / the Trainer's required feedback loop).

4. **Write `specs/<feature>/INDEX.md`** (the living state file — see PROCESS.md):
   - The **context** — what we're building and why, in a few lines.
   - **Links** to `spec.md`, `DESIGN.md`, `plan.md`, `Assignment.md`.
   - The **working-process** pointer: the build runs via the loop in `specs/prompts/loop.md`; the
     resume command is `read specs/<feature>/INDEX.md and continue`.
   - The **unit table** — every unit from the plan, all `planned`, with its "done when".
   - A clear **"resume here"** entry point.

5. **Do not implement any unit.** When the plan + index are written, end by printing the exact
   **loop prompt** to hand back:

   ```
   /loop read specs/<feature>/INDEX.md and continue
   ```

You are done when `plan.md` and `INDEX.md` exist, the units are small and ordered, and the loop
prompt is printed.
