#!/usr/bin/env python3
"""Tests for evaluator_guard.py and the evaluator's frontmatter contract.

Run:  python scripts/hooks/test_evaluator_guard.py

Two halves:
  1. BEHAVIOUR — the hook blocks the three forbidden sources and nothing else,
     and does so only for the evaluator.
  2. CONTRACT  — evaluator.md still says what the guard assumes: no
     `isolation: worktree`, no Edit/Write, and the hook actually registered.
     A guard registered nowhere protects nothing, so the registration is part
     of the test rather than an assumption.

What these do NOT prove: that Claude Code fires a frontmatter-registered hook,
or that the `command:` path resolves at runtime. Neither is decidable from a
script. Both were settled by live dispatch on 2026-08-24 — hooks fire and
`${CLAUDE_PROJECT_DIR}` IS expanded — but that verification is a point-in-time
fact about a Claude Code version, not something these tests re-check.

One thing no test here can enforce: when the definition is PROJECT-level, its
frontmatter hooks are silently skipped until the workspace is trusted, and the
evaluator then runs with NO read isolation. See docs/FIX_LOG.md.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "evaluator_guard.py")
AGENT_MD = os.path.normpath(os.path.join(HERE, "..", "..", ".claude", "agents",
                                         "evaluator.md"))

# (tool, tool_input, agent_type, expect_exit, label)
CASES = [
    # ---- the self-probe sentinel (Step 0) ----
    # Must block, and with its OWN message, so a live guard is distinguishable
    # from an unrelated failure.
    ("Read", {"file_path": ".claude/evaluator-hook-probe.txt"}, "evaluator", 2,
     "probe sentinel blocked"),
    ("Read", {"file_path": "C:/proj/.claude/evaluator-hook-probe.txt"}, "evaluator", 2,
     "probe sentinel blocked abs"),
    ("Read", {"file_path": ".claude\\evaluator-hook-probe.txt"}, "evaluator", 2,
     "probe sentinel blocked backslash"),

    # ---- the three forbidden sources ----
    ("Read", {"file_path": "docs/PROGRESS.md"}, "evaluator", 2, "read PROGRESS.md"),
    ("Read", {"file_path": "/abs/proj/docs/PROGRESS.md"}, "evaluator", 2, "read PROGRESS.md abs"),
    ("Read", {"file_path": "docs\\PROGRESS.md"}, "evaluator", 2, "read PROGRESS.md backslash"),
    ("Read", {"file_path": "session-context.md"}, "evaluator", 2, "read session-context.md"),
    ("Read", {"file_path": "docs/evals/eval-01.md"}, "evaluator", 2, "read prior eval"),
    ("Glob", {"pattern": "docs/evals/**"}, "evaluator", 2, "glob prior evals"),
    ("Grep", {"pattern": "auth", "path": "docs/evals/"}, "evaluator", 2, "grep prior evals"),
    ("Grep", {"pattern": "x", "path": "docs/PROGRESS.md"}, "evaluator", 2, "grep PROGRESS.md"),

    # ---- what the evaluator legitimately needs ----
    ("Read", {"file_path": "docs/SPEC.md"}, "evaluator", 0, "read SPEC.md"),
    ("Read", {"file_path": "src/app/page.tsx"}, "evaluator", 0, "read source"),
    ("Read", {"file_path": "package.json"}, "evaluator", 0, "read package.json"),
    ("Glob", {"pattern": "src/**/*.ts"}, "evaluator", 0, "glob source"),
    ("Grep", {"pattern": "createClient", "path": "src"}, "evaluator", 0, "grep source"),
    ("Read", {"file_path": "docs/BACKLOG.md"}, "evaluator", 0, "read BACKLOG.md"),
    ("Read", {"file_path": "supabase/migrations/001_init.sql"}, "evaluator", 0, "read migration"),

    # ---- agent scoping: the block is the evaluator's, not everyone's ----
    ("Read", {"file_path": "docs/PROGRESS.md"}, "general-purpose", 0,
     "PROGRESS readable by another agent"),
    ("Read", {"file_path": "docs/evals/eval-01.md"}, "code-reviewer", 0,
     "prior eval readable by another agent"),
    # Absent agent_type inside an evaluator-scoped registration must fail CLOSED.
    ("Read", {"file_path": "docs/PROGRESS.md"}, None, 2,
     "absent agent_type fails closed"),
]


def run(tool, tool_input, agent):
    payload = {"tool_name": tool, "tool_input": tool_input}
    if agent is not None:
        payload["agent_type"] = agent
    p = subprocess.run([sys.executable, GUARD], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, (p.stderr or "").strip()


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
    return "\n".join(lines[1:end]) if end else None


def contract_checks():
    """-> [(ok, label, detail)]"""
    out = []
    text = open(AGENT_MD, encoding="utf-8").read()
    fm = frontmatter(text)
    out.append((fm is not None, "evaluator.md has frontmatter", ""))
    if fm is None:
        return out

    keys = [l.split(":", 1)[0].strip() for l in fm.splitlines()
            if l.strip() and not l.startswith((" ", "\t", "-"))]

    out.append(("isolation" not in keys,
                "no `isolation:` key",
                "worktree isolation hides uncommitted work; A3 removed it"))

    tools_line = next((l for l in fm.splitlines() if l.strip().startswith("tools:")), "")
    granted = {t.strip() for t in tools_line.split(":", 1)[-1].split(",") if t.strip()}
    out.append((granted == {"Read", "Glob", "Grep", "Bash"},
                "tools are exactly Read, Glob, Grep, Bash",
                f"got {sorted(granted)}"))
    out.append((not (granted & {"Edit", "Write", "MultiEdit", "NotebookEdit"}),
                "no write tool granted", ""))

    out.append(("hooks:" in fm, "hooks registered in frontmatter", ""))
    out.append(("evaluator_guard.py" in fm,
                "registration points at evaluator_guard.py", ""))
    # A relative path resolves against the hook process's cwd, which is not
    # guaranteed to be the project root. Verified live: ${CLAUDE_PROJECT_DIR}
    # IS expanded in subagent frontmatter hook commands.
    cmd_line = next((l for l in fm.splitlines() if "evaluator_guard.py" in l), "")
    out.append(("${CLAUDE_PROJECT_DIR}" in cmd_line,
                "hook command is project-root-stable, not cwd-relative",
                cmd_line.strip()))
    out.append((os.path.exists(GUARD),
                "the registered guard file exists",
                GUARD))
    hook_matcher = next((l for l in fm.splitlines() if "matcher:" in l), "")
    out.append(("Read" in hook_matcher,
                "hook matcher covers Read",
                hook_matcher.strip()))

    # --- self-probe contract ---
    # The sentinel must EXIST. A missing file returns "does not exist", which
    # reads like a block and would make the probe report success while the
    # guard is dead — the probe would lie in exactly the direction that matters.
    sentinel = os.path.normpath(os.path.join(HERE, "..", "..", ".claude",
                                             "evaluator-hook-probe.txt"))
    out.append((os.path.exists(sentinel),
                "probe sentinel file exists", sentinel))
    if os.path.exists(sentinel):
        content = open(sentinel, encoding="utf-8").read().lower()
        leaks = [w for w in ("spec", "progress", "todo", "roadmap", "milestone")
                 if w in content.replace("progress.md", "")]
        out.append((not leaks,
                    "probe sentinel carries no project information",
                    f"suspicious tokens: {leaks}"))

    # The probe must return a DIFFERENT message than the isolation block, or the
    # evaluator cannot tell "guard alive" from "hit a forbidden file".
    probe_msg = run("Read", {"file_path": ".claude/evaluator-hook-probe.txt"}, "evaluator")[1]
    iso_msg = run("Read", {"file_path": "docs/PROGRESS.md"}, "evaluator")[1]
    out.append((probe_msg != iso_msg and "self-probe" in probe_msg.lower(),
                "probe block has its own distinguishable message", probe_msg[:60]))

    body = text[text.index("---", 3) + 3:]
    out.append(("evaluator-hook-probe" in body,
                "agent body performs the Step 0 self-probe", ""))
    out.append(("P0 HARNESS FAILURE" in body,
                "agent body defines the abort path when the probe SUCCEEDS", ""))
    out.append(("git status --porcelain" in body,
                "porcelain protocol present in the agent body", ""))
    out.append(("--untracked-files=no" not in body.replace(
                    "Not `--untracked-files=no`", ""),
                "does not instruct the porcelain form that hides new files", ""))
    out.append(("worktree" not in body.lower().replace("working tree", ""),
                "body no longer claims worktree isolation", ""))
    return out


def main():
    failures = []
    for tool, ti, agent, want, label in CASES:
        got, err = run(tool, ti, agent)
        if got != want:
            failures.append(f"  [{label}] {tool} {ti}: want exit {want}, got {got}. {err[:100]}")
    print(f"behaviour: {len(CASES) - len(failures)}/{len(CASES)} passed")

    contract = contract_checks()
    c_fail = [f"  [{label}] {detail}" for ok, label, detail in contract if not ok]
    print(f"contract:  {len(contract) - len(c_fail)}/{len(contract)} passed")

    if failures or c_fail:
        print("\nFAILURES:")
        for f in failures + c_fail:
            print(f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
