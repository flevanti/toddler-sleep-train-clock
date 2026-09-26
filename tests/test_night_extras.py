"""Night extras: star countdown maths and drawing (fireflies and shooting stars are added in Task 6)."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
LIT = "(root) => ['lit', 'gone', 'going'].map(function (k) { return document.querySelectorAll(root + ' [data-star=' + k + ']').length; })"
DUP_IDS = "() => { var seen = {}, d = []; [].forEach.call(document.querySelectorAll('[id]'), function (e) { if (seen[e.id]) d.push(e.id); seen[e.id] = 1; }); return d; }"


def at(p, *a):
    p.clock.set_system_time(datetime.datetime(*a))
    p.clock.run_for(1100)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={'width': 1024, 'height': 768})
    errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.clock.install(time=datetime.datetime(2026, 9, 23, 18, 0, 0))  # Wednesday
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(300)

    def lit(n, f):
        return p.evaluate("([n, f]) => %s.night.countdownLit(n, f)" % H, [n, f])

    got = [lit(8, 0), lit(8, 0.5), lit(8, 0.99999), lit(8, 1), lit(5, 0.5), lit(12, 1 / 12), lit(8, -1), lit(8, 2)]
    check('countdownLit maths', got == [8, 4, 1, 0, 3, 11, 8, 0], got)

    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp
        p.set_viewport_size({'width': vp[0], 'height': vp[1]})
        p.evaluate("() => %s.setS({showTimeNight: true, night: {extras: {countdown: {on: true}}}})" % H)
        at(p, 2026, 9, 23, 19, 0, 0)
        check(tag + 'bedtime: all 8 lit', p.evaluate(LIT, '#below') == [8, 0, 0], p.evaluate(LIT, '#below'))
        check(tag + 'face shrinks to make room', 'below-on' in p.evaluate("() => document.getElementById('clock').className"))
        fits = p.evaluate("() => document.getElementById('time').getBoundingClientRect().bottom <= window.innerHeight")
        check(tag + 'face, countdown and time fit on screen', fits)
        at(p, 2026, 9, 24, 1, 0, 0)
        check(tag + 'middle of the night: 4 lit, 4 gone, 1 going out', p.evaluate(LIT, '#below') == [4, 4, 1], p.evaluate(LIT, '#below'))
        check(tag + 'fade: going star fades over 3 s',
              p.evaluate("() => { var a = document.querySelector('#below [data-star=going] animate'); return a && a.getAttribute('dur'); }") == '3s')
        p.screenshot(path=os.path.join(SHOTS, 'countdown_arc_%dx%d.png' % vp))
        at(p, 2026, 9, 24, 1, 10, 0)
        p.evaluate("() => { window.__b = document.querySelector('#below svg'); }")
        p.clock.run_for(60000)
        check(tag + 'no redraw while no star goes out', p.evaluate("() => window.__b === document.querySelector('#below svg')"))
        at(p, 2026, 9, 24, 6, 59, 0)
        check(tag + 'just before wake: 1 lit', p.evaluate(LIT, '#below')[0] == 1, p.evaluate(LIT, '#below'))
        at(p, 2026, 9, 24, 7, 1, 0)
        check(tag + 'green: countdown gone', p.evaluate("() => document.getElementById('below').innerHTML") == '' and
              'below-on' not in p.evaluate("() => document.getElementById('clock').className"))

        p.evaluate("() => %s.setS({night: {extras: {countdown: {on: true, count: 12, layout: 'row', out: 'pop'}}}})" % H)
        at(p, 2026, 9, 24, 19, 0, 0)
        check(tag + '12 stars at bedtime', p.evaluate(LIT, '#below') == [12, 0, 0], p.evaluate(LIT, '#below'))
        at(p, 2026, 9, 25, 1, 0, 0)
        ys = p.evaluate("() => [].map.call(document.querySelectorAll('#below [data-star=lit], #below [data-star=gone]'), function (e) { var b = e.getBBox(); return Math.round(b.y + b.height / 2); })")
        check(tag + 'row layout: all on one line', len(set(ys)) == 1, set(ys))
        check(tag + 'pop: going star shrinks', p.evaluate("() => !!document.querySelector('#below [data-star=going] animateTransform')"))
        p.screenshot(path=os.path.join(SHOTS, 'countdown_row_%dx%d.png' % vp))

        # nap: counts from nap start to nap end
        at(p, 2026, 9, 25, 13, 0, 0)
        p.evaluate("() => { var t = Date.now(); %s.setS({night: {extras: {countdown: {on: true}}}, nap: {start: t, end: t + 45 * 60000}}); }" % H)
        p.clock.run_for(1100)
        check(tag + 'nap start: all lit', p.evaluate(LIT, '#below')[0] == 8, p.evaluate(LIT, '#below'))
        p.clock.run_for(int(22.5 * 60000))
        check(tag + 'nap half-way: 4 lit', p.evaluate(LIT, '#below')[0] == 4, p.evaluate(LIT, '#below'))
        p.evaluate("() => %s.setS({night: {extras: {countdown: {on: true}}}})" % H)

        # preview shows a half-finished night
        open_settings(p, vp)
        p.click('#pvtabs [data-pv="sleep"]')
        check(tag + 'mini: half the stars lit', p.evaluate(LIT, '#miniBelow')[0] == 4, p.evaluate(LIT, '#miniBelow'))
        check(tag + 'no duplicate ids', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))

        # simulation: stars go out as pretend time passes
        p.click('#simBtn')
        seen = []
        for _ in range(620):
            p.clock.run_for(100)
            s = p.evaluate("() => { var s = %s.sim(); return s ? s.mode : null; }" % H)
            if s == 'sleep':
                seen.append(p.evaluate(LIT, '#below')[0])
        after_bed = seen[seen.index(8):] if 8 in seen else []
        check(tag + 'sim: 8 at bedtime, then only goes down',
              bool(after_bed) and all(a >= b for a, b in zip(after_bed, after_bed[1:])) and after_bed[-1] <= 2, after_bed[:3] + ['…'] + after_bed[-3:])
        p.clock.run_for(6000)  # simulation ends and returns to settings
        p.click('#done')
    check('no page errors', not errs, errs)
    b.close()
srv.shutdown()
sys.exit(check.finish())
