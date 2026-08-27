# FIX_LOG

(Every real defect: dated entry — problem, fix, regression test, where found.
Template-derived apps split: FIX_LOG.md = what the next app from the template
would also hit; APP_FIX_LOG.md = the rest.)

---

## 2026-08-25 — Governance was writable from the shell; the docs claimed otherwise

**Problem.** `write_guard.py` is registered for `Edit|Write|MultiEdit` only, so it
never sees a shell command. `CLAUDE.md` nonetheless stated, under a heading reading
"Guardrails (deterministic — do not weaken)", that "`.claude/`, `.githooks/`, and
this file change only via the human". Measured against the live guard, eight shell
forms rewrote or deleted governance at exit 0: `cp foo CLAUDE.md`,
`sed -i 's/a/b/' CLAUDE.md`, `echo hi > CLAUDE.md`,
`cat foo > .claude/settings.json`, `cp foo .claude/commands/interview.md`,
`rm CLAUDE.md`, `mv foo.md CLAUDE.md`, `tee CLAUDE.md < foo`. Controls in the same
run (`--no-verify`, `git push --force`, `cat .env`) returned exit 2, so the probe
could distinguish. Found while installing a human-approved `CLAUDE.md` change: the
copy succeeded through a layer that was documented as closed.

**Fix.** Added `check_governance()` to the user-level `~/.claude/hooks/shell_guard.py`,
called per segment beside `check_recursive_delete`. It is token-based rather than a
regex over the command string, for the same reason `strip_quoted()` exists: a commit
message may legitimately name `CLAUDE.md`, so only the operands of a verb that
actually writes are treated as targets. `cp`/`mv`/`install`/`ln` contribute only
their LAST operand, keeping `cp CLAUDE.md /tmp/backup` (a read) allowed. Paths are
resolved against `CLAUDE_PROJECT_DIR` exactly as `write_guard.py` resolves them, so
the two guards cannot drift about what is protected, and `docs/proposed/CLAUDE.md`
— the sanctioned route for drafting a governance change — stays writable. `import os`
was added with it: without it the `NameError` would have been swallowed by the
module's fail-open `except`, and the guard would have allowed everything silently.

**Also fixed the claim, not just the code.** The shell guard is user-level and
machine-local (handoff B2), so this protection does not travel with the template.
`CLAUDE.md` and `README.md` now separate what ships with the repo (`write_guard.py`,
write tools only) from what is machine-local (`shell_guard.py`, the shell route),
and say plainly that on a machine without `~/.claude` configured, governance is
freely rewritable from the shell.

**Regression test.** 27 cases in `~/.claude/hooks/test_shell_guard.py` (suite 249 →
276): 16 BLOCK covering every measured bypass in both shells plus the glued
redirect, quoted destination, `dd of=`, and a second-segment form; 11 ALLOW pinning
the over-block direction — reading, `cp` governance *out*, `git add CLAUDE.md`, a
commit message naming the file, `docs/proposed/CLAUDE.md`, `docs/CLAUDE.md`, and the
near-miss directory `.claudette/`. Mutation `d1-governance-off` disables the check
and asserts exactly those 16 turn red with no collateral — verified: 16 expected, 16
actual. The fix was confirmed against itself: `cp docs/proposed/CLAUDE.md CLAUDE.md`,
the exact command that exposed the hole earlier in the session, is now blocked.

## 2026-08-25 — `.githooks/pre-commit` has never run in this clone

**Problem.** `core.hooksPath` is unset at local, global and effective scope, and
`.git/hooks/` holds no non-sample hook, so `.githooks/pre-commit` is inert here —
including for the commits made in this session. `CLAUDE.md` listed it among the
guardrails with no indication that it requires per-clone wiring, which reads as an
active verification layer and is a false-green path for anyone trusting the list.

**Fix — documentation only, deliberately.** `README.md` setup step 2 and
`~/.claude/new-app.ps1` (Step 2, with a readback assertion) already wire it for real
apps, and `README.md` residual gap 5 already recorded that this clone is unwired;
the defect was that `CLAUDE.md` did not. It now describes the hook as a per-clone
layer that does nothing until `git config core.hooksPath .githooks` is run, and says
this template's own commits are not gated by it. This clone was deliberately left
unwired: it has no `package.json`, so the hook would allow every commit anyway, and
wiring it would buy no protection while adding a claim to maintain. No shell-guard
exemption was added for the wiring command — `git config core.hooksPath` stays
blocked in both directions.

