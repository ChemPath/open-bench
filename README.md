# Open Bench

**Interactive, public demonstrations of computational chemistry and explainable ML for natural-product research. Every demo uses open methods and public or synthetic data, so its results can be checked rather than just believed. Production engines are not included.**

| Demo | Status | Run it |
| --- | --- | --- |
| **ChemPath Characterization:** structure identity, descriptors and coverage for botanical formulations, plus SHAP on a synthetic model | ✅ Live | [`web/index.html`](web/index.html) · `python -m chempath_demo` |
| Chemical Space Explorer | Planned | — |
| SHAP Playground | Planned | — |
| Similarity & Scaffold View | Planned | — |

---

## ChemPath Characterization

**Molecular characterization for botanical formulations: resolve each compound to a verified structure, report identity and physicochemical descriptors, and state coverage explicitly.**

ChemPath is the molecular characterization engine in Cloak & Quill Research's NeuroBotanica platform. Given a formulation (compound names, reported percentages, and optional explicit structures), it returns a Molecular Characterization Report: per-compound structure identity, physicochemical descriptors, coverage and QC information, and an explicit statement of scope.

This repository is a **public demonstration** of what ChemPath does. It runs end to end on open-source RDKit, a small public reference library, and synthetic example formulations. The production ChemPath engine is proprietary and is **not** included here. See [What this demo is and isn't](#what-this-demo-is-and-isnt).

---

### Quickstart

```bash
pip install -r requirements.txt
```

```bash
python -m chempath_demo analyze examples/cbn_formulation.json --pdf out/cbn.pdf
```

```
Molecular Characterization Report — SYNTHETIC DEMO — not a laboratory result
  formulation : SYNTHETIC CBN Demonstration
  status      : success  (coverage 100%)
  ✓ CBN                  C21H26O2    VBGLYOIFKLUMQG-UHFFFAOYSA-N
  · reported percentages sum to 1.0% (not independently verified)
```

Other commands:

| Command | What it shows |
| --- | --- |
| `python -m chempath_demo analyze examples/partial_formulation.json` | `partial` status: three entries resolved (one by explicit SMILES), one reported as uncharacterizable with a reason |
| `python -m chempath_demo batch examples/mixed_batch.json` | Batch of 4 items: valid items succeed, invalid ones fail with their error, and every item is accounted for |
| `python -m chempath_demo library` | The 16 bundled reference structures with computed formula and InChIKey |
| `python -m chempath_demo explain` | SHAP explainability on a synthetic model with a known ground truth |

---

### Website demo (`web/index.html`)

A single, self-contained page that runs the same characterization **in the visitor's browser** using [RDKit.js](https://www.npmjs.com/package/@rdkit/rdkit). There is no server, no upload and no build step. Drop the file onto any static host or embed it in a site page.

- Presets (CBN reference, full-spectrum, partial-result), plus free entry by name or SMILES
- Structure drawing, formula, InChIKey and descriptor profile for each compound; coverage, QC notes and scope statement
- Downloadable JSON report
- SHAP section with precomputed results from the synthetic model (global importance and per-compound explanations)
- Light and dark themes; works at phone width

By default RDKit.js loads from unpkg (`@rdkit/rdkit@2025.3.4-1.0.0`). To self-host, copy that package's `dist/` folder to your site and set `<html data-rdkit-base="/path/to/dist/">`.

After changing the library, examples or SHAP model, re-embed the page data:

```bash
python scripts/build_web.py
```

---

### Request → report

**Request**

```json
{
  "formulation_name": "SYNTHETIC CBN Demonstration",
  "entries": [
    { "name": "CBN", "percentage": 1 },
    { "name": "CBDV", "percentage": 0.8, "smiles": "CCCc1cc(O)c([C@@H]2C=C(C)CC[C@H]2C(C)=C)c(O)c1" }
  ]
}
```

- `entries` (not `compounds`), with at least one nonblank `name`
- `percentage` is optional, must be finite, and must be between 0 and 100 inclusive
- `smiles` or `inchi` is optional; an explicit structure takes precedence over name lookup

**Report (abridged)**

```json
{
  "report_type": "Molecular Characterization Report",
  "label": "SYNTHETIC DEMO — not a laboratory result",
  "analysis_id": "demo_3f9c1a2b7d4e",
  "status": "success",
  "entries": [{
    "input_name": "CBN",
    "status": "characterized",
    "structure_source": "reference_library",
    "molecular_formula": "C21H26O2",
    "inchikey": "VBGLYOIFKLUMQG-UHFFFAOYSA-N",
    "molecular_weight": 310.437,
    "descriptors": { "logp_crippen": 5.728, "tpsa": 29.46, "h_bond_donors": 1, "...": "..." }
  }],
  "qc": { "entries_submitted": 1, "entries_characterized": 1, "coverage": 1.0, "notes": ["..."] },
  "scope": { "covers": ["..."], "does_not_cover": ["synergy ...", "efficacy ...", "..."] },
  "disclaimer": "Structure characterization only. ..."
}
```

**Status semantics**

| Status | Meaning |
| --- | --- |
| `success` | Every entry characterized |
| `partial` | Some entries characterized; only those count toward coverage |
| `failed` | No entry characterized; no exportable report |

Uncharacterizable entries are always returned with a reason. They are never silently dropped.

Full field reference: [`docs/report_format.md`](docs/report_format.md).

---

### Explainability layer (SHAP)

`python -m chempath_demo explain` trains a gradient-boosted classifier on **synthetic** descriptor data. The label follows a planted rule: a noisy logistic function of logP (positive) and TPSA (negative). It then uses SHAP `TreeExplainer` to check that the explanation recovers that rule.

```
held-out accuracy: 0.920
planted drivers ('logp_crippen', 'tpsa') recovered as top features: True

global importance (mean |SHAP|, log-odds):
  logp_crippen       2.834
  tpsa               1.742
  aromatic_rings     0.205
  ...
```

Because the ground truth is known, the explanation can be checked rather than just believed. The same model then gives local, per-compound explanations for the reference library. These are demonstrations of the method, **not** bioactivity, efficacy or safety predictions.

---

### What this demo is and isn't

| This demo includes | Not included |
| --- | --- |
| Request and report format with status semantics | The production characterization engine and its internals |
| Structure identity and descriptors from open-source RDKit | Proprietary data sources, knowledge bases and reference databases |
| Simple, illustrative QC notes written for this demo | Production QC rules, thresholds and scoring |
| SHAP on a synthetic model with a planted ground truth | Production models, weights, features or training data |
| Synthetic example formulations | Service endpoints, customer data or deployment details |

Every output is labeled `SYNTHETIC DEMO`. No ChemPath output establishes synergy, efficacy, dosing, measured mixture composition, farm-to-patient traceability, or regulatory approval. Laboratory confirmation is required.

More detail: [`docs/scope.md`](docs/scope.md).

---

## Repository layout

```
chempath_demo/
  schema.py        request validation (entries, percentages, structures)
  library.py       name → structure lookup against the reference library
  characterize.py  per-compound characterization, formulation and batch analysis
  report.py        JSON and PDF report rendering
  explain.py       SHAP demo on a synthetic model
  cli.py           command-line interface
web/index.html                 browser demo for the website
scripts/build_web.py           embeds library, presets and SHAP results into the page
data/reference_compounds.csv   16 public structures (cannabinoids, terpenes, polyphenols)
examples/                      synthetic request files
tests/                         pytest suite (browser test needs Node + Playwright)
docs/                          report format, scope, research ethics
```

```bash
pytest --cov=chempath_demo
```

The suite includes InChIKey checks for CBN, CBD, Δ9-THC, caffeine and quercetin against their published identifiers.

---

## License

[MIT](LICENSE). The license covers the code and documentation in this repository. It grants no rights to the production ChemPath engine or to any other Cloak & Quill platform, none of which is included here.

## About

Cloak & Quill Research is a 501(c)(3) research organization in Henderson, Nevada. It works on natural therapeutic discovery through cheminformatics, systems biology and machine learning, with traditional-knowledge partnerships governed by free, prior and informed consent. See [`docs/research_ethics.md`](docs/research_ethics.md).

Partnerships and lab access: partnerships@cloakandquill.org
