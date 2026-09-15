"""Deterministic analysis primitives for the external-validation preprint.

Everything here reads frozen, committed artefacts. No network access and no
model inference occur in this module; the single new model run lives in
``hlm_low_clearance_sensitivity.py`` and is consumed here as a frozen CSV.

Fingerprint parameters, bootstrap seed, replicate count and cohort rules are
imported from ``validation.external_prediction.benchmark_core`` rather than
redefined, so the preprint analysis cannot silently drift from the v0.10.2
benchmark it re-analyses.
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from scipy import stats

from validation.external_prediction.benchmark_core import (  # noqa: F401 - re-exported constants
    BOOTSTRAP_CONFIDENCE,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    MORGAN_NBITS,
    MORGAN_RADIUS,
    REMOTE_SIMILARITY_THRESHOLD,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_DIR = REPO_ROOT / "validation/external_prediction"
PREPRINT_RESULTS = REPO_ROOT / "preprint/results"

ASAP_PREDICTIONS = EXTERNAL_DIR / "results/asap_processed_predictions.csv"
BIOGEN_PREDICTIONS = EXTERNAL_DIR / "results/biogen_hppb_processed_predictions.csv"
ASAP_SOURCE = EXTERNAL_DIR / "source_snapshots/asap_antiviral_admet_2025_unblinded.csv"
TRAINING_DIR = EXTERNAL_DIR / "training_reference"
COMPATIBILITY = EXTERNAL_DIR / "endpoint_compatibility.csv"
HLM_LOW_CLEARANCE = PREPRINT_RESULTS / "hlm_low_clearance_predictions.csv"

ENDPOINTS = ("Clearance_Microsome_AZ", "Lipophilicity_AstraZeneca", "PPBR_AZ")
ENDPOINT_LABELS = {
    "Clearance_Microsome_AZ": "Human liver microsomal clearance",
    "Lipophilicity_AstraZeneca": "LogD (pH 7.4)",
    "PPBR_AZ": "Human plasma protein binding",
}
ENDPOINT_UNITS = {
    "Clearance_Microsome_AZ": "uL/min/mg",
    "Lipophilicity_AstraZeneca": "logD at pH 7.4",
    "PPBR_AZ": "% bound",
}
HEADLINE_COHORT = "NO_EXACT_TRAINING_OVERLAP"

# CXSMILES enhanced-stereo group markers. "a" marks an absolute assignment and
# leaves the structure unambiguous; "o" (OR) and "&" (AND) mark an unknown
# single enantiomer or a racemate, i.e. the measured sample is not the single
# drawn stereoisomer.
_AMBIGUOUS_STEREO = re.compile(r"[o&]\d*:")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_prediction_rows() -> list[dict[str, str]]:
    """Frozen v0.10.2 prediction rows for both accepted datasets."""
    return read_csv(ASAP_PREDICTIONS) + read_csv(BIOGEN_PREDICTIONS)


def load_low_clearance_rows() -> list[dict[str, str]]:
    """Preprint sensitivity rows for ASAP HLM values below the reliable bound."""
    if not HLM_LOW_CLEARANCE.is_file():
        raise FileNotFoundError(
            f"{HLM_LOW_CLEARANCE} is missing. Run preprint/analysis/hlm_low_clearance_sensitivity.py first."
        )
    return read_csv(HLM_LOW_CLEARANCE)


TRAINING_SUMMARY = PREPRINT_RESULTS / "training_reference_summary.json"

#: Number of histogram bins retained in the derived training-label summary.
#: A binned density is an aggregate statistic computed by this project; it is
#: not a redistribution of the upstream dataset.
SUMMARY_HISTOGRAM_BINS = 42


def load_derived_training_summary() -> dict[str, Any]:
    """Load the derived training-reference summary (Level 1 input).

    This file is produced by ``build_training_reference_summary.py`` from the
    upstream Therapeutics Data Commons reference tables, which are **not**
    redistributed. It carries only aggregate statistics and this project's own
    derived error metrics, never upstream structure-target pairs.
    """
    if not TRAINING_SUMMARY.is_file():
        raise FileNotFoundError(
            f"{TRAINING_SUMMARY} is missing. It is required for Level 1 reproduction and is produced by "
            "preprint/analysis/build_training_reference_summary.py (Level 2, requires the upstream tables)."
        )
    return json.loads(TRAINING_SUMMARY.read_text(encoding="utf-8"))


def training_reference_available() -> bool:
    """True when the upstream reference tables are present locally (Level 2)."""
    return all((TRAINING_DIR / f"{endpoint}.csv").is_file() for endpoint in ENDPOINTS)


def load_training_targets(endpoint: str) -> dict[str, Any]:
    """Return training-label summary and a parent-structure -> median-target map."""
    values: list[float] = []
    by_parent: dict[str, list[float]] = defaultdict(list)
    for row in read_csv(TRAINING_DIR / f"{endpoint}.csv"):
        if row["structure_parse_status"] != "PARSED":
            continue
        target = float(row["source_target"])
        values.append(target)
        by_parent[row["parent_isomeric_smiles"]].append(target)
    array = np.asarray(values, dtype=float)
    return {
        "n": len(values),
        "values": array,
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "sd": float(array.std(ddof=0)),
        "nearest_neighbour_target": {key: statistics.median(items) for key, items in by_parent.items()},
    }


def asap_stereo_ambiguity() -> dict[str, bool]:
    """Map ASAP molecule name -> whether its CXSMILES carries an OR/AND stereo group."""
    flags: dict[str, bool] = {}
    for row in read_csv(ASAP_SOURCE):
        cx = row["CXSMILES"]
        block = cx.split("|", 1)[1] if "|" in cx else ""
        flags[row["Molecule Name"]] = bool(_AMBIGUOUS_STEREO.search(block))
    return flags


def row_molecule_name(row: dict[str, str]) -> str:
    return str(row["external_row_id"]).rsplit(":", 1)[0]


def is_stereo_unambiguous(row: dict[str, str], flags: dict[str, bool]) -> bool:
    """True when the source record is not an OR/AND enhanced-stereo entry.

    Biogen rows carry a plain SMILES column with no enhanced-stereo block and
    are therefore unambiguous by construction.
    """
    if row["external_dataset_id"] != "asap-antiviral-admet-2025-unblinded":
        return True
    return not flags.get(row_molecule_name(row), False)


def successful(rows: Iterable[dict[str, str]], endpoint: str, cohort: str | None = HEADLINE_COHORT) -> list[dict[str, str]]:
    selected = [
        row
        for row in rows
        if row["prediction_endpoint"] == endpoint and row["prediction_status"] == "SUCCESS"
    ]
    if cohort is not None:
        selected = [row for row in selected if cohort in row["cohorts"]]
    return selected


def observed(rows: Sequence[dict[str, str]]) -> list[float]:
    return [float(row["ground_truth_normalized_value"]) for row in rows]


def predicted(rows: Sequence[dict[str, str]]) -> list[float]:
    return [float(row["normalized_prediction"]) for row in rows]


def regression_metrics(expected: Sequence[float], prediction: Sequence[float]) -> dict[str, Any]:
    """Point metrics including calibration slope and dispersion diagnostics.

    ``r2`` uses the evaluated cohort's own mean as the reference model, which is
    the standard coefficient-of-determination definition and the reason it is
    sensitive to label-distribution shift.
    """
    y = np.asarray(expected, dtype=float)
    p = np.asarray(prediction, dtype=float)
    if y.shape != p.shape or y.ndim != 1 or len(y) == 0:
        raise ValueError("Expected and predicted values must be aligned, one-dimensional and non-empty")
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("Metrics require finite observations")
    errors = p - y
    n = len(y)
    denominator = float(np.sum((y - y.mean()) ** 2))
    truth_sd = float(y.std(ddof=0))
    prediction_sd = float(p.std(ddof=0))
    # Constant-prediction baselines are exactly constant by construction, but
    # ``np.std`` leaves floating-point residue, so degeneracy is tested on the
    # distinct values rather than on the standard deviation.
    truth_constant = len(set(y.tolist())) < 2
    prediction_constant = len(set(p.tolist())) < 2
    calibration_slope = None
    calibration_intercept = None
    if n >= 2 and not truth_constant:
        fit = stats.linregress(y, p)
        calibration_slope = float(fit.slope)
        calibration_intercept = float(fit.intercept)
    return {
        "n": n,
        "mae": float(np.mean(np.abs(errors))),
        "median_absolute_error": float(np.median(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "r2": None if denominator == 0 else float(1 - np.sum(errors**2) / denominator),
        "pearson_r": None
        if n < 2 or truth_constant or prediction_constant
        else float(stats.pearsonr(y, p).statistic),
        "spearman_rho": None
        if n < 2 or truth_constant or prediction_constant
        else float(stats.spearmanr(y, p).statistic),
        "mean_error_bias": float(np.mean(errors)),
        "calibration_slope": calibration_slope,
        "calibration_intercept": calibration_intercept,
        "truth_sd": truth_sd,
        "prediction_sd": prediction_sd,
        "sd_ratio": None if truth_sd == 0 else float(prediction_sd / truth_sd),
    }


_BOOTSTRAP_METRICS = ("mae", "rmse", "r2", "pearson_r", "spearman_rho", "mean_error_bias", "calibration_slope", "sd_ratio")


def _quantile_summary(samples: dict[str, list[float]], point: dict[str, Any], confidence: float) -> dict[str, Any]:
    alpha = (1 - confidence) / 2
    out: dict[str, Any] = {}
    for key, values in samples.items():
        out[key] = {
            "point_estimate": point[key],
            "lower": float(np.quantile(values, alpha)) if values else None,
            "upper": float(np.quantile(values, 1 - alpha)) if values else None,
            "valid_replicates": len(values),
        }
    return out


def bootstrap_rows(
    expected: Sequence[float],
    prediction: Sequence[float],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    confidence: float = BOOTSTRAP_CONFIDENCE,
) -> dict[str, Any]:
    """Row-level percentile bootstrap, matching the v0.10.2 resampling unit."""
    y = np.asarray(expected, dtype=float)
    p = np.asarray(prediction, dtype=float)
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {key: [] for key in _BOOTSTRAP_METRICS}
    for _ in range(replicates):
        index = rng.integers(0, len(y), size=len(y))
        metrics = regression_metrics(y[index], p[index])
        for key in samples:
            value = metrics[key]
            if value is not None and math.isfinite(float(value)):
                samples[key].append(float(value))
    return {
        "resampling_unit": "external source row",
        "seed": seed,
        "replicates": replicates,
        "confidence_level": confidence,
        "intervals": _quantile_summary(samples, regression_metrics(y, p), confidence),
    }


def bootstrap_structures(
    rows: Sequence[dict[str, str]],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    confidence: float = BOOTSTRAP_CONFIDENCE,
) -> dict[str, Any]:
    """Cluster bootstrap resampling whole structures, not rows.

    ASAP contains repeated structures, so the row-level interval slightly
    overstates precision. This resamples InChIKey clusters with replacement and
    keeps every row belonging to a drawn structure.
    """
    clusters: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        clusters[row["inchikey"]].append(
            (float(row["ground_truth_normalized_value"]), float(row["normalized_prediction"]))
        )
    keys = list(clusters)
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {key: [] for key in _BOOTSTRAP_METRICS}
    for _ in range(replicates):
        index = rng.integers(0, len(keys), size=len(keys))
        y: list[float] = []
        p: list[float] = []
        for i in index:
            for observation, prediction in clusters[keys[i]]:
                y.append(observation)
                p.append(prediction)
        metrics = regression_metrics(y, p)
        for key in samples:
            value = metrics[key]
            if value is not None and math.isfinite(float(value)):
                samples[key].append(float(value))
    point = regression_metrics(observed(rows), predicted(rows))
    return {
        "resampling_unit": "unique structure (InChIKey cluster)",
        "seed": seed,
        "replicates": replicates,
        "confidence_level": confidence,
        "clusters": len(keys),
        "intervals": _quantile_summary(samples, point, confidence),
    }


def aggregate_by_structure(rows: Sequence[dict[str, str]]) -> tuple[list[float], list[float], int]:
    """Collapse repeated structures to one observation/prediction pair.

    The observation is the median of the repeated experimental values; the
    prediction is deterministic per structure, so any member's value is taken
    after asserting they agree.
    """
    clusters: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        clusters[row["inchikey"]].append(
            (float(row["ground_truth_normalized_value"]), float(row["normalized_prediction"]))
        )
    y: list[float] = []
    p: list[float] = []
    for members in clusters.values():
        predictions = {round(value, 9) for _, value in members}
        if len(predictions) != 1:
            raise ValueError("Repeated structure carries divergent predictions; refusing to aggregate silently")
        y.append(statistics.median(observation for observation, _ in members))
        p.append(members[0][1])
    return y, p, len(clusters)


def baseline_predictions(rows: Sequence[dict[str, str]], training: dict[str, Any]) -> dict[str, Any]:
    """Training-mean and 1-NN Morgan/Tanimoto baselines.

    The nearest training neighbour is taken from the frozen
    ``maximum_training_similarity_smiles`` field so the baseline uses exactly
    the neighbour the benchmark already identified. Rows whose neighbour cannot
    be resolved are reported, never silently dropped.
    """
    lookup = training["nearest_neighbour_target"]
    nearest: list[float] = []
    unresolved = 0
    for row in rows:
        key = row.get("maximum_training_similarity_smiles", "")
        if key in lookup:
            nearest.append(lookup[key])
        else:
            unresolved += 1
            nearest.append(training["median"])
    return {
        "training_mean": [training["mean"]] * len(rows),
        "training_median": [training["median"]] * len(rows),
        "nearest_neighbour": nearest,
        "nearest_neighbour_unresolved_rows": unresolved,
    }


def label_shift(training: dict[str, Any], external: Sequence[float]) -> dict[str, Any]:
    """Two-sample Kolmogorov-Smirnov comparison of training and external labels."""
    y = np.asarray(external, dtype=float)
    test = stats.ks_2samp(training["values"], y)
    return {
        "training_n": training["n"],
        "training_mean": training["mean"],
        "training_sd": training["sd"],
        "training_median": training["median"],
        "external_n": int(len(y)),
        "external_mean": float(y.mean()),
        "external_sd": float(y.std(ddof=0)),
        "external_median": float(np.median(y)),
        "ks_statistic": float(test.statistic),
        "ks_p_value": float(test.pvalue),
        "test": "two-sample Kolmogorov-Smirnov on endpoint label values",
        "interpretation": "Describes label-distribution difference between reconstructed training labels and external labels. It is not a causal statement.",
    }


def similarity_error_association(rows: Sequence[dict[str, str]]) -> dict[str, Any]:
    """Spearman association between maximum training similarity and absolute error."""
    usable = [row for row in rows if row.get("maximum_training_similarity") not in (None, "")]
    if len(usable) < 3:
        return {"n": len(usable), "spearman_rho": None, "p_value": None}
    similarity = np.asarray([float(row["maximum_training_similarity"]) for row in usable], dtype=float)
    error = np.abs(np.asarray(predicted(usable), dtype=float) - np.asarray(observed(usable), dtype=float))
    result = stats.spearmanr(similarity, error)
    return {
        "n": len(usable),
        "median_maximum_similarity": float(np.median(similarity)),
        "spearman_rho": float(result.statistic),
        "p_value": float(result.pvalue),
        "interpretation": "Descriptive association only; it does not establish an applicability domain.",
    }


# ---------------------------------------------------------------------------
# Cohort selection shared by the summary builder (Level 2) and the analysis
# (Level 1). Defined once so the two stages cannot drift apart.
# ---------------------------------------------------------------------------

#: Cohorts whose reported blocks depend on the upstream training reference
#: (baselines and label-distribution shift). Everything else is computed from
#: the redistributable prediction rows alone.
TRAINING_DEPENDENT_COHORTS = ("A_HEADLINE", "B_HEADLINE_PLUS_LOW_CLEARANCE", "D_STEREO_UNAMBIGUOUS")


def select_cohort_rows(
    rows: Sequence[dict[str, str]],
    low_clearance_rows: Sequence[dict[str, str]],
    stereo_flags: dict[str, bool],
) -> dict[tuple[str, str], list[dict[str, str]]]:
    """Return the row set for every (endpoint, cohort) pair used in the paper."""
    selected: dict[tuple[str, str], list[dict[str, str]]] = {}
    for endpoint in ENDPOINTS:
        headline = successful(rows, endpoint, HEADLINE_COHORT)
        selected[(endpoint, "A_HEADLINE")] = headline
        selected[(endpoint, "C_STRUCTURE_AGGREGATED")] = headline
        selected[(endpoint, "D_STEREO_UNAMBIGUOUS")] = [
            row for row in headline if is_stereo_unambiguous(row, stereo_flags)
        ]
        for frozen in ("ALL_COMPATIBLE_DATA", "NO_PARENT_FORM_TRAINING_OVERLAP", "STRUCTURALLY_REMOTE_SUBSET"):
            selected[(endpoint, frozen)] = successful(rows, endpoint, frozen)
        if endpoint == "Clearance_Microsome_AZ":
            extra = [
                row
                for row in low_clearance_rows
                if row["prediction_status"] == "SUCCESS" and HEADLINE_COHORT in row["cohorts"]
            ]
            selected[(endpoint, "B_HEADLINE_PLUS_LOW_CLEARANCE")] = headline + extra
    return selected
