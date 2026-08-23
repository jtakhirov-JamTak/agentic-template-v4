---
description: Plan Mode discovery → design → spec for a new app, producing docs/SPEC.md
---
I want to build: $ARGUMENTS

Run three phases in this one Plan Mode session, in order. Do not blend
phases. Two human approvals exist: the solution direction and the final spec;
the problem summary is non-blocking.

## PHASE 1 — DISCOVER (elicitation only; no solutions)
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
Write it to `docs/SPEC.md` under `# Part 1 — Problem`, say "Unless anything
here is wrong, I'm proceeding to design," and continue. I interrupt only to
correct it.

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

**DIRECTION GATE** — I pick or approve the solution. Record the decision and
rationale in `docs/DECISIONS.md`, then continue.

## PHASE 3 — SPECIFY
Append to `docs/SPEC.md` under `# Part 2 — Spec`:
1. **Outcome** — one line + measurement method. If the app itself must produce
   the measurement data, instrumentation becomes a scoped feature.
2. **Target users.**
3. **Features**, numbered in build order (dependencies and risk first). Per
   feature: 2–4 sentences of user-facing behavior + acceptance criteria as
   observable, machine-checkable checks ("Returns HTTP 429 after more than 5
   requests/hour per IP", not "should have good rate limiting"). Mark every
   feature touching auth, authorization/RLS, money/billing, or migrations as
   **HIGH-RISK** (each requires an evaluator pass after build).
4. **Explicit v1 non-goals.**
5. **Key assumptions** (from the Phase 1 labels).
6. **Stack, auth/security model, shared entities** — 15 lines max. Anything
   only one feature needs is designed when that feature is built.
7. **Risks (pre-mortem).** Assume this spec failed: the 3 most likely reasons,
   with one mitigation each.
8. **Short file/step plan.**

Present the completed spec for my review. After I approve: do NOT begin
implementation. Tell me to start a fresh session to execute it — the build
session treats `docs/SPEC.md` as the source of truth per CLAUDE.md.
