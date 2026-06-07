"""Core data model for the per-company lead record.

The output record is intentionally explicit about confidence and provenance:
building size and headcount are *proxies*, so headcount is always reported as
``unknown`` with a confidence band rather than a fabricated number.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    LLC = "LLC"
    CORP = "CORP"
    LP = "LP"
    LLP = "LLP"
    SOLE_PROP = "SOLE_PROP"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewStatus(str, Enum):
    AUTO = "auto"               # passed automatically, no review needed
    NEEDS_REVIEW = "needs_review"  # low-confidence match queued for a human
    CONFIRMED = "confirmed"     # human-confirmed
    REJECTED = "rejected"       # human-rejected


class LcaFiling(BaseModel):
    """A single certified LCA/H1B filing line attributable to an employer."""

    case_number: str | None = None
    employer_name: str
    employer_address1: str | None = None
    employer_address2: str | None = None
    naics_code: str | None = None
    soc_code: str | None = None
    job_title: str | None = None
    worksite_city: str | None = None
    worksite_state: str | None = None
    worksite_zip: str | None = None
    employer_city: str | None = None
    employer_state: str | None = None
    employer_zip: str | None = None
    fiscal_year: int | None = None
    case_status: str | None = None


class Company(BaseModel):
    """The deduplicated per-company lead record — one row per real company."""

    # Identity
    company_id: str = Field(..., description="Stable hash id of the normalized name + state")
    name: str
    normalized_name: str
    aliases: list[str] = Field(default_factory=list)

    # Industry (signal #2)
    naics_code: str | None = None
    naics_description: str | None = None

    # Entity type (signal #4)
    entity_type: EntityType = EntityType.UNKNOWN
    entity_type_source: str | None = None

    # Flagged (not dropped) IT-staffing / consulting body shop
    is_staffing: bool = False

    # Location (signal #3 + basis for #5)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    # Small-building signal (#5) — score in [0,1], not a hard cut
    building_score: float | None = None
    building_flags: list[str] = Field(default_factory=list)

    # Sponsorship signal (#1)
    lca_filing_count: int = 0
    job_titles: list[str] = Field(default_factory=list)
    soc_codes: list[str] = Field(default_factory=list)

    # Corroboration
    approval_count: int | None = None

    # Headcount (#6) — NEVER fabricated
    headcount: str = "unknown"
    size_confidence: Confidence = Confidence.LOW
    in_target_band: bool | None = None  # plausibly 2..10 employees?

    # Match / review bookkeeping
    match_confidence: float | None = None  # 0..1, cross-source name match
    review_status: ReviewStatus = ReviewStatus.AUTO

    # Provenance
    source_links: dict[str, str] = Field(default_factory=dict)
    first_seen: date | None = None
    last_seen: date | None = None

    model_config = {"use_enum_values": True}
