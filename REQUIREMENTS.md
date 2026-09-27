# toddler-sleep-train-clock: requirements and decisions

Shown to the user as **Sleep Clock** (home-screen label, page title, settings header). iOS truncates icon labels at about 12 characters, so the full project name is used only in code, storage keys and docs.

A toddler "OK to wake" sleep-training clock, built as a web app for an old iPad mini that is wall-mounted like a clock. The goal is to replace a ~£30 commercial clock (FiveHome "OK to Wake") and do more than it does, most notably with a different schedule for each day.

The code already exists: `index.html` (everything, including the icon) and `sw.js` (offline cache). This document records what it must do and why it is built the way it is.

---

## 1. Target device (hard constraints)

- **iPad mini 2, iOS 12.5.7** (the highest version it can run), so the browser is **Safari 12**.
- Screen: 1024×768 points. It must work in **portrait and landscape**.
- **JavaScript must stay ES2017-safe.** Do not use:
  - optional chaining `?.` or nullish coalescing `??`
  - class fields, private `#fields`, `static x =`
  - `String.replaceAll`, `Array.at`, `structuredClone`, `Object.fromEntries` (12.1+ only; avoid it)
  - `<dialog>`
- **CSS must also be Safari-12-safe.** Do not use:
  - flexbox `gap`, `inset`, `aspect-ratio`, `:focus-visible`
  - Keep `-webkit-` prefixes on transforms and animations.
- **Web Audio** has to use `window.AudioContext || window.webkitAudioContext`. Unprefixed support only arrived in Safari 14.1.
- Audio unlocks on **`touchend` or `click`**. Since iOS 9, `touchstart` doesn't unlock it.
- Before finishing any change, grep the code for the forbidden features above and run a syntax check.

## 2. Why a web app and not a native app (decided)

- A native app signed with a free Apple ID expires every **7 days**. The paid account costs $99 a year and the app still expires yearly. That's no good for a clock on the wall.
- The web app is added to the home screen and runs full-screen. It never expires and needs no signing.
- The one real thing we give up is **screen brightness**: a web page can't set it, so we fake dimming with dark pixels. The LCD backlight still glows a little at night, and that is accepted.

## 3. Core behaviour (v1: implemented)

### Display states
| State | When | Look |
|---|---|---|
| **Sleep (red)** | From bedtime until the next morning's wake time | Black background, red face with closed eyes, the chosen night scene (default: "z"s and twinkling stars) plus any optional extras, dimmed to night brightness |
| **Almost time (amber)** | N minutes before wake (optional, off by default) | Amber face with half-closed eyes |
| **Wake (green)** | From wake time for the "green duration" | Dark green background, bright green smiling face with sun rays |
| **Day** | The rest of the day | Soft blue awake face, or just the time, or a black screen (setting) |

- The wake time belongs to the **morning of that day**. The bedtime belongs to the **evening of that day**. Sleep carries over midnight without a gap.
- Every day always has a schedule. There's no per-day on/off switch; I removed it because it created awkward edge cases.
- If bedtime is set earlier than wake time, show a warning.
- The state is worked out from the device clock and re-checked every second.

### Schedule
- **Per weekday:** wake time, bedtime, and wake sound (Off, Chime, Music box, Birds, Ding-dong).
- Defaults: bedtime 19:00 every day; wake 07:00 on weekdays and 07:30 at weekends.
- Shortcuts: "Copy Monday → Tue–Fri" and "Copy Saturday → Sunday".
- Global setting: how long the green face stays on (15 minutes to 2 hours, default 1 hour).

### Sound
- All sound is made by Web Audio oscillators, so there are no audio files.
- There is **one alarm volume slider** shared by every day (a deliberate simplification of the "volume per day" idea). The slider uses a squared curve so it feels even. It can't go louder than the iPad's own hardware volume.
- How long the alarm plays: 20 s, 1, 2 or 5 minutes, or "until tapped" (capped at 5 minutes).
- Optional **fade-in** over 20 seconds.
- **Tapping anywhere** stops a ringing alarm.
- The alarm fires **once**, within the first 90 seconds of the green phase. The last-fired key is saved to storage (`toddler-sleep-train-clock.fired`) so a reload doesn't set it off again.
- Optional **soft brown noise** during the red phase, with its own volume.
- A **silent looping buffer** keeps the audio context awake overnight.
- Settings has a test button for each tone.

