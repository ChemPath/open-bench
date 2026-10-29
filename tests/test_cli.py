"""CLI subcommand tests."""

import json

import pytest

from chempath_demo.cli import main


def test_cli_batch_library_explain(tmp_path, capsys):
    assert main(["batch", "examples/mixed_batch.json", "--out", str(tmp_path / "b.json")]) == 0
    assert json.loads((tmp_path / "b.json").read_text())["items_submitted"] == 4
    assert main(["library"]) == 0
    assert "VBGLYOIFKLUMQG-UHFFFAOYSA-N" in capsys.readouterr().out
    assert main(["explain", "--samples", "800"]) == 0
    assert "recovered as top features: True" in capsys.readouterr().out


def test_cli_pdf_and_failed(tmp_path, capsys):
    pytest.importorskip("reportlab")
    pdf = tmp_path / "p.pdf"
    assert main(["analyze", "examples/partial_formulation.json", "--pdf", str(pdf)]) == 0
    assert pdf.read_bytes().startswith(b"%PDF")
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps({"entries": [{"name": "unknown"}]}))
    assert main(["analyze", str(failed), "--pdf", str(tmp_path / "f.pdf")]) == 2
    assert not (tmp_path / "f.pdf").exists()
