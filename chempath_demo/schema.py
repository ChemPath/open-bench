"""Request validation for the ChemPath demo.

Mirrors the public request contract of the ChemPath formulation API:
``entries`` with a nonblank ``name``, an optional ``percentage`` in [0, 100],
and an optional explicit ``smiles`` or ``inchi`` structure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Optional

MAX_BATCH_ITEMS = 25


class RequestError(ValueError):
    """A request the API would reject before analysis.

    Attributes:
        http_status: The status code the hosted API returns for this class of
            error (400 for malformed JSON shapes, 422 for invalid inputs).
    """

    def __init__(self, message: str, http_status: int = 422) -> None:
        super().__init__(message)
        self.http_status = http_status


@dataclass(frozen=True)
class Entry:
    """One compound line in a formulation."""

    name: str
    percentage: Optional[float] = None
    smiles: Optional[str] = None
    inchi: Optional[str] = None


@dataclass(frozen=True)
class FormulationRequest:
    """A validated formulation request."""

    formulation_name: str
    entries: tuple[Entry, ...]


def _parse_percentage(value: Any, index: int) -> Optional[float]:
    """Validate an optional percentage: finite and between 0 and 100 inclusive."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RequestError(f"entries[{index}].percentage must be a number")
    pct = float(value)
    if not math.isfinite(pct) or not 0.0 <= pct <= 100.0:
        raise RequestError(f"entries[{index}].percentage must be finite and within 0-100")
    return pct


def _parse_optional_str(value: Any, field: str, index: int) -> Optional[str]:
    """Return a stripped string, or None when the field is absent or blank."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise RequestError(f"entries[{index}].{field} must be a string")
    return value.strip() or None


def parse_formulation(payload: Any) -> FormulationRequest:
    """Validate a formulation payload.

    Args:
        payload: Decoded JSON body, e.g.
            ``{"formulation_name": "...", "entries": [{"name": "CBN", "percentage": 1}]}``.

    Returns:
        A validated :class:`FormulationRequest`.

    Raises:
        RequestError: 400 for a non-object body or a missing/non-list
            ``entries`` field; 422 for invalid entry values.
    """
    if not isinstance(payload, Mapping):
        raise RequestError("formulation body must be a JSON object", http_status=400)
    if "compounds" in payload and "entries" not in payload:
        raise RequestError("use 'entries', not 'compounds'", http_status=400)
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        raise RequestError("'entries' must be a list", http_status=400)
    if not raw_entries:
        raise RequestError("'entries' must contain at least one compound")

    entries: list[Entry] = []
    for i, raw in enumerate(raw_entries):
        if not isinstance(raw, Mapping):
            raise RequestError(f"entries[{i}] must be an object", http_status=400)
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise RequestError(f"entries[{i}].name must be a nonblank string")
        entries.append(
            Entry(
                name=name.strip(),
                percentage=_parse_percentage(raw.get("percentage"), i),
                smiles=_parse_optional_str(raw.get("smiles"), "smiles", i),
                inchi=_parse_optional_str(raw.get("inchi"), "inchi", i),
            )
        )

    name = payload.get("formulation_name") or "Untitled formulation"
    if not isinstance(name, str):
        raise RequestError("'formulation_name' must be a string")
    return FormulationRequest(formulation_name=name.strip(), entries=tuple(entries))
