# Agentic App-Building Template (v4)

Plan → Build → Evaluate. One human, one main session, one evaluator subagent,
and a deterministic enforcement layer. v2's five-role pipeline is deleted; its
guardrails are kept and hardened.

## v4 changes (from v2)
1. **Planning moved to the main session.** `/interview` (Plan Mode) replaces the
   discovery + architect subagents — subagents can't interview you. Output is a
   single `docs/SPEC.md` (merges INTAKE + SPEC + ARCHITECTURE).
2. **Building moved to the main session.** No orchestrator, no builder subagent,
   no contracts, no two-tier approval, no eval counter. You approve twice: SPEC
   and release. Rules live in `CLAUDE.md` (35 lines).
3. **One evaluator, triggered by risk**: first slice · auth/RLS/money/migration
   features · pre-release. Evidence-only PASS/FAIL, never proposes fixes
   (reduces false rejections). It runs in the real working tree — see residual
   gap 1 for why, and what that costs.
4. **Hooks fixed for Windows.** Exec form (`"command": "python", "args": [...]`)
   — no shell, no `python3`-not-found silent death. SubagentStart plain-stdout
   injection deleted (it never reached the subagent; only JSON
   `additionalContext` does).
5. **Wider destructive coverage, both shells, fewer prompts**:
   `permissions.deny` for `git reset`, `git clean`, `git checkout --`,
   force-push, `rm -rf`, and `Remove-Item` — each mirrored for the PowerShell
   tool, which previously had zero coverage. Regex belt in `shell_guard` for
   chained forms. An `allow` list covers routine dev commands (npm/npx/node,
   git status/diff/add, supabase, localhost curl) in both shells. The only
   `ask` gate is `git push` — the moment work leaves the machine. Commits carry
   no allow rule on purpose, so they route through the auto-mode classifier
   that reads global `CLAUDE.md` ("never commit unless asked"); they still run
   without a terminal prompt. Deny always beats allow, so the guardrails hold
   in every mode.
6. **No `defaultMode` in project settings.** A project-level `"auto"` is a
   documented no-op, and setting any value here overrides your user-level
   preference. With the key absent, `~/.claude/settings.json` decides. In auto
   mode, broad exec allow rules (package-manager run commands, wildcarded
   interpreters like `node:*`) are dropped by design and route to the
   classifier; narrow rules stay in effect. The full allow list is kept anyway
   — it applies when cycling to manual/acceptEdits mid-session.
7. **Secrets scanner** now catches env-style `SUPABASE_SERVICE_ROLE_KEY=eyJ…`
   and `sb_secret_…` keys.
8. **`/interview` is a three-phase pipeline** — DISCOVER (elicitation only;
   no solution commitments) → non-blocking problem summary written to SPEC.md
   → DESIGN (no-build test, alternatives only when consequential, aggressive
   delete with the 10% rule, cost-to-reverse spikes) → direction gate
   (decision to DECISIONS.md) → SPECIFY (8-section spec with measurement
   method and a 3-item pre-mortem) → spec approval. The reusable operators
   also ship as a global `solutioning` skill in `global/skills/`.

## Layer map
| Layer | Location | Job |
|---|---|---|
| Deterministic guardrails | `.claude/settings.json`, `scripts/hooks/`, `.githooks/`, CI | mechanically enforced workflow guardrails — they stop drift, not a determined bypass |
| Workflow rules | `CLAUDE.md` | plan → build → evaluate, session hygiene |
| Evaluator | `.claude/agents/evaluator.md` | independent, isolated verification |
| Procedures | `.claude/skills/engineering-conventions/` | schema/auth/money/test rules, on demand |
| Project state | `docs/` | SPEC, PROGRESS, BACKLOG, DECISIONS, FIX_LOG, evals |

## Setup (per new app)

This repo is a GitHub template repository. The `/new-app` command in
`~/.claude/commands/` runs the whole sequence; do it by hand as follows if you
prefer. Run from your dev root, never from the home directory itself — a session
started there loads no project `CLAUDE.md`.

