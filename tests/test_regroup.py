import sys, os, datetime, threading, http.server, functools
from playwright.sync_api import sync_playwright
ROOT, SHOTS = sys.argv[1], sys.argv[2]
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8770), functools.partial(Q, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fails = []
def check(n, c, i=''):
    print(('PASS ' if c else 'FAIL ') + n, i)
    if not c: fails.append(n)
H = 'window.__toddlerSleepTrainClock'
EXPECT = [
  ('General', ['volume', 'testTone', 'showTime', 'h24', 'showLabel', 'fadeSec', 'audioStatus']),
  ('Weekly schedule', ['copyWk', 'copyWe']),
  ('Night', ['nightDim', 'showTimeNight', 'noise', 'noiseVol']),
  ('Almost time', ['soonMin']),
  ('Wake', ['greenMin', 'alarmLen', 'fadeIn']),
  ('Day', ['dayMode', 'dayDim']),
  ('Nap', ['napSound']),
  ('Device & safety', ['pinSet', 'expBtn', 'impBtn', 'resetBtn', 'codeBox']),
  ('Device setup checklist', []),
  ('About & feedback', []),
]
active = "() => document.querySelector('#pvtabs .b:not(.g)').getAttribute('data-pv')"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in [(1024, 768), (768, 1024)]:
        tag = '%dx%d ' % vp
        ctx = b.new_context(viewport={'width': vp[0], 'height': vp[1]}); p = ctx.new_page()
        errs = []; p.on('pageerror', lambda e: errs.append(str(e)))
        p.clock.install(time=datetime.datetime(2026, 9, 23, 12, 0, 0))
        p.goto('http://127.0.0.1:8770/index.html'); p.evaluate("() => localStorage.clear()"); p.reload(); p.clock.run_for(300)
        p.mouse.move(vp[0]-30, 30); p.mouse.down(); p.clock.run_for(2700); p.mouse.up(); p.clock.run_for(200)
        secs = p.evaluate("""() => [].map.call(document.querySelectorAll('#swrap .sec'), function (s) {
            var h = s.querySelector('h2'), c = h.cloneNode(true), sm = c.querySelector('small'); if (sm) c.removeChild(sm);
            return { title: c.textContent.trim(), ids: [].map.call(s.querySelectorAll('[id]'), function (e) { return e.id; }), pv: s.getAttribute('data-pv') }; })""")
        check(tag + 'section order', [x['title'] for x in secs] == [e[0] for e in EXPECT], [x['title'] for x in secs])
        for (title, ids), sec in zip(EXPECT, secs):
            missing = [i for i in ids if i not in sec['ids']]
            check(tag + 'controls in ' + title, not missing, missing)
        check(tag + 'phase sections tagged', [x['pv'] for x in secs[2:6]] == ['sleep', 'soon', 'wake', 'day'])
        check(tag + 'night swatches in Night', p.evaluate("() => !!document.querySelector('.sec[data-pv=sleep] [data-sw=nightColor]')"))
        check(tag + 'day swatches in Day', p.evaluate("() => !!document.querySelector('.sec[data-pv=day] [data-sw=dayColor]')"))
        # preview follows the section touched
        p.select_option('#alarmLen', '20'); check(tag + 'wake-section control -> Green tab', p.evaluate(active) == 'wake')
        p.click('.sec[data-pv=sleep] h2'); check(tag + 'tap Night heading -> Night tab', p.evaluate(active) == 'sleep')
        p.click('.sec[data-pv=day] h2'); check(tag + 'tap Day heading -> Day tab', p.evaluate(active) == 'day')
        p.dispatch_event('#noise', 'change')
        check(tag + 'noise toggle -> Night tab', p.evaluate(active) == 'sleep')
        # colour dots follow swatches
        p.click('[data-sw="nightColor"][data-c="orange"]'); p.click('[data-sw="dayColor"][data-c="teal"]')
        dots = p.evaluate("() => [getComputedStyle(document.getElementById('dotNight')).backgroundColor, getComputedStyle(document.getElementById('dotDay')).backgroundColor]")
        check(tag + 'section dots follow colours', dots == ['rgb(255, 122, 26)', 'rgb(79, 209, 197)'], dots)
        # settings still work after move
        p.select_option('#greenMin', '30'); p.select_option('#soonMin', '15'); p.select_option('#dayMode', 'clock')
        S = p.evaluate("() => %s.S()" % H)
        check(tag + 'moved controls still save', S['greenMin'] == 30 and S['soonMin'] == 15 and S['dayMode'] == 'clock' and S['alarmLen'] == 20)
        ov = p.evaluate("() => { var w = document.getElementById('swrap'); return w.scrollWidth <= w.clientWidth + 1; }")
        check(tag + 'no horizontal overflow', ov)
        for i, name in enumerate(['night', 'day']):
            p.locator('.sec[data-pv=%s]' % ('sleep' if name == 'night' else 'day')).scroll_into_view_if_needed()
            p.screenshot(path=os.path.join(SHOTS, 'regroup_%s_%dx%d.png' % (name, vp[0], vp[1])))
        p.evaluate("() => document.getElementById('sbody').scrollTop = 0"); p.screenshot(path=os.path.join(SHOTS, 'regroup_top_%dx%d.png' % vp))
        check(tag + 'no page errors', not errs, errs)
        ctx.close()
    b.close()
srv.shutdown()
print('FAILURES:', fails or 'none'); sys.exit(1 if fails else 0)
