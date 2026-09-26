"""Night animation controls: built from the registry, save typed values, extras rows, preview follows."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
TOGGLE = "(id) => { var e = document.getElementById(id); e.checked = !e.checked; e.dispatchEvent(new Event('change', {bubbles: true})); }"
ACTIVE = "() => document.querySelector('#pvtabs .b:not(.g)').getAttribute('data-pv')"

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
        open_settings(p, vp)

        names = p.evaluate("() => [].map.call(document.querySelectorAll('#na-scene option'), function (o) { return o.textContent; })")
        reg = p.evaluate("() => { var S = %s.night.SCENES; return Object.keys(S).map(function (k) { return S[k].name; }); }" % H)
        check(tag + 'scene list = registry', names == reg and len(reg) >= 3, names)
        check(tag + 'classic rows inside the Night section',
              p.evaluate("() => ['na-classic-stars', 'na-classic-zz', 'na-classic-speed'].every(function (i) { return !!document.querySelector('.sec[data-pv=sleep] #' + i); })"))

        p.select_option('#na-classic-stars', label='10')
        v = p.evaluate("() => %s.S().night.scenes.classic.stars" % H)
        check(tag + 'choice saved with its type', v == 10 and isinstance(v, int), v)
        check(tag + 'preview switched to Night', p.evaluate(ACTIVE) == 'sleep')
        check(tag + 'mini shows 10 stars', p.evaluate("() => document.querySelectorAll('#miniFace .twinkle').length") == 10)

        p.evaluate("() => { document.getElementById('sbody').scrollTop = 500; }")
        p.select_option('#na-scene', 'breathing')
        check(tag + 'scene saved', p.evaluate("() => %s.S().night.scene" % H) == 'breathing')
        check(tag + 'rows swapped to breathing',
              p.evaluate("() => !!document.getElementById('na-breathing-pace') && !document.getElementById('na-classic-stars')"))
        sc = p.evaluate("() => document.getElementById('sbody').scrollTop")
        check(tag + 'scroll kept after rebuild', sc == 500, sc)

        p.select_option('#na-breathing-pace', label='8 breaths a minute')
        p.evaluate(TOGGLE, 'na-breathing-glow')
        n = p.evaluate("() => %s.S().night.scenes.breathing" % H)
        check(tag + 'breathing controls save', n == {'pace': 8, 'depth': 'medium', 'glow': False}, n)
        dur = p.evaluate("() => { var a = document.querySelector('#miniFace animateTransform'); return a && a.getAttribute('dur'); }")
        check(tag + 'mini breathing at 7.5 s', dur == '7.5s', dur)

        p.select_option('#na-scene', 'classic')
        check(tag + 'classic settings remembered',
              p.evaluate("() => document.getElementById('na-classic-stars').selectedOptions[0].textContent") == '10')
        p.select_option('#na-scene', 'off')
        check(tag + 'off has no rows', p.evaluate("() => document.querySelectorAll('[id^=na-off-]').length") == 0)

        # every registered extra: a switch; its rows only while on (later tasks' extras are picked up automatically)
        for x in p.evaluate("() => Object.keys(%s.night.EXTRAS)" % H):
            check(tag + x + ': switch shown, rows hidden while off',
                  p.evaluate("(x) => !!document.getElementById('nx-' + x + '-on') && document.querySelectorAll('[id^=nx-' + x + '-]').length === 1", x))
            p.evaluate(TOGGLE, 'nx-%s-on' % x)
            n_opts = p.evaluate("(x) => %s.night.EXTRAS[x].opts.length" % H, x)
            check(tag + x + ': turning on saves and shows its rows',
                  p.evaluate("(x) => %s.S().night.extras[x].on" % H, x) is True and
                  p.evaluate("(x) => document.querySelectorAll('[id^=nx-' + x + '-]').length", x) == n_opts + 1)

        ov = p.evaluate("() => { var w = document.getElementById('swrap'); return w.scrollWidth <= w.clientWidth + 1; }")
        check(tag + 'no horizontal overflow', ov)
        p.locator('.sec[data-pv=sleep]').scroll_into_view_if_needed()
        p.screenshot(path=os.path.join(SHOTS, 'night_settings_%dx%d.png' % vp))
        check(tag + 'no page errors', not errs, errs)
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
