"""Configuration loading. All operational knobs live in ``config/*.yaml`` so that
adding a state or tuning the software-code set is config, not code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def _project_root() -> Path:
    # src/visa_finder/config.py -> project root is three parents up.
    return Path(__file__).resolve().parents[2]


def config_dir() -> Path:
    return _project_root() / "config"


def data_dir() -> Path:
    d = _project_root() / "data"
    return d


def _load_yaml(name: str) -> dict[str, Any]:
    path = config_dir() / name
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


@dataclass(frozen=True)
class RegistryConfig:
    adapter: str
    bulk_url: str | None = None
    opencorporates_jurisdiction: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class StateConfig:
    code: str
    name: str
    fips: str
    enabled: bool
    registry: RegistryConfig


@dataclass(frozen=True)
class SoftwareCodes:
    naics: tuple[str, ...]
    soc: tuple[str, ...]
    naics_is_authoritative: bool

    def is_software(self, naics_code: str | None, soc_code: str | None) -> bool:
        """A record is software if its NAICS matches, or (when NAICS is absent
        and not authoritative-only) its SOC matches."""
        if naics_code and any(naics_code.startswith(p) for p in self.naics):
            return True
        if naics_code and self.naics_is_authoritative:
            # NAICS present but not a software code -> not software.
            return False
        if soc_code and any(soc_code.startswith(p) for p in self.soc):
            return True
        return False


@dataclass(frozen=True)
class Config:
    states: dict[str, StateConfig]
    software: SoftwareCodes
    scoring: dict[str, Any] = field(default_factory=dict)

    def enabled_states(self) -> list[str]:
        return [code for code, s in self.states.items() if s.enabled]


@lru_cache(maxsize=1)
def load_config() -> Config:
    raw_states = _load_yaml("states.yaml").get("states", {})
    states: dict[str, StateConfig] = {}
    for code, body in raw_states.items():
        reg = body.get("registry", {}) or {}
        states[code] = StateConfig(
            code=code,
            name=body.get("name", code),
            fips=str(body.get("fips", "")),
            enabled=bool(body.get("enabled", False)),
            registry=RegistryConfig(
                adapter=reg.get("adapter", "opencorporates"),
                bulk_url=reg.get("bulk_url"),
                opencorporates_jurisdiction=reg.get("opencorporates_jurisdiction"),
                notes=reg.get("notes"),
            ),
        )

    raw_sw = _load_yaml("software_codes.yaml")
    software = SoftwareCodes(
        naics=tuple(str(c) for c in raw_sw.get("naics", [])),
        soc=tuple(str(c) for c in raw_sw.get("soc", [])),
        naics_is_authoritative=bool(raw_sw.get("naics_is_authoritative", True)),
    )

    scoring = _load_yaml("scoring.yaml")

    return Config(states=states, software=software, scoring=scoring)
