"""Single reproducible entry point for the external-validation preprint.

Regenerates every number used in the manuscript, tables and figures from
committed artefacts only. Deterministic, offline, and non-destructive: it never
writes to ``validation/`` or ``docs/``.

    PYTHONPATH=backend python preprint/analysis/run_preprint_analysis.py

Outputs (all under ``preprint/results/``):

    preprint_analysis.json     machine-readable results for every cohort
    table1_compatibility.csv   semantic compatibility matrix (12 pairings)
    table2_external_results.csv  main external-validation results table
    supplementary_sensitivity.csv  all sensitivity cohorts, long format
    analysis_summary.md        human-readable summary
    analysis_manifest.json     input and output hashes

The reproduction gate is hard: if any headline v0.10.2 metric fails to
reproduce from the frozen prediction rows, the run aborts without writing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
for candidate in (str(REPO_ROOT), str(BACKEND_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from preprint.analysis import core  # noqa: E402

RESULTS = REPO_ROOT / "preprint/results"
TABLES = REPO_ROOT / "preprint/tables"
V0102_METRICS = REPO_ROOT / "validation/reports/v0102_external_metrics.json"
FROZEN_MANIFEST = RESULTS / "frozen_input_manifest.json"

ANALYSIS_ID = "preprint-v1.0-external-validation-analysis"
REPRODUCTION_TOLERANCE = 1e-9

COHORT_DEFINITIONS = {
    "A_HEADLINE": (
        "Frozen v0.10.2 headline cohort: semantically compatible rows with a valid exact "
        "experimental value, excluding exact structure overlap with the endpoint training "
        "source and with any reconstructed regression multitask source."
    ),
    "B_HEADLINE_PLUS_LOW_CLEARANCE": (
        "Cohort A plus the ASAP human liver microsomal rows whose experimental value falls "
        "below the source's documented reliable exact bound of 10 uL/min/mg. These rows were "
        "excluded before inference in v0.10.2 and are predicted here by the same adapter and "
        "package version. HLM only."
    ),
    "C_STRUCTURE_AGGREGATED": (
        "Cohort A collapsed to one record per unique InChIKey. The experimental value is the "
        "median of repeated measurements; the prediction is deterministic per structure."
    ),
    "D_STEREO_UNAMBIGUOUS": (
        "Cohort A restricted to source records whose structure is not an OR/AND enhanced-stereo "
        "CXSMILES entry, i.e. excluding racemates and unknown single enantiomers that cannot be "
        "represented as the single drawn stereoisomer carried through the modelling path."
    ),
    "ALL_COMPATIBLE_DATA": (
        "Frozen v0.10.2 transparency cohort including rows with known training exposure. "
        "Reported for completeness and never used as an external-generalisation claim."
    ),
    "NO_PARENT_FORM_TRAINING_OVERLAP": "Frozen v0.10.2 cohort additionally excluding parent and salt-form training overlap.",
    "STRUCTURALLY_REMOTE_SUBSET": (
        "Frozen v0.10.2 cohort additionally requiring no stereo relation, an unseen Murcko "
        f"scaffold and maximum Morgan/Tanimoto similarity below {core.REMOTE_SIMILARITY_THRESHOLD:.2f}."
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


#: Inputs recorded in the frozen manifest that are deliberately not
#: redistributed (DATA_LICENSES.md section 3). Level 1 must run without them, so
#: their absence is expected rather than an error. Their hashes remain pinned in
#: preprint/results/training_reference_summary.json for Level 2 verification.
NON_REDISTRIBUTED_PREFIX = "validation/external_prediction/training_reference/"


def verify_frozen_inputs() -> dict[str, Any]:
    """Confirm every frozen input still hashes to the value recorded at branch creation.

    Inputs inside the redistribution boundary are skipped when absent and
    verified when present, so the same check serves a Level 1 clean clone and a
    Level 2 working copy. Any other missing input is a hard error.
    """
    manifest = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    mismatches: list[dict[str, Any]] = []
    missing: list[str] = []
    skipped: list[str] = []
    for relative, expected in manifest["inputs"].items():
        path = REPO_ROOT / relative
        if not path.is_file():
            if relative.startswith(NON_REDISTRIBUTED_PREFIX):
                skipped.append(relative)
            else:
                missing.append(relative)
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append({"file": relative, "expected": expected, "actual": actual})
    if missing:
        raise SystemExit(
            "Frozen inputs are missing and are not covered by the redistribution boundary. "
            "Refusing to run.\n" + json.dumps(missing, indent=2)
        )
    if mismatches:
        raise SystemExit(
            "Frozen inputs changed since the preprint branch was created. Refusing to run.\n"
            + json.dumps(mismatches, indent=2)
        )
    manifest["verified_inputs"] = len(manifest["inputs"]) - len(skipped)
    manifest["skipped_not_redistributed"] = sorted(skipped)
    return manifest


def reproduce_headline(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Hard gate: recompute frozen v0.10.2 metrics and compare field by field."""
    published = json.loads(V0102_METRICS.read_text(encoding="utf-8"))["endpoints"]
    checked: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    for endpoint in core.ENDPOINTS:
        for cohort in ("ALL_COMPATIBLE_DATA", "NO_EXACT_TRAINING_OVERLAP", "NO_PARENT_FORM_TRAINING_OVERLAP", "STRUCTURALLY_REMOTE_SUBSET"):
            selected = core.successful(rows, endpoint, cohort)
            recomputed = core.regression_metrics(core.observed(selected), core.predicted(selected))
            reference = published[endpoint]["cohorts"][cohort]["metrics"]
            for key in ("n", "mae", "median_absolute_error", "rmse", "r2", "pearson_r", "spearman_rho", "mean_error_bias"):
                expected = reference[key]
                actual = recomputed[key]
                if expected is None and actual is None:
                    continue
                if expected is None or actual is None or abs(float(expected) - float(actual)) > REPRODUCTION_TOLERANCE:
                    failures.append(
                        {"endpoint": endpoint, "cohort": cohort, "metric": key, "published": expected, "recomputed": actual}
                    )
            checked[f"{endpoint}::{cohort}"] = {"n": recomputed["n"], "status": "REPRODUCED"}
    if failures:
        raise SystemExit(
            "STOP: recomputed metrics differ from the published v0.10.2 values. "
            "No output was written and no historical file was touched.\n" + json.dumps(failures, indent=2)
        )
    return {
        "status": "ALL_PUBLISHED_METRICS_REPRODUCED",
        "tolerance": REPRODUCTION_TOLERANCE,
        "source": V0102_METRICS.relative_to(REPO_ROOT).as_posix(),
        "checks": checked,
    }


