"""Pipeline orchestrator — wires the phases together in value-first order.

  Phase 1: hard filters (sponsorship + software + state)
  Phase 2: dedupe -> Company records -> store
  Phase 3: LLC gate (if a registry export is available)
  Phase 4: building + headcount scoring (if enabled)

Each later phase is optional and degrades gracefully: with no registry data the
LLC gate is skipped (entity types stay UNKNOWN and route to review); with
building lookups disabled the building score stays unset.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config, data_dir, load_config
from ..models import Company, LcaFiling
from ..normalize import normalize_name
from ..sources import h1b_hub as hub_source
from ..sources import lca as lca_source
from ..sources.registry import RegistryRecord, get_adapter
from . import dedupe as dedupe_mod
from . import filters as filters_mod
from . import scoring as scoring_mod


@dataclass
class RunResult:
    companies: list[Company]
    review_queue: list[Company] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


def _load_filings(lca_path: Path, states: list[str] | None = None) -> Iterator[LcaFiling]:
    if lca_path.is_dir():
        yield from lca_source.read_lca_dir(lca_path, states=states)
    else:
        yield from lca_source.read_lca_file(lca_path, states=states)


def _load_registry(cfg: Config, states: list[str]) -> dict[str, RegistryRecord]:
    """Build {normalized_name: RegistryRecord} from any available bulk exports
    under data/raw/registry/<state>/."""
    registry: dict[str, RegistryRecord] = {}
    base = data_dir() / "raw" / "registry"
    for code in states:
        st_cfg = cfg.states.get(code)
        if not st_cfg:
            continue
        st_dir = base / code.lower()
        if not st_dir.exists():
            continue
        adapter = get_adapter(st_cfg.registry.adapter)
        for path in sorted(st_dir.glob("*")):
            if path.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
                continue
            for rec in adapter(path):
                # Keep the first/most-specific record per name.
                registry.setdefault(rec.normalized_name, rec)
    return registry


def _load_approvals() -> dict[tuple[str, str], int]:
    """Aggregate USCIS H-1B Employer Data Hub approval counts, if present."""
    approvals: dict[tuple[str, str], int] = {}
    base = data_dir() / "raw" / "h1b_hub"
    if not base.exists():
        return approvals
    for path in sorted(base.glob("*")):
        if path.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
            continue
        for key, count in hub_source.load_approval_counts(path).items():
            approvals[key] = approvals.get(key, 0) + count
    return approvals


def _attach_approvals(companies: list[Company], approvals: dict[tuple[str, str], int]) -> int:
    """Corroborate filings with approval counts, matched on (normalized name, state)."""
    attached = 0
    for comp in companies:
        key = (normalize_name(comp.name), (comp.state or "").upper())
        count = approvals.get(key)
        if count is None:
            # Fall back to a name-only match across the company's aliases.
            for alias in [comp.name, *comp.aliases]:
                count = approvals.get((normalize_name(alias), (comp.state or "").upper()))
                if count is not None:
                    break
        if count is not None:
            comp.approval_count = count
            attached += 1
    return attached


def run(
    lca_path: str | Path,
    states: list[str] | None = None,
    *,
    cfg: Config | None = None,
    apply_llc: bool = True,
    apply_scoring: bool = False,
    exclude_staffing: bool = False,
) -> RunResult:
    cfg = cfg or load_config()
    states = states or cfg.enabled_states()
    lca_path = Path(lca_path)
    stats: dict[str, int] = {}

    # Phase 1 — hard filters (state pre-filter pushed into the reader for speed).
    raw = _load_filings(lca_path, states=states)
    filtered = list(filters_mod.apply_hard_filters(raw, cfg, states))
    stats["filings_after_hard_filters"] = len(filtered)

    # Phase 2 — dedupe.
    companies = dedupe_mod.dedupe(filtered)
    stats["companies_after_dedupe"] = len(companies)

    # Optional: drop IT-staffing / consulting body shops to bias toward product
    # software companies.
    if exclude_staffing:
        before = len(companies)
        companies = [c for c in companies if not cfg.is_staffing(c.name)]
        stats["excluded_staffing"] = before - len(companies)

    # Corroboration — attach USCIS approval counts if available.
    approvals = _load_approvals()
    if approvals:
        stats["approval_records"] = len(approvals)
        stats["companies_with_approvals"] = _attach_approvals(companies, approvals)

    review_queue: list[Company] = []

    # Phase 3 — LLC gate (only if registry data is present).
    if apply_llc:
        registry = _load_registry(cfg, states)
        stats["registry_records"] = len(registry)
        if registry:
            companies, review_queue = scoring_mod.apply_llc_gate(companies, registry)
            stats["companies_after_llc_gate"] = len(companies)
            stats["review_queue"] = len(review_queue)

    # Phase 4 — building + headcount scoring.
    if apply_scoring:
        from ..sources import building as building_source

        scored = 0
        for comp in companies:
            if comp.address:
                full = ", ".join(
                    p for p in [comp.address, comp.city, comp.state, comp.zip] if p
                )
                info = building_source.lookup(full)
                if info:
                    comp.latitude = info.latitude
                    comp.longitude = info.longitude
                    scoring_mod.score_building(
                        comp, info.footprint_sqm, info.levels, cfg.scoring
                    )
                    scored += 1
            scoring_mod.score_headcount(comp, cfg.scoring)
        stats["buildings_scored"] = scored
    else:
        # Headcount confidence can still be set from filing volume alone.
        for comp in companies:
            scoring_mod.score_headcount(comp, cfg.scoring)

    return RunResult(companies=companies, review_queue=review_queue, stats=stats)
