"""Dev's Favourite pictures: hidden unless dev mode + its switch are on, a chosen one keeps showing, Pinocchio's nose grows."""
import datetime
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
CAT = "Dev's Favourite"
check = Checks()
srv, URL = serve(ROOT)
OPTS = "() => [].map.call(document.querySelectorAll('#na-animal-animal option'), function (o) { return o.textContent; })"
GROUPS = "() => [].map.call(document.querySelectorAll('#na-animal-animal optgroup'), function (g) { return g.label; })"
CHIPS = "() => [].map.call(document.querySelectorAll('#gchips button'), function (b) { return b.textContent; })"
CARDS = "() => [].map.call(document.querySelectorAll('#gtrack .gcard'), function (c) { return c.getAttribute('data-id'); })"
NOSE = "() => { var g = document.querySelector('#face [data-grow]'); return g ? g.getAttribute('transform') : null; }"


def ms(*a):
    return int(datetime.datetime(*a).timestamp() * 1000)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp
        p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.clock.install(time=datetime.datetime(2026, 9, 23, 12, 0, 0))
        p.goto(URL)
        p.evaluate("() => localStorage.clear()")
        p.reload()
        p.clock.run_for(300)
        pack = p.evaluate("(c) => { var A = %s.night.ANIMALS; return Object.keys(A).filter(function (k) { return A[k].cat === c; }); }" % H, CAT)
        names = p.evaluate("(ks) => ks.map(function (k) { return %s.night.ANIMALS[k].name; })" % H, pack)
        check('the pack is in the page (33 drawn + 6 imported)', len(pack) == 39, len(pack))

        # hidden by default
        p.evaluate("() => %s.setS({night: {scene: 'animal'}})" % H)
        open_settings(p, vp)
        check(tag + 'hidden from the picture list', CAT not in p.evaluate(GROUPS) and not set(names) & set(p.evaluate(OPTS)))
        p.click('[data-gallery=scene]')
        check(tag + 'hidden from the carousel', CAT not in p.evaluate(CHIPS) and not any(c.split(':')[-1] in pack for c in p.evaluate(CARDS)))
        p.click('#gclose')

        # dev mode on, switch off: still hidden; switch on: shown
        p.evaluate("() => %s.setS({night: {scene: 'animal'}, dev: {on: true, overlay: false, pack: false}})" % H)
        p.click('#done')
        open_settings(p, vp)
        check(tag + 'dev mode alone does not show the pack', CAT not in p.evaluate(GROUPS))
        p.evaluate("() => { var e = document.getElementById('dev-pack'); e.checked = true; e.dispatchEvent(new Event('change', {bubbles: true})); }")
        check(tag + 'switch on: pack in the picture list as its own group', p.evaluate(GROUPS)[-1] == CAT and set(names) <= set(p.evaluate(OPTS)), p.evaluate(GROUPS)[-2:])
        p.click('[data-gallery=scene]')
        chips = p.evaluate(CHIPS)
        check(tag + 'switch on: Dev\'s Favourite chip, last', chips[-1] == CAT, chips)
        p.click('#gchips button:has-text("%s")' % CAT)
        p.clock.run_for(100)
        check(tag + 'chip jumps to the pack and draws it', p.evaluate("() => !!document.querySelector('#gtrack .gcard .gstage svg[data-animal]')"))
        p.click('#gtrack [data-id="animal:duomo"]')
        check(tag + 'a pack picture can be chosen', p.evaluate("() => %s.S().night.scenes.animal.animal" % H) == 'duomo')

        # dev mode off: the chosen one keeps showing (and stays in the list), the others hide
        p.evaluate("() => { var s = %s.S(); s.dev.on = false; }" % H)
        p.click('#done')
        open_settings(p, vp)
        opts = p.evaluate(OPTS)
        check(tag + 'dev off: chosen pack picture stays selectable, the rest hide', 'Duomo' in opts and 'Palazzo Pitti' not in opts)
        p.click('#done')
        p.clock.set_system_time(datetime.datetime(2026, 9, 23, 22, 0, 0))
        p.clock.run_for(1100)
        check(tag + 'dev off: the clock keeps showing the chosen pack picture', p.evaluate("() => document.querySelector('#face svg').getAttribute('data-animal')") == 'duomo')

        # Pinocchio's nose grows through the night and is back to normal at bedtime
        p.evaluate("() => %s.setS({night: {scene: 'animal', scenes: {animal: {animal: 'pinocchio'}}}})" % H)
        grow = []
        for h, m in ((19, 0), (1, 0), (6, 50)):
            p.clock.set_system_time(datetime.datetime(2026, 9, 24 if h < 12 else 23, h, m, 30))
            p.clock.run_for(1100)
            grow.append(p.evaluate(NOSE))
        scales = [float(g.split('scale(')[1].split(')')[0]) if g else None for g in grow]
        check(tag + "Pinocchio's nose: normal at bedtime, longer at 1 am, longest before wake",
              scales[0] is not None and scales[0] < 1.05 and scales[0] < scales[1] < scales[2] and scales[2] >= 1.7, scales)
        p.evaluate("() => { window.__f = document.querySelector('#face svg'); }")
        p.clock.run_for(60000)
        check(tag + 'nose redraws in steps, not every tick', p.evaluate("() => window.__f === document.querySelector('#face svg')"))
        check(tag + 'no page errors', not errs, errs)
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
