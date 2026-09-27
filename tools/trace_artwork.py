#!/usr/bin/env python3
"""Turn any picture in artwork/incoming/ (SVG with colours/styles/text, PNG, JPG) into a potrace silhouette SVG,
so tools/import_artwork.py can take it like the rest.

Usage (from the repo root):   .venv/bin/python tools/trace_artwork.py [file ...]
Needs potrace (brew install potrace) and the test venv (Playwright + Chromium).

Each input is drawn at high resolution on white in headless Chromium, dark pixels (luminance < 50 %) become the
shape and light ones holes, then potrace traces it. The result replaces the file in incoming/ as <name>.svg and the
original is moved to artwork/sources/. Files already traced by potrace are left alone.
"""
import os
import shutil
import subprocess
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCOMING = os.path.join(ROOT, 'artwork', 'incoming')
SOURCES = os.path.join(ROOT, 'artwork', 'sources')
SIZE = 1200
IMG_EXT = ('.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp')

# Draw the image into a canvas and return a plain PBM (P1): 1 = dark.
TO_PBM = """async ([url, size]) => {
  const img = new Image(); img.src = url; await img.decode();
  const k = Math.min(size / img.naturalWidth, size / img.naturalHeight), w = Math.round(img.naturalWidth * k), h = Math.round(img.naturalHeight * k);
  const c = document.createElement('canvas'); c.width = w + 40; c.height = h + 40;
  const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.drawImage(img, 20, 20, w, h);
  const d = g.getImageData(0, 0, c.width, c.height).data; const rows = [];
  for (let y = 0; y < c.height; y++) { let r = ''; for (let x = 0; x < c.width; x++) { const i = (y * c.width + x) * 4;
    r += (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2] < 128) ? '1' : '0'; } rows.push(r); }
  return 'P1\\n' + c.width + ' ' + c.height + '\\n' + rows.join('\\n') + '\\n';
}"""


def main(names):
    if not shutil.which('potrace'):
        sys.exit('potrace not found: brew install potrace')
    os.makedirs(SOURCES, exist_ok=True)
    files = names or sorted(f for f in os.listdir(INCOMING) if f.lower().endswith(IMG_EXT))
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page()
        page.goto('about:blank')
        for f in files:
            src = os.path.join(INCOMING, f)
            if f.endswith('.svg') and 'potrace' in open(src, encoding='utf-8', errors='replace').read():
                print('already a potrace silhouette:', f)
                continue
            url = 'data:%s;base64,%s' % ('image/svg+xml' if f.endswith('.svg') else 'image/png',
                                         __import__('base64').b64encode(open(src, 'rb').read()).decode())
            pbm = page.evaluate(TO_PBM, [url, SIZE])
            base = os.path.splitext(f)[0]
            tmp = os.path.join(INCOMING, base + '.pbm')
            open(tmp, 'w').write(pbm)
            out = os.path.join(INCOMING, base + '.traced.svg')
            subprocess.run(['potrace', '-s', '-t', '8', '-O', '0.4', '-o', out, tmp], check=True)   # -t: drop specks
            os.remove(tmp)
            shutil.move(src, os.path.join(SOURCES, f))
            os.rename(out, os.path.join(INCOMING, base + '.svg'))
            print('traced:', f, '->', base + '.svg')
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:])
