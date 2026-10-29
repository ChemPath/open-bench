# ChemPath Demo

**Molecular characterization for botanical formulations: resolve each compound to a verified structure, report identity and physicochemical descriptors, and state coverage explicitly.**

ChemPath is the molecular characterization engine in Cloak & Quill Research's NeuroBotanica platform. Testing labs submit a formulation (compound names, reported percentages, and optional explicit structures). ChemPath returns a Molecular Characterization Report with per-compound structure identity, QC information, and a machine-readable statement of scope.

This repository is an **open reference implementation of ChemPath's output contract**. It produces reports with the same shape and status semantics as the hosted service, using only open-source RDKit and a small public reference library. The production engine is proprietary, hosted only, and **not** included here. See [What this demo is and isn't](#what-this-demo-is-and-isnt).

---

## Quickstart

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

## Request → report

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

| Status | Meaning | Hosted API |
| --- | --- | --- |
| `success` | Every entry characterized | 200 |
| `partial` | Some entries characterized; only those count toward coverage | 200 |
| `failed` | No entry characterized; stored, but no exportable report | 422 on analysis, 409 on export |

Uncharacterizable entries are always returned with a reason. They are never silently dropped.

Full contract: [`docs/api_contract.md`](docs/api_contract.md).

---

## Explainability layer (SHAP)

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

## What this demo is and isn't

| This repository includes | Not included (hosted ChemPath only) |
| --- | --- |
| The public request/response contract and status semantics | The production characterization engine and its internals |
| Structure identity and descriptors from open-source RDKit | Proprietary data sources, knowledge bases and reference databases |
| Simple, illustrative QC notes written for this demo | Production QC rules, thresholds and scoring |
| SHAP on a synthetic model with a planted ground truth | Production models, weights, features or training data |
| A thin client for the hosted API (bring your own credentials) | Service endpoints, credentials or deployment details |

Every output is labeled `SYNTHETIC DEMO`. No output here, or from the hosted service, establishes synergy, efficacy, dosing, measured mixture composition, farm-to-patient traceability, or regulatory approval. Laboratory confirmation is required.

More detail: [`docs/scope.md`](docs/scope.md).

---

## Hosted API (testing labs)

Registered testing labs call the hosted service with an `X-API-Key`. Endpoints:

```
POST /api/v1/chempath/formulation
POST /api/v1/chempath/batch                    (up to 25 items)
GET  /api/v1/chempath/{analysis_id}/report     (?format=json for JSON; PDF by default)
GET  /api/v1/chempath/history
GET  /api/lab/status
```

```python
from chempath_demo.client import ChemPathClient

client = ChemPathClient(base_url="<from onboarding>", api_key="<your lab key>")
result = client.formulation({"formulation_name": "SYNTHETIC check", "entries": [{"name": "CBN"}]})
```

The client has no default endpoint. Base URL and credentials come from lab onboarding. Every authenticated call counts toward your lab's quota.

---

## Repository layout

```
chempath_demo/
  schema.py        request validation (entries, percentages, structures)
  library.py       name → structure lookup against the reference library
  characterize.py  per-compound characterization, formulation and batch analysis
  report.py        JSON and PDF report rendering
  explain.py       SHAP demo on a synthetic model
  client.py        hosted-API client
  cli.py           command-line interface
data/reference_compounds.csv   16 public structures (cannabinoids, terpenes, polyphenols)
examples/                      synthetic request files
tests/                         pytest suite
docs/                          API contract, scope, research ethics
```

```bash
pytest --cov=chempath_demo
```

The suite has 36 tests with 98% line coverage. It includes InChIKey checks for CBN, CBD, Δ9-THC, caffeine and quercetin against their published identifiers.

---

## About

Cloak & Quill Research is a 501(c)(3) research organization in Henderson, Nevada. It works on natural therapeutic discovery through cheminformatics, systems biology and machine learning, with traditional-knowledge partnerships governed by free, prior and informed consent. See [`docs/research_ethics.md`](docs/research_ethics.md).

Lab partnerships and API access: partnerships@cloakandquill.org
