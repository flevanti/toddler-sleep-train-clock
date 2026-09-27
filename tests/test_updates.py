"""Updates: Reload button, "Check now", and the optional "New version available" note on the clock (day and green only)."""
import datetime
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
html = open(ROOT + '/index.html', encoding='utf-8').read()
FAKE = html.replace("var VERSION = '", "var VERSION = '9.9'; var OLD = '", 1)   # the "published" copy is newer
NOTE = "() => { var n = document.getElementById('updnote'), cs = getComputedStyle(n); return [cs.display, n.textContent, cs.color, +cs.opacity]; }"
STATUS = "() => { var e = document.getElementById('updStatus'); return e ? e.textContent : null; }"
server = {'mode': 'newer', 'checks': 0}   # what the page gets when it fetches itself: newer | same | offline


def route(r):
    if r.request.resource_type != 'fetch':
        return r.continue_()
    server['checks'] += 1
    if server['mode'] == 'offline':
        return r.abort()
    if server['mode'] == 'same':
        return r.continue_()
    return r.fulfill(status=200, content_type='text/html', body=FAKE)


def fresh(b, vp, when, settings=None):
    p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
    p.route(URL, route)
    p.clock.install(time=when)
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(500)
    if settings is not None:
        p.evaluate("(o) => %s.setS(o)" % H, settings)
    return p


def settle(p, ms=1100):
    """Let the fetch resolve (real time) and the 1-second timer redraw the note (fake time)."""
    p.wait_for_timeout(150)
    p.clock.run_for(ms)
    p.wait_for_timeout(150)


DAY = datetime.datetime(2026, 9, 23, 10, 0, 0)     # schedule: wake 07:00, green 60 min, then day
GREEN = datetime.datetime(2026, 9, 23, 7, 10, 0)
NIGHT = datetime.datetime(2026, 9, 23, 22, 0, 0)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp

        # ---- defaults: off, no checks on its own ----
        server.update(mode='newer', checks=0)
        p = fresh(b, vp, DAY)
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        check(tag + '"show new version" is off by default', p.evaluate("() => %s.S().updateNotice" % H) is False)
        p.clock.fast_forward(4 * 3600 * 1000)
        settle(p)
        check(tag + 'switched off: never checks by itself', server['checks'] == 0, server['checks'])

        # ---- settings: Updates section, Check now ----
        open_settings(p, vp)
        check(tag + 'Updates section with Reload, Check now and the switch',
              p.evaluate("() => !!(document.getElementById('reloadApp') && document.getElementById('checkUpd') && document.getElementById('updateNotice'))"))
        check(tag + 'status says not checked yet', p.evaluate(STATUS) == 'Not checked yet.', p.evaluate(STATUS))
        p.evaluate("() => { window.__marker = 1; }")
        p.click('#checkUpd')
        p.wait_for_function("() => /available/.test(document.getElementById('updStatus').textContent)", timeout=5000)
        check(tag + 'Check now finds the newer version', 'Version 9.9 is available' in p.evaluate(STATUS), p.evaluate(STATUS))
        check(tag + 'known to the app', p.evaluate("() => %s.newVersion()" % H) == '9.9')
        settle(p)
        check(tag + 'but nothing reloads by itself', p.evaluate("() => window.__marker") == 1)
        server['mode'] = 'same'
        p.click('#checkUpd')
        p.wait_for_function("() => /latest/.test(document.getElementById('updStatus').textContent)", timeout=5000)
        check(tag + 'same version: "you have the latest"', 'You have the latest version' in p.evaluate(STATUS), p.evaluate(STATUS))
        check(tag + 'same version: nothing pending', p.evaluate("() => %s.newVersion()" % H) is None)
        server['mode'] = 'offline'
        p.click('#checkUpd')
        p.wait_for_function("() => /Couldn/.test(document.getElementById('updStatus').textContent)", timeout=5000)
        check(tag + 'offline: says it couldn\'t check', 'Couldn’t check' in p.evaluate(STATUS), p.evaluate(STATUS))

        # ---- Reload button reloads the page ----
        server['mode'] = 'same'
        p.evaluate("() => { window.__marker = 1; }")
        with p.expect_navigation():
            p.click('#reloadApp')
        p.clock.run_for(500)
        check(tag + 'Reload reloads the app', p.evaluate("() => window.__marker") is None)
        check(tag + 'no page errors', not errs, errs)
        p.close()

        # ---- switched on in the day: auto-check, note in the day picture colour ----
        server.update(mode='newer', checks=0)
        p = fresh(b, vp, DAY, {'updateNotice': True})
        settle(p)
        check(tag + 'switched on: checks soon after start', server['checks'] == 1, server['checks'])
        note = p.evaluate(NOTE)
        check(tag + 'note shows in the day', note[0] == 'block' and note[1] == 'New version available', note)
        check(tag + 'note in the day picture colour, subtle', note[2] == 'rgb(122, 167, 255)' and 0.3 < note[3] <= 0.6, note)
        p.clock.fast_forward(3600 * 1000)
        settle(p)
        check(tag + 'no new check within the hour', server['checks'] == 1, server['checks'])
        p.clock.fast_forward(3 * 3600 * 1000)
        settle(p)
        check(tag + 'checks again after a few hours', server['checks'] == 2, server['checks'])
        p.screenshot(path='%s/updates-day-%dx%d.png' % (SHOTS, vp[0], vp[1]))
        p.evaluate("() => %s.setS({updateNotice: true, dayMode: 'dark'})" % H)
        settle(p)
        check(tag + 'day mode "dark screen": no note', p.evaluate(NOTE)[0] == 'none')
        p.evaluate("() => %s.setS({updateNotice: false})" % H)
        settle(p)
        check(tag + 'switched off again: note gone', p.evaluate(NOTE)[0] == 'none')
        p.close()

        # ---- green phase: note in green ----
        server.update(mode='newer', checks=0)
        p = fresh(b, vp, GREEN, {'updateNotice': True})
        settle(p)
        note = p.evaluate(NOTE)
        check(tag + 'green phase: note in the green face colour', note[0] == 'block' and note[2] == 'rgb(52, 199, 89)', note)
        p.close()

        # ---- night: no checks, no note ----
        server.update(mode='newer', checks=0)
        p = fresh(b, vp, NIGHT, {'updateNotice': True})
        p.evaluate("() => %s.checkUpdate()" % H)      # even when a new version is already known...
        settle(p)
        server['checks'] = 0
        check(tag + 'night: no note', p.evaluate(NOTE)[0] == 'none', p.evaluate(NOTE))
        p.clock.fast_forward(4 * 3600 * 1000)        # 22:00 -> 02:00
        settle(p)
        check(tag + 'night: never checks by itself', server['checks'] == 0, server['checks'])
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
