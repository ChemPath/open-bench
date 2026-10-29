"""Tests for report export, the reference library and the SHAP demo."""

import json

import pytest
from rdkit import Chem

from chempath_demo import analyze_formulation
from chempath_demo.cli import main
from chempath_demo.explain import PLANTED_DRIVERS, run
from chempath_demo.library import compounds
from chempath_demo.report import write_json, write_pdf

KNOWN_KEYS = {
    "CBD": "QHMBSVQNZZTUGM-ZWKOTPCHSA-N",
    "THC": "CYQFCXCEBYINGO-IAGOWNOFSA-N",
    "Caffeine": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
    "Quercetin": "REFJWTPEDVJJIY-UHFFFAOYSA-N",
}


def test_library_structures_parse_and_match_known_keys():
    lib = {c.name: c for c in compounds()}
    for c in lib.values():
        assert Chem.MolFromSmiles(c.smiles) is not None, c.name
    for name, key in KNOWN_KEYS.items():
        assert Chem.MolToInchiKey(Chem.MolFromSmiles(lib[name].smiles)) == key


def test_json_roundtrip(tmp_path):
    report = analyze_formulation({"entries": [{"name": "CBN"}]})
    path = write_json(report, tmp_path / "r.json")
    assert json.loads(path.read_text())["analysis_id"] == report["analysis_id"]


def test_pdf_render_and_failed_export(tmp_path):
    pytest.importorskip("reportlab")
    ok = analyze_formulation({"entries": [{"name": "CBN"}, {"name": "unknown"}]})
    assert write_pdf(ok, tmp_path / "r.pdf").read_bytes().startswith(b"%PDF")
    failed = analyze_formulation({"entries": [{"name": "unknown"}]})
    with pytest.raises(ValueError):
        write_pdf(failed, tmp_path / "f.pdf")


def test_shap_recovers_planted_drivers():
    result = run(n=1500, seed=3)
    assert result.planted_drivers_recovered
    assert tuple(sorted(result.global_importance.index[:2])) == tuple(sorted(PLANTED_DRIVERS))
    assert result.test_accuracy > 0.85


def test_cli_analyze_example(tmp_path, capsys):
    out = tmp_path / "cbn.json"
    assert main(["analyze", "examples/cbn_formulation.json", "--out", str(out)]) == 0
    assert json.loads(out.read_text())["entries"][0]["molecular_formula"] == "C21H26O2"


def test_cli_rejects_malformed_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert main(["analyze", str(bad)]) == 1
