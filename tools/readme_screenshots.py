#!/usr/bin/env python3
"""Regenerate the README screenshots in docs/screenshots/ from the real app (headless Chromium, faked clock).

Usage (from the repo root):   .venv/bin/python tools/readme_screenshots.py
"""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from playwright.sync_api import sync_playwright  # noqa: E402

from harness import H, open_settings, serve  # noqa: E402

OUT = os.path.join(ROOT, 'docs', 'screenshots')
LANDSCAPE, PORTRAIT = (1024, 768), (768, 1024)


def page(b, vp, when, settings=None, fade=0):
    p = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
    p.add_init_script("Object.defineProperty(navigator, 'standalone', {get: function () { return true; }})")  # as on the home screen
    p.clock.install(time=when)
    p.goto(URL)
    p.evaluate("() => localStorage.clear()")
    p.reload()
    p.clock.run_for(300)
    p.evaluate("(o) => %s.setS(o)" % H, dict({'fadeSec': fade, 'showTimeNight': True}, **(settings or {})))
    p.clock.run_for(1500)
    return p


def shot(p, name):
    p.screenshot(path=os.path.join(OUT, name))
    print('wrote', name)


os.makedirs(OUT, exist_ok=True)
srv, URL = serve(ROOT)
wed = lambda h, m=0: datetime.datetime(2026, 9, 23, h, m, 0)  # noqa: E731
with sync_playwright() as pw:
    b = pw.chromium.launch()
    # the three phases of a night, with the default look
    shot(page(b, LANDSCAPE, wed(21, 30), {'nightDim': 70}), 'night.png')
    shot(page(b, LANDSCAPE, wed(7, 10)), 'wake.png')
    shot(page(b, LANDSCAPE, wed(15, 0)), 'day.png')
    # night animations: moon & sky with the star countdown; a night picture in portrait
    shot(page(b, LANDSCAPE, datetime.datetime(2026, 9, 24, 1, 0, 0),
              {'nightDim': 80, 'night': {'scene': 'moon', 'extras': {'countdown': {'on': True}}}}), 'moon-countdown.png')
    shot(page(b, PORTRAIT, wed(22, 0), {'nightDim': 80, 'nightColor': 'amber',
                                        'night': {'scene': 'animal', 'scenes': {'animal': {'animal': 'giraffe-lying-down'}}}}), 'night-picture.png')
    # settings with the live preview, and the "See all" carousel
    p = page(b, LANDSCAPE, wed(22, 0), fade=3)
    open_settings(p, LANDSCAPE)
    p.click('#pvtabs [data-pv="sleep"]')
    shot(p, 'settings.png')
    p.click('[data-gallery=scene]')
    p.click('#gchips button:has-text("Vehicles")')
    p.clock.run_for(200)
    shot(p, 'carousel.png')
    b.close()
srv.shutdown()
