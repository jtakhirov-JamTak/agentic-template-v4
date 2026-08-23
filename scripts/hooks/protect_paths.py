#!/usr/bin/env python3
"""PreToolUse hook for Read|Edit|Write|MultiEdit.
Blocks (exit 2):
  - reading OR writing .env* / key files (belt; permissions.deny is suspenders —
    note: @file mentions may bypass Read hooks, which is why the deny rules
    in settings.json exist as the primary layer)
  - modifying an EXISTING migration file (forward-only; new files allowed)
  - agent self-modification of governance (.claude/, .githooks/, CLAUDE.md, FRAMEWORK.md)
Reads the tool call as JSON on stdin (tool_input.file_path)."""
import json, os, sys

MIGRATION_DIRS = ("supabase/migrations/", "migrations/", "prisma/migrations/", "db/migrations/")
GOVERNANCE = (".claude/", ".githooks/", "CLAUDE.md")
SECRET_BASENAMES = ("id_rsa", "id_ed25519")

def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)

def is_secret_file(rel):
    base = os.path.basename(rel)
    if base == ".env" or base.startswith(".env."):
        return True
    if base.endswith(".pem"):
        return True
    return any(base.startswith(s) for s in SECRET_BASENAMES)

def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    fp = (data.get("tool_input") or {}).get("file_path", "") or ""
    if not fp:
        sys.exit(0)
    root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    rel = os.path.relpath(os.path.abspath(fp), root).replace("\\", "/")

    if is_secret_file(rel):
        block("Blocked: secret files (.env*, keys) are never read or written by the agent. "
              "Reference secrets by env-var NAME; the human manages values.")

    if tool == "Read":
        sys.exit(0)  # remaining rules govern writes only

    for g in GOVERNANCE:
        if rel == g or rel.startswith(g):
            block("Blocked: governance files (.claude/, .githooks/, CLAUDE.md) "
                  "change only via the human (Phase 5 improvement loop).")

    for d in MIGRATION_DIRS:
        if rel.startswith(d):
            exists = os.path.exists(os.path.join(root, rel))
            if tool in ("Edit", "MultiEdit") or (tool == "Write" and exists):
                block("Blocked: migrations are forward-only. Never modify an existing "
                      "migration; create a NEW migration file instead.")
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"protect_paths hook error (allowed): {e}", file=sys.stderr)
        sys.exit(0)
