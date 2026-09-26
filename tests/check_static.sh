#!/bin/sh
# Syntax check (JavaScriptCore via osascript) + grep for features Safari 12 lacks. See REQUIREMENTS.md §1.
cd "$(dirname "$0")/.."
tmp="$(mktemp -t sleepclock).js"
python3 -c "import re,sys;s=open('index.html').read();open(sys.argv[1],'w').write(re.search(r'<script>(.*?)</script>',s,re.S).group(1))" "$tmp"
osascript -l JavaScript -e 'function run(a){new Function($.NSString.stringWithContentsOfFileEncodingError(a[0],4,null).js);return "syntax ok"}' "$tmp" || exit 1
if grep -nE "\?\.|\?\?|replaceAll|\.at\(|structuredClone|fromEntries|<dialog|[^-]gap:|inset:|aspect-ratio|focus-visible|=>|\blet |\bconst |\bclass " index.html sw.js | grep -v "Written for Safari"; then
  echo "forbidden features found (see above)"; exit 1
fi
echo "static ok"
