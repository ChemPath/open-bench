"""JSON and PDF rendering for Molecular Characterization Reports.

The PDF renderer only reads the finished JSON report, so it has no access to
anything beyond what the report already exposes. ``reportlab`` is optional and
needed only for PDF output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(report: dict[str, Any], path: Path) -> Path:
    """Write a report as pretty-printed JSON and return the path."""
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_pdf(report: dict[str, Any], path: Path) -> Path:
    """Render a formulation report to a PDF.

    Args:
        report: Output of :func:`chempath_demo.analyze_formulation`.
        path: Destination file.

    Returns:
        The written path.

    Raises:
        RuntimeError: If ``reportlab`` is not installed.
        ValueError: If the analysis failed (the hosted API returns 409 here).
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:  # pragma: no cover - exercised only without reportlab
        raise RuntimeError("PDF output requires reportlab: pip install reportlab") from exc

    if report["status"] == "failed":
        raise ValueError("failed analyses have no exportable report (API returns 409)")

    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("small", fontSize=8, leading=10)
    story: list[Any] = [
        Paragraph(report["report_type"], styles["Title"]),
        Paragraph(f"<font color='#b45309'><b>{report['label']}</b></font>", styles["BodyText"]),
        Spacer(1, 6),
        Paragraph(
            f"<b>Formulation:</b> {report['formulation_name']} &nbsp; "
            f"<b>Status:</b> {report['status']} &nbsp; "
            f"<b>Analysis ID:</b> {report['analysis_id']}<br/>"
            f"<b>Created:</b> {report['created_at']} &nbsp; "
            f"<b>Engine:</b> {report['engine']['name']} {report['engine']['version']} "
            f"(RDKit {report['engine']['rdkit_version']})",
            small,
        ),
        Spacer(1, 10),
    ]

    rows: list[list[Any]] = [["Input", "Reported %", "Status", "Formula", "MW", "InChIKey"]]
    for e in report["entries"]:
        pct = "—" if e["reported_percentage"] is None else f"{e['reported_percentage']:g}"
        if e["status"] == "characterized":
            rows.append([Paragraph(e["input_name"], small), pct, e["status"], e["molecular_formula"],
                         f"{e['molecular_weight']:.2f}", Paragraph(e["inchikey"], small)])
        else:
            rows.append([Paragraph(e["input_name"], small), pct, e["status"],
                         Paragraph(e["reason"], small), "", ""])
    table = Table(rows, colWidths=[1.2 * inch, 0.8 * inch, 1.1 * inch, 1.2 * inch, 0.7 * inch, 2.2 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [table, Spacer(1, 10)]

    qc = report["qc"]
    story.append(Paragraph(
        f"<b>Coverage:</b> {qc['entries_characterized']}/{qc['entries_submitted']} "
        f"({qc['coverage']:.0%})", styles["BodyText"]))
    for note in qc["notes"]:
        story.append(Paragraph(f"• {note}", small))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Scope — this report does not cover:</b>", styles["BodyText"]))
    for item in report["scope"]["does_not_cover"]:
        story.append(Paragraph(f"• {item}", small))
    story += [Spacer(1, 10), Paragraph(f"<i>{report['disclaimer']}</i>", small)]

    SimpleDocTemplate(str(path), pagesize=letter, title=report["report_type"],
                      leftMargin=0.6 * inch, rightMargin=0.6 * inch).build(story)
    return path
