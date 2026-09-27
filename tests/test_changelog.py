"""CHANGELOG.md and the app version stay in sync; every entry is well-formed; released versions have git tags."""
import os
import re
import subprocess
import sys

from harness import Checks

ROOT = sys.argv[1]
check = Checks()
html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
log = open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8').read()
app = re.search(r"var VERSION = '([^']+)';", html).group(1)
entries = re.findall(r'^## (\d+\.\d+(?:\.\d+)?) — (\d{4}-\d{2}-\d{2})\n((?:- .*\n?)+)', log, re.M)
versions = [e[0] for e in entries]

check('changelog has entries', len(entries) >= 1, versions)
check('newest changelog entry = the version the app shows (%s)' % app, versions[:1] == [app], versions[:1])
key = lambda v: tuple(int(x) for x in v.split('.'))  # noqa: E731
check('versions are newest first, no duplicates', versions == sorted(set(versions), key=key, reverse=True), versions)
check('dates never go forward as versions go back', [e[1] for e in entries] == sorted([e[1] for e in entries], reverse=True))
check('every "## x.y" heading is a well-formed entry with at least one bullet', len(re.findall(r'^## ', log, re.M)) == len(entries))

# every version except the newest (not tagged until it's merged) should have its git tag, if this is a git checkout
try:
    tags = set(subprocess.run(['git', '-C', ROOT, 'tag', '--list', 'v*'], capture_output=True, text=True, check=True).stdout.split())
except Exception:
    tags = None
if tags is not None:
    missing = ['v' + v for v in versions[1:] if key(v) >= (1, 3) and 'v' + v not in tags]
    check('older released versions (1.3 onwards) have git tags', not missing, missing)
sys.exit(check.finish())
