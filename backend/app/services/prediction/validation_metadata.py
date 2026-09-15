"""Conservative endpoint-level external-validation metadata.

Aggregate benchmark performance is not per-molecule uncertainty and is never
returned here.  The versioned artifact reference only indicates that a
compatible non-overlap external benchmark exists for the learned endpoint.
"""

from __future__ import annotations

from typing import Any


VALIDATION_ARTIFACT_ID = "v0.10.2-external-predictive-validation-2026-08-28"
VALIDATION_ARTIFACT_PATH = "docs/ADMET_AI_EXTERNAL_VALIDATION.md"
EXTERNALLY_BENCHMARKED_ENDPOINTS = frozenset(
    {
        "clearance_microsome_az",
        "lipophilicity_astrazeneca",
        "ppbr_az",
    }
)


def prediction_validation_metadata(endpoint_id: str, prediction_type: str | None) -> dict[str, Any]:
    normalized_id = endpoint_id.casefold()
    if prediction_type == "reference_percentile" or normalized_id.endswith("_percentile"):
        return {
            "validation_status": "EXTERNAL_VALIDATION_NOT_AVAILABLE",
            "validation_artifact_id": None,
            "validation_artifact_path": None,
            "validation_note": "Reference-distribution percentile only; it is not a probability and is not covered by the endpoint regression benchmark.",
        }
    if normalized_id in EXTERNALLY_BENCHMARKED_ENDPOINTS:
        return {
            "validation_status": "EXTERNAL_VALIDATION_AVAILABLE",
            "validation_artifact_id": VALIDATION_ARTIFACT_ID,
            "validation_artifact_path": VALIDATION_ARTIFACT_PATH,
            "validation_note": "A compatible non-overlap aggregate external benchmark is available. It is not per-molecule uncertainty, confidence, clinical validation, or an applicability-domain classification.",
        }
    return {
        "validation_status": "EXTERNAL_VALIDATION_NOT_AVAILABLE",
        "validation_artifact_id": None,
        "validation_artifact_path": None,
        "validation_note": "No compatible non-overlap external benchmark is available for this output; this is not an experimental measurement or clinical risk estimate.",
    }

