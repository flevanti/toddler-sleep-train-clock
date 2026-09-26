# Night Animations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let parents pick an animated night scene (Off, Z's & stars, Breathing, Moon & sky, or one of 14 sleeping animals) plus optional extras (Star countdown, Fireflies, Shooting star). Each scene and extra has its own settings.

**Architecture:** Everything lives in `index.html`. An animation **registry** (`SCENES`, `EXTRAS`) describes each animation: its name, a list of settings (`opts`) and the drawing functions. The settings screen, validation, defaults, export and the mini preview all read the registry. Each paint target (the real clock `MAIN` and the preview `MINI`) gets two new areas, `.below` (for the countdown) and `.layer` (full size, for sky, fireflies and shooting stars). Each area is redrawn only when its own key changes.

**Tech Stack:**
- The app: plain ES2017 JavaScript, inline SVG with SMIL animation, and CSS with `-webkit-` prefixes. Target is Safari 12 on an iPad mini 2.
- The tests: Python 3 and Playwright, in headless Chromium with a faked clock.

**Spec:** `docs/superpowers/specs/2026-09-26-night-animations-design.md`

## Global Constraints

- Deploy only `index.html` and `sw.js`. No new runtime files.
- JavaScript must be ES2017. None of these: `?.`, `??`, `=>`, `let`, `const`, `class`, `replaceAll`, `.at(`, `structuredClone`, `fromEntries`, `<dialog>`. CSS may not use flex `gap`, `inset`, `aspect-ratio` or `:focus-visible`. Keep `-webkit-` prefixes on transforms and animations. `tests/check_static.sh` enforces all of this.
- SVG animation uses SMIL (`<animate>`, `<animateTransform>`, `<animateMotion>`). The only exception is the existing Z's & stars look, which keeps its CSS keyframes `.twinkle` and `.zz`, so the default look doesn't change.
- Everything uses `NIGHT_COLORS[S.nightColor]` and is dimmed by `S.nightDim`. Nothing is brighter than the face.
- No `id` attributes in animation markup. The only exceptions are gradient ids that start with the paint target's `gid` (`shMain` or `shMini`).
- Animations run **only in the sleep phase** (`st.mode === 'sleep'`), naps included. Amber, green and day are unchanged.
- Default is `scene: 'classic'` with all extras off. Settings saved before v1.4 must load and look the same.
- Stored under `S.night = { scene, scenes: {<scene>: {...}}, extras: {<extra>: {on, ...}} }`.
- Use the git identity from the global git config. Every commit message ends with:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- All work happens on branch `night-animations`.

## Review Focus

1. **Saved settings that are old, hand-edited or corrupted** must still load. That covers `night` missing, a string, an array, `null`, or `scene: "toString"`, which is a name every JS object inherits. The expected result is the default look, never a blank screen or an exception. *Tested in Task 1.*
2. **Night brightness must dim every new layer.** A parent who sets 5% expects the countdown, sky stars and fireflies to be as dim as the face. *Tested in Task 2 (the plumbing) and Task 4 (the sky).*
3. **Turning the iPad while it's night:** fireflies and shooting stars are laid out in pixels. After rotation they must be redrawn to the new size, not stay in a corner or off-screen. *Tested in Task 6.*
4. **A bedtime that changes from one day to the next:** at 03:00 on Monday, "since" must be **Sunday's** bedtime, not Monday's. Otherwise the countdown is wrong every Monday. *Tested in Task 2.*
5. **Running all night on an old iPad:** nothing may be rebuilt every second. Each area is redrawn only when its key changes (a star goes out, the hour changes, a setting changes, the screen is resized). *Tested in Tasks 2, 5 and 6.*

## File map

| File | Change |
|---|---|
| `index.html` | Registry, storage, timing, drawing areas, scenes, extras, animals, settings controls, CSS |
| `tests/harness.py` | **New.** Shared test helpers (server, checks, settings opener) |
| `tests/check_static.sh` | **New.** Syntax check plus the forbidden-feature grep |
| `tests/test_night_settings.py` | **New.** Storage, validation, per-scene memory, export/import |
| `tests/test_night_render.py` | **New.** Timing, redraw keys, ids, dimming, fade, every scene |
| `tests/test_night_ui.py` | **New.** Settings controls built from the registry |
| `tests/test_night_extras.py` | **New.** Countdown, fireflies, shooting stars |
| `tests/test_night_animals.py` | **New.** The 14 animals, plus the screenshot sheet |
| `tests/README.md`, `REQUIREMENTS.md` | Docs |

How to run things:
- One suite: `.venv/bin/python tests/<file>.py . tests/screenshots`, from the repo root.
- All suites: `tests/run_all.sh`.
- Static checks: `tests/check_static.sh`.

---

## Stage 1: foundation

### Task 1: Test helpers, static checks, registry and storage

**Files:**
- Create: `tests/harness.py`, `tests/check_static.sh`, `tests/test_night_settings.py`
- Modify: `index.html`. Add the registry before `function defaults()`, the `night` default, a branch in `merge()`, and an entry in the test hook.

**Interfaces:**
- Produces:
  - `SCENES`, `EXTRAS` (objects keyed by id): `{ name, opts, face?, layer?, place?, draw?, key? }`
  - `opt = { key, label, type: 'choice'|'toggle', values?: [[value, label]], def }`
  - `has(obj, key) -> bool`
  - `optDefaults(opts) -> object`
  - `optValid(opt, v) -> bool`
  - `mergeOpts(target, opts, src)`
  - `nightDefaults() -> {scene, scenes, extras}`
  - `mergeNight(n, o)`
  - test hook `window.__toddlerSleepTrainClock.night = { SCENES, EXTRAS, defaults }`
- Python: `harness.serve(root) -> (server, url)`, `harness.Checks` (callable `check(name, cond, info)`, `.finish() -> exit code`), `harness.H`, `harness.open_settings(page, (w, h))`, `harness.VIEWPORTS`.

- [ ] **Step 1: Create the shared test helpers**

`tests/harness.py`:

```python
"""Shared helpers for the browser tests: static server, check(), settings opener."""
import functools
import http.server
import threading

H = 'window.__toddlerSleepTrainClock'
VIEWPORTS = [(1024, 768), (768, 1024)]


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root):
    """Serve the repo root on a free local port. Returns (server, url of index.html)."""
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, 'http://127.0.0.1:%d/index.html' % srv.server_address[1]


class Checks:
    def __init__(self):
        self.fails = []

    def __call__(self, name, cond, info=''):
        print(('PASS ' if cond else 'FAIL ') + name, info)
        if not cond:
            self.fails.append(name)

    def finish(self):
        print('FAILURES:', self.fails or 'none')
        return 1 if self.fails else 0


def open_settings(p, vp):
    """Long-press the top-right corner (page must use page.clock)."""
    p.mouse.move(vp[0] - 30, 30)
    p.mouse.down()
    p.clock.run_for(2700)
    p.mouse.up()
    p.clock.run_for(200)
```

- [ ] **Step 2: Create the static check script**

`tests/check_static.sh`:

```sh
#!/bin/sh
# Syntax check (JavaScriptCore via osascript) + grep for features Safari 12 lacks. See REQUIREMENTS.md §1.
cd "$(dirname "$0")/.."
tmp="$(mktemp -t sleepclock).js"
python3 -c "import re,sys;s=open('index.html').read();open(sys.argv[1],'w').write(re.search(r'<script>(.*?)</script>',s,re.S).group(1))" "$tmp"
osascript -l JavaScript -e 'function run(a){new Function($.NSString.stringWithContentsOfFileEncodingError(a[0],4,null).js);return "syntax ok"}' "$tmp" || exit 1
if grep -nE "\?\.|\?\?|replaceAll|\.at\(|structuredClone|fromEntries|<dialog|[^-]gap:|inset:|aspect-ratio|focus-visible|=>|\blet |\bconst |\bclass " index.html sw.js | grep -v "Written for Safari"; then
  echo "forbidden features found (see above)"; exit 1
fi
echo "static ok"
```

Run: `chmod +x tests/check_static.sh && tests/check_static.sh`
Expected: `syntax ok` then `static ok`.

- [ ] **Step 3: Write the failing storage test**

`tests/test_night_settings.py`:

```python
"""Night animation settings: defaults, validation against the registry, per-scene memory, export/import."""
import datetime
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
KEY = 'toddler-sleep-train-clock.settings.v1'
check = Checks()
srv, URL = serve(ROOT)


def night(p):
    return p.evaluate("() => %s.S().night || null" % H) or {}


def scene_opts(n, name):
    return (n.get('scenes') or {}).get(name) or {}


def load_saved(p, obj):
    p.evaluate("(o) => localStorage.setItem('%s', JSON.stringify(o))" % KEY, obj)
    p.reload()
    p.clock.run_for(300)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={'width': 1024, 'height': 768})
    errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.clock.install(time=datetime.datetime(2026, 9, 23, 12, 0, 0))
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(300)

    reg = p.evaluate("() => { var n = %s.night; return n ? {scenes: Object.keys(n.SCENES), extras: Object.keys(n.EXTRAS)} : null; }" % H) or {'scenes': [], 'extras': []}
    d = night(p)
    check('registry exposed with off + classic + breathing', {'off', 'classic', 'breathing'} <= set(reg['scenes']), reg)
    check('default scene is classic', d.get('scene') == 'classic', d.get('scene'))
    check('one settings set per registered scene', sorted((d.get('scenes') or {}).keys()) == sorted(reg['scenes']), d.get('scenes'))
    check('one entry per registered extra, all off',
          sorted((d.get('extras') or {}).keys()) == sorted(reg['extras']) and all(x.get('on') is False for x in (d.get('extras') or {}).values()),
          d.get('extras'))
    check('classic defaults', scene_opts(d, 'classic') == {'stars': 3, 'zz': True, 'speed': 'normal'}, scene_opts(d, 'classic'))
    check('breathing defaults', scene_opts(d, 'breathing') == {'pace': 6, 'depth': 'medium', 'glow': True}, scene_opts(d, 'breathing'))

    # settings saved before v1.4 have no "night" at all
    load_saved(p, {'nightColor': 'amber'})
    check('pre-1.4 settings get the default night', night(p).get('scene') == 'classic' and p.evaluate("() => %s.S().nightColor" % H) == 'amber')

    # tampered / invalid values
    load_saved(p, {'night': {'scene': 'toString',
                             'scenes': {'classic': {'stars': 4, 'zz': 'yes', 'speed': 'slow', 'bogus': 1}, 'breathing': {'pace': 8}, 'nope': {}},
                             'extras': {'nope': {'on': True}}}})
    n = night(p)
    check('inherited name rejected as scene', n.get('scene') == 'classic', n.get('scene'))
    check('invalid choice keeps default', scene_opts(n, 'classic').get('stars') == 3, scene_opts(n, 'classic'))
    check('wrong-type toggle keeps default', scene_opts(n, 'classic').get('zz') is True)
    check('valid values kept', scene_opts(n, 'classic').get('speed') == 'slow' and scene_opts(n, 'breathing').get('pace') == 8)
    check('unknown names and keys dropped',
          'bogus' not in scene_opts(n, 'classic') and 'nope' not in (n.get('scenes') or {}) and 'nope' not in (n.get('extras') or {}), n)
    for bad in ['garbage', 42, None, [], {'scenes': 'x', 'extras': [1, 2]}]:
        load_saved(p, {'night': bad})
        m = night(p)
        check('night=%r falls back to defaults' % (bad,), m.get('scene') == 'classic' and scene_opts(m, 'classic').get('stars') == 3, m)

    # each scene keeps its own settings
    p.evaluate("() => %s.setS({night: {scene: 'breathing', scenes: {classic: {stars: 10}, breathing: {depth: 'deep'}}}})" % H)
    n = night(p)
    check('switching scene keeps the other scene settings',
          n.get('scene') == 'breathing' and scene_opts(n, 'classic').get('stars') == 10 and scene_opts(n, 'breathing').get('depth') == 'deep', n)

    # export / import round trip through the settings screen
    open_settings(p, (1024, 768))
    p.click('#expBtn')
    code = p.input_value('#codeBox')
    p.evaluate("() => %s.setS({})" % H)
    p.fill('#codeBox', code)
    p.click('#impBtn')
    n = night(p)
    check('export/import keeps night settings', n.get('scene') == 'breathing' and scene_opts(n, 'classic').get('stars') == 10, n)
    check('no page errors', not errs, errs)
    b.close()
srv.shutdown()
sys.exit(check.finish())
```

- [ ] **Step 4: Run it to see it fail**

Run: `.venv/bin/python tests/test_night_settings.py . tests/screenshots`
Expected: `FAIL registry exposed…`, `FAIL default scene is classic`, and more. It ends with a `FAILURES:` list.

- [ ] **Step 5: Add the registry and storage helpers**

In `index.html`, insert this block immediately **before** the line `  function defaults() {`:

```js
  // ---------- night animations: registry ----------
  // A scene replaces the night face (choose one); extras draw on top (any number).
  // opt: { key, label, type: 'choice' | 'toggle', values: [[value, label], ...] (choice only), def }
  var SCENES = {
    off: { name: 'Off', opts: [] },
    classic: { name: 'Z’s & stars', opts: [
      { key: 'stars', label: 'Stars', type: 'choice', values: [[3, '3'], [6, '6'], [10, '10']], def: 3 },
      { key: 'zz', label: 'Floating z’s', type: 'toggle', def: true },
      { key: 'speed', label: 'Speed', type: 'choice', values: [['slow', 'Slow'], ['normal', 'Normal']], def: 'normal' }
    ] },
    breathing: { name: 'Breathing', opts: [
      { key: 'pace', label: 'Pace', type: 'choice', values: [[4, '4 breaths a minute'], [6, '6 breaths a minute'], [8, '8 breaths a minute']], def: 6 },
      { key: 'depth', label: 'Depth', type: 'choice', values: [['subtle', 'Subtle'], ['medium', 'Medium'], ['deep', 'Deep']], def: 'medium' },
      { key: 'glow', label: 'Glow on in-breath', type: 'toggle', def: true }
    ] }
  };
  var EXTRAS = {
  };

  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function optDefaults(opts) { var o = {}; for (var i = 0; i < opts.length; i++) o[opts[i].key] = opts[i].def; return o; }
  function optValid(opt, v) {
    if (opt.type === 'toggle') return typeof v === 'boolean';
    for (var i = 0; i < opt.values.length; i++) if (opt.values[i][0] === v) return true;
    return false;
  }
  function mergeOpts(target, opts, src) {
    if (!src || typeof src !== 'object') return;
    for (var i = 0; i < opts.length; i++) if (has(src, opts[i].key) && optValid(opts[i], src[opts[i].key])) target[opts[i].key] = src[opts[i].key];
  }
  function nightDefaults() {
    var n = { scene: 'classic', scenes: {}, extras: {} }, k;
    for (k in SCENES) n.scenes[k] = optDefaults(SCENES[k].opts);
    for (k in EXTRAS) { n.extras[k] = optDefaults(EXTRAS[k].opts); n.extras[k].on = false; }
    return n;
  }
  // Checks saved night settings against the registry: unknown names and keys are dropped, invalid values keep the default.
  function mergeNight(n, o) {
    if (!o || typeof o !== 'object') return;
    if (typeof o.scene === 'string' && has(SCENES, o.scene)) n.scene = o.scene;
    var k, src;
    for (k in SCENES) mergeOpts(n.scenes[k], SCENES[k].opts, o.scenes && typeof o.scenes === 'object' && has(o.scenes, k) ? o.scenes[k] : null);
    for (k in EXTRAS) {
      src = o.extras && typeof o.extras === 'object' && has(o.extras, k) ? o.extras[k] : null;
      mergeOpts(n.extras[k], EXTRAS[k].opts, src);
      if (src && typeof src === 'object' && typeof src.on === 'boolean') n.extras[k].on = src.on;
    }
  }

```

