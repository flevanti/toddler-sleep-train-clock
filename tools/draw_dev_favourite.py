#!/usr/bin/env python3
"""Dev's Favourite pictures: hand-drawn silhouettes (Florence, Tuscany, food, things), written into index.html.

Usage (from the repo root):   python3 tools/draw_dev_favourite.py [--sheet]

Each entry in D below is (name, movement, pivot, SVG body) on the clock's canvas (viewBox -40 -40 280 280,
ground at y=210). currentColor = the night colour, #000 = a cut-out. Pinocchio's nose is a <g data-grow="x y">
that the clock scales up as the night goes on. The script rewrites the block between the DEV FAVOURITE markers
inside the ANIMAL DRAWINGS section; --sheet also writes a preview to tests/screenshots/devpack/sheet.html.
The pictures stay hidden in the app unless dev mode and its "Dev's Favourite pictures" switch are on.
Not deployed: the clock only needs index.html and sw.js.
"""
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
SHEET = os.path.join(ROOT, 'tests', 'screenshots', 'devpack')
CAT = "Dev's Favourite"
BEGIN, END = '<!-- BEGIN DEV FAVOURITE', '<!-- END DEV FAVOURITE -->'
C, K = 'currentColor', '#000'   # K = cut-out (the night background is black)


def f(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def arch(x, y, w, h):          # window / arch opening: rectangle with a round top
    r = w / 2
    return 'M%s %s v-%s a%s %s 0 0 1 %s 0 v%s z' % (f(x), f(y), f(h - r), f(r), f(r), f(w), f(h - r))


def merlons(x0, x1, y, n, h=8):
    w = (x1 - x0) / (2 * n - 1)
    return ''.join('M%s %s h%s v-%s h-%s z' % (f(x0 + 2 * i * w), f(y), f(w), f(h), f(w)) for i in range(n))


def star_ring(cx, cy, r0, r1, n, rot=0):
    pts = []
    for i in range(2 * n):
        a = math.pi * i / n + rot
        r = r0 if i % 2 == 0 else r1
        pts.append('%s %s' % (f(cx + r * math.cos(a)), f(cy + r * math.sin(a))))
    return 'M' + ' L'.join(pts) + 'Z'


D = {}
# ---------------- Florence ----------------
D['duomo'] = ('Duomo', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-10 210 V160 H210 V210 Z"/>' % C,                         # nave
    '<path fill="%s" d="M40 160 V128 H160 V160 Z"/>' % C,                           # drum
    '<path fill="%s" d="M44 128 Q46 58 100 40 Q154 58 156 128 Z"/>' % C,            # dome
    '<path fill="%s" d="M92 40 V22 H108 V40 Z M96 22 L100 6 L104 22 Z"/>' % C,      # lantern
    '<path fill="none" stroke="%s" stroke-width="3" d="M72 128 Q72 72 100 42 M128 128 Q128 72 100 42"/>' % K,   # ribs
    '<path fill="%s" d="%s%s%s%s"/>' % (K, arch(56, 152, 10, 16), arch(95, 152, 10, 16), arch(134, 152, 10, 16), ''),
    '<path fill="%s" d="%s%s%s%s%s"/>' % (K, arch(2, 204, 14, 28), arch(36, 204, 14, 28), arch(150, 204, 14, 28), arch(184, 204, 14, 28), ''),
]))
D['giottos-bell-tower'] = ("Giotto's bell tower", 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M68 210 V26 H132 V210 Z"/>' % C,
    '<path fill="%s" d="M62 26 H138 V16 H62 Z"/>' % C,
    '<path fill="%s" d="%s"/>' % (C, merlons(62, 138, 16, 7, 6)),
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M68 170 H132 M68 130 H132 M68 80 H132"/>' % K,
    '<path fill="%s" d="%s%s%s%s%s"/>' % (K, arch(82, 124, 12, 32), arch(106, 124, 12, 32), arch(80, 74, 14, 40), arch(106, 74, 14, 40), arch(94, 166, 12, 22)),
]))
D['ponte-vecchio'] = ('Ponte Vecchio', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-30 150 H230 V200 H-30 Z"/>' % C,                                        # bridge body
    '<path fill="%s" d="M-20 150 V120 H20 V150 Z M24 150 V112 H64 V150 Z M136 150 V112 H176 V150 Z M180 150 V120 H220 V150 Z"/>' % C,   # shops
    '<path fill="%s" d="M-22 120 L0 108 L22 120 Z M22 112 L44 100 L66 112 Z M134 112 L156 100 L178 112 Z M178 120 L200 108 L222 120 Z"/>' % C,  # roofs
    '<path fill="%s" d="M68 150 V132 H132 V150 Z"/>' % C,                                        # middle loggia
    '<path fill="%s" d="%s%s%s"/>' % (K, arch(78, 150, 12, 14), arch(94, 150, 12, 14), arch(110, 150, 12, 14)),
    '<path fill="%s" d="M-8 200 Q20 166 48 200 Z M64 200 Q100 156 136 200 Z M152 200 Q180 166 208 200 Z"/>' % K,   # arches
    '<path fill="%s" d="M-30 200 H230 V210 H-30 Z" opacity=".5"/>' % C,                            # river
    '<path fill="%s" d="M-12 140 h8 v-10 h-8 z M40 132 h8 v-10 h-8 z M152 132 h8 v-10 h-8 z M204 140 h8 v-10 h-8 z"/>' % K,   # shop windows
]))
D['palazzo-vecchio'] = ('Palazzo Vecchio', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M10 210 V92 H190 V210 Z"/>' % C,
    '<path fill="%s" d="%s"/>' % (C, merlons(8, 192, 92, 12, 9)),
    '<path fill="%s" d="M88 92 V20 H112 V92 Z M82 20 H118 V8 H82 Z"/>' % C,
    '<path fill="%s" d="%s"/>' % (C, merlons(82, 118, 8, 4, 7)),
    '<path fill="%s" d="M98 0 V-14 H102 V0 Z"/>' % C,
    '<circle cx="100" cy="112" r="9" fill="%s"/>' % K,
    '<path fill="%s" d="%s%s%s%s%s%s"/>' % (K, arch(26, 146, 12, 18), arch(56, 146, 12, 18), arch(132, 146, 12, 18), arch(162, 146, 12, 18), arch(92, 210, 16, 30), arch(26, 184, 12, 18)),
    '<path fill="%s" d="%s"/>' % (K, arch(162, 184, 12, 18)),
]))
D['florentine-lily'] = ('Florentine lily', 'breathe', '100 210', '\n'.join([
    # the "giglio": a tall central petal, two petals curling out and down, a band, two stamens rising between the petals
    '<path fill="%s" d="M100 8 Q120 40 114 96 L108 128 H92 L86 96 Q80 40 100 8 Z"/>' % C,
    '<path fill="%s" d="M86 120 Q58 120 42 98 Q24 72 42 54 Q60 42 70 60 Q56 58 54 72 Q54 92 88 104 Z"/>' % C,
    '<path fill="%s" d="M114 120 Q142 120 158 98 Q176 72 158 54 Q140 42 130 60 Q144 58 146 72 Q146 92 112 104 Z"/>' % C,
    '<path fill="%s" d="M52 124 H148 V142 H52 Z"/>' % C,
    '<path fill="%s" d="M88 142 Q66 150 54 176 Q48 190 58 196 Q66 178 90 160 Z M112 142 Q134 150 146 176 Q152 190 142 196 Q134 178 110 160 Z M92 142 H108 L104 200 H96 Z"/>' % C,
    '<path fill="%s" d="M78 110 L60 44 L66 42 L84 104 Z M122 110 L140 44 L134 42 L116 104 Z"/>' % C,
    '<path fill="%s" d="M52 42 Q62 28 72 42 Q62 50 52 42 Z M128 42 Q138 28 148 42 Q138 50 128 42 Z"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="2" d="M58 133 H142"/>' % K,
]))
D['porcellino'] = ('Porcellino', 'breathe', '100 210', '\n'.join([
    # the bronze boar of the Mercato Nuovo: sitting on its haunches on a pedestal, snout forward
    '<path fill="%s" d="M10 210 V182 H196 V210 Z M4 182 H202 V172 H4 Z"/>' % C,
    '<path fill="%s" d="M180 172 Q194 130 170 104 Q150 84 118 86 Q96 70 72 72 Q52 66 34 76 L6 92 Q-6 100 0 110 Q8 118 24 116 Q34 124 52 124 L58 150 L52 172 H72 L78 140 Q96 138 108 150 Q118 162 120 172 Z"/>' % C,
    '<path fill="%s" d="M58 72 L66 44 L80 70 Z M76 74 L88 50 L96 78 Z"/>' % C,
    '<path fill="%s" d="M-2 100 Q-6 106 -2 110 Q2 106 -2 100 Z M150 108 Q170 120 172 150" stroke="%s" stroke-width="0"/>' % (K, K),
    '<path fill="none" stroke="%s" stroke-width="3" stroke-linecap="round" d="M16 112 Q10 98 20 92"/>' % K,
    '<circle cx="46" cy="90" r="4" fill="%s"/>' % K,
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M110 104 Q140 96 164 116 M116 122 Q142 116 162 136 M100 88 Q120 80 140 88"/>' % K,
    '<path fill="%s" d="M180 150 Q200 150 204 130 Q198 144 184 142 Z"/>' % C,
]))
D['leaning-tower-of-pisa'] = ('Leaning tower of Pisa', 'sway', '100 210', '<g transform="rotate(5 100 210)">' + '\n'.join([
    '<path fill="%s" d="M66 210 V30 H134 V210 Z"/>' % C,
    '<path fill="%s" d="M74 30 V6 H126 V30 Z"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="2.5" d="%s"/>' % (K, ''.join('M66 %d H134 ' % y for y in (60, 88, 116, 144, 172))),
    '<path fill="%s" d="%s"/>' % (K, ''.join(arch(x, y, 8, 18) for y in (84, 112, 140, 168) for x in (72, 88, 104, 120))),
    '<path fill="%s" d="%s"/>' % (K, ''.join(arch(x, 28, 8, 16) for x in (80, 96, 112))),
]) + '</g>')
D['cypress-road'] = ('Cypress road', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-40 210 Q20 150 100 158 Q180 166 240 130 V210 Z"/>' % C,          # hill
    '<path fill="%s" d="M40 210 Q60 190 100 184 Q150 176 160 162 Q170 176 122 190 Q80 198 70 210 Z"/>' % K,   # winding road
    '<path fill="%s" d="%s"/>' % (C, ''.join('M%s %s Q%s %s %s %s Q%s %s %s %s Z ' % (f(x), f(y), f(x - w), f(y - h * .45), f(x), f(y - h), f(x + w), f(y - h * .45), f(x), f(y))
                                         for x, y, w, h in ((132, 180, 9, 70), (152, 172, 8, 62), (170, 166, 7, 54), (186, 160, 6, 46), (200, 154, 5, 38), (112, 186, 10, 78)))),
]))
D['hill-village'] = ('Hill village', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-40 210 Q20 116 100 106 Q180 116 240 210 Z"/>' % C,
    '<path fill="%s" d="M40 118 V92 L54 82 L68 92 V112 Z M66 110 V80 H92 V106 Z M90 106 V60 H106 V106 Z M104 106 V84 L122 72 L140 84 V112 Z M138 112 V92 H160 V118 Z"/>' % C,
    '<path fill="%s" d="%s"/>' % (C, merlons(88, 108, 60, 3, 6)),
    '<path fill="%s" d="M48 100 h5 v6 h-5 z M74 90 h5 v6 h-5 z M78 98 h5 v6 h-5 z M95 70 h6 v9 h-6 z M114 94 h5 v6 h-5 z M126 92 h5 v6 h-5 z M144 100 h5 v6 h-5 z"/>' % K,
    '<path fill="%s" d="M170 150 Q166 130 172 104 Q178 130 174 150 Z M184 160 Q181 142 186 120 Q191 142 188 160 Z"/>' % K,   # cypress shadows on the hill
]))
D['olive-tree'] = ('Olive tree', 'sway', '100 210', '\n'.join([
    '<path fill="%s" d="M84 210 Q92 176 80 150 Q70 128 88 116 L96 126 Q84 140 96 160 Q106 140 100 118 L110 112 Q118 140 108 166 Q102 186 118 210 Z"/>' % C,
    '<path fill="%s" d="%s"/>' % (C, ''.join('M%s %s a%s %s 0 1 0 0.1 0 Z ' % (f(x), f(y), f(r), f(r * .8)) for x, y, r in
                                         ((100, 70, 42), (50, 90, 34), (150, 88, 36), (76, 50, 28), (128, 48, 30), (30, 112, 22), (172, 112, 22)))),
    '<path fill="%s" d="%s"/>' % (K, ''.join('M%s %s a4 2.5 30 1 0 0.1 0 Z ' % (f(x), f(y)) for x, y in
                                         ((70, 74), (92, 60), (118, 76), (140, 70), (54, 100), (160, 98), (100, 96), (84, 42), (130, 40), (36, 116), (170, 120)))),
]))
# ---------------- Food ----------------
wedge = 'M100 110 L178 66 A92 92 0 0 1 188 118 Z'
D['parmigiano'] = ('Parmigiano', 'breathe', '100 210', '\n'.join([
    # a whole wheel (side view) with the dotted brand on the rind, a wedge cut out, the almond-shaped knife stuck in
    '<path fill="%s" d="M-20 118 Q-24 146 -20 176 Q70 204 160 176 Q164 146 160 118 Q70 90 -20 118 Z"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="3" d="M-20 118 Q70 146 160 118"/>' % K,                       # top edge
    '<path fill="%s" d="%s"/>' % (K, ''.join('M%s %s a2.2 2.2 0 1 0 0.1 0 Z ' % (f(x), f(y + (x - 70) ** 2 / 900)) for y in (150, 160, 170) for x in range(0, 150, 9))),   # dotted rind
    '<path fill="%s" d="M110 128 L160 118 Q164 146 160 176 L110 150 Z"/>' % K,                                 # the wedge that was cut
    '<path fill="%s" d="M170 196 L226 170 L232 204 Q200 214 170 206 Z"/>' % C,                                 # the wedge, on the side
    '<path fill="%s" d="M206 176 a3 3 0 1 0 0.1 0 Z M218 188 a3 3 0 1 0 0.1 0 Z M196 194 a3 3 0 1 0 0.1 0 Z"/>' % K,   # grainy crumbs
    '<path fill="%s" d="M60 112 Q70 84 84 70 Q86 90 72 112 Z M76 70 L84 40 L90 42 L82 72 Z"/>' % C,            # almond-shaped knife stuck in the wheel
]))
D['pecorino'] = ('Pecorino', 'breathe', '100 210', '\n'.join([
    # a pecorino toscano: a low wheel with rounded sides and the woven-basket marks on the rind, one slice beside it
    '<path fill="%s" d="M-6 126 Q-18 150 -6 176 Q80 204 166 176 Q178 150 166 126 Q80 98 -6 126 Z"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="3" d="M-6 126 Q80 154 166 126"/>' % K,
    '<path fill="none" stroke="%s" stroke-width="2" d="%s"/>' % (K, ''.join('M%s %s l6 -8 M%s %s l6 8 ' % (f(x), f(y), f(x + 8), f(y - 8)) for y in (160, 176) for x in range(4, 156, 16))),   # basket weave
    '<path fill="%s" d="M176 206 L236 206 L210 150 Z"/>' % C,                                                   # a slice
    '<path fill="none" stroke="%s" stroke-width="3" d="M210 150 L236 206"/>' % K,
]))
D['moka'] = ('Moka', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M62 210 L52 150 H148 L138 210 Z"/>' % C,                 # boiler
    '<path fill="%s" d="M58 150 L72 134 H128 L142 150 Z"/>' % C,                 # waist
    '<path fill="%s" d="M72 134 L60 64 H140 L128 134 Z"/>' % C,                  # upper
    '<path fill="%s" d="M60 64 L70 50 H130 L140 64 Z M94 50 V40 H106 V50 Z"/>' % C,   # lid + knob
    '<path fill="%s" d="M60 70 L38 58 L44 76 L62 84 Z"/>' % C,                    # spout
    '<path fill="none" stroke="%s" stroke-width="14" stroke-linejoin="round" d="M138 76 H166 L160 124 H132"/>' % C,   # handle
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M100 64 V134 M100 150 V210 M76 150 L84 210 M124 150 L116 210"/>' % K,
    '<path fill="none" stroke="%s" stroke-width="3" stroke-linecap="round" opacity=".7" d="M86 30 q-8 -12 0 -24 M106 30 q8 -12 0 -24"/>' % C,   # steam
]))
D['gelato'] = ('Gelato', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M60 110 H140 L100 210 Z"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M70 110 L118 170 M90 110 L126 150 M110 110 L132 130 M130 110 L86 170 M110 110 L74 150 M90 110 L68 130"/>' % K,
    '<path fill="%s" d="M56 112 Q48 84 72 78 Q72 54 100 52 Q128 54 128 78 Q152 84 144 112 Z"/>' % C,
    '<path fill="%s" d="M70 60 Q70 30 100 28 Q130 30 130 60 Q116 50 100 52 Q84 50 70 60 Z"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="3" d="M56 112 Q66 102 78 110 Q90 100 102 110 Q114 100 126 110 Q136 102 144 112 M72 60 Q86 48 100 56 Q114 48 128 60"/>' % K,
    '<path fill="%s" d="M96 14 Q100 2 108 8 Q104 14 100 24 Z"/>' % C,           # wafer
]))
D['pizza'] = ('Pizza', 'breathe', '100 210', '\n'.join([
    '<circle cx="100" cy="124" r="86" fill="%s"/>' % C,
    '<circle cx="100" cy="124" r="72" fill="none" stroke="%s" stroke-width="3"/>' % K,
    '<path fill="%s" d="M100 124 L180 96 A86 86 0 0 1 186 132 Z"/>' % K,                     # slice gone
    '<path fill="%s" d="M110 124 L196 108 A90 90 0 0 1 200 140 Z"/>' % C,                      # the slice, pulled out
    '<path fill="%s" d="%s"/>' % (K, ''.join('M%s %s a9 9 0 1 0 0.1 0 Z ' % (f(x), f(y)) for x, y in ((70, 90), (120, 80), (60, 150), (104, 170), (140, 150), (86, 124), (46, 118), (178, 124)))),
    '<path fill="none" stroke="%s" stroke-width="2.5" stroke-linecap="round" d="M96 64 q6 -4 10 2 M44 90 q4 -6 10 -2 M130 110 q6 -4 10 2 M80 190 q6 -4 10 2"/>' % K,   # basil
]))
D['spaghetti'] = ('Spaghetti', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-10 180 Q100 226 210 180 Q100 204 -10 180 Z"/>' % C,                 # plate rim
    '<path fill="%s" d="M20 180 Q24 132 100 124 Q176 132 180 180 Q100 196 20 180 Z"/>' % C,    # pile
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M30 172 Q60 140 100 150 Q140 160 170 170 M40 160 Q80 132 120 146 Q150 156 166 150 M60 150 Q100 136 140 140 M36 178 Q70 160 110 170 Q150 178 172 176"/>' % K,
    '<circle cx="80" cy="132" r="9" fill="%s"/><circle cx="126" cy="138" r="8" fill="%s"/><circle cx="104" cy="120" r="8" fill="%s"/>' % (C, C, C),   # meatballs
    '<path fill="%s" d="M146 132 L204 28 L212 32 L154 136 Z"/>' % C,                         # fork handle
    '<path fill="%s" d="M200 22 L208 -2 L212 0 L206 24 Z M206 26 L218 4 L222 6 L212 28 Z"/>' % C,   # tines
]))
# ---------------- Things ----------------
D['vespa'] = ('Vespa', 'rock', '100 210', '\n'.join([
    '<circle cx="36" cy="186" r="20" fill="%s"/><circle cx="168" cy="186" r="20" fill="%s"/>' % (C, C),
    '<circle cx="36" cy="186" r="8" fill="%s"/><circle cx="168" cy="186" r="8" fill="%s"/>' % (K, K),
    '<path fill="%s" d="M22 176 Q18 150 40 144 L58 70 H80 L72 150 Q76 172 92 176 H126 Q118 138 150 120 Q190 108 206 140 Q214 170 196 180 L92 184 Q70 186 60 172 Q48 160 22 176 Z"/>' % C,   # shield, floorboard and rounded rear body
    '<path fill="%s" d="M48 66 Q70 58 94 64 L92 58 Q70 50 46 60 Z"/>' % C,                 # handlebar
    '<circle cx="68" cy="76" r="9" fill="%s"/><circle cx="68" cy="76" r="4" fill="%s"/>' % (C, K),   # headlight
    '<path fill="%s" d="M124 116 Q150 98 196 108 L194 118 Q156 110 126 126 Z"/>' % C,      # seat
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M140 156 Q168 138 200 154 M40 150 L56 78"/>' % K,
]))
D['fiat-500'] = ('Fiat 500', 'rock', '100 210', '\n'.join([
    # the classic 500: a rounded bubble with a domed roof, short bonnet, little round wheels at the very ends
    '<path fill="%s" d="M-14 184 Q-20 150 0 138 Q18 84 84 78 Q150 80 170 124 Q210 132 214 164 Q216 184 204 186 Z"/>' % C,
    '<path fill="%s" d="M20 134 Q34 96 80 92 V134 Z M90 92 Q134 94 152 134 H90 Z"/>' % K,                      # side windows
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M86 92 V178 M20 140 V176 M-10 160 H212"/>' % K,       # door line, trim
    '<path fill="%s" d="M60 146 h14 v4 h-14 z"/>' % K,                                                          # door handle
    '<circle cx="196" cy="150" r="8" fill="%s"/>' % K,                                                          # round headlight
    '<circle cx="24" cy="190" r="22" fill="%s"/><circle cx="168" cy="190" r="22" fill="%s"/>' % (K, K),
    '<circle cx="24" cy="190" r="17" fill="%s"/><circle cx="168" cy="190" r="17" fill="%s"/>' % (C, C),
    '<circle cx="24" cy="190" r="6" fill="%s"/><circle cx="168" cy="190" r="6" fill="%s"/>' % (K, K),
    '<path fill="%s" d="M-18 180 H0 V186 H-18 Z M200 180 H218 V186 H200 Z"/>' % C,                             # bumpers
]))
D['pinocchio'] = ('Pinocchio', 'breathe', '100 210', '<g transform="translate(100 212) scale(1.25) translate(-100 -212)">' + '\n'.join([
    '<path fill="%s" d="M84 210 L90 150 H98 L96 210 Z M104 210 L102 150 H110 L116 210 Z"/>' % C,
    '<path fill="%s" d="M78 212 H98 V204 H80 Z M102 212 H124 V204 H102 Z"/>' % C,
    '<path fill="%s" d="M80 152 L84 96 H116 L120 152 Z"/>' % C,
    '<path fill="%s" d="M84 100 L60 138 L66 142 L88 110 Z M116 100 L140 132 L134 136 L112 110 Z"/>' % C,
    '<circle cx="100" cy="78" r="20" fill="%s"/>' % C,
    '<path fill="%s" d="M80 64 Q100 62 120 64 L112 22 L126 16 Z"/>' % C,
    '<path fill="%s" d="M90 96 L100 104 L110 96 Z"/>' % K,
    '<circle cx="106" cy="74" r="3" fill="%s"/>' % K,
    '<g data-grow="118 80"><path fill="%s" d="M118 76 L150 80 L118 84 Z"/></g>' % C,
]) + '</g>')

