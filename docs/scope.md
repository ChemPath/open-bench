# Scope of This Demo

## What ChemPath characterizes

ChemPath answers one question per compound: **what structure is this, and what are its standard molecular properties?** For each formulation entry, it:

1. resolves the entry to a structure (an explicit SMILES/InChI, or a name lookup)
2. reports identity (formula, InChI, InChIKey, canonical SMILES) and physicochemical descriptors
3. records whether the entry was characterized, with a reason if it wasn't
4. summarizes coverage and flags input-consistency issues

## What it does not claim

These limits apply to ChemPath generally, not only to this demo:

- **Composition:** reported percentages are echoed from the request, not measured or verified.
- **Interaction:** no synergy, entourage, or compound–compound interaction claims.
- **Clinical:** no efficacy, therapeutic benefit, dosing, or safety claims.
- **Traceability:** no farm-to-patient chain of custody.
- **Regulatory:** no approval or regulatory-suitability determination.

Laboratory confirmation is required for any decision.

## How the demo differs from production ChemPath

| Aspect | Demo (this repo) | Production ChemPath |
| --- | --- | --- |
| Name resolution | 16-compound public CSV | Not published |
| Structure toolkit | Open-source RDKit | Proprietary, not published |
| QC notes | Simple illustrative checks | Production rules, not published |
| Explainability | SHAP on a synthetic, planted-rule model | Not published |
| Outputs | Labeled `SYNTHETIC DEMO` | Laboratory reports |

Demo outputs are for illustration only. They are not laboratory results and should not be presented as revalidated production reports.

## Reference library provenance

`data/reference_compounds.csv` holds structures transcribed from public chemical databases. The suite checks InChIKeys for CBN, CBD, Δ9-THC, caffeine and quercetin against published identifiers. Treat the other entries as convenience structures and verify them before any research use.

## Chemical Space Explorer dataset

`data/chemical_space.csv` holds 65 natural products across seven families: phytocannabinoids, monoterpenoids, sesquiterpenoids, flavonoids, phenolics, alkaloids, and triterpenoids/steroids. Each structure was checked in two ways: its formula against the published molecular formula, and its InChIKey connectivity block against published identifiers. Compounds that could not be confirmed confidently were left out.

- `stereo = defined`: full stereochemistry is given, and the InChIKey matches the natural configuration.
- `stereo = 2D only`: tetrahedral stereochemistry is deliberately omitted. These structures are correct as 2D connectivity, which is all the explorer's 2D descriptors and fingerprints use. They do not identify a specific stereoisomer.

The checks were made without live database access. Spot-check against PubChem before any research use.
