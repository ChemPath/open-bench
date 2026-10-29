"""Name-to-structure lookup against a small, public reference library.

The bundled library (``data/reference_compounds.csv``) lists common
phytocannabinoids, terpenes and polyphenols with structures transcribed from
public sources. It is intentionally small: names outside it must be submitted with ``smiles`` or
``inchi``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

DEFAULT_LIBRARY = Path(__file__).resolve().parent.parent / "data" / "reference_compounds.csv"


@dataclass(frozen=True)
class LibraryCompound:
    """A reference structure and its accepted names."""

    name: str
    compound_class: str
    smiles: str
    synonyms: tuple[str, ...]


def _key(name: str) -> str:
    """Normalize a compound name for case- and spacing-insensitive lookup."""
    return " ".join(name.lower().replace("_", " ").split())


@lru_cache(maxsize=4)
def load_library(path: Path = DEFAULT_LIBRARY) -> dict[str, LibraryCompound]:
    """Load the reference library, indexed by normalized name and synonym.

    Args:
        path: CSV with columns ``name, synonyms, compound_class, smiles``;
            synonyms are separated by ``;``.

    Returns:
        Mapping of normalized name/synonym to :class:`LibraryCompound`.
    """
    index: dict[str, LibraryCompound] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            synonyms = tuple(s.strip() for s in row["synonyms"].split(";") if s.strip())
            compound = LibraryCompound(
                name=row["name"],
                compound_class=row["compound_class"],
                smiles=row["smiles"],
                synonyms=synonyms,
            )
            for alias in (compound.name, *synonyms):
                index[_key(alias)] = compound
    return index


def lookup(name: str, path: Path = DEFAULT_LIBRARY) -> Optional[LibraryCompound]:
    """Return the library compound matching ``name``, or None."""
    return load_library(path).get(_key(name))


def compounds(path: Path = DEFAULT_LIBRARY) -> list[LibraryCompound]:
    """Return each library compound once, in file order."""
    seen: dict[str, LibraryCompound] = {}
    for compound in load_library(path).values():
        seen.setdefault(compound.name, compound)
    return list(seen.values())
