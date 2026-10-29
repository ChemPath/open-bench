#!/usr/bin/env python3
"""Build data for the Chemical Space Explorer and embed it in its page.

Computes, from ``data/chemical_space.csv``:

- standard RDKit descriptors for each compound
- a PCA of the standardized descriptor matrix (scores, explained variance, loadings)
- Lipinski rule-of-five and Veber rule checks
- the three nearest structural neighbours by Morgan-fingerprint Tanimoto similarity
- a 2D structure drawing (SVG)

The shared design kit (``web/_kit/bench.css``) and the data are written
between markers in ``web/chemical-space.html``, so the page stays one file.

Usage::

    python scripts/build_explorer.py          # rewrite the page
    python scripts/build_explorer.py --check  # exit 1 if the page is stale
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdFingerprintGenerator, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "chemical_space.csv"
PAGE = ROOT / "web" / "chemical-space.html"
KIT = ROOT / "web" / "_kit" / "bench.css"
DATA_MARK = re.compile(r"/\*EXPLORER-DATA:BEGIN\*/.*?/\*EXPLORER-DATA:END\*/", re.S)
KIT_MARK = re.compile(r"/\*KIT:BEGIN\*/.*?/\*KIT:END\*/", re.S)

FAMILY_ORDER = ["Phytocannabinoid", "Monoterpenoid", "Sesquiterpenoid", "Flavonoid",
                "Phenolic", "Alkaloid", "Triterpenoid/steroid"]

FEATURES: dict[str, str] = {
    "mw": "Molecular weight (g/mol)",
    "logp": "logP (Crippen)",
    "tpsa": "TPSA (Å²)",
    "hbd": "H-bond donors",
    "hba": "H-bond acceptors",
    "rotb": "Rotatable bonds",
    "arom": "Aromatic rings",
    "fsp3": "Fraction sp3 carbons",
    "heavy": "Heavy atoms",
}
"""Descriptor keys used for the PCA, with axis labels."""


def descriptors(mol: Chem.Mol) -> dict[str, float]:
    """Compute the explorer's descriptor set."""
    return {
        "mw": round(Descriptors.MolWt(mol), 2),
        "logp": round(Crippen.MolLogP(mol), 2),
        "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 1),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "rotb": rdMolDescriptors.CalcNumRotatableBonds(mol),
        "arom": rdMolDescriptors.CalcNumAromaticRings(mol),
        "fsp3": round(rdMolDescriptors.CalcFractionCSP3(mol), 3),
        "heavy": mol.GetNumHeavyAtoms(),
    }


def rule_checks(d: dict[str, float]) -> dict[str, Any]:
    """Lipinski (at most one violation allowed) and Veber oral-property heuristics."""
    lipinski = {"MW ≤ 500": d["mw"] <= 500, "logP ≤ 5": d["logp"] <= 5,
                "HBD ≤ 5": d["hbd"] <= 5, "HBA ≤ 10": d["hba"] <= 10}
    veber = {"Rotatable bonds ≤ 10": d["rotb"] <= 10, "TPSA ≤ 140 Å²": d["tpsa"] <= 140}
    violations = sum(not v for v in lipinski.values())
    return {
        "lipinski": lipinski,
        "lipinski_violations": violations,
        "lipinski_pass": violations <= 1,
        "veber": veber,
        "veber_pass": all(veber.values()),
    }


