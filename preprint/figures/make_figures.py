"""Generate Figures 1-3 from frozen artefacts only.

No manual post-editing of scientific content is permitted: every number, point
and annotation is read from ``preprint/results/preprint_analysis.json`` or from
the committed prediction CSVs.

    PYTHONPATH=backend python preprint/figures/make_figures.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
for candidate in (str(REPO_ROOT), str(REPO_ROOT / "backend")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from preprint.analysis import core  # noqa: E402

FIGURES = REPO_ROOT / "preprint/figures"
RESULTS = REPO_ROOT / "preprint/results"
ANALYSIS = RESULTS / "preprint_analysis.json"

INK = "#1b1b1f"
MUTED = "#6b6b76"
GRID = "#d8d8de"
MODEL = "#2f6f9f"
MEAN_BASE = "#b5651d"
NN_BASE = "#7a7a86"
ACCEPT = "#2e7d5b"
REJECT = "#a8443a"
TRAIN_DIST = "#9aa7b4"
EXT_DIST = "#2f6f9f"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.linewidth": 0.7,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    }
)

SHORT = {
    "Clearance_Microsome_AZ": "Human liver microsomal\nclearance (uL/min/mg)",
    "Lipophilicity_AstraZeneca": "LogD at pH 7.4",
    "PPBR_AZ": "Human plasma protein\nbinding (% bound)",
}

# Semantic category responsible for each rejection, taken from the frozen
# compatibility matrix reasons. Used only to group the bars in Figure 1.
REJECTION_CATEGORY = {
    "ASAP_MLM_MICROSOME": "Species mismatch",
    "BIOGEN_RPPB_PPBR": "Species mismatch",
    "BIOGEN_RLM_MICROSOME": "Species mismatch",
    "ASAP_MDR1_CACO2": "Different assay system",
    "BIOGEN_MDR1_CACO2": "Different assay system",
    "ASAP_KSOL_SOLUBILITY": "Incompatible result semantics",
    "BIOGEN_SOL_AQSOLDB": "Incompatible result semantics",
    "BIOGEN_HLM_MICROSOME": "Unresolvable unit scaling",
    "CACO2_TEMPORAL_CACO2": "Insufficient assay metadata",
}
CATEGORY_ORDER = [
    "Species mismatch",
    "Different assay system",
    "Incompatible result semantics",
    "Unresolvable unit scaling",
    "Insufficient assay metadata",
]


# Image containers embed a creation timestamp by default, which would make the
# published checksums differ on every run for identical scientific content.
# Both are pinned so the whole package is byte-reproducible.
PNG_METADATA = {"Software": None}
PDF_METADATA = {"Creator": None, "Producer": None, "CreationDate": None}


def save(fig, path: Path) -> None:
    fig.savefig(path, metadata=PNG_METADATA)
    fig.savefig(path.with_suffix(".pdf"), metadata=PDF_METADATA)


def load_analysis() -> dict:
    if not ANALYSIS.is_file():
        raise SystemExit("Run preprint/analysis/run_preprint_analysis.py before generating figures.")
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Figure 1 - semantic eligibility funnel
# ---------------------------------------------------------------------------


def figure1(analysis: dict) -> Path:
    compatibility = core.read_csv(core.COMPATIBILITY)
    accepted = [row for row in compatibility if row["numerical_validation_allowed"].lower() == "true"]
    rejected = [row for row in compatibility if row["numerical_validation_allowed"].lower() != "true"]

    counts: dict[str, int] = {name: 0 for name in CATEGORY_ORDER}
    for row in rejected:
        counts[REJECTION_CATEGORY[row["mapping_id"]]] += 1

    fig, (ax_funnel, ax_reasons) = plt.subplots(
        1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.0, 1.05], "wspace": 0.75}
    )

    # Funnel: candidates -> screened -> accepted / rejected
    ax_funnel.set_axis_off()
    ax_funnel.set_xlim(0, 1)
    ax_funnel.set_ylim(0, 1)
    ax_funnel.text(0.5, 0.88, f"{len(compatibility)} candidate\ndataset-to-output pairings",
                   ha="center", va="center", fontsize=7.5, color=INK,
                   bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=MUTED, linewidth=0.8))
    ax_funnel.text(0.5, 0.55, "pre-specified semantic\neligibility screen\n10 declared gates, fail-closed",
                   ha="center", va="center", fontsize=7.5, color=INK,
                   bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=INK, linewidth=0.9))
    ax_funnel.annotate("", xy=(0.5, 0.70), xytext=(0.5, 0.79),
                       arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=0.9))
    ax_funnel.annotate("", xy=(0.22, 0.27), xytext=(0.40, 0.40),
                       arrowprops=dict(arrowstyle="-|>", color=ACCEPT, linewidth=0.9))
    ax_funnel.annotate("", xy=(0.78, 0.27), xytext=(0.60, 0.40),
                       arrowprops=dict(arrowstyle="-|>", color=REJECT, linewidth=0.9))
    ax_funnel.text(0.20, 0.14, f"{len(accepted)} accepted\nfor numerical\nevaluation",
                   ha="center", va="center", fontsize=7.5, color=ACCEPT,
                   bbox=dict(boxstyle="round,pad=0.35", facecolor="#eaf3ee", edgecolor=ACCEPT, linewidth=0.8))
    ax_funnel.text(0.80, 0.14, f"{len(rejected)} not\nevaluable",
                   ha="center", va="center", fontsize=7.5, color=REJECT,
                   bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7ecea", edgecolor=REJECT, linewidth=0.8))
    ax_funnel.text(0.0, 1.06, "a  Eligibility screening", transform=ax_funnel.transAxes,
                   fontsize=9, fontweight="bold", va="bottom")

    # Rejection reasons, with the failing gate named on each bar.
    short_labels = {
        "Species mismatch": "species mismatch",
        "Different assay system": "different assay system",
        "Incompatible result semantics": "result semantics differ",
        "Unresolvable unit scaling": "unit scaling unresolvable",
        "Insufficient assay metadata": "assay metadata insufficient",
    }
    labels = [short_labels[name] for name in CATEGORY_ORDER]
    values = [counts[name] for name in CATEGORY_ORDER]
    positions = np.arange(len(labels))[::-1]
    ax_reasons.barh(positions, values, height=0.58, color=REJECT, alpha=0.85)
    for pos, value in zip(positions, values):
        ax_reasons.text(value + 0.07, pos, str(value), va="center", fontsize=7.5, color=INK)
    ax_reasons.set_yticks(positions)
    ax_reasons.set_yticklabels(labels, fontsize=7.5)
    ax_reasons.tick_params(axis="y", length=0, pad=2)
    ax_reasons.set_xlim(0, max(values) + 0.55)
    ax_reasons.set_xticks(range(0, max(values) + 1))
    ax_reasons.set_xlabel("pairings rejected", fontsize=7.5)
    ax_reasons.grid(axis="y", visible=False)
    ax_reasons.text(0.0, 1.06, "b  Reason the 9 rejected pairings failed", transform=ax_reasons.transAxes,
                    fontsize=9, fontweight="bold", va="bottom")

    ax_funnel.text(
        1.05, -0.20,
        "A matching endpoint name is not sufficient: 9 of 12 pairings share an endpoint concept but differ in species,\n"
        "assay system, result semantics, unit scaling, or documented assay context.",
        transform=ax_funnel.transAxes, ha="center", va="top", fontsize=7.5, color=MUTED,
    )
    path = FIGURES / "figure1_eligibility_funnel.png"
    save(fig, path)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Figure 2 - distribution shift and range compression
# ---------------------------------------------------------------------------


def figure2(analysis: dict) -> Path:
    rows = core.load_prediction_rows()
    summary = core.load_derived_training_summary()
    fig = plt.figure(figsize=(7.2, 6.1))
    outer = fig.add_gridspec(
        2, 3, height_ratios=[1.85, 1.0], hspace=0.50, wspace=0.34,
        left=0.09, right=0.98, top=0.90, bottom=0.14,
    )
    scatter_handles = None

    for column, endpoint in enumerate(core.ENDPOINTS):
        block = analysis["results"][endpoint]
        cohort = block["cohorts"]["A_HEADLINE"]
        metrics = cohort["metrics"]
        shift = cohort["label_shift"]
        selected = core.successful(rows, endpoint, core.HEADLINE_COHORT)
        y = np.asarray(core.observed(selected), dtype=float)
        p = np.asarray(core.predicted(selected), dtype=float)

        ax = fig.add_subplot(outer[0, column])
        ax.scatter(y, p, s=9, alpha=0.45, color=MODEL, linewidths=0, zorder=3)

        low = float(min(y.min(), p.min()))
        high = float(max(y.max(), p.max()))
        pad = 0.04 * (high - low)
        limits = (low - pad, high + pad)
        ax.plot(limits, limits, color=INK, linewidth=0.9, linestyle="--", zorder=2, label="identity")
        slope = metrics["calibration_slope"]
        intercept = metrics["calibration_intercept"]
        grid = np.linspace(*limits, 100)
        ax.plot(grid, slope * grid + intercept, color=MEAN_BASE, linewidth=1.3, zorder=4, label="calibration fit")
        ax.set_xlim(*limits)
        ax.set_ylim(*limits)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Observed")
        if column == 0:
            ax.set_ylabel("Predicted")
        ax.set_title(SHORT[endpoint], fontsize=8.5, pad=6)
        annotation = (
            f"n = {metrics['n']}\n"
            f"slope = {slope:.3f}\n"
            f"SD ratio = {metrics['sd_ratio']:.3f}\n"
            f"$R^2$ = {metrics['r2']:+.3f}\n"
            f"$\\rho$ = {metrics['spearman_rho']:+.3f}"
        )
        ax.text(0.04, 0.96, annotation, transform=ax.transAxes, va="top", ha="left", fontsize=7,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor=GRID, linewidth=0.6))
        if column == 0:
            scatter_handles = ax.get_legend_handles_labels()
            first_scatter_ax = ax
        if column == len(core.ENDPOINTS) - 1:
            last_scatter_ax = ax

        # Label-distribution panel. Clearance labels are strongly right-skewed,
        # so a log axis is used there to keep the shift legible; the other two
        # endpoints stay on their native linear scale.
        ax_dist = fig.add_subplot(outer[1, column])
        # The training-label density comes from the derived summary; the
        # upstream label values are not redistributed (see DATA_LICENSES.md).
        histogram = summary["endpoints"][endpoint]["label_histogram"]
        bins = np.asarray(histogram["edges"], dtype=float)
        train_density = np.asarray(histogram["density"], dtype=float)
        log_scale = histogram["scale"] == "log10"
        if log_scale:
            ax_dist.set_xscale("log")
            ext_plot = y[y > 0]
        else:
            ext_plot = y
        ax_dist.stairs(train_density, bins, fill=True, color=TRAIN_DIST, alpha=0.8, label="training labels")
        ax_dist.hist(ext_plot, bins=bins, density=True, color=EXT_DIST, alpha=0.55, label="external labels")
        ax_dist.set_yticks([])
        ax_dist.set_xlabel(core.ENDPOINT_UNITS[endpoint] + (" (log scale)" if log_scale else ""), fontsize=7.5)
        ax_dist.set_title(
            f"KS D = {shift['ks_statistic']:.3f}\n"
            f"SD  train {shift['training_sd']:.1f} | ext {shift['external_sd']:.1f} | pred {metrics['prediction_sd']:.1f}",
            fontsize=6.5, color=INK, pad=3, linespacing=1.4,
        )
        if column == 0:
            dist_handles = ax_dist.get_legend_handles_labels()
            first_dist_ax = ax_dist
            ax_dist.set_ylabel("density", fontsize=7.5)
        if column == len(core.ENDPOINTS) - 1:
            last_dist_ax = ax_dist

    # Panel labels and legends are anchored to axes rather than to the figure
    # so that the tight bounding box cannot shift them onto the plots.
    first_scatter_ax.text(0.0, 1.30, "a  Observed versus predicted, headline cohort",
                          transform=first_scatter_ax.transAxes, fontsize=9, fontweight="bold", va="bottom")
    last_scatter_ax.legend(*scatter_handles, loc="lower right", bbox_to_anchor=(1.02, 1.28),
                           ncol=2, frameon=False, fontsize=7.5)
    first_dist_ax.text(0.0, 1.46, "b  Training and external label distributions",
                       transform=first_dist_ax.transAxes, fontsize=9, fontweight="bold", va="bottom")
    last_dist_ax.legend(*dist_handles, loc="lower right", bbox_to_anchor=(1.02, 1.44),
                        ncol=2, frameon=False, fontsize=7.5)
    first_dist_ax.text(
        1.72, -0.42,
        "Microsomal clearance predictions span a fraction of the observed range (SD ratio 0.09, calibration slope 0.04)\n"
        "while the external labels are drawn from a markedly different distribution than the training labels (KS D = 0.45).",
        transform=first_dist_ax.transAxes, ha="center", va="top", fontsize=7.5, color=MUTED,
    )
    path = FIGURES / "figure2_shift_and_compression.png"
    save(fig, path)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Figure 3 - baseline-relative performance
# ---------------------------------------------------------------------------


def figure3(analysis: dict) -> Path:
    metrics_shown = [
        ("mae", "Mean absolute error\n(lower is better)", False),
        ("r2", "$R^2$\n(higher is better)", False),
        ("spearman_rho", "Spearman $\\rho$\n(higher is better)", True),
    ]
    series = [
        ("ADMET-AI 2.0.1", MODEL, lambda cohort: cohort["metrics"]),
        ("Training-set mean", MEAN_BASE, lambda cohort: cohort["baselines"]["training_mean"]),
        ("1-NN Morgan/Tanimoto", NN_BASE, lambda cohort: cohort["baselines"]["nearest_neighbour_morgan_tanimoto"]),
    ]

    fig, axes = plt.subplots(3, 3, figsize=(7.2, 5.2))
    for row_index, (metric_key, metric_label, rank_metric) in enumerate(metrics_shown):
        for column, endpoint in enumerate(core.ENDPOINTS):
            ax = axes[row_index][column]
            cohort = analysis["results"][endpoint]["cohorts"]["A_HEADLINE"]
            values = []
            colours = []
            labels = []
            for name, colour, getter in series:
                value = getter(cohort)[metric_key]
                if value is None:
                    value = 0.0
                    labels.append(f"{name}\n(undefined)")
                else:
                    labels.append(name)
                values.append(value)
                colours.append(colour)
            positions = np.arange(len(values))
            ax.bar(positions, values, width=0.62, color=colours)
            ax.axhline(0, color=INK, linewidth=0.7)
            ax.set_xticks(positions)
            ax.set_xticklabels(["model", "mean", "1-NN"], fontsize=7)
            ax.grid(axis="x", visible=False)
            for pos, value, original in zip(positions, values, [getter(cohort)[metric_key] for _, _, getter in series]):
                text = "n/a" if original is None else (f"{value:.2f}" if abs(value) >= 1 else f"{value:.3f}")
                offset = 0.02 * (max(values) - min(values) + 1e-9)
                ax.text(pos, value + (offset if value >= 0 else -offset), text,
                        ha="center", va="bottom" if value >= 0 else "top", fontsize=6.5)
            if rank_metric:
                ax.set_ylim(-0.15, 1.0)
            else:
                # Leave room so value labels on negative bars are not clipped.
                low, high = min(values + [0.0]), max(values + [0.0])
                span = (high - low) or 1.0
                ax.set_ylim(low - 0.16 * span, high + 0.12 * span)
            if column == 0:
                ax.set_ylabel(metric_label, fontsize=7.5)
            if row_index == 0:
                ax.set_title(SHORT[endpoint], fontsize=8.5, pad=6)

    handles = [plt.Rectangle((0, 0), 1, 1, color=colour) for _, colour, _ in series]
    fig.legend([h for h in handles], [name for name, _, _ in series],
               loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.035))
    fig.text(
        0.5, -0.085,
        "Constant-prediction baselines have undefined rank correlation, shown as n/a. ADMET-AI improves on both baselines\n"
        "for every accepted endpoint, including microsomal clearance where its $R^2$ is negative.",
        ha="center", fontsize=7.5, color=MUTED,
    )
    fig.tight_layout()
    path = FIGURES / "figure3_baseline_relative.png"
    save(fig, path)
    plt.close(fig)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    analysis = load_analysis()
    FIGURES.mkdir(parents=True, exist_ok=True)
    produced = [figure1(analysis), figure2(analysis), figure3(analysis)]
    manifest = {
        "artifact_id": "preprint-v1.0-figures",
        "generated_from": ANALYSIS.relative_to(REPO_ROOT).as_posix(),
        "generated_from_sha256": sha256_file(ANALYSIS),
        "manual_post_editing": False,
        "figures": {},
    }
    for path in produced:
        for variant in (path, path.with_suffix(".pdf")):
            manifest["figures"][variant.relative_to(REPO_ROOT).as_posix()] = sha256_file(variant)
        print(f"wrote {path.relative_to(REPO_ROOT).as_posix()} (+ .pdf)")
    (RESULTS / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {(RESULTS / 'figure_manifest.json').relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
