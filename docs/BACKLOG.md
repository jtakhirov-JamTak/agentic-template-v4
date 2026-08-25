# BACKLOG

(Deferred work, production issues, non-blocking findings. One line per item.)

## Found during the template P0 pass (2026-08-25), not fixed there

- **No app was ever scaffolded via `new-app.ps1`** — all four predate it (Feb-Jun
  2026) and shipped with no pre-commit, no `hooksPath`, no `write_guard`, no
  evaluator. `pure-eq` (real users) is being adopted manually in a separate session.
  The other three are unprotected; install pre-commit only on those still receiving
  commits.

## Resolved in Session B (2026-08-24)

- **[B1 — RESOLVED] `format-after-edit.ps1` deleted**, with its PostToolUse
  registration. Measured (interleaved, n=10): **528 ms median on every Edit/Write**
  even for a file it declines to format, 853 ms in a Prettier project — against a
  253 ms bare-PowerShell floor. Formatting now happens only at the verification /
  pre-commit boundary. Proved live at the time in a Prettier-using project whose
  `npm run verify` begins with `format:check`: green on a clean tree, and **red** on a
  deliberately unformatted file — the failing input that makes the check mean
  something. **That project has since been retired and deleted**, so the evidence is
  no longer independently re-runnable; re-prove it in whichever app adopts Prettier
  next rather than treating this line as standing proof.
- **[B2 — RESOLVED] Template `shell_guard.py` + `test_shell_guard.py` + the project
  `Bash|PowerShell` registration deleted.** Both files were byte-identical to the
  user-level copy (sha256 `d50bafc2…`, `5bffed9e…`), so a template repo paid two
  Python processes per shell call for one guard's worth of protection. Put-back
  trigger recorded in `docs/DECISIONS.md`, in `README.md`, and in `evaluator.md`.
- **[B3 — RESOLVED] Standardised on `env.example`.** The `.example/.sample/.template`
  carve-out is gone from `shell_guard.py`, so all four layers now agree that every
  `.env*` is secret: `.gitignore` (`!.env.example` negation removed), `permissions.deny`,
  `shell_guard.py`, `write_guard.py`. Proven with `git check-ignore` and both suites.
- **[B4 — RESOLVED] Over-blocking narrowed.** `Bash|PowerShell(git reset:*)` →
  `(git reset --hard:*)`; `PowerShell(Remove-Item:*)` → `(Remove-Item -Recurse:*)`;
  redundant `Read(./.env{,.*})` variants dropped (`**/.env{,.*}` subsumes them).
  `git reset HEAD file` and single-file deletion now pass; the destructive forms still
  block, including the flag orders and aliases a prefix deny rule structurally cannot
  see. Both directions asserted, and both narrowings carry a named-set mutation.
- **[B5 — SKIPPED ON MEASUREMENT, as the handoff instructs.]** `shell_guard.py` costs
  **+33 ms over the Python floor (85 ms wall)** per shell call. The handoff's own
  threshold is ~100 ms, so `if`-filtering Bash is not justified: it would trade real
  coverage for a saving below the bar. PowerShell stays unfiltered regardless.

## Found during Session B, not fixed there

- **[B4-class — FOUND AND FIXED 2026-08-24] `git restore --staged` on any dotted path
  was blocked, and destructive single-file restores were allowed.** Fixed by replacing
  the regex with a token-based `check_git_restore()` keyed on which tree the command
  writes: `--staged`/`-S` without `--worktree` is allowed for any path, everything
  else blocks (including the bare default, which IS `--worktree`). Token-based because
  `GIT_RULES` run with `re.IGNORECASE` and cannot tell `-S` (staged) from `-s`
  (`--source`). 18 regression cases both directions + 2 named-set mutations; verified
  live through the registered hook. Full entry in `~/.claude/FIX_LOG.md`. Original
  finding below.

  The rule
  `git\s+restore\s+(--staged\s+|--worktree\s+)*[.*]` uses a character CLASS, so `[.*]`
  matches a literal `.` — meaning `git restore --staged .claude/exceptions.md`, which
  unstages exactly one file and cannot lose working-tree work, is read as
  `git restore .`. Hit for real while unstaging a file during the B3 migration. Any
  path beginning with a dot is affected: `.gitignore`, `.github/...`, `.env`-adjacent
  paths, every dotfile. The intent is to catch whole-tree restores (`.` or `*` as the
  WHOLE pathspec), so the fix is an anchored alternation such as
  `(\.|\*)(\s|$)` rather than a character class. **Not fixed here**: Session B's guard
  scope was closed and this needs its own ALLOW/BLOCK pair plus a mutation. Workaround
  in the meantime is `git reset HEAD <file>`, which B4 deliberately re-allowed.

