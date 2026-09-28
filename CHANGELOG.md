# Changelog

Every version of Sleep Clock, newest first. The version shown in the app (`VERSION` in `index.html`) must match the newest entry here, and `tests/test_changelog.py` checks that it does. Use `tools/release.py` to add a version: it updates both. Each released version has a git tag (`v1.6`…) on the commit where it was finished. 1.0–1.2 were made before the project used git, so they have no tags.

## 1.10 — 2026-09-28
- **"Tap the screen once" prompt:** after the clock starts, it says when a tap is needed and why (to keep the screen on and/or play sounds), then shows a big thumbs-up once it's done. Small and dim at night.
- Installed apps on Android and desktop no longer see the "opened in a normal browser tab" warning.
- **Tech FAQ** in the README: the common problems (screen turning off, no sound, address bar, updating, settings, PIN) and how to fix them.
- Better for search engines: a descriptive page title and description, link previews, and structured data. The home-screen name is still "Sleep Clock".
- Tests: live progress per suite and faster runs.

## 1.9 — 2026-09-27
- **Fixed: the screen still went dark on older devices** (no built-in way to keep the screen on, e.g. older iPads). Safari ignores a muted or looping video for keeping the screen on, and ours was both. The video is now unmuted (its sound track is silent) and rewinds itself instead of looping. It needs one tap on the clock after the app starts.
- The dev overlay shows whether that video is really playing.

## 1.8 — 2026-09-27
- **Updates** in settings: a **Reload** button (a home-screen app has no browser reload), **Check now** for a new version, and an optional switch that checks every few hours and shows a small "New version available" on the clock, in the picture's colour, only in the daytime. Nothing ever updates by itself.
- Fixed a test that failed at random depending on where a Night picture was in its breathing animation.

## 1.7 — 2026-09-27
- **Installs as a full-screen app on Android:** the page now has a web app manifest (embedded, still just two files to deploy), so "Install app" / "Add to Home screen" gives the clock its own icon and opens it full screen with no address bar.
- New app icon: the green morning face with sun rays, with a maskable version that fits Android's round and squircle icon shapes.

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
