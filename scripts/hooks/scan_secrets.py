#!/usr/bin/env python3
"""PreToolUse hook for Edit|Write|MultiEdit.
Scans the content being written for common credential patterns; exit 2 blocks.
Conservative patterns to keep false positives low. Extend per stack."""
import json, re, sys

PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub personal access token"),
    (r"gho_[A-Za-z0-9]{36}", "GitHub OAuth token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"sk_live_[A-Za-z0-9]{20,}", "Stripe live secret key"),
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "Anthropic API key"),
    (r"(?i)service_role[a-z_]*[\"']?\s*[:=]\s*[\"']?eyJ[A-Za-z0-9_-]{20,}", "Supabase service-role JWT"),
    (r"(?i)sb_secret_[A-Za-z0-9_-]{20,}", "Supabase secret API key"),
]

def main():
    data = json.load(sys.stdin)
    ti = data.get("tool_input") or {}
    text = " ".join(str(ti.get(k, "")) for k in ("content", "new_string", "new_str", "file_text"))
    for pat, name in PATTERNS:
        if re.search(pat, text):
            print(f"Blocked: content appears to contain a {name}. Secrets never go in "
                  f"source/docs/logs — use the platform's env/secret system and reference "
                  f"it by variable name.", file=sys.stderr)
            sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"scan_secrets hook error (allowed): {e}", file=sys.stderr)
        sys.exit(0)
