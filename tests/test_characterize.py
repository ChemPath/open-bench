"""Contract tests for the ChemPath demo characterization and batch paths."""

import math

import pytest

from chempath_demo import RequestError, analyze_batch, analyze_formulation
from chempath_demo.schema import MAX_BATCH_ITEMS


def _formulation(*entries, name="SYNTHETIC test"):
    return {"formulation_name": name, "entries": list(entries)}


def test_cbn_reference_identity():
    report = analyze_formulation(_formulation({"name": "CBN", "percentage": 1}))
    assert report["status"] == "success"
    entry = report["entries"][0]
    assert entry["molecular_formula"] == "C21H26O2"
    assert entry["inchikey"] == "VBGLYOIFKLUMQG-UHFFFAOYSA-N"
    assert entry["structure_source"] == "reference_library"


@pytest.mark.parametrize("name", ["cbn", "  Cannabinol ", "CANNABINOL"])
def test_name_lookup_is_case_and_space_insensitive(name):
    report = analyze_formulation(_formulation({"name": name}))
    assert report["entries"][0]["inchikey"] == "VBGLYOIFKLUMQG-UHFFFAOYSA-N"


def test_explicit_smiles_overrides_name():
    report = analyze_formulation(_formulation({"name": "CBN", "smiles": "CCO"}))
    entry = report["entries"][0]
    assert entry["structure_source"] == "smiles"
    assert entry["molecular_formula"] == "C2H6O"


def test_explicit_inchi():
    report = analyze_formulation(_formulation({"name": "ethanol", "inchi": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"}))
    assert report["entries"][0]["inchikey"] == "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"


def test_partial_counts_only_characterized_entries():
    report = analyze_formulation(_formulation({"name": "CBD", "percentage": 10}, {"name": "unknown fraction"}))
    assert report["status"] == "partial"
    assert report["qc"]["coverage"] == 0.5
    failed = report["entries"][1]
    assert failed["status"] == "uncharacterizable" and failed["reason"]


def test_all_uncharacterizable_is_failed_422():
    report = analyze_formulation(_formulation({"name": "nothing", "smiles": "C1CC("}))
    assert report["status"] == "failed"
    assert report["http_status"] == 422


@pytest.mark.parametrize("pct", [-0.1, 100.01, math.inf, math.nan, "5", True])
def test_invalid_percentage_rejected(pct):
    with pytest.raises(RequestError) as exc:
        analyze_formulation(_formulation({"name": "CBN", "percentage": pct}))
    assert exc.value.http_status == 422


@pytest.mark.parametrize("pct", [0, 100, 0.0])
def test_percentage_bounds_inclusive(pct):
    assert analyze_formulation(_formulation({"name": "CBN", "percentage": pct}))["status"] == "success"


@pytest.mark.parametrize("payload, status", [
    ([], 400),
    ({"compounds": [{"name": "CBN"}]}, 400),
    ({"entries": "CBN"}, 400),
    ({"entries": []}, 422),
    ({"entries": [{"name": "  "}]}, 422),
])
def test_malformed_requests(payload, status):
    with pytest.raises(RequestError) as exc:
        analyze_formulation(payload)
    assert exc.value.http_status == status


def test_report_carries_scope_and_disclaimer():
    report = analyze_formulation(_formulation({"name": "CBN"}))
    assert "SYNTHETIC" in report["label"]
    assert report["analysis_id"].startswith("demo_")
    assert "efficacy" in report["disclaimer"]
    assert any("synergy" in s for s in report["scope"]["does_not_cover"])


def test_qc_flags_overfull_and_duplicate_entries():
    report = analyze_formulation(_formulation(
        {"name": "CBD", "percentage": 80}, {"name": "cannabidiol", "percentage": 30}))
    notes = " ".join(report["qc"]["notes"])
    assert "exceed 100%" in notes
    assert "same structure submitted more than once" in notes


def test_batch_accounts_for_every_item():
    result = analyze_batch({"items": [
        {"kind": "formulation", "formulation": _formulation({"name": "CBN"})},
        {"kind": "compound", "compound": {"name": "bad", "smiles": "C1CC("}},
        {"kind": "nonsense"},
    ]})
    assert result["status"] == "partial"
    assert [i["status"] for i in result["items"]] == ["success", "failed", "failed"]
    assert result["items"][2]["http_status"] == 400
    assert result["items_succeeded"] + result["items_failed"] == 3


def test_batch_limit():
    item = {"kind": "compound", "compound": {"name": "CBN"}}
    assert analyze_batch({"items": [item] * MAX_BATCH_ITEMS})["status"] == "success"
    with pytest.raises(RequestError):
        analyze_batch({"items": [item] * (MAX_BATCH_ITEMS + 1)})
