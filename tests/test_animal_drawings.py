"""Checks every animal drawing in index.html's ANIMAL DRAWINGS section (the <template id="animal-..."> blocks).

Static rules (safety, Safari 12, format) run on the raw SVG; render rules (fits the canvas, animates) run in the browser.
Any new animal pasted into index.html is checked automatically.
"""
import datetime
import re
import sys
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright

from harness import Checks, H, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
SVGNS = '{http://www.w3.org/2000/svg}'
ALLOWED = {'svg', 'g', 'path', 'circle', 'ellipse', 'rect', 'line', 'polyline', 'polygon',
           'defs', 'linearGradient', 'radialGradient', 'stop'}
MAX_BYTES = 6000
DK, LT = 'rgba(0,0,0,.55)', 'rgba(255,255,255,.22)'
# plain colour values Safari 12 understands: none, currentColor, #hex, rgb()/rgba(), or a gradient ref (no CSS vars / named colours)
COLOUR_OK = re.compile(r'^(none|currentColor|#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?|rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(,\s*[.0-9]+\s*)?\)|url\(#[A-Za-z][\w-]*\))$')

html = open(ROOT + '/index.html', encoding='utf-8').read()
section = re.search(r'<!-- =+ ANIMAL DRAWINGS =+.*?-->(.*?)<!-- =+ END ANIMAL DRAWINGS =+ -->', html, re.S)
check('ANIMAL DRAWINGS section present', section is not None)
templates = re.findall(r'<template id="animal-([^"]*)" data-name="([^"]*)" data-cat="([^"]*)">(.*?)</template>', section.group(1) if section else '', re.S)
CATS = ['Animals', 'Vehicles', 'Space', 'Nature', 'Food', 'Party', 'Christmas', 'Sports & people', 'Toys & characters', "Dev's Favourite"]
ANIMS = {'breathe', 'float', 'sway', 'rock', 'roll'}
check('at least 14 pictures', len(templates) >= 14, len(templates))
check('section holds only animal templates and comments',
      re.sub(r'<template id="animal-[^"]*" data-name="[^"]*" data-cat="[^"]*">.*?</template>|<!--.*?-->|\s+', '', section.group(1) if section else '', flags=re.S) == '')
ids = [t[0] for t in templates]
names = [t[1] for t in templates]
check('ids are unique: lower-case words, digits and hyphens', len(set(ids)) == len(ids) and all(re.match(r'^[a-z][a-z0-9-]*$', i) for i in ids), ids)
check('every picture has a known category, grouped in category order', all(t[2] in CATS for t in templates) and
      [t[2] for t in templates] == sorted([t[2] for t in templates], key=CATS.index), sorted({t[2] for t in templates}))
check('names are unique and non-empty', len(set(names)) == len(names) and all(n.strip() for n in names), names)