### Sound-locked handling
- iOS keeps sound locked until someone taps. After a reload, Safari re-locks it.
- If any sound feature is switched on and the audio context isn't `running`, show a badge:
  - **At night:** a small, dim pill at the bottom saying "🔇 tap to enable sound", so it doesn't light up the room.
  - **In the daytime:** a big centred prompt that explains why sound is locked.
- The display carries on working normally whether or not sound is locked.

### Nap timer
- Nap lengths: 30 min, 45 min, 1 h, 1½ h or 2 h, starting now. The clock goes red, then green for up to 30 minutes, with its own end-of-nap sound.
- The nap is saved in storage so it survives a reload. It can be cancelled.

### Display options
- Night colour (v1.1): swatches for red (default), orange, amber, pink, purple and soft blue. The face, "z"s, stars and time all use it. A hint says red/orange/amber are the most sleep-friendly.
- Night brightness: 5–100%.
- Daytime shows: the face, just the time, or nothing.
- Day colour (v1.1): swatches for blue (default), green, yellow, pink, purple, teal and white. The background is a very dark tint of the chosen colour. In "just the time" mode the digits use the day colour.
- Day brightness (v1.1): 20–100% (default 100%). It dims the face, time and label.
- Wake (green) and almost-time (amber) colours are **fixed on purpose**, so the "OK to wake" signal always looks the same to the child.
- Colour pickers are swatch buttons, not `<input type=color>`, which is unreliable on iOS 12. Unknown saved colours fall back to the defaults; brightness values are clamped.
- Show the time on or off, plus a separate "also at night" switch.
- 24-hour or 12-hour clock. No am/pm, to keep the face clean.
- Optional words under the face: "Stay in bed", "Almost time", "Good morning!", "Nap over!".
- **Phase change fade (v1.3):** Off / 1 / 3 / 5 / 10 s, default 3 s.
  - At every phase change (including nap start and end), a copy of the old screen is laid on top and faded out while the new screen is already underneath. Face, background, time, words and layout all blend together.
  - The change still happens at the exact scheduled time.
  - There's no fade on first load or when coming back to the app.
  - The mini preview fades between tabs with the same duration. The simulation caps fades at 500 ms.
  - The copy has its ids stripped and its SVG gradient renamed, so there are no duplicate ids (Safari confuses them). The clock's CSS uses classes for the same reason.
  - The old 2 s CSS transitions were removed; this replaces them.
- **Live preview (v1.2):** a mini copy of the clock is pinned at the top of settings (the settings list scrolls underneath). It has tabs for Night / Amber / Green / Day and switches to the matching tab when you touch a related control (e.g. night colour → Night, day brightness → Day, amber setting → Amber). It uses the same drawing code as the real clock, with a typical time from today's schedule. This replaced the old 8-second preview buttons.

### Day simulation (v1.2)
- A **"Simulate a day"** button in settings runs the real full-screen clock on a **pretend clock** to confirm the settings.
- It covers 24 hours, starting `max(30, amber + 15)` minutes before the chosen day's wake time, so it shows amber, green, day, bedtime, night and the next morning.
- **Controls** in a bar at the bottom:
  - day picker (default today)
  - speed: **"Full day in 30–120 s"** (default 60 s, steps of 10 s)
  - pause/play
  - mute
  - a **timeline strip** coloured by phase; tapping it jumps to that time and pauses
  - the pretend time and phase name
  - Exit
- **Sound:** the wake sound plays for about 3 s with no fade-in when green starts, only during normal playback (not on jumps). Noise plays during night if it's on. Mute turns both off.
- **Kept separate from real use:**
  - It never writes the alarm-fired marker.
  - It ignores and keeps a running nap.
  - It saves nothing and isn't restored after a reload.
  - The real 1-second tick is paused, so the real alarm can't fire during a simulation. If one is due, it fires on exit, provided it's still within the first 90 seconds of green.
- **It's part of settings: every exit goes back to settings** (no PIN asked, same scroll position), with the real clock running underneath:
  - the Exit button
  - the end of the cycle (it pauses, then returns after 5 s)
  - a **10-minute safety cap**, even when paused, so the display is never left on pretend time
