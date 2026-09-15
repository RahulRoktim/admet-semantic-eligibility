"""Predict the ASAP HLM rows that the v0.10.2 benchmark excluded before inference.

The v0.10.2 external benchmark treated ASAP human liver microsomal clearance
values below 10 uL/min/mg as unreliable exact measurements, following the
dataset's own documented limitation, and set ``prediction_status`` to
``NOT_RUN_GROUND_TRUTH_EXCLUDED`` for those rows.  Because those rows were
never predicted, the headline cohort cannot be checked for range restriction
from the frozen artefacts alone.

This module runs the *same* production adapter and package version over exactly
those rows and writes a new, separately versioned artefact.  It never rewrites
``validation/external_prediction/results/*.csv`` and never changes any
previously published number.

Run from the repository root:

    PYTHONPATH=backend python preprint/analysis/hlm_low_clearance_sensitivity.py
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
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.prediction.admet_ai_provider import AdmetAiProvider  # noqa: E402
from validation.external_prediction.benchmark_data import select_adapter_prediction  # noqa: E402

SOURCE_PREDICTIONS = REPO_ROOT / "validation/external_prediction/results/asap_processed_predictions.csv"
OUTPUT_CSV = REPO_ROOT / "preprint/results/hlm_low_clearance_predictions.csv"
OUTPUT_MANIFEST = REPO_ROOT / "preprint/results/hlm_low_clearance_manifest.json"

ENDPOINT = "Clearance_Microsome_AZ"
EXCLUDED_STATUS = "EXCLUDED_CENSORING_OR_BOUND"
MODEL_RUN_ID = "PREPRINT-V1-HLM-LOWCLEARANCE-ADMETAI-2.0.1"

# Columns carried over verbatim from the frozen v0.10.2 artefact so that the
# sensitivity rows can be concatenated with the headline rows without any
# re-derivation of structure identifiers or overlap status.
CARRIED_FIELDS = (
    "external_dataset_id",
    "external_row_id",
    "mapping_id",
    "prediction_endpoint",
    "original_smiles",
    "ground_truth_raw_value",
    "source_partition",
    "canonical_smiles",
    "isomeric_smiles",
    "inchikey",
    "parent_canonical_smiles",
    "parent_isomeric_smiles",
    "parent_inchikey",
    "murcko_scaffold",
    "structure_parse_status",
    "ground_truth_raw_unit",
    "ground_truth_qualifier",
    "ground_truth_status",
    "ground_truth_normalized_unit",
    "transformation",
    "reverse_transformation",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def select_excluded_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return the HLM rows excluded for being below the reliable exact bound."""
    selected = [
        row
        for row in rows
        if row["prediction_endpoint"] == ENDPOINT
        and row["ground_truth_status"] == EXCLUDED_STATUS
    ]
    for row in selected:
        # These invariants are what make the rows safe to re-use: the frozen
        # artefact must agree that they were never predicted.
        if row["prediction_status"] != "NOT_RUN_GROUND_TRUTH_EXCLUDED":
            raise ValueError(f"Row {row['external_row_id']} was already predicted; refusing to overwrite history")
        if row["normalized_prediction"] != "":
            raise ValueError(f"Row {row['external_row_id']} already carries a prediction")
        if row["structure_parse_status"] != "PARSED":
            raise ValueError(f"Row {row['external_row_id']} has no parsed structure")
    return selected


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args(argv)

    source_rows = read_csv(SOURCE_PREDICTIONS)
    excluded = select_excluded_rows(source_rows)
    if not excluded:
        raise SystemExit("No excluded HLM rows found; the frozen artefact does not match expectations")

    provider = AdmetAiProvider()
    if not provider.is_available():
        raise SystemExit(f"ADMET-AI is not available: {provider.initialization_error}")

    unique_smiles = list(dict.fromkeys(row["isomeric_smiles"] for row in excluded))
    predictions: dict[str, list[dict[str, Any]]] = {}
    for start in range(0, len(unique_smiles), args.batch_size):
        batch = unique_smiles[start : start + args.batch_size]
        records = provider.predict_smiles_batch(batch)
        if len(records) != len(batch):
            raise RuntimeError("Production adapter returned an unaligned prediction batch")
        predictions.update(zip(batch, records))

    package_version = getattr(provider, "package_version", None) or "UNKNOWN"
    adapter_version = getattr(provider, "version", None) or "UNKNOWN"

    output: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in excluded:
        new_row = {field: row[field] for field in CARRIED_FIELDS}
        new_row.update(
            {
                "model_run_id": MODEL_RUN_ID,
                "provider": "admet_ai",
                "package_version": package_version,
                "adapter_version": adapter_version,
                "sensitivity_cohort": "HLM_BELOW_RELIABLE_BOUND",
            }
        )
        try:
            selected = select_adapter_prediction(predictions[row["isomeric_smiles"]], ENDPOINT)
            value = float(selected["normalized_prediction"])
        except Exception as exc:  # pragma: no cover - explicit failure reporting
            new_row.update(
                {
                    "ground_truth_normalized_value": "",
                    "raw_prediction": "",
                    "normalized_prediction": "",
                    "prediction_status": "FAILED",
                    "failure_reason": repr(exc),
                }
            )
            failures.append(new_row)
            output.append(new_row)
            continue
        # The ground-truth value is the raw source value; the v0.10.2 artefact
        # deliberately left ``ground_truth_normalized_value`` empty for these
        # rows because they were excluded, so it is restored here on the same
        # identity scale (uL/min/mg, identity transform).
        new_row.update(
            {
                "ground_truth_normalized_value": float(row["ground_truth_raw_value"]),
                "raw_prediction": value,
                "normalized_prediction": value,
                "prediction_status": "SUCCESS",
                "failure_reason": "",
            }
        )
        output.append(new_row)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = list(output[0])
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)

    successes = [row for row in output if row["prediction_status"] == "SUCCESS"]
    values = [float(row["normalized_prediction"]) for row in successes]
    manifest = {
        "artifact_id": MODEL_RUN_ID,
        "schema_version": 1,
        "purpose": (
            "Range-restriction sensitivity for ASAP human liver microsomal clearance. "
            "Predicts only the rows the v0.10.2 headline benchmark excluded before inference."
        ),
        "source_artifact": SOURCE_PREDICTIONS.relative_to(REPO_ROOT).as_posix(),
        "source_artifact_sha256": sha256_file(SOURCE_PREDICTIONS),
        "provider": "admet_ai",
        "package_version": package_version,
        "adapter_version": adapter_version,
        "endpoint": ENDPOINT,
        "evaluation_scale": "uL/min/mg",
        "transformation": "identity",
        "rows_requested": len(excluded),
        "unique_structures_requested": len(unique_smiles),
        "rows_predicted": len(successes),
        "rows_failed": len(failures),
        "failures": [{"external_row_id": row["external_row_id"], "reason": row["failure_reason"]} for row in failures],
        "negative_predictions_retained": sum(1 for value in values if value < 0),
        "prediction_min": min(values) if values else None,
        "prediction_max": max(values) if values else None,
        "ground_truth_min": min(float(row["ground_truth_normalized_value"]) for row in successes) if successes else None,
        "ground_truth_max": max(float(row["ground_truth_normalized_value"]) for row in successes) if successes else None,
        "output_artifact": OUTPUT_CSV.relative_to(REPO_ROOT).as_posix(),
        "output_artifact_sha256": sha256_file(OUTPUT_CSV),
        "note": (
            "No row is filtered out of this artefact. Negative predictions are retained on the native scale. "
            "This artefact does not modify any v0.10.2 published number."
        ),
    }
    OUTPUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"rows requested        : {manifest['rows_requested']}")
    print(f"unique structures     : {manifest['unique_structures_requested']}")
    print(f"rows predicted        : {manifest['rows_predicted']}")
    print(f"rows failed           : {manifest['rows_failed']}")
    print(f"negative predictions  : {manifest['negative_predictions_retained']}")
    print(f"prediction range      : [{manifest['prediction_min']}, {manifest['prediction_max']}]")
    print(f"ground truth range    : [{manifest['ground_truth_min']}, {manifest['ground_truth_max']}]")
    print(f"wrote {OUTPUT_CSV.relative_to(REPO_ROOT)} ({manifest['output_artifact_sha256'][:16]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
