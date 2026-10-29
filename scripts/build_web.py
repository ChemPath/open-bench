#!/usr/bin/env python3
"""Embed demo data into ``web/index.html``.

Writes the reference library, example formulations and precomputed SHAP
results (from :mod:`chempath_demo.explain`) into the page between the
``/*DEMO-DATA:BEGIN*/`` and ``/*DEMO-DATA:END*/`` markers, so the page stays a
single self-contained file.

Usage::

    python scripts/build_web.py          # rewrite web/index.html
    python scripts/build_web.py --check  # exit 1 if the page is stale
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rdkit import Chem  # noqa: E402

from chempath_demo import __version__  # noqa: E402
from chempath_demo.characterize import describe  # noqa: E402
from chempath_demo.explain import PLANTED_DRIVERS, run  # noqa: E402
from chempath_demo.library import compounds  # noqa: E402

PAGE = ROOT / "web" / "index.html"
MARKER = re.compile(r"/\*DEMO-DATA:BEGIN\*/.*?/\*DEMO-DATA:END\*/", re.S)
PRESETS = {
    "cbn": "cbn_formulation.json",
    "full": "full_spectrum_formulation.json",
    "partial": "partial_formulation.json",
}
SHAP_SAMPLES, SHAP_SEED = 2000, 7


def build_data() -> dict[str, Any]:
    """Assemble everything the page embeds."""
    library = [
        {"name": c.name, "synonyms": list(c.synonyms), "compound_class": c.compound_class,
         "smiles": c.smiles}
        for c in compounds()
    ]
    rows = []
    for c in compounds():
        d = describe(Chem.MolFromSmiles(c.smiles))
        rows.append({"name": c.name, "molecular_weight": d["molecular_weight"], **d["descriptors"]})
    result = run(rows, n=SHAP_SAMPLES, seed=SHAP_SEED)
    shap = {
        "samples": SHAP_SAMPLES,
        "seed": SHAP_SEED,
        "test_accuracy": round(result.test_accuracy, 3),
        "planted_drivers": list(PLANTED_DRIVERS),
        "recovered": result.planted_drivers_recovered,
        "global": [{"feature": f, "value": round(float(v), 3)}
                   for f, v in result.global_importance.items()],
        "local": [
            {"name": name, "p": round(float(row["p_synthetic"]), 3),
             "contributions": {k: round(float(v), 3) for k, v in row.drop("p_synthetic").items()}}
            for name, row in result.local.iterrows()
        ],
    }
    presets = {k: json.loads((ROOT / "examples" / f).read_text()) for k, f in PRESETS.items()}
    return {"version": __version__, "library": library, "presets": presets, "shap": shap}


def render(page: str, data: dict[str, Any]) -> str:
    """Return ``page`` with the data block replaced."""
    block = ("/*DEMO-DATA:BEGIN*/\nconst DEMO_DATA = "
             + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
             + ";\n/*DEMO-DATA:END*/")
    if not MARKER.search(page):
        raise SystemExit("data markers not found in web/index.html")
    return MARKER.sub(lambda _: block, page)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the page is out of date")
    args = parser.parse_args()
    page = PAGE.read_text(encoding="utf-8")
    updated = render(page, build_data())
    if args.check:
        if updated != page:
            print("web/index.html is stale; run python scripts/build_web.py", file=sys.stderr)
            return 1
        return 0
    PAGE.write_text(updated, encoding="utf-8")
    print(f"updated {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
