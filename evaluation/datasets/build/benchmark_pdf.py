# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/benchmark_pdf.py — renders
evaluation/reports/benchmark_summary.pdf as a real structured PDF
(reportlab Platypus: headings, paragraphs, tables, embedded figures) —
not a text dump of the Markdown file. Content comes from the same stats
dict and table rows as the Markdown/CSV outputs, so all three stay
consistent by construction.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

from evaluation.datasets.build.common import REPO_ROOT

FIGURES_DIR = REPO_ROOT / "evaluation" / "reports" / "figures"
OUT_PATH = REPO_ROOT / "evaluation" / "reports" / "benchmark_summary.pdf"

INK_PRIMARY = colors.HexColor("#0b0b0b")
INK_SECONDARY = colors.HexColor("#52514e")
GRIDLINE = colors.HexColor("#e1e0d9")
SEQUENTIAL_BLUE = colors.HexColor("#2a78d6")
SURFACE = colors.HexColor("#fcfcfb")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("NSLBTitle", parent=ss["Title"], textColor=INK_PRIMARY, fontSize=20))
    ss.add(ParagraphStyle("NSLBH1", parent=ss["Heading1"], textColor=INK_PRIMARY, fontSize=15,
                            spaceBefore=14, spaceAfter=8))
    ss.add(ParagraphStyle("NSLBBody", parent=ss["BodyText"], textColor=INK_SECONDARY, fontSize=9.5,
                            leading=13.5))
    ss.add(ParagraphStyle("NSLBMeta", parent=ss["BodyText"], textColor=INK_SECONDARY, fontSize=8.5,
                            leading=11))
    return ss


