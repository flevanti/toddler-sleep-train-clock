# Night animations: design

Date: 2026-09-26 · Status: awaiting review · Target version: 1.4

## Goal

Parents can choose how the night screen moves. There are several calm **scenes**, plus optional **extras** layered on top, and each one has a few settings of its own. One extra, the **star countdown**, also helps the sleep training: it shows the toddler how much of the night is left.

## Decisions (agreed in conversation)

| Topic | Decision |
|---|---|
| How they combine | **Choose one scene**, plus **any number of extras** on top |
| Scenes | Off · Z's & stars (today's look) · Breathing · Moon & sky · Sleeping animal |
| Extras | Star countdown · Fireflies · Shooting star |
| Animals | 14: bunny, bear, cat, owl, dog, turtle, hedgehog, chicken, pig, horse, cow, robin, blackbird, lion |
| Animal in other phases | **Night only.** Amber, green and day keep the round face, so "green face = OK to get up" stays clear |
| When it plays | Only in the **night (sleep) phase**, including naps |
| Default | Z's & stars, no extras. The clock looks the same after the upgrade |
| Architecture | An **animation registry** inside `index.html`. Settings controls are built from each entry's list of settings. The app stays `index.html` + `sw.js` |

## Constraints

- Safari 12 (iPad mini 2, iOS 12.5.7). The rules in `REQUIREMENTS.md` §1 apply: ES2017, no flex `gap`, and `-webkit-` prefixes on CSS animations and transforms.
- Animations inside the SVG use **SMIL** (`<animate>`, `<animateTransform>`, `<animateMotion>`). Safari 12 supports it fully, and it avoids Safari 12's `transform-origin` quirks with CSS on SVG. Plain CSS keyframes are used only on HTML elements.
- Everything uses the chosen **night colour** and sits under the **night brightness** dimming. Nothing is brighter than the face.
- Keep the number of animated elements small for the iPad mini 2. Where many elements share a motion, they share one animation (e.g. sky stars in 3 twinkle groups, not 50 separate animations).
- **No `id` attributes** in animation markup, except gradient ids built from the paint target's `gid`. That keeps the phase-change fade copy free of duplicate ids.

## Architecture

### Registry

```js
// value lists are [value, label]; def must be one of the values
SCENES = {
  off:       { name: 'Off',             opts: [] , face: fn, layer: null },
  classic:   { name: "Z's & stars",     opts: [...], face: fn, layer: null },
  breathing: { name: 'Breathing',       opts: [...], face: fn, layer: null },
  moon:      { name: 'Moon & sky',      opts: [...], face: fn, layer: fn   },
  animal:    { name: 'Sleeping animal', opts: [...], face: fn, layer: null }
};
EXTRAS = {
  countdown: { name: 'Star countdown', opts: [...], place: 'below', draw: fn },
  fireflies: { name: 'Fireflies',      opts: [...], place: 'layer', draw: fn },
  shooting:  { name: 'Shooting star',  opts: [...], place: 'layer', draw: fn }
};
// opt: { key, label, type: 'choice' | 'toggle', values: [[v, label], ...] (choice only), def }
```

- `face(o, ctx)` returns the SVG for the face box, replacing today's night face. `layer(o, ctx)` returns markup for a full-screen layer.
- `ctx` holds `{ color, gid, frac, now, since, until }`. `frac` is how far through the night we are, from 0 to 1. `since` and `until` are when this night (or nap) started and ends.
- **Adding an animation** means adding one entry. The settings controls, validation, defaults, export and the mini preview pick it up automatically.

### Where things are drawn (per paint target: the real clock and the mini preview)

```
.clk / .mini
 ├─ .face    ← scene.face()                 (same 72vmin box as today)
 ├─ .below   ← extras with place 'below'    (countdown, between face and time)
 ├─ .time, .label
 └─ .layer   ← scene.layer() + extras with place 'layer' (absolute, full size, pointer-events: none)
```

