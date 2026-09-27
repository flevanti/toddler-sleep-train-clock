#!/usr/bin/env python3
"""Convert silhouette SVGs into Night picture templates in index.html.

Usage (from the repo root):   python3 tools/import_artwork.py

1. Moves new files from artwork/incoming/ to artwork/originals/ (names become the picture names).
2. Converts every artwork/originals/*.svg: flattens the traced outline, fits it on the clock's canvas
   (viewBox -40 -40 280 280, standing on the ground at y=210), simplifies it to a small path in currentColor.
3. Rewrites the block between the IMPORTED ARTWORK markers in index.html (one <template> per picture).
Categories come from artwork/CATALOG.md; the gentle movement comes from the category and name (see motion()).
Not deployed: the clock only needs index.html and sw.js.
"""
import math
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCOMING = os.path.join(ROOT, 'artwork', 'incoming')
ORIGINALS = os.path.join(ROOT, 'artwork', 'originals')
CATALOG = os.path.join(ROOT, 'artwork', 'CATALOG.md')
INDEX = os.path.join(ROOT, 'index.html')
BEGIN, END = '<!-- BEGIN IMPORTED ARTWORK', '<!-- END IMPORTED ARTWORK -->'

TARGET_BYTES = 2800          # aim per picture
MAX_BYTES = 6000             # hard limit (tests/test_animal_drawings.py)
BOX = (-25.0, -25.0, 225.0, 210.0)   # fit area: x0, y0, x1, ground y
CARTOON_IDS = {'bunny', 'bear', 'cat', 'owl', 'dog', 'turtle', 'hedgehog', 'chicken', 'pig', 'horse', 'cow', 'robin', 'blackbird', 'lion'}
CATEGORY_ORDER = ['Animals', 'Vehicles', 'Space', 'Nature', 'Food', 'Party', 'Christmas', 'Sports & people', 'Toys & characters']
MERGE = {'Sports': 'Sports & people', 'People': 'Sports & people', 'Characters': 'Toys & characters', 'Fantasy': 'Toys & characters',
         'Toys': 'Toys & characters', 'Things': 'Toys & characters'}


# ---------- reading potrace SVGs ----------
def parse_transform(t):
    """translate/scale/matrix chain -> 2x3 matrix (a, b, c, d, e, f)."""
    m = (1, 0, 0, 1, 0, 0)
    for name, args in re.findall(r'(\w+)\(([^)]*)\)', t or ''):
        v = [float(x) for x in re.split(r'[\s,]+', args.strip()) if x]
        if name == 'translate':
            n = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == 'scale':
            n = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == 'matrix':
            n = tuple(v)
        else:
            raise ValueError('unsupported transform ' + name)
        a, b, c, d, e, f = m
        A, B, C, D, E, F = n
        m = (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D, a * E + c * F + e, b * E + d * F + f)
    return m


def apply(m, p):
    return (m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5])


def cubic(p0, p1, p2, p3, n=8):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def path_points(d):
    """Path data -> list of closed polylines (untransformed). Supports M L H V C S Q Z, absolute and relative."""
    toks = re.findall(r'[MmLlHhVvCcSsQqZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?', d)
    subs, cur, pos, start, last_c, cmd, i = [], [], (0.0, 0.0), (0.0, 0.0), None, None, 0

    def num():
        nonlocal i
        i += 1
        return float(toks[i - 1])

    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in 'Zz':
                if cur:
                    subs.append(cur)
                cur, pos, last_c = [], start, None
                continue
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = pos if rel else (0.0, 0.0)
        if C == 'M':
            if cur:
                subs.append(cur)
            pos = (ox + num(), oy + num())
            start, cur, last_c = pos, [pos], None
            cmd = 'l' if rel else 'L'
        elif C == 'L':
            pos = (ox + num(), oy + num())
            cur.append(pos)
            last_c = None
        elif C == 'H':
            pos = ((pos[0] if rel else 0) + num(), pos[1])
            cur.append(pos)
            last_c = None
        elif C == 'V':
            pos = (pos[0], (pos[1] if rel else 0) + num())
            cur.append(pos)
            last_c = None
        elif C == 'C':
            p1 = (ox + num(), oy + num())
            p2 = (ox + num(), oy + num())
            p3 = (ox + num(), oy + num())
            cur += cubic(pos, p1, p2, p3)
            last_c, pos = p2, p3
        elif C == 'S':
            p1 = (2 * pos[0] - last_c[0], 2 * pos[1] - last_c[1]) if last_c else pos
            p2 = (ox + num(), oy + num())
            p3 = (ox + num(), oy + num())
            cur += cubic(pos, p1, p2, p3)
            last_c, pos = p2, p3
        elif C == 'Q':
            q = (ox + num(), oy + num())
            p3 = (ox + num(), oy + num())
            cur += cubic(pos, (pos[0] + 2 / 3 * (q[0] - pos[0]), pos[1] + 2 / 3 * (q[1] - pos[1])),
                         (p3[0] + 2 / 3 * (q[0] - p3[0]), p3[1] + 2 / 3 * (q[1] - p3[1])), p3)
            last_c, pos = None, p3
        else:
            raise ValueError('unsupported path command ' + cmd)
    if cur:
        subs.append(cur)
    return subs


