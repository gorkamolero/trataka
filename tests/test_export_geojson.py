import json
from pathlib import Path

from visa_finder.config import load_config
from visa_finder.export import export_geojson
from visa_finder.pipeline.run import run
from visa_finder.store import Store

FIXTURE = Path(__file__).parent / "fixtures" / "lca_sample.csv"


def test_geojson_uses_city_centroids(tmp_path):
    cfg = load_config()
    result = run(FIXTURE, ["MO", "TX"], cfg=cfg, apply_llc=False)
    db = tmp_path / "g.duckdb"
    out = tmp_path / "leads.geojson"
    with Store(db) as store:
        store.upsert(result.companies)
        n = export_geojson(store, out, states=["MO", "TX"], use_centroids=True, sample=True)

    fc = json.loads(out.read_text())
    assert fc["type"] == "FeatureCollection"
    assert fc["metadata"]["sample"] is True
    assert n == len(fc["features"]) == 3
    for feat in fc["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        # Sample addresses are unset, so all fall back to city centroids.
        assert feat["properties"]["geocode_precision"] == "city"
        # Coordinates are real US lon/lat ranges.
        assert -107 < lon < -89
        assert 29 < lat < 40


def test_geojson_skips_unplaceable_when_centroids_disabled(tmp_path):
    cfg = load_config()
    result = run(FIXTURE, ["MO", "TX"], cfg=cfg, apply_llc=False)
    db = tmp_path / "g2.duckdb"
    out = tmp_path / "leads2.geojson"
    with Store(db) as store:
        store.upsert(result.companies)
        n = export_geojson(store, out, states=["MO", "TX"], use_centroids=False)
    # No precise coords and centroids disabled -> nothing placed on the map.
    assert n == 0
