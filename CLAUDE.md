# Project Rules — Plan → Build → Evaluate

Global `~/.claude/CLAUDE.md` applies. Its hard stops (commit/push only when asked,
the delete/overwrite boundary, secrets only in `.env`, verification must be able to
fail) are not repeated here and are never overridden.

## Workflow
1. **PLAN** — route by size, and count the approvals:
   - **New app, or a change to architecture** → Plan Mode (Shift+Tab twice), run
     `/interview`. Two approvals: the direction, then the final `docs/SPEC.md`. Then
     a fresh session to build — the one handoff worth its cost.
   - **A feature** → `/interview`, which detects feature mode from an existing
     `docs/SPEC.md` and amends it with one feature entry. One approval, and then it
     builds **in the same session**. A fresh session there is an exception `/interview`
     may recommend on evidence, never a routine step.
   - **A one-sentence reversible change** → build it directly. No approval, no
     `/interview` — BUILD opens the metric row itself.

   `docs/SPEC.md` is the single source of truth for what to build.

2. **BUILD** — in the main session, one SPEC feature at a time, in SPEC order. Read
   `docs/SPEC.md` before touching anything.

   For each SPEC feature:
   ```
   read its requirements and acceptance criteria
   no metric row open for this feature (direct build, no /interview)
     → open it now, before any code: started_at = now UTC, green_at = —
   implement the thinnest correct version
   run the feature's acceptance checks
   red → diagnose, fix, rerun; do not ask
   UI added or changed → visually verify (below)
   evaluator trigger present → one evaluator run for the whole feature;
     fix P1 automatically; stop only for P0
   everything above actually passed → close the row: green_at = now UTC,
     cycle_time = green_at - started_at
   mark complete; immediately start the next feature; do not ask
   ```

   **The metric log measures elapsed real time, so it is opened before the work and
   closed after it — never reconstructed once the feature is done.** One row per
   feature in `docs/PROGRESS.md`; at most one open (`green_at` = `—`) at a time.
   - **`/interview` opens the row**, as its first workflow action, for anything that
     went through it. An interviewed feature's clock therefore includes its own
     planning; a new app's F1 clock includes the interview, the design, both approvals
     and the fresh-session handoff.
   - **BUILD opens the row** for a direct build that skipped `/interview` — immediately
     before implementation begins, not after.
   - **BUILD closes the row, always.** `green_at` is written only after all required
     and available verification passes — acceptance checks, visual verification when
     UI changed, the evaluator pass when a trigger applied. If a required check fails
     or is skipped, the row stays open and records why. Tooling unavailability blocks
     green only when that verification is required by the acceptance criteria or the
     release boundary. A `green_at` written ahead of its evidence turns the metric
     into fiction, and a metric nobody can trust stops the looking.
   - Never backfill `started_at` from memory, and never open and close a row in the
     same action.

   Opening or closing a row is bookkeeping, not a gate: it costs one line and stops
   for nobody.

   **Feature 1 is a walking skeleton**: the thinnest end-to-end usable path through
   UI → API → data (→ auth if relevant). If dependencies genuinely prevent that,
   Feature 2 must be. If there is still no end-to-end path after Feature 2, stop and
   amend SPEC.md.

   **Stop during BUILD only for:** material SPEC invalidation (stop, amend SPEC.md,
   then resume — never silently diverge) · an irreversible external action · a
   genuinely expensive-to-reverse decision the SPEC did not settle · evaluator P0 ·
   release or push · the production gate below · the delete/overwrite boundary as
   defined in global `~/.claude/CLAUDE.md`. Nothing else. Unrelated discoveries go to
   `docs/BACKLOG.md`; stay on the current intent.

   **Production gate — the one exception to zero build-time approvals.** For any app
   with real users (`pure-eq`), before executing any operation that can modify
   existing production user data or change auth/RLS behaviour — a migration, a repair
   script, a policy edit, anything — show it and wait.

   **Visual verification.** Requires browser tooling (Claude in Chrome or equivalent).
   If it is not available in this session, say so and skip it — do not substitute a
   prose description and call the screen verified. When it is available: start
   localhost → open the page at the target viewport → screenshot → compare against the
   approved mockup → exercise one key state.

3. **EVALUATE** — dispatch the `evaluator` subagent when the feature carries a trigger.

   **Always:** the first vertical slice · authentication, authorization, or RLS ·
   money or billing · a destructive or data-transforming migration · a migration
   touching existing production rows · any migration creating a table that will hold
   user data, regardless of how many rows it holds today · pre-release.

   **Not a trigger by default:** an additive migration on a table that holds no user
   data.

   Multiple triggers in one feature = **one** evaluator run for the whole feature.

   Its task prompt contains ONLY: which SPEC.md features are in scope and how to run
   the app. Never describe how anything was built. Save its report verbatim to
   `docs/evals/eval-NN.md`. P0 → stop, tell the human. P1 → fix before continuing.
   P2 → BACKLOG.md.

   Immediately BEFORE dispatching, run `git status --porcelain` and record the
   exact output. The evaluator runs in the real working tree so that it sees
   uncommitted work, which also means it could disturb it. Its report must open
   and close with the same command. All three outputs must be identical — if
   they are not, the evaluation is invalid and its findings do not count.

   If the report is a **P0 HARNESS FAILURE**, no evaluation happened. Do not
   record it as an eval, do not act on any grade in it. The usual cause is an
   untrusted workspace, which makes Claude Code skip the evaluator's frontmatter
   hooks: accept the trust dialog, then dispatch again.

## Build rules
- Load the `engineering-conventions` skill before schema, auth, money, or
  migration work.
- Self-test with the falsifiability check before claiming done (see skill).
- Session end: `npm run verify` green, or work stashed. Handoff state has one owner —
  `session-context.md`, whose trigger and format are defined in
  `~/.claude/commands/save-context.md`. `docs/PROGRESS.md` is not a handoff: it holds
  shipped milestones and the metric log. Commit only when the human approves.

## Guardrails (deterministic — do not weaken)
Which layer enforces what, because they are not the same layer:
- `.claude/settings.json` **permissions.deny** blocks: reading secrets (`.env*`,
  `*.pem`, keys) and the literal destructive git/delete prefixes. Every `.env*`
  is secret; the non-secret example file is `env.example`, no leading dot.
- `.claude/settings.json` **hooks** register `write_guard.py` for
  `Edit|Write|MultiEdit` — one process, which blocks writing secret files,
  self-modifying governance, editing existing migrations, and committing a
  credential in any field a write can carry.
- **`shell_guard.py` is registered at user level, not by this project**
  (handoff B2). It is what actually blocks `--no-verify`, repointing
  `core.hooksPath`, `git reset --hard` in every `-C`/`-c`/`--git-dir` spelling,
  force pushes, and recursive deletes — and it holds the evaluator's shell
  allowlist. On a machine without that user-level guard, none of those are
  blocked. See `docs/DECISIONS.md` for the put-back trigger.
- `.githooks/pre-commit` runs `npm run verify` when the project defines one, and
  fails the commit if `package.json` exists without one. It is fast local drift
  control, not a trust boundary: a local hook is bypassable, so CI is the backstop.
- `.claude/`, `.githooks/`, and this file change only via the human.

Safe operations are deliberately NOT blocked: `git reset HEAD file`,
`rm file.txt`, `Remove-Item file.txt`, reading and writing `env.example`.
Over-blocking is a framework defect, not caution. If a hook blocks you, fix the
approach — never work around it.
