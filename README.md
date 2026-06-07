# H1B Small-Software-Sponsor Finder

Builds a deduplicated, queryable dataset of **small software companies in Missouri
and Texas that sponsor H1B/LCA filings** — biased toward LLCs with ~2–10 employees
registered to small (non-tower) buildings.

Free / public sources only. Output is **leads to verify, not ground truth**.

> Note: this project currently lives in a repo named `trataka` for practical reasons.
> The package and tooling are all named `visa-finder`.

## What it does

Given quarterly federal disclosure data plus state registries and open building
data, it produces a per-company record and a filtered CSV export of qualifying
leads.

### Filters & signals

| # | Signal | Type | Source |
|---|--------|------|--------|
| 1 | Has certified H1B/LCA filings | hard filter | DOL OFLC LCA disclosure data |
| 2 | Software company (industry codes) | hard filter | NAICS / SOC code sets |
| 3 | State is MO or TX | hard filter | filing + registry address |
| 4 | Entity type is LLC | hard filter (+ review queue) | state business registries |
| 5 | Small building | score 0–1 | geocoding + open building data |
| 6 | Headcount 2–10 | confidence proxy | filing volume + building size |

Building and headcount are **proxies**. Headcount is never fabricated — actual
headcount is reported as `unknown` with a low/medium confidence band.

## Build order (value-first)

1. **Sponsorship + software + state filter** → an immediate real list.
2. **Dedupe + CSV export** → usable output fast.
3. **LLC gate** → biggest precision gain.
4. **Building + headcount scoring** → refinement last.

See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for architecture and
[`SPEC.md`](SPEC.md) for the planning-level spec.

## Quick start

```bash
# Install (editable) + dev deps
pip install -e ".[dev]"

# 1. Download the source files you want (prints URLs + saves to data/raw)
visa-finder sources list
visa-finder sources fetch lca --year 2024

# 2. Run the pipeline (Phase 1+2: filter + dedupe + export)
visa-finder run --states MO,TX --out leads.csv

# 3. Query the store directly
visa-finder query "SELECT name, city, lca_filing_count FROM companies ORDER BY lca_filing_count DESC LIMIT 20"
```

Adding a state is config, not code — see `config/states.yaml`.

## Map viewer (LibreMap)

A static, no-API-key map viewer lives in [`web/`](web/), built on
**MapLibre GL** with free OpenStreetMap-based vector tiles. It plots leads,
colours them by entity type (LLC vs other), sizes them by filing volume, and
offers LLC-only / target-band / min-filings filters plus a synced sidebar list.

Generate the map data from real pipeline output:

```bash
visa-finder run --states MO,TX --out leads.csv --geojson web/data/leads.geojson
```

Or build a SAMPLE map (synthetic companies placed at city centroids — clearly
flagged in the UI) without any downloads:

```bash
visa-finder demo            # writes web/data/leads.geojson
python -m http.server -d web 8000   # open http://localhost:8000
```

### Standalone single-file build (no server)

For a viewer you can just open in a browser — no web server, no hosting — build a
self-contained HTML with the data inlined:

```bash
visa-finder demo                      # or: run --geojson web/data/leads.geojson
python scripts/build_standalone.py    # -> dist/visa-finder-map.html
```

Open `dist/visa-finder-map.html` directly (MapLibre loads from its CDN; the
browser fetches tiles).

### Hosting

The viewer auto-deploys to **GitHub Pages** via
[`.github/workflows/pages.yml`](.github/workflows/pages.yml): CI builds the
sample GeoJSON and publishes `web/`. The published URL will be
`https://gorkamolero.github.io/trataka/`.

> Requires GitHub Actions to be enabled for the repo (Settings → Actions →
> General → "Allow all actions"). If Actions jobs fail instantly with no logs
> (startup failure, no runner assigned), Actions is disabled or the account
> needs email/billing verification — enable it, then re-run the workflow. Pages
> on a private repo also needs a paid plan; on a public repo it is free.

## Data sources (all free)

- **DOL OFLC LCA disclosure data** — the sponsorship signal (certified H1B/LCA filings).
- **USCIS H-1B Employer Data Hub** — approval-count corroboration.
- **Missouri / Texas Secretary of State business registries** — entity type + registered address.
- **U.S. Census geocoder + OpenStreetMap/Overpass** — geocoding and building footprints.
- **OpenCorporates API** — fallback company registry where state bulk data is thin.

Stick to official bulk downloads and free APIs. Sources whose terms prohibit
scraping are avoided.

## Status

All four phases implemented end to end: hard filters → dedupe (with fuzzy merge +
review queue) → LLC gate → building/headcount scoring. USCIS approval counts are
joined as corroboration when present. A MapLibre map viewer ships in `web/` and
deploys to GitHub Pages. Phases 3–4 activate fully once you drop the relevant
free source files into `data/raw/` (registry exports, building lookups). See
[`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for details.
