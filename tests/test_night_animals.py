"""Sleeping animals: every animal draws, breathing + little movements settings, ids, screenshot sheet for review."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
EXPECTED = ['bunny', 'bear', 'cat', 'owl']
check = Checks()
srv, URL = serve(ROOT)
STRAY = "() => [].filter.call(document.querySelectorAll('#face [id]'), function (e) { return !(e.id.indexOf('shMain') === 0 && /Gradient$/.test(e.tagName)); }).length"

with sync_playwright() as pw:
    b = pw.chromium.launch()
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
        names = p.evaluate("() => %s.night.ANIMALS ? Object.keys(%s.night.ANIMALS) : []" % (H, H))
        check(tag + 'animals registered in order', names == EXPECTED, names)
        check(tag + 'default animal is bunny', p.evaluate("() => %s.S().night.scenes.animal && %s.S().night.scenes.animal.animal" % (H, H)) == 'bunny')
        for a in names:
            p.evaluate("(a) => %s.setS({night: {scene: 'animal', scenes: {animal: {animal: a}}}})" % H, a)
            p.clock.run_for(1100)
            info = p.evaluate("""() => { var s = document.querySelector('#face svg');
                return s ? { animal: s.getAttribute('data-animal'), breath: !!s.querySelector('[data-part=body] > animateTransform'),
                             moves: [].map.call(s.querySelectorAll('[data-move] > animateTransform'), function (m) { return m.getAttribute('dur'); }) } : null; }""")
            check(tag + a + ': drawn, breathing, rare movements',
                  info and info['animal'] == a and info['breath'] and len(info['moves']) >= 1 and set(info['moves']) == {'20s'}, info)
            check(tag + a + ': no stray ids', p.evaluate(STRAY) == 0)
            p.locator('#face').screenshot(path=os.path.join(SHOTS, 'animal_%s_%dx%d.png' % (a, vp[0], vp[1])))
        p.evaluate("() => %s.setS({night: {scene: 'animal', scenes: {animal: {animal: 'cat', breath: false, moves: 'off'}}}})" % H)
        p.clock.run_for(1100)
        check(tag + 'breathing off, movements off',
              p.evaluate("() => !document.querySelector('#face [data-part=body] > animateTransform') && !document.querySelector('#face [data-move]')"))
        p.evaluate("() => %s.setS({night: {scene: 'animal', scenes: {animal: {animal: 'cat', moves: 'normal'}}}})" % H)
        p.clock.run_for(1100)
        check(tag + 'normal movements every 8 s',
              p.evaluate("() => [].every.call(document.querySelectorAll('#face [data-move] > animateTransform'), function (m) { return m.getAttribute('dur') === '8s'; })"))
        open_settings(p, vp)
        opts = p.evaluate("() => [].map.call(document.querySelectorAll('#na-animal-animal option'), function (o) { return o.textContent; })")
        check(tag + 'settings list every animal', len(opts) == len(EXPECTED), opts)
        p.select_option('#na-animal-animal', label=opts[-1])
        check(tag + 'choosing an animal saves it', p.evaluate("() => %s.S().night.scenes.animal.animal" % H) == EXPECTED[-1])
        check(tag + 'mini shows the chosen animal', p.evaluate("() => document.querySelector('#miniFace svg').getAttribute('data-animal')") == EXPECTED[-1])
        check(tag + 'no page errors', not errs, errs)
        p.close()

    # one sheet with every animal, for a visual review
    p = b.new_page(viewport={'width': 1000, 'height': 800})
    p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))
    p.goto(URL)
    p.clock.run_for(300)
    p.evaluate("""(list) => { var N = window.__toddlerSleepTrainClock.night, d = document.createElement('div');
        d.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99;background:#000;display:flex;flex-wrap:wrap;align-content:flex-start';
        list.forEach(function (k) { var c = document.createElement('div');
          c.style.cssText = 'width:20%;padding:6px;box-sizing:border-box;color:#888;font:13px sans-serif;text-align:center';
          c.innerHTML = N.sceneAnimal({animal: k, breath: false, moves: 'off'}, {color: '#ff3b1f', gid: 'sheet' + k}) + '<div>' + k + '</div>';
          c.firstChild.style.width = '100%'; d.appendChild(c); });
        document.body.appendChild(d); }""", EXPECTED)
    p.screenshot(path=os.path.join(SHOTS, 'animals_sheet.png'))
    p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
