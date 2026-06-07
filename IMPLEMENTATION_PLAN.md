# Implementation Plan

Architecture and milestones for the H1B Small-Software-Sponsor Finder.

## Tech choices

- **Python 3.10+** — best ecosystem for this dedup-heavy, fuzzy-matched data work.
- **DuckDB** — single-file, SQL-queryable store; trivial CSV export; handles the
  joins and aggregations well without standing up a server.
- **pandas** — tolerant readers for the messy DOL/registry spreadsheets.
- **rapidfuzz** — fast fuzzy matching for cross-source name resolution.
- **pydantic v2** — the per-company record schema with validation.
- **click** — CLI.

## Repository layout

```
config/
  states.yaml          # geography is config, not code
  software_codes.yaml  # the "software" definition (NAICS + SOC)
  scoring.yaml         # building / headcount tunables
src/visa_finder/
  models.py            # Company + LcaFiling schema
  normalize.py         # shared name normalization + stable id
  config.py            # typed config loader
  store.py             # DuckDB store (upsert by company_id, first/last seen)
  export.py            # filtered CSV exports (leads + review queue)
  cli.py               # `visa-finder` command
  sources/             # one adapter per free/public input
    lca.py             # DOL OFLC disclosure data  (signal #1)
    h1b_hub.py         # USCIS approval counts      (corroboration)
    registry.py        # MO/TX registries          (signal #4)
    building.py        # Census geocoder + Overpass (signal #5)
    opencorporates.py  # registry fallback
  pipeline/
    filters.py         # hard filters #1-#3
    dedupe.py          # exact collapse + fuzzy merge + review queue
    scoring.py         # LLC gate #4, building #5, headcount #6
    run.py             # orchestrator (value-first order)
tests/                 # unit tests on synthetic fixtures
```

## Per-company record (schema)

See `src/visa_finder/models.py::Company`. Key invariants:

- `company_id` = sha1(normalized_name + state)[:16] — stable across refreshes.
- `headcount` is **always** `"unknown"`; `size_confidence` (low/medium/high) and
  `in_target_band` carry the proxy signal instead.
- `building_score` ∈ [0,1] or `None` when no footprint is available — never a
  hard cut.
- `review_status` routes low-confidence matches and unknown entity types to a
  human queue instead of guessing.

## Cross-source matching

Name matching is the main error source, so it is centralized:

1. `normalize.normalize_name` strips legal suffixes / punctuation consistently in
   every adapter.
2. Stage-1 dedupe collapses exact `(normalized_name, state)`.
3. Stage-2 fuzzy merge (`rapidfuzz.token_sort_ratio`) merges ≥92 automatically,
   merges 85–92 but flags `needs_review`, and keeps <85 separate.
4. The LLC gate routes `UNKNOWN` entity types to the review queue rather than
   dropping or assuming.

## Build order & milestones

### Phase 1 — Sponsorship + software + state filter ✅
Read DOL LCA files → keep certified, MO/TX, software (NAICS/SOC) filings.
*Done: `sources/lca.py`, `pipeline/filters.py`.*

### Phase 2 — Dedupe + CSV export ✅
Collapse to one company per employer; export filtered leads CSV; persist to
DuckDB with first/last-seen tracking.
*Done: `pipeline/dedupe.py`, `store.py`, `export.py`, `cli.py`.*

### Phase 3 — LLC gate ✅ (wired; needs registry bulk data to activate)
Join registry exports, classify entity type, keep LLCs, queue ambiguous ones.
*Done: `sources/registry.py`, `pipeline/scoring.py::apply_llc_gate`. Drop a MO/TX
registry export into `data/raw/registry/<state>/` to activate.*

### Phase 4 — Building + headcount scoring ✅ (wired; opt-in via `--score-buildings`)
Geocode addresses (Census), fetch footprints (Overpass), score smallness with
virtual-office / registered-agent / high-rise penalties; derive headcount
confidence band.
*Done: `sources/building.py`, `pipeline/scoring.py::score_building/score_headcount`.*

## Operational notes

- DOL data refreshes quarterly → re-run per release; `upsert` accumulates and
  `last_seen` tracks appearance over time.
- USCIS H-1B Employer Data Hub provides `approval_count` corroboration (loader in
  `sources/h1b_hub.py`; joining it into the store is the next small task).
- All building/headcount output is **leads to verify**, not ground truth.

## Next tasks (smallest valuable increments)

1. Join `h1b_hub` approval counts into the store after dedupe.
2. Add a `geocode-batch` command using the Census *batch* endpoint (faster than
   per-address) for Phase 4 at scale.
3. Expand virtual-office / registered-agent marker lists from observed data.
4. Add an `--quarter` flag to tag each run for appearance-over-time reporting.
