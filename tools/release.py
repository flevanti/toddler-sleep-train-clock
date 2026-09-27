#!/usr/bin/env python3
"""Start a new version: bump VERSION in index.html and add its entry at the top of CHANGELOG.md.

Usage (from the repo root, on the branch, before merging):
    python3 tools/release.py 1.7 "First change" "Second change" ...

After the branch is merged into main, tag the merge:
    git tag v1.7 && git push origin v1.7
"""
import datetime
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
CHANGELOG = os.path.join(ROOT, 'CHANGELOG.md')


def parse(v):
    return tuple(int(x) for x in v.split('.'))


def main(args):
    if len(args) < 2 or not re.match(r'^\d+\.\d+(\.\d+)?$', args[0]):
        sys.exit(__doc__)
    new, notes = args[0], args[1:]
    html = open(INDEX, encoding='utf-8').read()
    cur = re.search(r"var VERSION = '([^']+)';", html).group(1)
    if parse(new) <= parse(cur):
        sys.exit('new version %s must be greater than the current %s' % (new, cur))
    html = html.replace("var VERSION = '%s';" % cur, "var VERSION = '%s';" % new, 1)
    log = open(CHANGELOG, encoding='utf-8').read()
    entry = '## %s — %s\n%s\n\n' % (new, datetime.date.today().isoformat(), '\n'.join('- ' + n for n in notes))
    first = log.index('\n## ') + 1                     # insert above the newest version
    log = log[:first] + entry + log[first:]
    open(INDEX, 'w', encoding='utf-8').write(html)
    open(CHANGELOG, 'w', encoding='utf-8').write(log)
    print('version %s -> %s; CHANGELOG entry added. After merging into main: git tag v%s && git push origin v%s' % (cur, new, new, new))


if __name__ == '__main__':
    main(sys.argv[1:])
