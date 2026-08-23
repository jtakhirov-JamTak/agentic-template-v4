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
5. **Wider destructive-git coverage, fewer prompts**: `permissions.deny` for
   `git reset`, `git clean`, `git checkout --`, force-push, `rm -rf`; regex belt
   in bash_guard for chained forms. Default mode is `acceptEdits` with an
   `allow` list for routine dev commands (npm/npx/node, git status/diff/add,
   supabase, localhost curl), so build sessions run prompt-free. The only
   `ask` gate is `git push` — the moment work leaves the machine. Commits are
   governed behaviorally (CLAUDE.md + global "only when I ask") and
   quality-gated by pre-commit verify, so they don't prompt. Deny always beats
   allow, so the guardrails hold in every mode.
6. **Secrets scanner** now catches env-style `SUPABASE_SERVICE_ROLE_KEY=eyJ…`
   and `sb_secret_…` keys.
7. **`/interview` is a three-phase pipeline** — DISCOVER (elicitation only;
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
1. Copy template → new repo → `git init` → `git config core.hooksPath .githooks`.
2. `git update-index --chmod=+x .githooks/pre-commit` after the first `git add`
   (Windows can't set the executable bit; CI/WSL/macOS skip non-executable hooks).
3. Confirm `python --version` works in the shell Claude Code uses. If only `py`
   resolves, change `"command": "python"` to `"command": "py"` in settings.json.
4. Start `claude` (sessions open in acceptEdits; Shift+Tab to cycle modes).
   For planning: Shift+Tab into Plan Mode, run `/interview <app idea>`.
5. Fresh session → build feature 1 → evaluator pass → continue per CLAUDE.md.

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
- `/hooks` shows the three PreToolUse hooks; `/permissions` shows deny/ask rules.
- Ask Claude to read `.env` → denied. Write a fake `AKIA…` key → blocked.
  Write `SUPABASE_SERVICE_ROLE_KEY=eyJ<25 chars>` → blocked.
- Edit a file in `supabase/migrations/` → blocked. Edit `CLAUDE.md` → blocked.
- `npm test` runs without a prompt. `git push` → asks you.
  `git commit --no-verify` → blocked.
  `git reset --hard` → blocked (even chained after `npm test &&`).
- With a failing `npm run verify`, `git commit` → pre-commit rejects.
- Spawn the evaluator; have it try `echo x > src/a.ts` → allowlist blocks it.

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
   `protect_paths.py` / `bash_guard.py` / `.githooks/pre-commit` for other stacks.
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
