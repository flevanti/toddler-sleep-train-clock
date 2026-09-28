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
        v = p.evaluate("() => { var v = __vid.last; return v ? [v.muted, v.loop, v.hasAttribute('playsinline'), (v.currentSrc || v.src || '').slice(0, 15), v.parentNode === document.body] : null; }")
        # Safari ignores muted or looping videos for keeping the screen on (WebKit HTMLMediaElement::shouldDisableSleep)
        check(tag + 'fallback video: NOT muted, NOT looping, inline, tiny built-in mp4, in the page', v == [False, False, True, 'data:video/mp4;', True], v)
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

        # ---- installed app on Android / desktop: no navigator.standalone, but display-mode says fullscreen ----
        p = fresh(b, vp, "var mm = window.matchMedia; window.matchMedia = function (q) { return /display-mode/.test(q) ? {matches: true, media: q} : mm.call(window, q); };" + WAKELOCK)
        open_settings(p, vp)
        warn = p.evaluate("() => [].map.call(document.querySelectorAll('#swrap .status.bad'), function (e) { return e.textContent; }).join(' | ')")
        check(tag + 'installed app (display-mode): no "normal browser tab" warning', 'normal browser tab' not in warn, warn)
        check(tag + 'installed app (display-mode): says it is already full screen', 'full screen from the home screen' in p.evaluate("() => document.querySelector('#swrap .sec').textContent"))
        p.close()
        p = fresh(b, vp, WAKELOCK)
        open_settings(p, vp)
        check(tag + 'normal browser tab: warning says so, device-neutral', 'Opened in a normal browser tab' in p.evaluate("() => document.getElementById('swrap').textContent"))
        p.close()
    b.close()

    # ---- real playback in WebKit (Safari's engine), if installed: `.venv/bin/playwright install webkit` ----
    # Checks the conditions WebKit needs to keep the display on: playing, unmuted, sound + video tracks, never looping or ending.
    try:
        wk = pw.webkit.launch()
    except Exception as e:
        wk = None
        print('SKIP WebKit playback check (WebKit not installed)', str(e).splitlines()[0])
    if wk:
        p = wk.new_page(viewport={'width': 1024, 'height': 768})
        p.add_init_script("Object.defineProperty(navigator, 'wakeLock', {configurable: true, value: undefined});")
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.goto(URL)
        p.wait_for_timeout(800)
        VID = "() => { var v = document.querySelector('body > video'); return {paused: v.paused, muted: v.muted, loop: v.loop, vol: v.volume, t: v.currentTime, dur: v.duration, audio: v.audioTracks.length, video: v.videoTracks.length}; }"
        check('WebKit: unmuted video waits for a tap', p.evaluate(VID)['paused'] is True)
        p.mouse.click(512, 400)
        ts = []
        for i in range(16):
            p.wait_for_timeout(250)
            ts.append(p.evaluate(VID)['t'])
        v = p.evaluate(VID)
        check('WebKit: after a tap it plays, unmuted, with sound and video tracks, no loop',
              not v['paused'] and not v['muted'] and not v['loop'] and v['vol'] > 0 and v['audio'] >= 1 and v['video'] >= 1, v)
        check('WebKit: rewound before the end, so it never "ends"', max(ts) < v['dur'] - 0.1 and min(ts[4:]) < 0.4, [round(t, 2) for t in ts])
        check('WebKit: no page errors', not errs, errs)
        wk.close()
srv.shutdown()
sys.exit(check.finish())
