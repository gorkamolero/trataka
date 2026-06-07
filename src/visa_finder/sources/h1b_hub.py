"""USCIS H-1B Employer Data Hub reader — approval-count corroboration.

The Hub export has one row per employer per fiscal year with initial/continuing
approvals and denials. We aggregate to an approval count keyed by normalized
employer name + state.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..normalize import normalize_name

_NAME_COLS = ["Employer (Petitioner) Name", "EMPLOYER_NAME", "Employer Name"]
_STATE_COLS = ["Petitioner State", "STATE", "State"]
_APPROVAL_COLS = [
    "Initial Approval", "Initial Approvals",
    "Continuing Approval", "Continuing Approvals",
]


def _first_present(df: pd.DataFrame, candidates: list[str]) -> str | None:
    upper = {c.upper().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.upper() in upper:
            return upper[cand.upper()]
    return None


def load_approval_counts(path: str | Path) -> dict[tuple[str, str], int]:
    """Return {(normalized_name, state): approval_count}."""
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str, low_memory=False)

    name_col = _first_present(df, _NAME_COLS)
    state_col = _first_present(df, _STATE_COLS)
    approval_cols = [c for c in (_first_present(df, [a]) for a in _APPROVAL_COLS) if c]
    if not name_col:
        raise ValueError(f"{path.name}: no employer-name column found")

    counts: dict[tuple[str, str], int] = {}
    for _, row in df.iterrows():
        name = row.get(name_col)
        if not name or pd.isna(name):
            continue
        state = (row.get(state_col) if state_col else "") or ""
        key = (normalize_name(str(name)), str(state).upper().strip())
        total = 0
        for col in approval_cols:
            v = row.get(col)
            try:
                total += int(float(v)) if v and not pd.isna(v) else 0
            except (ValueError, TypeError):
                continue
        counts[key] = counts.get(key, 0) + total
    return counts