- **Performance:**
  - It steps every 100 ms, with at most 250 ms of real time per step.
  - The 2 s CSS fades are turned off during the simulation.
  - Short phases pass quickly (10 min of amber is about 0.2 s at 30 s speed). Use pause or the timeline to look at them.

### Night animations (v1.4)
- Only during the night (sleep) phase, including naps. The design is in `docs/superpowers/specs/2026-09-26-night-animations-design.md`.
- **Scene** (choose one): Off, Z's & stars (default, same look as before), Breathing, Moon & sky, Sleeping animal. Each scene keeps its own settings.
- **"See all" carousel:** "See all ▸" next to the Scene dropdown opens a full-screen carousel of every scene and every Night picture (Off, Z's & stars, Breathing, Moon & sky, then all pictures by category), starting on the current choice. Each card is large and animated and shows the current settings and night colour. Swipe or use ◀ ▶, tap a card or **Choose this** to pick, and **Close** keeps the current choice. The carousel is emptied on close so no animations keep running. Each card has **View SVG**: a still, standalone SVG of that drawing (animations removed, 560×560, current night colour) with **Select all & copy**, so a parent can edit a drawing in any tool and hand it back to be turned into an animal (main colour → night colour, darker/lighter → `DK`/`LT`, breathing and twitches re-added).
- **Night picture (v1.4):** the "Sleeping animal" scene is now **Night picture**. It has 138 pictures: the 14 cartoon animals plus 124 imported silhouettes, in 9 categories (Animals, Vehicles, Space, Nature, Food, Party, Christmas, Sports & people, Toys & characters).
  - Internal ids stay the same (`scene: 'animal'`, option `animal`), so saved settings keep working.
  - Cartoon animals that share a name with a silhouette are called "… (cartoon)".
  - Settings list the pictures grouped by category (`<optgroup>`).
  - The carousel has category chips that jump to a group. Only the 5 cards around the middle are drawn, and the rest are empty frames with their name, so the iPad isn't animating 138 drawings at once.
  - Silhouettes move as a whole (`data-anim` on the `<svg>`): animals **breathe**; balloons, boats, planes, rockets and sea creatures **float**; trees and flowers **sway**; vehicles **rock**; balls slowly **roll**. The "Breathing / gentle movement" switch turns it off.
  - Import pipeline: `artwork/` (see its README) and `tools/import_artwork.py`, which converts potrace-style silhouettes to about 2–3 KB paths in `currentColor`. The 124 pictures add about 214 KB to `index.html`.
- **Animal drawing format (v1.4):** each animal is plain SVG in its own `<template id="animal-<id>" data-name="<Name>">` inside the **ANIMAL DRAWINGS** section of `index.html` (before the script), in the order shown in settings. Adding an animal = adding a template; the registry, dropdown and carousel pick it up.
  - Canvas `viewBox="-40 -40 280 280"`, animal on the ground near y≈210, facing left.
  - Main colour `currentColor` (= night colour); darker `rgba(0,0,0,.55)`, lighter `rgba(255,255,255,.22)`; a few fixed accents allowed (beaks, combs).
  - `<g data-part="body">` breathes (the clock scales it from its bottom centre); `<g data-move="<deg>" data-pivot="<x> <y>">` twitches now and then. The clock adds the SMIL; templates contain none.
  - Ids only on gradients (the clock prefixes them per copy on screen).
  - `tests/test_animal_drawings.py` checks every template: well-formed, no DOCTYPE/ENTITY, only plain shapes/gradients (no script, image, text, filter, style, use), no event handlers/links/inline styles/classes, plain colour values, `currentColor` used, one body group, ≥1 valid twitch group, ≤ 6 KB, unique ids/names, and — rendered in the app — fits the canvas, breathes and twitches in the night colour.
  - SVGs from outside are converted to this format by hand (main colour → `currentColor`, parts grouped, rescaled to the canvas) and must pass that test.
- **Sleeping animal:** 14 animals (bunny, bear, cat, owl, dog, turtle, hedgehog, chicken, pig, horse, cow, robin, blackbird, lion). They share one drawing style (`kitBody`, `kitHead`, `kitEyes`, `birdParts`), use the night colour, and appear **at night only**. Settings: breathing on/off, little movements off / rare (every 20 s) / normal (every 8 s).
- **Extras** (any number, all off by default):
  - **Star countdown:** stars go out one by one from bedtime (or nap start) to wake. Gone stars stay as faint outlines. In the simulation it follows the pretend clock.
  - **Fireflies:** seeded per night; redrawn when the screen size changes.
  - **Shooting star:** every 2/5/10 min ±30 %, optionally only in the first hour after bedtime. The schedule is fixed per night, so redraws don't reschedule it.
- The controls are built from the `SCENES` / `EXTRAS` registry in `index.html`. Saved values are checked against it, and unknown or invalid ones fall back to the defaults.
- Each paint target has three areas: face, `.below` and `.layer`. Each is redrawn only when its key changes, never on every tick.
- `computeState()` sleep states carry `since`: tonight's bedtime, yesterday's bedtime from yesterday's schedule, or the nap start. `nightFrac()` goes from 0 at bedtime to 1 at wake.

### Settings layout (v1.3)
Grouped so each control sits with the phase it affects. The mini preview and the "Simulate a day" button are pinned above the list.

1. **General:** sound status, alarm volume, test a sound, show the time, 24-hour clock, words under the face, phase change fade.
2. **Weekly schedule:** wake, bedtime and wake sound for each day, plus the copy buttons.
3. **● Night** (bedtime → wake): colour, brightness, show the time at night, soft noise, noise volume, the Animation (scene + its settings) and Extras controls.
4. **● Almost time** (amber): minutes before wake, or Off.
5. **● Wake** (green): how long green stays on, how long the wake sound plays, fade-in.
6. **● Day:** what it shows, colour, brightness.
7. **Nap:** start or cancel, and the sound when the nap ends.
8. **Device & safety:** PIN, backup (export, import, reset).
9. **iPad setup checklist**

Details:
- Each phase section has a coloured dot that follows the chosen colour.
- Phase sections carry `data-pv`, so touching anything inside one (including its heading) switches the mini preview to that phase.

### Version, save time and feedback (v1.5)
- **The settings header shows three things:**
  - the version (`VERSION`; bumped with `tools/release.py`, which also adds the `CHANGELOG.md` entry; `tests/test_changelog.py` keeps the two in sync, and released versions are git-tagged `vX.Y`);
  - **app updated** `<date>`: the server's `Last-Modified` date for `index.html`, read from `document.lastModified`. It needs no build step and still works offline. It's hidden when the server sends no date (browsers then report the load time);
  - **settings saved** `<when>`: the time settings last actually changed (`S.savedAt`). Saving with nothing new, e.g. closing settings, doesn't count. The value is included in export/import.
- **The About & feedback section** links to the GitHub repo and to two GitHub issue forms (`.github/ISSUE_TEMPLATE/`: feature request and bug report). The forms are pre-filled with the version and the device's user agent. The links open in the browser with `rel="noopener"`, need internet, and need a GitHub account to submit.

### Keep the screen on and full screen (v1.6)
- **"Keep the screen on"** is a switch under General, **on by default**.
  - **Newer browsers:** it uses the Screen Wake Lock API. The lock is asked for again whenever the page becomes visible, because the system releases it when the page is hidden.
  - **Older browsers** (no Wake Lock, e.g. old iPads): a tiny silent looping MP4 keeps the screen awake. It's muted, inline and off-screen. The video and technique come from NoSleep.js (MIT, Rich Tibbett), and the file is embedded as a data URI.
  - It may need one tap after a reload, the same tap that enables sound.
  - A status line under the switch says what's working: "built into this device", "older device: tiny silent video", "tap the clock once", or off.
  - It's a safety net only: the device's own screen timeout / Auto-Lock and low-power mode still matter (see the checklist).
- **Full screen:** settings say whether the clock is already running full screen from the home screen. Otherwise they explain how to add it (iPad/iPhone and Android), and show a **"Go full screen"** button where the browser supports the Fullscreen API (not on iPhone). It lasts until the page reloads.
- The setup checklist in settings is now device-neutral: **Device setup checklist**.

### Dev mode (v1.5)
- **Holding the top-right corner does nothing until you let go.** The time held decides what happens:

  | Hold for | Ring | On release |
  |---|---|---|
  | under 2.5 s | white, filling | nothing |
  | 2.5–3.5 s | solid green, still (looks finished, so nothing hints at more) | settings open |
  | 3.5–6 s | green, with a purple arc filling | settings open |
  | 6–10 s | solid purple | PIN (if one is set), then **dev mode toggles**, then settings open |
  | over 10 s | fades | nothing (something is resting on the corner) |

- **Toggling dev mode** shows a soft "DEV MODE ON/OFF" message for 1.5 s, in the current phase colour and brightness (dim at night).
- **Dev mode on its own changes nothing on the clock.** It shows a **DEV** badge and a secret **Developer** section in settings, with one switch per feature:
  - the stats overlay;
  - Dev's Favourite pictures.

  Turning dev mode off pauses the features and remembers the switches. They're stored as `S.dev = {on, overlay, pack}`; invalid values are ignored.
- **Stats overlay:** a dim box in the bottom-left corner that can't be tapped and updates every second. Everything is measured on the device. It shows:
  - version and app date;
  - 1-second timer delay (average and worst over the last minute);
  - redraw counts per area;
  - running animations;
  - uptime, and page loads today with their times (the last 30 loads are kept in `toddler-sleep-train-clock.loads`, to spot overnight reloads);
  - sound state and when the alarm last rang;
  - how the screen is kept on (wake lock, silent video, needs a tap, off);
  - online status and whether the offline copy is active;
  - storage used;
  - the current phase and the time of the next change.

### Dev's Favourite pictures (v1.5)
- **A hidden pack of 39 Night pictures**, in the "Dev's Favourite" category (internal id `original_dev_pack`): Florence, Tuscany, Italian food and things, plus a few from the developer's life.
  - 33 are drawn in `tools/draw_dev_favourite.py`, which writes the DEV FAVOURITE block of the ANIMAL DRAWINGS section.
  - 6 are imported through `tools/trace_artwork.py` → `tools/import_artwork.py`.
- **When they're listed:** only while dev mode **and** its "Dev's Favourite pictures" switch are on, in both the picture list (as their own group) and the carousel (as their own chip).
  - The picture on the clock always stays listed and keeps showing, even after dev mode is turned off. The pack is hidden from the lists, never from what the child sees.
  - Saved values stay valid either way, because the hiding only affects what's listed.
- **Pinocchio's nose** is a `<g data-grow="x y">`. It grows from 1× at bedtime to 1.8× by the morning, in 10 steps (it's redrawn only when a step changes).

