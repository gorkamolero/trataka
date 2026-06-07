"""Coarse city-centroid coordinates for MO/TX, used as a fallback placement when
precise address geocoding is unavailable.

These are *real* city coordinates, not fabricated company locations. A company
placed here is flagged ``geocode_precision="city"`` so the map and exports are
honest about the precision.
"""

from __future__ import annotations

# (city_lower, state) -> (lat, lon)
CITY_CENTROIDS: dict[tuple[str, str], tuple[float, float]] = {
    # Missouri
    ("columbia", "MO"): (38.9517, -92.3341),
    ("st louis", "MO"): (38.6270, -90.1994),
    ("saint louis", "MO"): (38.6270, -90.1994),
    ("kansas city", "MO"): (39.0997, -94.5786),
    ("springfield", "MO"): (37.2090, -93.2923),
    ("jefferson city", "MO"): (38.5767, -92.1735),
    ("st charles", "MO"): (38.7881, -90.4974),
    ("independence", "MO"): (39.0911, -94.4155),
    ("joplin", "MO"): (37.0842, -94.5133),
    # Texas
    ("austin", "TX"): (30.2672, -97.7431),
    ("houston", "TX"): (29.7604, -95.3698),
    ("dallas", "TX"): (32.7767, -96.7970),
    ("san antonio", "TX"): (29.4241, -98.4936),
    ("fort worth", "TX"): (32.7555, -97.3308),
    ("el paso", "TX"): (31.7619, -106.4850),
    ("plano", "TX"): (33.0198, -96.6989),
    ("frisco", "TX"): (33.1507, -96.8236),
    ("irving", "TX"): (32.8140, -96.9489),
    ("arlington", "TX"): (32.7357, -97.1081),
    ("round rock", "TX"): (30.5083, -97.6789),
}


def centroid_for(city: str | None, state: str | None) -> tuple[float, float] | None:
    if not city or not state:
        return None
    key = (city.strip().lower(), state.strip().upper())
    return CITY_CENTROIDS.get(key)