def read_svg(path):
    s = open(path, encoding='utf-8').read()
    if re.search(r'<(script|image|foreignObject|use|style)\b', s, re.I) or re.search(r'\son\w+=', s):
        raise ValueError('refusing: script/image/style/use/event handler inside')
    polys = []
    g = re.search(r'<g\b[^>]*transform="([^"]*)"', s)
    m = parse_transform(g.group(1) if g else '')
    for d in re.findall(r'<path\b[^>]*\sd="([^"]+)"', s):
        for sub in path_points(d):
            polys.append([apply(m, p) for p in sub])
    if not polys:
        raise ValueError('no paths')
    return polys


# ---------- fitting and simplifying ----------
def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1e-9
    best, idx = -1, 0
    for i in range(1, len(pts) - 1):
        dist = abs(dy * (pts[i][0] - a[0]) - dx * (pts[i][1] - a[1])) / L
        if dist > best:
            best, idx = dist, i
    if best <= eps:
        return [a, b]
    return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps)


def fit(polys):
    xs = [p[0] for s in polys for p in s]
    ys = [p[1] for s in polys for p in s]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = min((BOX[2] - BOX[0]) / (x1 - x0), (BOX[3] - BOX[1]) / (y1 - y0))
    cx = (x0 + x1) / 2
    return [[((x - cx) * k + 100, (y - y1) * k + BOX[3]) for x, y in s] for s in polys]


def encode(polys, eps):
    parts = []
    for s in polys:
        w = max(p[0] for p in s) - min(p[0] for p in s)
        h = max(p[1] for p in s) - min(p[1] for p in s)
        if max(w, h) < 2.2 * eps + 1:        # specks smaller than the simplification step
            continue
        # closed outline: split at the point farthest from the start, simplify both halves
        k = max(range(len(s)), key=lambda i: (s[i][0] - s[0][0]) ** 2 + (s[i][1] - s[0][1]) ** 2)
        pts = rdp(s[:k + 1], eps)[:-1] + rdp(s[k:] + [s[0]], eps)[:-1]
        if len(pts) < 3:
            continue
        r = [(round(x, 1), round(y, 1)) for x, y in pts]
        out = 'M%s %s' % (fmt(r[0][0]), fmt(r[0][1]))
        prev = r[0]
        for p in r[1:]:
            out += 'l%s %s' % (fmt(p[0] - prev[0]), fmt(p[1] - prev[1]))
            prev = p
        parts.append(out + 'z')
    return ''.join(parts).replace(' -', '-')


def fmt(v):
    """Shortest form of a 1-decimal number: 3, 2.5, .5, -.5"""
    s = ('%.1f' % round(v, 1)).rstrip('0').rstrip('.')
    s = '0' if s in ('', '-0') else s
    return s.replace('-0.', '-.') if s.startswith('-0.') else s.replace('0.', '.', 1) if s.startswith('0.') else s