# ---------------- batch 2 ----------------
def win_row(x0, x1, y, n, w, h):
    step = (x1 - x0) / n
    return ''.join(arch(x0 + step * i + (step - w) / 2, y, w, h) for i in range(n))


D['palazzo-pitti'] = ('Palazzo Pitti', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-34 196 V92 H234 V196 Z"/>' % C,
    '<path fill="%s" d="M-40 210 L-34 196 H234 L240 210 Z"/>' % C,                                   # sloping piazza
    '<path fill="none" stroke="%s" stroke-width="2" d="M-34 160 H234 M-34 126 H234"/>' % K,
    '<path fill="%s" d="%s"/>' % (K, win_row(-34, 234, 156, 11, 12, 22) + win_row(-34, 234, 122, 11, 12, 22)),
    '<path fill="%s" d="%s%s%s"/>' % (K, arch(66, 196, 18, 30), arch(91, 196, 18, 30), arch(116, 196, 18, 30)),
    '<path fill="%s" d="%s"/>' % (K, win_row(-34, 60, 190, 3, 8, 12) + win_row(140, 234, 190, 3, 8, 12)),
]))
D['santo-spirito'] = ('Santo Spirito', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M186 210 V40 H198 V210 Z M184 40 L192 14 L200 40 Z"/>' % C,                  # bell tower behind
    '<path fill="%s" d="M150 120 Q150 84 170 76 Q172 96 176 120 Z"/>' % C,                            # little dome behind
    # the famous plain facade: a wide base and a narrower top joined by curved "shoulders"
    '<path fill="%s" d="M20 210 V124 H62 Q70 124 72 112 Q74 96 80 90 V46 Q100 30 120 46 V90 Q126 96 128 112 Q130 124 138 124 H180 V210 Z"/>' % C,
    '<circle cx="100" cy="72" r="11" fill="%s"/>' % K,
    '<path fill="%s" d="%s%s%s"/>' % (K, arch(90, 210, 20, 40), arch(40, 210, 12, 26), arch(148, 210, 12, 26)),
    '<path fill="%s" d="M-30 210 H230 V204 H-30 Z" opacity=".5"/>' % C,
]))
D['florence-skyline'] = ('Florence skyline', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-40 210 V176 Q40 160 100 170 Q170 156 240 172 V210 Z" opacity=".45"/>' % C,           # hills behind
    '<path fill="%s" d="M-40 210 V182 H-18 V174 H4 V186 H22 V168 H40 V184 H150 V172 H176 V186 H200 V176 H240 V210 Z"/>' % C,   # rooftops
    '<path fill="%s" d="M56 184 V150 H112 V184 Z M60 150 Q62 104 84 96 Q106 104 108 150 Z M80 96 V86 H88 V96 Z"/>' % C,          # Duomo
    '<path fill="%s" d="M118 184 V112 H132 V184 Z"/>' % C,                                                                       # Giotto
    '<path fill="%s" d="M156 184 V104 H166 V184 Z M152 104 H170 V96 H152 Z M160 96 V86 H162 V96 Z"/>' % C,                     # Palazzo Vecchio tower
    '<path fill="%s" d="M4 184 V150 L10 140 L16 150 V184 Z"/>' % C,                                                              # Santa Croce bell tower
    '<path fill="%s" d="M-40 196 H240 V210 H-40 Z"/>' % K,                                                                       # the Arno
    '<path fill="none" stroke="%s" stroke-width="2" opacity=".6" d="M-30 202 H10 M40 204 H90 M120 202 H170 M190 204 H230"/>' % C,
]))
D['chianti-wine'] = ('Chianti wine', 'breathe', '100 210', '\n'.join([
    # the "fiasco": a round glass belly in a woven straw jacket, a long thin neck, a straw loop to carry it
    '<path fill="%s" d="M84 20 H100 V12 H84 Z M86 20 H98 V96 Q140 108 142 150 Q144 196 92 202 Q40 196 42 150 Q44 108 86 96 Z"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="2" d="%s"/>' % (K, ''.join('M%s 118 Q%s 160 %s 198 ' % (f(x), f(x + (x - 92) * .25), f(92 + (x - 92) * .7)) for x in range(54, 132, 10))),   # vertical straw
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M48 124 Q92 138 136 124 M44 146 Q92 162 140 146 M46 168 Q92 184 138 168 M56 188 Q92 200 128 188"/>' % K,   # woven bands
    '<path fill="none" stroke="%s" stroke-width="6" d="M134 124 Q170 110 164 150 Q160 176 138 168"/>' % C,     # straw handle loop
    '<path fill="none" stroke="%s" stroke-width="2" d="M88 30 V96"/>' % K,
    '<path fill="%s" d="M172 128 H206 Q208 154 192 162 V194 H202 V200 H176 V194 H186 V162 Q170 154 172 128 Z"/>' % C,   # glass
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M174 140 H204"/>' % K,
]))
D['david'] = ('David', 'breathe', '100 210', '<g transform="translate(100 212) scale(1.25) translate(-100 -212)">' + '\n'.join([
    '<path fill="%s" d="M56 212 V194 H144 V212 Z"/>' % C,                                                        # plinth
    '<path fill="%s" d="M140 194 L134 150 Q132 140 124 138 L122 150 L128 194 Z"/>' % C,                          # tree stump support
    '<circle cx="100" cy="30" r="13" fill="%s"/>' % C,                                                           # head, turned to his left
    '<path fill="%s" d="M88 26 Q90 12 102 14 Q114 16 112 26 Q106 18 96 22 Z"/>' % C,                             # curls
    '<path fill="%s" d="M96 42 H106 V50 H96 Z"/>' % C,                                                           # neck
    '<path fill="%s" d="M82 52 Q100 46 118 52 L116 96 Q112 108 104 110 H94 Q86 108 84 96 Z"/>' % C,              # torso
    '<path fill="%s" d="M94 108 L90 150 L86 194 H98 L102 150 L104 112 Z"/>' % C,                                 # weight-bearing right leg
    '<path fill="%s" d="M104 110 L114 146 L110 194 H122 L124 146 L114 104 Z"/>' % C,                             # relaxed left leg, knee forward
    '<path fill="%s" d="M118 54 L128 82 L126 110 L120 110 L120 84 L114 62 Z"/>' % C,                            # right arm hanging (holds the stone)
    '<path fill="%s" d="M84 56 L70 72 L78 40 L86 40 L82 64 L88 58 Z"/>' % C,                                     # left arm raised to the shoulder
    '<path fill="none" stroke="%s" stroke-width="2" d="M80 40 Q96 70 92 104"/>' % K,                             # the sling over his back
]) + '</g>')
D['renaioli'] = ('Renaioli boat', 'float', '100 210', '\n'.join([
    '<path fill="%s" d="M-30 176 H230 L210 198 H-10 Z"/>' % C,                                        # flat river boat
    '<path fill="%s" d="M92 176 L98 150 L96 120 L104 118 L110 150 L110 176 Z"/>' % C,                 # renaiolo standing
    '<circle cx="104" cy="108" r="9" fill="%s"/>' % C,
    '<path fill="%s" d="M96 102 H114 L110 94 H100 Z"/>' % C,                                          # hat
    '<path fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" d="M150 40 L60 212"/>' % C, # the long pole
    '<path fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" d="M100 128 L126 104 M108 132 L122 116"/>' % C,
    '<path fill="%s" d="M-40 198 H240 V212 H-40 Z" opacity=".5"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="2" d="M-20 206 H20 M60 208 H120 M160 206 H210"/>' % K,
]))
D['porta-alla-croce'] = ('Piazza Beccaria arch', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-40 210 Q100 186 240 210 Z" opacity=".5"/>' % C,                             # the square
    '<path fill="%s" d="M50 206 V40 H150 V206 Z"/>' % C,
    '<path fill="%s" d="M44 40 H156 V28 H44 Z"/>' % C,
    '<path fill="%s" d="%s"/>' % (C, merlons(44, 156, 28, 9, 8)),
    '<path fill="%s" d="%s"/>' % (K, arch(70, 206, 60, 104)),                                         # the gate arch
    '<path fill="%s" d="M92 70 h16 v20 h-16 z"/>' % K,
    '<path fill="none" stroke="%s" stroke-width="2" d="M50 110 H70 M130 110 H150"/>' % K,
]))
D['val-d-orcia'] = ("Val d'Orcia", 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-40 150 Q10 120 70 136 Q130 150 180 124 Q214 110 240 118 V210 H-40 Z" opacity=".55"/>' % C,
    '<path fill="%s" d="M-40 210 V176 Q30 146 100 160 Q170 174 240 150 V210 Z"/>' % C,
    '<path fill="none" stroke="%s" stroke-width="2" d="M-40 196 Q40 170 120 186 Q180 196 240 176"/>' % K,
    '<path fill="%s" d="M146 130 V114 L158 104 L170 114 V130 Z"/>' % C,                               # farmhouse on the hill
    '<path fill="%s" d="%s"/>' % (C, ''.join('M%s %s Q%s %s %s %s Q%s %s %s %s Z ' % (f(x), f(y), f(x - w), f(y - h * .45), f(x), f(y - h), f(x + w), f(y - h * .45), f(x), f(y))
                                         for x, y, w, h in ((40, 164, 7, 52), (58, 158, 6, 44), (74, 154, 5, 38), (90, 150, 5, 32), (104, 146, 4, 28), (118, 142, 4, 24), (132, 138, 3, 20), (-10, 176, 8, 60), (4, 172, 8, 56)))),
    '<path fill="none" stroke="%s" stroke-width="2.5" d="M36 172 Q90 150 140 132"/>' % K,             # the white road, as a line
]))
D['san-gimignano'] = ('San Gimignano', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-40 210 Q20 150 100 146 Q180 150 240 210 Z"/>' % C,
    '<path fill="%s" d="%s"/>' % (C, ''.join('M%s 160 V%s H%s V160 Z ' % (f(x), f(top), f(x + w)) for x, w, top in
                                         ((20, 12, 104), (40, 14, 70), (60, 10, 92), (76, 16, 50), (98, 12, 64), (116, 14, 40), (136, 10, 84), (152, 16, 60), (174, 12, 96)))),
    '<path fill="%s" d="M10 162 H196 V150 H10 Z"/>' % C,
    '<path fill="%s" d="%s"/>' % (K, ''.join('M%s %s h4 v8 h-4 z ' % (f(x + 5), f(top + 10)) for x, top in ((40, 70), (76, 50), (116, 40), (152, 60), (98, 64)))),
]))
def checkerboard(y0, y1, rows, cols, vx, vy):
    # squares on the ground, converging towards the vanishing point (vx, vy)
    def X(xb, y):   # clipped to the canvas, so the edge squares are cut off at the sides
        return min(238, max(-38, vx + (xb - vx) * (y - vy) / (y1 - vy)))
    ys = [y0 + (y1 - y0) * (i / rows) ** 1.25 for i in range(rows + 1)]
    xs = [-150 + 440 * j / cols for j in range(cols + 1)]
    d = ''
    for i in range(rows):
        for j in range(cols):
            if (i + j) % 2:
                a, b = ys[i], ys[i + 1]
                d += 'M%s %s L%s %s L%s %s L%s %s Z ' % (f(X(xs[j], a)), f(a), f(X(xs[j + 1], a)), f(a), f(X(xs[j + 1], b)), f(b), f(X(xs[j], b)), f(b))
    return d


