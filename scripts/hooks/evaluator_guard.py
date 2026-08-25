#!/usr/bin/env python3
"""PreToolUse hook for the `evaluator` subagent only: Read|Grep|Glob.

Registered in `.claude/agents/evaluator.md` frontmatter, NOT in settings.json,
so it runs only while that subagent is active. Ordinary sessions keep zero
custom processes on the Read path.

The evaluator grades the implementation against docs/SPEC.md starting from zero
knowledge of how anything was built. Three sources would hand it that knowledge
and are therefore closed:
  docs/PROGRESS.md      the build ledger
  session-context.md    the current session's working state
  docs/evals/**         what previous evaluations already concluded

`isolation: worktree` used to be the backstop for this. It was removed so the
evaluator can see uncommitted work, so this hook plus shell_guard's evaluator
branch ARE the containment now — there is nothing behind them.

Because there is nothing behind them, this hook not running is indistinguishable
from it running and allowing everything. That is not hypothetical: a project-
level subagent's frontmatter hooks are silently skipped until the workspace is
trusted, and a live run in that state read every forbidden file without
objection. So the evaluator Reads `.claude/evaluator-hook-probe.txt` first, and
a block is its proof this file is alive. The sentinel is empty of meaning on
purpose — if the guard IS dead, the probe read succeeds, and probing a real file
would hand the evaluator the history it must be blind to.

Residual gap, stated rather than papered over: a Grep whose `path` is the repo
root and whose pattern happens to match text inside a forbidden file can still
surface a line from it. This closes the paths, not every possible read.
"""
import json
import sys

FORBIDDEN = ("progress.md", "session-context.md", "evals/")
# Every field the three tools name a location in.
LOCATION_KEYS = ("file_path", "path", "pattern", "glob", "notebook_path")

# The self-probe sentinel. The evaluator Reads this first; a block proves this
# hook is alive. It gets its OWN message so the evaluator can tell a live guard
# apart from an unrelated failure, and so a human reading a transcript can too.
PROBE = "evaluator-hook-probe"
PROBE_MSG = (
    "Evaluator hook self-probe: BLOCKED, which is the expected result. "
    "evaluator_guard.py is registered and running, so context isolation is "
    "active. Continue the evaluation."
)
ISOLATION_MSG = (
    "Evaluator context isolation: PROGRESS.md, session-context.md and prior "
    "docs/evals/ are off-limits. Grade against docs/SPEC.md and the running app "
    "only. If you believe you need this file, report that as a finding instead "
    "of working around it."
)


def main():
    data = json.load(sys.stdin)

    # Registration already scopes this to the evaluator. The check is here so
    # the hook is inert rather than surprising if it is ever registered wider.
    # An ABSENT agent_type is treated as the evaluator: inside an
    # evaluator-scoped registration, "cannot tell" must fail closed.
    agent = (data.get("agent_type") or data.get("agent_name") or "").lower()
    if agent and agent != "evaluator":
        sys.exit(0)

    ti = data.get("tool_input") or {}
    for key in LOCATION_KEYS:
        value = ti.get(key)
        if not value:
            continue
        target = str(value).replace("\\", "/").lower()
        if PROBE in target:
            print(PROBE_MSG, file=sys.stderr)
            sys.exit(2)
        for name in FORBIDDEN:
            if name in target:
                print(ISOLATION_MSG, file=sys.stderr)
                sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"evaluator_guard hook error (allowed): {e}", file=sys.stderr)
        sys.exit(0)