### Settings access and PIN
- A **hidden gesture** opens settings: hold the top-right corner (110×110 px) for **2.5 seconds**. A progress ring fills while you hold.
- Apart from that, taps on the clock only unlock sound or stop the alarm. Scrolling and pinch-zoom are blocked.
- An **optional 4-digit PIN** has an on-screen keypad (no system keyboard) and must be typed twice when it's set. After 3 wrong tries it locks for 30 seconds.
- The PIN is kept in plain text on the device. It stops toddlers, not adults, and that is acceptable.
- The PIN pad must sit **above** the settings panel. There was a z-index bug here that has been fixed.

### Persistence
- Everything is saved in `localStorage` under the key `toddler-sleep-train-clock.settings.v1`. Every storage call is wrapped in try/catch.
- On load, data under the pre-rename keys (`okclock.settings.v1`, `okclock.fired`) is moved to the new keys once, so an iPad set up before the rename keeps its settings.
- On load, saved values are merged into the defaults and checked field by field, so a new version can add fields safely.
- **Export and Import:** a text code, `toddler-sleep-train-clock.v1:` followed by base64 JSON, that you copy somewhere safe. Import also accepts old codes starting `OKC1:`.
- Reset to defaults needs a second tap to confirm.
- If storage fails, show a warning.
- Caveats to surface in the settings panel:
  - The home-screen version and a normal Safari tab have **separate storage**. Always use the home-screen icon.
  - Clearing Safari's website data wipes the settings.
  - Home-screen apps are exempt from the 7-day data wipe that applies to websites.

