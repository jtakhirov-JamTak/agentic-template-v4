# FIX_LOG

(Every real defect: dated entry — problem, fix, regression test, where found.
Template-derived apps split: FIX_LOG.md = what the next app from the template
would also hit; APP_FIX_LOG.md = the rest.)

---

## 2026-08-23 — Guard rules were absent on the PowerShell tool entirely

**Problem.** `bash_guard.py` was registered with `"matcher": "Bash"`. On Windows
the PowerShell tool is the primary shell, so every protection in it — the
`--no-verify` block, the `core.hooksPath` block, the migration and `.env` rules,
and the evaluator read-only allowlist — did not run at all on the path most
likely to be used. The `permissions.deny` list had the same gap: `Bash(...)`
rules do not match PowerShell tool calls.

**Fix.** Renamed to `shell_guard.py`, registered `Bash|PowerShell`, and made it
shell-aware: PowerShell separators, alias canonicalization (so `gc`, `type`,
`rm`, `ri` resolve to their cmdlet before matching), and quote-stripping (so a
literal inside a commit message cannot fake a flag). PowerShell mirrors added to
`deny`, `ask`, and `allow` in `.claude/settings.json`.

**Regression test.** `scripts/hooks/test_shell_guard.py`, 61 cases, both
directions. Verified falsifiable: disabling the `core.hooksPath` rule turns it
59/61 red on exactly the two hooksPath cases, and restoring returns 61/61.

**Where found.** Config review of the template against `~/.claude`.

## 2026-08-23 — `.env.example` was blocked from being read

**Problem.** The `.env` rules matched `\.env(\.|$|\s)`, so `.env.example` —
committed on purpose, and explicitly re-included in `.gitignore` — was treated
as a secret file and blocked. Same for `.env.sample` and `.env.template`. This
was pre-existing in `bash_guard.py`, not introduced by the PowerShell work; it
surfaced only because the new test table includes must-ALLOW cases.

**Fix.** `ENVFILE = r"\.env(?!\.example|\.sample|\.template)"`, applied to every
env rule in both shells. `.env`, `.env.local`, and `.env.production` stay
blocked.

**Regression test.** Four cases in `test_shell_guard.py`: `.env.example` and
`.env.sample` must be allowed; `.env.local` and `.env.production` must stay
blocked. The last two are what stop this fix from becoming a hole.

**Where found.** First run of the new `shell_guard` test table — a
block-only test suite would not have caught it.
