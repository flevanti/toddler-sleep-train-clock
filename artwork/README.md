# Artwork for Night pictures

Not deployed. The clock only needs `index.html` and `sw.js`. This folder holds the source drawings.

- `incoming/`: drop new SVGs here. Name each file as it should appear in the app (`fire-engine.svg`, `rocket-2.svg`), in lower case with hyphens.
- `originals/`: every imported drawing, as downloaded. The importer moves files here from `incoming/`.
- `CATALOG.md`: name and category of each picture. The category decides the carousel group and the gentle movement.

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
