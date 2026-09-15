"""Run v0.10.2 external ADMET validation through the production adapter."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.prediction.admet_ai_provider import AdmetAiProvider
from validation.external_prediction.benchmark_core import (
    BOOTSTRAP_CONFIDENCE,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    MORGAN_NBITS,
    MORGAN_RADIUS,
    REMOTE_SIMILARITY_THRESHOLD,
    bootstrap_intervals,
    chemical_neighborhood,
    cohort_memberships,
    combine_training_indexes,
    identity_overlap,
    load_training_index,
    regression_metrics,
)
from validation.external_prediction.benchmark_data import (
    normalize_prediction,
    prepare_accepted_rows,
    select_adapter_prediction,
)
from validation.external_prediction.compatibility import load_compatibility
from validation.external_prediction.training_reference import sha256_file, structure_identifiers


MODEL_RUN_ID = "V0102-EXTERNAL-20260828-ADMETAI-2.0.1"
ENDPOINT_TO_INDEX = {
    "Clearance_Microsome_AZ": "Clearance_Microsome_AZ.csv",
    "Lipophilicity_AstraZeneca": "Lipophilicity_AstraZeneca.csv",
    "PPBR_AZ": "PPBR_AZ.csv",
    "Caco2_Wang": "Caco2_Wang.csv",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: ";".join(value) if isinstance(value, (tuple, list)) else value
                    for key, value in row.items()
                }
            )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_indexes(training_dir: Path) -> tuple[dict[str, Any], Any]:
    all_indexes = {
        path.stem: load_training_index(path)
        for path in sorted(training_dir.glob("*.csv"))
    }
    selected = {endpoint: all_indexes[Path(filename).stem] for endpoint, filename in ENDPOINT_TO_INDEX.items()}
    return selected, combine_training_indexes(all_indexes.values())


def annotate_overlap(rows: list[dict[str, Any]], endpoint_indexes: dict[str, Any], multitask_index: Any) -> list[dict[str, Any]]:
    for row in rows:
        row.update(
            {
                "model_run_id": MODEL_RUN_ID,
                "provider": "admet_ai",
                "package_version": "2.0.1",
                "adapter_version": "v2",
                "raw_prediction": None,
                "normalized_prediction": None,
                "prediction_status": "NOT_RUN_GROUND_TRUTH_EXCLUDED",
            }
        )
        if row["ground_truth_status"] != "VALID_EXACT" or row["structure_parse_status"] != "PARSED":
            row.update(
                {
                    "endpoint_training_identity_status": "NOT_EVALUATED",
                    "multitask_training_identity_status": "NOT_EVALUATED",
                    "scaffold_status": "NOT_EVALUATED",
                    "maximum_training_similarity": None,
                    "maximum_training_similarity_smiles": "",
                    "similarity_bin": "NOT_EVALUATED",
                    "cohorts": (),
                }
            )
            continue
        endpoint_index = endpoint_indexes[row["prediction_endpoint"]]
        endpoint_identity = identity_overlap(row["original_smiles"], endpoint_index)
        multitask_identity = identity_overlap(row["original_smiles"], multitask_index)
        neighborhood = chemical_neighborhood(row["original_smiles"], endpoint_index)
        row.update(
            {
                "endpoint_training_identity_status": endpoint_identity["identity_status"],
                "multitask_training_identity_status": multitask_identity["identity_status"],
                **neighborhood,
            }
        )
        row["cohorts"] = cohort_memberships(row)
        row["prediction_status"] = "READY"
    return rows


def run_adapter_predictions(rows: list[dict[str, Any]], provider: Any, batch_size: int = 256) -> None:
    unique_smiles = list(
        dict.fromkeys(
            row["isomeric_smiles"]
            for row in rows
            if row["prediction_status"] == "READY"
        )
    )
    predictions: dict[str, list[dict[str, Any]]] = {}
    for start in range(0, len(unique_smiles), batch_size):
        batch = unique_smiles[start : start + batch_size]
        batch_records = provider.predict_smiles_batch(batch)
        if len(batch_records) != len(batch):
            raise ValueError("Production adapter returned an unaligned prediction batch")
        predictions.update(zip(batch, batch_records))

    package_version = getattr(provider, "package_version", None) or "UNKNOWN"
    adapter_version = getattr(provider, "version", None) or "UNKNOWN"
    for row in rows:
        row["package_version"] = package_version
        row["adapter_version"] = adapter_version
        if row["prediction_status"] != "READY":
            continue
        selected = select_adapter_prediction(predictions[row["isomeric_smiles"]], row["prediction_endpoint"])
        raw_prediction = float(selected["normalized_prediction"])
        row["raw_prediction"] = raw_prediction
        row["normalized_prediction"] = normalize_prediction(row, raw_prediction)
        row["prediction_status"] = "SUCCESS"


def metric_rows_for_cohort(rows: Iterable[dict[str, Any]], endpoint: str, cohort: str) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row["prediction_endpoint"] == endpoint
        and row["prediction_status"] == "SUCCESS"
        and cohort in row["cohorts"]
    ]


def _metrics_for_rows(rows: list[dict[str, Any]], include_bootstrap: bool = True) -> dict[str, Any]:
    expected = [float(row["ground_truth_normalized_value"]) for row in rows]
    predicted = [float(row["normalized_prediction"]) for row in rows]
    result: dict[str, Any] = {"metrics": regression_metrics(expected, predicted)}
    result["bootstrap"] = (
        bootstrap_intervals(expected, predicted)
        if include_bootstrap and len(rows) >= 20
        else {
            "status": "NOT_CALCULATED_N_BELOW_20",
            "n": len(rows),
        }
    )
    return result


def build_metric_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    endpoints = sorted({row["prediction_endpoint"] for row in rows if row["prediction_status"] == "SUCCESS"})
    report: dict[str, Any] = {
        "schema_version": "v0.10.2-external-metrics-1",
        "model_run_id": MODEL_RUN_ID,
        "bootstrap": {
            "seed": BOOTSTRAP_SEED,
            "replicates": BOOTSTRAP_REPLICATES,
            "confidence_level": BOOTSTRAP_CONFIDENCE,
            "resampling_unit": "external source row",
            "interpretation": "Aggregate benchmark interval; not per-molecule prediction uncertainty",
        },
        "endpoints": {},
    }
    cohorts = (
        "ALL_COMPATIBLE_DATA",
        "NO_EXACT_TRAINING_OVERLAP",
        "NO_PARENT_FORM_TRAINING_OVERLAP",
        "STRUCTURALLY_REMOTE_SUBSET",
    )
    for endpoint in endpoints:
        endpoint_rows = [row for row in rows if row["prediction_endpoint"] == endpoint and row["prediction_status"] == "SUCCESS"]
        endpoint_report = {
            "evaluation_scale": endpoint_rows[0]["ground_truth_normalized_unit"],
            "cohorts": {},
            "special_views": {},
        }
        for cohort in cohorts:
            selected = metric_rows_for_cohort(rows, endpoint, cohort)
            endpoint_report["cohorts"][cohort] = _metrics_for_rows(selected) if selected else {"metrics": {"n": 0}, "bootstrap": {"status": "NOT_CALCULATED_EMPTY_COHORT"}}
        if endpoint in {"Clearance_Microsome_AZ", "Lipophilicity_AstraZeneca"}:
            nonoverlap = metric_rows_for_cohort(rows, endpoint, "NO_EXACT_TRAINING_OVERLAP")
            endpoint_report["special_views"]["ASAP_ALL_NONOVERLAP"] = _metrics_for_rows(nonoverlap) if nonoverlap else {"metrics": {"n": 0}}
            original_test = [row for row in nonoverlap if row["source_partition"] == "TEST"]
            endpoint_report["special_views"]["ASAP_ORIGINAL_TEST_NONOVERLAP"] = _metrics_for_rows(original_test) if original_test else {"metrics": {"n": 0}}
        report["endpoints"][endpoint] = endpoint_report
    return report


def build_stratification(rows: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "analysis_name": "EMPIRICAL_GENERALIZATION_STRATIFICATION",
        "causal_interpretation": False,
        "applicability_domain_interpretation": False,
        "endpoints": {},
    }
    for endpoint in sorted({row["prediction_endpoint"] for row in rows if row["prediction_status"] == "SUCCESS"}):
        base = metric_rows_for_cohort(rows, endpoint, "NO_EXACT_TRAINING_OVERLAP")
        endpoint_report: dict[str, Any] = {"similarity_bins": {}, "scaffold_status": {}}
        for field, groups in (
            ("similarity_bins", ["<0.40", "0.40-<0.60", "0.60-<0.80", "0.80-<0.90", ">=0.90"]),
            ("scaffold_status", ["SEEN_SCAFFOLD", "UNSEEN_SCAFFOLD"]),
        ):
            source_field = "similarity_bin" if field == "similarity_bins" else "scaffold_status"
            for group in groups:
                selected = [row for row in base if row[source_field] == group]
                endpoint_report[field][group] = _metrics_for_rows(selected, include_bootstrap=False)["metrics"] if selected else {"n": 0}
        report["endpoints"][endpoint] = endpoint_report
    return report


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    similarities = [float(row["maximum_training_similarity"]) for row in rows if row.get("maximum_training_similarity") is not None]
    return {
        "external_n": len(rows),
        "exact_endpoint_training_overlap_n": sum(row.get("endpoint_training_identity_status") == "EXACT_STRUCTURE_OVERLAP" for row in rows),
        "exact_multitask_structure_exposure_n": sum(row.get("multitask_training_identity_status") == "EXACT_STRUCTURE_OVERLAP" for row in rows),
        "parent_or_salt_endpoint_overlap_n": sum(row.get("endpoint_training_identity_status") in {"PARENT_FORM_OVERLAP", "SALT_FORM_OVERLAP"} for row in rows),
        "stereo_related_endpoint_n": sum(row.get("endpoint_training_identity_status") == "STEREO_RELATED" for row in rows),
        "seen_scaffold_n": sum(row.get("scaffold_status") == "SEEN_SCAFFOLD" for row in rows),
        "unseen_scaffold_n": sum(row.get("scaffold_status") == "UNSEEN_SCAFFOLD" for row in rows),
        "median_maximum_similarity": statistics.median(similarities) if similarities else None,
        "similarity_distribution": dict(sorted(Counter(row.get("similarity_bin") for row in rows if row.get("similarity_bin") not in {None, "NOT_EVALUATED"}).items())),
        "final_no_exact_overlap_n": sum("NO_EXACT_TRAINING_OVERLAP" in row.get("cohorts", ()) for row in rows),
        "final_parent_form_free_n": sum("NO_PARENT_FORM_TRAINING_OVERLAP" in row.get("cohorts", ()) for row in rows),
        "structurally_remote_n": sum("STRUCTURALLY_REMOTE_SUBSET" in row.get("cohorts", ()) for row in rows),
    }


def audit_caco2_overlap(caco2_path: Path, endpoint_index: Any, multitask_index: Any) -> dict[str, Any]:
    source_rows = _read_csv(caco2_path)
    annotated: list[dict[str, Any]] = []
    for number, source in enumerate(source_rows, start=1):
        identifiers = structure_identifiers(source["smiles"])
        endpoint_identity = identity_overlap(source["smiles"], endpoint_index)
        multitask_identity = identity_overlap(source["smiles"], multitask_index)
        neighborhood = chemical_neighborhood(source["smiles"], endpoint_index)
        row = {
            "external_row_id": f"CACO2:{number:04d}",
            "ground_truth_status": "VALID_EXACT",
            **identifiers,
            "endpoint_training_identity_status": endpoint_identity["identity_status"],
            "multitask_training_identity_status": multitask_identity["identity_status"],
            **neighborhood,
        }
        row["cohorts"] = cohort_memberships(row)
        annotated.append(row)
    return {
        "dataset_id": "duke-caco2-2022-2023",
        "endpoint": "Caco2_Wang",
        "compatibility_decision": "INSUFFICIENT_METADATA",
        "metrics_computed": False,
        "reason": "Permeability direction and row-level assay context are not supplied.",
        **_counts(annotated),
    }


def build_overlap_report(rows: list[dict[str, Any]], caco2: dict[str, Any], training_manifest: dict[str, Any]) -> dict[str, Any]:
    training_counts = {row["admet_ai_output_name"]: row["valid_structure_count"] for row in training_manifest["datasets"]}
    endpoints: dict[str, Any] = {}
    for endpoint in sorted({row["prediction_endpoint"] for row in rows}):
        valid = [row for row in rows if row["prediction_endpoint"] == endpoint and row["ground_truth_status"] == "VALID_EXACT"]
        endpoints[endpoint] = {
            "training_n": training_counts[endpoint],
            "unique_external_structures": len({row["isomeric_smiles"] for row in valid}),
            **_counts(valid),
        }
    endpoints["Caco2_Wang"] = {"training_n": training_counts["Caco2_Wang"], **caco2}
    return {
        "schema_version": "v0.10.2-overlap-1",
        "exact_overlap_policy": "Headline cohort excludes exact endpoint-source overlap and exact exposure in any regression multitask source.",
        "fingerprint": {"type": "Morgan", "radius": MORGAN_RADIUS, "n_bits": MORGAN_NBITS, "similarity": "Tanimoto"},
        "structurally_remote_definition": f"No exact/parent/salt/stereo relation, unseen Murcko scaffold, maximum similarity < {REMOTE_SIMILARITY_THRESHOLD:.2f}",
        "endpoints": endpoints,
    }


def build_failure_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for endpoint in sorted({row["prediction_endpoint"] for row in rows if row["prediction_status"] == "SUCCESS"}):
        selected = metric_rows_for_cohort(rows, endpoint, "NO_EXACT_TRAINING_OVERLAP")
        selected = sorted(selected, key=lambda row: abs(float(row["normalized_prediction"]) - float(row["ground_truth_normalized_value"])), reverse=True)[:10]
        for rank, row in enumerate(selected, start=1):
            error = float(row["normalized_prediction"]) - float(row["ground_truth_normalized_value"])
            failures.append(
                {
                    "prediction_endpoint": endpoint,
                    "rank_by_absolute_error": rank,
                    "external_dataset_id": row["external_dataset_id"],
                    "external_row_id": row["external_row_id"],
                    "isomeric_smiles": row["isomeric_smiles"],
                    "ground_truth_raw_value": row["ground_truth_raw_value"],
                    "ground_truth_normalized_value": row["ground_truth_normalized_value"],
                    "raw_prediction": row["raw_prediction"],
                    "normalized_prediction": row["normalized_prediction"],
                    "signed_error_prediction_minus_truth": error,
                    "absolute_error": abs(error),
                    "endpoint_training_identity_status": row["endpoint_training_identity_status"],
                    "multitask_training_identity_status": row["multitask_training_identity_status"],
                    "scaffold_status": row["scaffold_status"],
                    "maximum_training_similarity": row["maximum_training_similarity"],
                    "similarity_bin": row["similarity_bin"],
                    "source_measurement_flag": row["ground_truth_qualifier"],
                    "outlier_excluded": False,
                }
            )
    return failures


def _update_processed_hashes(manifest_path: Path, asap_path: Path, biogen_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_id = {row["dataset_id"]: row for row in manifest["datasets"]}
    by_id["asap-antiviral-admet-2025-unblinded"].update({"processed_file": str(asap_path), "processed_file_hash": sha256_file(asap_path)})
    by_id["biogen-adme-fang-3521"].update({"processed_file": str(biogen_path), "processed_file_hash": sha256_file(biogen_path)})
    _write_json(manifest_path, manifest)


def run(
    *,
    external_root: Path,
    caco2_dir: Path,
    reports_dir: Path,
    provider: Any | None = None,
) -> dict[str, Any]:
    compatibility = load_compatibility(external_root / "endpoint_compatibility.csv")
    accepted = {row["mapping_id"] for row in compatibility if row["numerical_validation_allowed"].lower() == "true"}
    if accepted != {"ASAP_HLM_MICROSOME", "ASAP_LOGD_LIPOPHILICITY", "BIOGEN_HPPB_PPBR"}:
        raise ValueError("Accepted endpoint set changed without updating the benchmark protocol")

    endpoint_indexes, multitask_index = load_indexes(external_root / "training_reference")
    rows = prepare_accepted_rows(external_root / "source_snapshots")
    if {row["mapping_id"] for row in rows} != accepted:
        raise ValueError("Prepared benchmark rows do not match the semantic gate")
    annotate_overlap(rows, endpoint_indexes, multitask_index)

    adapter = provider or AdmetAiProvider()
    if not adapter.is_available():
        raise RuntimeError(f"Production ADMET-AI adapter unavailable: {getattr(adapter, 'initialization_error', None)}")
    run_adapter_predictions(rows, adapter)

    results_dir = external_root / "results"
    asap_path = results_dir / "asap_processed_predictions.csv"
    biogen_path = results_dir / "biogen_hppb_processed_predictions.csv"
    _write_csv(asap_path, [row for row in rows if row["external_dataset_id"].startswith("asap-")])
    _write_csv(biogen_path, [row for row in rows if row["external_dataset_id"].startswith("biogen-")])

    caco2 = audit_caco2_overlap(caco2_dir / "logPapp_external_set.csv", endpoint_indexes["Caco2_Wang"], multitask_index)
    training_manifest = json.loads((external_root / "admet_ai_training_manifest.json").read_text(encoding="utf-8"))
    metrics = build_metric_report(rows)
    overlap = build_overlap_report(rows, caco2, training_manifest)
    stratification = build_stratification(rows)
    failures = build_failure_rows(rows)
    _write_json(reports_dir / "v0102_external_metrics.json", metrics)
    _write_json(reports_dir / "v0102_external_overlap.json", overlap)
    _write_json(reports_dir / "v0102_external_stratification.json", stratification)
    _write_csv(external_root / "failure_analysis.csv", failures)
    _update_processed_hashes(external_root / "external_dataset_manifest.json", asap_path, biogen_path)
    summary = {
        "prediction_rows": sum(row["prediction_status"] == "SUCCESS" for row in rows),
        "metrics_path": str(reports_dir / "v0102_external_metrics.json"),
        "overlap_path": str(reports_dir / "v0102_external_overlap.json"),
        "stratification_path": str(reports_dir / "v0102_external_stratification.json"),
        "failure_rows": len(failures),
    }
    _write_json(reports_dir / "v0102_external_run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", type=Path, default=Path("validation/external_prediction"))
    parser.add_argument("--caco2-dir", type=Path, default=Path("validation/outputs/v0102_external/raw/caco2"))
    parser.add_argument("--reports-dir", type=Path, default=Path("validation/reports"))
    args = parser.parse_args()
    print(json.dumps(run(external_root=args.external_root, caco2_dir=args.caco2_dir, reports_dir=args.reports_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
