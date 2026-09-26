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