### Installability and offline use
- It must be served over **HTTPS**. Check the certificate chain actually loads on iOS 12 before relying on a host.
- Apple meta tags: `apple-mobile-web-app-capable`, a black-translucent status bar and `apple-touch-icon` (180×180 PNG, **inlined as a base64 data URI**).
- **Deploy exactly two files: `index.html` + `sw.js` (decided).** All CSS, JS and the icon live in `index.html`. A service worker can't be inlined (it must be a separate same-origin script), so `sw.js` stays as its own file.
- `sw.js` uses a **network-first** service worker that falls back to the cache, so the clock still loads if the Wi-Fi drops and the page reloads. It is only registered on `https:`. Service workers work on iOS 11.3 and later. Bump `CACHE` in `sw.js` when its file list changes.
- When the page runs in a normal Safari tab, settings shows an "Add to Home Screen" hint.

### Setup checklist (shown in settings)
1. Turn Auto-Lock to Never, and switch off Auto-Brightness.
2. Set **Use Side Switch To: Lock Rotation**, so the switch can't mute web audio. Check Control Centre isn't on mute.
3. Set the hardware volume, then test the sound in settings.
4. Open from the home-screen icon and **tap once** to enable sound.
5. Turn on **Guided Access**. Disable the volume and sleep/wake buttons, but **leave Touch on**, so sound can be re-enabled after a reload.
6. Keep it charging, and check the battery for swelling from time to time.

