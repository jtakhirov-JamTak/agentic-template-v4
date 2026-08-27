# PROGRESS

Shipped milestones and the metric log.

**This is not a handoff file.** In-flight session state has one owner:
`session-context.md`, written by `/save-context` and read by `/resume-context`. Do not
duplicate next-actions or working state here.

## Metric log

The governing metric is time from request to a correct, green, usable feature. One row
per SPEC feature. Times are UTC (`date -u +%Y-%m-%dT%H:%MZ`, or in PowerShell
`(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mmZ")`) — read the clock, never
estimate it.

**A row is opened when the work starts and closed when it is verified green. It is
never written in one go after the fact**, because a row reconstructed at the end
measures nothing but memory.

| Feature | started_at | green_at | cycle_time | human_stops | rework | defects_after_green |
|---|---|---|---|---|---|---|

### Who opens the row

- **`/interview` opens it**, as its first workflow action, for any feature that goes
  through it — so the clock includes the feature's own planning, not just its code.
- **BUILD opens it** for a direct build that skipped `/interview` (the one-sentence
  reversible change), immediately before implementation begins.
- **New app:** `/interview` opens **F1** when the new-app interview begins. F1's
  `cycle_time` therefore covers request → interview → design → approval →
  fresh-session handoff → implementation → verification → green, which is the number
  worth knowing. F2 onward start when work on that feature starts.

**At most one row may be open at a time** (`green_at` = `—`). If a second feature is
about to start while a row is still open, the previous one never went green: resolve
that row first. If planning ends with nothing to build, delete the row it opened.

### Who closes the row

**BUILD closes it, always.** `green_at` is written only after all required and
available verification passes — acceptance checks, visual verification when UI changed,
the evaluator pass when a trigger applied. If a required check fails or is skipped, the
row stays open and records why. Tooling unavailability blocks green only when that
verification is required by the acceptance criteria or the release boundary. A
`green_at` ahead of its evidence is the one failure this log cannot survive.

Then record `cycle_time` = `green_at` − `started_at` as elapsed time (`1h40m`, `2d3h`).

### Columns

- **cycle_time** — the metric. Real elapsed time from the moment work began to
  verified green.
- **human_stops** — how many times the build loop stopped for the human. An ordinary
  feature should be 0; the BUILD section lists the only legitimate reasons. Anything
  above 0 carries its reason in the row.
- **rework** — how many times work already believed finished had to be reopened
  *before* green, evaluator P1 fixes included. The evaluator pass runs inside the
  feature's own loop, so a finding it raises there is rework, not an escaped defect.
- **defects_after_green** — the escaped-defect counter: defects found in use after
  `green_at` was written. A later defect does **not** reopen the row — `cycle_time`
  already happened and cannot be un-measured. It increments this column and gets a
  dated `docs/FIX_LOG.md` entry with its regression test.

A row that never gets filled in is itself the signal: the loop is not being followed,
and the metric cannot be read.

## Shipped milestones

(Newest first. One line per shipped milestone, dated.)
