# Changelog

Every version of Sleep Clock, newest first. The version shown in the app (`VERSION` in `index.html`) must match the newest entry here, and `tests/test_changelog.py` checks that it does. Use `tools/release.py` to add a version: it updates both. Each released version has a git tag (`v1.6`…) on the commit where it was finished. 1.0–1.2 were made before the project used git, so they have no tags.

## 1.6 — 2026-09-27
- **Keep the screen on:** a new switch, on by default. It uses the browser's built-in way to keep the screen awake where there is one, and a tiny silent looping video on older devices (the technique from NoSleep.js, MIT). A status line in settings says what's working.
- **Full-screen help in settings:** how to run the clock from the home screen on iPad/iPhone and Android, plus a "Go full screen" button where the browser supports it.
- The settings setup checklist is now a device-neutral **Device setup checklist**.
- The dev overlay shows how the screen is kept on.

## 1.5 — 2026-09-27
- **Settings header:** version, "app updated" date (from the web server) and when settings last changed.
- **About & feedback:** links to the GitHub repo and to the "Suggest a feature" and "Report a problem" issue forms, pre-filled with the version and device.
- **Dev mode:** hold the top-right corner for 6 seconds. It opens a secret Developer section with a live stats overlay (timer delay, redraws, reloads, sound, storage, phase). Settings now open when you let go of the corner.
- **Dev's Favourite:** 39 hidden Night pictures (Florence, Tuscany, food, things), listed only in dev mode. Pinocchio's nose grows through the night.
- **README** with screenshots, and an **MIT licence** (third-party artwork keeps its own terms).

## 1.4 — 2026-09-27
- **Night animations:** calm scenes (Z's & stars, Breathing, Moon & sky) and extras on top (star countdown, fireflies, shooting stars), each with its own settings.
- **Night pictures:** 14 cartoon animals plus 124 imported silhouettes in 9 categories, each breathing, floating, swaying, rocking or rolling gently.
- **"See all" carousel** of every scene and picture, with category chips and "View SVG" to copy a drawing.
- Pictures are plain SVG templates in one section of the page. There's an import tool for new artwork, and automatic checks on every drawing.

## 1.3 — 2026-09-26
- **Phase change fade:** the old screen fades into the new one (off to 10 seconds).
- **Settings regrouped:** General, the weekly schedule, then one section per phase (Night, Almost time, Wake, Day), plus Nap and Device & safety.

## 1.2 — 2026-09-26
- **Live mini preview** of the clock pinned at the top of settings.
- **Simulate a day:** a whole day and night plays in 30–120 seconds, then returns to settings.

## 1.1 — 2026-09-26
- **Night and day colours and brightness**, chosen from colour swatches.
- A **single page** (the icon is embedded) plus the small offline-cache file.
- Renamed to **Sleep Clock**.

## 1.0 — 2026-09-26
- The first "OK to wake" clock: a schedule for each day of the week, red night, optional amber "almost time", green wake-up, day screen, wake sounds, nap timer, PIN, backup codes and offline use.
