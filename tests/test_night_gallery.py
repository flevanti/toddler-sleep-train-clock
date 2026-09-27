"""'See all' carousel for night scenes and animals: opens from settings, big animated cards, choose / close."""
import datetime
import os
import sys

from playwright.sync_api import sync_playwright

from harness import Checks, H, VIEWPORTS, open_settings, serve

ROOT, SHOTS = sys.argv[1], sys.argv[2]
check = Checks()
srv, URL = serve(ROOT)
DUP_IDS = "() => { var seen = {}, d = []; [].forEach.call(document.querySelectorAll('[id]'), function (e) { if (seen[e.id]) d.push(e.id); seen[e.id] = 1; }); return d; }"
CARDS = "() => [].map.call(document.querySelectorAll('#gtrack .gcard'), function (c) { return [c.getAttribute('data-id'), c.className.indexOf(' on') >= 0]; })"
CENTRED = "() => document.getElementById('gcount').textContent"

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

        # scenes
        check(tag + 'scene "See all" button', p.is_visible('[data-gallery=scene]'))
        p.click('[data-gallery=scene]')
        scenes = p.evaluate("() => Object.keys(%s.night.SCENES)" % H)
        animals = p.evaluate("() => Object.keys(%s.night.ANIMALS)" % H)
        expect = [s_ for s_ in scenes if s_ != 'animal'] + ['animal:' + a for a in animals]
        cards = p.evaluate(CARDS)
        check(tag + 'gallery open over settings', p.is_visible('#gallery') and p.is_visible('#settings'))
        check(tag + 'every scene and every animal has its own card, current highlighted',
              [c[0] for c in cards] == expect and len(expect) == 18 and [c[0] for c in cards if c[1]] == ['classic'], [c[0] for c in cards])
        check(tag + 'animal cards named after the animal', p.evaluate("() => document.querySelector('#gtrack [data-id=\"animal:owl\"] .gname').textContent") == 'Owl')
        check(tag + 'starts on the current scene', p.evaluate(CENTRED).startswith('2 /'), p.evaluate(CENTRED))
        big = p.evaluate("() => document.querySelector('#gtrack .gcard .gstage').getBoundingClientRect().width")
        check(tag + 'cards are big (>= 55% of the screen width)', big >= 0.55 * vp[0], big)
        check(tag + 'moon card shows its sky', p.evaluate("() => document.querySelectorAll('#gtrack [data-id=moon] .glayer circle').length") == 25)
        check(tag + 'cards animate (breathing card has SMIL)', p.evaluate("() => !!document.querySelector('#gtrack [data-id=breathing] animateTransform')"))
        check(tag + 'no duplicate ids', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))
        p.click('#gnext')
        p.clock.run_for(100)
        check(tag + 'next arrow moves one card', p.evaluate(CENTRED).startswith('3 /'), p.evaluate(CENTRED))
        p.screenshot(path=os.path.join(SHOTS, 'gallery_scenes_%dx%d.png' % vp))
        p.click('#gpick')
        check(tag + 'choose this picks the centred card', p.evaluate("() => %s.S().night.scene" % H) == 'breathing')
        check(tag + 'gallery closed, back in settings', not p.is_visible('#gallery') and p.is_visible('#settings'))
        check(tag + 'dropdown and preview updated',
              p.evaluate("() => document.getElementById('na-scene').value") == 'breathing' and
              p.evaluate("() => !!document.querySelector('#miniFace animateTransform')") and
              p.evaluate("() => document.querySelector('#pvtabs .b:not(.g)').getAttribute('data-pv')") == 'sleep')
        p.click('[data-gallery=scene]')
        p.click('#gtrack [data-id="animal:cat"]')
        check(tag + 'tapping an animal card chooses the animal scene with that animal',
              p.evaluate("() => [%s.S().night.scene, %s.S().night.scenes.animal.animal]" % (H, H)) == ['animal', 'cat'] and not p.is_visible('#gallery'))
        p.click('[data-gallery=scene]')
        check(tag + 'reopened: the chosen animal card is highlighted', [c[0] for c in p.evaluate(CARDS) if c[1]] == ['animal:cat'])
        p.click('#gclose')

        # animals
        check(tag + 'animal "See all" button', p.is_visible('[data-gallery=animal]'))
        p.click('[data-gallery=animal]')
        animals = p.evaluate("() => Object.keys(%s.night.ANIMALS)" % H)
        cards = p.evaluate(CARDS)
        check(tag + 'one card per animal, cat highlighted', [c[0] for c in cards] == ['animal:' + a for a in animals] and len(animals) == 14 and
              [c[0] for c in cards if c[1]] == ['animal:cat'], [c[0] for c in cards if c[1]])
        check(tag + 'animal cards are animals', p.evaluate("() => document.querySelector('#gtrack [data-id=\"animal:owl\"] svg').getAttribute('data-animal')") == 'owl')
        check(tag + 'no duplicate ids (animals)', p.evaluate(DUP_IDS) == [], p.evaluate(DUP_IDS))
        check(tag + 'starts on the chosen animal (cat = 3rd)', p.evaluate(CENTRED).startswith('3 /'), p.evaluate(CENTRED))
        p.click('#gprev'); p.click('#gprev'); p.click('#gprev')
        check(tag + 'prev at the first card stays there', p.evaluate(CENTRED).startswith('1 /'), p.evaluate(CENTRED))
        p.screenshot(path=os.path.join(SHOTS, 'gallery_animals_%dx%d.png' % vp))
        p.click('#gclose')
        check(tag + 'close keeps the choice', p.evaluate("() => %s.S().night.scenes.animal.animal" % H) == 'cat' and not p.is_visible('#gallery'))
        p.click('[data-gallery=animal]')
        p.click('#gtrack [data-id="animal:lion"]')
        check(tag + 'choosing an animal saves it', p.evaluate("() => %s.S().night.scenes.animal.animal" % H) == 'lion')
        check(tag + 'animal dropdown and preview updated',
              p.evaluate("() => document.getElementById('na-animal-animal').selectedOptions[0].textContent") == 'Lion' and
              p.evaluate("() => document.querySelector('#miniFace svg').getAttribute('data-animal')") == 'lion')
        check(tag + 'gallery emptied after closing (no animations left running)', p.evaluate("() => document.getElementById('gtrack').innerHTML") == '')
        ov = p.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        check(tag + 'no page-level horizontal scroll', ov)
        check(tag + 'no page errors', not errs, errs)
        p.close()
    b.close()
srv.shutdown()
sys.exit(check.finish())
