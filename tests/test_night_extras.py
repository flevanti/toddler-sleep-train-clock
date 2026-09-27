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
        p.evaluate("() => %s.setS({fadeSec: 0, showTimeNight: true, night: {extras: {countdown: {on: true}}}})" % H)
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
        check(tag + 'well after switch-off: 4 lit, 4 gone, 0 going', p.evaluate(LIT, '#below') == [4, 4, 0], p.evaluate(LIT, '#below'))
        p.evaluate("() => %s.repaint()" % H)
        p.clock.run_for(300)
        check(tag + 'repaint well after switch-off: still 0 going (no replay)', p.evaluate(LIT, '#below') == [4, 4, 0], p.evaluate(LIT, '#below'))
        p.evaluate("() => { window.__b = document.querySelector('#below svg'); }")
        p.clock.run_for(60000)
        check(tag + 'no redraw while no star goes out', p.evaluate("() => window.__b === document.querySelector('#below svg')"))
        at(p, 2026, 9, 24, 6, 59, 0)
        check(tag + 'just before wake: 1 lit', p.evaluate(LIT, '#below')[0] == 1, p.evaluate(LIT, '#below'))
        at(p, 2026, 9, 24, 7, 1, 0)
        check(tag + 'green: countdown gone', p.evaluate("() => document.getElementById('below').innerHTML") == '' and
              'below-on' not in p.evaluate("() => document.getElementById('clock').className"))

        p.evaluate("() => %s.setS({fadeSec: 0, night: {extras: {countdown: {on: true, count: 12, layout: 'row', out: 'pop'}}}})" % H)
        at(p, 2026, 9, 24, 19, 0, 0)
        check(tag + '12 stars at bedtime', p.evaluate(LIT, '#below') == [12, 0, 0], p.evaluate(LIT, '#below'))
        at(p, 2026, 9, 25, 1, 0, 0)
        ys = p.evaluate("() => [].map.call(document.querySelectorAll('#below [data-star=lit], #below [data-star=gone]'), function (e) { var b = e.getBBox(); return Math.round(b.y + b.height / 2); })")
        check(tag + 'row layout: all on one line', len(set(ys)) == 1, set(ys))
        check(tag + 'pop: going star shrinks', p.evaluate("() => !!document.querySelector('#below [data-star=going] animateTransform')"))
        p.screenshot(path=os.path.join(SHOTS, 'countdown_row_%dx%d.png' % vp))

        # nap: counts from nap start to nap end
        at(p, 2026, 9, 25, 13, 0, 0)
        p.evaluate("() => { var t = Date.now(); %s.setS({fadeSec: 0, night: {extras: {countdown: {on: true}}}, nap: {start: t, end: t + 45 * 60000}}); }" % H)
        p.clock.run_for(1100)
        check(tag + 'nap start: all lit', p.evaluate(LIT, '#below')[0] == 8, p.evaluate(LIT, '#below'))
        p.clock.run_for(int(22.5 * 60000))
        check(tag + 'nap half-way: 4 lit', p.evaluate(LIT, '#below')[0] == 4, p.evaluate(LIT, '#below'))
        p.evaluate("() => %s.setS({fadeSec: 0, night: {extras: {countdown: {on: true}}}})" % H)

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

    # ---- fireflies ----
    p.set_viewport_size({'width': 1024, 'height': 768})
    p.evaluate("() => %s.setS({fadeSec: 0, night: {extras: {fireflies: {on: true}}}})" % H)
    at(p, 2026, 9, 26, 22, 0, 0)
    ff = p.evaluate("""() => [].map.call(document.querySelectorAll('#layer circle'), function (c) {
        var m = c.querySelector('animateMotion'); return { fill: c.getAttribute('fill'), dur: m && parseFloat(m.getAttribute('dur')), path: m && m.getAttribute('path') }; })""")
    check('fireflies default: 5, night colour, very slow',
          len(ff) == 5 and all(f['fill'] == '#ff3b1f' and 40 <= f['dur'] <= 70 for f in ff), ff[:1])

    def path_max(fl):
        nums = [float(v) for f in fl for v in f['path'].replace('M', ' ').replace('Q', ' ').split()]
        return max(nums[0::2]), max(nums[1::2])

    mx, my = path_max(ff)
    check('firefly paths inside the screen', mx <= 1024 and my <= 768, (mx, my))
    p.screenshot(path=os.path.join(SHOTS, 'fireflies_1024x768.png'))
    p.evaluate("() => { window.__l = document.querySelector('#layer svg'); }")
    p.clock.run_for(5000)
    check('fireflies: no redraw between ticks', p.evaluate("() => window.__l === document.querySelector('#layer svg')"))
    p.evaluate("() => %s.repaint()" % H)
    p.clock.run_for(200)
    same = p.evaluate("() => [].map.call(document.querySelectorAll('#layer animateMotion'), function (m) { return m.getAttribute('path'); })")
    check('fireflies: same paths after a redraw', same == [f['path'] for f in ff])
    p.set_viewport_size({'width': 768, 'height': 1024})
    p.clock.run_for(1100)
    ff2 = p.evaluate("() => [].map.call(document.querySelectorAll('#layer circle'), function (c) { return { path: c.querySelector('animateMotion').getAttribute('path') }; })")
    mx, my = path_max(ff2)
    check('rotated: fireflies redrawn for the new size', mx <= 768 and my <= 1024 and ff2 != [{'path': f['path']} for f in ff], (mx, my))
    p.evaluate("() => %s.setS({fadeSec: 0, nightDim: 20, night: {extras: {fireflies: {on: true, count: 8, speed: 'slow', color: 'warm'}}}})" % H)
    p.clock.run_for(1100)
    ff = p.evaluate("() => [].map.call(document.querySelectorAll('#layer circle'), function (c) { return [c.getAttribute('fill'), parseFloat(c.querySelector('animateMotion').getAttribute('dur'))]; })")
    check('fireflies 8, warm, slow', len(ff) == 8 and all(f[0] == '#ffd27a' and 20 <= f[1] <= 35 for f in ff), ff[:1])
    check('fireflies dimmed with the night', p.evaluate("() => document.getElementById('layer').style.opacity") == '0.2')
    p.screenshot(path=os.path.join(SHOTS, 'fireflies_768x1024.png'))

    # mini preview also draws fireflies
    open_settings(p, (768, 1024))
    p.click('#pvtabs [data-pv="sleep"]')
    check('mini preview draws fireflies', p.evaluate("() => document.querySelectorAll('#miniLayer circle').length") == 8,
          p.evaluate("() => document.querySelectorAll('#miniLayer circle').length"))
    p.click('#done')

    # ---- shooting stars ----
    def ms(*a):
        return int(datetime.datetime(*a).timestamp() * 1000)

    since = ms(2026, 9, 26, 19, 0)

    def times(o, frm, to):
        return p.evaluate("([o, s, f, t]) => %s.night.shootingTimes(o, s, f, t)" % H, [o, since, frm, to])

    t1 = times({'every': 5, 'firstHour': True}, since, since + 6 * 3600000)
    gaps = [b_ - a_ for a_, b_ in zip([since] + t1, t1)]
    check('first hour only: 10–13 times, all within the hour', 10 <= len(t1) <= 13 and all(since < t <= since + 3600000 for t in t1), len(t1))
    check('spacing 5 min ± 30 % (gaps 2–8 min)', all(0.4 * 300000 <= g <= 1.6 * 300000 for g in gaps[1:]), [round(g / 60000, 1) for g in gaps])
    check('same inputs, same times', t1 == times({'every': 5, 'firstHour': True}, since, since + 6 * 3600000))
    t2 = times({'every': 10, 'firstHour': False}, since, since + 6 * 3600000)
    check('all night when not first hour only', max(t2) > since + 5 * 3600000 and 30 <= len(t2) <= 37, len(t2))
    check('window respected', all(since + 3600000 <= t < since + 7200000 for t in times({'every': 2, 'firstHour': False}, since + 3600000, since + 7200000)))

    p.set_viewport_size({'width': 1024, 'height': 768})
    p.evaluate("() => %s.setS({fadeSec: 0, night: {extras: {shooting: {on: true, every: 2}}}})" % H)
    at(p, 2026, 9, 26, 19, 10, 0)
    now = ms(2026, 9, 26, 19, 10, 1)
    shots = p.evaluate("() => [].map.call(document.querySelectorAll('#layer [data-shoot]'), function (g) { return [+g.getAttribute('data-shoot'), parseFloat(g.querySelector('animate').getAttribute('begin'))]; })")
    expect = times({'every': 2, 'firstHour': True}, now - 1000, since + 3600000 + 60000)
    check('drawn shooting stars = scheduled ones this hour', [s[0] for s in shots] == expect, (len(shots), len(expect)))
    check('each starts at its time', all(abs(s[1] - (s[0] - now) / 1000) < 2 for s in shots))
    p.screenshot(path=os.path.join(SHOTS, 'shooting_1024x768.png'))
    p.evaluate("() => { window.__l = document.querySelector('#layer svg'); }")
    p.clock.run_for(60000)
    check('shooting: no redraw within the hour', p.evaluate("() => window.__l === document.querySelector('#layer svg')"))
    at(p, 2026, 9, 26, 21, 0, 0)
    check('none after the first hour', p.evaluate("() => document.querySelectorAll('#layer [data-shoot]').length") == 0)
    check('no duplicate ids with all extras', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))

    # mini preview also draws a shooting star, independent of the real schedule
    open_settings(p, (1024, 768))
    p.click('#pvtabs [data-pv="sleep"]')
    check('mini preview draws a shooting star', p.evaluate("() => !!document.querySelector('#miniLayer [data-shoot]')"))
    p.click('#done')

    # once the first hour has passed, the layer stops rebuilding hourly (fireflies keep their state)
    p.evaluate("() => %s.setS({fadeSec: 0, night: {extras: {fireflies: {on: true}, shooting: {on: true, every: 5, firstHour: true}}}})" % H)
    at(p, 2026, 9, 26, 21, 0, 0)
    p.evaluate("() => { window.__l2 = document.querySelector('#layer svg'); }")
    at(p, 2026, 9, 26, 22, 0, 0)
    check('layer unchanged across the hour once shooting is done (fireflies do not restart)',
          p.evaluate("() => window.__l2 === document.querySelector('#layer svg')"))
    p.set_viewport_size({'width': 768, 'height': 1024})

    # simulation: begin times use the sped-up clock
    p.evaluate("() => %s.setS({fadeSec: 0, night: {extras: {shooting: {on: true, every: 2, firstHour: false}}}})" % H)
    open_settings(p, (768, 1024))
    p.click('#simBtn')
    begins = []
    for _ in range(300):
        p.clock.run_for(100)
        begins += p.evaluate("() => [].map.call(document.querySelectorAll('#layer [data-shoot] animate'), function (a) { return parseFloat(a.getAttribute('begin')); })")
    check('sim: shooting stars scheduled in sped-up time', bool(begins) and max(begins) < 3, max(begins) if begins else None)
    p.click('#simExit')
    p.click('#done')

    check('no page errors', not errs, errs)
    b.close()
srv.shutdown()
sys.exit(check.finish())
