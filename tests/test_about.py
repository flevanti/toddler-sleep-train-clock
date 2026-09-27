"""Settings header info (version, app updated date, settings saved time) and the GitHub links / issue forms."""
import datetime
import os
import sys
import urllib.parse

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
REPO = 'https://github.com/flevanti/toddler-sleep-train-clock'
KEY = 'toddler-sleep-train-clock.settings.v1'
check = Checks()
srv, URL = serve(ROOT)

# the local test server sends Last-Modified = index.html's modification time, like GitHub Pages does
mtime = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, 'index.html')), datetime.timezone.utc).astimezone()
updated = '%d %s %d' % (mtime.day, mtime.strftime('%b'), mtime.year)

for name, fields in [('feature_request.yml', ['id: idea', 'id: version', 'id: device']), ('bug_report.yml', ['id: what', 'id: version', 'id: device'])]:
    path = os.path.join(ROOT, '.github', 'ISSUE_TEMPLATE', name)
    text = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
    check('issue form %s has its fields' % name, text.startswith('name:') and all(f in text for f in fields), path)

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
        version = p.evaluate("() => document.documentElement.innerHTML.match(/var VERSION = '([^']+)'/)[1]")
        open_settings(p, vp)

        info = p.inner_text('#appinfo')
        check(tag + 'header shows the version', ('v' + version) in info, info)
        check(tag + 'header shows when the app was published (server date)', ('app updated ' + updated) in info, info)
        check(tag + 'fresh device: settings not saved yet', 'settings not saved yet' in info, info)
        box = p.evaluate("() => [document.getElementById('appinfo').getBoundingClientRect().bottom, document.getElementById('mini').getBoundingClientRect().bottom, document.getElementById('shead').getBoundingClientRect().bottom]")
        check(tag + 'info line fits in the header', box[0] < box[2] and box[1] <= box[2], box)

        p.clock.run_for(60000)  # 12:01
        p.select_option('#greenMin', '30')
        info = p.inner_text('#appinfo')
        check(tag + 'a change is saved with its time', 'settings saved today 12:01' in info, info)
        saved = p.evaluate("(k) => JSON.parse(localStorage.getItem(k)).savedAt", KEY)
        check(tag + 'save time stored with the settings', abs(saved - p.evaluate("() => Date.now()")) < 5000, saved)
        p.click('#done')
        p.clock.fast_forward(3600000)  # an hour later (jumped, not ticked through): closing and reopening settings is not a change
        open_settings(p, vp)
        check(tag + 'opening/closing settings does not count as a change', 'settings saved today 12:01' in p.inner_text('#appinfo'), p.inner_text('#appinfo'))
        p.click('#expBtn')
        code = p.input_value('#codeBox')
        check(tag + 'export includes the save time', '"savedAt":' in p.evaluate("(c) => decodeURIComponent(escape(atob(c.slice(c.indexOf(':') + 1))))", code))

        links = p.evaluate("""() => [].map.call(document.querySelectorAll('#swrap a[target=_blank]'), function (a) { return [a.textContent, a.getAttribute('href'), a.getAttribute('rel')]; })""")
        hrefs = [l[1] for l in links]
        check(tag + 'link to the GitHub repo', REPO in hrefs, links)
        feat = [h for h in hrefs if 'template=feature_request.yml' in h]
        bug = [h for h in hrefs if 'template=bug_report.yml' in h]
        check(tag + 'suggest-a-feature link opens the feature form', len(feat) == 1 and feat[0].startswith(REPO + '/issues/new?'), feat)
        check(tag + 'report-a-problem link opens the bug form', len(bug) == 1 and bug[0].startswith(REPO + '/issues/new?'), bug)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(bug[0] if bug else '').query)
        ua = p.evaluate("() => navigator.userAgent")
        check(tag + 'problem form pre-filled with version and device',
              q.get('version', [''])[0].startswith('v' + version) and updated in q.get('version', [''])[0] and q.get('device', [''])[0] == ua, q)
        check(tag + 'links open outside the app safely', all(l[2] == 'noopener' for l in links), links)
        p.locator('#swrap .sec:has(h2:text-is("About & feedback"))').scroll_into_view_if_needed()
        p.screenshot(path=os.path.join(SHOTS, 'about_%dx%d.png' % vp))
        check(tag + 'no page errors', not errs, errs)
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
