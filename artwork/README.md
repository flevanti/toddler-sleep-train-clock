# Artwork for Night pictures

Not deployed. The clock only needs `index.html` and `sw.js`. This folder holds the source drawings.

- `incoming/`: drop new SVGs here. Name each file as it should appear in the app (`fire-engine.svg`, `rocket-2.svg`), in lower case with hyphens.
- `originals/`: every imported drawing as a silhouette SVG. The importer moves files here from `incoming/`.
- `sources/`: the raw files that were traced into silhouettes (coloured SVGs, PNGs…), kept for reference.
- `CATALOG.md`: name and category of each picture. The category decides the carousel group and the gentle movement.

Pictures that aren't already one-colour silhouettes (colours, text, styles, PNG/JPG) are turned into one first with `.venv/bin/python tools/trace_artwork.py`. It needs potrace (`brew install potrace`), and it moves the original to `sources/`.

The hand-drawn **Dev's Favourite** pictures don't come from files: they're drawn in code in `tools/draw_dev_favourite.py` (run it after editing a drawing). They're hidden in the app unless dev mode and its switch are on.

To add pictures:
1. Put the SVGs in `incoming/`.
2. Add a row for each to `CATALOG.md`.
3. Run `python3 tools/import_artwork.py`.
4. Run `tests/run_all.sh`.

The importer:
- flattens each outline, fits it to the clock's canvas and simplifies it to about 3 KB;
- paints it in the night colour;
- rewrites the IMPORTED ARTWORK block in `index.html`.

`tests/test_animal_drawings.py` then checks every picture for safety, Safari 12, size, fit and movement.

Movement by picture:
- animals: breathe;
- balloons, boats, planes, rockets and sea creatures: float;
- trees and flowers: sway;
- vehicles: rock;
- balls: roll.

See `motion()` in the importer.
