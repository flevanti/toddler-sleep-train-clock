import sys, os, datetime, threading, http.server, functools
from playwright.sync_api import sync_playwright
ROOT, SHOTS = sys.argv[1], sys.argv[2]
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8769), functools.partial(Q, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fails = []
def check(n, c, i=''):
    print(('PASS ' if c else 'FAIL ') + n, i)
    if not c: fails.append(n)
H = 'window.__toddlerSleepTrainClock'
SNAP = """() => [].map.call(document.querySelectorAll('.clk.snap'), function (e) { return { op: e.style.opacity, tr: e.style.transition, ids: e.querySelectorAll('[id]').length - e.querySelectorAll('radialGradient[id]').length, own: e.id, grad: (e.querySelector('radialGradient') || {}).id, fill: (e.querySelector('circle[fill^=url]') || {getAttribute: function(){return null}}).getAttribute('fill') }; })"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in [(1024, 768), (768, 1024)]:
        tag = '%dx%d ' % vp
        ctx = b.new_context(viewport={'width': vp[0], 'height': vp[1]}); p = ctx.new_page()
        errs = []; p.on('pageerror', lambda e: errs.append(str(e)))
        p.clock.install(time=datetime.datetime(2026, 9, 23, 6, 59, 55))  # Wed, wake 07:00
        p.goto('http://127.0.0.1:8769/index.html')
        p.evaluate("() => localStorage.clear()"); p.reload(); p.clock.run_for(300)
        check(tag + 'default fade 3 s', p.evaluate("() => %s.S().fadeSec" % H) == 3)
        check(tag + 'no fade on first paint', p.evaluate(SNAP) == [])
        p.clock.run_for(5000)  # cross 07:00 -> green
        sn = p.evaluate(SNAP)
        check(tag + 'snapshot on sleep->wake', len(sn) == 1 and sn[0]['op'] == '0' and '3000ms' in sn[0]['tr'], sn)
        check(tag + 'snapshot has no duplicate ids', sn and sn[0]['ids'] == 0 and sn[0]['own'] == '', sn)
        check(tag + 'snapshot gradient renamed', sn and sn[0]['grad'].startswith('shMainSnap') and sn[0]['fill'] == 'url(#%s)' % sn[0]['grad'], sn)
        check(tag + 'real clock already green underneath', p.evaluate("() => document.querySelector('#face svg circle[r=\"92\"]').getAttribute('fill')") == '#34c759')
        check(tag + 'snapshot shows old night face', p.evaluate("() => document.querySelector('.clk.snap svg circle[r=\"92\"]').getAttribute('fill')") == '#ff3b1f')
        p.screenshot(path=os.path.join(SHOTS, 'fade_mid_%dx%d.png' % vp))
        p.clock.run_for(3300)
        check(tag + 'snapshot removed after fade', p.evaluate(SNAP) == [])
        # hard change when Off
        p.evaluate("() => %s.setS({fadeSec: 0, greenMin: 15})" % H)  # green ends 07:15 -> day
        p.clock.set_system_time(datetime.datetime(2026, 9, 23, 7, 14, 58)); p.clock.run_for(4000)
        check(tag + 'Off = hard change', p.evaluate("() => %s.computeState(new Date()).mode" % H) == 'day' and p.evaluate(SNAP) == [])
        # bad saved value
        p.evaluate("() => localStorage.setItem('toddler-sleep-train-clock.settings.v1', JSON.stringify({fadeSec: 7}))"); p.reload(); p.clock.run_for(300)
        check(tag + 'invalid fadeSec -> 3', p.evaluate("() => %s.S().fadeSec" % H) == 3)
        # mini preview fades on tab change; settings control saves
        p.mouse.move(vp[0]-30, 30); p.mouse.down(); p.clock.run_for(2700); p.mouse.up(); p.clock.run_for(200)
        check(tag + 'no mini fade on opening settings', p.evaluate("() => document.querySelectorAll('.mini.snap').length") == 0)
        p.select_option('#fadeSec', '5')
        check(tag + 'fade setting saved', p.evaluate("() => %s.S().fadeSec" % H) == 5)
        p.click('#pvtabs [data-pv="sleep"]')
        ms = p.evaluate("() => [].map.call(document.querySelectorAll('.mini.snap'), function (e) { return [e.style.position, e.style.transition]; })")
        check(tag + 'mini tab change fades (5 s, overlaid)', len(ms) == 1 and ms[0][0] == 'absolute' and '5000ms' in ms[0][1], ms)
        lay = p.evaluate("() => { var a = document.getElementById('mini').getBoundingClientRect(), b = document.querySelector('.mini.snap').getBoundingClientRect(); return [a.left, a.top, a.width, a.height, b.left, b.top, b.width, b.height]; }")
        check(tag + 'mini snapshot exactly over preview', lay[:4] == lay[4:], lay)
        p.clock.run_for(5200)
        check(tag + 'mini snapshot removed', p.evaluate("() => document.querySelectorAll('.mini.snap').length") == 0)
        # simulation caps fade at 500 ms
        p.click('#simBtn')
        caps = set()
        for _ in range(200):
            p.clock.run_for(100)
            for sn in p.evaluate(SNAP): caps.add(sn['tr'])
        check(tag + 'sim fades capped at 500 ms', caps and all('500ms' in c for c in caps), caps)
        check(tag + 'no page errors', not errs, errs)
        ctx.close()
    b.close()
srv.shutdown()
print('FAILURES:', fails or 'none'); sys.exit(1 if fails else 0)