def svg(mol: Chem.Mol, w: int = 280, h: int = 190) -> str:
    """Compact 2D depiction with a transparent background."""
    drawer = rdMolDraw2D.MolDraw2DSVG(w, h)
    opts = drawer.drawOptions()
    opts.clearBackground = False
    opts.bondLineWidth = 1.6
    drawer.DrawMolecule(rdMolDraw2D.PrepareMolForDrawing(mol))
    drawer.FinishDrawing()
    text = drawer.GetDrawingText().split("?>", 1)[-1]
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"(\d+\.\d)\d+", r"\1", text)  # 0.1 px precision is plenty
    text = re.sub(r" class='[^']*'", "", text)
    text = re.sub(r"\s+xmlns:(rdkit|xlink)='[^']*'|\s+xml:space='preserve'|\s+baseProfile='full'", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1", "")
    return re.sub(r">\s+<", "><", text).strip()


def pca(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """PCA via SVD on z-scored columns.

    Returns:
        ``(scores[:, :2], explained_variance_ratio[:2], loadings[:2, :])``.
        Components are sign-fixed so the largest-magnitude loading is positive,
        keeping the layout stable between builds.
    """
    z = (matrix - matrix.mean(axis=0)) / matrix.std(axis=0)
    _, s, vt = np.linalg.svd(z, full_matrices=False)
    for i in range(vt.shape[0]):
        if vt[i, np.argmax(np.abs(vt[i]))] < 0:
            vt[i] *= -1
    scores = z @ vt[:2].T
    ratio = (s ** 2) / np.sum(s ** 2)
    return scores, ratio[:2], vt[:2]


def build_data() -> dict[str, Any]:
    """Assemble the explorer's embedded dataset."""
    rows = list(csv.DictReader(open(DATA, encoding="utf-8")))
    mols = [Chem.MolFromSmiles(r["smiles"]) for r in rows]
    descs = [descriptors(m) for m in mols]
    keys = list(FEATURES)
    scores, ratio, loadings = pca(np.array([[d[k] for k in keys] for d in descs], dtype=float))

    gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    fps = [gen.GetFingerprint(m) for m in mols]

    compounds = []
    for i, (r, m, d) in enumerate(zip(rows, mols, descs)):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps)
        ranked = sorted((j for j in range(len(rows)) if j != i), key=lambda j: -sims[j])[:3]
        compounds.append({
            "name": r["name"],
            "family": r["family"],
            "compound_class": r["compound_class"],
            "stereo": r["stereo"],
            "formula": rdMolDescriptors.CalcMolFormula(m),
            "inchikey": r["inchikey"],
            "smiles": r["smiles"],
            **d,
            "pc1": round(float(scores[i, 0]), 3),
            "pc2": round(float(scores[i, 1]), 3),
            "rules": rule_checks(d),
            "neighbors": [{"name": rows[j]["name"], "tanimoto": round(sims[j], 2)} for j in ranked],
            "svg": svg(m),
        })

    return {
        "features": {**FEATURES, "pc1": f"PC1 ({ratio[0]:.0%} of variance)",
                     "pc2": f"PC2 ({ratio[1]:.0%} of variance)"},
        "families": FAMILY_ORDER,
        "pca": {
            "explained": [round(float(x), 3) for x in ratio],
            "loadings": [{k: round(float(v), 3) for k, v in zip(keys, comp)} for comp in loadings],
        },
        "compounds": compounds,
    }


def render(page: str, data: dict[str, Any], kit: str) -> str:
    """Return ``page`` with the kit and data blocks replaced."""
    if not DATA_MARK.search(page) or not KIT_MARK.search(page):
        raise SystemExit("markers not found in web/chemical-space.html")
    page = KIT_MARK.sub(lambda _: "/*KIT:BEGIN*/\n" + kit.strip() + "\n/*KIT:END*/", page)
    block = ("/*EXPLORER-DATA:BEGIN*/\nconst EXPLORER = "
             + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
             + ";\n/*EXPLORER-DATA:END*/")
    return DATA_MARK.sub(lambda _: block, page)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the page is out of date")
    args = parser.parse_args()
    page = PAGE.read_text(encoding="utf-8")
    updated = render(page, build_data(), KIT.read_text(encoding="utf-8"))
    if args.check:
        if updated != page:
            print("web/chemical-space.html is stale; run python scripts/build_explorer.py", file=sys.stderr)
            return 1
        return 0
    PAGE.write_text(updated, encoding="utf-8")
    print(f"updated {PAGE.relative_to(ROOT)} ({len(updated) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