## 4. Known limitations (accepted)
- Screen brightness can't be controlled; dimming is faked.
- Sound needs one physical tap after every page reload.
- The mute switch can silence Web Audio. We rely on the side switch being set to Lock Rotation instead of using the hack that plays a silent `<audio>` element.
- The PIN can be bypassed by anyone using developer tools.

## 5. Open / next steps
- [ ] **Choose a host.** Options: a GitHub Pages repo, Cloudflare Pages, or one of my own VPS servers. Then confirm that HTTPS loads on the real iPad.
- [ ] Test on the device:
  - add to the home screen
  - unlock sound
  - an overnight run, checking the audio context stays running until morning
  - the alarm fires once
  - the badge appears after a forced reload
  - Guided Access with Touch on
- [ ] Check the brightness of the red face at night in a dark room.
- [ ] Confirm the inlined data-URI home-screen icon shows on iOS 12 (fallback: go back to a separate `icon.png`).

## 6. v2 (optional, later): pair a phone
- The iPad shows a **6-digit pairing code that expires in about 5 minutes**. You type it into a web page on your phone, which can then edit the schedule, volume and PIN.
- The iPad checks for changes every **30–60 seconds**, using `XMLHttpRequest` to be safe on old Safari.
- It needs a small backend. Free-tier options: Cloudflare Worker + KV, Supabase or Firebase. It would also back up the settings to the cloud.
- The phone **cannot unlock sound**, since that needs a physical tap on the iPad. It can show "sound locked on iPad".

## 7. Testing approach used so far
- Headless Chromium through Playwright at 1024×768 and 768×1024, using `page.clock` to simulate the time.
- What was covered:
  - all four states
  - rolling over midnight
  - the later weekend wake time
  - settings surviving a reload
  - the long-press
  - setting and entering the PIN
  - exporting settings
  - (v1.1) day/night colour + brightness in both orientations, swatch UI, bad saved values falling back, export/import keeping the new fields
  - (v1.1) page makes no request besides `index.html`; icon data URI decodes at 180×180; offline reload served from the service worker
- `window.__toddlerSleepTrainClock` exposes `S()`, `computeState(date, ignoreNap)`, `setS(obj)`, `sim()`, `firedKey()` and `alarmPlaying()` for tests.
- (v1.2) Live preview (tab follows the control, colour and brightness update, gradient ids unique). Simulation:
  - phases in order, sound once at green
  - no fired marker, settings and nap untouched
  - auto-exit, 10-minute cap
  - timeline jump, mute, speed, day picker
- (v1.3) Settings layout: section order, every control in its section, preview follows the section and heading taps, dots follow the colours, moved controls still save, no horizontal overflow.
- (v1.3) Fade:
  - no copy on first paint; a copy on sleep→wake with the old face on top and the new one underneath
  - no duplicate ids; removed after the set duration
  - Off means a hard change; an invalid saved value becomes 3 s
  - the mini tab fades exactly over the preview
  - the simulation caps fades at 500 ms
- (v1.4) Night animations:
  - `test_night_settings`: storage and validation
  - `test_night_render`: timing, redraw keys, ids, dimming, fade, every scene
  - `test_night_ui`: controls
  - `test_night_extras`: countdown, fireflies, shooting stars, simulation
  - `test_night_animals`: 14 animals, plus `tests/screenshots/animals_sheet.png` for visual review
  - `tests/check_static.sh`: syntax check and the Safari 12 forbidden-feature grep
- This is not a substitute for testing on real Safari 12.