- Only the **sleep** phase draws scenes and extras. Other phases clear `.below` and `.layer` and use the existing faces.
- **Redraw key:** today's `faceKey` becomes `mode | nightColor | dayColor | scene id + its settings | extras on + their settings | countdown stars lit`. The markup is rebuilt only when the key changes (normally a few times a night), never on every tick.
- `.layer` and `.below` are inside `.clk`, so the **phase-change fade** copies them, and the **mini preview** shows them scaled down (`.mini .layer` is absolutely positioned inside the preview box).

### Night timing (`computeState`)

- The sleep state gains `since`:
  - before wake: yesterday's bedtime
  - after bedtime: today's bedtime
  - during a nap: `nap.start`
- `until` exists already.
- `frac = clamp((now − since) / (until − since), 0, 1)`.
- In the **simulation**, `now` is the pretend time, so the countdown follows the pretend clock. SMIL and CSS motion always run in real time.

### Stored settings

A new settings group, `S.night`:

```js
night: {
  scene: 'classic',
  scenes: { classic: {...}, breathing: {...}, moon: {...}, animal: {...} }, // one set per scene, kept when switching
  extras: { countdown: { on: false, ... }, fireflies: { on: false, ... }, shooting: { on: false, ... } }
}
```

- `merge()` checks it against the registry. Unknown scenes, extras or keys are dropped. Invalid values become `def`. `on` must be a boolean.
- It's built from the registry defaults, so settings saved by older versions load unchanged, and export and import carry it.

## Settings for each animation (defaults in **bold**)

### Scenes

