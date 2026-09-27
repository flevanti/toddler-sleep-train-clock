"""Dev mode: the long-hold trigger (settings / dev toggle / give up), PIN, soft ON/OFF message, Developer section, stats overlay."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)


def hold(p, vp, ms):
    """Press the top-right corner for ms (fake clock), then release."""
    p.mouse.move(vp[0] - 30, 30)
    p.mouse.down()
    p.clock.run_for(ms)
    p.mouse.up()
    p.clock.run_for(100)


def ring(p):
    return p.evaluate("() => [document.getElementById('hotring').style.opacity, document.getElementById('hotbase').getAttribute('stroke'), document.getElementById('hotarc').getAttribute('stroke')]")


def dev(p):
    return p.evaluate("() => %s.S().dev" % H)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp
        p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))  # night
        p.goto(URL)
        p.evaluate("() => localStorage.clear()")
        p.reload()
        p.clock.run_for(300)

        check(tag + 'dev mode off by default, features off', dev(p) == {'on': False, 'overlay': False, 'pack': False}, dev(p))

        # ---- ring stages while holding ----
        p.mouse.move(vp[0] - 30, 30)
        p.mouse.down()
        p.clock.run_for(1000)
        r0 = ring(p)
        p.clock.run_for(2000)   # 3 s: settings armed, purple starts
        r1 = ring(p)
        p.clock.run_for(2500)   # 5.5 s: dev armed
        r2 = ring(p)
        p.clock.run_for(5000)   # 10.5 s: gave up
        r3 = ring(p)
        p.mouse.up()
        p.clock.run_for(200)
        check(tag + 'ring: white while filling', r0[0] == '1' and r0[2] == '#fff', r0)
        check(tag + 'ring: green base + purple arc after 2.5 s', r1[1] == '#34c759' and r1[2] == '#a66bff', r1)
        check(tag + 'ring: solid purple after 5 s', r2[1] == '#a66bff', r2)
        check(tag + 'ring: fades after 10 s', r3[0] == '0', r3)
        check(tag + 'held > 10 s: nothing opens, nothing toggles', not p.is_visible('#settings') and not dev(p)['on'])

        # ---- short hold: nothing; 2.5–5 s: settings on release ----
        hold(p, vp, 1500)
        check(tag + 'released before 2.5 s: nothing opens', not p.is_visible('#settings'))
        p.mouse.move(vp[0] - 30, 30)
        p.mouse.down()
        p.clock.run_for(2700)
        check(tag + 'settings do not open while still holding', not p.is_visible('#settings'))
        p.mouse.up()
        p.clock.run_for(100)
        check(tag + 'settings open on release after 2.5 s', p.is_visible('#settings') and not dev(p)['on'])
        check(tag + 'no Developer section when dev mode is off', p.evaluate("() => !document.querySelector('#swrap .sec[data-dev]')"))
        p.click('#done')

        # ---- 5–10 s: dev mode toggles, soft message, then settings ----
        hold(p, vp, 5500)
        check(tag + 'dev mode switched on', dev(p)['on'] is True)
        msg = p.evaluate("() => { var f = document.getElementById('devflash'); return [getComputedStyle(f).display, f.textContent, f.style.color, f.style.opacity]; }")
        check(tag + 'soft DEV MODE ON message in the night colour, dimmed', msg[0] != 'none' and msg[1] == 'DEV MODE ON' and msg[2] == 'rgb(255, 59, 31)' and float(msg[3]) <= 0.35 + 1e-9, msg)
        check(tag + 'settings wait for the message', not p.is_visible('#settings'))
        p.clock.run_for(1600)
        check(tag + 'then settings open, message gone', p.is_visible('#settings') and not p.is_visible('#devflash'))
        check(tag + 'DEV badge in the header', p.is_visible('#devbadge'))
        check(tag + 'Developer section with its switches',
              p.evaluate("() => { var s = document.querySelector('#swrap .sec[data-dev]'); return !!s && !!s.querySelector('#dev-overlay') && !!s.querySelector('#dev-pack'); }"))
        before = p.evaluate("() => document.getElementById('clock').innerHTML.length")
        p.click('#done')
        p.clock.run_for(1100)
        check(tag + 'dev mode with no features: clock unchanged, no overlay',
              not p.is_visible('#devstats') and abs(p.evaluate("() => document.getElementById('clock').innerHTML.length") - before) < 50)

        # ---- stats overlay ----
        hold(p, vp, 2700)
        p.evaluate("() => { var e = document.getElementById('dev-overlay'); e.checked = true; e.dispatchEvent(new Event('change', {bubbles: true})); }")
        p.click('#done')
        p.clock.run_for(3100)
        check(tag + 'overlay switch saved', dev(p) == {'on': True, 'overlay': True, 'pack': False}, dev(p))
        stats = p.inner_text('#devstats') if p.is_visible('#devstats') else ''
        for label in ['v1.', 'tick delay', 'redraws', 'animations', 'up ', 'loads today', 'sound', 'online', 'offline copy', 'storage', 'phase night']:
            check(tag + 'overlay shows ' + label.strip(), label in stats, stats.replace('\n', ' | ')[:160])
        box = p.evaluate("() => { var r = document.getElementById('devstats').getBoundingClientRect(); return [r.left, r.bottom, window.innerHeight, getComputedStyle(document.getElementById('devstats')).pointerEvents]; }")
        check(tag + 'overlay bottom-left, not tappable', box[0] < 40 and box[2] - box[1] < 40 and box[3] == 'none', box)
        up1 = stats
        p.clock.run_for(2000)
        check(tag + 'overlay updates every second', p.inner_text('#devstats') != up1)
        p.screenshot(path=os.path.join(SHOTS, 'dev_overlay_%dx%d.png' % vp))

        # ---- PIN before toggling; OFF keeps the switches ----
        p.evaluate("() => { var s = %s.S(); s.pin = '1234'; }" % H)
        hold(p, vp, 5500)
        check(tag + 'PIN asked before toggling', p.is_visible('#pinpad') and dev(p)['on'] is True)
        for k in '1234':
            p.click('#pinkeys [data-k="%s"]' % k)
        p.clock.run_for(300)
        check(tag + 'after the PIN: dev mode OFF, message shown', dev(p)['on'] is False and p.inner_text('#devflash') == 'DEV MODE OFF')
        p.clock.run_for(1600)
        check(tag + 'switches remembered while off', dev(p) == {'on': False, 'overlay': True, 'pack': False}, dev(p))
        check(tag + 'no Developer section and no badge when off', p.evaluate("() => !document.querySelector('#swrap .sec[data-dev]')") and not p.is_visible('#devbadge'))
        p.click('#done')
        p.clock.run_for(1100)
        check(tag + 'overlay paused while dev mode is off', not p.is_visible('#devstats'))
        p.evaluate("() => { var s = %s.S(); s.pin = ''; }" % H)

        # ---- saved settings: bad dev values fall back ----
        p.evaluate("() => localStorage.setItem('toddler-sleep-train-clock.settings.v1', JSON.stringify({dev: {on: 'yes', overlay: true, pack: 1, bogus: true}}))")
        p.reload()
        p.clock.run_for(300)
        check(tag + 'invalid dev values ignored', dev(p) == {'on': False, 'overlay': True, 'pack': False}, dev(p))
        check(tag + 'no page errors', not errs, errs)
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