- **[B4 — RESOLVED 2026-08-24, applied by the user] user-level `Read` deny narrowed to
  the full secret class.** `~/.claude/settings.json` now carries exactly
  `Read(~/**/.env)` + `Read(~/**/.env.*)`, replacing the four narrow variants. The
  agent could not make this edit itself — the auto-mode classifier refuses an agent
  rewriting its own permission deny list, which is the right call even for a change
  that only broadens coverage — so the user applied it by hand. Verified through the
  live permission layer, not just by reading the file: `.env`, `.env.local`,
  `.env.development`, `.env.staging` and `.env.example` all return "denied by your
  permission settings", while `env.example` reads normally. The two non-existent paths
  (`.env.development`, `.env.staging`) returning *denied* rather than *not found* is
  what proves the rule matched rather than the file merely being absent. B3's "every
  `.env*` is secret" now holds globally, not just inside a template-derived project.

- **[B3 migration — DONE 2026-08-24, committed and pushed in all four app repos]
  `.env.example` → `env.example` + all references updated.** Applied mechanically
  across `pure-eq`, `the-leaf-v2`, `you-inc` and `PurePath`. Every rename recorded by
  git as `R100` (content byte-identical); every edit byte-preserving apart from the
  filename itself. Verified afterwards: zero tracked references to the dotted name in
  any repo, and each renamed file is genuinely usable — shell read/write allowed and
  `write_guard` accepts its ACTUAL contents (they carry placeholder credentials, so
  this was a real risk of swapping one over-block for another), while a real
  `sk_live_` key in the same file still blocks.

  Read-only compatibility scan run 2026-08-24 across all tracked files in all four
  repos (`git ls-files` + in-process grep; a shell `grep .env.example` is itself
  blocked by the guard). Result: **zero runtime file access, zero `package.json`
  scripts, zero CI/deploy references.** Two of the four repos do have
  `.github/workflows/ci.yml`, and neither names the file — so that zero is a
  real negative, not a vacuous one. Every surviving reference is prose, a comment, a
  `.gitignore` negation, or a Claude rule. The rename was mechanical in all four.

  Per repo — refs beyond the file itself:
  - `pure-eq` (4): `.gitignore:71` negation · `README.md:8` (`cp .env.example .env.local`)
    · `docs/Engineering_Playbook.txt:290,875`
  - `the-leaf-v2` (0) and `PurePath` (0): the file only, nothing referenced it
  - `you-inc` (6): `.gitignore:71` · `README.md:8` ·
    `docs/Engineering_Playbook.txt:290,875` · **`CLAUDE.md:46,118`**

  **The one thing that was not just a rename:** `you-inc/CLAUDE.md:118` instructed the
  agent to *"edit `.env.example` instead"* of touching `.env.local`. With
  `Read(~/**/.env.*)` live that instruction cannot be followed — not a code
  regression, but a documented agent workflow that breaks. It was updated to
  `env.example` in the same commit as the rename, along with `CLAUDE.md:46`.

- **[B2 consequence — MITIGATED 2026-08-25] The evaluator now detects a missing shell
  guard itself.** Step 0b runs `python -c "print('evaluator shell probe')"`, which the
  evaluator allowlist rejects: blocked means shell containment is live, and if it
  actually prints, the evaluator aborts with **P0 HARNESS FAILURE** instead of grading.
  The command is inert by construction — if the guard is dead and it does run, it
  prints one line and touches no file, Git state, environment or network. That matters
  because the wording it replaced told the evaluator to probe with
  `echo x > /tmp/probe`, which WRITES A FILE when the guard is dead, i.e. causes the
  exact mutation the evaluator is forbidden to make; a contract test now blocks that
  line from returning. Proven both directions: `test_shell_guard.py` asserts the probe
  blocks for the evaluator and stays inert for every other agent, and the
  `eval-shell-allowlist-off` mutation turns exactly those cases red — that is the
  SUCCEEDS branch. Four contract assertions in `test_evaluator_guard.py` pin the
  instruction, each verified to fail when `evaluator.md` is broken in its specific way.
  **Still OPEN underneath:** the probe reports the failure, it does not prevent it, and
  it covers only the evaluator — an ordinary session on a machine with no user-level
  guard still has no shell containment and nothing to notice it. The put-back trigger
  in `docs/DECISIONS.md` remains the real fix.
