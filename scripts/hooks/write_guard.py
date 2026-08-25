#!/usr/bin/env python3
"""PreToolUse hook for Edit|Write|MultiEdit — the ONE write-security process.

Replaces protect_paths.py + scan_secrets.py. Those were two processes on every
write doing one job between them, and the split is how the MultiEdit hole
survived: protect_paths saw `file_path` (which MultiEdit has) while scan_secrets
saw only the flat content keys (which MultiEdit does not use), so a secret in
`edits[].new_string` was written with neither hook objecting.

Blocks (exit 2):
  * writing a secret file (.env*, *.pem, id_rsa*, id_ed25519*)
  * agent self-modification of governance (.claude/, .githooks/, CLAUDE.md)
  * modifying an EXISTING migration file (forward-only; new files allowed)
  * content that contains a credential, in ANY field a write can carry

There is deliberately NO Read branch. Read is governed by permissions.deny in
.claude/settings.json, which is the only layer that also covers @file mentions,
and keeping a hook off the Read path keeps ordinary reads at zero extra
processes.

Reads the tool call as JSON on stdin.
"""
import json
import os
import re
import sys

MIGRATION_DIRS = ("supabase/migrations/", "migrations/", "prisma/migrations/",
                  "db/migrations/")
GOVERNANCE = (".claude/", ".githooks/", "CLAUDE.md")
SECRET_BASENAMES = ("id_rsa", "id_ed25519")

# Every field a write tool can carry text in. MultiEdit puts its text in
# edits[].new_string and nowhere else, which is why the flat list is not enough.
CONTENT_KEYS = ("content", "new_string", "new_str", "file_text")
EDIT_KEYS = ("new_string", "new_str", "content")

PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub personal access token"),
    (r"gho_[A-Za-z0-9]{36}", "GitHub OAuth token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "Anthropic API key"),
    (r"(?i)service_role[a-z_]*[\"']?\s*[:=]\s*[\"']?eyJ[A-Za-z0-9_-]{20,}",
     "Supabase service-role JWT"),
    (r"(?i)sb_secret_[A-Za-z0-9_-]{20,}", "Supabase secret API key"),
    # Stripe secret and restricted keys, test or live. `pk_` publishable keys
    # are NOT secret and are not matched: they belong in client code, and
    # blocking them would be an over-block. The \b keeps the pattern from
    # matching inside a longer word.
    (r"\b(?:sk|rk)_(?:test|live)_[A-Za-z0-9]{10,}",
     "Stripe secret or restricted key"),
    (r"whsec_[A-Za-z0-9_-]{16,}", "webhook signing secret"),
    (r"sntrys_[A-Za-z0-9_\-.=]{20,}", "Sentry auth token"),
    # Postgres URLs are handled by check_postgres_urls(), not here: telling a
    # real credential from a documentation placeholder needs to look at the
    # captured password, which a flat pattern cannot do.
]

# A connection string carrying inline credentials. Bare hosts and password-less
# URLs do not match at all.
PG_URL = re.compile(
    r"postgres(?:ql)?://(?P<user>[^\s:/@]+):(?P<pw>[^\s/@]+)@(?P<host>[^\s/]+)",
    re.I)

# A password that CANNOT be a literal credential because it is a template the
# reader is expected to substitute. Safe to exempt on its own.
PG_TEMPLATED_PW = re.compile(r"""^(?:
      <[^>]*>              # <password>, <YOUR_PASSWORD>
    | \$\{[^}]*\}          # ${DB_PASSWORD}
    | \{\{[^}]*\}\}        # {{password}}
    | %[A-Za-z_][\w]*%     # %DB_PASSWORD%
    | \$[A-Za-z_]\w*       # $DB_PASSWORD
    | \*{3,}               # ****
)$""", re.X)

# Literal placeholder words. These are exempt ONLY when the USERNAME is also a
# placeholder — i.e. the whole URL is obviously illustrative, as in
# `postgres://user:password@host`. Deliberately narrow: a real username beside
# a weak password is still treated as a leak, and this must never become a
# general database-URL bypass.
PG_PLACEHOLDER_PW = {"password", "passwd", "pass", "pwd", "secret", "changeme",
                     "placeholder", "yourpassword", "your_password",
                     "mypassword", "my_password", "xxxx", "xxxxx"}
PG_PLACEHOLDER_USER = {"user", "username", "usr", "youruser", "your_user",
                       "myuser", "my_user", "dbuser", "db_user", "postgres",
                       "placeholder", "example"}


def is_placeholder_pg(user, pw):
    """True when this URL is plainly documentation rather than a credential."""
    if PG_TEMPLATED_PW.match(pw):
        return True
    return pw.lower() in PG_PLACEHOLDER_PW and user.lower() in PG_PLACEHOLDER_USER


def check_postgres_urls(text):
    for m in PG_URL.finditer(text):
        if is_placeholder_pg(m.group("user"), m.group("pw")):
            continue
        block("Blocked: content contains a Postgres connection string with an "
              "inline password. Secrets never go in source/docs/logs — use the "
              "platform's env/secret system and reference it by variable name. "
              "In documentation, write the password as a placeholder "
              "(postgres://user:password@host) or a template "
              "(postgres://appuser:${DB_PASSWORD}@host).")


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


def check_path(tool, rel, root):
    if is_secret_file(rel):
        block("Blocked: secret files (.env*, keys) are never read or written by "
              "the agent. Reference secrets by env-var NAME; the human manages "
              "values.")

    for g in GOVERNANCE:
        if rel == g or rel.startswith(g):
            block("Blocked: governance files (.claude/, .githooks/, CLAUDE.md) "
                  "change only via the human (Phase 5 improvement loop).")

    for d in MIGRATION_DIRS:
        if rel.startswith(d):
            exists = os.path.exists(os.path.join(root, rel))
            if tool in ("Edit", "MultiEdit") or (tool == "Write" and exists):
                block("Blocked: migrations are forward-only. Never modify an "
                      "existing migration; create a NEW migration file instead.")


def written_text(ti):
    """Every piece of text this call would write, whichever tool produced it."""
    parts = []
    for k in CONTENT_KEYS:
        v = ti.get(k)
        if v:
            parts.append(str(v))
    edits = ti.get("edits")
    if isinstance(edits, list):
        for e in edits:
            if not isinstance(e, dict):
                continue
            for k in EDIT_KEYS:
                v = e.get(k)
                if v:
                    parts.append(str(v))
    return "\n".join(parts)


def check_content(ti):
    text = written_text(ti)
    if not text:
        return
    for pat, name in PATTERNS:
        if re.search(pat, text):
            block(f"Blocked: content appears to contain a {name}. Secrets never "
                  f"go in source/docs/logs — use the platform's env/secret "
                  f"system and reference it by variable name.")
    check_postgres_urls(text)


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    if tool not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)

    ti = data.get("tool_input") or {}
    fp = ti.get("file_path", "") or ""
    if fp:
        root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        rel = os.path.relpath(os.path.abspath(fp), root).replace("\\", "/")
        check_path(tool, rel, root)

    check_content(ti)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"write_guard hook error (allowed): {e}", file=sys.stderr)
        sys.exit(0)