checker = checkerboard(150, 210, 5, 10, 100, 60)
D['terrazza-mascagni'] = ('Terrazza Mascagni', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-40 210 V150 H240 V210 Z"/>' % C,                                           # the terrace
    '<path fill="%s" d="%s"/>' % (K, checker),                                                        # black-and-white checkerboard
    '<path fill="%s" d="M-40 150 V136 H240 V150 Z"/>' % C,                                            # balustrade
    '<path fill="%s" d="%s"/>' % (K, ''.join('M%d 148 q3 -6 0 -10 h4 q-3 4 0 10 z ' % x for x in range(-36, 240, 10))),
    '<path fill="none" stroke="%s" stroke-width="2" opacity=".6" d="M-40 118 H240 M-20 126 H40 M80 124 H150 M180 128 H230"/>' % C,   # the sea
    '<path fill="%s" d="M146 136 V96 H150 V136 Z M190 136 V96 H194 V136 Z M140 98 Q170 70 200 98 Z M168 80 V70 H172 V80 Z"/>' % C,   # the gazebo
]))
D['siena'] = ('Siena', 'breathe', '100 210', '\n'.join([
    '<path fill="%s" d="M-40 210 Q20 164 100 160 Q180 164 240 210 Z"/>' % C,
    '<path fill="%s" d="M40 168 V132 H120 V168 Z"/>' % C,                                              # Palazzo Pubblico
    '<path fill="%s" d="%s"/>' % (C, merlons(38, 122, 132, 9, 6)),
    '<path fill="%s" d="M122 168 V30 H134 V168 Z M118 30 H138 V22 H118 Z M120 22 L128 4 L136 22 Z"/>' % C,   # Torre del Mangia
    '<path fill="%s" d="M150 168 V120 H200 V168 Z M156 120 Q158 96 174 92 Q190 96 192 120 Z M170 92 V84 H178 V92 Z"/>' % C,   # the Duomo
    '<path fill="%s" d="M202 168 V78 H214 V168 Z M200 78 L208 64 L216 78 Z"/>' % C,                   # its striped bell tower
    '<path fill="none" stroke="%s" stroke-width="2" d="M202 96 H214 M202 112 H214 M202 128 H214 M202 144 H214"/>' % K,
    '<path fill="%s" d="%s"/>' % (K, win_row(40, 120, 158, 6, 6, 12)),
    '<path fill="%s" d="M-30 186 V172 H-4 V178 H18 V168 H34 V186 Z M214 186 V174 H236 V186 Z"/>' % C,  # houses on the hill
]))
D['seagull-at-sunset'] = ('Seagull at sunset', 'float', '100 210', '\n'.join([
    '<path fill="%s" d="M30 170 A70 70 0 0 1 170 170 Z"/>' % C,                                         # the setting sun
    '<path fill="%s" d="M26 152 H174 V156 H26 Z M30 140 H170 V143 H30 Z M40 128 H160 V130 H40 Z"/>' % K,
    '<path fill="%s" d="M-40 170 H240 V210 H-40 Z" opacity=".45"/>' % C,                                 # the sea
    '<path fill="none" stroke="%s" stroke-width="3" d="M40 180 H160 M60 190 H140 M80 200 H120"/>' % C,  # the sun on the water
    '<path fill="%s" d="M40 70 Q70 40 100 72 Q130 40 160 70 Q130 56 100 84 Q70 56 40 70 Z"/>' % C,       # the gull
]))

