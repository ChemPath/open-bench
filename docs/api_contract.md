# ChemPath API Contract

This document describes the public request/response contract shared by this demo and the hosted ChemPath service. Field names and status semantics match. Values computed by the hosted engine can differ from the demo's open RDKit output.

## Formulation request

| Field | Type | Rules |
| --- | --- | --- |
| `formulation_name` | string | Optional; defaults to `Untitled formulation` |
| `entries` | array | Required, at least one item. Use `entries`, not `compounds` |
| `entries[].name` | string | Required, nonblank |
| `entries[].percentage` | number | Optional; finite; between 0 and 100 inclusive. Not independently verified |
| `entries[].smiles` | string | Optional explicit structure; takes precedence over name lookup |
| `entries[].inchi` | string | Optional explicit structure; used when `smiles` is absent |

## Request errors

| Condition | Hosted API | Demo |
| --- | --- | --- |
| Body is not an object; `entries` missing or not a list; entry not an object | 400 | `RequestError(http_status=400)` |
| Empty `entries`; blank name; invalid percentage | 422 | `RequestError(http_status=422)` |
| No entry could be characterized | 422, stored as failed | report with `status: "failed"`, `http_status: 422` |
| Export of a failed analysis | 409 | `write_pdf` raises `ValueError` |
| Missing or invalid API key | 401 | n/a |
| Non-testing-lab account | 403 | n/a |
| Unknown analysis, or one belonging to another lab | 404 | n/a |
| Quota exceeded | 429 + `Retry-After` | n/a |

## Report

| Field | Description |
| --- | --- |
| `analysis_id` | Identifier for report retrieval (`demo_…` in this repo) |
| `status` | `success`, `partial`, or `failed` |
| `entries[]` | Per-compound result, in request order |
| `entries[].status` | `characterized` or `uncharacterizable` |
| `entries[].reason` | Present when uncharacterizable |
| `entries[].structure_source` | `reference_library`, `smiles`, `inchi`, or `name` (unresolved) |
| `entries[].molecular_formula`, `inchi`, `inchikey`, `canonical_smiles` | Structure identity |
| `entries[].molecular_weight`, `exact_mass` | Average MW (g/mol) and monoisotopic mass |
| `entries[].descriptors` | logP (Crippen), TPSA, H-bond donors/acceptors, rotatable bonds, heavy atoms, rings, aromatic rings, Fsp3, stereocenters |
| `qc.coverage` | Characterized entries ÷ submitted entries |
| `qc.notes` | Input-consistency notes (percentage totals, duplicates, unspecified stereochemistry) |
| `scope.covers`, `scope.does_not_cover` | Machine-readable scope statement |
| `disclaimer` | Human-readable scope statement |

## Batch

```json
{
  "items": [
    { "kind": "formulation", "formulation": { "entries": [ { "name": "CBN" } ] } },
    { "kind": "compound", "compound": { "name": "Quercetin" } }
  ]
}
```

- 1–25 items.
- Each item returns its own status. An invalid item fails with its error and does not fail the batch.
- Batch `status` is `success` (no failures), `partial`, or `failed` (no successes).
- A formulation item with `partial` status counts as succeeded.
