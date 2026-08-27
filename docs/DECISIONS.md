# DECISIONS

(Important decisions, approved exceptions, RCA notes. Date each entry.
Inclusion test: record it only if a future session would reasonably ask
"why did we do this?" — otherwise don't.)

---

## 2026-08-25 — Governance protection goes in the global guard; the pre-commit claim goes in the docs

**Governance shell-writes are blocked in the user-level guard, not a restored
project copy.** The B2 put-back trigger below was considered and deliberately not
fired: restoring `scripts/hooks/shell_guard.py` would reinstate ~132 ms per shell
call of double-guard cost, measured in B2, to buy protection on machines that do not
exist yet. `check_governance()` went into `~/.claude/hooks/shell_guard.py` instead,
scoped to governance-path mutation only. **The cost is stated rather than hidden:**
this protection is machine-local, so a checkout elsewhere has the write-tool half
(`write_guard.py`, which ships) and not the shell half. `CLAUDE.md` and `README.md`
now separate those two reaches instead of presenting one enforcement story. **Put
back the project copy** under the existing B2 triggers — they are unchanged by this.

**`.githooks/pre-commit` stays unwired in this clone; only the claim changed.**
Wiring it here would not materially change protection: this template has no
`package.json`, so the hook allows every commit by design, and `new-app.ps1` already
wires and readback-asserts it for the apps that do have one. Adding
`git config core.hooksPath .githooks` to this clone would have bought nothing and
added a claim to keep true. A shell-guard exemption for the wiring command was
rejected outright: it would put a hole in a rule that currently has none, to save
the human one command they run once per clone. Demoted from P0 on that basis — the
false-green risk was in the documentation, and the documentation is what changed.

---

## 2026-08-25 — Template P0 pass: routing, build loop, context ownership, truthfulness

One session, one intent: reduce interruptions and remove claims the framework cannot
support. Grouped rather than split because they were decided together.

**Template-maintenance sessions pay five manual file copies.** `write_guard.py` locks
`.claude/`, `.githooks/` and `CLAUDE.md` (`GOVERNANCE`, line 30), so a session whose
whole purpose is editing the framework hands those files to the human instead of
writing them. This session staged five complete files plus one PowerShell script that
copies them and hash-compares each. Accepted: the framework-freeze rule makes these
sessions rare, and the alternative — disarming the guard for the duration — is the
agent editing its own governance. **Put-back trigger:** more than two maintenance
sessions in one calendar month. Then design a maintainer mode — a scoped, auditable
exception. Do not weaken the guard before then.

**Planning routes by size, with the approval count stated as a number.** New app or
architecture change = 2 approvals; a feature = 1; a one-sentence reversible change =
0, and no `/interview` at all. Previously every feature that "doesn't fit in one
sentence" paid the full three-phase interview, which made skipping planning entirely
the cheap path. `/interview` now detects its mode from whether `docs/SPEC.md` exists,
and feature mode is forbidden from touching Part 1 or any other feature's entry.
**Put-back trigger:** if feature mode ships a feature whose architecture impact should
have escalated, tighten the escalation rule — do not merge the modes back.

**One mockup, not three, and only when a screen changes.** The UI block is four
questions in one batch; its output is a short block inside the SPEC feature entry,
never a separate document, and it rides inside an existing approval rather than adding
a gate. **KILL CRITERION:** after three UI-bearing features, if mockup approval has
not reduced post-build UI rework (the `rework` column in `docs/PROGRESS.md`), delete
the mockup step. It is a cost until it is shown not to be.

**Evaluator triggers are named by effect, not by the word "migration".** "Any
migration" over-fired on additive columns and under-fired on a table created empty
that would hold user data a week later. The list now keys on what the change can do:
first vertical slice, auth/authz/RLS, money, destructive or data-transforming
migrations, migrations touching existing production rows, any migration creating a
table that will hold user data regardless of current row count, and pre-release.
Multiple triggers in one feature = one run. **Re-scope on evidence:** ~20 optional
evals with zero unique P0/P1 findings → narrow the list. Two serious defects escaping
unevaluated work → broaden it.

**`.githooks/pre-commit` is drift control, not a trust boundary — and now says so.**
It claimed "red code cannot be committed", which a local hook cannot guarantee
(`--no-verify`, repointing `core.hooksPath`); that was `BACKLOG` C7. It also
fail-opened when `package.json` existed with no `verify` script — precisely the state
where a project has verification and is not running it. Now: no package.json → allow;
package.json without `verify` → fail; with `verify` → run it. Detection is `node -e`
parsing `scripts.verify`, because the old `grep -q '"verify"'` was satisfied by a
*dependency* named `verify`. **Residual limit, stated rather than hidden:** when
`node` is absent the hook falls back to `grep -Eq '"verify"[[:space:]]*:'`, which
still cannot separate `scripts.verify` from a dependency key; the hook prints which
check ran, so the weaker answer is never silent. Covered by
`scripts/hooks/test_pre_commit.py`: 6 behaviour cases, 5 contract assertions, and a
mutation that restores the fail-open branch and must turn exactly two cases red.

**Handoff state has one owner: `session-context.md`.** `CLAUDE.md` previously required
reading `docs/PROGRESS.md` before touching anything and appending a next-action to it
every session — the same job `/save-context` already does, into a file the evaluator
is deliberately blocked from reading. `docs/PROGRESS.md` is now shipped milestones
plus the metric log (one row per feature: started_at, green_at, human_stops, rework,
defects_after_green), which is the instrument for the governing metric. Its dangling
`progress-hygiene` reference is gone — no such skill exists in this repo or in
`~/.claude`. `session-context.md` is now gitignored; nothing ignored it before, so it
was committable.

**`.archive/` deliberately NOT added to `.gitignore`.** It was proposed alongside
`session-context.md`, but `~/.claude/DECISIONS.md` (2026-08-25, P0 config pass)
records archiving, the 20-snapshot retention, category detection and the 14-day prune
as deleted ceremony — `/save-context` overwrites one file whole and creates no
archive. An ignore rule for a directory nothing produces is dead config that reads as
coverage. **Put back if** a producer of `.archive/` is ever added.

**Visual verification is conditional on browser tooling being present.** Claude in
Chrome was confirmed available on this machine (one local extension, Windows), so the
sequence — start localhost, open the page at the target viewport, screenshot, compare
against the approved mockup, exercise one key state — is written into the BUILD loop.
But `CLAUDE.md` ships to every app scaffolded from this template, including machines
without the extension, so the rule carries its precondition and says to skip and
report rather than substitute a prose description. Asserting the tools exist would
have added a false claim in the same pass that removed seven.

**`add-*` knowledge extracted; the four commands are now safe to delete.**
`~/.claude/DECISIONS.md` (2026-08-25) gated deletion of `add-table`, `add-endpoint`,
`add-page` and `add-webhook` on a session verifying their knowledge had been
extracted. This was that session. Failure-preventing rules moved into
`.claude/skills/engineering-conventions/SKILL.md` — the `set_updated_at` ordering
dependency, `archived_at` obligations, partial unique indexes, fail-loud UNIQUE
creation, RLS policies in the creating migration, the seven-step handler order with
its gate exclusions, and the webhook raw-body → verify → parse → replay → dispatch →
mutate → ack protocol — and into `.claude/rules/react-traps.md` (Strict-Mode
double-invocation, wizard-step keying, setState-then-submit, progressive save,
gate-preserve). Workflow steps, "Verify" sections, and anything already carried by
`~/.claude/REVIEWER_CONVENTIONS.md` §6 were dropped rather than copied. Deleting the
four files still requires repairing `~/.claude/commands/new-app.md`, whose frontmatter
description names three of them.

**`env.example` created, because the README told you to verify a file that did not
exist.** Four files cite it — `.gitignore`, `CLAUDE.md`, `README.md` and this one — and
the README's guardrail check says "Read `env.example` → allowed". There was no such
file in the repo, so that check could not pass. Same class of defect as the fail-open
pre-commit fixed in this pass: a verification step that cannot fail measures nothing.
It ships with empty values and one comment per key; a filled-in value here would be a
committed secret, and this repo is public.

**`.claude/rules/` is a real mechanism and its frontmatter key is `paths`, not
`globs`.** Verified against the Claude Code memory documentation before use: a rule
carrying `paths` loads only when a matching file is read. This is the first rules file
in the template.

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
