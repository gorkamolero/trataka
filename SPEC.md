# H1B Small-Software-Sponsor Finder — Spec

## Objective

Build a dataset of small software companies in Missouri and Texas that sponsor
H1B/LCA filings, biased toward LLCs with ~2–10 employees registered to small
(non-tower) buildings. Free sources only, for now.

## Scope

- **Geography:** MO + TX to start; design so adding states is config, not rework.
- **Industry:** software companies only.
- **Output:** a clean, deduplicated, queryable dataset with an exportable filtered list.

## Inputs (all free/public)

- Federal H1B/LCA disclosure data (the sponsorship signal).
- Federal H1B approval-count data (corroboration).
- State business registries (entity type + registered address).
- Free address-geocoding and open building-data sources (for the "small building" signal).
- A free company-registry API as fallback where state bulk data is thin.

## Filters & signals

1. **Sponsorship** — has certified H1B/LCA filings. (Hard filter.)
2. **Software** — matches a defined set of software industry codes. (Hard filter.)
3. **State** — MO or TX. (Hard filter.)
4. **LLC** — entity type is an LLC. (Hard filter, with a review queue for ambiguous matches.)
5. **Small building** — scored 0–1, not a hard cut, using building size/type and
   penalties for known virtual-office and registered-agent addresses.
6. **Headcount (2–10)** — no free source gives reliable headcount, so this is a
   confidence proxy derived from filing volume + building size, never a fabricated
   number. Reported as low/medium confidence with actual headcount marked unknown.

## Output

A per-company record: name, industry code, entity type, address + location,
building score and flags, filing counts and job titles, approval counts,
size-confidence, source links, and first/last-seen dates. Delivered as a
queryable store plus a filtered CSV export.

## Operating assumptions

- Federal data refreshes quarterly → re-run per release; track appearance over time.
- Cross-source name matching is the main error source → fuzzy match with a
  manual-review queue for low-confidence cases.
- Building and headcount are proxies → output is leads to verify, not ground truth.
- Stick to official bulk downloads and free APIs; avoid sources whose terms
  prohibit scraping.

## Build order (value-first)

1. Sponsorship + software + state filter → an immediate real list.
2. Dedupe + CSV export → usable output fast.
3. LLC gate → biggest precision gain.
4. Building + headcount scoring → refinement last.