**Regression test.** None, and that is the honest position: the defect was a false
claim in prose, and `test_pre_commit.py` already covers the script's logic while
explicitly not covering its installation (README residual gap 5). A test asserting
"this clone is unwired" would pin an accident rather than a requirement.

---

## 2026-08-24 — Deny rules blocked safe work: unstaging and single-file deletion

**Problem.** Two `permissions.deny` rules blocked legitimate operations that the
hook layer deliberately allowed. `Bash|PowerShell(git reset:*)` is a prefix
matcher, so it caught `git reset HEAD file` — the ordinary way to unstage —
along with `git reset` and `git reset --soft`. `PowerShell(Remove-Item:*)` caught
every single-file deletion. Neither over-block bought anything: the destructive
forms they were aimed at (`reset --hard`, recursive delete) are caught by
`shell_guard.py`, which parses flags and so is not fooled by order, position, or
alias. The handoff's kill criteria name a blocked safe action as a framework
defect in its own right, equal in weight to a missed destructive one, because an
over-block is what teaches an agent to route around the guard.

**Fix.** Narrowed to `Bash|PowerShell(git reset --hard:*)` and
`PowerShell(Remove-Item -Recurse:*)`. Dropped the redundant `Read(./.env)` /
`Read(./.env.*)` variants, which `Read(**/.env)` / `Read(**/.env.*)` already
subsume. The deny list now claims only what a prefix matcher can actually see;
the hook covers the rest, which was already true and is now also honest.

**Regression test.** Both directions asserted in `test_shell_guard.py`: six ALLOW
cases (`git reset HEAD file` in both shells, `git reset`, `--soft`, `--mixed`,
single-file `Remove-Item`/`ri`/`-Path`) and BLOCK cases for `reset --hard` bare,
with a ref, behind `-C`, and after `&&`. Because the deny rule narrowed, the hook
is now the ONLY layer catching `-Recurse` in non-leading position, so five cases
pin exactly that: `-Force -Recurse`, trailing `-Recurse`, `-Path … -Recurse`, and
the `rd` / `erase` aliases. Two named-set mutations (`b4-git-reset`,
`b4-ps-recursive`) prove those cases fail when the narrowing is reverted or the
flag scan is disabled, and that nothing outside the named set moves.

**Where found.** Recorded in BACKLOG during Session A; fixed in Session B.

---

## 2026-08-24 — Four layers disagreed about whether `.env.example` was a secret

**Problem.** `shell_guard.py` ALLOWED `.env.example` via an explicit
`(?!\.example|\.sample|\.template)` carve-out. `write_guard.py` BLOCKED it.
`.gitignore` carried a `!.env.example` negation implying the file should exist
and be committed. `permissions.deny` blocked `**/.env.*`, which includes it. So
the agent could read the file through the shell, could not create it with Write,
and git was told to commit a file two guards treated as secret. Every layer was
individually defensible and the set was incoherent — the failure mode of an
exception that has to be restated correctly in four places.

**Fix.** Deleted the exception instead of synchronising it. The non-secret
example file is now `env.example`, with no leading dot, which does not contain
the substring `.env` and therefore cannot match any secret rule in any layer.
`ENVFILE` in `shell_guard.py` is plain `\.env`; the `!.env.example` negation is
gone from `.gitignore`. Every `.env*` is secret, with nothing to keep in step.

**Regression test.** `test_shell_guard.py`: `.env.example`, `.env.sample` and
`.env.template` must now BLOCK (these three flipped from ALLOW, which is the
change); `env.example` must be readable and writable in both shells and in a
subdirectory; `cp env.example .env` must still block, so the rename cannot be
used as a laundering route. `test_write_guard.py` asserts the same file set from
the write side. `.gitignore` behaviour proven directly with `git check-ignore`:
`.env.example` ignored, `env.example` tracked. Mutation `b3-env-carveout`
restores the carve-out and turns exactly those three cases red.

**Where found.** Recorded in BACKLOG during Session A; fixed in Session B.

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

## 2026-08-23 — Recursive delete and force push were reachable around both layers

**Problem.** `permissions.deny` matches on a command *prefix*, so `Bash(rm -rf:*)`
covered `rm -rf x` and nothing else — not `rm -fr x`, not `rm -r -f x`, and not
`cd s ; rm -rf x`, where `rm` is not the first token. `shell_guard`'s own `rm`
rule did not close the gap: it only fired when the target was `/`, `~`, or
`$HOME`, so **project files were never protected by either layer**. Force push
had the same shape: the rule required `--force`/`-f` *and* an explicit
`main`/`master`, so `git push --force-with-lease` and the refspec form
`git push origin +main` both passed.

