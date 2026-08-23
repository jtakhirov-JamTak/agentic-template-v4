#!/usr/bin/env python3
"""PreToolUse hook for Bash.

Two enforcement modes:
1. UNIVERSAL DENYLIST (all agents): destructive/bypass commands.
2. EVALUATOR ALLOWLIST: when the hook fires inside the `evaluator` subagent
   (agent_type/agent_name in hook input), Bash is restricted to read-only
   inspection and test commands. Fail CLOSED for the evaluator.

Field caveat: agent identity arrives as `agent_type` (documented for hooks
inside subagents) or `agent_name` (seen in some payloads). Both are checked.
If neither is present, evaluator mode cannot engage — the evaluator's
`isolation: worktree` checkout is the backstop. Verify field names on your
Claude Code version before trusting allowlist mode."""
import json, re, shlex, sys

DENY_RULES = [
    (r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\s+(/|~|\$HOME)(\s|$)",
     "Destructive recursive delete of home/root is blocked."),
    (r"git\s+push\s+.*(--force|-f)\b.*\b(main|master)\b",
     "Force-pushing to main/master is blocked."),
    (r"git\s+commit\s+.*--no-verify",
     "Bypassing commit verification is blocked. Fix the check instead."),
    (r"git\s+config\s+.*hooksPath",
     "Repointing git hooks is blocked. .githooks/pre-commit is a release control."),
    (r"(sed\s+-i|mv\s|rm\s|>\s*|tee\s).*(supabase/|prisma/|db/)?migrations/",
     "Modifying migration files via shell is blocked. Create a new migration."),
    (r"(cat|echo|printf|tee).*(>>?|\|)\s*\.env(\.|$|\s)",
     "Writing .env files via shell is blocked. Use the platform's secret manager."),
    (r"(cat|less|more|head|tail|grep|cp|scp)\s+[^|;&]*\.env(\.|$|\s)",
     "Reading/copying .env files via shell is blocked."),
    (r"git\s+reset\s+--hard",
     "git reset --hard is blocked. Show the human what would be discarded first."),
    (r"git\s+clean\s+-[a-zA-Z]*f",
     "git clean -f is blocked. Show the human what would be deleted first."),
    (r"git\s+(checkout|restore)\s+(--\s|\.\s*$|\*)",
     "Discarding working-tree changes is blocked. Show the human first."),
]

# Evaluator mode: first token of every pipeline segment must be allowlisted,
# and no write/mutation constructs anywhere.
EVAL_ALLOWED = {"npm", "npx", "node", "curl", "jq", "cat", "ls", "grep", "head",
                "tail", "find", "wc", "diff", "pwd", "echo", "which", "sleep", "git"}
EVAL_GIT_OK = {"status", "diff"}  # git log is forbidden by the isolation protocol
EVAL_DENY_PAT = re.compile(r"(>>?|`|\$\(|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|"
                           r"\bchmod\b|\bchown\b|\bln\b|\btouch\b|\bnpm\s+(i|install|ci|add)\b)")

def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)

def check_evaluator(cmd):
    if EVAL_DENY_PAT.search(cmd):
        block("Evaluator is read-only: redirection, file mutation, and installs are "
              "blocked. Inspect and test only; report findings instead of fixing.")
    for segment in re.split(r"\||;|&&|\|\|", cmd):
        toks = shlex.split(segment.strip()) if segment.strip() else []
        if not toks:
            continue
        head = toks[0]
        if head not in EVAL_ALLOWED:
            block(f"Evaluator Bash allowlist: '{head}' is not permitted. Allowed: "
                  f"{', '.join(sorted(EVAL_ALLOWED))} (git: status/diff only). "
                  f"Extend the list in scripts/hooks/bash_guard.py if a read-only "
                  f"tool is missing.")
        if head == "git" and (len(toks) < 2 or toks[1] not in EVAL_GIT_OK):
            block("Evaluator may only run `git status` / `git diff`. Git history and "
                  "mutations are off-limits (context isolation).")

def main():
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    for pat, msg in DENY_RULES:
        if re.search(pat, cmd):
            block(f"Blocked: {msg}")
    agent = (data.get("agent_type") or data.get("agent_name") or "").lower()
    if agent == "evaluator":
        check_evaluator(cmd)
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"bash_guard hook error (allowed): {e}", file=sys.stderr)
        sys.exit(0)
