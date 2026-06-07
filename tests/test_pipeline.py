from pathlib import Path

from visa_finder.config import load_config
from visa_finder.export import export_leads
from visa_finder.models import ReviewStatus
from visa_finder.pipeline.run import run
from visa_finder.store import Store

FIXTURE = Path(__file__).parent / "fixtures" / "lca_sample.csv"


def _names(companies):
    return {c.normalized_name for c in companies}


def test_hard_filters_and_dedupe():
    cfg = load_config()
    # LLC gate off here (no registry fixture); just test phases 1-2.
    result = run(FIXTURE, ["MO", "TX"], cfg=cfg, apply_llc=False)
    names = _names(result.companies)

    # Kept: software + MO/TX + certified.
    assert "synthetic software" in names      # MO, two filings, exact-collapsed
    assert "fictional apps" in names          # TX

    # Dropped: denied, retail (non-software), out-of-state.
    assert "rejected co" not in names
    assert "bigbox retail" not in names
    assert "out of state tech" not in names

    # Megacorp is a Corp but software+TX+certified -> still present pre-LLC-gate.
    assert "megacorp systems" in names


def test_exact_collapse_counts_filings():
    cfg = load_config()
    result = run(FIXTURE, ["MO", "TX"], cfg=cfg, apply_llc=False)
    synthetic = next(c for c in result.companies if c.normalized_name == "synthetic software")
    assert synthetic.lca_filing_count == 2     # two MO filings collapsed
    assert len(synthetic.job_titles) == 2


def test_fuzzy_merge_flags_review():
    cfg = load_config()
    result = run(FIXTURE, ["MO", "TX"], cfg=cfg, apply_llc=False)
    # "Fictional Apps LLC" and "Fictional Apps Solutions LLC" should fuzzy-merge.
    fictional = [c for c in result.companies if "fictional apps" in c.normalized_name]
    assert len(fictional) == 1
    merged = fictional[0]
    assert merged.lca_filing_count == 2
    # Merge was below auto threshold -> flagged for review.
    assert merged.review_status == ReviewStatus.NEEDS_REVIEW.value


def test_headcount_never_fabricated():
    cfg = load_config()
    result = run(FIXTURE, ["MO", "TX"], cfg=cfg, apply_llc=False)
    assert all(c.headcount == "unknown" for c in result.companies)
    assert all(c.size_confidence in {"low", "medium", "high"} for c in result.companies)


def test_store_and_export(tmp_path):
    cfg = load_config()
    result = run(FIXTURE, ["MO", "TX"], cfg=cfg, apply_llc=False)
    db = tmp_path / "test.duckdb"
    out = tmp_path / "leads.csv"
    with Store(db) as store:
        store.upsert(result.companies)
        n = export_leads(store, out, states=["MO", "TX"])
        assert n == store.count()
        # Idempotent upsert: re-running does not duplicate.
        store.upsert(result.companies)
        assert store.count() == n
    assert out.exists()
    assert out.read_text().splitlines()[0].startswith("name,")
