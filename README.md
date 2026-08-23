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
   (reduces false rejections), native `isolation: worktree` replaces
   `eval-worktree.sh`.
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

- `/hooks` shows the three PreToolUse hooks, the last matching `Bash|PowerShell`;
  `/permissions` shows deny/ask rules for both tools.
- Ask Claude to read `.env` → denied. Write a fake `AKIA…` key → blocked.
  Write `SUPABASE_SERVICE_ROLE_KEY=eyJ<25 chars>` → blocked.
  Read `.env.example` → allowed (committed on purpose; `.env.local` still denied).
- Edit a file in `supabase/migrations/` → blocked. Edit `CLAUDE.md` → blocked.
- `npm test` runs without a prompt. `git push` → asks you, in either shell.
- Blocked in **both** shells: `git commit --no-verify` and its `-n` shorthand ·
  `git config core.hooksPath x` · `git reset --hard` (even chained after
  `npm test &&` in bash or `npm test ;` in PowerShell) · `git restore .`
- Recursive delete, every spelling: `rm -rf`, `rm -fr`, `rm -r -f`, `rm -R`,
  `rm --recursive`, and any of them after a `;` or `&&`. The deny rules catch
  only the literal `rm -rf ` prefix; the hook parses flags, so arrangement and
  position do not matter. `rm file.txt` stays allowed.
- Force push, every spelling: `--force`, `-f`, `--force-with-lease`,
  `--force-if-includes`, and `git push origin +main`. Ordinary
  `git push origin main` is allowed here and gated by the `ask` rule instead.
- PowerShell specifically: `Get-Content .env` → blocked, and so are its aliases
  `gc` and `type` (commands are canonicalized before matching) ·
  `Set-Content supabase/migrations/001.sql` → blocked ·
  recursive `Remove-Item` → denied.
- With a failing `npm run verify`, `git commit` → pre-commit rejects.
- Spawn the evaluator; have it try `echo x > src/a.ts` (bash) or
  `Set-Content src/a.ts 'x'` (PowerShell) → allowlist blocks both.

The `shell_guard` rules are covered by a block/allow case table in both
directions — a rule that stops firing and a rule that over-matches each show up
as a failure. Re-run it after editing any pattern.

## Version-sensitive (check once on your Claude Code version)
- `isolation: worktree` in agent frontmatter — if unsupported, fall back to a
  manual `git worktree add --detach ../<app>-eval HEAD` and pass the path in the
  evaluator's task prompt.
- `agent_type` in Bash hook input inside subagents (powers the evaluator
  allowlist). If absent, the worktree is the only isolation.
- Hook reference: https://code.claude.com/docs/en/hooks

## Residual gaps (honest list)
1. Evaluator allowlist is bypassable via `node -e` / `npm run <script>`; the
   worktree is the real isolation. Hardest guarantee = container/read-only mount.
2. Hooks fail open on their own bugs (by design, except allowlist matches).
   They stop drift, not a determined bypass.
3. Stack assumptions: `npm run verify`, Supabase/Postgres migration dirs. Edit
   `protect_paths.py` / `shell_guard.py` / `.githooks/pre-commit` for other stacks.
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
