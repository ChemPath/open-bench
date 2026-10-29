# Scope of This Demo

## What ChemPath characterizes

ChemPath answers one question per compound: **what structure is this, and what are its standard molecular properties?** For each formulation entry, it:

1. resolves the entry to a structure (an explicit SMILES/InChI, or a name lookup)
2. reports identity (formula, InChI, InChIKey, canonical SMILES) and physicochemical descriptors
3. records whether the entry was characterized, with a reason if it wasn't
4. summarizes coverage and flags input-consistency issues

## What it does not claim

These limits apply to both the hosted service and this demo:

- **Composition:** reported percentages are echoed from the request, not measured or verified.
- **Interaction:** no synergy, entourage, or compound–compound interaction claims.
- **Clinical:** no efficacy, therapeutic benefit, dosing, or safety claims.
- **Traceability:** no farm-to-patient chain of custody.
- **Regulatory:** no approval or regulatory-suitability determination.

Laboratory confirmation is required for any decision.

## How the demo differs from the hosted engine

| Aspect | Demo (this repo) | Hosted ChemPath |
| --- | --- | --- |
| Name resolution | 16-compound public CSV | Hosted service |
| Structure toolkit | Open-source RDKit | Proprietary, not published |
| QC notes | Simple illustrative checks | Production rules, not published |
| Explainability | SHAP on a synthetic, planted-rule model | Not published |
| Persistence, tenancy, quotas, branding | None (local, stateless) | Hosted service |
| Outputs | Labeled `SYNTHETIC DEMO` | Lab reports |

Demo outputs are for illustration and integration testing. They are not laboratory results and should not be presented as revalidated production reports.

## Reference library provenance

`data/reference_compounds.csv` holds structures transcribed from public chemical databases. The suite checks InChIKeys for CBN, CBD, Δ9-THC, caffeine and quercetin against published identifiers. Treat the other entries as convenience structures and verify them before any research use.
