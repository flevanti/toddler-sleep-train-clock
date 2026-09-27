"""Web app manifest (embedded in index.html): installable, full screen, proper icons — checked through Chromium's DevTools protocol."""
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
html = open(ROOT + '/index.html', encoding='utf-8').read()
check('manifest linked from the page, embedded (no extra file to deploy)', '<link rel="manifest" href="data:application/manifest+json,' in html)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context()
    p = ctx.new_page()
    p.goto(URL)
    # the app registers its offline copy only on https; register it here so Chromium can judge installability
    p.evaluate("() => navigator.serviceWorker.register('sw.js').then(function () { return navigator.serviceWorker.ready; })")
    p.reload()
    p.wait_for_timeout(1500)
    cdp = ctx.new_cdp_session(p)
    am = cdp.send('Page.getAppManifest')
    check('manifest parses without errors', am.get('errors') == [], am.get('errors'))
    m = __import__('json').loads(am.get('data') or '{}')   # the manifest as the browser fetched it
    check('named Sleep Clock', m.get('name') == 'Sleep Clock' and m.get('short_name') == 'Sleep Clock', (m.get('name'), m.get('short_name')))
    disp = m.get('display')
    check('opens full screen', disp in ('fullscreen', 'kFullscreen') or 'fullscreen' in str(disp).lower(), disp)
    errs = cdp.send('Page.getInstallabilityErrors')['installabilityErrors']
    check('Chromium says the page is installable', errs == [], [e['errorId'] for e in errs])

    icons = __import__('json').loads(am['data'])['icons']
    sizes = p.evaluate("""(icons) => Promise.all(icons.map(function (ic) { return new Promise(function (ok) {
        var i = new Image(); i.onload = function () { ok([ic.sizes, ic.purpose || 'any', i.naturalWidth, i.naturalHeight]); }; i.onerror = function () { ok([ic.sizes, 'broken', 0, 0]); }; i.src = ic.src; }); }))""", icons)
    check('icons are real 512 px PNGs (one normal, one maskable for Android shapes)',
          sorted(s[1] for s in sizes) == ['any', 'maskable'] and all(s[0] == '512x512' and s[2] == 512 and s[3] == 512 for s in sizes), sizes)
    b.close()
srv.shutdown()
sys.exit(check.finish())
