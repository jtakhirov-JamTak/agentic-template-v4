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
- Session end: `npm run verify` green, or work stashed with the reason in
  PROGRESS.md. Always append to `docs/PROGRESS.md`: date · what was done ·
  state (verify GREEN / STASHED + why) · next step specific enough for a cold
  session. Commit only when the human approves.

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

Safe operations are deliberately NOT blocked: `git reset HEAD file`,
`rm file.txt`, `Remove-Item file.txt`, reading and writing `env.example`.
Over-blocking is a framework defect, not caution. If a hook blocks you, fix the
approach — never work around it.
- `.githooks/pre-commit` runs `npm run verify`; red code cannot be committed.
- `.claude/`, `.githooks/`, and this file change only via the human.
