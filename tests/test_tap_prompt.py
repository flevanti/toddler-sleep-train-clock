"""The "tap the screen once" prompt after a start (sound and/or keep-awake need a touch) and the thumbs-up after the tap."""
import datetime
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)

# An older device: no Wake Lock, the keep-awake video is refused until a tap, and sound starts suspended until resume().
OLD_DEVICE = """
Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: undefined });
window.__deny = true;
HTMLMediaElement.prototype.play = function () { return window.__deny ? Promise.reject(new Error('NotAllowedError')) : Promise.resolve(); };
(function () {
  var Real = window.AudioContext;
  window.AudioContext = function () {
    var c = new Real(), st = 'suspended';
    Object.defineProperty(c, 'state', { get: function () { return st; } });
    c.resume = function () { if (!window.__deny) { st = 'running'; if (c.onstatechange) setTimeout(c.onstatechange, 0); } return Promise.resolve(); };
    return c;
  };
})();
"""
# A newer device: Wake Lock works without a tap.
NEW_DEVICE = """
Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request: function () {
  return Promise.resolve({ addEventListener: function () {}, release: function () { return Promise.resolve(); } }); } } });
"""
BADGE = "() => { var b = document.getElementById('badge'); return [getComputedStyle(b).display, b.className, b.textContent]; }"
THUMBS = "() => document.getElementById('thumbs').className"


def fresh(b, vp, script, when, tone=True):
    p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
    p.add_init_script(script)
    p.clock.install(time=when)
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(300)
    if tone:   # a wake sound on every day, so sound needs the tap too
        p.evaluate("() => { var s = %s.S(), d = s.days.map(function (x) { return {bed: x.bed, wake: x.wake, tone: 'chime'}; }); %s.setS({days: d}); }" % (H, H))
    p.clock.run_for(1200)
    return p


DAY = datetime.datetime(2026, 9, 23, 10, 0, 0)
NIGHT = datetime.datetime(2026, 9, 23, 22, 0, 0)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp

        # ---- day, older device: big prompt that says why, then a thumbs-up ----
        p = fresh(b, vp, OLD_DEVICE, DAY)
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        bd = p.evaluate(BADGE)
        check(tag + 'day: big "Tap the screen once" prompt', bd[0] == 'block' and bd[1] == 'big' and 'Tap the screen once' in bd[2], bd)
        check(tag + 'says why: keep the screen on and play sounds, for technical reasons',
              'keep the screen on and play sounds' in bd[2] and 'technical reasons' in bd[2], bd[2])
        check(tag + 'no thumbs-up before the tap', p.evaluate(THUMBS) == '')
        p.screenshot(path='%s/tap-prompt-day-%dx%d.png' % (SHOTS, vp[0], vp[1]))
        p.evaluate("() => { __deny = false; }")
        p.mouse.click(vp[0] / 2, vp[1] * 0.8)
        p.clock.run_for(600)
        check(tag + 'after the tap: prompt gone', p.evaluate(BADGE)[0] == 'none', p.evaluate(BADGE))
        check(tag + 'after the tap: thumbs-up shows', p.evaluate(THUMBS) == 'show')
        p.clock.run_for(2000)
        check(tag + 'thumbs-up goes away by itself', p.evaluate(THUMBS) == '')
        check(tag + 'no page errors', not errs, errs)
        p.close()

        # ---- only the screen needs the tap (no sounds set) ----
        p = fresh(b, vp, OLD_DEVICE, DAY, tone=False)
        bd = p.evaluate(BADGE)
        check(tag + 'no sounds set: asks only to keep the screen on', bd[0] == 'block' and 'keep the screen on.' in bd[2] and 'sounds' not in bd[2], bd[2])
        p.evaluate("() => %s.setS({keepAwake: false})" % H)   # the need goes away without a tap: no thumbs-up
        p.clock.run_for(1200)
        check(tag + 'need gone without a tap: prompt hides, no thumbs-up', p.evaluate(BADGE)[0] == 'none' and p.evaluate(THUMBS) == '')
        p.close()

        # ---- night: small, dim prompt; dim thumbs-up in the night colour ----
        p = fresh(b, vp, OLD_DEVICE, NIGHT)
        bd = p.evaluate(BADGE)
        check(tag + 'night: small dim prompt', bd[0] == 'block' and bd[1] == 'night' and 'tap once to keep the screen on and play sounds' in bd[2], bd)
        p.evaluate("() => { __deny = false; }")
        p.mouse.click(vp[0] / 2, vp[1] * 0.8)
        p.clock.run_for(600)
        th = p.evaluate("() => { var t = document.getElementById('thumbs'); return [t.className, getComputedStyle(t).color, +t.querySelector('g').style.opacity]; }")
        check(tag + 'night: thumbs-up in the night colour, dimmed', th[0] == 'show' and th[1] == 'rgb(255, 59, 31)' and th[2] < 0.5, th)
        p.close()

        # ---- newer device, no sounds: nothing to ask ----
        p = fresh(b, vp, NEW_DEVICE, DAY, tone=False)
        check(tag + 'newer device, no sounds: no prompt at all', p.evaluate(BADGE)[0] == 'none', p.evaluate(BADGE))
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
