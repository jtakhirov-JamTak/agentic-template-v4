# Project Rules — Plan → Build → Evaluate

Global `~/.claude/CLAUDE.md` applies. Its hard stops (commit/push only when asked,
show before delete/overwrite, secrets only in `.env`, verification must be able
to fail) are not repeated here and are never overridden.

## Workflow
1. **PLAN** — for a new app or any feature that doesn't fit in one sentence:
   enter Plan Mode (Shift+Tab twice) and run `/interview`. Output is
   `docs/SPEC.md` — the single source of truth for what to build.
2. **BUILD** — in the main session, one SPEC feature at a time, in SPEC order.
   Read `docs/SPEC.md` and `docs/PROGRESS.md` before touching anything. If
   implementation proves SPEC.md materially wrong: stop, amend SPEC.md, then
   resume — never silently diverge. Unrelated discoveries go to
   `docs/BACKLOG.md`; stay on the current intent.
3. **EVALUATE** — dispatch the `evaluator` subagent after: the first vertical
   slice · any feature touching auth, authorization/RLS, money/billing, or
   migrations · before release. Its task prompt contains ONLY: which SPEC.md
   features are in scope and how to run the app. Never describe how anything
   was built. Save its report verbatim to `docs/evals/eval-NN.md`.
   P0 → stop, tell the human. P1 → fix before continuing. P2 → BACKLOG.md.

## Build rules
- Load the `engineering-conventions` skill before schema, auth, money, or
  migration work.
- Self-test with the falsifiability check before claiming done (see skill).
- Session end: `npm run verify` green, or work stashed with the reason in
  PROGRESS.md. Always append to `docs/PROGRESS.md`: date · what was done ·
  state (verify GREEN / STASHED + why) · next step specific enough for a cold
  session. Commit only when the human approves.

## Guardrails (deterministic — do not weaken)
- `.claude/settings.json` permissions + hooks block: secrets read/write,
  editing existing migrations, `--no-verify`, repointing git hooks, destructive
  git commands. If a hook blocks you, fix the approach — never work around it.
- `.githooks/pre-commit` runs `npm run verify`; red code cannot be committed.
- `.claude/`, `.githooks/`, and this file change only via the human.
