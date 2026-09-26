"""Night scenes and drawing: timing (since/frac), per-area redraw keys, ids, dimming, fade, a screenshot of every scene."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
DUP_IDS = "() => { var seen = {}, d = []; [].forEach.call(document.querySelectorAll('[id]'), function (e) { if (seen[e.id]) d.push(e.id); seen[e.id] = 1; }); return d; }"
# inside a paint target only its container ids and gradients named after its gid are allowed
STRAY_IDS = """([root, gid, keep]) => [].filter.call(document.querySelectorAll(root + ' [id]'), function (e) {
    return keep.indexOf(e.id) < 0 && !(e.id.indexOf(gid) === 0 && /Gradient$/.test(e.tagName)); }).map(function (e) { return e.tagName + '#' + e.id; })"""
MAIN_KEEP = ['face', 'below', 'time', 'label', 'layer']
MINI_KEEP = ['miniFace', 'miniBelow', 'miniTime', 'miniLabel', 'miniLayer']
BREATH = "(root) => { var a = document.querySelector(root + ' animateTransform'); return a ? [a.getAttribute('dur'), a.getAttribute('values'), !!document.querySelector(root + ' radialGradient[id$=Halo]')] : null; }"


def ms(*a):
    return int(datetime.datetime(*a).timestamp() * 1000)


with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ---- timing ----
    p = b.new_page(viewport={'width': 1024, 'height': 768})
    p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))  # Wednesday night
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(300)
    days = [{'bed': '19:00', 'wake': '07:00', 'tone': 'off'} for _ in range(7)]
    days[0]['bed'] = '20:30'  # Sunday
    p.evaluate("(d) => %s.setS({days: d})" % H, days)

    def st(*a):
        return p.evaluate("(t) => %s.computeState(new Date(t))" % H, ms(*a))

    s = st(2026, 9, 23, 22, 0)
    check('evening: since = tonight bedtime', s.get('since') == ms(2026, 9, 23, 19, 0) and s.get('until') == ms(2026, 9, 24, 7, 0), s)
    s = st(2026, 9, 24, 3, 0)
    check('after midnight: since = yesterday bedtime', s.get('since') == ms(2026, 9, 23, 19, 0), s)
    s = st(2026, 9, 28, 3, 0)  # Monday 03:00; Sunday bedtime differs
    check('uses the previous day schedule (Sun 20:30)', s.get('since') == ms(2026, 9, 27, 20, 30), s)

    def frac(t, a, z):
        return p.evaluate("([t, a, z]) => %s.nightFrac({since: a, until: z}, new Date(t))" % H, [t, a, z])

    a, z = ms(2026, 9, 23, 19, 0), ms(2026, 9, 24, 7, 0)
    check('frac 0 / 0.5 / 1', [frac(a, a, z), frac((a + z) // 2, a, z), frac(z, a, z)] == [0, 0.5, 1])
    check('frac clamps and handles missing times',
          [frac(a - 60000, a, z), frac(z + 60000, a, z), p.evaluate("() => %s.nightFrac({}, new Date())" % H)] == [0, 1, 0])
    p.evaluate("() => { var t = Date.now(); %s.setS({nap: {start: t - 600000, end: t + 1200000}}); }" % H)
    s = p.evaluate("() => %s.computeState(new Date())" % H)
    check('nap: since = nap start', s.get('nap') is True and s.get('since') == s.get('until', 0) - 1800000, s)
    p.close()

    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp
        p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))
        p.goto(URL)
        p.evaluate("() => localStorage.clear()")
        p.reload()
        p.clock.run_for(300)

        # every registered scene (later tasks' scenes are picked up automatically)
        for sc in p.evaluate("() => Object.keys(%s.night.SCENES)" % H):
            p.evaluate("(k) => %s.setS({night: {scene: k}})" % H, sc)
            p.clock.run_for(1100)
            check(tag + sc + ': face drawn', p.evaluate("() => !!document.querySelector('#face svg')"))
            stray = p.evaluate(STRAY_IDS, ['#clock', 'shMain', MAIN_KEEP])
            check(tag + sc + ': no stray ids', stray == [], stray)
            p.evaluate("() => { window.__f = document.querySelector('#face svg'); window.__l = document.getElementById('layer').firstChild; }")
            p.clock.run_for(3000)
            check(tag + sc + ': no redraw between ticks',
                  p.evaluate("() => window.__f === document.querySelector('#face svg') && window.__l === document.getElementById('layer').firstChild"))
            p.screenshot(path=os.path.join(SHOTS, 'night_%s_%dx%d.png' % (sc, vp[0], vp[1])))

        # Z's & stars: default look unchanged, settings apply
        count = "() => [document.querySelectorAll('#face .twinkle').length, document.querySelectorAll('#face .zz').length, document.querySelectorAll('#face .slow').length]"
        p.evaluate("() => %s.setS({})" % H)
        p.clock.run_for(1100)
        check(tag + 'classic default = 3 stars, 2 z, normal speed', p.evaluate(count) == [3, 2, 0], p.evaluate(count))
        p.evaluate("() => %s.setS({night: {scenes: {classic: {stars: 10, zz: false, speed: 'slow'}}}})" % H)
        p.clock.run_for(1100)
        check(tag + 'classic 10 stars, no z, slow', p.evaluate(count) == [10, 0, 1], p.evaluate(count))

        # breathing
        p.evaluate("() => %s.setS({night: {scene: 'breathing'}})" % H)
        p.clock.run_for(1100)
        check(tag + 'breathing default: 10 s, 4 %, glow', p.evaluate(BREATH, '#face') == ['10s', '1;1.04;1', True], p.evaluate(BREATH, '#face'))
        p.evaluate("() => %s.setS({night: {scene: 'breathing', scenes: {breathing: {pace: 8, depth: 'deep', glow: false}}}})" % H)
        p.clock.run_for(1100)
        check(tag + 'breathing 8/min, deep, no glow', p.evaluate(BREATH, '#face') == ['7.5s', '1;1.07;1', False], p.evaluate(BREATH, '#face'))

        # moon & sky
        p.evaluate("() => %s.setS({night: {scene: 'moon'}})" % H)
        p.clock.run_for(1100)
        sky = p.evaluate("""() => { var l = document.getElementById('layer');
            return { stars: l.querySelectorAll('circle').length, anim: [].map.call(l.querySelectorAll('animate'), function (a) { return a.getAttribute('dur'); }),
                     pos: [].map.call(l.querySelectorAll('circle'), function (c) { return [parseFloat(c.getAttribute('cx')), parseFloat(c.getAttribute('cy'))]; }),
                     face: document.querySelectorAll('#face path').length }; }""")
        check(tag + 'moon default: 25 sky stars, slow twinkle, face', sky['stars'] == 25 and sky['anim'] == ['7s', '9s', '11s'] and sky['face'] == 2, sky['anim'])
        check(tag + 'sky stars keep clear of moon and time', all(not (22 < x < 78 and 8 < y < 88) for x, y in sky['pos']))
        p.evaluate("() => %s.setS({nightDim: 30, night: {scene: 'moon', scenes: {moon: {sky: 50, twinkle: 'off', face: false}}}})" % H)
        p.clock.run_for(1100)
        sky = p.evaluate("() => { var l = document.getElementById('layer'); return [l.querySelectorAll('circle').length, l.querySelectorAll('animate').length, document.querySelectorAll('#face path').length, l.style.opacity]; }")
        check(tag + 'moon 50 stars, no twinkle, no face, dimmed', sky == [50, 0, 0, '0.3'], sky)

        # night brightness reaches every area
        p.evaluate("() => %s.setS({nightDim: 40})" % H)
        p.clock.run_for(1100)
        op = p.evaluate("() => ['face', 'below', 'layer'].map(function (id) { return document.getElementById(id).style.opacity; })")
        check(tag + 'night brightness dims face, below and layer', op == ['0.4', '0.4', '0.4'], op)

        # nothing drawn outside the night
        p.clock.set_system_time(datetime.datetime(2026, 9, 24, 12, 0, 0))
        p.clock.run_for(1100)
        check(tag + 'day: below and layer empty',
              p.evaluate("() => document.getElementById('below').innerHTML === '' && document.getElementById('layer').innerHTML === ''"))

        # mini preview draws the scene too
        p.evaluate("() => %s.setS({night: {scene: 'breathing'}})" % H)
        open_settings(p, vp)
        p.click('#pvtabs [data-pv="sleep"]')
        check(tag + 'mini shows the scene', p.evaluate(BREATH, '#miniFace') is not None)
        stray = p.evaluate(STRAY_IDS, ['#mini', 'shMini', MINI_KEEP])
        check(tag + 'mini: no stray ids', stray == [], stray)
        check(tag + 'no duplicate ids with both targets', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))
        p.click('#done')

        # phase-change fade copy of a scene that has its own gradient
        p.evaluate("() => %s.setS({soonMin: 15, fadeSec: 3, night: {scene: 'breathing'}})" % H)
        p.clock.set_system_time(datetime.datetime(2026, 9, 25, 6, 44, 57))
        p.clock.run_for(1100)
        p.clock.run_for(3500)  # crosses 06:45 -> amber
        check(tag + 'fade copy present', p.evaluate("() => document.querySelectorAll('.clk.snap').length") == 1)
        check(tag + 'no duplicate ids during fade', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))
        refs = p.evaluate("() => [].map.call(document.querySelectorAll('.clk.snap [fill^=url]'), function (e) { var m = /#(.+)\\)/.exec(e.getAttribute('fill')); return !!(m && document.getElementById(m[1])); })")
        check(tag + 'fade copy gradient refs resolve', bool(refs) and all(refs), refs)
        check(tag + 'no page errors', not errs, errs)
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
