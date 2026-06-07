#!/usr/bin/env python3
"""Build a single self-contained HTML file of the map viewer.

Inlines style.css, app.js, and the leads GeoJSON into one HTML document so it
works by simply opening the file in a browser (file://) — no web server and no
GitHub Pages required. MapLibre GL itself is still loaded from its CDN, which the
browser fetches directly.

Usage:
    python scripts/build_standalone.py [--data web/data/leads.geojson] [--out dist/visa-finder-map.html]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def build(data_path: Path, out_path: Path) -> int:
    style = (WEB / "style.css").read_text()
    app = (WEB / "app.js").read_text()
    geojson = json.loads(data_path.read_text())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>H1B Small-Software-Sponsor Finder — MO/TX</title>
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" />
  <style>
{style}
  </style>
</head>
<body>
  <div id="app">
    <aside id="sidebar">
      <header>
        <h1>H1B Small-Software-Sponsor Finder</h1>
        <p class="subtitle">Small software companies in MO &amp; TX with H1B/LCA filings — leads to verify, not ground truth.</p>
        <div id="sample-banner" class="banner hidden">
          Showing <strong>SAMPLE</strong> data (synthetic companies at city centroids).
          Run the pipeline with real DOL data for live leads.
        </div>
      </header>
      <div class="controls">
        <label class="check"><input type="checkbox" id="llc-only" /> LLC only</label>
        <label class="check"><input type="checkbox" id="band-only" /> In target band (2&ndash;10)</label>
        <label class="range">
          Min filings: <span id="minf-val">1</span>
          <input type="range" id="min-filings" min="1" max="20" value="1" />
        </label>
      </div>
      <div id="stats" class="stats"></div>
      <ul id="list" class="list"></ul>
      <footer>
        <span id="count"></span> &middot;
        <a href="https://github.com/gorkamolero/trataka" target="_blank" rel="noopener">source</a>
      </footer>
    </aside>
    <main id="map"></main>
  </div>

  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>window.__LEADS__ = {json.dumps(geojson)};</script>
  <script>
{app}
  </script>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return len(geojson.get("features", []))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(WEB / "data" / "leads.geojson"))
    ap.add_argument("--out", default=str(ROOT / "dist" / "visa-finder-map.html"))
    args = ap.parse_args()
    n = build(Path(args.data), Path(args.out))
    print(f"Wrote standalone viewer with {n} features -> {args.out}")


if __name__ == "__main__":
    main()