# ---------------- batch 3 ----------------
def ring_lashings():
    d = ''
    for deg in (45, 135, 225, 315):   # the four rope lashings across the buoy
        a = math.radians(deg)
        for k in (-7, -2.5, 2, 6.5):
            t = a + math.radians(k)
            d += 'M%s %s L%s %s ' % (f(100 + 58 * math.cos(t)), f(118 + 58 * math.sin(t)), f(100 + 84 * math.cos(t)), f(118 + 84 * math.sin(t)))
    return d


def rope_loops():
    d = ''
    for deg in (0, 90, 180, 270):     # a loop of rope bulging out between two lashings
        a0, a1, am = math.radians(deg - 45), math.radians(deg + 45), math.radians(deg)
        d += 'M%s %s Q%s %s %s %s ' % (f(100 + 84 * math.cos(a0)), f(118 + 84 * math.sin(a0)), f(100 + 150 * math.cos(am)), f(118 + 150 * math.sin(am)),
                                       f(100 + 84 * math.cos(a1)), f(118 + 84 * math.sin(a1)))
    return d


D['canottieri-firenze'] = ('Canottieri Firenze', 'breathe', '100 210', '\n'.join([
    '<path fill="none" stroke="%s" stroke-width="7" d="%s"/>' % (C, rope_loops()),
    '<path fill="none" stroke="%s" stroke-width="2" stroke-dasharray="3 4" d="%s"/>' % (K, rope_loops()),     # twisted-rope look
    '<circle cx="100" cy="118" r="71" fill="none" stroke="%s" stroke-width="26"/>' % C,                     # the life buoy
    '<path fill="none" stroke="%s" stroke-width="2.5" d="%s"/>' % (K, ring_lashings()),
    '<path fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" d="M70 84 V170"/>' % C,         # staff
    '<path fill="%s" d="M72 86 L156 110 L72 132 Z"/>' % C,                                                   # pennant
    '<path fill="%s" d="M86 90 L96 93 L84 128 L78 129 Z M106 96 L116 99 L108 122 L100 124 Z M126 102 L134 104 L130 116 L122 118 Z"/>' % K,   # its diagonal stripes
]))
D['iris'] = ('Iris', 'sway', '100 210', '\n'.join([
    # a bearded iris: three rounded petals standing up, three wide ruffled petals hanging down, sword-shaped leaves
    '<path fill="%s" d="M97 210 Q96 170 98 120 H104 Q104 170 103 210 Z"/>' % C,                                          # stem
    '<path fill="%s" d="M92 210 Q64 170 58 100 Q76 150 98 204 Z M108 210 Q134 176 148 118 Q138 172 104 206 Z M90 210 Q78 190 70 160 Q86 186 96 206 Z"/>' % C,   # leaves
    '<path fill="%s" d="M100 96 Q78 70 84 44 Q90 26 100 22 Q110 26 116 44 Q122 70 100 96 Z"/>' % C,                     # centre standard
    '<path fill="%s" d="M98 94 Q66 84 62 60 Q62 44 74 44 Q80 70 100 88 Z M102 94 Q134 84 138 60 Q138 44 126 44 Q120 70 100 88 Z"/>' % C,   # side standards
    '<path fill="%s" d="M100 96 Q64 92 42 108 Q26 122 34 142 Q40 156 54 150 Q58 138 66 132 Q74 142 70 158 Q86 150 88 128 Q92 112 100 106 Z"/>' % C,   # left fall
    '<path fill="%s" d="M100 96 Q136 92 158 108 Q174 122 166 142 Q160 156 146 150 Q142 138 134 132 Q126 142 130 158 Q114 150 112 128 Q108 112 100 106 Z"/>' % C,   # right fall
    '<path fill="%s" d="M96 100 Q100 132 104 100 Z"/>' % C,                                                              # centre fall (front)
    '<path fill="none" stroke="%s" stroke-width="2" d="M98 100 Q76 108 56 136 M102 100 Q124 108 144 136 M100 90 V36 M92 112 Q100 126 108 112"/>' % K,   # veins and beard
]))




