#!/usr/bin/env python3
"""Build the web app manifest (embedded in index.html) and its icons.

Usage (from the repo root):   .venv/bin/python tools/make_manifest.py

The icon is the green morning face with its sun rays (the clock's "OK to get up" face), drawn as SVG and rendered
to 512 px PNGs in headless Chromium: one normal, one "maskable" with extra margin because Android crops app icons
into circles / squircles. The manifest (full screen, black background) goes into a data: URL in a
<link rel="manifest"> tag, so the clock still deploys as index.html + sw.js only.
"""
import base64
import json
import math
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from playwright.sync_api import sync_playwright  # noqa: E402

INDEX = os.path.join(ROOT, 'index.html')


def icon_svg(scale):
    """The morning face on dark green; scale < 1 leaves room for Android's icon masks."""
    rays = ''.join('<line x1="0" y1="-%d" x2="0" y2="-%d" transform="rotate(%d)"/>' % (round(200 * scale), round(236 * scale), a) for a in range(0, 360, 30))
    r = 150 * scale
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-256 -256 512 512" width="512" height="512">'
            '<rect x="-256" y="-256" width="512" height="512" fill="#0c3a1b"/>'
            '<g stroke="#ffd60a" stroke-width="%s" stroke-linecap="round">%s</g>' % (round(22 * scale), rays) +
            '<circle r="%s" fill="#34c759"/>' % r +
            '<circle cx="%s" cy="%s" r="%s" fill="#0d2a16"/><circle cx="%s" cy="%s" r="%s" fill="#0d2a16"/>' % (-0.36 * r, -0.2 * r, 0.12 * r, 0.36 * r, -0.2 * r, 0.12 * r) +
            '<path d="M%s %s Q0 %s %s %s Z" fill="#0d2a16"/>' % (-0.52 * r, 0.18 * r, 0.95 * r, 0.52 * r, 0.18 * r) +
            '</svg>')


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={'width': 512, 'height': 512})
        pngs = {}
        for name, scale in (('any', 1.0), ('maskable', 0.72)):   # maskable: keep everything inside the 80 % safe circle
            p.set_content('<body style="margin:0">%s</body>' % icon_svg(scale))
            pngs[name] = 'data:image/png;base64,' + base64.b64encode(p.locator('svg').screenshot(omit_background=False)).decode()
        b.close()
    manifest = {
        'name': 'Sleep Clock', 'short_name': 'Sleep Clock',
        'description': 'An "OK to wake" clock for toddlers: red at night, green when it\'s time to get up. Works offline.',
        'start_url': './', 'scope': './', 'display': 'fullscreen', 'display_override': ['fullscreen', 'standalone'],
        'orientation': 'any', 'background_color': '#000000', 'theme_color': '#000000',
        'icons': [{'src': pngs['any'], 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
                  {'src': pngs['maskable'], 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}],
    }
    link = '<link rel="manifest" href="data:application/manifest+json,%s">' % urllib.parse.quote(json.dumps(manifest, separators=(',', ':')), safe='')
    html = open(INDEX, encoding='utf-8').read()
    if '<link rel="manifest"' in html:
        html = re.sub(r'<link rel="manifest" href="[^"]*">', lambda m: link, html)
    else:
        html = html.replace('<title>', link + '\n<title>', 1)
    open(INDEX, 'w', encoding='utf-8').write(html)
    print('manifest written (%d KB, icons %s)' % (len(link) // 1024, ', '.join('%s %d KB' % (k, len(v) // 1024) for k, v in pngs.items())))


if __name__ == '__main__':
    main()
