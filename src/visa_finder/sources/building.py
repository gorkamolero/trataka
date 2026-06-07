"""Geocoding + open building data for the small-building signal (#5).

Two free services:
  * US Census batch/oneline geocoder -> lat/lon (no key required).
  * OpenStreetMap Overpass API -> nearest building footprint + tags.

Both are network calls and rate-limited, so results are cached on disk. Nothing
here fabricates data: if a lookup fails we return ``None`` and the building score
is left unset.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from ..config import data_dir

CENSUS_ONELINE = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
OVERPASS = "https://overpass-api.de/api/interpreter"


@dataclass
class BuildingInfo:
    latitude: float | None = None
    longitude: float | None = None
    footprint_sqm: float | None = None
    levels: int | None = None
    tags: dict[str, str] = field(default_factory=dict)


def _cache_path() -> Path:
    p = data_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p / "building_cache.json"


def _load_cache() -> dict[str, dict]:
    path = _cache_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict[str, dict]) -> None:
    _cache_path().write_text(json.dumps(cache))


def geocode(address: str, timeout: float = 20.0) -> tuple[float, float] | None:
    """Return (lat, lon) via the free Census geocoder, or None."""
    params = {"address": address, "benchmark": "Public_AR_Current", "format": "json"}
    try:
        resp = requests.get(CENSUS_ONELINE, params=params, timeout=timeout)
        resp.raise_for_status()
        matches = resp.json().get("result", {}).get("addressMatches", [])
        if not matches:
            return None
        coords = matches[0]["coordinates"]
        return float(coords["y"]), float(coords["x"])
    except (requests.RequestException, KeyError, ValueError):
        return None


def _ring_area_sqm(coords: list[list[float]]) -> float:
    """Approximate planar area (sqm) of a small lon/lat ring via the shoelace
    formula with a local equirectangular projection."""
    import math

    if len(coords) < 3:
        return 0.0
    lat0 = sum(c[1] for c in coords) / len(coords)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat0))
    pts = [(lon * m_per_deg_lon, lat * m_per_deg_lat) for lon, lat in coords]
    area = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def building_at(lat: float, lon: float, radius_m: int = 40, timeout: float = 30.0) -> BuildingInfo:
    """Query Overpass for the nearest building footprint around a point."""
    query = f"""
    [out:json][timeout:25];
    (way["building"](around:{radius_m},{lat},{lon});near);
    out tags geom;
    """
    info = BuildingInfo(latitude=lat, longitude=lon)
    try:
        resp = requests.post(OVERPASS, data={"data": query}, timeout=timeout)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
    except (requests.RequestException, ValueError):
        return info

    best_area = None
    for el in elements:
        tags = el.get("tags", {})
        geom = el.get("geometry", [])
        ring = [[p["lon"], p["lat"]] for p in geom]
        area = _ring_area_sqm(ring) if ring else None
        # Choose the smallest footprint that contains the point's vicinity — a
        # small standalone building rather than a giant complex.
        if area and (best_area is None or area < best_area):
            best_area = area
            info.footprint_sqm = area
            info.tags = {k: str(v) for k, v in tags.items()}
            levels = tags.get("building:levels")
            try:
                info.levels = int(float(levels)) if levels else None
            except ValueError:
                info.levels = None
    return info


def lookup(address: str, sleep_s: float = 1.0) -> BuildingInfo | None:
    """Cached geocode + building lookup for an address string."""
    cache = _load_cache()
    if address in cache:
        return BuildingInfo(**cache[address])

    coords = geocode(address)
    if coords is None:
        return None
    time.sleep(sleep_s)  # be polite to Overpass
    info = building_at(*coords)
    cache[address] = {
        "latitude": info.latitude,
        "longitude": info.longitude,
        "footprint_sqm": info.footprint_sqm,
        "levels": info.levels,
        "tags": info.tags,
    }
    _save_cache(cache)
    return info
