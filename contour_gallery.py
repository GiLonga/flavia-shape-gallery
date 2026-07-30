#!/usr/bin/env python3
"""
Specimen-plate gallery: renders every contour of one cleaned dataset (the
same DATASETS list from mendeley_400pt_flusser_rf.py every experiment script
in this repo uses) as a small SVG silhouette, grouped by class, for a quick
visual QC scan -- the generator behind the Flavia leaf-contour gallery
artifact (2026-07-30).

Each shape is downsampled to N_RENDER_PTS points (just for thumbnail
legibility -- the tooltip's area figure is computed from the full-resolution
contour) and normalized into its own 100x100 SVG viewBox, centered and
scaled to its bounding box, so shapes of very different native sizes still
render at a consistent thumbnail size.

Runs shape_qc.py's own per-contour checks (finite coordinates, positive
area, correct turning number/closure, no self-intersections -- see
shape_qc.py's docstring for why each matters) and gives any flagged shape a
rust-colored outline directly in the gallery, instead of needing shape_qc.py's
CSV cross-referenced separately. Those checks are the expensive part
(shapely GEOS noding + a Kmoment turning-number pass per shape), so they run
through a multiprocessing.Pool the same way shape_qc.py itself does --
without it this would be impractical on anything past a few thousand shapes.

No JavaScript anywhere -- hover tooltips, the sticky class nav, and
jump-to-class links are all plain CSS/HTML (:hover, position: sticky,
<a href="#...">).

Usage:
    python contour_gallery.py                            # Flavia (default)
    GALLERY_DATASET=MPEG7 python contour_gallery.py
    GALLERY_MAX_PER_CLASS=30 python contour_gallery.py   # cap per class (large datasets)
"""

import os
from multiprocessing import Pool

import numpy as np

from mendeley_400pt_flusser_rf import DATA_DIR, DATASETS, ROOT_DIR
from shape_qc import _check_one

GALLERY_DIR = os.path.join(ROOT_DIR, "galleries")
N_RENDER_PTS = 100  # downsample 400 -> 100 pts/shape for lightweight SVGs

# Filenames each dataset is deployed under in the flavia-shape-gallery repo
# (Flavia stays "index.html" -- that's the site's original root page, and a
# shared link to it with a "#class-N" anchor must keep working, so it can't
# move to its own flavia.html). Used only to build the cross-dataset nav
# strip below; contour_gallery.py itself still writes every dataset to
# galleries/{name}_gallery.html regardless of this mapping -- the rename
# happens when copying into the deployed repo.
PAGE_FILENAMES = {
    "BBBC010": "bbbc010.html",
    "Flavia": "index.html",
    "HeLa_Kyoto": "hela-kyoto.html",
    "MOC": "moc.html",
    "MPEG400": "mpeg400.html",
    "MPEG7": "mpeg7.html",
    "Mendeley": "mendeley.html",
    "Swedish_SE_SL": "swedish-se-sl.html",
}

# Pretty display name for each dataset key -- falls back to
# name.replace("_", " ") for anything not listed here.
DISPLAY_NAMES = {
    "Swedish_SE_SL": "Swedish Leaves",
}


def display_name(name):
    return DISPLAY_NAMES.get(name, name.replace("_", " "))


def build_site_nav(current):
    links = []
    for name, page in PAGE_FILENAMES.items():
        active = ' aria-current="page"' if name == current else ""
        links.append(f'<a href="{page}"{active}>{display_name(name)}</a>')
    return "".join(links)


def shoelace_area(z):
    x, y = z.real, z.imag
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def to_svg_points(z, pad=6, size=100):
    x, y = z.real, z.imag
    xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
    w, h = xmax - xmin, ymax - ymin
    scale = (size - 2 * pad) / max(w, h, 1e-9)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    sx = (x - cx) * scale + size / 2
    sy = -(y - cy) * scale + size / 2  # flip y: SVG y-axis points down
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(sx, sy))