(`EXTRAS` stays an object literal that later tasks fill in. Don't reassign it, because the test hook holds a reference to it.)

- [ ] **Step 6: Add the default and the merge branch**

In `defaults()` replace:

```js
      fadeSec: 3,          // crossfade length at each phase change (0 = hard change)
```

with:

```js
      fadeSec: 3,          // crossfade length at each phase change (0 = hard change)
      night: nightDefaults(), // night scene + extras, see SCENES / EXTRAS
```

In `merge()` replace:

```js
      } else if (typeof o[k] === typeof s[k] || s[k] === null) {
```

with:

```js
      } else if (k === 'night') {
        mergeNight(s.night, o.night);
      } else if (typeof o[k] === typeof s[k] || s[k] === null) {
```

(This branch must come before the generic `typeof` branch. Otherwise any saved object would overwrite `s.night` unchecked.)

- [ ] **Step 7: Expose the registry to tests**

Replace:

```js
    sim: function () { return sim; }, firedKey: function () { return firedKey; }, alarmPlaying: alarmPlaying };
```

with:

```js
    sim: function () { return sim; }, firedKey: function () { return firedKey; }, alarmPlaying: alarmPlaying,
    night: { SCENES: SCENES, EXTRAS: EXTRAS, defaults: nightDefaults } };
```

- [ ] **Step 8: Run the test to see it pass, then everything else**

Run: `.venv/bin/python tests/test_night_settings.py . tests/screenshots`
Expected: every line `PASS`, and `FAILURES: none`.

Run: `tests/check_static.sh && tests/run_all.sh`
Expected: `static ok`. Every suite reports `FAILURES: none` or `RESULT PASS`, and the exit code is 0.

- [ ] **Step 9: Commit**

```bash
git add index.html tests/harness.py tests/check_static.sh tests/test_night_settings.py
git commit -m "Night animations: registry and validated storage

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Night timing, drawing areas, and the Off, Z's & stars and Breathing scenes

**Files:**
- Modify: `index.html`. This task touches `computeState`, `faceSVG` (split into `faceInner` and `faceSVG`), the clock and mini markup, `MAIN` and `MINI`, `paint`, `snapshot`, `openSettings`, the CSS, the registry entries and the test hook.
- Create: `tests/test_night_render.py`

**Interfaces:**
- Consumes (Task 1): `SCENES`, `EXTRAS`, `S.night`.
- Produces:
  - `computeState(now, ignoreNap)`: its sleep results now also carry `since` (in ms).
  - `nightFrac(st, now) -> 0..1`
  - `SVG_OPEN` (string)
  - `faceInner(mode, gid, sleepExtra) -> string`
  - `faceSVG(mode, gid, sleepExtra) -> string`
  - a scene's `face(o, ctx) -> svg string` and optional `layer(o, ctx) -> svg string`
  - an extra's `draw(o, ctx) -> svg string`, `place: 'below' | 'layer'`, optional `key(o, ctx) -> string`
  - a scene's optional `layerKey(o, ctx) -> string`
  - `ctx = { color, gid, frac, now, since, until, scale, w, h }`
  - paint targets gain `.below`, `.layer` and `.keys = {face, below, layer}`, replacing `.key`
  - test hook top-level `nightFrac` and `repaint()`

- [ ] **Step 1: Write the failing render test**

`tests/test_night_render.py`:

```python
"""Night scenes and drawing: timing (since/frac), per-area redraw keys, ids, dimming, fade, a screenshot of every scene."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
DUP_IDS = "() => { var seen = {}, d = []; [].forEach.call(document.querySelectorAll('[id]'), function (e) { if (seen[e.id]) d.push(e.id); seen[e.id] = 1; }); return d; }"
# inside a paint target only its container ids and gradients named after its gid are allowed
STRAY_IDS = """([root, gid, keep]) => [].filter.call(document.querySelectorAll(root + ' [id]'), function (e) {
    return keep.indexOf(e.id) < 0 && !(e.id.indexOf(gid) === 0 && /Gradient$/.test(e.tagName)); }).map(function (e) { return e.tagName + '#' + e.id; })"""
MAIN_KEEP = ['face', 'below', 'time', 'label', 'layer']
MINI_KEEP = ['miniFace', 'miniBelow', 'miniTime', 'miniLabel', 'miniLayer']
BREATH = "(root) => { var a = document.querySelector(root + ' animateTransform'); return a ? [a.getAttribute('dur'), a.getAttribute('values'), !!document.querySelector(root + ' radialGradient[id$=Halo]')] : null; }"


def ms(*a):
    return int(datetime.datetime(*a).timestamp() * 1000)


with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ---- timing ----
    p = b.new_page(viewport={'width': 1024, 'height': 768})
    p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))  # Wednesday night
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(300)
    days = [{'bed': '19:00', 'wake': '07:00', 'tone': 'off'} for _ in range(7)]
    days[0]['bed'] = '20:30'  # Sunday
    p.evaluate("(d) => %s.setS({days: d})" % H, days)

    def st(*a):
        return p.evaluate("(t) => %s.computeState(new Date(t))" % H, ms(*a))

    s = st(2026, 9, 23, 22, 0)
    check('evening: since = tonight bedtime', s.get('since') == ms(2026, 9, 23, 19, 0) and s.get('until') == ms(2026, 9, 24, 7, 0), s)
    s = st(2026, 9, 24, 3, 0)
    check('after midnight: since = yesterday bedtime', s.get('since') == ms(2026, 9, 23, 19, 0), s)
    s = st(2026, 9, 28, 3, 0)  # Monday 03:00; Sunday bedtime differs
    check('uses the previous day schedule (Sun 20:30)', s.get('since') == ms(2026, 9, 27, 20, 30), s)

    def frac(t, a, z):
        return p.evaluate("([t, a, z]) => %s.nightFrac({since: a, until: z}, new Date(t))" % H, [t, a, z])

    a, z = ms(2026, 9, 23, 19, 0), ms(2026, 9, 24, 7, 0)
    check('frac 0 / 0.5 / 1', [frac(a, a, z), frac((a + z) // 2, a, z), frac(z, a, z)] == [0, 0.5, 1])
    check('frac clamps and handles missing times',
          [frac(a - 60000, a, z), frac(z + 60000, a, z), p.evaluate("() => %s.nightFrac({}, new Date())" % H)] == [0, 1, 0])
    p.evaluate("() => { var t = Date.now(); %s.setS({nap: {start: t - 600000, end: t + 1200000}}); }" % H)
    s = p.evaluate("() => %s.computeState(new Date())" % H)
    check('nap: since = nap start', s.get('nap') is True and s.get('since') == s.get('until', 0) - 1800000, s)
    p.close()

    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp
        p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))
        p.goto(URL)
        p.evaluate("() => localStorage.clear()")
        p.reload()
        p.clock.run_for(300)

        # every registered scene (later tasks' scenes are picked up automatically)
        for sc in p.evaluate("() => Object.keys(%s.night.SCENES)" % H):
            p.evaluate("(k) => %s.setS({night: {scene: k}})" % H, sc)
            p.clock.run_for(1100)
            check(tag + sc + ': face drawn', p.evaluate("() => !!document.querySelector('#face svg')"))
            stray = p.evaluate(STRAY_IDS, ['#clock', 'shMain', MAIN_KEEP])
            check(tag + sc + ': no stray ids', stray == [], stray)
            p.evaluate("() => { window.__f = document.querySelector('#face svg'); window.__l = document.getElementById('layer').firstChild; }")
            p.clock.run_for(3000)
            check(tag + sc + ': no redraw between ticks',
                  p.evaluate("() => window.__f === document.querySelector('#face svg') && window.__l === document.getElementById('layer').firstChild"))
            p.screenshot(path=os.path.join(SHOTS, 'night_%s_%dx%d.png' % (sc, vp[0], vp[1])))

        # Z's & stars: default look unchanged, settings apply
        count = "() => [document.querySelectorAll('#face .twinkle').length, document.querySelectorAll('#face .zz').length, document.querySelectorAll('#face .slow').length]"
        p.evaluate("() => %s.setS({})" % H)
        p.clock.run_for(1100)
        check(tag + 'classic default = 3 stars, 2 z, normal speed', p.evaluate(count) == [3, 2, 0], p.evaluate(count))
        p.evaluate("() => %s.setS({night: {scenes: {classic: {stars: 10, zz: false, speed: 'slow'}}}})" % H)
        p.clock.run_for(1100)
        check(tag + 'classic 10 stars, no z, slow', p.evaluate(count) == [10, 0, 1], p.evaluate(count))

        # breathing
        p.evaluate("() => %s.setS({night: {scene: 'breathing'}})" % H)
        p.clock.run_for(1100)
        check(tag + 'breathing default: 10 s, 4 %, glow', p.evaluate(BREATH, '#face') == ['10s', '1;1.04;1', True], p.evaluate(BREATH, '#face'))
        p.evaluate("() => %s.setS({night: {scene: 'breathing', scenes: {breathing: {pace: 8, depth: 'deep', glow: false}}}})" % H)
        p.clock.run_for(1100)
        check(tag + 'breathing 8/min, deep, no glow', p.evaluate(BREATH, '#face') == ['7.5s', '1;1.07;1', False], p.evaluate(BREATH, '#face'))

        # night brightness reaches every area
        p.evaluate("() => %s.setS({nightDim: 40})" % H)
        p.clock.run_for(1100)
        op = p.evaluate("() => ['face', 'below', 'layer'].map(function (id) { return document.getElementById(id).style.opacity; })")
        check(tag + 'night brightness dims face, below and layer', op == ['0.4', '0.4', '0.4'], op)

        # nothing drawn outside the night
        p.clock.set_system_time(datetime.datetime(2026, 9, 24, 12, 0, 0))
        p.clock.run_for(1100)
        check(tag + 'day: below and layer empty',
              p.evaluate("() => document.getElementById('below').innerHTML === '' && document.getElementById('layer').innerHTML === ''"))

        # mini preview draws the scene too
        p.evaluate("() => %s.setS({night: {scene: 'breathing'}})" % H)
        open_settings(p, vp)
        p.click('#pvtabs [data-pv="sleep"]')
        check(tag + 'mini shows the scene', p.evaluate(BREATH, '#miniFace') is not None)
        stray = p.evaluate(STRAY_IDS, ['#mini', 'shMini', MINI_KEEP])
        check(tag + 'mini: no stray ids', stray == [], stray)
        check(tag + 'no duplicate ids with both targets', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))
        p.click('#done')

        # phase-change fade copy of a scene that has its own gradient
        p.evaluate("() => %s.setS({soonMin: 15, fadeSec: 3, night: {scene: 'breathing'}})" % H)
        p.clock.set_system_time(datetime.datetime(2026, 9, 25, 6, 44, 57))
        p.clock.run_for(1100)
        p.clock.run_for(3500)  # crosses 06:45 -> amber
        check(tag + 'fade copy present', p.evaluate("() => document.querySelectorAll('.clk.snap').length") == 1)
        check(tag + 'no duplicate ids during fade', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))
        refs = p.evaluate("() => [].map.call(document.querySelectorAll('.clk.snap [fill^=url]'), function (e) { var m = /#(.+)\\)/.exec(e.getAttribute('fill')); return !!(m && document.getElementById(m[1])); })")
        check(tag + 'fade copy gradient refs resolve', bool(refs) and all(refs), refs)
        check(tag + 'no page errors', not errs, errs)
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python tests/test_night_render.py . tests/screenshots`
Expected: `FAIL evening: since = tonight bedtime` and others. It may stop with a Python error because `nightFrac` doesn't exist yet. Either counts as a failure.

- [ ] **Step 3: Add `since` to the sleep states, and add `nightFrac`**

In `computeState` replace:

```js
      if (t < S.nap.end) return { mode: 'sleep', nap: true, until: S.nap.end };
```

with:

```js
      if (t < S.nap.end) return { mode: 'sleep', nap: true, since: S.nap.start, until: S.nap.end };
```

Replace:

```js
      if (soonMs > 0 && t >= W - soonMs) return { mode: 'soon', until: W };
      return { mode: 'sleep', until: W };
```

with:

```js
      if (soonMs > 0 && t >= W - soonMs) return { mode: 'soon', until: W };
      var yd = new Date(t); yd.setDate(yd.getDate() - 1); // this night began at yesterday's bedtime (yesterday's schedule)
      return { mode: 'sleep', since: at(yd, S.days[yd.getDay()].bed).getTime(), until: W };
```

Replace:

```js
      return { mode: 'sleep', until: at(tmr, S.days[tmr.getDay()].wake).getTime() };
```

with:

```js
      return { mode: 'sleep', since: B, until: at(tmr, S.days[tmr.getDay()].wake).getTime() };
```

Directly after the closing `}` of `computeState`, add:

```js
  // How far through this night (or nap) we are: 0 at bedtime, 1 at wake.
  function nightFrac(st, now) {
    if (!st.since || !st.until || st.until <= st.since) return 0;
    return Math.min(1, Math.max(0, (now.getTime() - st.since) / (st.until - st.since)));
  }
```

- [ ] **Step 4: Split `faceSVG` and move the Z's & stars decoration out**

Replace this `faceSVG` header and sleep branch:

```js
  function faceSVG(mode, gid) {
    var dark = 'rgba(0,0,0,.72)';
    var c, eyes, mouth, extra = '', cheeks = '';
    if (mode === 'sleep') {
      c = NIGHT_COLORS[S.nightColor] || NIGHT_COLORS.red;
      eyes = '<path d="M52 92 Q68 106 84 92" fill="none" stroke="' + dark + '" stroke-width="7" stroke-linecap="round"/>' +
             '<path d="M116 92 Q132 106 148 92" fill="none" stroke="' + dark + '" stroke-width="7" stroke-linecap="round"/>';
      mouth = '<ellipse cx="100" cy="138" rx="9" ry="7" fill="' + dark + '"/>';
      extra = '<g fill="' + c + '">' +
        '<text class="zz" x="186" y="30" font-size="30" font-family="Helvetica" font-weight="bold">z</text>' +
        '<text class="zz" style="animation-delay:1.6s;-webkit-animation-delay:1.6s" x="208" y="4" font-size="22" font-family="Helvetica" font-weight="bold">z</text>' +
        '<circle class="twinkle" cx="-14" cy="20" r="3"/>' +
        '<circle class="twinkle" style="animation-delay:1.3s;-webkit-animation-delay:1.3s" cx="-26" cy="160" r="2.5"/>' +
        '<circle class="twinkle" style="animation-delay:2.2s;-webkit-animation-delay:2.2s" cx="224" cy="170" r="3"/>' +
        '</g>';
    } else if (mode === 'soon') {
```

with:

```js
  var SVG_OPEN = '<svg viewBox="-40 -40 280 280" xmlns="http://www.w3.org/2000/svg">';
  function faceSVG(mode, gid, sleepExtra) { return SVG_OPEN + faceInner(mode, gid, sleepExtra) + '</svg>'; }
  // The round face without its <svg> wrapper; sleepExtra = decoration drawn behind the night face (from the scene).
  function faceInner(mode, gid, sleepExtra) {
    var dark = 'rgba(0,0,0,.72)';
    var c, eyes, mouth, extra = '', cheeks = '';
    if (mode === 'sleep') {
      c = NIGHT_COLORS[S.nightColor] || NIGHT_COLORS.red;
      eyes = '<path d="M52 92 Q68 106 84 92" fill="none" stroke="' + dark + '" stroke-width="7" stroke-linecap="round"/>' +
             '<path d="M116 92 Q132 106 148 92" fill="none" stroke="' + dark + '" stroke-width="7" stroke-linecap="round"/>';
      mouth = '<ellipse cx="100" cy="138" rx="9" ry="7" fill="' + dark + '"/>';
      extra = sleepExtra || '';
    } else if (mode === 'soon') {
```

Then replace the end of that function:

```js
    return '<svg viewBox="-40 -40 280 280" xmlns="http://www.w3.org/2000/svg">' + extra +
      '<circle cx="100" cy="100" r="92" fill="' + c + '"/>' +
```

with:

```js
    return extra +
      '<circle cx="100" cy="100" r="92" fill="' + c + '"/>' +
```

and:

```js
      cheeks + eyes + mouth + '</svg>';
  }
```

with:

```js
      cheeks + eyes + mouth;
  }
```

- [ ] **Step 5: Add the three scenes**

Insert directly after `faceInner`'s closing `}`:

```js
  // ---------- night scenes ----------
  function sceneOff(o, c) { return faceSVG('sleep', c.gid, ''); }
  // [cx, cy, r, twinkle delay s]; the first three are the original Z's & stars positions
  var STAR_SPOTS = [[-14, 20, 3, 0], [-26, 160, 2.5, 1.3], [224, 170, 3, 2.2], [232, 70, 2.5, 0.6], [-32, 92, 2, 1.8],
    [18, -26, 2.5, 2.8], [150, 230, 2, 0.3], [-8, 222, 2.5, 1.1], [64, 234, 2, 2.5], [238, 124, 2, 3.1]];
  function sceneClassic(o, c) {
    var h = '<g fill="' + c.color + '"' + (o.speed === 'slow' ? ' class="slow"' : '') + '>', i;
    if (o.zz) h += '<text class="zz" x="186" y="30" font-size="30" font-family="Helvetica" font-weight="bold">z</text>' +
      '<text class="zz" style="animation-delay:1.6s;-webkit-animation-delay:1.6s" x="208" y="4" font-size="22" font-family="Helvetica" font-weight="bold">z</text>';
    for (i = 0; i < o.stars; i++) {
      var s = STAR_SPOTS[i];
      h += '<circle class="twinkle"' + (s[3] ? ' style="animation-delay:' + s[3] + 's;-webkit-animation-delay:' + s[3] + 's"' : '') +
        ' cx="' + s[0] + '" cy="' + s[1] + '" r="' + s[2] + '"/>';
    }
    return faceSVG('sleep', c.gid, h + '</g>');
  }
  var BREATH_DEPTH = { subtle: 1.02, medium: 1.04, deep: 1.07 };
  function sceneBreathing(o, c) {
    var ease = ' calcMode="spline" keyTimes="0;0.5;1" keySplines=".42 0 .58 1;.42 0 .58 1" dur="' + (60 / o.pace) + 's" repeatCount="indefinite"';
    var halo = !o.glow ? '' :
      '<defs><radialGradient id="' + c.gid + 'Halo"><stop offset=".6" stop-color="' + c.color + '" stop-opacity=".45"/><stop offset="1" stop-color="' + c.color + '" stop-opacity="0"/></radialGradient></defs>' +
      '<circle cx="100" cy="100" r="128" fill="url(#' + c.gid + 'Halo)" opacity="0"><animate attributeName="opacity" values="0;1;0"' + ease + '/></circle>';
    return SVG_OPEN + halo + '<g transform="translate(100 100)"><g><animateTransform attributeName="transform" type="scale" values="1;' + BREATH_DEPTH[o.depth] + ';1"' + ease + '/>' +
      '<g transform="translate(-100 -100)">' + faceInner('sleep', c.gid, '') + '</g></g></g></svg>';
  }
```

Wire them into the registry by editing these three lines:
- `    off: { name: 'Off', opts: [] },` → `    off: { name: 'Off', face: sceneOff, opts: [] },`
- `    classic: { name: 'Z’s & stars', opts: [` → `    classic: { name: 'Z’s & stars', face: sceneClassic, opts: [`
- `    breathing: { name: 'Breathing', opts: [` → `    breathing: { name: 'Breathing', face: sceneBreathing, opts: [`

(The functions are declared further down the file, but function declarations are hoisted, so the registry can reference them.)

- [ ] **Step 6: Add the `.below` and `.layer` areas to both paint targets**

Replace:

```html
<div id="clock" class="clk">
  <div id="face" class="face"></div>
  <div id="time" class="time"></div>
  <div id="label" class="label"></div>
</div>
```

with:

```html
<div id="clock" class="clk">
  <div id="face" class="face"></div>
  <div id="below" class="below"></div>
  <div id="time" class="time"></div>
  <div id="label" class="label"></div>
  <div id="layer" class="layer"></div>
</div>
```

Replace:

```html
<div id="mini" class="mini"><div id="miniFace" class="face"></div><div id="miniTime" class="time"></div><div id="miniLabel" class="label"></div></div>
```

with:

```html
<div id="mini" class="mini"><div id="miniFace" class="face"></div><div id="miniBelow" class="below"></div><div id="miniTime" class="time"></div><div id="miniLabel" class="label"></div><div id="miniLayer" class="layer"></div></div>
```

Replace the two target definitions:

```js
  var MAIN = { clock: elClock, face: $('face'), time: $('time'), label: $('label'), gid: 'shMain', bigTime: '26vmin', key: null };
  var MINI = { clock: $('mini'), face: $('miniFace'), time: $('miniTime'), label: $('miniLabel'), gid: 'shMini', bigTime: '56px', key: null, overlay: true };
```

with:

```js
  var MAIN = { clock: elClock, face: $('face'), below: $('below'), time: $('time'), label: $('label'), layer: $('layer'), gid: 'shMain', bigTime: '26vmin', keys: {} };
  var MINI = { clock: $('mini'), face: $('miniFace'), below: $('miniBelow'), time: $('miniTime'), label: $('miniLabel'), layer: $('miniLayer'), gid: 'shMini', bigTime: '56px', keys: {}, overlay: true };
```

Then, anywhere in `index.html`, replace every `MAIN.key = null` with `MAIN.keys = {}` and every `MINI.key = null` with `MINI.keys = {}`:

```bash
sed -i '' 's/MAIN\.key = null/MAIN.keys = {}/g; s/MINI\.key = null/MINI.keys = {}/g' index.html
grep -n "\.key = null\|key: null" index.html   # expect no output
```

- [ ] **Step 7: Redraw each area only when its key changes**

In `paint`, replace:

```js
    var faceKey = mode + '|' + S.nightColor + '|' + S.dayColor;
    if (faceKey !== t.key) { t.face.innerHTML = faceSVG(mode, t.gid); t.key = faceKey; }
    t.clock.style.backgroundColor = bg;
    t.face.style.display = showFace ? '' : 'none';
    t.face.style.opacity = faceOp;
```

with:

```js
    drawParts(t, st, now);
    t.clock.style.backgroundColor = bg;
    t.face.style.display = showFace ? '' : 'none';
    t.face.style.opacity = faceOp;
    t.below.style.opacity = faceOp;
    t.layer.style.opacity = faceOp;
```

Directly after `paint`'s closing `}`, add:

```js
  // Night scene + extras. Each area (face, below, layer) is redrawn only when its key changes,
  // so nothing is rebuilt every tick: keys change when a setting changes, a star goes out, the hour turns or the screen is resized.
  function nightCtx(t, st, now) {
    return { color: NIGHT_COLORS[S.nightColor], gid: t.gid, frac: nightFrac(st, now), now: now.getTime(), since: st.since, until: st.until,
      scale: st.scale || 1, w: t.layer.clientWidth || 1024, h: t.layer.clientHeight || 768 };
  }
  function extrasMarkup(place, c) {
    var h = '', k;
    for (k in EXTRAS) if (EXTRAS[k].place === place && S.night.extras[k].on) h += EXTRAS[k].draw(S.night.extras[k], c);
    return h;
  }
  function drawParts(t, st, now) {
    var mode = st.mode, keys = { face: mode + '|' + S.nightColor + '|' + S.dayColor, below: '', layer: '' };
    var n = S.night, sc = SCENES[n.scene], so = n.scenes[n.scene], c = null, k;
    if (mode === 'sleep') {
      c = nightCtx(t, st, now);
      keys.face += '|' + n.scene + JSON.stringify(so);
      if (sc.layer) keys.layer = n.scene + JSON.stringify(so) + (sc.layerKey ? sc.layerKey(so, c) : '');
      for (k in EXTRAS) {
        if (!n.extras[k].on) continue;
        keys[EXTRAS[k].place] += '|' + k + JSON.stringify(n.extras[k]) + (EXTRAS[k].key ? EXTRAS[k].key(n.extras[k], c) : '');
      }
      if (keys.below) keys.below += '|' + S.nightColor;
      if (keys.layer) keys.layer += '|' + S.nightColor + '|' + c.w + 'x' + c.h;
    }
    if (keys.face !== t.keys.face) t.face.innerHTML = c ? sc.face(so, c) : faceSVG(mode, t.gid);
    if (keys.below !== t.keys.below) {
      t.below.innerHTML = keys.below ? extrasMarkup('below', c) : '';
      t.clock.className = t.clock.className.replace(/ below-on/g, '') + (keys.below ? ' below-on' : '');
    }
    if (keys.layer !== t.keys.layer) t.layer.innerHTML = keys.layer ? (sc.layer ? sc.layer(so, c) : '') + extrasMarkup('layer', c) : '';
    t.keys = keys;
  }
```

- [ ] **Step 8: Keep gradients working in the phase-change fade copy**

In `snapshot`, replace:

```js
    var ids = c.querySelectorAll('[id]');
    for (var i = 0; i < ids.length; i++) ids[i].removeAttribute('id');
    var grad = c.querySelector('radialGradient'), shade = c.querySelector('circle[fill^="url"]');
    if (grad && shade) { var gid = t.gid + 'Snap' + (++snapN); grad.setAttribute('id', gid); shade.setAttribute('fill', 'url(#' + gid + ')'); }
```

with:

```js
    // Gradients keep working under new unique ids; every other id is dropped.
    var ids = c.querySelectorAll('[id]'), map = {}, i, n = ++snapN;
    for (i = 0; i < ids.length; i++) {
      if (/Gradient$/.test(ids[i].tagName)) { map[ids[i].id] = ids[i].id + 'Snap' + n; ids[i].setAttribute('id', map[ids[i].id]); }
      else ids[i].removeAttribute('id');
    }
    var refs = c.querySelectorAll('[fill^="url"]');
    for (i = 0; i < refs.length; i++) {
      var m = /^url\(#(.+)\)$/.exec(refs[i].getAttribute('fill'));
      if (m && map[m[1]]) refs[i].setAttribute('fill', 'url(#' + map[m[1]] + ')');
    }
```

- [ ] **Step 9: Show settings before drawing the preview, so the preview can measure its size**

Replace in `openSettings`:

```js
    settingsOpen = true; stopAlarm(); unlockAudio(); renderSettings();
    pvMode = curState ? curState.mode : 'day'; MINI.keys = {}; MINI.lastMode = null; updatePreview();
    $('settings').className = 'overlay show'; $('sbody').scrollTop = keepScroll ? settingsScroll : 0;
```

with:

```js
    settingsOpen = true; stopAlarm(); unlockAudio();
    $('settings').className = 'overlay show'; // visible first: the preview measures its layer size
    renderSettings();
    pvMode = curState ? curState.mode : 'day'; MINI.keys = {}; MINI.lastMode = null; updatePreview();
    $('sbody').scrollTop = keepScroll ? settingsScroll : 0;
```

- [ ] **Step 10: Add the CSS**

After the line `  .snap { pointer-events: none; }`, add:

```css
  .clk .below { width: 60vmin; }
  .mini .below { width: 150px; }
  .below svg { width: 100%; height: auto; display: block; }
  .layer { position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; overflow: hidden; }
  .layer svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
  .clk.below-on .face { width: 58vmin; height: 58vmin; }
  .mini.below-on .face { width: 76px; height: 76px; }
  body.sim .clk.below-on .face { width: 42vmin; height: 42vmin; }
  .slow .twinkle { -webkit-animation-duration: 7s; animation-duration: 7s; }
  .slow .zz { -webkit-animation-duration: 8s; animation-duration: 8s; }
```

In the `.mini {` rule, add `position: relative;` right after `  .mini { `, so it reads `  .mini { position: relative; width: 250px; …`.

- [ ] **Step 11: Expose `nightFrac` and `repaint` to tests**

Replace:

```js
    night: { SCENES: SCENES, EXTRAS: EXTRAS, defaults: nightDefaults } };
```

with:

```js
    night: { SCENES: SCENES, EXTRAS: EXTRAS, defaults: nightDefaults },
    nightFrac: nightFrac, repaint: function () { MAIN.keys = {}; MAIN.lastMode = null; tick(); } };
```

- [ ] **Step 12: Run the render test, then everything else**

Run: `.venv/bin/python tests/test_night_render.py . tests/screenshots`
Expected: `FAILURES: none`.

Run: `tests/check_static.sh && tests/run_all.sh`
Expected: `static ok`, and every suite passes. `test_fade.py` covers the gradient renaming, and its names still start `shMainSnap`.

Open `tests/screenshots/night_classic_1024x768.png` and compare it with the look before this change. It should be identical: a red sleeping face, 2 z's and 3 stars.

- [ ] **Step 13: Commit**

```bash
git add index.html tests/test_night_render.py
git commit -m "Night animations: timing, per-area redraw, Off / Z's & stars / Breathing scenes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Night animation controls in settings

**Files:**
- Modify: `index.html`. This task touches the settings helpers (next to `swatches()`), the Night section in `renderSettings`, `wireSettings`, `pvTime`, `updatePreview` and the CSS.
- Create: `tests/test_night_ui.py`
- Modify: `REQUIREMENTS.md`

**Interfaces:**
- Consumes: `SCENES`, `EXTRAS`, `S.night` (Task 1); `paint` taking a state with `since` and `until` (Task 2).
- Produces:
  - control ids `na-scene`, `na-<scene>-<key>`, `nx-<extra>-on`, `nx-<extra>-<key>`
  - `optRow(id, opt, val)`
  - `nightSettingsHTML()`
  - `onNightControl(e)`
  - `rerenderSettings()`
  - `pvState(mode)`

- [ ] **Step 1: Write the failing UI test**

`tests/test_night_ui.py`:

```python
"""Night animation controls: built from the registry, save typed values, extras rows, preview follows."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
TOGGLE = "(id) => { var e = document.getElementById(id); e.checked = !e.checked; e.dispatchEvent(new Event('change', {bubbles: true})); }"
ACTIVE = "() => document.querySelector('#pvtabs .b:not(.g)').getAttribute('data-pv')"

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
        open_settings(p, vp)

        names = p.evaluate("() => [].map.call(document.querySelectorAll('#na-scene option'), function (o) { return o.textContent; })")
        reg = p.evaluate("() => { var S = %s.night.SCENES; return Object.keys(S).map(function (k) { return S[k].name; }); }" % H)
        check(tag + 'scene list = registry', names == reg and len(reg) >= 3, names)
        check(tag + 'classic rows inside the Night section',
              p.evaluate("() => ['na-classic-stars', 'na-classic-zz', 'na-classic-speed'].every(function (i) { return !!document.querySelector('.sec[data-pv=sleep] #' + i); })"))

        p.select_option('#na-classic-stars', label='10')
        v = p.evaluate("() => %s.S().night.scenes.classic.stars" % H)
        check(tag + 'choice saved with its type', v == 10 and isinstance(v, int), v)
        check(tag + 'preview switched to Night', p.evaluate(ACTIVE) == 'sleep')
        check(tag + 'mini shows 10 stars', p.evaluate("() => document.querySelectorAll('#miniFace .twinkle').length") == 10)

        p.evaluate("() => { document.getElementById('sbody').scrollTop = 500; }")
        p.select_option('#na-scene', 'breathing')
        check(tag + 'scene saved', p.evaluate("() => %s.S().night.scene" % H) == 'breathing')
        check(tag + 'rows swapped to breathing',
              p.evaluate("() => !!document.getElementById('na-breathing-pace') && !document.getElementById('na-classic-stars')"))
        sc = p.evaluate("() => document.getElementById('sbody').scrollTop")
        check(tag + 'scroll kept after rebuild', sc == 500, sc)

        p.select_option('#na-breathing-pace', label='8 breaths a minute')
        p.evaluate(TOGGLE, 'na-breathing-glow')
        n = p.evaluate("() => %s.S().night.scenes.breathing" % H)
        check(tag + 'breathing controls save', n == {'pace': 8, 'depth': 'medium', 'glow': False}, n)
        dur = p.evaluate("() => { var a = document.querySelector('#miniFace animateTransform'); return a && a.getAttribute('dur'); }")
        check(tag + 'mini breathing at 7.5 s', dur == '7.5s', dur)

        p.select_option('#na-scene', 'classic')
        check(tag + 'classic settings remembered',
              p.evaluate("() => document.getElementById('na-classic-stars').selectedOptions[0].textContent") == '10')
        p.select_option('#na-scene', 'off')
        check(tag + 'off has no rows', p.evaluate("() => document.querySelectorAll('[id^=na-off-]').length") == 0)

        # every registered extra: a switch; its rows only while on (later tasks' extras are picked up automatically)
        for x in p.evaluate("() => Object.keys(%s.night.EXTRAS)" % H):
            check(tag + x + ': switch shown, rows hidden while off',
                  p.evaluate("(x) => !!document.getElementById('nx-' + x + '-on') && document.querySelectorAll('[id^=nx-' + x + '-]').length === 1", x))
            p.evaluate(TOGGLE, 'nx-%s-on' % x)
            n_opts = p.evaluate("(x) => %s.night.EXTRAS[x].opts.length" % H, x)
            check(tag + x + ': turning on saves and shows its rows',
                  p.evaluate("(x) => %s.S().night.extras[x].on" % H, x) is True and
                  p.evaluate("(x) => document.querySelectorAll('[id^=nx-' + x + '-]').length", x) == n_opts + 1)

        ov = p.evaluate("() => { var w = document.getElementById('swrap'); return w.scrollWidth <= w.clientWidth + 1; }")
        check(tag + 'no horizontal overflow', ov)
        p.locator('.sec[data-pv=sleep]').scroll_into_view_if_needed()
        p.screenshot(path=os.path.join(SHOTS, 'night_settings_%dx%d.png' % vp))
        check(tag + 'no page errors', not errs, errs)
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python tests/test_night_ui.py . tests/screenshots`
Expected: `FAIL … scene list = registry`, plus a Python/Playwright error when it tries to select `#na-classic-stars`.

- [ ] **Step 3: Add the control builders and the handler**

Insert directly after the `swatches` function:

```js
  // Night animation controls, built from the registry. ids: na-scene, na-<scene>-<key>, nx-<extra>-on, nx-<extra>-<key>.
  // A choice's <option> value is its index in opt.values, so numbers stay numbers when saved.
  function optRow(id, opt, val) {
    if (opt.type === 'toggle') return '<div class="row sub"><label class="l">' + opt.label + '</label>' + sw(id, val) + '</div>';
    var h = '<div class="row sub"><label class="l">' + opt.label + '</label><select id="' + id + '">';
    for (var i = 0; i < opt.values.length; i++) h += '<option value="' + i + '"' + (opt.values[i][0] === val ? ' selected' : '') + '>' + opt.values[i][1] + '</option>';
    return h + '</select></div>';
  }
  function nightSettingsHTML() {
    var n = S.night, so = SCENES[n.scene].opts, k, i;
    var h = '<h3>Animation</h3><div class="row"><label class="l">Scene</label><select id="na-scene">';
    for (k in SCENES) h += '<option value="' + k + '"' + (k === n.scene ? ' selected' : '') + '>' + SCENES[k].name + '</option>';
    h += '</select></div>';
    for (i = 0; i < so.length; i++) h += optRow('na-' + n.scene + '-' + so[i].key, so[i], n.scenes[n.scene][so[i].key]);
    if (Object.keys(EXTRAS).length) h += '<h3>Extras</h3>';
    for (k in EXTRAS) {
      var x = n.extras[k], xo = EXTRAS[k].opts;
      h += '<div class="row"><label class="l">' + EXTRAS[k].name + '</label>' + sw('nx-' + k + '-on', x.on) + '</div>';
      if (x.on) for (i = 0; i < xo.length; i++) h += optRow('nx-' + k + '-' + xo[i].key, xo[i], x[xo[i].key]);
    }
    return h;
  }
  function optByKey(opts, key) { for (var i = 0; i < opts.length; i++) if (opts[i].key === key) return opts[i]; return null; }
  function rerenderSettings() { var y = $('sbody').scrollTop; renderSettings(); $('sbody').scrollTop = y; }
  function onNightControl(e) {
    var el = e.target, p = el.id.split('-');
    if (el.id === 'na-scene') { S.night.scene = el.value; save(); rerenderSettings(); return; }
    var isScene = p[0] === 'na', reg = isScene ? SCENES[p[1]] : EXTRAS[p[1]], store = isScene ? S.night.scenes[p[1]] : S.night.extras[p[1]];
    if (p[2] === 'on') { store.on = el.checked; save(); rerenderSettings(); return; }
    var opt = optByKey(reg.opts, p[2]);
    store[p[2]] = opt.type === 'toggle' ? el.checked : opt.values[+el.value][0];
    save();
  }
```

- [ ] **Step 4: Put the controls in the Night section and wire them up**

In `renderSettings`, replace the end of the Night section:

```js
      '<div class="row"><label class="l">Noise volume</label><input type="range" min="5" max="100" step="5" id="noiseVol" value="' + S.noiseVol + '"><span class="val" id="noiseVolV">' + S.noiseVol + '%</span></div></div>';
```

with:

```js
      '<div class="row"><label class="l">Noise volume</label><input type="range" min="5" max="100" step="5" id="noiseVol" value="' + S.noiseVol + '"><span class="val" id="noiseVolV">' + S.noiseVol + '%</span></div>' +
      nightSettingsHTML() + '</div>';
```

In `wireSettings`, find the line that starts with:

```js
    ['napSound', 'dayMode'].forEach(
```

and insert **before** it (`i` is already declared earlier in `wireSettings`):

```js
    var nc = w.querySelectorAll('[id^="na-"], [id^="nx-"]');
    for (i = 0; i < nc.length; i++) nc[i].addEventListener('change', onNightControl);
```

(The `change` event bubbles on to `#sbody`, where `pvFollow` switches the preview to the Night tab via the section's `data-pv="sleep"`. That still works after the handler rebuilds the settings, because the bubbling path is fixed when the event is dispatched.)

- [ ] **Step 5: Show a half-finished night in the preview**

Replace:

```js
    if (mode === 'sleep') return at(now, c.bed);
```

(in `pvTime`) with:

```js
    if (mode === 'sleep') { var ns = pvState('sleep'); return new Date((ns.since + ns.until) / 2); } // middle of tonight
```

Directly before `function pvTime`, add:

```js
  // The preview's night is tonight (today's bedtime to tomorrow's wake), so the countdown shows half its stars.
  function pvState(mode) {
    if (mode !== 'sleep') return { mode: mode };
    var now = new Date(), tmr = new Date(now.getTime()); tmr.setDate(tmr.getDate() + 1);
    return { mode: 'sleep', since: at(now, S.days[now.getDay()].bed).getTime(), until: at(tmr, S.days[tmr.getDay()].wake).getTime() };
  }
```

In `updatePreview`, replace:

```js
    paint(MINI, pvTime(pvMode), { mode: pvMode }, S.fadeSec * 1000);
```

with:

```js
    paint(MINI, pvTime(pvMode), pvState(pvMode), S.fadeSec * 1000);
```

- [ ] **Step 6: Add the CSS**

Directly after the `.dot { … }` rule, add:

```css
  .sec h3 { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: #8a8f9c; margin: 16px 0 2px; font-weight: 600; }
  .row.sub { padding-left: 18px; }
  .row.sub label.l { color: #b9bdc7; }
```

- [ ] **Step 7: Run the UI test, then everything else**

Run: `.venv/bin/python tests/test_night_ui.py . tests/screenshots`
Expected: `FAILURES: none`.

Run: `tests/check_static.sh && tests/run_all.sh`
Expected: `static ok`, and every suite passes.

- [ ] **Step 8: Document stage 1**

In `REQUIREMENTS.md`, insert this before `### Settings layout (v1.3)`:

```markdown
### Night animations (v1.4)
- Only during the night (sleep) phase, including naps. The design is in `docs/superpowers/specs/2026-09-26-night-animations-design.md`.
- **Scene** (choose one): Off, Z's & stars (default, same look as before), Breathing. Each scene keeps its own settings.
- The controls are built from the `SCENES` / `EXTRAS` registry in `index.html`. Saved values are checked against it, and unknown or invalid ones fall back to the defaults.
- Each paint target has three areas: face, `.below` and `.layer`. Each is redrawn only when its key changes, never on every tick.
- `computeState()` sleep states carry `since`: tonight's bedtime, yesterday's bedtime from yesterday's schedule, or the nap start. `nightFrac()` goes from 0 at bedtime to 1 at wake.
```

- [ ] **Step 9: Commit**

```bash
git add index.html tests/test_night_ui.py REQUIREMENTS.md
git commit -m "Night animations: settings controls built from the registry

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Stage 2: sky and extras

### Task 4: Moon & sky scene

**Files:**
- Modify: `index.html`. Add a registry entry, `rng`, `sceneMoon` and `skyLayer`.
- Modify: `tests/test_night_render.py`. Add the moon checks.

**Interfaces:**
- Consumes: registry, `drawParts` with a scene's `layer`, `ctx`, `SVG_OPEN` (Task 2).
- Produces: `rng(seed) -> function () -> [0, 1)` (reused in Tasks 6 and 8), `sceneMoon(o, c)`, `skyLayer(o, c)`.

- [ ] **Step 1: Add the failing moon checks**

In `tests/test_night_render.py`, insert directly **before** the line `        # night brightness reaches every area`:

```python
        # moon & sky
        p.evaluate("() => %s.setS({night: {scene: 'moon'}})" % H)
        p.clock.run_for(1100)
        sky = p.evaluate("""() => { var l = document.getElementById('layer');
            return { stars: l.querySelectorAll('circle').length, anim: [].map.call(l.querySelectorAll('animate'), function (a) { return a.getAttribute('dur'); }),
                     pos: [].map.call(l.querySelectorAll('circle'), function (c) { return [parseFloat(c.getAttribute('cx')), parseFloat(c.getAttribute('cy'))]; }),
                     face: document.querySelectorAll('#face path').length }; }""")
        check(tag + 'moon default: 25 sky stars, slow twinkle, face', sky['stars'] == 25 and sky['anim'] == ['7s', '9s', '11s'] and sky['face'] == 2, sky['anim'])
        check(tag + 'sky stars keep clear of moon and time', all(not (22 < x < 78 and 8 < y < 88) for x, y in sky['pos']))
        p.evaluate("() => %s.setS({nightDim: 30, night: {scene: 'moon', scenes: {moon: {sky: 50, twinkle: 'off', face: false}}}})" % H)
        p.clock.run_for(1100)
        sky = p.evaluate("() => { var l = document.getElementById('layer'); return [l.querySelectorAll('circle').length, l.querySelectorAll('animate').length, document.querySelectorAll('#face path').length, l.style.opacity]; }")
        check(tag + 'moon 50 stars, no twinkle, no face, dimmed', sky == [50, 0, 0, '0.3'], sky)
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python tests/test_night_render.py . tests/screenshots`
Expected: `FAIL … moon default…`. `moon` isn't registered yet, so `setS` falls back to classic.

- [ ] **Step 3: Implement**

Add the registry entry after the `breathing` entry (keep the comma after breathing's closing `] }`):

```js
    moon: { name: 'Moon & sky', face: sceneMoon, layer: skyLayer, opts: [
      { key: 'sky', label: 'Sky stars', type: 'choice', values: [[10, '10'], [25, '25'], [50, '50']], def: 25 },
      { key: 'twinkle', label: 'Twinkle', type: 'choice', values: [['off', 'Off'], ['slow', 'Slow'], ['normal', 'Normal']], def: 'slow' },
      { key: 'face', label: 'Sleepy face on the moon', type: 'toggle', def: true }
    ] }
```

After `sceneBreathing`, add:

```js
  // Small seeded random generator (mulberry32), so stars and paths stay put when an area is redrawn.
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function sceneMoon(o, c) {
    var dark = 'rgba(0,0,0,.72)';
    var h = SVG_OPEN +
      '<defs><radialGradient id="' + c.gid + '" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#000" stop-opacity=".12"/></radialGradient></defs>' +
      '<circle cx="100" cy="100" r="92" fill="' + c.color + '"/><circle cx="100" cy="100" r="92" fill="url(#' + c.gid + ')"/>' +
      '<circle cx="148" cy="72" r="84" fill="#000"/>'; // bite out of the moon (the night background is always black)
    if (o.face) h += '<path d="M34 104 Q44 114 54 104" fill="none" stroke="' + dark + '" stroke-width="6" stroke-linecap="round"/>' +
      '<path d="M44 146 Q54 154 66 148" fill="none" stroke="' + dark + '" stroke-width="5" stroke-linecap="round"/>';
    return h + '</svg>';
  }
  var TWINKLE_DUR = { slow: [7, 9, 11], normal: [3.5, 4.5, 5.5] };
  // Sky stars in 3 groups that share one twinkle each (cheap on the iPad mini 2). Positions in %, so no stretching.
  function skyLayer(o, c) {
    var r = rng(o.sky * 7919), groups = ['', '', ''], i, x, y;
    for (i = 0; i < o.sky; i++) {
      do { x = r() * 100; y = r() * 100; } while (x > 22 && x < 78 && y > 8 && y < 88); // keep clear of the moon and the time
      groups[i % 3] += '<circle cx="' + x.toFixed(1) + '%" cy="' + y.toFixed(1) + '%" r="' + (1 + r() * 1.4).toFixed(1) + '"/>';
    }
    var h = '<svg xmlns="http://www.w3.org/2000/svg"><g fill="' + c.color + '">';
    for (i = 0; i < 3; i++) h += '<g opacity=".8">' + (o.twinkle === 'off' ? '' :
      '<animate attributeName="opacity" values=".25;1;.25" dur="' + TWINKLE_DUR[o.twinkle][i] + 's" begin="' + (i * 1.3).toFixed(1) + 's" repeatCount="indefinite"/>') + groups[i] + '</g>';
    return h + '</g></svg>';
  }
```

- [ ] **Step 4: Run the render test, then everything else**

Run: `.venv/bin/python tests/test_night_render.py . tests/screenshots`
Expected: `FAILURES: none`. The scene loop now also covers `moon` (face, ids, no redraw between ticks, screenshot).
Run: `tests/check_static.sh && tests/run_all.sh`
Expected: everything passes. `test_night_ui.py` also sees the new scene in the list.

Look at `tests/screenshots/night_moon_1024x768.png` and `night_moon_768x1024.png`. You should see a crescent with a sleepy face, and stars around the edges, not behind the moon or the time.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_night_render.py
git commit -m "Night animations: Moon & sky scene

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Star countdown

**Files:**
- Modify: `index.html`. Add an `EXTRAS.countdown` entry, `countdownLit`, `starPath`, `drawCountdown`, and an entry in the test hook.
- Create: `tests/test_night_extras.py`

**Interfaces:**
- Consumes: `.below` area and `extra.key` (Task 2); `pvState` midpoint (Task 3); `sim` (existing: `startSim`, `simStep`).
- Produces:
  - `countdownLit(n, frac) -> int`
  - `starPath(cx, cy, r) -> path d`
  - `drawCountdown(o, c)`
  - star markers `data-star="lit" | "gone" | "going"`
  - test hook `night.countdownLit`

- [ ] **Step 1: Write the failing extras test (countdown part)**

`tests/test_night_extras.py`:

```python
"""Night extras: star countdown maths and drawing (fireflies and shooting stars are added in Task 6)."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
LIT = "(root) => ['lit', 'gone', 'going'].map(function (k) { return document.querySelectorAll(root + ' [data-star=' + k + ']').length; })"
DUP_IDS = "() => { var seen = {}, d = []; [].forEach.call(document.querySelectorAll('[id]'), function (e) { if (seen[e.id]) d.push(e.id); seen[e.id] = 1; }); return d; }"


def at(p, *a):
    p.clock.set_system_time(datetime.datetime(*a))
    p.clock.run_for(1100)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={'width': 1024, 'height': 768})
    errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.clock.install(time=datetime.datetime(2026, 9, 23, 18, 0, 0))  # Wednesday
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(300)

    def lit(n, f):
        return p.evaluate("([n, f]) => %s.night.countdownLit(n, f)" % H, [n, f])

    got = [lit(8, 0), lit(8, 0.5), lit(8, 0.99999), lit(8, 1), lit(5, 0.5), lit(12, 1 / 12), lit(8, -1), lit(8, 2)]
    check('countdownLit maths', got == [8, 4, 1, 0, 3, 11, 8, 0], got)

    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp
        p.set_viewport_size({'width': vp[0], 'height': vp[1]})
        p.evaluate("() => %s.setS({showTimeNight: true, night: {extras: {countdown: {on: true}}}})" % H)
        at(p, 2026, 9, 23, 19, 0, 0)
        check(tag + 'bedtime: all 8 lit', p.evaluate(LIT, '#below') == [8, 0, 0], p.evaluate(LIT, '#below'))
        check(tag + 'face shrinks to make room', 'below-on' in p.evaluate("() => document.getElementById('clock').className"))
        fits = p.evaluate("() => document.getElementById('time').getBoundingClientRect().bottom <= window.innerHeight")
        check(tag + 'face, countdown and time fit on screen', fits)
        at(p, 2026, 9, 24, 1, 0, 0)
        check(tag + 'middle of the night: 4 lit, 4 gone, 1 going out', p.evaluate(LIT, '#below') == [4, 4, 1], p.evaluate(LIT, '#below'))
        check(tag + 'fade: going star fades over 3 s',
              p.evaluate("() => { var a = document.querySelector('#below [data-star=going] animate'); return a && a.getAttribute('dur'); }") == '3s')
        p.screenshot(path=os.path.join(SHOTS, 'countdown_arc_%dx%d.png' % vp))
        at(p, 2026, 9, 24, 1, 10, 0)
        p.evaluate("() => { window.__b = document.querySelector('#below svg'); }")
        p.clock.run_for(60000)
        check(tag + 'no redraw while no star goes out', p.evaluate("() => window.__b === document.querySelector('#below svg')"))
        at(p, 2026, 9, 24, 6, 59, 0)
        check(tag + 'just before wake: 1 lit', p.evaluate(LIT, '#below')[0] == 1, p.evaluate(LIT, '#below'))
        at(p, 2026, 9, 24, 7, 1, 0)
        check(tag + 'green: countdown gone', p.evaluate("() => document.getElementById('below').innerHTML") == '' and
              'below-on' not in p.evaluate("() => document.getElementById('clock').className"))

        p.evaluate("() => %s.setS({night: {extras: {countdown: {on: true, count: 12, layout: 'row', out: 'pop'}}}})" % H)
        at(p, 2026, 9, 24, 19, 0, 0)
        check(tag + '12 stars at bedtime', p.evaluate(LIT, '#below') == [12, 0, 0], p.evaluate(LIT, '#below'))
        at(p, 2026, 9, 25, 1, 0, 0)
        ys = p.evaluate("() => [].map.call(document.querySelectorAll('#below [data-star=lit], #below [data-star=gone]'), function (e) { var b = e.getBBox(); return Math.round(b.y + b.height / 2); })")
        check(tag + 'row layout: all on one line', len(set(ys)) == 1, set(ys))
        check(tag + 'pop: going star shrinks', p.evaluate("() => !!document.querySelector('#below [data-star=going] animateTransform')"))
        p.screenshot(path=os.path.join(SHOTS, 'countdown_row_%dx%d.png' % vp))

        # nap: counts from nap start to nap end
        at(p, 2026, 9, 25, 13, 0, 0)
        p.evaluate("() => { var t = Date.now(); %s.setS({night: {extras: {countdown: {on: true}}}, nap: {start: t, end: t + 45 * 60000}}); }" % H)
        p.clock.run_for(1100)
        check(tag + 'nap start: all lit', p.evaluate(LIT, '#below')[0] == 8, p.evaluate(LIT, '#below'))
        p.clock.run_for(int(22.5 * 60000))
        check(tag + 'nap half-way: 4 lit', p.evaluate(LIT, '#below')[0] == 4, p.evaluate(LIT, '#below'))
        p.evaluate("() => %s.setS({night: {extras: {countdown: {on: true}}}})" % H)

        # preview shows a half-finished night
        open_settings(p, vp)
        p.click('#pvtabs [data-pv="sleep"]')
        check(tag + 'mini: half the stars lit', p.evaluate(LIT, '#miniBelow')[0] == 4, p.evaluate(LIT, '#miniBelow'))
        check(tag + 'no duplicate ids', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))

        # simulation: stars go out as pretend time passes
        p.click('#simBtn')
        seen = []
        for _ in range(620):
            p.clock.run_for(100)
            s = p.evaluate("() => { var s = %s.sim(); return s ? s.mode : null; }" % H)
            if s == 'sleep':
                seen.append(p.evaluate(LIT, '#below')[0])
        after_bed = seen[seen.index(8):] if 8 in seen else []
        check(tag + 'sim: 8 at bedtime, then only goes down',
              bool(after_bed) and all(a >= b for a, b in zip(after_bed, after_bed[1:])) and after_bed[-1] <= 2, after_bed[:3] + ['…'] + after_bed[-3:])
        p.clock.run_for(6000)  # simulation ends and returns to settings
        p.click('#done')
    check('no page errors', not errs, errs)
    b.close()
srv.shutdown()
sys.exit(check.finish())
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python tests/test_night_extras.py . tests/screenshots`
Expected: a Python/JS error, because `countdownLit` isn't defined yet.

- [ ] **Step 3: Implement**

Replace the empty extras registry:

```js
  var EXTRAS = {
  };
```

with:

```js
  var EXTRAS = {
    countdown: { name: 'Star countdown', place: 'below', draw: drawCountdown, key: function (o, c) { return countdownLit(o.count, c.frac); }, opts: [
      { key: 'count', label: 'Number of stars', type: 'choice', values: [[5, '5'], [8, '8'], [10, '10'], [12, '12']], def: 8 },
      { key: 'layout', label: 'Layout', type: 'choice', values: [['arc', 'Arc'], ['row', 'Row']], def: 'arc' },
      { key: 'out', label: 'How a star goes out', type: 'choice', values: [['fade', 'Fade'], ['pop', 'Pop']], def: 'fade' }
    ] }
  };
```

After `skyLayer`, add:

```js
  // ---------- night extras ----------
  // Stars still lit: all at bedtime, none at wake, going out at equal steps.
  function countdownLit(n, frac) { return Math.max(0, Math.min(n, Math.ceil(n * (1 - frac)))); }
  function starPath(cx, cy, r) {
    var d = '', i;
    for (i = 0; i < 10; i++) {
      var a = Math.PI / 5 * i - Math.PI / 2, rr = i % 2 ? r * 0.45 : r;
      d += (i ? 'L' : 'M') + (cx + rr * Math.cos(a)).toFixed(1) + ' ' + (cy + rr * Math.sin(a)).toFixed(1);
    }
    return d + 'Z';
  }
  // Lit stars on the left, gone ones as faint outlines; only the star that just went out animates.
  function drawCountdown(o, c) {
    var n = o.count, lit = countdownLit(n, c.frac), r = Math.min(13, 250 / n / 2.1), h = '', i;
    for (i = 0; i < n; i++) {
      var f = n === 1 ? 0.5 : i / (n - 1), x = 20 + 260 * f, y = o.layout === 'row' ? 30 : 48 - 30 * Math.sin(Math.PI * f), d = starPath(x, y, r);
      if (i < lit) { h += '<path data-star="lit" d="' + d + '" fill="' + c.color + '"/>'; continue; }
      h += '<path data-star="gone" d="' + d + '" fill="none" stroke="' + c.color + '" stroke-width="1.5" opacity=".15"/>';
      if (i !== lit) continue;
      h += o.out === 'pop'
        ? '<g data-star="going" transform="translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ')"><g transform="scale(0)">' +
          '<animateTransform attributeName="transform" type="scale" values="1;1.3;0" dur=".5s" fill="freeze"/><path d="' + starPath(0, 0, r) + '" fill="' + c.color + '"/></g></g>'
        : '<path data-star="going" d="' + d + '" fill="' + c.color + '" opacity="0"><animate attributeName="opacity" values="1;0" dur="3s" fill="freeze"/></path>';
    }
    return '<svg viewBox="0 0 300 64" xmlns="http://www.w3.org/2000/svg">' + h + '</svg>';
  }
```

Test hook: replace `    night: { SCENES: SCENES, EXTRAS: EXTRAS, defaults: nightDefaults },` with:

```js
    night: { SCENES: SCENES, EXTRAS: EXTRAS, defaults: nightDefaults, countdownLit: countdownLit },
```

- [ ] **Step 4: Run the extras test, then everything else**

Run: `.venv/bin/python tests/test_night_extras.py . tests/screenshots`
Expected: `FAILURES: none`.
Run: `tests/check_static.sh && tests/run_all.sh`
Expected: everything passes. `test_night_settings.py` now also checks the countdown default, and `test_night_ui.py` checks its switch and rows.

Look at `tests/screenshots/countdown_arc_*.png`: a small arc of stars under a smaller face, with the right half as faint outlines.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_night_extras.py
git commit -m "Night animations: star countdown

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Fireflies and shooting stars

**Files:**
- Modify: `index.html`. Add the `EXTRAS.fireflies` and `EXTRAS.shooting` entries, `loopPath`, `drawFireflies`, `shootingTimes` and `drawShooting`; set `st.scale` in `simStep`; add a test hook entry.
- Modify: `tests/test_night_extras.py`
- Modify: `REQUIREMENTS.md`

**Interfaces:**
- Consumes: `rng` (Task 4), `ctx.w/h/scale/since/until/now` (Task 2), `.layer` redraw key including `w×h` (Task 2).
- Produces:
  - `shootingTimes(o, since, from, to) -> [ms]` (strictly increasing)
  - `drawFireflies(o, c)`
  - `drawShooting(o, c)`
  - markers `data-shoot="<ms>"`
  - test hook `night.shootingTimes`

- [ ] **Step 1: Add the failing checks**

In `tests/test_night_extras.py`, insert directly before the final `    check('no page errors', not errs, errs)`:

```python
    # ---- fireflies ----
    p.set_viewport_size({'width': 1024, 'height': 768})
    p.evaluate("() => %s.setS({night: {extras: {fireflies: {on: true}}}})" % H)
    at(p, 2026, 9, 26, 22, 0, 0)
    ff = p.evaluate("""() => [].map.call(document.querySelectorAll('#layer circle'), function (c) {
        var m = c.querySelector('animateMotion'); return { fill: c.getAttribute('fill'), dur: m && parseFloat(m.getAttribute('dur')), path: m && m.getAttribute('path') }; })""")
    check('fireflies default: 5, night colour, very slow',
          len(ff) == 5 and all(f['fill'] == '#ff3b1f' and 40 <= f['dur'] <= 70 for f in ff), ff[:1])

    def path_max(fl):
        nums = [float(v) for f in fl for v in f['path'].replace('M', ' ').replace('Q', ' ').split()]
        return max(nums[0::2]), max(nums[1::2])

    mx, my = path_max(ff)
    check('firefly paths inside the screen', mx <= 1024 and my <= 768, (mx, my))
    p.evaluate("() => { window.__l = document.querySelector('#layer svg'); }")
    p.clock.run_for(5000)
    check('fireflies: no redraw between ticks', p.evaluate("() => window.__l === document.querySelector('#layer svg')"))
    p.evaluate("() => %s.repaint()" % H)
    p.clock.run_for(200)
    same = p.evaluate("() => [].map.call(document.querySelectorAll('#layer animateMotion'), function (m) { return m.getAttribute('path'); })")
    check('fireflies: same paths after a redraw', same == [f['path'] for f in ff])
    p.set_viewport_size({'width': 768, 'height': 1024})
    p.clock.run_for(1100)
    ff2 = p.evaluate("() => [].map.call(document.querySelectorAll('#layer circle'), function (c) { return { path: c.querySelector('animateMotion').getAttribute('path') }; })")
    mx, my = path_max(ff2)
    check('rotated: fireflies redrawn for the new size', mx <= 768 and my <= 1024 and ff2 != [{'path': f['path']} for f in ff], (mx, my))
    p.evaluate("() => %s.setS({nightDim: 20, night: {extras: {fireflies: {on: true, count: 8, speed: 'slow', color: 'warm'}}}})" % H)
    p.clock.run_for(1100)
    ff = p.evaluate("() => [].map.call(document.querySelectorAll('#layer circle'), function (c) { return [c.getAttribute('fill'), parseFloat(c.querySelector('animateMotion').getAttribute('dur'))]; })")
    check('fireflies 8, warm, slow', len(ff) == 8 and all(f[0] == '#ffd27a' and 20 <= f[1] <= 35 for f in ff), ff[:1])
    check('fireflies dimmed with the night', p.evaluate("() => document.getElementById('layer').style.opacity") == '0.2')
    p.screenshot(path=os.path.join(SHOTS, 'fireflies_768x1024.png'))

    # ---- shooting stars ----
    def ms(*a):
        return int(datetime.datetime(*a).timestamp() * 1000)

    since = ms(2026, 9, 26, 19, 0)

    def times(o, frm, to):
        return p.evaluate("([o, s, f, t]) => %s.night.shootingTimes(o, s, f, t)" % H, [o, since, frm, to])

    t1 = times({'every': 5, 'firstHour': True}, since, since + 6 * 3600000)
    gaps = [b_ - a_ for a_, b_ in zip([since] + t1, t1)]
    check('first hour only: 10–13 times, all within the hour', 10 <= len(t1) <= 13 and all(since < t <= since + 3600000 for t in t1), len(t1))
    check('spacing 5 min ± 30 % (gaps 2–8 min)', all(0.4 * 300000 <= g <= 1.6 * 300000 for g in gaps[1:]), [round(g / 60000, 1) for g in gaps])
    check('same inputs, same times', t1 == times({'every': 5, 'firstHour': True}, since, since + 6 * 3600000))
    t2 = times({'every': 10, 'firstHour': False}, since, since + 6 * 3600000)
    check('all night when not first hour only', max(t2) > since + 5 * 3600000 and 30 <= len(t2) <= 37, len(t2))
    check('window respected', all(since + 3600000 <= t < since + 7200000 for t in times({'every': 2, 'firstHour': False}, since + 3600000, since + 7200000)))

    p.evaluate("() => %s.setS({night: {extras: {shooting: {on: true, every: 2}}}})" % H)
    at(p, 2026, 9, 26, 19, 10, 0)
    now = ms(2026, 9, 26, 19, 10, 1)
    shots = p.evaluate("() => [].map.call(document.querySelectorAll('#layer [data-shoot]'), function (g) { return [+g.getAttribute('data-shoot'), parseFloat(g.querySelector('animate').getAttribute('begin'))]; })")
    expect = times({'every': 2, 'firstHour': True}, now - 1000, since + 3600000 + 60000)
    check('drawn shooting stars = scheduled ones this hour', [s[0] for s in shots] == expect, (len(shots), len(expect)))
    check('each starts at its time', all(abs(s[1] - (s[0] - now) / 1000) < 2 for s in shots))
    p.evaluate("() => { window.__l = document.querySelector('#layer svg'); }")
    p.clock.run_for(60000)
    check('shooting: no redraw within the hour', p.evaluate("() => window.__l === document.querySelector('#layer svg')"))
    at(p, 2026, 9, 26, 21, 0, 0)
    check('none after the first hour', p.evaluate("() => document.querySelectorAll('#layer [data-shoot]').length") == 0)
    check('no duplicate ids with all extras', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))

    # simulation: begin times use the sped-up clock
    p.evaluate("() => %s.setS({night: {extras: {shooting: {on: true, every: 2, firstHour: false}}}})" % H)
    open_settings(p, (768, 1024))
    p.click('#simBtn')
    begins = []
    for _ in range(300):
        p.clock.run_for(100)
        begins += p.evaluate("() => [].map.call(document.querySelectorAll('#layer [data-shoot] animate'), function (a) { return parseFloat(a.getAttribute('begin')); })")
    check('sim: shooting stars scheduled in sped-up time', bool(begins) and max(begins) < 3, max(begins) if begins else None)
    p.click('#simExit')
    p.click('#done')
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python tests/test_night_extras.py . tests/screenshots`
Expected: the countdown checks still `PASS`; `FAIL fireflies default…`; then an error at `shootingTimes`.

- [ ] **Step 3: Implement**

In the `EXTRAS` literal, after the `countdown` entry's `] }`, add a comma and:

```js
    fireflies: { name: 'Fireflies', place: 'layer', draw: drawFireflies, opts: [
      { key: 'count', label: 'How many', type: 'choice', values: [[3, '3'], [5, '5'], [8, '8']], def: 5 },
      { key: 'speed', label: 'Speed', type: 'choice', values: [['vslow', 'Very slow'], ['slow', 'Slow']], def: 'vslow' },
      { key: 'color', label: 'Colour', type: 'choice', values: [['night', 'Match night colour'], ['warm', 'Warm yellow']], def: 'night' }
    ] },
    shooting: { name: 'Shooting star', place: 'layer', draw: drawShooting, key: function (o, c) { return Math.floor((c.now - c.since) / 3600000); }, opts: [
      { key: 'every', label: 'How often', type: 'choice', values: [[2, 'Every 2 minutes'], [5, 'Every 5 minutes'], [10, 'Every 10 minutes']], def: 5 },
      { key: 'firstHour', label: 'Only in the first hour after bedtime', type: 'toggle', def: true }
    ] }
```

After `drawCountdown`, add:

```js
  var FIREFLY_DUR = { vslow: [40, 70], slow: [20, 35] };
  // A smooth closed loop through 4 random points (quadratic curves between midpoints), in pixels.
  function loopPath(r, w, h) {
    var p = [], d, i;
    for (i = 0; i < 4; i++) p.push([r() * w, r() * h]);
    function mid(a, b) { return ((a[0] + b[0]) / 2).toFixed(0) + ' ' + ((a[1] + b[1]) / 2).toFixed(0); }
    d = 'M' + mid(p[0], p[1]);
    for (i = 1; i <= 4; i++) d += ' Q' + p[i % 4][0].toFixed(0) + ' ' + p[i % 4][1].toFixed(0) + ' ' + mid(p[i % 4], p[(i + 1) % 4]);
    return d;
  }
  // Seeded per night, so a redraw (e.g. a setting change) keeps the same paths; the layer key includes the size, so turning the iPad redraws them.
  function drawFireflies(o, c) {
    var r = rng(Math.floor(c.since / 60000) + o.count), col = o.color === 'warm' ? '#ffd27a' : c.color, sp = FIREFLY_DUR[o.speed], h = '', i;
    for (i = 0; i < o.count; i++) {
      var dur = (sp[0] + r() * (sp[1] - sp[0])).toFixed(0);
      h += '<circle r="3" fill="' + col + '" opacity=".6"><animate attributeName="opacity" values=".15;.9;.3;.8;.15" dur="' + (5 + r() * 4).toFixed(1) + 's" repeatCount="indefinite"/>' +
        '<animateMotion dur="' + dur + 's" repeatCount="indefinite" path="' + loopPath(r, c.w, c.h) + '"/></circle>';
    }
    return '<svg xmlns="http://www.w3.org/2000/svg">' + h + '</svg>';
  }
  // Shooting star times (ms) in [from, to): every `every` minutes after `since`, each moved by up to ±30 %.
  // The same night always gives the same times, so redraws don't reschedule them.
  function shootingTimes(o, since, from, to) {
    var step = o.every * 60000, last = o.firstHour ? since + 3600000 : Infinity, out = [], k, t;
    for (k = Math.max(1, Math.floor((from - since) / step)); ; k++) {
      t = since + (k + (rng(Math.floor(since / 60000) * 131 + k)() - 0.5) * 0.6) * step;
      if (t >= to || t > last) break;
      if (t >= from) out.push(t);
    }
    return out;
  }
  // Draws this hour's shooting stars with SMIL begin offsets; the layer key changes each hour, so the next hour is drawn then.
  // c.scale is real ms per pretend ms (1 normally, much smaller in the day simulation).
  function drawShooting(o, c) {
    var hourEnd = c.since + (Math.floor((c.now - c.since) / 3600000) + 1) * 3600000;
    var times = shootingTimes(o, c.since, c.now, Math.min(hourEnd + 60000, c.until || hourEnd)), h = '', i;
    for (i = 0; i < times.length; i++) {
      var r = rng(Math.floor(times[i] / 1000)), x = c.w * (0.1 + r() * 0.5), y = c.h * (0.05 + r() * 0.25);
      var begin = ((times[i] - c.now) * c.scale / 1000).toFixed(2) + 's';
      h += '<g data-shoot="' + times[i] + '" opacity="0"><animate attributeName="opacity" values="0;1;1;0" dur="1.5s" begin="' + begin + '"/>' +
        '<animateTransform attributeName="transform" type="translate" from="0 0" to="' + (c.w / 3).toFixed(0) + ' ' + (c.h / 6).toFixed(0) + '" dur="1.5s" begin="' + begin + '"/>' +
        '<line x1="' + x.toFixed(0) + '" y1="' + y.toFixed(0) + '" x2="' + (x - 46).toFixed(0) + '" y2="' + (y - 23).toFixed(0) + '" stroke="' + c.color + '" stroke-width="2" stroke-linecap="round"/></g>';
    }
    return '<svg xmlns="http://www.w3.org/2000/svg">' + h + '</svg>';
  }
```

In `simStep`, replace:

```js
    var now = new Date(sim.v), st = computeState(now, true);
```

with:

```js
    var now = new Date(sim.v), st = computeState(now, true);
    st.scale = simSpeed * 1000 / DAY_MS; // real ms per pretend ms, for timed night extras
```

Test hook: replace `countdownLit: countdownLit },` with `countdownLit: countdownLit, shootingTimes: shootingTimes },`.

- [ ] **Step 4: Run the extras test, then everything else**

Run: `.venv/bin/python tests/test_night_extras.py . tests/screenshots`
Expected: `FAILURES: none`.
Run: `tests/check_static.sh && tests/run_all.sh`
Expected: everything passes.

- [ ] **Step 5: Document stage 2**

In `REQUIREMENTS.md`, under `### Night animations (v1.4)`, replace the `**Scene**` bullet with:

```markdown
- **Scene** (choose one): Off, Z's & stars (default, same look as before), Breathing, Moon & sky. Each scene keeps its own settings.
- **Extras** (any number, all off by default):
  - **Star countdown:** stars go out one by one from bedtime (or nap start) to wake. Gone stars stay as faint outlines. In the simulation it follows the pretend clock.
  - **Fireflies:** seeded per night; redrawn when the screen size changes.
  - **Shooting star:** every 2/5/10 min ±30 %, optionally only in the first hour after bedtime. The schedule is fixed per night, so redraws don't reschedule it.
```

- [ ] **Step 6: Commit**

```bash
git add index.html tests/test_night_extras.py REQUIREMENTS.md
git commit -m "Night animations: fireflies and shooting stars

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Stage 3: animals

### Task 7: Animal drawing kit, the animal scene, and the first four animals

**Files:**
- Modify: `index.html`. Add `ANIMALS` and `ANIMAL_LIST` (placed **before** `var SCENES`), the kit helpers, `sceneAnimal`, the `SCENES.animal` entry and a test hook entry.
- Create: `tests/test_night_animals.py`

**Interfaces:**
- Consumes: registry (Task 1), `SVG_OPEN` (Task 2).
- Produces:
  - `ANIMALS = { <id>: { name, draw(c, mv) -> { back?, body, head, front? } } }`
  - `ANIMAL_LIST = [[id, name]]` (used as `values` of the `animal` option)
  - `DK`, `LT` (detail colours)
  - `kitBody(c)`, `kitHead(c, x, y, r)`, `kitEyes(x, y)`
  - `sceneAnimal(o, c)`, which outputs `<svg data-animal="<id>">` with `[data-part=body]` and `[data-move]` markers
  - test hook `night.ANIMALS`, `night.sceneAnimal`

- [ ] **Step 1: Write the failing animal test**

`tests/test_night_animals.py`:

```python
"""Sleeping animals: every animal draws, breathing + little movements settings, ids, screenshot sheet for review."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
EXPECTED = ['bunny', 'bear', 'cat', 'owl']
check = Checks()
srv, URL = serve(ROOT)
STRAY = "() => [].filter.call(document.querySelectorAll('#face [id]'), function (e) { return !(e.id.indexOf('shMain') === 0 && /Gradient$/.test(e.tagName)); }).length"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for vp in VIEWPORTS:
        tag = '%dx%d ' % vp
        p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))
        p.goto(URL)
        p.evaluate("() => localStorage.clear()")
        p.reload()
        p.clock.run_for(300)
        names = p.evaluate("() => %s.night.ANIMALS ? Object.keys(%s.night.ANIMALS) : []" % (H, H))
        check(tag + 'animals registered in order', names == EXPECTED, names)
        check(tag + 'default animal is bunny', p.evaluate("() => %s.S().night.scenes.animal && %s.S().night.scenes.animal.animal" % (H, H)) == 'bunny')
        for a in names:
            p.evaluate("(a) => %s.setS({night: {scene: 'animal', scenes: {animal: {animal: a}}}})" % H, a)
            p.clock.run_for(1100)
            info = p.evaluate("""() => { var s = document.querySelector('#face svg');
                return s ? { animal: s.getAttribute('data-animal'), breath: !!s.querySelector('[data-part=body] > animateTransform'),
                             moves: [].map.call(s.querySelectorAll('[data-move] > animateTransform'), function (m) { return m.getAttribute('dur'); }) } : null; }""")
            check(tag + a + ': drawn, breathing, rare movements',
                  info and info['animal'] == a and info['breath'] and len(info['moves']) >= 1 and set(info['moves']) == {'20s'}, info)
            check(tag + a + ': no stray ids', p.evaluate(STRAY) == 0)
            p.locator('#face').screenshot(path=os.path.join(SHOTS, 'animal_%s_%dx%d.png' % (a, vp[0], vp[1])))
        p.evaluate("() => %s.setS({night: {scene: 'animal', scenes: {animal: {animal: 'cat', breath: false, moves: 'off'}}}})" % H)
        p.clock.run_for(1100)
        check(tag + 'breathing off, movements off',
              p.evaluate("() => !document.querySelector('#face [data-part=body] > animateTransform') && !document.querySelector('#face [data-move]')"))
        p.evaluate("() => %s.setS({night: {scene: 'animal', scenes: {animal: {animal: 'cat', moves: 'normal'}}}})" % H)
        p.clock.run_for(1100)
        check(tag + 'normal movements every 8 s',
              p.evaluate("() => [].every.call(document.querySelectorAll('#face [data-move] > animateTransform'), function (m) { return m.getAttribute('dur') === '8s'; })"))
        open_settings(p, vp)
        opts = p.evaluate("() => [].map.call(document.querySelectorAll('#na-animal-animal option'), function (o) { return o.textContent; })")
        check(tag + 'settings list every animal', len(opts) == len(EXPECTED), opts)
        p.select_option('#na-animal-animal', label=opts[-1])
        check(tag + 'choosing an animal saves it', p.evaluate("() => %s.S().night.scenes.animal.animal" % H) == EXPECTED[-1])
        check(tag + 'mini shows the chosen animal', p.evaluate("() => document.querySelector('#miniFace svg').getAttribute('data-animal')") == EXPECTED[-1])
        check(tag + 'no page errors', not errs, errs)
        p.close()

    # one sheet with every animal, for a visual review
    p = b.new_page(viewport={'width': 1000, 'height': 800})
    p.clock.install(time=datetime.datetime(2026, 9, 23, 22, 0, 0))
    p.goto(URL)
    p.clock.run_for(300)
    p.evaluate("""(list) => { var N = window.__toddlerSleepTrainClock.night, d = document.createElement('div');
        d.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99;background:#000;display:flex;flex-wrap:wrap;align-content:flex-start';
        list.forEach(function (k) { var c = document.createElement('div');
          c.style.cssText = 'width:20%;padding:6px;box-sizing:border-box;color:#888;font:13px sans-serif;text-align:center';
          c.innerHTML = N.sceneAnimal({animal: k, breath: false, moves: 'off'}, {color: '#ff3b1f', gid: 'sheet' + k}) + '<div>' + k + '</div>';
          c.firstChild.style.width = '100%'; d.appendChild(c); });
        document.body.appendChild(d); }""", EXPECTED)
    p.screenshot(path=os.path.join(SHOTS, 'animals_sheet.png'))
    p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python tests/test_night_animals.py . tests/screenshots`
Expected: `FAIL … animals registered in order []`, followed by more failures or an error.

- [ ] **Step 3: Add the kit and the first four animals**

Insert directly **before** `  var SCENES = {` (it has to come first, because `SCENES.animal` uses `ANIMAL_LIST` as it's built):

```js
  // ---------- sleeping animals: one shared curled-up pose, each animal adds its own features ----------
  // draw(c, mv) returns SVG parts: back (behind), body (breathes), head, front. c = night colour;
  // DK / LT = dark / light details; mv(px, py, deg, markup) wraps a part in a little movement around px,py.
  var DK = 'rgba(0,0,0,.55)', LT = 'rgba(255,255,255,.22)';
  function kitBody(c) { return '<ellipse cx="110" cy="160" rx="92" ry="48" fill="' + c + '"/>'; }
  function kitHead(c, x, y, r) { return '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + c + '"/>'; }
  function kitEyes(x, y) { // two closed eyes centred on x,y
    return '<path d="M' + (x - 22) + ' ' + y + ' q8 8 16 0 M' + (x + 6) + ' ' + y + ' q8 8 16 0" fill="none" stroke="' + DK + '" stroke-width="5" stroke-linecap="round"/>';
  }
  var ANIMALS = {
    bunny: { name: 'Bunny', draw: function (c, mv) { return {
      back: '<ellipse cx="38" cy="78" rx="13" ry="42" fill="' + c + '" transform="rotate(-18 38 78)"/>' +
        mv(72, 110, -14, '<ellipse cx="72" cy="74" rx="13" ry="42" fill="' + c + '" transform="rotate(14 72 74)"/><ellipse cx="72" cy="78" rx="6" ry="30" fill="' + DK + '" opacity=".35" transform="rotate(14 72 78)"/>'),
      body: kitBody(c) + '<circle cx="202" cy="150" r="16" fill="' + c + '"/><circle cx="202" cy="150" r="16" fill="' + LT + '"/>',
      head: kitHead(c, 58, 140, 44) + kitEyes(58, 136) + '<ellipse cx="58" cy="156" rx="5" ry="4" fill="' + DK + '"/>'
    }; } },
    bear: { name: 'Bear', draw: function (c, mv) { return {
      back: mv(30, 108, -10, '<circle cx="24" cy="104" r="17" fill="' + c + '"/><circle cx="24" cy="104" r="8" fill="' + DK + '" opacity=".4"/>') +
        '<circle cx="92" cy="104" r="17" fill="' + c + '"/><circle cx="92" cy="104" r="8" fill="' + DK + '" opacity=".4"/>',
      body: kitBody(c) + '<ellipse cx="150" cy="176" rx="34" ry="18" fill="' + LT + '"/>',
      head: kitHead(c, 58, 140, 44) + kitEyes(58, 134) + '<ellipse cx="58" cy="158" rx="17" ry="12" fill="' + LT + '"/><ellipse cx="58" cy="153" rx="6" ry="4.5" fill="' + DK + '"/>'
    }; } },
    cat: { name: 'Cat', draw: function (c, mv) { return {
      back: '<path d="M22 124 L28 84 L52 106 Z M64 106 L88 84 L94 124 Z" fill="' + c + '"/><path d="M30 112 L32 94 L44 106 Z M72 106 L84 94 L86 112 Z" fill="' + DK + '" opacity=".35"/>',
      body: kitBody(c),
      head: kitHead(c, 58, 140, 42) + kitEyes(58, 136) + '<path d="M54 152 l4 4 4 -4 Z" fill="' + DK + '"/>' +
        '<path d="M20 152 L44 156 M20 162 L44 160 M96 152 L72 156 M96 162 L72 160" stroke="' + DK + '" stroke-width="1.5" opacity=".6"/>',
      front: mv(196, 176, 16, '<path d="M196 176 Q226 204 176 212 Q120 218 96 204" fill="none" stroke="' + c + '" stroke-width="15" stroke-linecap="round"/>')
    }; } },
    owl: { name: 'Owl', draw: function (c, mv) { return {
      back: '<path d="M-20 214 L230 214" stroke="' + DK + '" stroke-width="10" stroke-linecap="round"/>',
      body: mv(100, 200, 3, '<ellipse cx="100" cy="140" rx="66" ry="72" fill="' + c + '"/><path d="M42 130 Q30 180 66 206 M158 130 Q170 180 134 206" fill="none" stroke="' + DK + '" stroke-width="5" opacity=".45"/>' +
        '<path d="M80 150 q6 6 12 0 M108 150 q6 6 12 0 M86 170 q6 6 12 0 M102 170 q6 6 12 0 M94 188 q6 6 12 0" fill="none" stroke="' + LT + '" stroke-width="3"/>'),
      head: '<path d="M52 70 L60 34 L80 62 Z M148 70 L140 34 L120 62 Z" fill="' + c + '"/>' + kitHead(c, 100, 86, 50) +
        '<circle cx="80" cy="84" r="17" fill="' + LT + '"/><circle cx="120" cy="84" r="17" fill="' + LT + '"/>' + kitEyes(100, 84) +
        '<path d="M94 98 L106 98 L100 110 Z" fill="#e0a13a"/>' +
        '<path d="M82 212 l0 6 M92 212 l0 6 M108 212 l0 6 M118 212 l0 6" stroke="#e0a13a" stroke-width="4" stroke-linecap="round"/>'
    }; } }
  };
  var ANIMAL_LIST = [];
  for (var animalId in ANIMALS) ANIMAL_LIST.push([animalId, ANIMALS[animalId].name]);

```

In the `SCENES` literal, after the `moon` entry's `] }`, add a comma and:

```js
    animal: { name: 'Sleeping animal', face: sceneAnimal, opts: [
      { key: 'animal', label: 'Animal', type: 'choice', values: ANIMAL_LIST, def: 'bunny' },
      { key: 'breath', label: 'Breathing', type: 'toggle', def: true },
      { key: 'moves', label: 'Little movements', type: 'choice', values: [['off', 'Off'], ['rare', 'Rare'], ['normal', 'Normal']], def: 'rare' }
    ] }
```

After `skyLayer` (and before the `// ---------- night extras ----------` comment), add:

```js
  // An animal asleep: the body breathes (scaled from its bottom centre, so the belly rises), parts twitch now and then.
  function sceneAnimal(o, c) {
    var dur = o.moves === 'normal' ? 8 : 20;
    function mv(px, py, deg, part) {
      if (o.moves === 'off') return part;
      var z = '0 ' + px + ' ' + py;
      return '<g data-move="1"><animateTransform attributeName="transform" type="rotate" values="' + z + ';' + z + ';' + deg + ' ' + px + ' ' + py + ';' + z + ';' + z +
        '" keyTimes="0;.9;.93;.96;1" dur="' + dur + 's" repeatCount="indefinite"/>' + part + '</g>';
    }
    var a = ANIMALS[o.animal], p = a.draw(c.color, mv);
    var breath = !o.breath ? '' : '<animateTransform attributeName="transform" type="scale" values="1 1;1.03 1.05;1 1" keyTimes="0;.5;1" calcMode="spline" keySplines=".42 0 .58 1;.42 0 .58 1" dur="10s" repeatCount="indefinite"/>';
    return '<svg viewBox="-40 -40 280 280" xmlns="http://www.w3.org/2000/svg" data-animal="' + o.animal + '">' + (p.back || '') +
      '<g transform="translate(100 205)"><g data-part="body">' + breath + '<g transform="translate(-100 -205)">' + p.body + '</g></g></g>' +
      p.head + (p.front || '') + '</svg>';
  }
```

Test hook: replace `countdownLit: countdownLit, shootingTimes: shootingTimes },` with `countdownLit: countdownLit, shootingTimes: shootingTimes, ANIMALS: ANIMALS, sceneAnimal: sceneAnimal },`.

- [ ] **Step 4: Run the animal test, then everything else**

Run: `.venv/bin/python tests/test_night_animals.py . tests/screenshots`
Expected: `FAILURES: none`.
Run: `tests/check_static.sh && tests/run_all.sh`
Expected: everything passes. `test_night_render.py` now also loops over the `animal` scene.

Look at `tests/screenshots/animals_sheet.png`. All four should read as their animal, asleep, in red.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_night_animals.py
git commit -m "Night animations: sleeping animal scene with bunny, bear, cat, owl

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: The other ten animals

**Files:**
- Modify: `index.html`. Add `birdParts` and ten `ANIMALS` entries.
- Modify: `tests/test_night_animals.py`. Extend `EXPECTED`.

**Interfaces:**
- Consumes: `ANIMALS`, `DK`, `LT`, `kitBody`, `kitHead`, `kitEyes`, `mv` contract (Task 7).
- Produces: `birdParts(c, mv, breast, beak, legs, tail, darkBody)`, plus 10 more animal ids.

- [ ] **Step 1: Extend the expected list (so the test fails)**

In `tests/test_night_animals.py`, replace:

```python
EXPECTED = ['bunny', 'bear', 'cat', 'owl']
```

with:

```python
EXPECTED = ['bunny', 'bear', 'cat', 'owl', 'dog', 'turtle', 'hedgehog', 'chicken', 'pig', 'horse', 'cow', 'robin', 'blackbird', 'lion']
```

Run: `.venv/bin/python tests/test_night_animals.py . tests/screenshots`
Expected: `FAIL … animals registered in order` (only 4 are registered).

- [ ] **Step 2: Add the ten animals**

In `ANIMALS`, after the `owl` entry's `}; } }`, add a comma and:

```js
    dog: { name: 'Dog', draw: function (c, mv) { return {
      body: kitBody(c) + '<ellipse cx="140" cy="146" rx="26" ry="16" fill="' + DK + '" opacity=".25"/><path d="M198 150 Q222 136 214 118" fill="none" stroke="' + c + '" stroke-width="12" stroke-linecap="round"/>',
      head: kitHead(c, 58, 140, 42) + kitEyes(58, 132) + '<ellipse cx="58" cy="160" rx="18" ry="13" fill="' + LT + '"/><ellipse cx="58" cy="154" rx="7" ry="5" fill="' + DK + '"/>',
      front: mv(22, 112, 10, '<ellipse cx="18" cy="140" rx="12" ry="30" fill="' + c + '"/><ellipse cx="18" cy="140" rx="12" ry="30" fill="' + DK + '" opacity=".3"/>') +
        '<ellipse cx="98" cy="140" rx="12" ry="30" fill="' + c + '"/><ellipse cx="98" cy="140" rx="12" ry="30" fill="' + DK + '" opacity=".3"/>'
    }; } },
    turtle: { name: 'Turtle', draw: function (c, mv) { return {
      back: '<ellipse cx="72" cy="206" rx="14" ry="8" fill="' + c + '"/><ellipse cx="160" cy="206" rx="14" ry="8" fill="' + c + '"/>',
      body: '<path d="M40 196 Q46 96 120 96 Q194 96 200 196 Z" fill="' + c + '"/><path d="M40 196 Q46 96 120 96 Q194 96 200 196 Z" fill="' + DK + '" opacity=".2"/>' +
        '<path d="M84 196 L96 140 L144 140 L156 196 M96 140 L120 104 L144 140 M62 170 L96 140 M178 170 L144 140" fill="none" stroke="' + DK + '" stroke-width="4" opacity=".5"/>',
      head: mv(40, 186, -8, '<circle cx="14" cy="178" r="24" fill="' + c + '"/><path d="M2 176 q7 6 14 0" fill="none" stroke="' + DK + '" stroke-width="4" stroke-linecap="round"/>')
    }; } },
    hedgehog: { name: 'Hedgehog', draw: function (c, mv) {
      var spikes = '', i;
      for (i = 0; i < 9; i++) spikes += 'M' + (60 + i * 18) + ' ' + (130 - Math.round(Math.sin(i / 8 * Math.PI) * 20)) + ' l10 -24 l10 24 ';
      return {
        body: kitBody(c) + '<path d="' + spikes + '" fill="' + c + '"/><path d="' + spikes + '" fill="' + DK + '" opacity=".35"/><ellipse cx="130" cy="150" rx="80" ry="30" fill="' + DK + '" opacity=".25"/>',
        head: '<ellipse cx="46" cy="160" rx="40" ry="28" fill="' + c + '"/>' + kitEyes(50, 152) + mv(8, 162, 8, '<circle cx="8" cy="162" r="6" fill="' + DK + '"/>')
      };
    } },
    chicken: { name: 'Chicken', draw: function (c, mv) { return {
      back: '<path d="M170 150 Q206 96 226 118 Q214 132 222 150 Q206 148 196 166 Z" fill="' + c + '"/><path d="M-20 214 L230 214" stroke="' + DK + '" stroke-width="8" stroke-linecap="round"/>',
      body: '<ellipse cx="120" cy="160" rx="84" ry="52" fill="' + c + '"/>' + mv(120, 150, 6, '<path d="M92 150 Q130 120 176 156 Q134 190 92 150 Z" fill="' + DK + '" opacity=".25"/>'),
      head: '<circle cx="50" cy="110" r="10" fill="#ff5a4a"/><circle cx="64" cy="104" r="11" fill="#ff5a4a"/><circle cx="78" cy="110" r="9" fill="#ff5a4a"/>' +
        kitHead(c, 62, 138, 38) + kitEyes(62, 134) + '<path d="M26 142 L40 136 L40 150 Z" fill="#f2b23a"/><ellipse cx="42" cy="160" rx="6" ry="9" fill="#ff5a4a"/>'
    }; } },
    pig: { name: 'Pig', draw: function (c, mv) { return {
      body: kitBody(c) + '<path d="M200 150 q14 -6 10 -16 q-4 -10 -12 -2 q-6 8 6 10" fill="none" stroke="' + c + '" stroke-width="5" stroke-linecap="round"/>',
      head: mv(30, 110, -10, '<path d="M20 124 L26 92 L48 108 Z" fill="' + c + '"/>') + '<path d="M68 108 L90 92 L96 124 Z" fill="' + c + '"/>' +
        kitHead(c, 58, 140, 42) + kitEyes(58, 130) + '<ellipse cx="58" cy="158" rx="17" ry="12" fill="' + LT + '"/>' +
        '<ellipse cx="52" cy="158" rx="3" ry="4.5" fill="' + DK + '"/><ellipse cx="64" cy="158" rx="3" ry="4.5" fill="' + DK + '"/>'
    }; } },
    horse: { name: 'Horse', draw: function (c, mv) { return {
      back: mv(200, 150, 12, '<path d="M200 150 Q236 170 222 212" fill="none" stroke="' + c + '" stroke-width="14" stroke-linecap="round"/><path d="M200 150 Q236 170 222 212" fill="none" stroke="' + DK + '" stroke-width="14" stroke-linecap="round" opacity=".35"/>'),
      body: kitBody(c),
      head: '<path d="M70 150 Q60 96 96 84 L112 124 Z" fill="' + c + '"/><path d="M60 84 L64 62 L76 80 Z" fill="' + c + '"/>' +
        '<ellipse cx="46" cy="126" rx="26" ry="44" fill="' + c + '" transform="rotate(38 46 126)"/>' +
        '<path d="M70 86 Q96 80 110 120" fill="none" stroke="' + DK + '" stroke-width="12" stroke-linecap="round" opacity=".45"/>' +
        '<path d="M44 106 q7 6 14 0" fill="none" stroke="' + DK + '" stroke-width="4" stroke-linecap="round"/><ellipse cx="20" cy="150" rx="4" ry="3" fill="' + DK + '"/>'
    }; } },
    cow: { name: 'Cow', draw: function (c, mv) { return {
      back: '<path d="M34 104 Q22 84 30 72 M82 104 Q94 84 86 72" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="7" stroke-linecap="round"/>' +
        mv(20, 124, -12, '<ellipse cx="8" cy="126" rx="18" ry="9" fill="' + c + '"/>') + '<ellipse cx="108" cy="126" rx="18" ry="9" fill="' + c + '"/>',
      body: kitBody(c) + '<ellipse cx="128" cy="148" rx="22" ry="14" fill="' + DK + '" opacity=".3"/><ellipse cx="176" cy="172" rx="16" ry="11" fill="' + DK + '" opacity=".3"/><ellipse cx="100" cy="184" rx="12" ry="8" fill="' + DK + '" opacity=".3"/>',
      head: kitHead(c, 58, 140, 42) + kitEyes(58, 130) + '<ellipse cx="58" cy="162" rx="24" ry="14" fill="' + LT + '"/>' +
        '<ellipse cx="50" cy="162" rx="3" ry="4" fill="' + DK + '"/><ellipse cx="66" cy="162" rx="3" ry="4" fill="' + DK + '"/>'
    }; } },
    robin: { name: 'Robin', draw: function (c, mv) { return birdParts(c, mv, 'rgba(255,110,60,.85)', DK, 'rgba(60,40,30,.8)', 34, false); } },
    blackbird: { name: 'Blackbird', draw: function (c, mv) { return birdParts(c, mv, null, '#ffc400', '#ffc400', 52, true); } },
    lion: { name: 'Lion', draw: function (c, mv) {
      var mane = '', i;
      for (i = 0; i < 12; i++) mane += '<circle cx="' + (58 + Math.cos(i / 12 * Math.PI * 2) * 46).toFixed(0) + '" cy="' + (138 + Math.sin(i / 12 * Math.PI * 2) * 46).toFixed(0) + '" r="17"/>';
      return {
        back: '<g fill="' + c + '">' + mane + '</g><g fill="' + DK + '" opacity=".35">' + mane + '</g>',
        body: kitBody(c) + mv(200, 160, 14, '<path d="M200 160 Q226 150 228 126" fill="none" stroke="' + c + '" stroke-width="7" stroke-linecap="round"/><circle cx="228" cy="122" r="9" fill="' + c + '"/><circle cx="228" cy="122" r="9" fill="' + DK + '" opacity=".35"/>'),
        head: kitHead(c, 58, 138, 40) + '<circle cx="30" cy="104" r="10" fill="' + c + '"/><circle cx="86" cy="104" r="10" fill="' + c + '"/>' +
          kitEyes(58, 132) + '<ellipse cx="58" cy="156" rx="16" ry="11" fill="' + LT + '"/><path d="M52 150 l6 6 6 -6 Z" fill="' + DK + '"/>'
      };
    } }
```

Directly after `kitEyes`, add the shared bird drawing:

```js
  // Robin and blackbird: a round bird asleep on a branch. breast = colour or null; darkBody shades the whole bird.
  function birdParts(c, mv, breast, beak, legs, tail, darkBody) {
    return {
      back: '<path d="M-20 212 L230 212" stroke="' + DK + '" stroke-width="8" stroke-linecap="round"/>' +
        mv(160, 170, 8, '<path d="M160 160 L' + (170 + tail) + ' ' + (190 - tail / 3) + ' L' + (164 + tail) + ' ' + (206 - tail / 4) + ' Z" fill="' + c + '"/>'),
      body: '<ellipse cx="110" cy="146" rx="64" ry="54" fill="' + c + '"/>' + mv(118, 140, 5, '<path d="M92 134 Q140 112 172 154 Q128 176 92 134 Z" fill="' + DK + '" opacity=".25"/>'),
      head: '<circle cx="78" cy="104" r="36" fill="' + c + '"/>' +
        (darkBody ? '<ellipse cx="110" cy="146" rx="64" ry="54" fill="' + DK + '" opacity=".55"/><circle cx="78" cy="104" r="36" fill="' + DK + '" opacity=".55"/>' : '') +
        (breast ? '<ellipse cx="72" cy="146" rx="30" ry="34" fill="' + breast + '"/>' : '') +
        '<path d="M50 96 q7 6 14 0" fill="none" stroke="' + (darkBody ? '#ffc400' : DK) + '" stroke-width="4" stroke-linecap="round"/>' +
        '<path d="M42 104 L24 110 L42 114 Z" fill="' + beak + '"/>' +
        '<path d="M96 198 l0 14 M116 198 l0 14" stroke="' + legs + '" stroke-width="4" stroke-linecap="round"/>'
    };
  }
```

- [ ] **Step 3: Run the animal test, then everything else**

Run: `.venv/bin/python tests/test_night_animals.py . tests/screenshots`
Expected: `FAILURES: none`.
Run: `tests/check_static.sh && tests/run_all.sh`
Expected: everything passes.

- [ ] **Step 4: Commit**

```bash
git add index.html tests/test_night_animals.py
git commit -m "Night animations: dog, turtle, hedgehog, chicken, pig, horse, cow, robin, blackbird, lion

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Docs, version, and the visual review gate

**Files:**
- Modify: `index.html` (version), `REQUIREMENTS.md`, `tests/README.md`

- [ ] **Step 1: Bump the version**

Replace `  var VERSION = '1.3';` with `  var VERSION = '1.4';`.

- [ ] **Step 2: Finish `REQUIREMENTS.md`**

Under `### Night animations (v1.4)`, replace the `**Scene**` bullet with:

```markdown
- **Scene** (choose one): Off, Z's & stars (default, same look as before), Breathing, Moon & sky, Sleeping animal. Each scene keeps its own settings.
- **Sleeping animal:** 14 animals (bunny, bear, cat, owl, dog, turtle, hedgehog, chicken, pig, horse, cow, robin, blackbird, lion). They share one drawing style (`kitBody`, `kitHead`, `kitEyes`, `birdParts`), use the night colour, and appear **at night only**. Settings: breathing on/off, little movements off / rare (every 20 s) / normal (every 8 s).
```

In `## 7. Testing approach used so far`, add:

```markdown
- (v1.4) Night animations:
  - `test_night_settings`: storage and validation
  - `test_night_render`: timing, redraw keys, ids, dimming, fade, every scene
  - `test_night_ui`: controls
  - `test_night_extras`: countdown, fireflies, shooting stars, simulation
  - `test_night_animals`: 14 animals, plus `tests/screenshots/animals_sheet.png` for visual review
  - `tests/check_static.sh`: syntax check and the Safari 12 forbidden-feature grep
```

- [ ] **Step 3: Add the new suites to `tests/README.md`**

Append these rows to the table in `tests/README.md`:

```markdown
| `test_night_settings.py` | night animation storage: defaults, validation, per-scene memory, export/import |
| `test_night_render.py` | night timing (since/frac), per-area redraw, ids, dimming, fade, every scene |
| `test_night_ui.py` | night animation controls built from the registry |
| `test_night_extras.py` | star countdown, fireflies, shooting stars, in the simulation too |
| `test_night_animals.py` | the 14 sleeping animals, plus `animals_sheet.png` for a visual review |
```

and add below the table:

```markdown
`tests/check_static.sh` runs the syntax check and the grep for features Safari 12 lacks.
```

- [ ] **Step 4: Run everything**

Run: `tests/check_static.sh && tests/run_all.sh`
Expected: `static ok`, every suite passes, and the exit code is 0.

- [ ] **Step 5: Commit**

```bash
git add index.html REQUIREMENTS.md tests/README.md
git commit -m "Night animations: docs and version 1.4

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Visual review gate (human)**

Show the user these screenshots and ask for feedback before calling the work done:
- `tests/screenshots/animals_sheet.png`
- `tests/screenshots/night_*_1024x768.png`
- `tests/screenshots/countdown_arc_1024x768.png`
- `tests/screenshots/fireflies_768x1024.png`

Also remind them to check on the real iPad:
- SMIL animation
- performance with the 50 sky stars plus fireflies
- brightness in a dark room

Any changes to the drawings are follow-up tasks.