def cohort_block(
    rows: list[dict[str, str]],
    derived: dict[str, Any] | None,
    *,
    aggregate: bool = False,
    cluster_bootstrap: bool = True,
) -> dict[str, Any]:
    """Assemble one cohort block.

    ``derived`` supplies the two quantities that depend on the upstream
    training reference — the baselines and the label-shift statistic — read
    from the derived summary rather than recomputed, so that this stage runs
    without the non-redistributed upstream tables.
    """
    if aggregate:
        y, p, clusters = core.aggregate_by_structure(rows)
        block: dict[str, Any] = {
            "n": len(y),
            "unique_structures": clusters,
            "metrics": core.regression_metrics(y, p),
            "bootstrap_rows": core.bootstrap_rows(y, p),
        }
        return block
    y = core.observed(rows)
    p = core.predicted(rows)
    if derived is None:
        raise ValueError("A training-derived block is required for a non-aggregated cohort")
    if derived["n"] != len(rows):
        raise ValueError(
            f"Derived summary covers {derived['n']} rows but this cohort has {len(rows)}; "
            "rebuild preprint/results/training_reference_summary.json"
        )
    block = {
        "n": len(rows),
        "unique_structures": len({row["inchikey"] for row in rows}),
        "metrics": core.regression_metrics(y, p),
        "bootstrap_rows": core.bootstrap_rows(y, p),
        "baselines": derived["baselines"],
        "label_shift": derived["label_shift"],
        "similarity_error_association": core.similarity_error_association(rows),
    }
    if cluster_bootstrap:
        block["bootstrap_structures"] = core.bootstrap_structures(rows)
    return block


