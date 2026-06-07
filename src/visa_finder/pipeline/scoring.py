"""Phase 3–4 refinements: the LLC gate and the building / headcount scoring.

These run after dedupe and never invent data — missing inputs leave the relevant
field unset and lower the confidence rather than guessing.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..models import Company, Confidence, EntityType, ReviewStatus
from ..sources.registry import RegistryRecord

# Known virtual-office / registered-agent / mailbox markers used to penalize the
# building score. Extend as you encounter more providers.
VIRTUAL_OFFICE_MARKERS = (
    "regus", "wework", "spaces", "intelligent office", "davinci", "opus virtual",
    "alliance virtual", "premier workspaces",
)
REGISTERED_AGENT_MARKERS = (
    "registered agent", "northwest registered", "cogency", "ct corporation",
    "corporation service company", "csc", "incfile", "legalzoom", "harbor compliance",
    "national registered agents",
)
PO_BOX_MARKERS = ("po box", "p.o. box", "p o box", "mailbox", "the ups store")


# ---- Signal #4: LLC gate ----------------------------------------------------

def apply_llc_gate(
    companies: list[Company],
    registry: Mapping[str, RegistryRecord],
) -> tuple[list[Company], list[Company]]:
    """Attach entity type from the registry and split into (passing, review).

    Returns (llc_companies, review_queue). Companies whose entity type cannot be
    determined are routed to the review queue rather than dropped or assumed.
    """
    passing: list[Company] = []
    review: list[Company] = []
    for comp in companies:
        rec = registry.get(comp.normalized_name)
        if rec is not None:
            comp.entity_type = rec.entity_type
            comp.entity_type_source = "registry"
            if rec.address and not comp.address:
                comp.address = rec.address
            if rec.city and not comp.city:
                comp.city = rec.city
            if rec.zip and not comp.zip:
                comp.zip = rec.zip

        etype = comp.entity_type
        # Pydantic ``use_enum_values`` may store the raw string.
        etype_val = etype.value if isinstance(etype, EntityType) else etype
        if etype_val == EntityType.LLC.value:
            passing.append(comp)
        elif etype_val == EntityType.UNKNOWN.value:
            comp.review_status = ReviewStatus.NEEDS_REVIEW
            review.append(comp)
        # Non-LLC known types are dropped from the LLC-gated output.
    return passing, review


# ---- Signal #5: small-building score ---------------------------------------

def _smallness(footprint_sqm: float | None, cfg: dict[str, Any]) -> float | None:
    if footprint_sqm is None:
        return None
    small = float(cfg.get("small_footprint_sqm", 200))
    large = float(cfg.get("large_footprint_sqm", 5000))
    if footprint_sqm <= small:
        return 1.0
    if footprint_sqm >= large:
        return 0.0
    # Linear interpolation between small and large.
    return round(1.0 - (footprint_sqm - small) / (large - small), 3)


def score_building(
    comp: Company,
    footprint_sqm: float | None,
    levels: int | None,
    cfg: dict[str, Any],
) -> None:
    """Set ``building_score`` (0..1) and ``building_flags`` on the company.

    Penalties for virtual-office / registered-agent / PO-box / high-rise are
    applied based on the address text and building tags.
    """
    bcfg = cfg.get("building", {})
    flags: list[str] = []
    base = _smallness(footprint_sqm, bcfg)

    addr = (comp.address or "").lower()
    penalties = bcfg.get("penalties", {})
    penalty = 0.0

    if any(m in addr for m in VIRTUAL_OFFICE_MARKERS):
        flags.append("virtual_office")
        penalty = max(penalty, float(penalties.get("virtual_office", 0.8)))
    if any(m in addr for m in REGISTERED_AGENT_MARKERS):
        flags.append("registered_agent")
        penalty = max(penalty, float(penalties.get("registered_agent", 0.6)))
    if any(m in addr for m in PO_BOX_MARKERS):
        flags.append("po_box")
        penalty = max(penalty, float(penalties.get("po_box", 0.7)))
    if levels is not None and levels >= int(bcfg.get("high_rise_levels", 8)):
        flags.append("high_rise")
        penalty = max(penalty, float(penalties.get("high_rise", 0.5)))

    if base is None:
        # No footprint; score only reflects penalties if any flag fired.
        comp.building_score = None if not flags else round(max(0.0, 1.0 - penalty), 3)
    else:
        comp.building_score = round(max(0.0, min(1.0, base - penalty)), 3)
    comp.building_flags = flags


# ---- Signal #6: headcount confidence proxy ---------------------------------

def score_headcount(comp: Company, cfg: dict[str, Any]) -> None:
    """Set ``in_target_band`` and ``size_confidence``.

    Headcount itself stays ``unknown`` — this is a confidence proxy derived from
    filing volume and the building score, never a fabricated count.
    """
    hcfg = cfg.get("headcount", {})
    fv = hcfg.get("filing_volume", {})
    plausible_min = int(fv.get("plausible_min", 1))
    plausible_max = int(fv.get("plausible_max", 6))
    too_many = int(fv.get("too_many", 20))

    n = comp.lca_filing_count
    building = comp.building_score

    if n >= too_many:
        comp.in_target_band = False
        comp.size_confidence = Confidence.LOW
    elif plausible_min <= n <= plausible_max:
        comp.in_target_band = True
        # Building corroboration bumps confidence from low to medium.
        comp.size_confidence = (
            Confidence.MEDIUM if (building is not None and building >= 0.5) else Confidence.LOW
        )
    else:
        comp.in_target_band = None
        comp.size_confidence = Confidence.LOW

    comp.headcount = "unknown"  # invariant: never fabricated
