import sys, json, base64, threading, http.server, functools
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8767), functools.partial(Q, directory=sys.argv[1]))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fails = []
def check(n, c, i=''):
    print(('PASS ' if c else 'FAIL ') + n, i)
    if not c: fails.append(n)
with sync_playwright() as pw:
    b = pw.chromium.launch(); p = b.new_page(viewport={'width':1024,'height':768})
    p.goto('http://127.0.0.1:8767/index.html')
    check('title starts with the name (the rest is for search engines)', p.title().startswith('Sleep Clock'), p.title())
    check('description for search engines', 'OK to wake' in (p.get_attribute('meta[name=description]', 'content') or ''))
    check('structured data is valid JSON', __import__('json').loads(p.inner_text('script[type="application/ld+json"]'))['name'] == 'Sleep Clock')
    check('app title meta', p.get_attribute('meta[name=apple-mobile-web-app-title]', 'content') == 'Sleep Clock')
    # simulate an iPad set up before the rename
    p.evaluate("""() => { localStorage.clear();
      localStorage.setItem('okclock.settings.v1', JSON.stringify({dayColor:'teal', nightColor:'amber', days:[{bed:'20:15',wake:'06:45',tone:'birds'},{},{},{},{},{},{}]}));
      localStorage.setItem('okclock.fired', 'w123'); }""")
    p.reload(); p.wait_for_timeout(300)
    S = p.evaluate("() => window.__toddlerSleepTrainClock.S()")
    check('settings migrated', S['dayColor'] == 'teal' and S['nightColor'] == 'amber' and S['days'][0]['bed'] == '20:15')
    ls = p.evaluate("() => { var o = {}; for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); o[k] = localStorage.getItem(k); } return o; }")
    check('old keys removed, new keys present', set(ls) - {'toddler-sleep-train-clock.loads'} == {'toddler-sleep-train-clock.settings.v1', 'toddler-sleep-train-clock.fired'} and ls['toddler-sleep-train-clock.fired'] == 'w123', list(ls))
    # new key wins if both exist
    p.evaluate("""() => { localStorage.setItem('okclock.settings.v1', JSON.stringify({dayColor:'pink'})); }""")
    p.reload(); p.wait_for_timeout(300)
    check('new key not overwritten by stale old key', p.evaluate("() => window.__toddlerSleepTrainClock.S().dayColor") == 'teal')
    # settings UI: header + export prefix + import old/new/bad codes
    p.mouse.move(994, 30); p.mouse.down(); p.wait_for_timeout(2700); p.mouse.up(); p.wait_for_timeout(200)
    check('settings header', p.inner_text('#settings .topbar h1') == 'Sleep Clock')
    p.click('#expBtn'); code = p.input_value('#codeBox')
    check('export uses new prefix', code.startswith('toddler-sleep-train-clock.v1:'), code[:40])
    p.evaluate("() => window.__toddlerSleepTrainClock.setS({})")
    p.fill('#codeBox', code); p.click('#impBtn')
    check('import new code', p.evaluate("() => window.__toddlerSleepTrainClock.S().dayColor") == 'teal')
    old = 'OKC1:' + base64.b64encode(json.dumps({'dayColor': 'yellow'}).encode()).decode()
    p.fill('#codeBox', old); p.click('#impBtn')
    check('import old OKC1 code', p.evaluate("() => window.__toddlerSleepTrainClock.S().dayColor") == 'yellow')
    p.fill('#codeBox', 'garbage'); p.click('#impBtn'); p.wait_for_timeout(100)
    check('reject bad code', 'Sleep Clock code' in p.inner_text('#toast'), p.inner_text('#toast'))
    b.close()
srv.shutdown()
print('FAILURES:', fails or 'none'); sys.exit(1 if fails else 0)