# ---------- naming, categories, movement ----------
def catalog():
    cats = {}
    if os.path.exists(CATALOG):
        for name, cat in re.findall(r'^\| ([a-z0-9-]+) \| ([^|]+?) \|', open(CATALOG, encoding='utf-8').read(), re.M):
            cats[name] = MERGE.get(cat.strip(), cat.strip())
    return cats


def display_name(slug):
    words = slug.split('-')
    if words[-1].isdigit():
        return ' '.join(words[:-1]).capitalize() + ' ' + words[-1]
    return ' '.join(words).capitalize()


def motion(slug, cat):
    """Whole-picture movement: breathe (animals, default), float, sway, rock, roll."""
    if re.search(r'balloon|boat|aeroplane|biplane|submarine|rocket|shuttle|saturn|whale|fish|jellyfish|flying|dragonfly|butterfly|mermaid', slug):
        return 'float'
    if cat == 'Nature' or re.search(r'christmas|tree|forest|flower|sunflower|clover', slug):
        return 'sway'
    if re.search(r'ball$|^football$|^baseball$', slug):
        return 'roll'
    if cat == 'Vehicles':
        return 'rock'
    return 'breathe'


def template(slug, cat, path):
    polys = fit(read_svg(path))
    eps, d = 0.35, ''
    while True:
        d = encode(polys, eps)
        if len(d) <= TARGET_BYTES or eps >= 2.5:
            break
        eps *= 1.25
    pid = slug + '-shape' if slug in CARTOON_IDS else slug
    anim = motion(slug, cat)
    xs = [float(v) for v in re.findall(r'M(-?[\d.]+)', d)] or [100]
    pivot = '100 210'
    if anim == 'roll':
        ys_all = [p[1] for s in polys for p in s]
        pivot = '%d %d' % (100, round((min(ys_all) + max(ys_all)) / 2))
    t = ('<template id="animal-%s" data-name="%s" data-cat="%s"><svg xmlns="http://www.w3.org/2000/svg" viewBox="-40 -40 280 280" '
         'data-anim="%s" data-pivot="%s">\n  <path fill="currentColor" d="%s"/>\n</svg></template>') % (pid, display_name(slug), cat, anim, pivot, d)
    return t, len(t.encode()), eps


def main():
    os.makedirs(ORIGINALS, exist_ok=True)
    for f in sorted(os.listdir(INCOMING)) if os.path.isdir(INCOMING) else []:
        if f.endswith('.svg'):
            if os.path.exists(os.path.join(ORIGINALS, f)):
                sys.exit('name already used in originals/: ' + f)
            shutil.move(os.path.join(INCOMING, f), os.path.join(ORIGINALS, f))
    cats = catalog()
    items = []
    for f in sorted(os.listdir(ORIGINALS)):
        if not f.endswith('.svg'):
            continue
        slug = f[:-4]
        if not re.match(r'^[a-z][a-z0-9-]*$', slug):
            sys.exit('bad file name (use lower-case words and hyphens): ' + f)
        cat = cats.get(slug, 'Toys & characters')
        t, size, eps = template(slug, cat, os.path.join(ORIGINALS, f))
        items.append((CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else 99, slug, t, size, eps))
    items.sort()
    block = BEGIN + ' (generated by tools/import_artwork.py from artwork/originals — edit the originals, then re-run) -->\n' + \
        '\n'.join(i[2] for i in items) + '\n' + END
    html = open(INDEX, encoding='utf-8').read()
    if BEGIN in html:
        html = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END), lambda m: block, html, flags=re.S)
    else:
        html = html.replace('<!-- ======================== END ANIMAL DRAWINGS', block + '\n<!-- ======================== END ANIMAL DRAWINGS')
    open(INDEX, 'w', encoding='utf-8').write(html)
    big = [(i[1], i[3]) for i in items if i[3] > MAX_BYTES]
    print('%d pictures, %d KB total, largest %s' % (len(items), sum(i[3] for i in items) // 1024, max(items, key=lambda i: i[3])[1:4:2]))
    if big:
        sys.exit('over %d bytes: %s' % (MAX_BYTES, big))


if __name__ == '__main__':
    main()
