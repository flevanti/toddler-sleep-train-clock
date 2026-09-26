#!/bin/sh
# Runs every browser test against the app in the repo root.
# Setup once: python3 -m venv .venv && .venv/bin/pip install -r tests/requirements.txt && .venv/bin/playwright install chromium
set -u
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
mkdir -p tests/screenshots
fail=0
for t in tests/test_*.py; do
  echo "== $t"
  out=$("$PY" -u "$t" . tests/screenshots 2>&1) || fail=1
  printf '%s\n' "$out" | grep -E "FAIL|FAILURES|RESULT|Error"
done
exit $fail