1. `gh repo create <name> --template jtakhirov-JamTak/agentic-template-v4 --private --clone`
2. `cd <name>` ; `git config core.hooksPath .githooks`
3. `git update-index --chmod=+x .githooks/pre-commit` then commit the mode change
   (Windows can't set the executable bit; CI/WSL/macOS skip non-executable hooks).
   Confirm with `git ls-files -s .githooks/pre-commit` — mode should be `100755`.
4. Confirm `python --version` works in the shell Claude Code uses. If only `py`
   resolves, change `"command": "python"` to `"command": "py"` in
   `.claude/settings.json` — all three hook entries.
5. Start `claude`. Session mode comes from your user settings (auto by default),
   not from this repo; Shift+Tab cycles modes.
   For planning: Shift+Tab into Plan Mode, run `/interview <app idea>`.
6. Fresh session → build feature 1 → evaluator pass → continue per CLAUDE.md.

## Global install (optional, one-time)
- Copy `global/skills/solutioning/` to `~/.claude/skills/solutioning/` — the
  decision framework for non-app questions (feature-sized decisions, process
  changes, retros).
- Add two lines to `~/.claude/CLAUDE.md`:
  "Before optimizing or building anything non-trivial, ask what should not
  exist and try deleting it; name what would guarantee failure before proposing
  how to succeed. Full protocol: `/interview` for new apps, the `solutioning`
  skill otherwise."
- Commit `~/.claude` after (it is a git repo).

## Verify the guardrails before trusting them (5 minutes)

Run the shell checks through **both** tools — `shell_guard.py` is registered for
`Bash|PowerShell`, and PowerShell is the path that had no coverage before v4.

> **Where the shell guard lives (handoff B2).** This template no longer ships
> `scripts/hooks/shell_guard.py`. On the maintainer machine the identical guard
> is registered once at **user level** in `~/.claude/settings.json`, which covers
> every repo, so a project-level copy was pure duplication — two processes doing
> the same work on every shell call. **Put-back trigger: if this template has to
> work on a machine that does not have that `~/.claude` configuration, restore
> the project-relative guard and its `Bash|PowerShell` registration before
> relying on any shell claim below.** Without one of the two, none of the shell
> bullets in this section hold, and the evaluator loses its shell allowlist.
> See `docs/DECISIONS.md`.

- `/hooks` shows the project PreToolUse hook matching `Edit|Write|MultiEdit`
  (plus the evaluator's own `Read|Grep|Glob` hook from its frontmatter, and the
  user-level `Bash|PowerShell` guard if this machine has one);
  `/permissions` shows deny/ask rules for both tools.
- Ask Claude to read `.env` → denied. Write a fake `AKIA…` key → blocked.
  Write `SUPABASE_SERVICE_ROLE_KEY=eyJ<25 chars>` → blocked.
  Read `env.example` → allowed; `.env.example` → **denied**. Every `.env*` is
  secret with no exception, and the non-secret example file carries no leading
  dot (handoff B3). `.gitignore`, `shell_guard.py` and `write_guard.py` all
  agree on that; they used to disagree.
- Edit a file in `supabase/migrations/` → blocked. Edit `CLAUDE.md` → blocked.
- `npm test` runs without a prompt. `git push` → asks you, in either shell.
- Blocked in **both** shells: `git commit --no-verify` and its `-n` shorthand ·
  `git config core.hooksPath x` · `git reset --hard` (even chained after
  `npm test &&` in bash or `npm test ;` in PowerShell) · `git restore .`
- Recursive delete, every spelling: `rm -rf`, `rm -fr`, `rm -r -f`, `rm -R`,
  `rm --recursive`, and any of them after a `;` or `&&`. The deny rules catch
  only the literal `rm -rf ` prefix; the hook parses flags, so arrangement and
  position do not matter. `rm file.txt` and `Remove-Item file.txt` stay allowed
  — ordinary single-file deletion is not the protected capability (handoff B4).
- `git reset HEAD file` (unstage) is **allowed**; `git reset --hard` is blocked.
  The deny list names only the destructive form, because a prefix matcher cannot
  see the `-C` / `-c` / `--git-dir` spellings anyway — the hook is what covers
  those, and a deny rule that pretends otherwise is just an over-block (B4).
- Force push, every spelling: `--force`, `-f`, `--force-with-lease`,
  `--force-if-includes`, and `git push origin +main`. Ordinary
  `git push origin main` is allowed here and gated by the `ask` rule instead.
- PowerShell specifically: `Get-Content .env` → blocked, and so are its aliases
  `gc` and `type` (commands are canonicalized before matching) ·
  `Set-Content supabase/migrations/001.sql` → blocked ·
  recursive `Remove-Item` → denied, single-file `Remove-Item` → allowed.
- With a failing `npm run verify`, `git commit` → pre-commit rejects.
- Spawn the evaluator; have it try `echo x > src/a.ts` (bash) or
  `Set-Content src/a.ts 'x'` (PowerShell) → allowlist blocks both. **This one
  depends on a shell guard being registered somewhere** (see the B2 note above):
  the evaluator allowlist lives inside `shell_guard.py`, so on a machine with no
  user-level guard and no project copy, the evaluator has no shell containment
  at all and this check silently passes the wrong way.

The `shell_guard` rules are covered by a block/allow case table in both
directions — a rule that stops firing and a rule that over-matches each show up
as a failure. Re-run it after editing any pattern. The suite lives beside the
guard: `~/.claude/hooks/test_shell_guard.py` on this machine.

## Version-sensitive (check once on your Claude Code version)
Verified live 2026-08-24 on this machine; re-check after a Claude Code upgrade.
- Per-agent `hooks:` in subagent frontmatter fire, and `${CLAUDE_PROJECT_DIR}`
  IS expanded in the hook `command`. This is what scopes `evaluator_guard.py` to
  the evaluator and keeps ordinary sessions free of any hook on the Read path.
  Use the `${CLAUDE_PROJECT_DIR}` form, never a bare relative path — a relative
  path resolves against the hook process's cwd, which is not guaranteed to be
  the project root.
- `agent_type` in hook input inside subagents. It powers both the evaluator
  shell allowlist and the read guard. If absent, neither engages — and there is
  no longer a worktree behind them (see below).

## WORKSPACE TRUST GATES THE EVALUATOR'S READ ISOLATION
`.claude/agents/evaluator.md` is a PROJECT-level definition, and Claude Code
**skips a project-level subagent's frontmatter hooks until the folder is
trusted**. Until then the evaluator still runs — with no read guard at all. It
fails silent: the only signal is a line in the debug log.

Verified in both directions. Untrusted:

```
[ERROR] Skipping frontmatter hooks for main-thread agent 'evaluator': the folder
its definition file came from is not trusted (source: projectSettings).
```

and the evaluator read `PROGRESS.md`, `session-context.md` and a prior eval
without objection. Trust-free source (`~/.claude/agents/`): all three blocked.

So: **accept the trust dialog on first launch in a new app** — `/new-app`
already tells you to, and this is a second reason it matters. Note that `-p`
/ non-interactive runs skip the trust dialog entirely, so an evaluator dispatched
from CI has no read isolation unless the folder was trusted beforehand. That
headless gap is known and not solved: the probe below makes it loud, it does not
make the hooks run.

**The evaluator now detects this itself.** Its Step 0 is to Read
`.claude/evaluator-hook-probe.txt`, a committed sentinel holding no project
information. Blocked → the guard is alive, continue. Succeeds → **P0 HARNESS
FAILURE**, abort without grading. A dead guard and a live one are otherwise
indistinguishable from inside the evaluator, which is how the untrusted run
produced a confident report built on contaminated context. Keep that file
committed and keep it meaningless: a missing sentinel returns "does not exist",
which reads like a block and would make the probe lie.

- Hook reference: https://code.claude.com/docs/en/hooks
- Subagent reference: https://code.claude.com/docs/en/sub-agents

## Residual gaps (honest list)
1. The evaluator runs in the REAL working tree. `isolation: worktree` was
   removed deliberately: a worktree is branched from the default branch, so the
   evaluator could not see uncommitted work and graded a tree that never
   existed. The trade is that nothing sandboxes it any more — the shell
   allowlist, the read guard, and the before/after `git status --porcelain`
   comparison are the whole containment, and the allowlist is still bypassable
   via `node -e` / `npm run <script>`. Hardest guarantee = container/read-only
   mount.
2. Hooks fail open on their own bugs (by design, except allowlist matches).
   They stop drift, not a determined bypass.
3. `shell_guard` sees a shell COMMAND STRING and treats all of it as commands,
   so a heredoc writing a file whose text contains a blocked command is blocked.
   Author files with Write/Edit rather than heredocs.
4. Stack assumptions: `npm run verify`, Supabase/Postgres migration dirs. Edit
   `write_guard.py` / `shell_guard.py` / `.githooks/pre-commit` for other stacks.
4. Governance lock: the agent can't edit `.claude/`, `.githooks/`, `CLAUDE.md`.
   You edit those manually — that's the point.

## Put-back triggers (add complexity only on evidence from a real build)
- Sessions keep ending with a dirty tree → restore the v2 Stop hook
  (`stop_guard.py` in v2 history).
- Evaluator keeps finding P1s in "ordinary" features → evaluate every feature.
- SPEC drift bites twice → per-feature mini-plan in Plan Mode before building
  high-risk features (not a contracts directory).
- Retro is by evidence, not by scaffold: after each shipped app, one build =
  proposal, repeated evidence = template default. No retro step lives in any
  command or CLAUDE.md.