| Scene | Setting | Values |
|---|---|---|
| Off | none | A still night face |
| Z's & stars | Stars | **3** / 6 / 10 |
| | Floating z's | **on** / off |
| | Speed | slow / **normal** |
| Breathing | Pace | 4 / **6** / 8 breaths a minute |
| | Depth | subtle / **medium** / deep (scale 2 / 4 / 7 %) |
| | Glow on in-breath | **on** / off (a soft halo, via radial gradient, no blur filter) |
| Moon & sky | Sky stars | 10 / **25** / 50 (in the layer, placed at random but spread out, away from the moon and the time) |
| | Twinkle | off / **slow** / normal |
| | Sleepy face on the moon | **on** / off |
| Sleeping animal | Animal | **bunny** / bear / cat / owl / dog / turtle / hedgehog / chicken / pig / horse / cow / robin / blackbird / lion |
| | Breathing | **on** / off (belly rises and falls, about 6 breaths a minute) |
| | Little movements | off / **rare** / normal (each animal's own: ear twitch, tail flick, feather ruffle, …) |

### Extras (all **off** by default)

| Extra | Setting | Values |
|---|---|---|
| Star countdown | Number of stars | 5 / **8** / 10 / 12 |
| | Layout | **arc** / row |
| | How a star goes out | **fade** / pop |
| Fireflies | How many | 3 / **5** / 8 |
| | Speed | **very slow** / slow |
| | Colour | **match night colour** / warm yellow (`#ffd27a`) |
| Shooting star | How often | every 2 / **5** / 10 minutes (with ±30 % random variation) |
| | Only in the first hour after bedtime | **on** / off |

### Behaviour notes

- **Star countdown:**
  - Stars lit = `ceil(N × (1 − frac))`: all N lit at bedtime, none at wake, going out at equal intervals.
  - Gone stars stay as faint outlines (opacity 0.15), so the child sees both how many are left and how many have gone.
  - "Fade" means a star fades out over 3 s when it goes out; "pop" means a quick shrink.
  - Only the star that just went out animates. The others stay still.
- **Shooting star:**
  - Scheduled from `since` in steps of the chosen interval, with random variation; seeded per night so a redraw doesn't reschedule it.
  - Each one crosses about a third of the screen in about 1.5 s, then disappears.
  - With "first hour only" on, none are scheduled after `since + 60 min`.
- **Fireflies:**
  - Each firefly follows a random, slow, looping `<animateMotion>` path (40–70 s per loop when very slow, 20–35 s when slow).
  - Its opacity pulses gently.
  - Paths are made when the fireflies are drawn and stay the same until the next redraw.
- **Animals:**
  - All 14 share one drawing style: a curled-up sleeping body (ellipse), a head (circle) and closed-eye arcs.
  - Each animal adds its own features: long ears (bunny), round ears (bear), pointed ears and tail (cat), feathers and tufts (owl), floppy ears (dog), shell (turtle), spikes (hedgehog), comb and beak (chicken), snout and curly tail (pig), mane and long face (horse), horns and spots (cow), red breast (robin), yellow beak (blackbird), mane ring (lion).
  - Drawn in the night colour with dark details, like the round face.

## Settings screen

The Night section gains an **Animation** part:

```
● NIGHT  bedtime → wake
  Colour · Brightness · Show the time at night · Soft noise · Noise volume
  ── Animation ──
  Scene                [ Z's & stars ▾ ]
     Stars [3 ▾]   Floating z's [●]   Speed [normal ▾]      ← settings for the chosen scene
  ── Extras ──
  Star countdown       [○]
  Fireflies            [●]
     How many [5 ▾]  Speed [very slow ▾]  Colour [match ▾]  ← shown only while the extra is on
  Shooting star        [○]
```

- The rows are built from the registry. Control ids follow the pattern `na-<scene>-<key>` and `nx-<extra>-<key>`, plus `nx-<extra>-on`.
- Changing any of them saves, redraws the settings panel if the scene or an extra was switched, and updates the mini preview. It's all inside the Night section, so the preview switches to the Night tab automatically.
- On the **mini preview Night tab**, the countdown shows a half-finished night: the time shown is the midpoint of tonight and `frac = 0.5`.

## Testing

Add to `tests/` (and `tests/run_all.sh` picks them up):

- `test_night_settings.py`:
  - defaults are unchanged after an upgrade (saved settings without `night` look exactly like today)
  - invalid, unknown or missing values fall back
  - each scene keeps its own settings when you switch
  - export and import round-trip
  - controls are built for every scene and extra
  - an extra's settings show only while it's on
  - every control saves
- `test_night_render.py`:
  - every scene, every extra and all 14 animals draw in the real clock and the mini preview without page errors
  - no ids in the markup except gradient ids that start with the target's `gid`
  - nothing is drawn outside the sleep phase
  - the redraw key doesn't change from one tick to the next when nothing changed
- **Countdown maths:**
  - N lit at `since`, N/2 at the midpoint, 0 at `until`
  - a nap uses `nap.start` → `nap.end`
  - in the simulation, the lit count goes down as pretend time passes
- **Shooting star:** the schedule respects the interval and the first-hour limit; redraws don't reschedule it.
- **Fade:** the phase-change fade copy still has no duplicate ids with animations present.
- **Screenshots** of every scene, extra and animal, in both orientations, for a visual review.
- Every stage finishes with the Safari 12 forbidden-feature grep, a syntax check and `tests/run_all.sh` fully passing.

## Delivery stages

1. **Foundation:**
   - the registry, the settings controls built from it, and storage and validation of `S.night`
   - `computeState().since` and `frac`
   - the `.below` and `.layer` areas and the new redraw key
   - scenes: **Off**, **Z's & stars** (identical look by default, with its new settings) and **Breathing**
2. **Sky and extras:** **Moon & sky**, **Star countdown**, **Fireflies**, **Shooting star**.
3. **Animals:** the shared animal style and **14 animals**, with breathing and little movements. You review the screenshot sheet before this stage is called done.

Each stage is committed on the `night-animations` branch, with `REQUIREMENTS.md` updated.

## Out of scope

- Animals or scenes in the amber, green or day phases.
- Sounds tied to animations.
- Custom animal colours (animals use the night colour).
- Controlling the speed of the SMIL and CSS motion in the simulation (motion stays real-time; the countdown follows pretend time).

## Risks

- **Performance on the iPad mini 2:** 50 sky stars plus fireflies plus breathing all at once is the heaviest case. Grouped animations should keep it light, but it needs checking on the device. If needed, the fallback is to cap the sky at 25 stars when fireflies are on.
- **How the animals look is a matter of taste:** stage 3 ends with your review of the screenshot sheet.
- **Headless Chromium isn't Safari 12:** SMIL and layout need a check on the real iPad after each stage.
