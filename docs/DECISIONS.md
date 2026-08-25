# DECISIONS

(Important decisions, approved exceptions, RCA notes. Date each entry.
Inclusion test: record it only if a future session would reasonably ask
"why did we do this?" — otherwise don't.)

---

## 2026-08-24 — The shell guard is registered once, at user level, not per project (handoff B2)

Context: `scripts/hooks/shell_guard.py` and `~/.claude/hooks/shell_guard.py` were
byte-identical (sha256 `d50bafc230245794…`), and both were registered for
`Bash|PowerShell`. Every shell call in a template-derived repo therefore paid for
**two** Python processes running the same parser over the same string.

**Measured.** One guard invocation: **66 ms median** on Bash (42 ms of that is
bare `python -c pass` startup, so ~24 ms is the guard). Duplicated, that is
~132 ms per shell call for zero additional protection.

**Done.** Deleted `scripts/hooks/shell_guard.py`, `scripts/hooks/test_shell_guard.py`,
and the project `Bash|PowerShell` registration in `.claude/settings.json`. The
user-level guard covers every repo on this machine, including this template, and
was verified firing from the template working directory — destructive git forms
blocked, `git status` allowed, and the full evaluator allowlist still enforced
(`echo >`, `git log`, `cat docs/PROGRESS.md`, non-allowlisted binaries all
blocked; `npm test` and `git status --porcelain` allowed).

**Scope of the claim — read this before trusting it.** "The user-level guard
protects all repos" is true *of this machine only*. It is a statement about
`~/.claude/settings.json`, not about the template. A checkout of this template
on any other machine now has **no shell guard whatsoever**.

**PUT-BACK TRIGGER.** Restore `scripts/hooks/shell_guard.py`, its test suite, and
the `Bash|PowerShell` registration when **any** of these becomes true:

1. the template must work on a machine without this `~/.claude` configuration
   (another person, another laptop, a fresh OS install, a container, CI);
2. a generated app needs guard coverage that does not depend on the developer's
   personal config;
3. the evaluator is dispatched anywhere the user-level guard is not installed —
   **this is the sharp edge**: the evaluator's shell allowlist lives *inside*
   `shell_guard.py`, so with no guard registered the evaluator keeps `tools: Bash`
   and gains an unrestricted shell. Its read isolation (`evaluator_guard.py`) is
   project-relative and survives; its *shell* isolation does not. A P0 harness
   failure that the Step 0 read probe does **not** detect, because that probe
   only tests the Read path.

Recovery is `git show 4d2c989 -- scripts/hooks/shell_guard.py`; nothing unique
was lost, since the deleted bytes are exactly the surviving user-level copy.

---

## 2026-08-23 — Permission and hook scope: what was changed and what was left alone

Context: the guardrail layer was written for the Bash tool only. On Windows the
PowerShell tool is the primary shell, so every protection was absent on the path
most likely to be used.

**Done.** `bash_guard.py` → `shell_guard.py`, registered `Bash|PowerShell`, made
shell-aware (PowerShell separators, alias canonicalization so `gc`/`type`/`rm`
cannot slip a rule, quote-stripping so a literal in a commit message cannot fake
a flag). PowerShell mirrors added to `deny`/`ask`/`allow`. Covered by 61
block/allow cases in both directions.

**`Remove-Item:*` denied broadly, not by flag.** Flag-order matching is
unreliable (`-Recurse -Force` in either order, abbreviated as `-rec`). The
built-in checks already deny system-path and wildcard targets; the broad rule
closes the rest. Alias canonicalization means it also catches `rm`, `del`, `ri`.

### Rejected

**No `defaultMode` in this file.** Per the docs, `"auto"` in project
`.claude/settings.json` does not take effect and setting any value here
overrides the user's own preference. With the key absent, the user-level
`~/.claude/settings.json` value applies (and the built-in default is auto on
Pro/Max/Team). Do not re-add it — a project-level `"auto"` is a documented no-op
that silently forces the built-in default instead.

**No `git commit` allow rule.** An allow rule resolves *before* the classifier,
which would skip the review that reads global `CLAUDE.md` — where "NEVER commit
or push unless I ask" actually lives. With no rule, commits route through the
auto-mode classifier and that hard stop is checked. Commits run without a
terminal prompt either way; the cost is one background classifier round-trip.
This reverses an earlier draft that added the rule.

**No comment inside `settings.json`.** JSON has no comment syntax, and this file
is the security layer — a parse failure would silently drop every deny rule and
hook. The note that belongs there lives in the README instead: in auto mode,
broad exec allow rules (package-manager run commands, wildcarded interpreters
like `node:*`) are dropped by design and route to the classifier; narrow rules
stay in effect. The full allow list is kept regardless, because it applies when
cycling to manual/acceptEdits mid-session.

**`/interview` stays project-level.** It writes relative `docs/` paths and
assumes the scaffold exists; the flow is scaffold-first by design
(`/new-app` → `/interview`). A global copy would run against no `docs/`.

**`engineering-conventions` stays project-level.** It is stack-specific
(Supabase/Postgres, `npm run verify`) and should version with the template, not
with the machine. Its three rules that duplicated global `CLAUDE.md` — UTC,
`archived_at`, falsifiable verification — were replaced with a pointer so they
have one home.

### Deferred

Migrating `/interview` from command to skill format, which would let it declare
`allowed-tools`. No forcing evidence yet.
