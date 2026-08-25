#!/usr/bin/env python3
"""Regression + mutation test for write_guard.py.

Run:  python scripts/hooks/test_write_guard.py
      python scripts/hooks/test_write_guard.py --mutate

BLOCK cases must exit 2; ALLOW cases must exit 0. Both directions are
represented for every rule, so a green run means the rule fires AND does not
over-fire. Add a case here before changing any pattern.

--mutate removes the edits[] traversal — the exact hole that existed while
protect_paths.py and scan_secrets.py split this job between them — and asserts
that EXACTLY the MultiEdit-secret cases turn red. If a MultiEdit case survives
that mutation it was never testing the traversal; if an unrelated case moves,
the traversal is doing more than claimed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "write_guard.py")

MUTATION_ANCHOR = '    edits = ti.get("edits")'
MUTATION_PATCH = "    edits = None"

# Named explicitly rather than derived from a label prefix. A prefix rule would
# silently absorb any new MultiEdit case, which defeats the point: the set is
# supposed to be a claim about which cases the traversal protects, and a claim
# that updates itself cannot be wrong.
MUTATION_EXPECT_RED = {
    "secret in MultiEdit first entry",
    "secret in MultiEdit middle entry",
    "secret in MultiEdit last entry",
    "secret in MultiEdit new_str key",
    "pg real credential in a later MultiEdit entry still blocked",
}

# Representative secrets, one per class. Fake values, correct shapes.
#
# Deliberately kept SHORTER and more obviously fake than a real key. These have
# to satisfy two opposing readers: write_guard.py, whose Stripe pattern needs
# {10,} alphanumerics after the prefix, and GitHub push protection, whose Stripe
# detector wants {24,} and rejected the push when these fixtures were full
# length. A visibly-fake FAKE0000... body matches ours and not theirs.
#
# Fixed this way rather than by clicking GitHub's "allow this secret" URL: that
# allowlist entry would persist on the repo and could mask a genuine key leaking
# from this same file later. If write_guard's minimum length ever rises above
# these, lengthen them with more zeros -- never with realistic-looking entropy.
AWS = "AKIAIOSFODNN7EXAMPLE"  # AWS's own documented example key
STRIPE_SK = "sk_live_FAKE00000000"
STRIPE_RK = "rk_test_FAKE00000000"
STRIPE_PK = "pk_live_FAKE00000000"   # publishable — must be ALLOWED
WHSEC = "whsec_FAKE0000000000000"
SNTRYS = "sntrys_FAKE00000000000000000000"
PGURL = "postgres://appuser:s3cr3tpw@db.internal:5432/app"
PGURL_QL = "postgresql://appuser:s3cr3tpw@db.internal:5432/app"
SAFE = "export const RETRIES = 3;\n"


def cases(root):
    """-> [(tool, tool_input, expect_exit, label)]"""
    p = lambda *a: os.path.join(root, *a)
    return [
        # ---- safe writes, every tool ----
        ("Write", {"file_path": p("src", "a.ts"), "content": SAFE}, 0, "Write safe"),
        ("Edit", {"file_path": p("src", "a.ts"), "new_string": SAFE}, 0, "Edit safe"),
        ("MultiEdit", {"file_path": p("src", "a.ts"),
                       "edits": [{"old_string": "x", "new_string": SAFE},
                                 {"old_string": "y", "new_string": SAFE}]},
         0, "MultiEdit safe"),

        # ---- secrets in the flat fields ----
        ("Write", {"file_path": p("src", "a.ts"), "content": f"KEY={AWS}"}, 2,
         "secret in Write content"),
        ("Edit", {"file_path": p("src", "a.ts"), "new_string": f"KEY={AWS}"}, 2,
         "secret in Edit new_string"),
        ("Edit", {"file_path": p("src", "a.ts"), "new_str": f"KEY={AWS}"}, 2,
         "secret in Edit new_str"),
        ("Write", {"file_path": p("src", "a.ts"), "file_text": f"KEY={AWS}"}, 2,
         "secret in Write file_text"),

        # ---- secrets inside edits[]: first, middle, last ----
        # Position matters: a traversal that only checked edits[0] would pass
        # two of these three.
        ("MultiEdit", {"file_path": p("src", "a.ts"),
                       "edits": [{"old_string": "x", "new_string": f"K={AWS}"},
                                 {"old_string": "y", "new_string": SAFE},
                                 {"old_string": "z", "new_string": SAFE}]},
         2, "secret in MultiEdit first entry"),
        ("MultiEdit", {"file_path": p("src", "a.ts"),
                       "edits": [{"old_string": "x", "new_string": SAFE},
                                 {"old_string": "y", "new_string": f"K={AWS}"},
                                 {"old_string": "z", "new_string": SAFE}]},
         2, "secret in MultiEdit middle entry"),
        ("MultiEdit", {"file_path": p("src", "a.ts"),
                       "edits": [{"old_string": "x", "new_string": SAFE},
                                 {"old_string": "y", "new_string": SAFE},
                                 {"old_string": "z", "new_string": f"K={AWS}"}]},
         2, "secret in MultiEdit last entry"),
        ("MultiEdit", {"file_path": p("src", "a.ts"),
                       "edits": [{"old_string": "x", "new_str": f"K={AWS}"}]},
         2, "secret in MultiEdit new_str key"),
        # An old_string may legitimately contain a secret being REMOVED.
        ("MultiEdit", {"file_path": p("src", "a.ts"),
                       "edits": [{"old_string": f"K={AWS}", "new_string": SAFE}]},
         0, "secret only in MultiEdit old_string is a removal"),

        # ---- secret classes ----
        ("Write", {"file_path": p("src", "a.ts"), "content": STRIPE_SK}, 2, "stripe sk_live"),
        ("Write", {"file_path": p("src", "a.ts"), "content": STRIPE_RK}, 2, "stripe rk_test"),
        ("Write", {"file_path": p("src", "a.ts"), "content": WHSEC}, 2, "webhook signing secret"),
        ("Write", {"file_path": p("src", "a.ts"), "content": SNTRYS}, 2, "sentry token"),
        ("Write", {"file_path": p("src", "a.ts"), "content": PGURL}, 2, "postgres url with password"),
        ("Write", {"file_path": p("src", "a.ts"), "content": PGURL_QL}, 2, "postgresql url with password"),
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "-----BEGIN RSA PRIVATE KEY-----\nabc\n"}, 2, "private key"),
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "token = ghp_" + "a" * 36}, 2, "github pat"),
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "SUPABASE_SERVICE_ROLE_KEY=eyJ" + "a" * 30}, 2,
         "supabase service-role jwt"),

        # ---- secret classes that must NOT fire ----
        ("Write", {"file_path": p("src", "a.ts"), "content": STRIPE_PK}, 0,
         "stripe pk_live publishable allowed"),
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "pk_test_51H8ZqRLkdIwHu7ixHTQzKmSs"}, 0,
         "stripe pk_test publishable allowed"),
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "postgres://localhost:5432/app"}, 0,
         "postgres url without credentials allowed"),
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "postgresql://appuser@db.internal/app"}, 0,
         "postgres url without password allowed"),

        # ---- postgres: real credential vs documentation placeholder ----
        # Realistic secrets must still BLOCK, whatever the username looks like.
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "postgres://user:8Fq2LmZp1XvT@db.internal/app"}, 2,
         "pg real password with placeholder username still blocked"),
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "postgres://postgres:hunter2secret9@localhost/db"}, 2,
         "pg real password with common username still blocked"),
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "postgresql://svc_billing:Tq!7vX2m@10.0.0.4:5432/prod"}, 2,
         "pg real credential in docs still blocked"),
        # A weak-looking password beside a REAL username is still a leak: the
        # exemption requires the whole URL to read as illustrative.
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "postgres://svc_billing:password@prod-db.internal/app"}, 2,
         "pg placeholder password with real username still blocked"),
        # Obvious documentation placeholders must PASS.
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "postgres://user:password@host"}, 0,
         "pg canonical placeholder allowed"),
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "postgresql://user:password@host:5432/dbname"}, 0,
         "pg placeholder with port and db allowed"),
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "postgres://username:changeme@host/db"}, 0,
         "pg changeme placeholder allowed"),
        # Templated passwords cannot be a literal credential, so the username
        # does not need to look illustrative.
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "postgres://appuser:${DB_PASSWORD}@db.internal:5432/app"}, 0,
         "pg templated ${VAR} password allowed"),
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "postgres://svc_billing:<password>@prod-db/app"}, 0,
         "pg templated <password> allowed"),
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "postgres://appuser:%DB_PASSWORD%@db/app"}, 0,
         "pg templated %VAR% allowed"),
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "postgres://appuser:****@db/app"}, 0,
         "pg redacted password allowed"),
        # A placeholder line next to a real one must NOT launder the real one.
        ("Write", {"file_path": p("docs", "setup.md"),
                   "content": "Example: postgres://user:password@host\n"
                              "Actual:  postgres://svc:Rk9wPz2Qa@prod/app\n"}, 2,
         "pg placeholder does not launder a real credential beside it"),
        ("MultiEdit", {"file_path": p("docs", "setup.md"),
                       "edits": [{"old_string": "a", "new_string": "postgres://user:password@host"},
                                 {"old_string": "b", "new_string": "postgres://svc:Rk9wPz2Qa@prod/app"}]},
         2, "pg real credential in a later MultiEdit entry still blocked"),
        ("Write", {"file_path": p("src", "a.ts"),
                   "content": "const key = process.env.STRIPE_SECRET_KEY"}, 0,
         "referencing a secret by env-var name allowed"),

        # ---- governance ----
        ("Write", {"file_path": p("CLAUDE.md"), "content": SAFE}, 2, "governance CLAUDE.md"),
        ("Edit", {"file_path": p(".claude", "settings.json"), "new_string": SAFE}, 2,
         "governance .claude/"),
        ("Edit", {"file_path": p(".githooks", "pre-commit"), "new_string": SAFE}, 2,
         "governance .githooks/"),
        ("Write", {"file_path": p("docs", "PROGRESS.md"), "content": SAFE}, 0,
         "ordinary docs write allowed"),

        # ---- migrations: forward-only ----
        ("Edit", {"file_path": p("supabase", "migrations", "001_existing.sql"),
                  "new_string": SAFE}, 2, "edit existing migration"),
        ("MultiEdit", {"file_path": p("supabase", "migrations", "001_existing.sql"),
                       "edits": [{"old_string": "x", "new_string": SAFE}]}, 2,
         "multiedit existing migration"),
        ("Write", {"file_path": p("supabase", "migrations", "001_existing.sql"),
                   "content": SAFE}, 2, "overwrite existing migration"),
        ("Write", {"file_path": p("supabase", "migrations", "002_new.sql"),
                   "content": SAFE}, 0, "new migration allowed"),

        # ---- env files ----
        ("Write", {"file_path": p(".env"), "content": SAFE}, 2, ".env blocked"),
        ("Write", {"file_path": p(".env.local"), "content": SAFE}, 2, ".env.local blocked"),
        ("Edit", {"file_path": p(".env.production"), "new_string": SAFE}, 2,
         ".env.production blocked"),
        # env.example — no leading dot — is the non-secret name (handoff B3).
        ("Write", {"file_path": p("env.example"), "content": "STRIPE_SECRET_KEY="}, 0,
         "env.example allowed"),
        ("Edit", {"file_path": p("env.example"), "new_string": "DATABASE_URL="}, 0,
         "env.example edit allowed"),
        # B3 RESOLVED: .env.example is blocked here AND by shell_guard.py AND
        # ignored by .gitignore. All three layers now agree that every `.env*`
        # is secret and that the non-secret file is `env.example`. These cases
        # are what proves the layers stopped disagreeing: if a carve-out is ever
        # restored to shell_guard, its suite goes red while these stay green,
        # which is the signal that the two drifted apart again.
        ("Write", {"file_path": p(".env.example"), "content": SAFE}, 2,
         ".env.example blocked (B3: no carve-out in any layer)"),
        ("Write", {"file_path": p(".env.sample"), "content": SAFE}, 2,
         ".env.sample blocked (B3)"),
        ("Write", {"file_path": p(".env.template"), "content": SAFE}, 2,
         ".env.template blocked (B3)"),
        ("Write", {"file_path": p("config", "env.example"), "content": SAFE}, 0,
         "env.example in a subdir allowed (B3)"),
        ("Write", {"file_path": p("certs", "server.pem"), "content": SAFE}, 2, ".pem blocked"),
        ("Write", {"file_path": p("id_rsa"), "content": SAFE}, 2, "id_rsa blocked"),

        # ---- tools this hook does not govern ----
        ("Read", {"file_path": p(".env")}, 0, "Read is not this hook's job"),
        ("Bash", {"command": f"echo {AWS}"}, 0, "Bash is not this hook's job"),
    ]


def run(guard, tool, tool_input, root):
    payload = {"tool_name": tool, "tool_input": tool_input}
    env = dict(os.environ, CLAUDE_PROJECT_DIR=root)
    p = subprocess.run([sys.executable, guard], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, (p.stderr or "").strip()


def make_root():
    root = tempfile.mkdtemp(prefix="write_guard_test_")
    os.makedirs(os.path.join(root, "supabase", "migrations"))
    os.makedirs(os.path.join(root, "src"))
    with open(os.path.join(root, "supabase", "migrations", "001_existing.sql"), "w") as fh:
        fh.write("-- already applied\n")
    return root


def results(guard, root):
    return {label: (run(guard, tool, ti, root)[0] == want)
            for tool, ti, want, label in cases(root)}


def normal():
    root = make_root()
    try:
        failures = []
        cs = cases(root)
        for tool, ti, want, label in cs:
            got, err = run(GUARD, tool, ti, root)
            if got != want:
                failures.append((label, tool, want, got, err[:140]))
        print(f"{len(cs) - len(failures)}/{len(cs)} passed")
        if failures:
            print("\nFAILURES:")
            for label, tool, want, got, err in failures:
                print(f"  [{label}] {tool}: want exit {want}, got {got}. stderr: {err}")
            return 1
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


def mutate():
    src = open(GUARD, encoding="utf-8").read()
    if src.count(MUTATION_ANCHOR) != 1:
        print(f"MUTATION SETUP FAILED: anchor not found exactly once:\n  {MUTATION_ANCHOR}")
        return 1

    root = make_root()
    mutant = None
    try:
        baseline = results(GUARD, root)
        unhealthy = sorted(l for l, ok in baseline.items() if not ok)
        if unhealthy:
            print("Run the normal suite first — it is not green:")
            for l in unhealthy:
                print(f"  {l}")
            return 1

        fd, mutant = tempfile.mkstemp(suffix="_mutant.py", text=True)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src.replace(MUTATION_ANCHOR, MUTATION_PATCH))
        after = results(mutant, root)
    finally:
        if mutant:
            os.unlink(mutant)
        shutil.rmtree(root, ignore_errors=True)

    expect_red = MUTATION_EXPECT_RED
    unknown = expect_red - set(baseline)
    if unknown:
        print("MUTATION SETUP FAILED: named labels that no case produces:")
        for l in sorted(unknown):
            print(f"  {l}")
        return 1
    went_red = {l for l, ok in after.items() if not ok}
    missing = expect_red - went_red
    extra = went_red - expect_red

    print("mutation: edits[] traversal removed")
    print(f"  expected red: {len(expect_red)}   actually red: {len(went_red)}")
    ok = True
    if missing:
        ok = False
        print("\n  STILL PASSING without the traversal — these were never testing it:")
        for l in sorted(missing):
            print(f"    {l}")
    if extra:
        ok = False
        print("\n  UNEXPECTEDLY red — the traversal affects cases outside the named set:")
        for l in sorted(extra):
            print(f"    {l}")
    if ok:
        print("  exactly the MultiEdit-secret cases turned red; every other case held.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(mutate() if "--mutate" in sys.argv else normal())
