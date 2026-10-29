"""Tests for the Chemical Space Explorer data build and page.

The browser checks need Node with Playwright and are skipped otherwise.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_explorer  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return build_explorer.build_data()


def test_page_is_fresh():
    assert subprocess.run([sys.executable, str(ROOT / "scripts" / "build_explorer.py"), "--check"]).returncode == 0


def test_pca_is_well_formed(data):
    explained = data["pca"]["explained"]
    assert explained[0] >= explained[1] > 0 and sum(explained) <= 1
    for comp in data["pca"]["loadings"]:
        assert abs(np.linalg.norm(list(comp.values())) - 1) < 1e-2
    pc1 = np.array([c["pc1"] for c in data["compounds"]])
    assert abs(pc1.mean()) < 1e-2


def test_rule_checks_match_definitions(data):
    for c in data["compounds"]:
        r = c["rules"]
        expected = sum([c["mw"] > 500, c["logp"] > 5, c["hbd"] > 5, c["hba"] > 10])
        assert r["lipinski_violations"] == expected, c["name"]
        assert r["veber_pass"] == (c["rotb"] <= 10 and c["tpsa"] <= 140), c["name"]


def test_neighbors_are_chemically_sensible(data):
    by = {c["name"]: c for c in data["compounds"]}
    assert by["CBD"]["neighbors"][0]["name"] == "CBDV"
    assert by["Quercetin"]["neighbors"][0]["name"] in {"Kaempferol", "Myricetin"}
    assert by["Caffeine"]["neighbors"][0]["name"] == "Theobromine"
    for c in data["compounds"]:
        sims = [n["tanimoto"] for n in c["neighbors"]]
        assert sims == sorted(sims, reverse=True) and c["name"] not in [n["name"] for n in c["neighbors"]]


def _node_playwright() -> bool:
    return bool(shutil.which("node")) and subprocess.run(
        ["node", "-e", "require('playwright')"], capture_output=True).returncode == 0


@pytest.fixture(scope="module")
def browser(tmp_path_factory):
    if not _node_playwright():
        pytest.skip("requires node + playwright")
    out = tmp_path_factory.mktemp("explorer") / "out.json"
    shots = os.environ.get("CHEMPATH_WEB_SHOTS")
    cmd = ["node", str(ROOT / "tests" / "web" / "explorer_check.js"),
           str(ROOT / "web" / "chemical-space.html"), str(out)] + ([shots] if shots else [])
    subprocess.run(cmd, check=True, timeout=120)
    return json.loads(out.read_text())


def test_explorer_renders(browser, data):
    assert browser["errors"] == []
    assert browser["hits"] == browser["rows"] == len(data["compounds"])
    assert browser["highlighted"] == sum(c["family"] == "Phytocannabinoid" for c in data["compounds"])
    assert browser["hollow"] == sum(not (c["rules"]["lipinski_pass"] and c["rules"]["veber_pass"])
                                    for c in data["compounds"])
    assert browser["multiples"] == 7
    assert browser["detail_name"] == "CBD"


def test_rule_region_only_on_property_axes(browser):
    assert browser["region_on_pca"] == 0
    assert browser["region_on_logp_tpsa"] == 1
    assert "≤ 5" in browser["region_label"] and "≤ 140" in browser["region_label"]


def test_interactions(browser, data):
    assert browser["after_find"]["detail"] == "Quercetin"
    assert browser["after_find"]["family"] == "Flavonoid"
    assert "c=Quercetin" in browser["after_find"]["url"]
    assert browser["after_neighbor"] in {"Kaempferol", "Myricetin"}
    lightest = min(data["compounds"], key=lambda c: (c["mw"], c["name"].lower()))
    assert browser["first_by_mw"] == lightest["name"]
    assert browser["family_after_mini"] == "Alkaloid"  # 6th small multiple
    assert browser["url_restore"] == {"x": "mw", "y": "logp", "family": "Flavonoid", "selected": "Apigenin"}
    assert browser["mobile_overflow"] is False
