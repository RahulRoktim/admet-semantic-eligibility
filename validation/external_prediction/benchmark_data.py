"""Lossless external-row preparation and auditable endpoint transformations."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from validation.external_prediction.training_reference import structure_identifiers


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _base_row(
    *,
    dataset_id: str,
    external_row_id: str,
    mapping_id: str,
    output_name: str,
    original_smiles: str,
    raw_value: str,
    source_partition: str,
) -> dict[str, Any]:
    return {
        "external_dataset_id": dataset_id,
        "external_row_id": external_row_id,
        "mapping_id": mapping_id,
        "prediction_endpoint": output_name,
        "original_smiles": original_smiles,
        "ground_truth_raw_value": raw_value,
        "source_partition": source_partition,
        **structure_identifiers(original_smiles),
    }


def _parse_number(raw: str) -> float | None:
    if raw is None or not str(raw).strip():
        return None
    value = float(raw)
    return value if math.isfinite(value) else None


def prepare_asap_rows(path: Path) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for source_number, source in enumerate(_read(path), start=1):
        row_id = source.get("Molecule Name") or f"ASAP:{source_number}"
        smiles = source["CXSMILES"]
        partition = source["Set"].upper()

        raw_hlm = source["HLM"]
        hlm = _parse_number(raw_hlm)
        row = _base_row(
            dataset_id="asap-antiviral-admet-2025-unblinded",
            external_row_id=f"{row_id}:HLM",
            mapping_id="ASAP_HLM_MICROSOME",
            output_name="Clearance_Microsome_AZ",
            original_smiles=smiles,
            raw_value=raw_hlm,
            source_partition=partition,
        )
        row.update(
            {
                "ground_truth_raw_unit": "uL/min/mg",
                "ground_truth_qualifier": "=" if hlm is not None and hlm >= 10 else ("LOWER_BOUND_UNRELIABLE_<10" if hlm is not None else "MISSING"),
                "ground_truth_status": "VALID_EXACT" if hlm is not None and hlm >= 10 else ("EXCLUDED_CENSORING_OR_BOUND" if hlm is not None else "EXCLUDED_MISSING"),
                "ground_truth_normalized_value": hlm if hlm is not None and hlm >= 10 else None,
                "ground_truth_normalized_unit": "uL/min/mg",
                "transformation": "identity",
                "reverse_transformation": "identity",
            }
        )
        prepared.append(row)

        raw_logd = source["LogD"]
        logd = _parse_number(raw_logd)
        row = _base_row(
            dataset_id="asap-antiviral-admet-2025-unblinded",
            external_row_id=f"{row_id}:LogD",
            mapping_id="ASAP_LOGD_LIPOPHILICITY",
            output_name="Lipophilicity_AstraZeneca",
            original_smiles=smiles,
            raw_value=raw_logd,
            source_partition=partition,
        )
        row.update(
            {
                "ground_truth_raw_unit": "logD at pH 7.4",
                "ground_truth_qualifier": "=" if logd is not None else "MISSING",
                "ground_truth_status": "VALID_EXACT" if logd is not None else "EXCLUDED_MISSING",
                "ground_truth_normalized_value": logd,
                "ground_truth_normalized_unit": "logD at pH 7.4",
                "transformation": "identity",
                "reverse_transformation": "identity",
            }
        )
        prepared.append(row)
    return prepared


def prepare_biogen_hppb_rows(path: Path) -> list[dict[str, Any]]:
    field = "LOG PLASMA PROTEIN BINDING (HUMAN) (% unbound)"
    prepared: list[dict[str, Any]] = []
    for source_number, source in enumerate(_read(path), start=1):
        raw_value = source[field]
        log_percent_unbound = _parse_number(raw_value)
        percent_bound = None if log_percent_unbound is None else 100 - (10**log_percent_unbound)
        valid = percent_bound is not None and 0 <= percent_bound <= 100
        row = _base_row(
            dataset_id="biogen-adme-fang-3521",
            external_row_id=f"{source.get('Internal ID') or source_number}:hPPB",
            mapping_id="BIOGEN_HPPB_PPBR",
            output_name="PPBR_AZ",
            original_smiles=source["SMILES"],
            raw_value=raw_value,
            source_partition="PUBLIC_SET",
        )
        row.update(
            {
                "ground_truth_raw_unit": "log10(% unbound)",
                "ground_truth_qualifier": "=" if valid else ("OUT_OF_RANGE_AFTER_TRANSFORM" if percent_bound is not None else "MISSING"),
                "ground_truth_status": "VALID_EXACT" if valid else ("EXCLUDED_INVALID_TRANSFORM" if percent_bound is not None else "EXCLUDED_MISSING"),
                "ground_truth_normalized_value": percent_bound if valid else None,
                "ground_truth_normalized_unit": "% bound",
                "transformation": "100 - (10**raw_log10_percent_unbound)",
                "reverse_transformation": "log10(100 - normalized_percent_bound)",
            }
        )
        prepared.append(row)
    return prepared


def prepare_accepted_rows(snapshot_dir: Path) -> list[dict[str, Any]]:
    return prepare_asap_rows(snapshot_dir / "asap_antiviral_admet_2025_unblinded.csv") + prepare_biogen_hppb_rows(
        snapshot_dir / "biogen_ADME_public_set_3521.csv"
    )


def reverse_ground_truth(record: dict[str, Any]) -> float:
    value = float(record["ground_truth_normalized_value"])
    mapping = record["mapping_id"]
    if mapping == "ASAP_HLM_MICROSOME":
        return value
    if mapping == "ASAP_LOGD_LIPOPHILICITY":
        return value
    if mapping == "BIOGEN_HPPB_PPBR":
        return math.log10(100 - value)
    raise ValueError(f"No reverse transform registered for {mapping}")


def normalize_prediction(record: dict[str, Any], raw_prediction: float) -> float:
    return raw_prediction


def select_adapter_prediction(records: list[dict[str, Any]], output_name: str) -> dict[str, Any]:
    matches = [
        record
        for record in records
        if record.get("source_output_name", "").casefold() == output_name.casefold()
        and record.get("prediction_type") == "regression"
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one regression output for {output_name}; found {len(matches)}")
    if matches[0]["endpoint_id"].endswith("_percentile"):
        raise ValueError("Reference percentile cannot be used as a model prediction")
    return matches[0]
