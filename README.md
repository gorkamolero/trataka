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

## Data sources (all free)

- **DOL OFLC LCA disclosure data** — the sponsorship signal (certified H1B/LCA filings).
- **USCIS H-1B Employer Data Hub** — approval-count corroboration.
- **Missouri / Texas Secretary of State business registries** — entity type + registered address.
- **U.S. Census geocoder + OpenStreetMap/Overpass** — geocoding and building footprints.
- **OpenCorporates API** — fallback company registry where state bulk data is thin.

Stick to official bulk downloads and free APIs. Sources whose terms prohibit
scraping are avoided.

## Status

Scaffold + Phase 1/2 pipeline (filter, dedupe, export) implemented. Phases 3–4
(LLC gate, building/headcount scoring) are wired into the pipeline with working
interfaces and are progressively being filled in. See the implementation plan
for the milestone breakdown.
