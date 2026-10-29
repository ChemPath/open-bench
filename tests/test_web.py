"""Browser test for web/index.html.

The page's JavaScript is checked against the Python package on the same
inputs. RDKit.js is replaced by a stub whose answers come from Python RDKit,
so the test covers the page's own logic (validation, resolution, QC, status,
rendering), not RDKit.js itself. Requires Node with Playwright; skipped otherwise.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from rdkit import Chem, rdBase
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D

from chempath_demo import RequestError, analyze_formulation
from chempath_demo.library import compounds

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tests" / "web" / "browser_check.js"

PAYLOADS = [
    *(json.loads(p.read_text()) for p in sorted((ROOT / "examples").glob("*_formulation.json"))),
    {"entries": [{"name": "cannabinol", "percentage": 60}, {"name": "CBN", "percentage": 50}]},
    {"entries": [{"name": "racemic", "smiles": "CC(O)CC"}]},
    {"entries": [{"name": "bad", "smiles": "C1CC("}]},
    {"entries": [{"name": "CBD", "percentage": 140}]},
    {"entries": [{"name": "  "}]},
    {"compounds": [{"name": "CBN"}]},
    {"entries": []},
]


def _node_playwright() -> bool:
    node = shutil.which("node")
    if not node:
        return False
    probe = subprocess.run([node, "-e", "require('playwright')"], capture_output=True)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(not _node_playwright(), reason="requires node + playwright")


def _stub_source(smiles_inputs: list[str]) -> str:
    """Build a JS stand-in for RDKit.js from Python RDKit results."""
    mols, keys = {}, {}
    for smi in smiles_inputs:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        inchi = Chem.MolToInchi(mol)
        keys[inchi] = Chem.MolToInchiKey(mol)
        drawer = rdMolDraw2D.MolDraw2DSVG(260, 170)
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        mols[smi] = {
            "smiles": Chem.MolToSmiles(mol),
            "inchi": inchi,
            "svg": drawer.GetDrawingText().split("?>", 1)[-1],
            "descriptors": {
                "amw": Descriptors.MolWt(mol),
                "exactmw": Descriptors.ExactMolWt(mol),
                "CrippenClogP": Crippen.MolLogP(mol),
                "tpsa": rdMolDescriptors.CalcTPSA(mol),
                "NumHBD": Lipinski.NumHDonors(mol),
                "NumHBA": Lipinski.NumHAcceptors(mol),
                "NumRotatableBonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
                "NumHeavyAtoms": mol.GetNumHeavyAtoms(),
                "NumRings": rdMolDescriptors.CalcNumRings(mol),
                "NumAromaticRings": rdMolDescriptors.CalcNumAromaticRings(mol),
                "FractionCSP3": rdMolDescriptors.CalcFractionCSP3(mol),
                "NumAtomStereoCenters": rdMolDescriptors.CalcNumAtomStereoCenters(mol),
            },
        }
    return f"""
window.initRDKitModule = () => {{
  const MOLS = {json.dumps(mols)};
  const KEYS = {json.dumps(keys)};
  return Promise.resolve({{
    version: () => "{rdBase.rdkitVersion}-stub",
    get_inchikey_for_inchi: (i) => KEYS[i],
    get_mol: (s) => {{
      const m = MOLS[s];
      if (!m) return null;
      return {{ is_valid: () => true, delete: () => {{}}, get_smiles: () => m.smiles,
               get_inchi: () => m.inchi, get_svg: () => m.svg,
               get_descriptors: () => JSON.stringify(m.descriptors) }};
    }},
  }});
}};"""


def _close(a, b) -> bool:
    """Deep equality with float tolerance for rounding differences."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b) <= 1e-3
    return a == b


def _comparable(report: dict) -> dict:
    """Fields that must match between the Python and browser builds."""
    return {k: report[k] for k in ("formulation_name", "status", "http_status", "entries", "qc",
                                   "scope", "disclaimer", "label")}


@pytest.fixture(scope="module")
def browser_run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("web")
    smiles = [c.smiles for c in compounds()]
    smiles += [e["smiles"] for p in PAYLOADS for e in p.get("entries", []) if isinstance(e, dict) and "smiles" in e]
    job = {"page": str(ROOT / "web" / "index.html"), "stub": _stub_source(smiles), "payloads": PAYLOADS}
    (tmp / "job.json").write_text(json.dumps(job))
    shots = os.environ.get("CHEMPATH_WEB_SHOTS")
    cmd = ["node", str(SCRIPT), str(tmp / "job.json"), str(tmp / "out.json")] + ([shots] if shots else [])
    subprocess.run(cmd, check=True, timeout=120)
    return json.loads((tmp / "out.json").read_text())


def test_page_data_is_fresh():
    assert subprocess.run(["python3", str(ROOT / "scripts" / "build_web.py"), "--check"]).returncode == 0


def test_no_page_errors(browser_run):
    assert browser_run["console_errors"] == []
    assert browser_run["boot_status"].strip() == "success"


def test_browser_matches_python(browser_run):
    for payload, got in zip(PAYLOADS, browser_run["results"]):
        try:
            expected = _comparable(analyze_formulation(payload))
        except RequestError as exc:
            assert got == {"error": str(exc), "http_status": exc.http_status}, payload
            continue
        assert "ok" in got, (payload, got)
        assert _close(_comparable(got["ok"]), expected), (payload, got["ok"], expected)


def test_partial_preset_renders_missing_card(browser_run):
    assert browser_run["partial_cards"] == 4
    assert browser_run["partial_missing"] == 1


def test_mobile_has_no_horizontal_scroll(browser_run):
    assert browser_run["mobile_overflow"] is False