def build_gallery(name, contours_file, labels_file, pool, n_jobs, max_per_class=None):
    contours = np.load(os.path.join(DATA_DIR, contours_file), allow_pickle=True)
    labels = np.load(os.path.join(ROOT_DIR, labels_file), allow_pickle=True).astype(int)

    chunksize = max(1, len(contours) // (n_jobs * 4))
    checks = pool.map(_check_one, list(contours), chunksize=chunksize)

    by_class = {}
    n_flagged = 0
    for i, (z, lab, check) in enumerate(zip(contours, labels, checks)):
        if not check["ok"]:
            n_flagged += 1
        idx = np.linspace(0, len(z) - 1, N_RENDER_PTS).astype(int)
        pts = to_svg_points(z[idx])
        area = shoelace_area(z)
        by_class.setdefault(int(lab), []).append((i, pts, area, not check["ok"]))

    if max_per_class:
        by_class = {c: items[:max_per_class] for c, items in by_class.items()}

    class_ids = sorted(by_class.keys())
    nav_pills = "\n".join(
        f'<a class="pill" href="#class-{c}">{c:02d}<span class="pill-n">{len(by_class[c])}</span></a>'
        for c in class_ids
    )

    sections = []
    for c in class_ids:
        cards = []
        for idx, pts, area, flagged in by_class[c]:
            flag_cls = " flagged" if flagged else ""
            flag_tip = "<span>flagged by shape_qc</span>" if flagged else ""
            cards.append(
                f'<div class="card{flag_cls}" tabindex="0">'
                f'<svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">'
                f'<polygon points="{pts}"></polygon></svg>'
                f'<div class="cap">#{idx}</div>'
                f'<div class="tip"><span>index {idx}</span><span>class {c}</span>'
                f'<span>area {area:,.0f}</span>{flag_tip}</div>'
                f'</div>'
            )
        sections.append(
            f'<section class="class-block" id="class-{c}">'
            f'<div class="class-head"><h2>Class {c:02d}</h2>'
            f'<span class="class-count">{len(by_class[c])} specimens</span></div>'
            f'<div class="grid">{"".join(cards)}</div>'
            f'</section>'
        )

    total = sum(len(v) for v in by_class.values())
    html_out = HTML_TEMPLATE.format(
        dataset=display_name(name), total=total, n_classes=len(class_ids), n_flagged=n_flagged,
        nav_pills=nav_pills, sections="".join(sections),
        site_nav=build_site_nav(name), n_render_pts=N_RENDER_PTS,
    )

    os.makedirs(GALLERY_DIR, exist_ok=True)
    out_path = os.path.join(GALLERY_DIR, f"{name}_gallery.html")
    with open(out_path, "w") as f:
        f.write(html_out)
    print(f"{name}: {total} shapes, {len(class_ids)} classes, {n_flagged} flagged -> {out_path}")
    return out_path


HTML_TEMPLATE = """<title>{dataset}</title>
<style>
  :root {{
    --bg: #10160f;
    --surface: #1b231a;
    --surface-hi: #232c21;
    --ink: #ede7d8;
    --muted: #8b9186;
    --accent: #c9a34e;
    --rule: #2c352a;
    --rust: #b5543a;
    --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
    --sans: ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --mono: ui-monospace, "SF Mono", "Menlo", "Consolas", monospace;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--ink);
    font-family: var(--sans);
    line-height: 1.5;
  }}
  a {{ color: inherit; }}

  nav.sitenav {{
    display: flex;
    gap: 1.1rem;
    flex-wrap: wrap;
    padding: 0.7rem clamp(1.25rem, 4vw, 3rem);
    background: var(--surface);
    border-bottom: 1px solid var(--rule);
    font-family: var(--mono);
    font-size: 0.72rem;
  }}
  .sitenav a {{
    color: var(--muted);
    text-decoration: none;
    padding-bottom: 0.15rem;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
  }}
  .sitenav a:hover, .sitenav a:focus-visible {{ color: var(--ink); }}
  .sitenav a[aria-current="page"] {{ color: var(--accent); border-color: var(--accent); }}

  header.masthead {{
    padding: 2.75rem clamp(1.25rem, 4vw, 3rem) 1.5rem;
    border-bottom: 1px solid var(--rule);
  }}
  .eyebrow {{
    font-family: var(--mono);
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 0.6rem;
  }}
  h1 {{
    font-family: var(--serif);
    font-weight: 500;
    font-size: clamp(1.8rem, 3vw, 2.6rem);
    margin: 0 0 0.5rem;
    text-wrap: balance;
    letter-spacing: 0.01em;
  }}
  .sub {{
    color: var(--muted);
    max-width: 62ch;
    margin: 0 0 1.4rem;
    font-size: 0.95rem;
  }}
  .stats {{
    display: flex;
    gap: clamp(1.25rem, 3vw, 2.5rem);
    flex-wrap: wrap;
    font-family: var(--mono);
    font-variant-numeric: tabular-nums;
  }}
  .stat b {{ display: block; font-size: 1.4rem; color: var(--ink); }}
  .stat span {{
    display: block;
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-top: 0.15rem;
  }}

  nav.classnav {{
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    padding: 0.75rem clamp(1.25rem, 4vw, 3rem);
    background: rgba(16, 22, 15, 0.92);
    backdrop-filter: blur(6px);
    border-bottom: 1px solid var(--rule);
  }}
  .pill {{
    font-family: var(--mono);
    font-size: 0.72rem;
    text-decoration: none;
    color: var(--muted);
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: 0.2rem 0.5rem;
    display: inline-flex;
    gap: 0.35rem;
    align-items: baseline;
    transition: border-color 0.15s, color 0.15s;
  }}
  .pill:hover, .pill:focus-visible {{ border-color: var(--accent); color: var(--ink); }}
  .pill-n {{ color: var(--accent); }}

  main {{ padding: 0.5rem clamp(1.25rem, 4vw, 3rem) 4rem; }}

  .class-block {{ padding-top: 2.25rem; scroll-margin-top: 3.25rem; }}
  .class-head {{
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 0.4rem;
    margin-bottom: 0.9rem;
  }}
  .class-head h2 {{
    font-family: var(--serif);
    font-weight: 500;
    font-size: 1.15rem;
    margin: 0;
    color: var(--accent);
  }}
  .class-count {{ font-family: var(--mono); font-size: 0.72rem; color: var(--muted); }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(76px, 1fr));
    gap: 0.4rem;
  }}
  .card {{
    position: relative;
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 0.3rem;
    cursor: default;
    transition: transform 0.12s ease, border-color 0.12s ease, background 0.12s ease;
  }}
  .card:hover, .card:focus-visible {{
    transform: translateY(-2px) scale(1.05);
    border-color: var(--accent);
    background: var(--surface-hi);
    z-index: 2;
    outline: none;
  }}
  .card.flagged {{ border-color: var(--rust); }}
  .card svg {{ width: 100%; height: auto; display: block; }}
  .card polygon {{ fill: none; stroke: var(--ink); stroke-width: 2.5; stroke-linejoin: round; }}
  .card.flagged polygon {{ stroke: var(--rust); }}
  .cap {{
    font-family: var(--mono);
    font-size: 0.58rem;
    color: var(--muted);
    text-align: center;
    margin-top: 0.15rem;
  }}
  .tip {{
    position: absolute;
    bottom: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    background: var(--surface-hi);
    border: 1px solid var(--accent);
    border-radius: 4px;
    padding: 0.35rem 0.55rem;
    font-family: var(--mono);
    font-size: 0.66rem;
    white-space: nowrap;
    display: none;
    flex-direction: column;
    gap: 0.1rem;
    color: var(--ink);
    box-shadow: 0 6px 18px rgba(0,0,0,0.4);
  }}
  .card:hover .tip, .card:focus-visible .tip {{ display: flex; }}

  footer {{
    padding: 1.5rem clamp(1.25rem, 4vw, 3rem) 3rem;
    color: var(--muted);
    font-size: 0.8rem;
    font-family: var(--mono);
  }}
</style>

<nav class="sitenav">{site_nav}</nav>

<header class="masthead">
  <p class="eyebrow">Varifold-Moments &middot; shape_qc pass</p>
  <h1>{dataset} contours</h1>
  <p class="sub">Every cleaned {dataset} silhouette, grouped by class, for a quick visual scan.
     A rust outline marks a shape shape_qc.py flagged (non-finite coordinates, non-positive
     area, a turning number away from &plusmn;2&pi;, or a self-intersection).</p>
  <div class="stats">
    <div class="stat"><b>{total:,}</b><span>Specimens</span></div>
    <div class="stat"><b>{n_classes}</b><span>Classes</span></div>
    <div class="stat"><b>{n_flagged}</b><span>Flagged</span></div>
  </div>
</header>

<nav class="classnav">{nav_pills}</nav>

<main>
{sections}
</main>

<footer>Rendered at {n_render_pts} points/shape (downsampled from the native 400) purely for silhouette
legibility at thumbnail scale — index and area above are computed from the full-resolution
contour.</footer>
"""


def main():
    dataset = os.environ.get("GALLERY_DATASET", "Flavia")
    max_per_class = os.environ.get("GALLERY_MAX_PER_CLASS")
    max_per_class = int(max_per_class) if max_per_class else None

    by_name = {n: (f, l) for n, f, l in DATASETS}
    if dataset not in by_name:
        raise ValueError(f"unknown dataset {dataset!r}, choose from {list(by_name)}")
    contours_file, labels_file = by_name[dataset]

    n_jobs = int(os.environ.get("SLURM_CPUS_PER_TASK", os.cpu_count() or 1))
    with Pool(n_jobs) as pool:
        build_gallery(dataset, contours_file, labels_file, pool, n_jobs, max_per_class)


if __name__ == "__main__":
    main()
