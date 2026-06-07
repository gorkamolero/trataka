from pathlib import Path

from visa_finder.config import load_config
from visa_finder.export import export_markdown
from visa_finder.pipeline.run import run
from visa_finder.store import Store

FIXTURE = Path(__file__).parent / "fixtures" / "lca_sample.csv"


def test_markdown_report_has_table_and_maps_links(tmp_path):
    cfg = load_config()
    result = run(FIXTURE, ["MO", "TX"], cfg=cfg, apply_llc=False)
    db = tmp_path / "m.duckdb"
    out = tmp_path / "report.md"
    with Store(db) as store:
        store.upsert(result.companies)
        n = export_markdown(store, out, states=["MO", "TX"], sample=True)

    text = out.read_text()
    assert n == 3
    assert "# H1B Small-Software-Sponsor Finder" in text
    assert "SAMPLE DATA" in text  # sample flag honoured
    assert "| # | Company |" in text  # table header
    # One Google Maps link per company.
    assert text.count("https://www.google.com/maps/search/") >= 3
    assert "Synthetic Software LLC" in text
