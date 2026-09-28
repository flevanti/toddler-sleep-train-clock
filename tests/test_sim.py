import sys, os, json, datetime, threading, http.server, functools
from playwright.sync_api import sync_playwright
ROOT, SHOTS = sys.argv[1], sys.argv[2]
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8768), functools.partial(Q, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fails = []
def check(n, c, i=''):
    print(('PASS ' if c else 'FAIL ') + n, i)
    if not c: fails.append(n)
H = 'window.__toddlerSleepTrainClock'
def open_settings(p, vp):
    p.mouse.move(vp[0]-30, 30); p.mouse.down(); p.clock.run_for(2700); p.mouse.up(); p.clock.run_for(200)
def active_tab(p):
    return p.evaluate("() => document.querySelector('#pvtabs .b:not(.g)').getAttribute('data-pv')")
def mini_fill(p):
    return p.evaluate("() => document.querySelector('#miniFace svg circle[r=\"92\"]').getAttribute('fill')")
with sync_playwright() as pw:
    b = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    for vp in [(1024, 768), (768, 1024)]:
        tag = '%dx%d ' % vp
        ctx = b.new_context(viewport={'width': vp[0], 'height': vp[1]}); p = ctx.new_page()
        errs = []; p.on('pageerror', lambda e: errs.append(str(e)))
        p.clock.install(time=datetime.datetime(2026, 9, 23, 12, 0, 0))  # Wednesday noon
        p.goto('http://127.0.0.1:8768/index.html')
        p.evaluate("() => localStorage.clear()"); p.reload(); p.clock.run_for(500)
        days = [{'bed': '19:00', 'wake': '07:00', 'tone': 'chime'} for _ in range(7)]
        p.evaluate("(d) => %s.setS({days: d, soonMin: 15})" % H, days)
        # ---- live preview ----
        open_settings(p, vp)
        check(tag + 'mini preview visible, starts on current phase', p.is_visible('#mini') and active_tab(p) == 'day', active_tab(p))
        check(tag + 'gradient ids unique', p.evaluate("() => document.querySelectorAll('#shMain').length === 1 && document.querySelectorAll('#shMini').length === 1"))
        p.click('[data-sw="nightColor"][data-c="purple"]')
        check(tag + 'night swatch -> Night tab + colour', active_tab(p) == 'sleep' and mini_fill(p) == '#a66bff', (active_tab(p), mini_fill(p)))
        p.fill('#dayDim', '40'); p.dispatch_event('#dayDim', 'input')
        op = p.evaluate("() => document.getElementById('miniFace').style.opacity")
        check(tag + 'day brightness -> Day tab + dim', active_tab(p) == 'day' and op == '0.4', (active_tab(p), op))
        p.select_option('#soonMin', '20')
        check(tag + 'amber setting -> Amber tab', active_tab(p) == 'soon' and 'Almost time, 20 min' in p.inner_text('#pvnote'), p.inner_text('#pvnote'))
        p.click('#pvtabs [data-pv="wake"]')
        check(tag + 'Green tab', mini_fill(p) == '#34c759' and '07:00' in p.inner_text('#pvnote'), p.inner_text('#pvnote'))
        p.select_option('#dayMode', 'clock')
        check(tag + 'day mode clock -> face hidden in mini', p.evaluate("() => document.getElementById('miniFace').style.display") == 'none')
        p.select_option('#dayMode', 'face')
        p.screenshot(path=os.path.join(SHOTS, 'settings_preview_%dx%d.png' % vp))
        ov = p.evaluate("() => { var h = document.querySelector('#shead .hwrap'); return h.scrollWidth <= h.clientWidth + 1; }")
        check(tag + 'header no overflow', ov)
        # ---- simulation ----
        saved_before = p.evaluate("() => localStorage.getItem('toddler-sleep-train-clock.settings.v1')")
        p.evaluate("() => { var t = Date.now(); %s.S().nap = null; }" % H)
        p.evaluate("() => { document.getElementById('sbody').scrollTop = 400; }")
        p.click('#simBtn'); p.clock.run_for(200)
        check(tag + 'sim started', p.is_visible('#simbar') and not p.is_visible('#settings') and p.evaluate("() => document.body.className") == 'sim')
        t0 = p.evaluate("() => { var d = new Date(%s.sim().t0); return [d.getDay(), d.getHours(), d.getMinutes()]; }" % H)
        check(tag + 'sim starts Wed 06:25 (amber 20 min + 15 before wake)', t0 == [3, 6, 25], t0)
        segs = p.evaluate("() => document.querySelectorAll('#simsegs .seg').length")
        check(tag + 'timeline has phase segments', segs == 5, segs)  # sleep, soon, wake, day, sleep
        p.screenshot(path=os.path.join(SHOTS, 'sim_start_%dx%d.png' % vp))
        # play the whole default 60 s cycle, sampling every 100 ms
        seq, alarm_seen_in, fired_marker = [], None, False
        for _ in range(620):
            p.clock.run_for(100)
            m = p.evaluate("() => { var s = %s.sim(); return s ? s.mode : null; }" % H)
            if m and (not seq or seq[-1] != m): seq.append(m)
            if alarm_seen_in is None and p.evaluate("() => %s.alarmPlaying()" % H): alarm_seen_in = m
            if m == 'day' and not os.path.exists(os.path.join(SHOTS, 'sim_day_%dx%d.png' % vp)):
                p.screenshot(path=os.path.join(SHOTS, 'sim_day_%dx%d.png' % vp))
        check(tag + 'phases in order', seq == ['sleep', 'soon', 'wake', 'day', 'sleep'], seq)
        check(tag + 'wake sound fired at green', alarm_seen_in == 'wake', alarm_seen_in)
        s_ = p.evaluate("() => %s.sim()" % H)
        check(tag + 'finished + paused', s_ and s_['done'] and not s_['playing'], s_ and {k: s_[k] for k in ['done','playing']})
        check(tag + 'no fired marker written', p.evaluate("() => localStorage.getItem('toddler-sleep-train-clock.fired')") is None and p.evaluate("() => %s.firedKey()" % H) == '')
        check(tag + 'settings unchanged by sim', p.evaluate("() => localStorage.getItem('toddler-sleep-train-clock.settings.v1')") == saved_before)
        p.clock.run_for(5500)
        check(tag + 'auto-exit after finish', p.evaluate("() => %s.sim()" % H) is None and not p.is_visible('#simbar') and p.evaluate("() => document.body.className") == '')
        check(tag + 'finish returns to settings (no PIN)', p.is_visible('#settings') and not p.is_visible('#pinpad'))
        sc = p.evaluate("() => document.getElementById('sbody').scrollTop")
        check(tag + 'settings scroll position kept', sc == 400, sc)
        rt = p.evaluate("() => { var d = new Date(); return [document.getElementById('time').textContent, ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2)]; }")
        check(tag + 'back to real time', rt[0] == rt[1], rt)
        # ---- nap untouched, jump, mute, speed, cap ----
        # Exit button -> settings
        p.click('#simBtn'); p.clock.run_for(2000); p.click('#simExit'); p.clock.run_for(200)
        check(tag + 'Exit button returns to settings', p.evaluate("() => %s.sim()" % H) is None and p.is_visible('#settings') and not p.is_visible('#simbar'))
        p.evaluate("() => { var t = Date.now(); %s.S().nap = {start: t, end: t + 45*60000}; }" % H)
        p.click('#simBtn'); p.clock.run_for(200)
        check(tag + 'sim ignores real nap', p.evaluate("() => %s.sim().mode" % H) == 'sleep' and p.evaluate("() => { var d = new Date(%s.sim().t0); return [d.getDay(), d.getHours(), d.getMinutes()]; }" % H) == [3, 6, 25])
        box = p.locator('#simline').bounding_box()
        p.mouse.click(box['x'] + box['width'] * 0.5, box['y'] + box['height'] / 2); p.clock.run_for(300)
        txt = p.inner_text('#simNow'); s_ = p.evaluate("() => %s.sim()" % H)
        check(tag + 'timeline jump to middle pauses on day', '18:25' in txt and 'Day' in txt and not s_['playing'], txt)
        p.click('#simMute'); check(tag + 'mute', p.evaluate("() => %s.sim().muted" % H) and p.inner_text('#simMute') == '🔇')
        p.fill('#simSpeed', '30'); p.dispatch_event('#simSpeed', 'input')
        check(tag + 'speed label', p.inner_text('#simSpeedV') == '30 s')
        p.select_option('#simDay', '6'); p.clock.run_for(200)  # Saturday restarts, playing
        check(tag + 'day picker restarts on Sat', p.evaluate("() => { var d = new Date(%s.sim().t0); return [d.getDay(), d.getHours(), d.getMinutes()]; }" % H) == [6, 6, 25] and p.evaluate("() => %s.sim().playing" % H), p.inner_text('#simNow'))
        p.clock.run_for(30500)
        check(tag + '30 s speed finishes in ~30 s', p.evaluate("() => %s.sim().done" % H))
        check(tag + 'muted: no alarm', not p.evaluate("() => %s.alarmPlaying()" % H))
        p.click('#simPlay'); p.clock.run_for(200)  # ↺ restart
        p.click('#simPlay')  # pause
        p.clock.run_for(10 * 60000 + 1000)
        check(tag + '10-min safety cap exits sim to settings', p.evaluate("() => %s.sim()" % H) is None and p.is_visible('#settings'))
        check(tag + 'nap still there after sim', p.evaluate("() => !!%s.S().nap" % H))
        sb = p.evaluate("() => { var e = document.getElementById('simbar'); e.style.display='block'; var r = e.scrollWidth <= e.clientWidth + 1; e.style.display='none'; return r; }")
        check(tag + 'sim bar no overflow', sb)
        check(tag + 'no page errors', not errs, errs)
        ctx.close()
    b.close()
srv.shutdown()
print('FAILURES:', fails or 'none'); sys.exit(1 if fails else 0)
