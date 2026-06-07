from visa_finder.config import load_config
from visa_finder.models import Company, EntityType, ReviewStatus
from visa_finder.pipeline.scoring import apply_llc_gate, score_building, score_headcount
from visa_finder.sources.registry import RegistryRecord


def _company(name, etype=EntityType.UNKNOWN, source=None, **kw):
    return Company(
        company_id=name,
        name=name,
        normalized_name=name.lower(),
        entity_type=etype,
        entity_type_source=source,
        **kw,
    )


def test_llc_gate_registry_confirmed_passes_without_review():
    comp = _company("Acme", etype=EntityType.UNKNOWN)
    registry = {
        "acme": RegistryRecord(
            normalized_name="acme", raw_name="Acme LLC", entity_type=EntityType.LLC
        )
    }
    passing, review = apply_llc_gate([comp], registry)
    assert len(passing) == 1
    assert not review
    assert passing[0].entity_type_source == "registry"


def test_llc_gate_name_inferred_llc_passes_but_flags_review():
    comp = _company("Beta LLC", etype=EntityType.LLC, source="name_inference")
    passing, review = apply_llc_gate([comp], registry={})
    assert len(passing) == 1
    assert len(review) == 1
    assert passing[0].review_status == ReviewStatus.NEEDS_REVIEW.value


def test_llc_gate_drops_known_non_llc():
    comp = _company("Gamma Inc", etype=EntityType.CORP, source="name_inference")
    passing, review = apply_llc_gate([comp], registry={})
    assert not passing
    assert not review  # dropped entirely


def test_llc_gate_unknown_goes_to_review():
    comp = _company("Delta", etype=EntityType.UNKNOWN)
    passing, review = apply_llc_gate([comp], registry={})
    assert not passing
    assert len(review) == 1


def test_building_score_penalizes_virtual_office():
    cfg = load_config().scoring
    comp = _company("VO Co", address="123 Main St, Regus Center")
    score_building(comp, footprint_sqm=150, levels=2, cfg=cfg)
    assert "virtual_office" in comp.building_flags
    assert comp.building_score < 0.5  # small building, but heavy penalty


def test_building_score_small_standalone_is_high():
    cfg = load_config().scoring
    comp = _company("Small Co", address="42 Quiet Ln")
    score_building(comp, footprint_sqm=150, levels=1, cfg=cfg)
    assert comp.building_score == 1.0


def test_headcount_confidence_band():
    cfg = load_config().scoring
    small = _company("Small", lca_filing_count=2, building_score=0.9)
    score_headcount(small, cfg)
    assert small.in_target_band is True
    assert small.size_confidence == "medium"  # building corroborates
    assert small.headcount == "unknown"

    big = _company("Big", lca_filing_count=50)
    score_headcount(big, cfg)
    assert big.in_target_band is False
    assert big.headcount == "unknown"