def build_results(
    rows: list[dict[str, str]],
    low_clearance: list[dict[str, str]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    stereo_flags = core.asap_stereo_ambiguity()
    cohorts = core.select_cohort_rows(rows, low_clearance, stereo_flags)
    results: dict[str, Any] = {}
    for endpoint in core.ENDPOINTS:
        derived_endpoint = summary["endpoints"][endpoint]
        derived_cohorts = derived_endpoint["cohorts"]
        headline = cohorts[(endpoint, "A_HEADLINE")]
        endpoint_block: dict[str, Any] = {
            "label": core.ENDPOINT_LABELS[endpoint],
            "evaluation_scale": core.ENDPOINT_UNITS[endpoint],
            "training_labels": derived_endpoint["training_labels"],
            "source_row_counts": _source_counts(rows, endpoint),
            "cohorts": {},
        }
        endpoint_block["cohorts"]["A_HEADLINE"] = cohort_block(headline, derived_cohorts["A_HEADLINE"])

        for frozen in ("ALL_COMPATIBLE_DATA", "NO_PARENT_FORM_TRAINING_OVERLAP", "STRUCTURALLY_REMOTE_SUBSET"):
            selected = cohorts[(endpoint, frozen)]
            if selected:
                endpoint_block["cohorts"][frozen] = {
                    "n": len(selected),
                    "unique_structures": len({row["inchikey"] for row in selected}),
                    "metrics": core.regression_metrics(core.observed(selected), core.predicted(selected)),
                }

        endpoint_block["cohorts"]["C_STRUCTURE_AGGREGATED"] = cohort_block(headline, None, aggregate=True)

        unambiguous = cohorts[(endpoint, "D_STEREO_UNAMBIGUOUS")]
        endpoint_block["cohorts"]["D_STEREO_UNAMBIGUOUS"] = {
            **cohort_block(unambiguous, derived_cohorts["D_STEREO_UNAMBIGUOUS"], cluster_bootstrap=False),
            "rows_excluded_as_ambiguous": len(headline) - len(unambiguous),
        }

        if endpoint == "Clearance_Microsome_AZ":
            combined = cohorts[(endpoint, "B_HEADLINE_PLUS_LOW_CLEARANCE")]
            successful_low = [r for r in low_clearance if r["prediction_status"] == "SUCCESS"]
            endpoint_block["cohorts"]["B_HEADLINE_PLUS_LOW_CLEARANCE"] = {
                **cohort_block(combined, derived_cohorts["B_HEADLINE_PLUS_LOW_CLEARANCE"]),
                "rows_added": len(combined) - len(headline),
                "rows_available_below_bound": len(successful_low),
                "rows_below_bound_with_exact_training_overlap": len(
                    [r for r in successful_low if core.HEADLINE_COHORT not in r["cohorts"]]
                ),
            }
        results[endpoint] = endpoint_block
    return results


def _source_counts(rows: list[dict[str, str]], endpoint: str) -> dict[str, int]:
    subset = [row for row in rows if row["prediction_endpoint"] == endpoint]
    counts: dict[str, int] = {"source_rows": len(subset)}
    for status in sorted({row["ground_truth_status"] for row in subset}):
        counts[status.lower()] = sum(1 for row in subset if row["ground_truth_status"] == status)
    return counts


def write_table1(path: Path) -> None:
    fields = [
        "mapping_id",
        "external_dataset_id",
        "external_endpoint",
        "admet_ai_output_name",
        "same_species",
        "same_matrix",
        "same_assay_family",
        "same_result_semantics",
        "units_compatible",
        "same_transformation",
        "transformation",
        "decision",
        "numerical_validation_allowed",
        "reason",
    ]
    source = core.read_csv(core.COMPATIBILITY)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in source:
            writer.writerow({field: row.get(field, "") for field in fields})


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_table2(path: Path, results: dict[str, Any]) -> None:
    fields = [
        "endpoint", "label", "evaluation_scale", "source_rows", "usable_rows", "headline_n", "unique_structures",
        "excluded_missing", "excluded_other", "exact_overlap_excluded",
        "mae", "mae_ci_low", "mae_ci_high", "median_absolute_error", "rmse",
        "r2", "r2_ci_low", "r2_ci_high", "pearson_r", "spearman_rho", "spearman_ci_low", "spearman_ci_high",
        "mean_error_bias", "bias_ci_low", "bias_ci_high", "calibration_slope", "calibration_slope_ci_low",
        "calibration_slope_ci_high", "truth_sd", "prediction_sd", "sd_ratio",
        "baseline_training_mean_mae", "baseline_training_mean_r2",
        "baseline_1nn_morgan_mae", "baseline_1nn_morgan_r2",
        "label_shift_ks_d", "label_shift_ks_p",
    ]
    rows_out = []
    for endpoint, block in results.items():
        cohort = block["cohorts"]["A_HEADLINE"]
        metrics = cohort["metrics"]
        intervals = cohort["bootstrap_rows"]["intervals"]
        counts = block["source_row_counts"]
        usable = counts.get("valid_exact", 0)
        all_compatible = block["cohorts"].get("ALL_COMPATIBLE_DATA", {}).get("n", usable)
        rows_out.append(
            {
                "endpoint": endpoint,
                "label": block["label"],
                "evaluation_scale": block["evaluation_scale"],
                "source_rows": counts["source_rows"],
                "usable_rows": usable,
                "headline_n": metrics["n"],
                "unique_structures": cohort["unique_structures"],
                "excluded_missing": counts.get("excluded_missing", 0),
                "excluded_other": counts.get("excluded_censoring_or_bound", 0) + counts.get("excluded_invalid_transform", 0),
                "exact_overlap_excluded": all_compatible - metrics["n"],
                "mae": _fmt(metrics["mae"]),
                "mae_ci_low": _fmt(intervals["mae"]["lower"]),
                "mae_ci_high": _fmt(intervals["mae"]["upper"]),
                "median_absolute_error": _fmt(metrics["median_absolute_error"]),
                "rmse": _fmt(metrics["rmse"]),
                "r2": _fmt(metrics["r2"]),
                "r2_ci_low": _fmt(intervals["r2"]["lower"]),
                "r2_ci_high": _fmt(intervals["r2"]["upper"]),
                "pearson_r": _fmt(metrics["pearson_r"]),
                "spearman_rho": _fmt(metrics["spearman_rho"]),
                "spearman_ci_low": _fmt(intervals["spearman_rho"]["lower"]),
                "spearman_ci_high": _fmt(intervals["spearman_rho"]["upper"]),
                "mean_error_bias": _fmt(metrics["mean_error_bias"]),
                "bias_ci_low": _fmt(intervals["mean_error_bias"]["lower"]),
                "bias_ci_high": _fmt(intervals["mean_error_bias"]["upper"]),
                "calibration_slope": _fmt(metrics["calibration_slope"]),
                "calibration_slope_ci_low": _fmt(intervals["calibration_slope"]["lower"]),
                "calibration_slope_ci_high": _fmt(intervals["calibration_slope"]["upper"]),
                "truth_sd": _fmt(metrics["truth_sd"]),
                "prediction_sd": _fmt(metrics["prediction_sd"]),
                "sd_ratio": _fmt(metrics["sd_ratio"]),
                "baseline_training_mean_mae": _fmt(cohort["baselines"]["training_mean"]["mae"]),
                "baseline_training_mean_r2": _fmt(cohort["baselines"]["training_mean"]["r2"]),
                "baseline_1nn_morgan_mae": _fmt(cohort["baselines"]["nearest_neighbour_morgan_tanimoto"]["mae"]),
                "baseline_1nn_morgan_r2": _fmt(cohort["baselines"]["nearest_neighbour_morgan_tanimoto"]["r2"]),
                "label_shift_ks_d": _fmt(cohort["label_shift"]["ks_statistic"]),
                "label_shift_ks_p": f"{cohort['label_shift']['ks_p_value']:.3e}",
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_out)


def write_supplementary(path: Path, results: dict[str, Any]) -> None:
    fields = [
        "endpoint", "cohort", "cohort_definition", "n", "unique_structures", "mae", "median_absolute_error",
        "rmse", "r2", "pearson_r", "spearman_rho", "mean_error_bias", "calibration_slope",
        "truth_sd", "prediction_sd", "sd_ratio",
    ]
    rows_out = []
    for endpoint, block in results.items():
        for cohort, payload in block["cohorts"].items():
            metrics = payload["metrics"]
            rows_out.append(
                {
                    "endpoint": endpoint,
                    "cohort": cohort,
                    "cohort_definition": COHORT_DEFINITIONS.get(cohort, ""),
                    "n": metrics["n"],
                    "unique_structures": payload.get("unique_structures", ""),
                    **{key: _fmt(metrics[key]) for key in (
                        "mae", "median_absolute_error", "rmse", "r2", "pearson_r", "spearman_rho",
                        "mean_error_bias", "calibration_slope", "truth_sd", "prediction_sd", "sd_ratio")},
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_out)


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# External-validation preprint — analysis summary",
        "",
        f"Analysis id: `{payload['analysis_id']}`",
        f"Reproduction gate: **{payload['reproduction']['status']}**",
        "",
        "All numbers below are regenerated from committed artefacts by",
        "`preprint/analysis/run_preprint_analysis.py`. No value in `validation/` or `docs/` is modified.",
        "",
        "## Compatibility screening",
        "",
        f"- Candidate dataset-to-output pairings: {payload['compatibility']['candidates']}",
        f"- Accepted for numerical evaluation: {payload['compatibility']['accepted']}",
        f"- Rejected or not evaluable: {payload['compatibility']['rejected']}",
        "",
        "## Headline cohort (A)",
        "",
        "| Endpoint | n | structures | MAE | R2 | Spearman | bias | slope | SD ratio |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for endpoint, block in payload["results"].items():
        metrics = block["cohorts"]["A_HEADLINE"]["metrics"]
        lines.append(
            f"| {block['label']} | {metrics['n']} | {block['cohorts']['A_HEADLINE']['unique_structures']} | "
            f"{metrics['mae']:.3f} | {metrics['r2']:+.3f} | {metrics['spearman_rho']:+.3f} | "
            f"{metrics['mean_error_bias']:+.3f} | {metrics['calibration_slope']:.3f} | {metrics['sd_ratio']:.3f} |"
        )
    lines += ["", "## Baseline-relative performance (cohort A)", "",
              "| Endpoint | ADMET-AI MAE | training-mean MAE | 1-NN MAE | ADMET-AI R2 | training-mean R2 | 1-NN R2 |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for endpoint, block in payload["results"].items():
        cohort = block["cohorts"]["A_HEADLINE"]
        model = cohort["metrics"]
        mean = cohort["baselines"]["training_mean"]
        nn = cohort["baselines"]["nearest_neighbour_morgan_tanimoto"]
        lines.append(
            f"| {block['label']} | {model['mae']:.3f} | {mean['mae']:.3f} | {nn['mae']:.3f} | "
            f"{model['r2']:+.3f} | {mean['r2']:+.3f} | {nn['r2']:+.3f} |"
        )
    lines += ["", "## Label-distribution shift (cohort A)", "",
              "| Endpoint | training mean +/- SD | external mean +/- SD | KS D | KS p |",
              "| --- | --- | --- | ---: | ---: |"]
    for endpoint, block in payload["results"].items():
        shift = block["cohorts"]["A_HEADLINE"]["label_shift"]
        lines.append(
            f"| {block['label']} | {shift['training_mean']:.2f} +/- {shift['training_sd']:.2f} | "
            f"{shift['external_mean']:.2f} +/- {shift['external_sd']:.2f} | "
            f"{shift['ks_statistic']:.3f} | {shift['ks_p_value']:.2e} |"
        )
    hlm = payload["results"]["Clearance_Microsome_AZ"]["cohorts"]
    lines += ["", "## HLM range-restriction sensitivity (cohort B)", "",
              "| Cohort | n | MAE | R2 | Spearman | bias | slope | SD ratio |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name in ("A_HEADLINE", "B_HEADLINE_PLUS_LOW_CLEARANCE", "C_STRUCTURE_AGGREGATED", "D_STEREO_UNAMBIGUOUS"):
        metrics = hlm[name]["metrics"]
        lines.append(
            f"| {name} | {metrics['n']} | {metrics['mae']:.3f} | {metrics['r2']:+.3f} | "
            f"{metrics['spearman_rho']:+.3f} | {metrics['mean_error_bias']:+.3f} | "
            f"{metrics['calibration_slope']:.3f} | {metrics['sd_ratio']:.3f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-input-verification", action="store_true", help="for development only")
    args = parser.parse_args(argv)

    frozen = None if args.skip_input_verification else verify_frozen_inputs()

    rows = core.load_prediction_rows()
    reproduction = reproduce_headline(rows)

    # Structural overlap annotation for the sensitivity rows is derived from the
    # upstream training reference, which is not redistributed, so it is read
    # from the derived summary rather than recomputed here.
    summary = core.load_derived_training_summary()
    low_clearance = core.load_low_clearance_rows()
    annotation = summary["low_clearance_annotation"]
    for row in low_clearance:
        row.update(annotation[row["external_row_id"]])

    compatibility = core.read_csv(core.COMPATIBILITY)
    accepted = [row for row in compatibility if row["numerical_validation_allowed"].lower() == "true"]
    results = build_results(rows, low_clearance, summary)

    payload = {
        "analysis_id": ANALYSIS_ID,
        "schema_version": 1,
        "determinism": {
            "bootstrap_seed": core.BOOTSTRAP_SEED,
            "bootstrap_replicates": core.BOOTSTRAP_REPLICATES,
            "confidence_level": core.BOOTSTRAP_CONFIDENCE,
            "fingerprint": {"type": "Morgan", "radius": core.MORGAN_RADIUS, "n_bits": core.MORGAN_NBITS, "similarity": "Tanimoto"},
            "network_access_required": False,
            "model_inference_in_this_script": False,
        },
        "inputs": {
            "level": 1,
            "description": (
                "Reproduced from redistributable committed artefacts only: the frozen prediction rows, the "
                "low-clearance sensitivity predictions, the compatibility matrix, and the derived "
                "training-reference summary. The upstream Therapeutics Data Commons reference tables are "
                "not required and are not redistributed; see DATA_LICENSES.md."
            ),
            "training_reference_summary": core.TRAINING_SUMMARY.relative_to(REPO_ROOT).as_posix(),
            "training_reference_summary_sha256": sha256_file(core.TRAINING_SUMMARY),
            "upstream_training_tables_present_locally": core.training_reference_available(),
            "frozen_inputs_verified": (frozen or {}).get("verified_inputs"),
            "frozen_inputs_absent_by_policy": (frozen or {}).get("skipped_not_redistributed", []),
        },
        "reproduction": reproduction,
        "cohort_definitions": COHORT_DEFINITIONS,
        "compatibility": {
            "candidates": len(compatibility),
            "accepted": len(accepted),
            "rejected": len(compatibility) - len(accepted),
            "accepted_mapping_ids": [row["mapping_id"] for row in accepted],
            "decision_counts": {
                decision: sum(1 for row in compatibility if row["decision"] == decision)
                for decision in sorted({row["decision"] for row in compatibility})
            },
            "status": "PRE_SPECIFIED_EXPLICIT_AUDITABLE_FAIL_CLOSED; not externally validated",
        },
        "results": results,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    analysis_path = RESULTS / "preprint_analysis.json"
    analysis_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_table1(TABLES / "table1_compatibility.csv")
    write_table2(TABLES / "table2_external_results.csv", results)
    write_supplementary(TABLES / "supplementary_sensitivity.csv", results)
    write_summary(RESULTS / "analysis_summary.md", payload)

    outputs = [
        analysis_path,
        TABLES / "table1_compatibility.csv",
        TABLES / "table2_external_results.csv",
        TABLES / "supplementary_sensitivity.csv",
        RESULTS / "analysis_summary.md",
    ]
    manifest = {
        "artifact_id": f"{ANALYSIS_ID}-manifest",
        "frozen_inputs_verified": frozen is not None,
        "inputs": (frozen or {}).get("inputs", {}),
        "new_model_artifact": {
            "path": core.HLM_LOW_CLEARANCE.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(core.HLM_LOW_CLEARANCE),
        },
        "outputs": {path.relative_to(REPO_ROOT).as_posix(): sha256_file(path) for path in outputs},
    }
    (RESULTS / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    absent = (frozen or {}).get("skipped_not_redistributed", [])
    print(f"frozen inputs         : {(frozen or {}).get('verified_inputs', 0)} verified"
          + (f", {len(absent)} absent by redistribution policy" if absent else ""))
    print(f"reproduction gate     : {reproduction['status']}")
    print(f"compatibility         : {payload['compatibility']['accepted']}/{payload['compatibility']['candidates']} accepted")
    for endpoint, block in results.items():
        metrics = block["cohorts"]["A_HEADLINE"]["metrics"]
        print(
            f"  {endpoint:26s} n={metrics['n']:4d} MAE={metrics['mae']:8.3f} R2={metrics['r2']:+.3f} "
            f"rho={metrics['spearman_rho']:+.3f} slope={metrics['calibration_slope']:.3f} sd_ratio={metrics['sd_ratio']:.3f}"
        )
    for path in outputs:
        print(f"wrote {path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
