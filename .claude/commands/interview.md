---
description: Plan Mode discovery → design → spec. New-app mode produces docs/SPEC.md; feature mode amends it with one feature entry.
---
I want to build: $ARGUMENTS

## MODE — decide this first
Read `docs/SPEC.md`.

- **It does not exist → NEW-APP MODE.** Run Phases 1–3 in order, in this one Plan
  Mode session. Do not blend phases.
- **It exists → FEATURE MODE.** Skip Phases 1–3 and go to FEATURE MODE below.

**Escalation.** If feature mode turns up a genuine architecture change, run the full
DESIGN → SPECIFY for that change — but do **not** rerun or rewrite Part 1 (target
users, outcome, stack, auth model) unless the product outcome itself changed. Say
plainly that you are escalating, and why, before you do it.

## APPROVAL GATES — count them, and do not add more
| Work | Approvals | What is approved |
|---|---|---|
| New app, or an architecture change | **2** | the direction (including the mockup, if UI) · the final SPEC |
| Feature | **1** | the feature delta (including the mockup, if UI) |
| One-sentence reversible change | **0** | build it directly — do not run this command |

The Phase 1 problem summary is non-blocking and is not one of these.

## PHASE 1 — DISCOVER (new-app mode; elicitation only, no solutions)
Interview me using the AskUserQuestion tool, in batches of at most 4 questions.

Understand first: business outcome AND how it will be measured · target users ·
the problem behind the request · core user workflows · success criteria ·
constraints. Then, where relevant: priorities, UI/UX, data and integrations,
technical considerations, security/privacy, edge cases, tradeoffs.

Include failure framing as QUESTIONS to me: "What would make this a failure
for you?" "What would make you miserable at the end of this process?"

Do not waste questions on things that can be reasonably inferred. Prioritize
hard, high-impact questions I may not have considered. As you go, label what
you learn: fact vs assumption vs requirement vs preference.

Stop when the remaining unknowns can no longer materially change the product,
scope, or architecture.

**Do not recommend or commit to any solution or architecture in this phase.**
Architecture-sensitive questions are allowed when the answer could materially
change feasibility, scope, or risk.

**PROBLEM SUMMARY (non-blocking)** — Present it: outcome + measurement method
· users · problem · requirements (labeled) · constraints · failure conditions.
Write it to `docs/SPEC.md` under `# Part 1 — Problem`, say you are proceeding to
design unless anything there is wrong, and continue. I interrupt only to correct it.

## PHASE 2 — DESIGN (analysis; I appear only at the direction gate)
1. **Invert.** What would guarantee the outcome fails, independent of any
   solution? The biggest failure paths become constraints or kill criteria.
2. **Diverge (when it matters).** Always test first whether the outcome can
   be achieved without building software (no-build / off-the-shelf). Then
   generate materially different alternatives only when the choice is
   consequential or genuinely uncertain — never invent inferior options to
   fill a quota. For each candidate: how it works, tradeoffs, risks, rough
   effort, fit against Part 1.
3. **Delete.** For the leading candidate, per requirement/component:
   question it → delete it entirely → see what actually breaks → restore only
   what the outcome requires → simplify what's left. If you are not forced to
   put back at least 10% of what you deleted, you did not delete enough.
4. **Decide.** Recommend one. Classify its major decisions by the cost to
   reverse *in this project*: cheap-to-reverse decisions decide now;
   expensive-to-reverse ones get the cheapest experiment that could invalidate
   them before commitment. (Schema shape, auth model, and platform are
   typically expensive to reverse in apps like these — but judge by actual
   cost here, not the category.) It is a valid recommendation that the app
   should be simplified, postponed, or not built.

If the app has any UI at all, run the UI BLOCK for the first screen before this
gate, so the mockup is part of what I approve.

**DIRECTION GATE (approval 1 of 2)** — I pick or approve the solution. Record the
decision and rationale in `docs/DECISIONS.md`, then continue.

## PHASE 3 — SPECIFY
Append to `docs/SPEC.md` under `# Part 2 — Spec`:
1. **Outcome** — one line + measurement method. If the app itself must produce
   the measurement data, instrumentation becomes a scoped feature.
