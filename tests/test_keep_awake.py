"""Keep the screen on (Wake Lock, or the silent-video fallback on older devices) and the full-screen help in settings."""
import datetime
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)

# A fake Wake Lock API that records requests and lets the test release the lock like the system would.
WAKELOCK = """
window.__wl = { requests: 0, released: 0, deny: false, sentinel: null };
Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request: function (type) {
  window.__wl.requests++;
  if (window.__wl.deny) return Promise.reject(new Error('NotAllowedError'));
  var handlers = [];
  var s = { type: type, released: false, addEventListener: function (e, f) { if (e === 'release') handlers.push(f); },
            release: function () { s.released = true; window.__wl.released++; handlers.forEach(function (f) { f(); }); return Promise.resolve(); } };
  window.__wl.sentinel = s;
  return Promise.resolve(s);
} } });
"""
# An older browser: no Wake Lock; video play() is recorded (and can be refused until a tap).
NO_WAKELOCK = """
Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: undefined });
window.__vid = { plays: 0, deny: true, last: null };
HTMLMediaElement.prototype.play = function () {
  window.__vid.plays++; window.__vid.last = this;
  return window.__vid.deny ? Promise.reject(new Error('NotAllowedError')) : Promise.resolve();
};
"""
FULLSCREEN = "window.__fs = 0; Element.prototype.requestFullscreen = function () { window.__fs++; return Promise.resolve(); };"
STATUS = "() => { var e = document.getElementById('awakeStatus'); return e ? e.textContent : null; }"


def fresh(b, vp, script):
    p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
    p.add_init_script(script)
    p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(500)
    return p


with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp

        # ---- modern browser: Wake Lock ----
        p = fresh(b, vp, WAKELOCK + FULLSCREEN)
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        check(tag + 'keep the screen on is on by default', p.evaluate("() => %s.S().keepAwake" % H) is True)
        check(tag + 'wake lock requested at start', p.evaluate("() => __wl.requests") >= 1)
        p.evaluate("() => __wl.sentinel.release()")            # the system lets go (e.g. the app went to the background)
        p.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
        p.clock.run_for(100)
        check(tag + 'asked again when the page is visible again', p.evaluate("() => __wl.requests") >= 2 and p.evaluate("() => !__wl.sentinel.released"))
        open_settings(p, vp)
        check(tag + 'settings: switch + status "built in"', p.is_visible('#keepAwake') is False and p.evaluate("() => !!document.getElementById('keepAwake')") and
              'built into this device' in (p.evaluate(STATUS) or ''), p.evaluate(STATUS))
        p.evaluate("() => { var e = document.getElementById('keepAwake'); e.checked = false; e.dispatchEvent(new Event('change', {bubbles: true})); }")
        p.clock.run_for(100)
        check(tag + 'switched off: lock released, saved, status says off',
              p.evaluate("() => __wl.sentinel.released") and p.evaluate("() => %s.S().keepAwake" % H) is False and 'Off' in (p.evaluate(STATUS) or ''), p.evaluate(STATUS))
        n = p.evaluate("() => __wl.requests")
        p.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
        p.clock.run_for(100)
        check(tag + 'switched off: not asked again', p.evaluate("() => __wl.requests") == n)

        # full-screen help
        fs = p.evaluate("() => { var s = document.querySelector('#swrap .sec'); return s.textContent; }")
        check(tag + 'full-screen help: home-screen steps for iPad/iPhone and Android', 'Add to Home Screen' in fs and 'Android' in fs, fs[:80])
        check(tag + '"Go full screen" button when the browser allows it', p.is_visible('#goFull'))
        p.click('#goFull')
        check(tag + 'button asks the browser for full screen', p.evaluate("() => __fs") == 1)
        check(tag + 'setup checklist is for any device', p.evaluate("() => [].some.call(document.querySelectorAll('#swrap h2'), function (h) { return h.textContent === 'Device setup checklist'; })"))
        check(tag + 'no page errors', not errs, errs)
        p.close()

        # ---- older browser: silent video, needs a tap ----
        p = fresh(b, vp, NO_WAKELOCK)
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        v = p.evaluate("() => { var v = __vid.last; return v ? [v.muted, v.loop, v.hasAttribute('playsinline'), (v.currentSrc || v.src || '').slice(0, 15)] : null; }")
        check(tag + 'fallback video: muted, looping, inline, tiny built-in mp4', v == [True, True, True, 'data:video/mp4;'], v)
        open_settings(p, vp)
        check(tag + 'refused before a tap: status asks for a tap', 'Tap the clock once' in (p.evaluate(STATUS) or ''), p.evaluate(STATUS))
        p.click('#done')
        p.evaluate("() => { __vid.deny = false; }")
        p.mouse.click(vp[0] / 2, vp[1] / 2)                    # the tap that also unlocks sound
        p.clock.run_for(400)
        open_settings(p, vp)
        check(tag + 'after a tap: video playing, status "older device"', 'older device' in (p.evaluate(STATUS) or ''), p.evaluate(STATUS))
        check(tag + 'no "Go full screen" button when the browser has no full-screen support',
              not p.is_visible('#goFull') or p.evaluate("() => !!document.documentElement.requestFullscreen"))
        check(tag + 'no page errors (older browser)', not errs, errs)
        p.close()

        # ---- already running from the home screen ----
        p = fresh(b, vp, "Object.defineProperty(navigator, 'standalone', {get: function () { return true; }});" + WAKELOCK)
        open_settings(p, vp)
        fs = p.evaluate("() => document.querySelector('#swrap .sec').textContent")
        check(tag + 'home-screen app: says it is already full screen, no button', 'full screen from the home screen' in fs and not p.is_visible('#goFull'), fs[:120])
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
