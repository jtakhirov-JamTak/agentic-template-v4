"""Behaviour + contract tests for .githooks/pre-commit.

Runs the hook script directly with bash in a temp working directory. It
deliberately does NOT go through a real `git commit`: this repo's
`core.hooksPath` is unset, so the hook does not fire here at all. (The mode is
100755 as of 2026-08-26, which makes it executable in clones that wire it; that
fixed a real defect but changes nothing for this repo, and nothing here depends
on the mode either way, since bash is invoked explicitly.) These tests cover the
script's LOGIC, not its installation. Do not read a green run as evidence that
the hook is wired up.

`npm` and `node` are shimmed onto PATH so cases are hermetic and fast.

  python scripts/hooks/test_pre_commit.py
  python scripts/hooks/test_pre_commit.py --mutate
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.normpath(os.path.join(HERE, "..", "..", ".githooks", "pre-commit"))

VERIFY_PKG = '{"name":"x","scripts":{"verify":"echo verifying"}}'

# (package.json content or None, npm shim exit code, expected exit, label)
CASES = [
    (None, 0, 0, "no package.json allows"),
    ('{"name":"x","scripts":{"test":"jest"}}', 0, 1, "verify missing blocks"),
    ('{"name":"x","dependencies":{"verify":"^1.0.0"}}', 0, 1,
     "verify as dependency name blocks"),
    (VERIFY_PKG, 0, 0, "verify green allows"),
    (VERIFY_PKG, 1, 1, "verify red blocks"),
    ('{not json', 0, 1, "unparseable package.json blocks"),
]

# Restoring the old fail-open branch must turn exactly these red. Hardcoded, not
# derived from a label prefix: a claim that updates itself cannot be wrong.
MUTATION_ANCHOR = (
    '  echo "[pre-commit] Add one, or make this commit before package.json exists." >&2\n'
    "  exit 1\n"
    "fi"
)
MUTATION_PATCH = (
    '  echo "[pre-commit] Add one, or make this commit before package.json exists." >&2\n'
    "  exit 0\n"
    "fi"
)
MUTATION_EXPECT_RED = {
    "verify missing blocks",
    "verify as dependency name blocks",
}

# The truthfulness requirements this rewrite exists to satisfy.
MUST_NOT_CONTAIN = ["red code cannot be committed", "shell_guard"]
MUST_CONTAIN = ["CI is the backstop", "drift"]


def _shim_dir(root, npm_exit):
    binp = os.path.join(root, "shimbin")
    os.makedirs(binp, exist_ok=True)
    npm = os.path.join(binp, "npm")
    with open(npm, "w", newline="\n") as fh:
        fh.write("#!/usr/bin/env bash\nexit %d\n" % npm_exit)
    os.chmod(npm, 0o755)
    return binp


def run(hook, pkg, npm_exit):
    root = tempfile.mkdtemp(prefix="precommit-")
    work = os.path.join(root, "work")
    os.makedirs(work)
    if pkg is not None:
        with open(os.path.join(work, "package.json"), "w", newline="\n") as fh:
            fh.write(pkg)
    env = dict(os.environ)
    env["PATH"] = _shim_dir(root, npm_exit) + os.pathsep + env.get("PATH", "")
    try:
        p = subprocess.run(["bash", hook], cwd=work, env=env,
                           capture_output=True, text=True)
        return p.returncode
    finally:
        shutil.rmtree(root, ignore_errors=True)


def behaviour(hook, quiet=False):
    failures = []
    for pkg, npm_exit, expect, label in CASES:
        got = run(hook, pkg, npm_exit)
        ok = got == expect
        if not ok:
            failures.append(label)
        if not quiet and not ok:
            print("  FAIL %-38s expected %d, got %d" % (label, expect, got))
    if not quiet:
        print("behaviour: %d/%d passed" % (len(CASES) - len(failures), len(CASES)))
    return failures


def contract():
    with open(HOOK, encoding="utf-8") as fh:
        text = fh.read()
    failures = []
    for needle in MUST_NOT_CONTAIN:
        if needle in text:
            failures.append("must not claim: %r" % needle)
    for needle in MUST_CONTAIN:
        if needle not in text:
            failures.append("must state: %r" % needle)
    if "exit 1" not in text:
        failures.append("hook has no failing branch at all")
    for line in failures:
        print("  FAIL contract: %s" % line)
    print("contract: %d/%d passed" % (
        len(MUST_NOT_CONTAIN) + len(MUST_CONTAIN) + 1 - len(failures),
        len(MUST_NOT_CONTAIN) + len(MUST_CONTAIN) + 1))
    return failures


def mutate():
    with open(HOOK, encoding="utf-8") as fh:
        original = fh.read()
    if behaviour(HOOK, quiet=True):
        print("mutation: SKIPPED - baseline is not green")
        return ["baseline not green"]
    if MUTATION_ANCHOR not in original:
        print("mutation: FAIL - anchor not found; the hook changed shape")
        return ["anchor missing"]

    root = tempfile.mkdtemp(prefix="precommit-mut-")
    patched = os.path.join(root, "pre-commit")
    with open(patched, "w", newline="\n") as fh:
        fh.write(original.replace(MUTATION_ANCHOR, MUTATION_PATCH))
    try:
        went_red = set(behaviour(patched, quiet=True))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    missing = MUTATION_EXPECT_RED - went_red
    extra = went_red - MUTATION_EXPECT_RED
    for label in sorted(missing):
        print("  FAIL survived the mutation: %s" % label)
    for label in sorted(extra):
        print("  FAIL unexpectedly red: %s" % label)
    print("mutation: %d/%d expected-red cases turned red" % (
        len(MUTATION_EXPECT_RED) - len(missing), len(MUTATION_EXPECT_RED)))
    return sorted(missing) + sorted(extra)


def main():
    if "--mutate" in sys.argv:
        return 1 if mutate() else 0
    failures = behaviour(HOOK) + contract()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
