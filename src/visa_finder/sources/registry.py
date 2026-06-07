"""State business-registry adapters — entity type (#4) + registered address.

Each adapter loads a state's bulk registry export into a common
:class:`RegistryRecord` keyed by normalized name. Where a state's bulk data is
thin, the pipeline falls back to OpenCorporates (see ``opencorporates.py``).

Adapters are registered by name so ``config/states.yaml`` can select one per state.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..models import EntityType
from ..normalize import normalize_name


@dataclass
class RegistryRecord:
    normalized_name: str
    raw_name: str
    entity_type: EntityType
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None


def classify_entity_type(text: str | None) -> EntityType:
    """Best-effort entity-type classification from a registry string."""
    if not text:
        return EntityType.UNKNOWN
    t = text.upper()
    if "LIMITED LIABILITY" in t or "L.L.C" in t or "LLC" in t or "PLLC" in t:
        return EntityType.LLC
    if "L.L.P" in t or "LLP" in t:
        return EntityType.LLP
    if "L.P" in t or t.endswith(" LP") or "LIMITED PARTNERSHIP" in t:
        return EntityType.LP
    if "CORP" in t or "INCORPORATED" in t or t.endswith(" INC") or "INC." in t:
        return EntityType.CORP
    if "SOLE PROP" in t:
        return EntityType.SOLE_PROP
    return EntityType.OTHER


def _read(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str, low_memory=False)


def _col(df: pd.DataFrame, *candidates: str) -> str | None:
    upper = {c.upper().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.upper() in upper:
            return upper[cand.upper()]
    return None


def _cell(row: pd.Series, col: str | None) -> str | None:
    """Return a stripped string value for a column, or None if absent/empty."""
    if not col:
        return None
    v = row.get(col)
    if v is None or pd.isna(v):
        return None
    s = str(v).strip()
    return s or None


def _generic_adapter(
    path: Path,
    name_cols: tuple[str, ...],
    type_cols: tuple[str, ...],
    addr_cols: tuple[str, ...],
    city_cols: tuple[str, ...],
    state_cols: tuple[str, ...],
    zip_cols: tuple[str, ...],
    default_state: str,
) -> Iterator[RegistryRecord]:
    df = _read(path)
    name_col = _col(df, *name_cols)
    if not name_col:
        raise ValueError(f"{path.name}: no business-name column found")
    type_col = _col(df, *type_cols)
    addr_col = _col(df, *addr_cols)
    city_col = _col(df, *city_cols)
    state_col = _col(df, *state_cols)
    zip_col = _col(df, *zip_cols)

    for _, row in df.iterrows():
        raw = _cell(row, name_col)
        if not raw:
            continue
        # Entity type comes from an explicit column if present, else inferred
        # from the name itself.
        type_text = _cell(row, type_col) or raw
        state_val = _cell(row, state_col)
        yield RegistryRecord(
            normalized_name=normalize_name(raw),
            raw_name=raw,
            entity_type=classify_entity_type(type_text),
            address=_cell(row, addr_col),
            city=_cell(row, city_col),
            state=state_val.upper() if state_val else default_state,
            zip=_cell(row, zip_col),
        )


def missouri_sos(path: str | Path) -> Iterator[RegistryRecord]:
    return _generic_adapter(
        Path(path),
        name_cols=("Entity Name", "BUSINESS_NAME", "Name"),
        type_cols=("Entity Type", "TYPE", "Entity Creation Type"),
        addr_cols=("Address", "Principal Address", "Street Address"),
        city_cols=("City",),
        state_cols=("State",),
        zip_cols=("Zip", "Postal Code", "ZIP"),
        default_state="MO",
    )


def texas_comptroller(path: str | Path) -> Iterator[RegistryRecord]:
    return _generic_adapter(
        Path(path),
        name_cols=("Taxpayer Name", "Taxpayer_Name", "Name"),
        type_cols=("Taxpayer Organization Type", "Organization Type", "Entity Type"),
        addr_cols=("Taxpayer Address", "Taxpayer Mailing Address", "Address"),
        city_cols=("Taxpayer City", "City"),
        state_cols=("Taxpayer State", "State"),
        zip_cols=("Taxpayer Zip Code", "Taxpayer Zip", "Zip"),
        default_state="TX",
    )


ADAPTERS: dict[str, Callable[[str | Path], Iterator[RegistryRecord]]] = {
    "missouri_sos": missouri_sos,
    "texas_comptroller": texas_comptroller,
}


def get_adapter(name: str) -> Callable[[str | Path], Iterator[RegistryRecord]]:
    if name not in ADAPTERS:
        raise KeyError(f"Unknown registry adapter: {name!r}. Known: {sorted(ADAPTERS)}")
    return ADAPTERS[name]
