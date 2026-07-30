# Flavia shape gallery

A visual QC gallery for the Flavia leaf-contour dataset: every cleaned shape,
grouped by species class, rendered as a small silhouette for a quick visual
scan. Each shape also runs through the same finite-coordinate / positive-area
/ closure (turning number) / self-intersection checks used across the
[Varifold-Moments](https://github.com/GiLonga/Varifold-Moments) research repo
— any shape that fails one gets a rust-colored outline instead of needing a
separate CSV cross-referenced by hand.

**Live page:** enabled via GitHub Pages on this repo (Settings → Pages once
enabled) — see the repo's "About" section for the URL once it's live.

## What's here

- `index.html` — the generated gallery (static, no JavaScript, no external
  requests — safe to open directly from disk too)
- `contour_gallery.py` — the generator. This is a **reference copy**: it
  imports `JC_functions`, `mendeley_400pt_flusser_rf`, and `shape_qc` from
  the main [Varifold-Moments](https://github.com/GiLonga/Varifold-Moments)
  repo and isn't meant to run standalone here. To regenerate the gallery
  (or build one for a different dataset), copy it back into that repo and
  run:

  ```
  GALLERY_DATASET=Flavia python contour_gallery.py
  ```

  which writes `galleries/{dataset}_gallery.html`.

## How it works

No JavaScript: hover tooltips, the sticky class-nav bar, and jump-to-class
links are plain CSS/HTML (`:hover`, `position: sticky`, `<a href="#...">`).
Each shape is downsampled to 56 points purely for thumbnail legibility (the
tooltip's area figure comes from the full-resolution contour) and normalized
into its own 100×100 SVG viewBox so shapes of very different native sizes
still render at a consistent thumbnail size.
