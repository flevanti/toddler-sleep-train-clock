import sys, threading, http.server, functools
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8766), functools.partial(Q, directory=sys.argv[1]))
threading.Thread(target=srv.serve_forever, daemon=True).start()
ok = True
with sync_playwright() as pw:
    b = pw.chromium.launch(); ctx = b.new_context(viewport={'width':1024,'height':768}); p = ctx.new_page()
    reqs, bad = [], []
    p.on('request', lambda r: reqs.append(r.url))
    p.on('requestfailed', lambda r: bad.append(r.url))
    errs = []; p.on('pageerror', lambda e: errs.append(str(e)))
    p.goto('http://127.0.0.1:8766/index.html')
    p.evaluate("() => navigator.serviceWorker.register('sw.js').then(function(){ return navigator.serviceWorker.ready; })")
    p.reload(); p.wait_for_timeout(500)
    print('requests:', sorted(set(u.split('8766/')[1] for u in reqs)))
    print('failed:', bad, 'pageerrors:', errs); ok &= not bad and not errs
    icon = p.evaluate("() => { var l=document.querySelector('link[rel=apple-touch-icon]'); var i=new Image(); return new Promise(function(r){ i.onload=function(){r([i.width,i.height])}; i.onerror=function(){r('err')}; i.src=l.href; }); }")
    print('icon decodes:', icon); ok &= icon == [180,180]
    srv.shutdown(); srv.server_close()   # server gone = offline
    ctx.set_offline(True)
    p.reload()
    fine = p.evaluate("() => !!(window.__toddlerSleepTrainClock && document.querySelector('#face svg'))")
    print('offline reload renders clock:', fine); ok &= fine
    b.close()
print('RESULT', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
