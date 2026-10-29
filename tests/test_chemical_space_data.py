"""Integrity checks for data/chemical_space.csv (Chemical Space Explorer dataset)."""

import csv
from pathlib import Path

from rdkit import Chem

ROWS = list(csv.DictReader(open(Path(__file__).resolve().parent.parent / "data" / "chemical_space.csv")))
FAMILIES = {"Phytocannabinoid", "Monoterpenoid", "Sesquiterpenoid", "Flavonoid", "Phenolic",
            "Alkaloid", "Triterpenoid/steroid"}


def test_rows_parse_and_keys_are_current():
    assert len(ROWS) == 65
    for r in ROWS:
        mol = Chem.MolFromSmiles(r["smiles"])
        assert mol is not None, r["name"]
        assert Chem.MolToInchiKey(mol) == r["inchikey"], r["name"]


def test_names_unique_and_families_known():
    assert len({r["name"] for r in ROWS}) == len(ROWS)
    assert {r["family"] for r in ROWS} == FAMILIES


def test_2d_only_rows_carry_no_tetrahedral_stereo():
    for r in ROWS:
        if r["stereo"] == "2D only":
            assert "@" not in r["smiles"], r["name"]
        else:
            assert r["stereo"] == "defined", r["name"]