for aid, name, cat, src in templates:
    tag = aid + ': '
    src = src.strip()
    check(tag + 'size <= %d bytes' % MAX_BYTES, len(src.encode()) <= MAX_BYTES, len(src.encode()))
    # drawings come from the internet: no DTD/entities (blocks entity-expansion attacks before parsing)
    if re.search(r'<!(DOCTYPE|ENTITY)', src, re.I):
        check(tag + 'no DOCTYPE / ENTITY declarations', False)
        continue
    try:
        root = ET.fromstring(src)
    except ET.ParseError as e:
        check(tag + 'well-formed SVG', False, e)
        continue
    check(tag + 'root is <svg> with the shared canvas', root.tag == SVGNS + 'svg' and root.get('viewBox') == '-40 -40 280 280', root.attrib)
    bad_tags, bad_attrs, bad_colours, ids_found, refs = [], [], [], [], []
    for el in root.iter():
        t = el.tag.replace(SVGNS, '')
        if t not in ALLOWED:
            bad_tags.append(t)
        for k, v in el.attrib.items():
            k2 = k.split('}')[-1]
            if k2.lower().startswith('on') or k2 in ('href', 'style', 'class') or 'javascript:' in v.lower():
                bad_attrs.append('%s@%s' % (t, k2))
            if k2 in ('fill', 'stroke', 'stop-color') and not COLOUR_OK.match(v.strip()):
                bad_colours.append('%s=%s' % (k2, v))
            if k2 == 'id':
                ids_found.append((t, v))
            refs += re.findall(r'url\(#([^)]+)\)', v)
    check(tag + 'only plain SVG shapes/gradients (no script, image, text, filter, style, use)', not bad_tags, bad_tags)
    check(tag + 'no event handlers, links, inline styles or classes', not bad_attrs, bad_attrs)
    check(tag + 'colours are plain values (currentColor, #hex, rgb/rgba, gradient ref)', not bad_colours, bad_colours)
    check(tag + 'ids only on gradients, every url(#) ref resolves',
          all(t.endswith('Gradient') for t, _ in ids_found) and set(refs) <= {v for _, v in ids_found}, (ids_found, refs))
    check(tag + 'main colour follows the night colour (uses currentColor)', 'currentColor' in src)
    bodies = [el for el in root.iter() if el.get('data-part') == 'body']
    moves = [el for el in root.iter() if el.get('data-move') is not None]
    if root.get('data-anim') is not None:   # silhouette: the whole picture moves
        check(tag + 'whole-picture movement is known, with a pivot, and no parts',
              root.get('data-anim') in ANIMS and re.match(r'^-?[\d.]+ -?[\d.]+$', root.get('data-pivot') or '') and not bodies and not moves, root.attrib)
    else:                                   # cartoon: breathing body + twitching parts
        check(tag + 'exactly one breathing body group', len(bodies) == 1 and bodies[0].tag == SVGNS + 'g', len(bodies))
        check(tag + 'at least one twitch group with angle + pivot',
              len(moves) >= 1 and all(m.tag == SVGNS + 'g' and re.match(r'^-?\d+(\.\d+)?$', m.get('data-move')) and
                                      re.match(r'^-?[\d.]+ -?[\d.]+$', m.get('data-pivot') or '') for m in moves), len(moves))
    check(tag + 'no animation elements (the clock adds them)', not re.search(r'<(animate|set)', src))

# ---- render checks: every animal fits the canvas and animates in the app ----
srv, URL = serve(ROOT)
with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={'width': 1024, 'height': 768})
    errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(300)
    reg = p.evaluate("() => Object.keys(%s.night.ANIMALS)" % H)
    check('registry = template order', reg == ids, reg)
    for aid in ids:
        p.evaluate("(a) => %s.setS({night: {scene: 'animal', scenes: {animal: {animal: a}}}})" % H, aid)
        p.clock.run_for(1100)
        # measure the resting pose: SMIL runs on real time (not the fake clock), so an unpaused sample lands at a random
        # point of the motion, and edge-to-edge scenes breathe a few units past the canvas at their peak
        box = p.evaluate("""() => { var s = document.querySelector('#face svg'); s.pauseAnimations(); s.setCurrentTime(0);
            var g = s.getBBox(); return [g.x, g.y, g.x + g.width, g.y + g.height]; }""")
        check(aid + ': drawing fits inside the canvas', box[0] >= -40 and box[1] >= -40 and box[2] <= 240 and box[3] <= 240, [round(v) for v in box])
        info = p.evaluate("""() => { var s = document.querySelector('#face svg');
            var whole = s.querySelector('[data-whole] > animateTransform');
            return [s.getAttribute('data-animal'), !!s.querySelector('[data-part=body] > animateTransform') || !!whole,
                    s.querySelectorAll('[data-move] > animateTransform').length + (whole ? 1 : 0), getComputedStyle(s).color]; }""")
        check(aid + ': drawn in the night colour and moving', info[0] == aid and info[1] and info[2] >= 1 and info[3] == 'rgb(255, 59, 31)', info)
    check('no page errors', not errs, errs)
    b.close()
srv.shutdown()
sys.exit(check.finish())
