#!/bin/sh
# Runs every browser test against the app in the repo root, with one line of progress per suite:
#   [ 3/22] test_colors                ok    24 checks    9s
# Failing checks are printed under their suite. -v prints every check live as it runs.
# Setup once: python3 -m venv .venv && .venv/bin/pip install -r tests/requirements.txt && .venv/bin/playwright install chromium
# Optional: .venv/bin/playwright install webkit  (adds a real Safari-engine playback check to test_keep_awake.py)
set -u
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
VERBOSE=0; [ "${1:-}" = "-v" ] && VERBOSE=1
mkdir -p tests/screenshots
LOG=$(mktemp "${TMPDIR:-/tmp}/sleepclock-tests.XXXXXX")
trap 'rm -f "$LOG"' EXIT
total=$(ls tests/test_*.py | wc -l | tr -d ' ')
failed=''; i=0; t0=$(date +%s)
for t in tests/test_*.py; do
  i=$((i + 1)); name=$(basename "$t" .py); s=$(date +%s)
  printf '[%2d/%d] %-26s ' "$i" "$total" "$name"
  if [ $VERBOSE = 1 ]; then
    echo
    { "$PY" -u "$t" . tests/screenshots 2>&1; echo "__EXIT $?"; } | tee "$LOG" | grep -v '^__EXIT' | sed 's/^/    /'
    code=$(sed -n 's/^__EXIT //p' "$LOG")
    printf '%34s' ''
  else
    "$PY" -u "$t" . tests/screenshots > "$LOG" 2>&1; code=$?
  fi
  secs=$(($(date +%s) - s))
  if [ "$code" = 0 ]; then
    printf 'ok   %4d checks %4ds\n' "$(grep -c '^PASS ' "$LOG")" "$secs"
  else
    failed="$failed $name"
    printf 'FAIL             %4ds\n' "$secs"
    grep -E '^FAIL |Error|Traceback' "$LOG" | sed 's/^/    /'
  fi
done
nf=$(echo $failed | wc -w | tr -d ' ')
echo "done in $(($(date +%s) - t0))s: $((total - nf)) of $total suites passed${failed:+ (failed:$failed)}"
if [ "$nf" = 0 ]; then echo 'RESULT PASS'; exit 0; else echo 'RESULT FAIL'; exit 1; fi
