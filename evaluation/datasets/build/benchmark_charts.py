# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/benchmark_charts.py — static, print-quality
figures (PNG + SVG) characterizing the NSLB v1.0 benchmark, for direct
inclusion in a report/paper. Read-only over the stats dict from
analyze_benchmark.compute_all(); writes only under evaluation/reports/figures/.

Palette and form choices follow the dataviz skill's validated defaults
(references/palette.md, references/choosing-a-form.md): magnitude
comparisons use the single sequential blue hue; part-to-whole uses
horizontal stacked bars with the fixed 8-slot categorical order (folding
any 9th+ series into "Other" rather than generating a new hue); no pie
charts, no dual axes, no 3D.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from evaluation.datasets.build.common import REPO_ROOT

FIGURES_DIR = REPO_ROOT / "evaluation" / "reports" / "figures"

# ── dataviz skill palette (references/palette.md), light mode ──────────────
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
               "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQUENTIAL_BLUE = "#2a78d6"
SEQUENTIAL_BLUE_LIGHT = "#9ec5f4"
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
NEUTRAL_REMAINDER = "#e1e0d9"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK_PRIMARY,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_SECONDARY,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "axes.grid": False,
    "font.size": 10,
})


def _save(fig, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(FIGURES_DIR / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def _hbar_magnitude(labels: list[str], values: list[float], title: str,
                     xlabel: str, name: str, value_fmt: str = "{:.0f}") -> None:
    """Sequential single-hue horizontal bar — magnitude comparison, sorted."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]

    fig, ax = plt.subplots(figsize=(8, 0.55 * len(labels) + 1.2))
    bars = ax.barh(labels, values, color=SEQUENTIAL_BLUE, height=0.6, zorder=3)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=12, fontweight="bold", color=INK_PRIMARY, pad=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(left=False)
    ax.xaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
                 value_fmt.format(val), va="center", fontsize=9, color=INK_SECONDARY)
    fig.tight_layout()
    _save(fig, name)


def _stacked_hbar(categories: list[str], series: dict[str, list[float]],
                   title: str, xlabel: str, name: str, colors: list[str] | None = None) -> None:
    """Part-to-whole horizontal stacked bar, fixed categorical color order."""
    colors = colors or CATEGORICAL
    fig, ax = plt.subplots(figsize=(8, 0.55 * len(categories) + 2.0))
    left = [0.0] * len(categories)
    for i, (label, values) in enumerate(series.items()):
        ax.barh(categories, values, left=left, label=label, color=colors[i % len(colors)],
                 height=0.6, zorder=3)
        left = [l + v for l, v in zip(left, values)]
    ax.set_xlabel(xlabel, labelpad=10)
    ax.set_title(title, fontsize=12, fontweight="bold", color=INK_PRIMARY, pad=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(left=False)
    ax.xaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    bottom_margin = 1.4 / (0.55 * len(categories) + 2.0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -bottom_margin * 0.55), ncol=len(series),
              frameon=False, fontsize=9)
    fig.subplots_adjust(bottom=bottom_margin)
    _save(fig, name)


def _grouped_coverage_bar(labels: list[str], covered_pct: list[float],
                           title: str, name: str) -> None:
    """Coverage-vs-remainder as a 100%-stacked horizontal bar per act —
    part-to-whole, two-color (covered / not-yet-covered), not a gauge."""
    fig, ax = plt.subplots(figsize=(8, 0.6 * len(labels) + 1.7))
    remainder = [100 - c for c in covered_pct]
    ax.barh(labels, covered_pct, color=SEQUENTIAL_BLUE, height=0.55, zorder=3, label="Covered")
    ax.barh(labels, remainder, left=covered_pct, color=NEUTRAL_REMAINDER, height=0.55,
            zorder=3, label="Not yet covered")
    for i, (c) in enumerate(covered_pct):
        ax.text(c + 1, i, f"{c:.1f}%", va="center", fontsize=9, color=INK_SECONDARY)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of sections covered", labelpad=10)
    ax.set_title(title, fontsize=12, fontweight="bold", color=INK_PRIMARY, pad=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(left=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2, frameon=False, fontsize=9)
    fig.subplots_adjust(bottom=0.32)
    _save(fig, name)


def generate_all(stats: dict) -> list[str]:
    generated = []

    # 1. Dataset distribution — record counts per dataset
    ov = stats["overview"]
    ds_names = ["ipc_bns_mapping", "retrieval", "document_analysis", "legal_qa",
                "end_to_end", "translation", "multilingual", "robustness", "research"]
    ds_counts = [stats["dataset_statistics"][d]["n_records"] for d in ds_names]
    _hbar_magnitude(ds_names, ds_counts, "NSLB v1.0 — Records per Dataset",
                     "Number of records", "01_dataset_distribution")
    generated.append("01_dataset_distribution")

    # 2. Document category distribution — external corpus, full inventory
    cat_table = stats["corpus_statistics"]["category_table"]
    cats = sorted(cat_table)
    cat_counts = [cat_table[c]["total_documents"] for c in cats]
    _hbar_magnitude(cats, cat_counts, "External Corpus — Documents per Category",
                     "Number of documents (full inventory, n=4020)", "02_document_category_distribution")
    generated.append("02_document_category_distribution")

    # 3. Language distribution — corpus-wide
    lang_dist = stats["corpus_statistics"]["overall_language_distribution"]
    langs = sorted(lang_dist, key=lambda k: -lang_dist[k])
    lang_counts = [lang_dist[l] for l in langs]
    _hbar_magnitude(langs, lang_counts, "External Corpus — Language Distribution",
                     "Number of documents", "03_language_distribution")
    generated.append("03_language_distribution")

    # 4. Coverage chart — BNS/BNSS/BSA section coverage in retrieval.jsonl
    cov = stats["coverage"]
    _grouped_coverage_bar(
        ["BNS (358 sections)", "BNSS (531 sections)", "BSA (170 sections)"],
        [cov["bns_section_coverage_pct"], cov["bnss_section_coverage_pct"], cov["bsa_section_coverage_pct"]],
        "Retrieval Coverage — New-Code Sections Indexed vs Total",
        "04_coverage_chart",
    )
    generated.append("04_coverage_chart")

    # 5. Dataset composition — phase-1 vs corpus-expansion split per dataset
    ds_stats = stats["dataset_statistics"]
    phase1_vals = [ds_stats[d]["n_phase1_records"] for d in ds_names]
    expansion_vals = [ds_stats[d]["n_corpus_expansion_records"] for d in ds_names]
    _stacked_hbar(ds_names, {"Phase-1 (in-repo sources)": phase1_vals,
                              "Corpus-expansion (external corpus)": expansion_vals},
                  "NSLB v1.0 — Dataset Composition by Source Phase",
                  "Number of records", "05_dataset_composition",
                  colors=[CATEGORICAL[0], CATEGORICAL[1]])
    generated.append("05_dataset_composition")

    # 6. Record distribution — share of total benchmark, folded to 8 slots
    total = ov["total_benchmark_records"]
    pairs = sorted(zip(ds_names, ds_counts), key=lambda kv: -kv[1])
    top = pairs[:7]
    other_sum = sum(v for _, v in pairs[7:])
    fold_labels = [p[0] for p in top] + (["Other"] if other_sum else [])
    fold_values = [p[1] for p in top] + ([other_sum] if other_sum else [])
    fig, ax = plt.subplots(figsize=(9, 3.6))
    left = 0.0
    for i, (label, val) in enumerate(zip(fold_labels, fold_values)):
        pct = 100 * val / total
        ax.barh([0], [pct], left=left, color=CATEGORICAL[i % len(CATEGORICAL)], height=0.5,
                label=f"{label} ({val}, {pct:.1f}%)")
        left += pct
    ax.set_xlim(0, 100)
    ax.set_ylim(-1.6, 0.4)
    ax.set_yticks([])
    ax.set_xlabel(f"% of total benchmark records (n={total})", labelpad=10)
    ax.set_title("NSLB v1.0 — Record Distribution Across Datasets", fontsize=12,
                  fontweight="bold", color=INK_PRIMARY, pad=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.55), ncol=3, frameon=False, fontsize=8)
    fig.subplots_adjust(bottom=0.42)
    _save(fig, "06_record_distribution")
    generated.append("06_record_distribution")

    # 7. Corpus composition — external corpus category share (part-to-whole)
    total_corpus = stats["corpus_statistics"]["total_inventoried"]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    left = 0.0
    for i, c in enumerate(sorted(cat_table, key=lambda k: -cat_table[k]["total_documents"])):
        val = cat_table[c]["total_documents"]
        pct = 100 * val / total_corpus
        ax.barh([0], [pct], left=left, color=CATEGORICAL[i % len(CATEGORICAL)], height=0.5,
                label=f"{c} ({val}, {pct:.1f}%)")
        left += pct
    ax.set_xlim(0, 100)
    ax.set_ylim(-1.4, 0.4)
    ax.set_yticks([])
    ax.set_xlabel(f"% of external corpus (n={total_corpus})", labelpad=10)
    ax.set_title("External Corpus — Category Composition", fontsize=12,
                  fontweight="bold", color=INK_PRIMARY, pad=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.5), ncol=3, frameon=False, fontsize=8)
    fig.subplots_adjust(bottom=0.4)
    _save(fig, "07_corpus_composition")
    generated.append("07_corpus_composition")

    return generated


if __name__ == "__main__":
    from evaluation.datasets.build.analyze_benchmark import compute_all
    names = generate_all(compute_all())
    print(f"Generated {len(names)} figures (PNG+SVG) -> {FIGURES_DIR}")
    for n in names:
        print(f"  - {n}.png / {n}.svg")
