"""Command-line interface.

    visa-finder sources list
    visa-finder sources fetch lca --year 2024
    visa-finder run --states MO,TX --lca data/raw/lca --out leads.csv
    visa-finder query "SELECT name, lca_filing_count FROM companies LIMIT 20"
"""

from __future__ import annotations

from pathlib import Path

import click

from .config import data_dir, load_config
from .export import export_geojson, export_leads, export_markdown, export_review_queue
from .pipeline.run import run as run_pipeline
from .sources import SOURCES, list_sources
from .store import Store

DEFAULT_DB = "visa_finder.duckdb"
SAMPLE_LCA = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "lca_sample.csv"


def _parse_states(states: str | None) -> list[str] | None:
    if not states:
        return None
    return [s.strip().upper() for s in states.split(",") if s.strip()]


@click.group()
def cli() -> None:
    """Find small software companies in MO/TX that sponsor H1B/LCA filings."""


# ---- sources ----------------------------------------------------------------

@cli.group()
def sources() -> None:
    """Inspect and fetch the free/public data sources."""


@sources.command("list")
def sources_list() -> None:
    for s in list_sources():
        ok = "ok" if s.terms_ok else "CHECK TERMS"
        click.echo(f"\n{click.style(s.key, bold=True)}  [{ok}]")
        click.echo(f"  {s.name}")
        click.echo(f"  signal : {s.signal}")
        click.echo(f"  home   : {s.homepage}")
        click.echo(f"  fetch  : {s.fetch_hint}")


@sources.command("fetch")
@click.argument("key")
@click.option("--year", type=int, help="Fiscal year for time-bound sources (e.g. LCA).")
def sources_fetch(key: str, year: int | None) -> None:
    """Print where to get a source and the local path to drop it in.

    We deliberately do not auto-scrape: most of these are large official bulk
    downloads. This prints the homepage and the expected local directory so the
    file lands where the pipeline looks for it.
    """
    info = SOURCES.get(key)
    if not info:
        raise click.ClickException(f"Unknown source {key!r}. Try `visa-finder sources list`.")
    subdir = {
        "lca": Path("lca"),
        "h1b_hub": Path("h1b_hub"),
        "registry_mo": Path("registry/mo"),
        "registry_tx": Path("registry/tx"),
    }.get(key, Path(key))
    dest = data_dir() / "raw" / subdir
    dest.mkdir(parents=True, exist_ok=True)
    click.echo(f"{info.name}")
    click.echo(f"  download from : {info.homepage}")
    click.echo(f"  {info.fetch_hint}")
    if year:
        click.echo(f"  fiscal year   : {year}")
    click.echo(f"  save files to : {dest}")


# ---- run --------------------------------------------------------------------

@cli.command("run")
@click.option("--states", default=None, help="Comma-separated states, e.g. MO,TX.")
@click.option("--lca", "lca_path", default=None, help="LCA file or dir (default: data/raw/lca).")
@click.option("--db", default=DEFAULT_DB, help="DuckDB store path.")
@click.option("--out", default="leads.csv", help="CSV export path.")
@click.option("--llc-only/--no-llc-only", default=False, help="Restrict CSV to entity_type=LLC.")
@click.option("--score-buildings", is_flag=True, help="Enable Phase 4 building lookups (network).")
@click.option("--geojson", "geojson_path", default=None, help="Also write GeoJSON for the map.")
@click.option("--markdown", "markdown_path", default=None, help="Also write a Markdown report.")
def run_cmd(
    states: str | None,
    lca_path: str | None,
    db: str,
    out: str,
    llc_only: bool,
    score_buildings: bool,
    geojson_path: str | None,
    markdown_path: str | None,
) -> None:
    """Run the pipeline and export a filtered CSV."""
    cfg = load_config()
    state_list = _parse_states(states) or cfg.enabled_states()
    lca = Path(lca_path) if lca_path else data_dir() / "raw" / "lca"
    if not lca.exists():
        raise click.ClickException(
            f"No LCA data at {lca}. Run `visa-finder sources fetch lca` and drop the file there."
        )

    result = run_pipeline(
        lca, state_list, cfg=cfg, apply_scoring=score_buildings
    )

    n_geo = None
    with Store(db) as store:
        store.upsert(result.companies)
        if result.review_queue:
            store.upsert(result.review_queue)
        n_leads = export_leads(store, out, states=state_list, llc_only=llc_only)
        rq_path = Path(out).with_name("review_queue.csv")
        n_review = export_review_queue(store, rq_path)
        if geojson_path:
            n_geo = export_geojson(store, geojson_path, states=state_list, llc_only=llc_only)
        if markdown_path:
            export_markdown(store, markdown_path, states=state_list, llc_only=llc_only)
        total = store.count()

    click.echo(click.style("Pipeline complete.", fg="green", bold=True))
    for k, v in result.stats.items():
        click.echo(f"  {k}: {v}")
    click.echo(f"  exported leads: {n_leads} -> {out}")
    click.echo(f"  review queue: {n_review} -> {rq_path}")
    if n_geo is not None:
        click.echo(f"  geojson features: {n_geo} -> {geojson_path}")
    if markdown_path:
        click.echo(f"  markdown report -> {markdown_path}")
    click.echo(f"  total companies in store: {total} ({db})")


