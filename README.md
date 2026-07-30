# Shape gallery

A visual QC gallery for every cleaned contour dataset used across the
[Varifold-Moments](https://github.com/GiLonga/Varifold-Moments) research repo
(all of them except MNIST — see "Why MNIST is excluded" below): every shape,
grouped by class, rendered as a small silhouette for a quick visual scan.
Each shape also runs through the same finite-coordinate / positive-area /
closure (turning number) / self-intersection checks used throughout that
repo (`shape_qc.py`) — any shape that fails one gets a rust-colored outline
instead of needing a separate CSV cross-referenced by hand.

The site kept growing dataset-by-dataset, but `index.html` stays the Flavia
page specifically — it was the first page published here, links to it
(including `#class-N` anchors) were already shared, and every other page's
nav strip links back to it as "Flavia", so its filename can't move.

## Pages

| Dataset | Shapes | Classes | Flagged | Page |
|---|--:|--:|--:|---|
| Flavia | 1,907 | 32 | 0 | [index.html](index.html) |
| BBBC010 | 1,407 | 2 | 0 | [bbbc010.html](bbbc010.html) |
| HeLa Kyoto | 313 | 4 | 0 | [hela-kyoto.html](hela-kyoto.html) |
| MOC | 650 | 3 | 0 | [moc.html](moc.html) |
| MPEG400 | 400 | 20 | 0 | [mpeg400.html](mpeg400.html) |
| MPEG7 | 1,400 | 70 | 0 | [mpeg7.html](mpeg7.html) |
| Mendeley | 9,000 | 9 | 0 | [mendeley.html](mendeley.html) |
| Swedish SE/SL | 1,125 | 15 | 0 | [swedish-se-sl.html](swedish-se-sl.html) |

All 33 originally-flagged shapes (2 in BBBC010, 23 in MOC, 1 in MPEG7, 7 in
Swedish SE/SL — all self-intersections, none unfixable) were repaired in
place in `test_scripts/cleaned_data/*_cleaned.npy`. The fix is deliberately
the gentlest one that resolves each shape: a Gaussian smoothing pass over
the point sequence *in its original order* (`sigma` 1–5, picked as the
smallest value that clears the check — no point reordering or reversal at
all), which softens exactly the small kinks causing each crossing without
otherwise reshaping the silhouette. An earlier pass used a 2-opt
"uncross by reversing a sub-chain" algorithm instead; it technically
resolved every shape too, but reordering points is a structural change with
no guarantee the result is the *intended* boundary, so it was reverted in
favor of this smoothing-only approach. Originals are backed up alongside
those files under `pre_self_intersection_fix_backup/`.

Every page carries the same cross-dataset nav strip at the top, so you can
jump between all eight from any one of them.

**Live site:** https://gilonga.github.io/flavia-shape-gallery/

### Why MNIST is excluded

MNIST is 60,000 contours. `shape_qc.py`'s per-shape checks (shapely GEOS
noding + a Kmoment turning-number pass) are the expensive part of building
each page, and a single-file gallery at that count also isn't a practical
page to load or scroll. None of the other seven have that problem.

## What's here

- `index.html`, `bbbc010.html`, `hela-kyoto.html`, `moc.html`, `mpeg400.html`,
  `mpeg7.html`, `mendeley.html`, `swedish-se-sl.html` — the generated
  galleries (static, no JavaScript, no external requests — safe to open
  directly from disk too)
- `contour_gallery.py` — the generator. This is a **reference copy**: it
  imports `JC_functions`, `mendeley_400pt_flusser_rf`, and `shape_qc` from
  the main [Varifold-Moments](https://github.com/GiLonga/Varifold-Moments)
  repo and isn't meant to run standalone here. To regenerate a page (or add
  one for a dataset not listed above), copy it back into that repo and run:

  ```
  GALLERY_DATASET=MPEG7 python contour_gallery.py
  ```

  which writes `galleries/{dataset}_gallery.html` — copy that into this repo
  under the filename listed in the table above (see `PAGE_FILENAMES` in
  `contour_gallery.py` for the exact mapping).

## How it works

No JavaScript anywhere: hover tooltips, the sticky class-nav bar,
jump-to-class links, and the cross-dataset nav strip are all plain CSS/HTML
(`:hover`, `position: sticky`, `<a href="#...">`). Each shape is downsampled
to 100 points purely for thumbnail legibility (the tooltip's area figure
comes from the full-resolution contour) and normalized into its own 100×100
SVG viewBox so shapes of very different native sizes still render at a
consistent thumbnail size.
