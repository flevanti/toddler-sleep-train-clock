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

Headless Chromium isn't Safari 12. Also check on the real iPad, and grep for the forbidden features listed in `REQUIREMENTS.md` §1.
