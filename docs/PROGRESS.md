# PROGRESS

Shipped milestones and the metric log.

**This is not a handoff file.** In-flight session state has one owner:
`session-context.md`, written by `/save-context` and read by `/resume-context`. Do not
duplicate next-actions or working state here.

## Metric log

The governing metric is time from request to a correct, green, usable feature. One row
per SPEC feature, added when the feature goes green (per the BUILD loop in
`CLAUDE.md`). Times are UTC.

| Feature | started_at | green_at | human_stops | rework | defects_after_green |
|---|---|---|---|---|---|

- **human_stops** — how many times the build loop stopped for the human. An ordinary
  feature should be 0; the BUILD section lists the only legitimate reasons. Anything
  above 0 carries its reason in the row.
- **rework** — how many times a feature marked complete had to be reopened.
- **defects_after_green** — defects found after the feature went green, whether by the
  evaluator or in use. Each also gets a dated `docs/FIX_LOG.md` entry with its
  regression test.

A row that never gets filled in is itself the signal: the loop is not being followed,
and the metric cannot be read.

## Shipped milestones

(Newest first. One line per shipped milestone, dated.)