def svg(body, anim, pivot):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-40 -40 280 280" data-anim="%s" data-pivot="%s">\n%s\n</svg>' % (anim, pivot, body)


def main():
    html = open(INDEX, encoding='utf-8').read()
    taken = set(re.findall(r'<template id="animal-([^"]+)"', re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END), '', html, flags=re.S)))
    clash = [k for k in D if k in taken]
    if clash:
        sys.exit('ids already used by other pictures: %s' % clash)
    block = BEGIN + ' (generated by tools/draw_dev_favourite.py - edit the drawings there, then re-run) -->\n' + '\n'.join(
        '<template id="animal-%s" data-name="%s" data-cat="%s">%s</template>' % (k, name, CAT, svg(body, anim, pivot))
        for k, (name, anim, pivot, body) in D.items()) + '\n' + END
    if BEGIN in html:
        html = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END), lambda m: block, html, flags=re.S)
    else:
        html = html.replace('<!-- ======================== END ANIMAL DRAWINGS', block + '\n<!-- ======================== END ANIMAL DRAWINGS')
    open(INDEX, 'w', encoding='utf-8').write(html)
    print('%d pictures, %d KB' % (len(D), len(block.encode()) // 1024))
    if '--sheet' in sys.argv:
        os.makedirs(SHEET, exist_ok=True)
        cells = ''.join('<div style="display:inline-block;width:150px;margin:3px;text-align:center;font:12px sans-serif;color:#aaa;background:#000">'
                        '<div style="width:150px;height:150px;color:#ff3b1f">%s</div>%s</div>' % (svg(b, a, pv).replace('<svg ', '<svg width="150" height="150" '), n)
                        for k, (n, a, pv, b) in D.items())
        open(os.path.join(SHEET, 'sheet.html'), 'w').write('<body style="margin:4px;background:#222;width:940px">%s</body>' % cells)


if __name__ == '__main__':
    main()
