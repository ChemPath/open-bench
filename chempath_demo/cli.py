"""Command-line interface for the ChemPath demo.

Examples::

    python -m chempath_demo analyze examples/cbn_formulation.json --pdf out/cbn.pdf
    python -m chempath_demo batch examples/mixed_batch.json
    python -m chempath_demo library
    python -m chempath_demo explain
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from rdkit import Chem

from chempath_demo import __version__
from chempath_demo.characterize import analyze_batch, analyze_formulation, describe
from chempath_demo.library import compounds
from chempath_demo.report import write_json, write_pdf
from chempath_demo.schema import RequestError


def _load(path: str) -> Any:
    """Read a JSON request file, or stdin when ``path`` is ``-``."""
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RequestError(f"malformed JSON: {exc}", 400) from exc


def _summary(report: dict[str, Any]) -> str:
    """One-screen text summary of a formulation report."""
    lines = [
        f"{report['report_type']} — {report['label']}",
        f"  formulation : {report['formulation_name']}",
        f"  analysis_id : {report['analysis_id']}",
        f"  status      : {report['status']}  (coverage {report['qc']['coverage']:.0%})",
    ]
    for e in report["entries"]:
        if e["status"] == "characterized":
            lines.append(f"  ✓ {e['input_name']:<20} {e['molecular_formula']:<11} {e['inchikey']}")
        else:
            lines.append(f"  ✗ {e['input_name']:<20} {e['reason']}")
    lines += [f"  · {n}" for n in report["qc"]["notes"]]
    return "\n".join(lines)


def _emit(obj: dict[str, Any], out: Optional[str]) -> None:
    """Write JSON to ``out`` or print it."""
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        write_json(obj, Path(out))
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze one formulation request file."""
    report = analyze_formulation(_load(args.request))
    print(_summary(report), file=sys.stderr)
    _emit(report, args.out)
    if args.pdf:
        if report["status"] == "failed":
            print("no PDF for a failed analysis (API equivalent: 409)", file=sys.stderr)
        else:
            Path(args.pdf).parent.mkdir(parents=True, exist_ok=True)
            write_pdf(report, Path(args.pdf))
            print(f"wrote {args.pdf}", file=sys.stderr)
    return 2 if report["status"] == "failed" else 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Analyze a batch request file."""
    result = analyze_batch(_load(args.request))
    print(f"batch {result['batch_id']}: {result['status']} — "
          f"{result['items_succeeded']} succeeded, {result['items_failed']} failed", file=sys.stderr)
    _emit(result, args.out)
    return 2 if result["status"] == "failed" else 0


def cmd_library(_: argparse.Namespace) -> int:
    """List the bundled reference compounds with computed identity fields."""
    for c in compounds():
        d = describe(Chem.MolFromSmiles(c.smiles))
        print(f"{c.name:<20} {c.compound_class:<20} {d['molecular_formula']:<11} {d['inchikey']}")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    """Run the synthetic SHAP demo and explain the reference compounds."""
    from chempath_demo.explain import PLANTED_DRIVERS, run

    rows = []
    for c in compounds():
        d = describe(Chem.MolFromSmiles(c.smiles))
        rows.append({"name": c.name, "molecular_weight": d["molecular_weight"], **d["descriptors"]})
    result = run(rows, n=args.samples, seed=args.seed)

    print("SHAP explainability demo — SYNTHETIC model, planted ground truth.")
    print("Outputs are not bioactivity, efficacy or safety predictions.\n")
    print(f"held-out accuracy: {result.test_accuracy:.3f}")
    print(f"planted drivers {PLANTED_DRIVERS} recovered as top features: "
          f"{result.planted_drivers_recovered}\n")
    print("global importance (mean |SHAP|, log-odds):")
    for feat, val in result.global_importance.items():
        print(f"  {feat:<18} {val:.3f}")
    print("\nlocal explanations for reference compounds (top 2 contributions):")
    for name, row in result.local.iterrows():
        contrib = row.drop("p_synthetic").sort_values(key=abs, ascending=False)[:2]
        parts = ", ".join(f"{k} {v:+.2f}" for k, v in contrib.items())
        print(f"  {name:<20} p={row['p_synthetic']:.2f}  {parts}")
    return 0 if result.planted_drivers_recovered else 1


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    p = argparse.ArgumentParser(prog="chempath_demo", description=__doc__.splitlines()[0])
    p.add_argument("--version", action="version", version=f"chempath-demo {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="characterize one formulation")
    a.add_argument("request", help="JSON request file, or - for stdin")
    a.add_argument("--out", help="write JSON report here instead of stdout")
    a.add_argument("--pdf", help="also render a PDF report (requires reportlab)")
    a.set_defaults(func=cmd_analyze)

    b = sub.add_parser("batch", help="run a batch of up to 25 items")
    b.add_argument("request")
    b.add_argument("--out")
    b.set_defaults(func=cmd_batch)

    sub.add_parser("library", help="list reference compounds").set_defaults(func=cmd_library)

    e = sub.add_parser("explain", help="SHAP demo on a synthetic model")
    e.add_argument("--samples", type=int, default=2000)
    e.add_argument("--seed", type=int, default=7)
    e.set_defaults(func=cmd_explain)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except RequestError as exc:
        print(f"request rejected (HTTP {exc.http_status} equivalent): {exc}", file=sys.stderr)
        return 1
