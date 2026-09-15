"""Fail-closed semantic compatibility gate for external ADMET benchmarks."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


ALLOWED_DECISIONS = {
    "EXACTLY_COMPATIBLE",
    "COMPATIBLE_WITH_DOCUMENTED_TRANSFORM",
    "RELATED_NOT_COMPARABLE",
    "INCOMPATIBLE",
    "INSUFFICIENT_METADATA",
}
BENCHMARKABLE_DECISIONS = {
    "EXACTLY_COMPATIBLE",
    "COMPATIBLE_WITH_DOCUMENTED_TRANSFORM",
}
SEMANTIC_FIELDS = (
    "same_biological_endpoint",
    "same_matrix",
    "same_species",
    "same_assay_family",
    "same_measurement_direction",
    "same_result_semantics",
    "units_compatible",
    "same_transformation",
    "same_classification_threshold",
    "same_positive_class",
)
ALLOWED_GATE_VALUES = {"YES", "NO", "UNKNOWN", "NOT_APPLICABLE", "DOCUMENTED_TRANSFORM"}


def load_compatibility(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))
    for record in records:
        validate_mapping(record)
    return records


def validate_mapping(record: dict[str, Any]) -> None:
    decision = str(record.get("decision", ""))
    if decision not in ALLOWED_DECISIONS:
        raise ValueError(f"Unsupported compatibility decision: {decision}")
    for field in SEMANTIC_FIELDS:
        value = str(record.get(field, ""))
        if value not in ALLOWED_GATE_VALUES:
            raise ValueError(f"Unsupported {field} value: {value}")
    allowed = str(record.get("numerical_validation_allowed", "")).lower() == "true"
    if allowed != (decision in BENCHMARKABLE_DECISIONS):
        raise ValueError("Numerical-validation flag contradicts compatibility decision")
    if decision in BENCHMARKABLE_DECISIONS:
        disqualifying = [
            field
            for field in SEMANTIC_FIELDS[:7]
            if record[field] in {"NO", "UNKNOWN"}
        ]
        if disqualifying:
            raise ValueError(f"Accepted mapping has unresolved semantic gates: {disqualifying}")
        if not str(record.get("reason", "")).strip():
            raise ValueError("Accepted mapping requires a written reason")
        if decision == "COMPATIBLE_WITH_DOCUMENTED_TRANSFORM" and not str(record.get("transformation", "")).strip():
            raise ValueError("Transformed mapping requires an auditable transformation")


def can_benchmark(record: dict[str, Any]) -> bool:
    validate_mapping(record)
    return str(record["decision"]) in BENCHMARKABLE_DECISIONS