def _table(rows: list[list], col_widths=None) -> Table:
    str_rows = [[str(c) for c in row] for row in rows]
    t = Table(str_rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SEQUENTIAL_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, GRIDLINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SURFACE, colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def build_pdf(stats: dict, tables: dict[str, list[list]]) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT_PATH), pagesize=A4,
                              leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                              topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                              title="NyayaSetu Legal Benchmark v1.0 — Characterization Report")
    ss = _styles()
    story = []

    ov = stats["overview"]
    cov = stats["coverage"]
    q = stats["data_quality"]

    story.append(Paragraph("NyayaSetu Legal Benchmark (NSLB) v1.0", ss["NSLBTitle"]))
    story.append(Paragraph("Benchmark Characterization Report", ss["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"{ov['total_benchmark_records']} records across {ov['number_of_datasets']} datasets, "
        f"built from {ov['total_source_documents_phase1_fixtures']} phase-1 in-repo source plus "
        f"{ov['total_documents_deep_processed_external_corpus']} deep-processed documents drawn "
        f"from a {ov['total_source_documents_inventoried_external_corpus']}-document external "
        f"corpus (fully inventoried). No evaluation experiments have been run — this document "
        f"characterizes the ground-truth benchmark itself.",
        ss["NSLBBody"]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("1. Overall Benchmark Summary", ss["NSLBH1"]))
    story.append(_table(tables["table1_benchmark_overview"], col_widths=[11 * cm, 5 * cm]))
    story.append(PageBreak())

    story.append(Paragraph("2. Corpus Statistics", ss["NSLBH1"]))
    story.append(_table(tables["table2_corpus_statistics"]))
    story.append(Spacer(1, 10))
    img_path = FIGURES_DIR / "02_document_category_distribution.png"
    if img_path.exists():
        story.append(Image(str(img_path), width=16 * cm, height=16 * cm * 0.44))
    story.append(Spacer(1, 8))
    img_path = FIGURES_DIR / "03_language_distribution.png"
    if img_path.exists():
        story.append(Image(str(img_path), width=16 * cm, height=16 * cm * 0.34))
    story.append(PageBreak())

    story.append(Paragraph("3. Dataset Statistics", ss["NSLBH1"]))
    story.append(_table(tables["table3_dataset_distribution"], col_widths=[3.2 * cm] + [1.8 * cm] * 6 + [2 * cm]))
    story.append(Spacer(1, 10))
    img_path = FIGURES_DIR / "01_dataset_distribution.png"
    if img_path.exists():
        story.append(Image(str(img_path), width=16 * cm, height=16 * cm * 0.7))
    story.append(PageBreak())
    img_path = FIGURES_DIR / "05_dataset_composition.png"
    if img_path.exists():
        story.append(Image(str(img_path), width=16 * cm, height=16 * cm * 0.75))
    story.append(PageBreak())

    story.append(Paragraph("4. Coverage Statistics", ss["NSLBH1"]))
    story.append(_table(tables["table4_coverage_analysis"], col_widths=[7.5 * cm, 2.5 * cm, 4 * cm, 2.5 * cm]))
    story.append(Spacer(1, 10))
    img_path = FIGURES_DIR / "04_coverage_chart.png"
    if img_path.exists():
        story.append(Image(str(img_path), width=16 * cm, height=16 * cm * 0.38))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Denominators for BNS/BNSS/BSA coverage (358/531/170) are each act's own final section "
        f"number, already extracted verbatim from its repeal clause and stored in "
        f"retrieval.jsonl (ids retr_bns_358, retr_bnss_531, retr_bsa_170) — not an imported fact. "
        f"No authoritative IPC/CrPC/IEA total-section count exists in this project, so only "
        f"absolute mapped-section counts are reported for those acts.",
        ss["NSLBMeta"]))
    story.append(PageBreak())

    story.append(Paragraph("5. Data Quality Analysis", ss["NSLBH1"]))
    story.append(_table(tables["table5_data_quality_summary"], col_widths=[11 * cm, 5 * cm]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Validation success rate: {q['validation_success_rate_pct']}% across "
        f"{q['total_records_checked']} records, independently re-checked by this report "
        f"(duplicate ids, duplicate QA content, contradictory mappings, missing metadata) rather "
        f"than only citing the build-time log.",
        ss["NSLBBody"]))
    story.append(PageBreak())

    story.append(Paragraph("6. Benchmark Characteristics", ss["NSLBH1"]))
    story.append(Paragraph("<b>Strengths</b>", ss["NSLBBody"]))
    story.append(Paragraph(
        "Every record traces to a real, named source; "
        f"{q['validation_success_rate_pct']}% validation success rate; broad absolute IPC/CrPC/IEA "
        "mapping coverage merged from two independent sources.", ss["NSLBBody"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Limitations</b>", ss["NSLBBody"]))
    story.append(Paragraph(
        "Zero contract-type document coverage (rental/employment/loan/sale/service/NDA); "
        f"{cov['language_coverage_count']}/13 language coverage; "
        f"{cov['combined_new_code_coverage_pct']}% retrieval section coverage; legal_qa "
        "corpus-expansion records are entirely template-generated, not human-authored.",
        ss["NSLBBody"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Potential bias / imbalance</b>", ss["NSLBBody"]))
    story.append(Paragraph(
        "Corpus is 93%+ Legal_Notice documents concentrated in 2 of 3 High Court sources; "
        "document_analysis is almost entirely FIR/Legal_Notice/Court_Notice/Affidavit; language "
        "content is English/Marathi only.", ss["NSLBBody"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Remaining work for publication</b>", ss["NSLBBody"]))
    story.append(Paragraph(
        "~20-25 labeled contract-type documents; ~30-40 human-authored comprehension QA records; "
        "a separate multilingual source-acquisition effort; a section-aware statute re-chunker "
        "(or ~50-100 manually labeled retrieval queries) to grow retrieval coverage.",
        ss["NSLBBody"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "Full detail, all 5 tables as CSV, and all 7 figures in PNG+SVG: see "
        "evaluation/reports/benchmark_summary.md, evaluation/reports/tables/, and "
        "evaluation/reports/figures/.", ss["NSLBMeta"]))

    doc.build(story)


if __name__ == "__main__":
    from evaluation.datasets.build.analyze_benchmark import compute_all
    from evaluation.datasets.build.benchmark_tables import build_all_tables
    s = compute_all()
    build_pdf(s, build_all_tables(s))
    print(f"Wrote {OUT_PATH}")