@cli.command("demo")
@click.option("--out", default="web/data/leads.geojson", help="GeoJSON output path for the viewer.")
def demo_cmd(out: str) -> None:
    """Build the map viewer's data from the bundled SAMPLE dataset.

    Used by CI to populate the hosted site. The output is clearly marked as
    sample data (synthetic companies placed at city centroids) so the live map
    demonstrates the viewer without implying these are real leads.
    """
    cfg = load_config()
    result = run_pipeline(SAMPLE_LCA, ["MO", "TX"], cfg=cfg, apply_llc=False)
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    db_path = out_path.parent / "demo.duckdb"
    if db_path.exists():
        db_path.unlink()
    with Store(db_path) as store:
        store.upsert(result.companies)
        n = export_geojson(store, out_path, states=["MO", "TX"], use_centroids=True, sample=True)
    db_path.unlink(missing_ok=True)
    click.echo(f"Wrote {n} sample features -> {out_path}")


# ---- query ------------------------------------------------------------------

@cli.command("report")
@click.option("--states", default=None, help="Comma-separated states, e.g. MO,TX.")
@click.option("--lca", "lca_path", default=None, help="LCA file or dir (default: data/raw/lca).")
@click.option("--out", default="report.md", help="Markdown report output path.")
@click.option("--llc-only/--no-llc-only", default=False, help="Restrict to entity_type=LLC.")
def report_cmd(states: str | None, lca_path: str | None, out: str, llc_only: bool) -> None:
    """Write a Markdown findings report (tables + Google Maps links).

    Uses real LCA data when present under data/raw/lca (or --lca); otherwise
    falls back to the bundled SAMPLE dataset, clearly labelled as such.
    """
    cfg = load_config()
    state_list = _parse_states(states) or ["MO", "TX"]
    default_lca = data_dir() / "raw" / "lca"
    if lca_path:
        lca, sample = Path(lca_path), False
    elif default_lca.exists() and any(default_lca.iterdir()):
        lca, sample = default_lca, False
    else:
        lca, sample = SAMPLE_LCA, True
        click.echo("No real LCA data found — building report from SAMPLE dataset.")

    result = run_pipeline(lca, state_list, cfg=cfg, apply_llc=not sample)
    out_path = Path(out)
    db_path = out_path.with_suffix(".duckdb")
    db_path.unlink(missing_ok=True)
    with Store(db_path) as store:
        store.upsert(result.companies)
        if result.review_queue:
            store.upsert(result.review_queue)
        n = export_markdown(store, out_path, states=state_list, llc_only=llc_only, sample=sample)
    db_path.unlink(missing_ok=True)
    click.echo(f"Wrote report with {n} companies -> {out_path}")


@cli.command("query")
@click.argument("sql")
@click.option("--db", default=DEFAULT_DB, help="DuckDB store path.")
def query_cmd(sql: str, db: str) -> None:
    """Run a read-only SQL query against the store."""
    if not Path(db).exists():
        raise click.ClickException(f"No store at {db}. Run `visa-finder run` first.")
    with Store(db) as store:
        rel = store.query(sql)
        rows = rel.fetchall()
        cols = [d[0] for d in rel.description] if rel.description else []
        if cols:
            click.echo(" | ".join(cols))
        for row in rows:
            click.echo(" | ".join("" if v is None else str(v) for v in row))


if __name__ == "__main__":
    cli()