2. **Target users.**
3. **Features**, numbered in build order (dependencies and risk first). Per
   feature: 2–4 sentences of user-facing behavior + acceptance criteria as
   observable, machine-checkable checks ("Returns HTTP 429 after more than 5
   requests/hour per IP", not "should have good rate limiting"). Tag each
   feature with the evaluator trigger(s) that apply per EVALUATOR TRIGGERS
   below, or `none`. **Feature 1 must be the walking skeleton** — the thinnest
   end-to-end usable path through UI → API → data (→ auth if relevant).
4. **Explicit v1 non-goals.**
5. **Key assumptions** (from the Phase 1 labels).
6. **Stack, auth/security model, shared entities** — 15 lines max. Anything
   only one feature needs is designed when that feature is built.
7. **Risks (pre-mortem).** Assume this spec failed: the 3 most likely reasons,
   with one mitigation each.
8. **Short file/step plan.**

**SPEC GATE (approval 2 of 2)** — Present the completed spec for my review. After I
approve: do NOT begin implementation. Tell me to start a fresh session to execute it —
the build session treats `docs/SPEC.md` as the source of truth per CLAUDE.md.

## FEATURE MODE
Read `docs/SPEC.md` and `docs/DECISIONS.md` before asking anything. DECISIONS.md
records what has already been rejected and why; do not re-open a settled question
without new evidence.

Ask, in batches of at most 4, only what can change **this** feature:
- the user-facing behavior and the flow through it
- acceptance criteria — observable and machine-checkable
- edge cases and failure states
- data and API impact: new tables or columns, new endpoints, changed contracts
- any hard-to-reverse choice this feature forces

Same stop rule as Phase 1: stop when the remaining unknowns can no longer change
scope, architecture, risk, or acceptance. Apply inversion and delete/restore to the
feature rather than the product — what would make this feature fail, and what can be
removed from it entirely. The no-build test still applies: say so if the outcome is
better served without building this.

If the work adds or changes a screen, run the UI BLOCK.

**Output — amend `docs/SPEC.md` with ONE feature entry**, appended in build order:

```
### F<n> — <name>
- Behavior — 2-4 sentences of user-facing behavior.
- Acceptance criteria — observable, machine-checkable checks.
- Non-goals — what this feature deliberately does not do.
- Risks — the most likely failures, one mitigation each.
- Evaluator — which trigger(s) apply, or none.
- UI — the short block from the UI BLOCK, if it ran.
```

**Forbidden in feature mode:** editing any other feature's entry, and editing Part 1.
If this feature appears to require either, that is the escalation signal — say so and
stop, rather than doing it quietly.

**FEATURE GATE (the single approval)** — present the feature entry, and the mockup if
one was made. After I approve: do NOT begin implementation. Tell me to start a fresh
session to build it.

## UI BLOCK (conditional — only when the work adds or changes a screen)
Exactly four questions, one batch:
1. What is the primary action a user takes on this screen?
2. Mobile-first, desktop-first, or both?
3. References — first list what already exists in `docs/mockups/<feature>/` and ask
   which of those apply. Ask for new references only if that directory is empty or
   none of it fits.
4. Which of empty / loading / error / gated states matter here?

Then produce **ONE** mockup, not three:
- **Frontend stack already settled** → a thin page in the actual stack with hardcoded
  data, on a branch. It is throwaway scaffolding for the decision, not the
  implementation.
- **Stack not settled** → the smallest executable prototype that can be reused later.

The mockup rides inside the approval for the mode you are in. It does not add a gate.

**Output:** a short UI block inside the SPEC feature entry (or inside the Phase 3
feature, in new-app mode): primary action · viewport target · states covered · path
to the mockup. Never a separate document.

## EVALUATOR TRIGGERS (shared by both modes)
Tag a feature for an evaluator pass when **any** of these is true:
- it is the first vertical slice
- authentication, authorization, or RLS
- money or billing
- a destructive or data-transforming migration
- a migration touching existing production rows
- a migration creating a table that will hold user data — regardless of how many rows
  it holds today
- pre-release

**Not a trigger by default:** an additive migration on a table that holds no user data.

Multiple triggers in one feature = **one** evaluator run for the whole feature.
