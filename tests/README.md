# Tests

Browser tests for Sleep Clock, run in headless Chromium with Playwright. They're not deployed; only `index.html` and `sw.js` go to the host.

## Setup (once)

```sh
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
.venv/bin/playwright install chromium
```

## Run

```sh
tests/run_all.sh
```

Each suite serves the repo root on a local port, fakes the clock with `page.clock`, and runs in 1024×768 and 768×1024. Screenshots go to `tests/screenshots/`, which git ignores.

Each file can also be run on its own: `.venv/bin/python tests/test_sim.py . tests/screenshots`.

| Suite | Covers |
|---|---|
| `test_colors.py` | day and night colour and brightness, swatches, saved-value fallbacks, export and import |
| `test_rename.py` | Sleep Clock naming, migration from the old `okclock` storage keys, old and new export codes |
| `test_single.py` | single-file page (no extra requests), inlined icon, offline reload via `sw.js` |
| `test_sim.py` | live mini preview and the day simulation |
| `test_fade.py` | the phase-change crossfade |
| `test_regroup.py` | settings layout and the preview following the section you touch |
| `test_night_settings.py` | night animation storage: defaults, validation, per-scene memory, export/import |
| `test_night_render.py` | night timing (since/frac), per-area redraw, ids, dimming, fade, every scene |
| `test_night_ui.py` | night animation controls built from the registry |
| `test_night_extras.py` | star countdown, fireflies, shooting stars, in the simulation too |
| `test_keep_awake.py` | keep the screen on (Wake Lock, silent-video fallback, tap, release) and the full-screen help |
| `test_changelog.py` | the app version matches the newest `CHANGELOG.md` entry, entries are well-formed, released versions have git tags |
| `test_about.py` | settings header (version, app date, save time), GitHub links and issue forms |
| `test_dev_mode.py` | the long-hold trigger (settings / 1 s pause / dev toggle / give up), PIN, ON/OFF message, Developer section, stats overlay |
| `test_dev_pack.py` | Dev's Favourite pictures hidden unless enabled, the chosen one kept, Pinocchio's nose growing |
| `test_animal_drawings.py` | every animal template in index.html: safety, Safari 12, format, size, fits the canvas, breathes and twitches |
| `test_night_gallery.py` | the "See all" carousel for scenes and animals: opens, big cards, choose / close |
| `test_night_animals.py` | the 14 sleeping animals, plus `animals_sheet.png` for a visual review |

New Night pictures are imported with `tools/import_artwork.py` (see `artwork/README.md`), then checked by `test_animal_drawings.py`.

`tests/check_static.sh` runs the syntax check and the grep for features Safari 12 lacks.

Headless Chromium isn't Safari 12. Also check on the real iPad, and grep for the forbidden features listed in `REQUIREMENTS.md` §1.
