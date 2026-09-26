import sys, datetime, json, threading, http.server, functools, os
from playwright.sync_api import sync_playwright
ROOT = sys.argv[1]; SHOTS = sys.argv[2]
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
H = functools.partial(Q, directory=ROOT)
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8765), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
fails = []
def check(name, cond, info=''):
    print(('PASS ' if cond else 'FAIL ') + name, info)
    if not cond: fails.append(name)
def state(p):
    return p.evaluate("""() => {
      var c = document.getElementById('clock').style.backgroundColor;
      var circ = document.querySelector('#face svg circle[r="92"]');
      return { bg: c, fill: circ ? circ.getAttribute('fill') : null,
        faceOp: document.getElementById('face').style.opacity, faceDisp: document.getElementById('face').style.display,
        timeColor: document.getElementById('time').style.color, timeOp: document.getElementById('time').style.opacity,
        mode: window.__toddlerSleepTrainClock.computeState(new Date()).mode };
    }""")
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in [(1024, 768), (768, 1024)]:
        ctx = b.new_context(viewport={'width': vp[0], 'height': vp[1]})
        p = ctx.new_page()
        # Wed 2026-09-23 12:00 -> day
        p.clock.install(time=datetime.datetime(2026, 9, 23, 12, 0, 0))
        p.goto('http://127.0.0.1:8765/index.html')
        p.evaluate("() => localStorage.clear()"); p.reload(); p.wait_for_timeout(300)
        # CSS has 2s bg transition; skip via fast-forward
        p.clock.run_for(3000)
        s = state(p); tag = '%dx%d ' % vp
        check(tag + 'default day blue', s['mode'] == 'day' and s['fill'] == '#7aa7ff' and s['bg'] == 'rgb(11, 18, 32)', s)
        p.evaluate("() => window.__toddlerSleepTrainClock.setS({dayColor:'pink', dayDim:50})"); p.clock.run_for(3000)
        s = state(p)
        check(tag + 'day pink 50%', s['fill'] == '#ff8fb8' and s['bg'] == 'rgb(28, 11, 18)' and s['faceOp'] == '0.5' and s['timeOp'] == '0.5', s)
        p.screenshot(path=os.path.join(SHOTS, 'day_pink_%dx%d.png' % vp))
        p.evaluate("() => window.__toddlerSleepTrainClock.setS({dayColor:'teal', dayMode:'clock', dayDim:70})"); p.clock.run_for(3000)
        s = state(p)
        check(tag + 'clock-only teal', s['faceDisp'] == 'none' and s['timeColor'] == 'rgb(79, 209, 197)' and s['timeOp'] == '0.7', s)
        # night 22:00
        p.clock.set_system_time(datetime.datetime(2026, 9, 23, 22, 0, 0))
        p.evaluate("() => window.__toddlerSleepTrainClock.setS({nightColor:'purple', nightDim:40})"); p.clock.run_for(3000)
        s = state(p)
        check(tag + 'night purple 40%', s['mode'] == 'sleep' and s['fill'] == '#a66bff' and s['faceOp'] == '0.4', s)
        p.screenshot(path=os.path.join(SHOTS, 'night_purple_%dx%d.png' % vp))
        # old / bad saved settings
        p.evaluate("() => localStorage.setItem('toddler-sleep-train-clock.settings.v1', JSON.stringify({nightColor:'foo', dayColor:'nope', dayDim:'x', nightDim:500}))")
        p.reload(); p.wait_for_timeout(300)
        S = p.evaluate("() => window.__toddlerSleepTrainClock.S()")
        check(tag + 'bad saved values fall back', S['nightColor'] == 'red' and S['dayColor'] == 'blue' and S['dayDim'] == 100 and S['nightDim'] == 100, {k: S[k] for k in ['nightColor','dayColor','dayDim','nightDim']})
        # settings UI: open via long-press on hot corner
        p.clock.set_system_time(datetime.datetime(2026, 9, 23, 12, 0, 0))
        p.evaluate("() => window.__toddlerSleepTrainClock.setS({})")
        p.mouse.move(vp[0]-30, 30); p.mouse.down(); p.clock.run_for(2700); p.mouse.up()
        p.wait_for_timeout(200)
        check(tag + 'settings open', p.is_visible('#settings'))
        p.click('[data-sw="dayColor"][data-c="green"]')
        p.click('[data-sw="nightColor"][data-c="amber"]')
        p.fill('#dayDim', '60'); p.dispatch_event('#dayDim', 'input'); p.dispatch_event('#dayDim', 'change')
        on = p.evaluate("() => [].map.call(document.querySelectorAll('.swc.on'), function(b){return b.getAttribute('data-c')})")
        check(tag + 'swatch selection shown', on == ['amber', 'green'], on)
        check(tag + 'dayDim label', p.inner_text('#dayDimV') == '60%')
        sec = p.locator('.sec', has_text='bedtime → wake').first; sec.scroll_into_view_if_needed()
        sec.screenshot(path=os.path.join(SHOTS, 'settings_display_%dx%d.png' % vp))
        # no horizontal overflow of the display section
        ov = p.evaluate("() => { var w = document.getElementById('swrap'); return w.scrollWidth <= w.clientWidth + 1; }")
        check(tag + 'no horizontal overflow', ov)
        p.click('#done'); p.clock.run_for(3000)
        s = state(p)
        check(tag + 'UI choices applied', s['fill'] == '#5ad17a' and s['faceOp'] == '0.6', s)
        # persistence + export/import
        p.reload(); p.wait_for_timeout(300)
        S = p.evaluate("() => window.__toddlerSleepTrainClock.S()")
        check(tag + 'persisted', S['dayColor'] == 'green' and S['nightColor'] == 'amber' and S['dayDim'] == 60)
        code = 'OKC1:' + __import__('base64').b64encode(json.dumps(S).encode()).decode()
        p.evaluate("() => window.__toddlerSleepTrainClock.setS({})")
        p.mouse.move(vp[0]-30, 30); p.mouse.down(); p.clock.run_for(2700); p.mouse.up(); p.wait_for_timeout(200)
        p.fill('#codeBox', code); p.click('#impBtn')
        S = p.evaluate("() => window.__toddlerSleepTrainClock.S()")
        check(tag + 'import restores colours', S['dayColor'] == 'green' and S['nightColor'] == 'amber' and S['dayDim'] == 60)
        errs = []
        ctx.close()
    b.close()
srv.shutdown()
print('FAILURES:', fails if fails else 'none')
sys.exit(1 if fails else 0)