- **[B2 consequence] Nothing asserts that a shell guard is registered anywhere.**
  `test_evaluator_guard.py`'s contract checks cover `evaluator.md` frontmatter only,
  and no suite ever asserted the settings-level `Bash|PowerShell` registration. Now
  that the guard lives outside the repo, a template checkout can lose shell protection
  entirely — including the evaluator's allowlist — with every test still green. The
  Step 0 read probe does not catch it, because it only exercises the Read path. A
  matching shell probe (`echo x > /tmp/probe` must block) is the obvious fix; the
  evaluator prompt now instructs it by hand, which is weaker than a test.
- **[B7 measurement] `statusline.ps1` costs 622 ms median per render** (+369 ms over
  the bare-PowerShell floor), the single most expensive custom process measured. It is
  per-turn, not per-tool-call, so it does not block tool execution. **Not changed** —
  the handoff says measure only, and no change should follow from theory. If it is ever
  addressed, the fix is the interpreter, not the script logic: 253 ms of it is
  PowerShell startup that no rewrite of the script can remove.
- **[B6 NOT MEASURED] `effortLevel` medium-vs-high was not practical to test here.**
  It needs two comparable real features built end to end, with retries, evaluator P0/P1
  counts and rework tracked across both — not something this session could produce
  without fabricating the comparison. `effortLevel` is unchanged at `high`.

## Found during Session A (handoff v2.2), deliberately not fixed there
- **[C4/C5] `.githooks/pre-commit` is mode `100644` at template source**, so every
  scaffold repairs it with `git update-index --chmod=+x` and an automatic commit.
- **[C5] `/new-app` still creates up to two automatic commits** (the chmod commit, and
  the `py`-launcher commit when `python` is missing). Invoking `/new-app` should not
  imply authorisation to commit.
- **[C7] "red code cannot be committed" is still claimed** in `.githooks/pre-commit`'s
  comment and in `CLAUDE.md`. A local hook is not an independent trust boundary.
- **[A3 — RESOLVED 2026-08-24, verified by live dispatch] Frontmatter hooks fire and
  `${CLAUDE_PROJECT_DIR}` expands.** Registration changed from a bare relative path to
  the `${CLAUDE_PROJECT_DIR}` form and proven live. See `docs/FIX_LOG.md`.
- **[A3 — MITIGATED 2026-08-24] Workspace trust silently disables the evaluator's read
  isolation.** A project-level subagent's frontmatter hooks are skipped until the folder
  is trusted; the evaluator then runs with NO read guard. Now self-detecting: the Step 0
  probe of `.claude/evaluator-hook-probe.txt` turns this from an invisible failure into
  a P0 HARNESS FAILURE abort. The sentinel is used instead of `PROGRESS.md` precisely
  because the probe only succeeds when the guard is dead, and a real file would
  contaminate the evaluator at that moment. Still OPEN underneath: the probe reports the
  failure, it does not prevent it.
- **[A3 — OPEN, headless/CI] Project-level frontmatter hooks cannot be assumed active
  under `claude -p`.** Non-interactive runs skip the trust dialog entirely, so a
  CI-dispatched evaluator has no read isolation unless the folder was trusted
  beforehand. The probe makes such a run abort loudly rather than emit a clean-looking
  report. A headless trust mechanism is deliberately NOT built yet. Options when it
  matters: pre-seed trust for the checkout, or ship the evaluator definition at user
  level / via `--agents`, where hooks run without trust.
- **[A3 — OPEN, optional] `/new-app` could verify trust explicitly** rather than only
  telling the user to accept the dialog. Its canary already checks that `.env` reads are
  denied; a matching check that the evaluator probe blocks would close the loop.
- **[A3 residual] The evaluator keeps `git diff`**, so `PROGRESS.md` content is still
  reachable through a diff even though the path is blocked for Read and shell. The
  guard narrows the path; it does not close it.
- **`shell_guard` cannot tell file content from commands.** Writing a file via heredoc
  is blocked when the text contains a blocked command — hit for real while authoring the
  guard itself. Correct-but-blunt; use Write/Edit for file authoring. Revisit only if it
  proves costly.