Found by a `/permissions` review in a scaffolded app, then reproduced against
the hook directly: seven commands that should have been blocked were allowed.

**Fix.** Recursive deletes now go through `check_recursive_delete()`, which walks
every command segment and reads the flags, so flag order, flag splitting,
abbreviation, aliasing, and position in the line all stop mattering. Force push
is matched on every spelling: `--force`, `-f`, `--force-with-lease`,
`--force-if-includes`, and `+ref` refspecs, on any branch rather than only
main/master.

Single-file deletes stay allowed in **both** shells — `rm file.txt` and
`Remove-Item one.txt`. The hook draws its line at the recursive case, which is
the data-loss event; blocking every delete would leave the ALLOW column proving
nothing and would fire constantly on temp files. The template's
`PowerShell(Remove-Item:*)` deny rule is still the stricter layer inside a
scaffolded app, and the `CLAUDE.md` hard stop ("show me what something is
before you delete it") governs single-file deletes behaviourally everywhere.
**Residual risk, stated plainly: a single-file delete is not mechanically
gated outside a template-derived project.**

**Regression test.** 23 new cases in `test_shell_guard.py` (84 total). Verified
falsifiable: removing the `check_recursive_delete()` call turns it 69/84 red on
exactly the delete cases, and restoring returns 84/84.

**Lesson for the next app.** A prefix-matched deny rule is a statement about one
spelling of a command, not about the capability. Anything genuinely destructive
needs the hook layer, where the command can be parsed.

## 2026-08-23 — Reading the hooks path was blocked as if it were a write

**Problem.** The rule matched any `git config` line mentioning the hooks path,
so reading the value was blocked along with setting it — including the bare
read that `/new-app` step 2 uses to verify the path took. An over-block on a
read is worse than a miss: it teaches the agent to route around the guard.
It fired for real mid-session, on a commit message that merely quoted the
command.

**Fix.** Split into write-only forms — a value following the key, or
`--unset` / `--unset-all` / `--replace-all` / `--add`. Reads pass.

**Regression test.** 9 cases (95 total): four write forms blocked, four read
forms allowed, plus the PowerShell mirror.

**Where found.** A real session, not a review.

## 2026-08-24 — Every destructive git command was reachable by adding a global option

**Problem.** The git rules matched the raw command line, so they only knew one
spelling of each command. Git accepts global options *before* the subcommand,
and every one of them defeated the guard. Measured against the shipped guard,
11 of 13 destructive forms exited 0 — through the hook AND through
`permissions.deny`, which is prefix-matched and misses the same forms:
`-C repo`, `-c color.ui=false`, `--git-dir=`, `--work-tree=`,
`--config-env=core.hooksPath=`, and `GIT_CONFIG_*`/`GIT_DIR` environment
prefixes, against `reset --hard`, `clean -fd`, `push --force`, `commit
--no-verify` and `checkout -- .`, in both shells.

The same line-oriented matching produced a false POSITIVE: the reset rule fired
on the path *text* in `--git-dir=/tmp/r/dotgit reset --hard` while missing the
identical command with `--git-dir=/srv/repo`. One bad mechanism, both error
directions.

**Fix.** Git handling became parse → normalize → match. Each segment is
tokenized, leading `NAME=VALUE` assignments and git global options are lifted
off, and the rules match the resulting `git <subcommand> ...` form — so one rule
now covers every spelling of its command class instead of one string. The lifted
globals are judged separately, because anything setting `core.hooksPath` IS the
bypass rather than a detail of it. An unknown global that swallows the
subcommand slot fails CLOSED rather than matching rules against a non-command.

The tokenizer is purpose-built, not `shlex`: `posix=False` splits
`--git-dir="C:\p with spaces\x"` into three tokens because it only honours a
quote that OPENS a token — which would have recreated the bypass — and
`posix=True` discards the quoted-ness needed to stop `-m "the -n flag"` from
faking a flag. Plain `.split()` fails the same way, which is why the handoff
forbade it.

**Regression test.** `scripts/hooks/test_shell_guard.py`, 172 cases (up from
95), both directions, including quoted Windows paths with spaces, chained and
substituted forms, and PowerShell mirrors. Verified falsifiable by
`--mutate`, which disables ONLY the global-option lifting and asserts that
exactly 22 named cases turn red and nothing else moves. That assertion caught a
real error while being written: three cases originally claimed as covered by
normalization survived the mutation, because a leading `NAME=VALUE` does not
break `git <verb>` adjacency and because `...\.git reset --hard` contains the
pattern by coincidence — the very false positive above. They were removed from
the claim and a discriminating variant added.

**Where found.** Reproduced against the shipped guard before any edit.

## 2026-08-24 — A secret in a MultiEdit was written with no hook objecting

**Problem.** Two hooks ran on every write. `protect_paths.py` read
`tool_input.file_path`, which MultiEdit has; `scan_secrets.py` read only the
flat content keys (`content`, `new_string`, `new_str`, `file_text`), which
MultiEdit does not use — its text lives in `edits[].new_string`. So an AWS key
in a MultiEdit exited 0 while the identical key in a `Write` exited 2. Two
processes on the hot path, and the hole was in the seam between them.

**Fix.** One `write_guard.py` on `Edit|Write|MultiEdit`, scanning every field a
write can carry text in, `edits[]` included. Secret classes extended with
`whsec_`, `(sk|rk)_(test|live)_`, `sntrys_`, and Postgres URLs carrying an inline
password; Stripe `pk_` publishable keys are deliberately NOT matched. The
Python Read hook was deleted outright — `permissions.deny` is the hard Read
layer, it is the only one that also covers `@file` mentions, and removing it
takes ordinary reads to zero custom processes.

**Regression test.** `scripts/hooks/test_write_guard.py`, 44 cases, both
directions — secrets in the first, middle and last `edits[]` entry (a
traversal that only checked `edits[0]` would pass two of three), `pk_` and
password-less Postgres URLs asserted ALLOWED, plus governance, forward-only
migrations and env files. Verified falsifiable by `--mutate`, which removes the
`edits[]` traversal and asserts exactly the four MultiEdit-secret cases turn
red.

**Where found.** Reproduced against the shipped hooks before any edit.

## 2026-08-24 — The evaluator graded a tree that never existed

**Problem.** `evaluator.md` carried `isolation: worktree`. Per the subagent
reference, that worktree is branched from the repository's DEFAULT BRANCH, not
from the parent session's `HEAD` — so the evaluator saw neither uncommitted work
nor, on a feature branch, committed work. It was grading something that had
never existed on anyone's disk, and reporting PASS/FAIL about it.

**Fix.** Removed `isolation: worktree`; the evaluator now inspects the real
working tree. Because that removes the sandbox, three things replace it: a
`git status --porcelain` invariant (main session before = evaluator first =
evaluator final, any difference invalidates the evaluation — and NOT
`--untracked-files=no`, which hides exactly the files being checked for); the
existing shell allowlist, extended to block reads of `PROGRESS.md`,
`session-context.md` and `docs/evals/` since the evaluator keeps `cat`; and a
new `evaluator_guard.py` on `Read|Grep|Glob`, registered in the agent's own
frontmatter `hooks:` so it runs ONLY for that subagent and ordinary sessions
keep zero processes on the Read path.

**Regression test.** `scripts/hooks/test_evaluator_guard.py` — 18 behaviour
cases (the three sources blocked, SPEC/source/migrations allowed, and the block
scoped to the evaluator rather than global) plus 11 contract checks asserting
`evaluator.md` still says what the guard assumes. Verified falsifiable: the
contract half fails 6/11 against the pre-fix `evaluator.md`.

**Verified live (2026-08-24), full dispatch.** A real evaluator session in a
purpose-built repo whose `HEAD` lacks the feature and whose working tree has it:
- sees the uncommitted work — read the working-tree file carrying a marker
  absent from `HEAD`, and graded the acceptance criterion PASS that the `HEAD`
  version FAILS. Under `isolation: worktree` the verdict inverts, so the removal
  is load-bearing and not cosmetic;
- reads of `PROGRESS.md`, `session-context.md` and a prior eval were all BLOCKED
  by the live frontmatter hook, returning `evaluator_guard.py`'s own message;
- a shell mutation (`echo mutated >> src/total.js`) was BLOCKED, and the target
  file contains no `mutated` line;
- `git rev-parse` was blocked by the git-history rule, incidentally confirming
  the evaluator branch is live;
- `git status --porcelain` byte-identical before and after, checked
  independently rather than taken from the agent's report.

Frontmatter hooks DO fire and `${CLAUDE_PROJECT_DIR}` IS expanded in the hook
command; the registration was changed from a bare relative path to the
`${CLAUDE_PROJECT_DIR}` form, since a relative path resolves against the hook
process's cwd rather than the project root.

**Discovered by that run — workspace trust gates the whole thing.** The first
dispatch, with the definition PROJECT-level in an untrusted folder, read all
three forbidden files without objection. Claude Code had silently skipped the
frontmatter hooks:

```
[ERROR] Skipping frontmatter hooks for main-thread agent 'evaluator': the folder
its definition file came from is not trusted (source: projectSettings).
```

The evaluator still ran — with no read isolation, and no signal outside the
debug log. Re-running with the identical definition from a trust-free source
(`~/.claude/agents/`) blocked all three. So the guard is correct and the gate is
trust. `-p` / non-interactive runs skip the trust dialog, so an evaluator
dispatched from CI in an untrusted folder has no read isolation at all. The
project shell guard is unaffected — it comes from `settings.json` and ran in
both cases, which is why mutation was blocked even in the untrusted run.

**Where found.** Handoff v2.2 A3; the default-branch detail confirmed in the
subagent reference, not assumed. The trust gate was found by the live run, not
by reading docs — the structural tests passed 11/11 while the read isolation was
entirely absent, which is exactly the failure mode structural tests cannot see.

## 2026-08-24 — A dead evaluator guard was indistinguishable from a live one

**Problem.** Follow-on from the trust finding above. From inside the evaluator,
"my read guard is running" and "my read guard is not running" look identical:
both present as reads that simply succeed. The untrusted live run produced a
full, confident, well-evidenced evaluation report while having read the build
log, the session context and a prior eval. Nothing in the harness noticed; the
only trace was one line in a debug log nobody reads on a green run.

**Fix.** A self-probe. `.claude/evaluator-hook-probe.txt` is a committed
sentinel containing no project information, added to `evaluator_guard.py`'s
denied set with its OWN message. The evaluator's Step 0 — before SPEC.md,
before any shell command — is to Read it:

- blocked → the guard is alive, say so and continue;
- succeeds → **P0 HARNESS FAILURE**, abort immediately, grade nothing;
- "does not exist" → also a harness failure; the sentinel was deleted and the
  probe can no longer tell you anything.

The sentinel is deliberately meaningless. Probing a real file such as
PROGRESS.md would be self-defeating: the probe only "fires" when the guard is
dead, which is exactly the moment the read succeeds and contaminates the
evaluator with the history it must be blind to. The file must also EXIST — a
missing file returns "does not exist", which reads like a block and would make
the probe lie in the one direction that matters.

`CLAUDE.md` now tells the main session that a P0 HARNESS FAILURE means no
evaluation happened: do not record it, do not act on any grade in it.

**Regression test.** 3 behaviour cases (sentinel blocked, absolute and
backslash spellings) and 6 contract checks: the sentinel exists, carries no
project tokens, returns a message distinguishable from the isolation block, and
the agent body performs the probe and defines the abort path. That last check
caught a real defect while being written — `P0 HARNESS FAILURE` was split across
a line wrap in the agent body and was not a contiguous string.

**Known limitation, not solved here.** Under `claude -p` / CI the trust dialog
is skipped entirely, so project-level frontmatter hooks cannot be assumed
active. The probe now makes that state loud instead of silent — the run aborts
with P0 rather than producing a clean-looking report — but it does not make the
hooks run. A headless trust mechanism is deliberately out of scope.

**Where found.** The live A3 verification run, not a review.

## 2026-08-24 — The secret scanner blocked its own documentation

**Problem.** The Postgres rule matched any `postgres://user:pass@host`, which
includes the canonical placeholder `postgres://user:password@host` — the exact
string that belongs in a README or `env.example`. Blocking a legitimate write is
a defect by the same standard as missing a real one, and this one would have
trained the obvious workaround: stop writing connection-string docs.

**Fix.** `check_postgres_urls()` captures user, password and host and exempts
only what cannot be a live credential:
- a TEMPLATED password (`<password>`, `${DB_PASSWORD}`, `{{pw}}`, `%VAR%`,
  `$VAR`, `****`) — exempt on its own, since it is not a literal;
- a literal placeholder word (`password`, `changeme`, …) — exempt ONLY when the
  username is also a placeholder, so the whole URL reads as illustrative.

`postgres://svc_billing:password@prod-db.internal/app` therefore still blocks: a
real service account beside a weak password is a leak, not documentation. This
is intentionally not a general database-URL bypass.

**Regression test.** 13 cases both directions — realistic credentials blocked
with placeholder-looking and real usernames, in docs, and in a later MultiEdit
entry; placeholders and templated forms allowed. Two cases pin the sharp edges:
a placeholder sitting beside a real credential does not launder it, and a
placeholder password with a real username still blocks. Verified falsifiable by
forcing the exemption on and off: ON turns 8 BLOCK cases red, OFF turns 7 ALLOW
cases red, with no overlap — so both the rule and its narrowness are
load-bearing.

**Where found.** Flagged as a disagreement when A2 was implemented to spec, then
fixed on instruction.
