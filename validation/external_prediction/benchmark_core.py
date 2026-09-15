"""Identity, chemical-neighborhood, cohort, and metric primitives for v0.10.2."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from scipy import stats

from validation.external_prediction.training_reference import structure_identifiers


MORGAN_RADIUS = 2
MORGAN_NBITS = 2048
REMOTE_SIMILARITY_THRESHOLD = 0.60
BOOTSTRAP_SEED = 20260828
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_CONFIDENCE = 0.95


@dataclass(frozen=True)
class TrainingIndex:
    source_dataset: str
    rows: tuple[dict[str, str], ...]
    exact_isomeric: frozenset[str]
    exact_inchikey: frozenset[str]
    canonical_to_isomeric: dict[str, frozenset[str]]
    parent_isomeric: frozenset[str]
    parent_inchikey: frozenset[str]
    parent_canonical_to_isomeric: dict[str, frozenset[str]]
    salt_parent_isomeric: frozenset[str]
    scaffolds: frozenset[str]
    fingerprint_smiles: tuple[str, ...]
    fingerprints: tuple[Any, ...]


def _freeze_multimap(values: dict[str, set[str]]) -> dict[str, frozenset[str]]:
    return {key: frozenset(items) for key, items in values.items()}


def build_training_index(rows: Sequence[dict[str, str]], source_dataset: str) -> TrainingIndex:
    valid = tuple(row for row in rows if row.get("structure_parse_status") == "PARSED")
    canonical_to_isomeric: dict[str, set[str]] = {}
    parent_canonical_to_isomeric: dict[str, set[str]] = {}
    salt_parent_isomeric: set[str] = set()
    fp_smiles: list[str] = []
    fps: list[Any] = []
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=MORGAN_RADIUS, fpSize=MORGAN_NBITS)
    seen_fp_smiles: set[str] = set()
    for row in valid:
        canonical_to_isomeric.setdefault(row["canonical_smiles"], set()).add(row["isomeric_smiles"])
        parent_canonical_to_isomeric.setdefault(row["parent_canonical_smiles"], set()).add(row["parent_isomeric_smiles"])
        if "." in row["original_smiles"]:
            salt_parent_isomeric.add(row["parent_isomeric_smiles"])
        fp_smile = row["parent_isomeric_smiles"]
        if fp_smile and fp_smile not in seen_fp_smiles:
            mol = Chem.MolFromSmiles(fp_smile)
            if mol is not None:
                seen_fp_smiles.add(fp_smile)
                fp_smiles.append(fp_smile)
                fps.append(generator.GetFingerprint(mol))
    return TrainingIndex(
        source_dataset=source_dataset,
        rows=valid,
        exact_isomeric=frozenset(row["isomeric_smiles"] for row in valid),
        exact_inchikey=frozenset(row["inchikey"] for row in valid),
        canonical_to_isomeric=_freeze_multimap(canonical_to_isomeric),
        parent_isomeric=frozenset(row["parent_isomeric_smiles"] for row in valid),
        parent_inchikey=frozenset(row["parent_inchikey"] for row in valid),
        parent_canonical_to_isomeric=_freeze_multimap(parent_canonical_to_isomeric),
        salt_parent_isomeric=frozenset(salt_parent_isomeric),
        scaffolds=frozenset(row["murcko_scaffold"] for row in valid if row["murcko_scaffold"]),
        fingerprint_smiles=tuple(fp_smiles),
        fingerprints=tuple(fps),
    )


def load_training_index(path: Path) -> TrainingIndex:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    source = rows[0]["source_dataset"] if rows else path.stem
    return build_training_index(rows, source)


def combine_training_indexes(indexes: Iterable[TrainingIndex], name: str = "ALL_REGRESSION_TASKS") -> TrainingIndex:
    rows: list[dict[str, str]] = []
    for index in indexes:
        rows.extend(index.rows)
    return build_training_index(rows, name)


def identity_overlap(original_smiles: str, index: TrainingIndex) -> dict[str, str]:
    query = structure_identifiers(original_smiles)
    if query["structure_parse_status"] != "PARSED":
        return {"identity_status": "UNRESOLVED", **query}

    if query["isomeric_smiles"] in index.exact_isomeric or query["inchikey"] in index.exact_inchikey:
        status = "EXACT_STRUCTURE_OVERLAP"
    elif query["canonical_smiles"] in index.canonical_to_isomeric:
        status = "STEREO_RELATED"
    elif query["parent_isomeric_smiles"] in index.parent_isomeric or query["parent_inchikey"] in index.parent_inchikey:
        status = (
            "SALT_FORM_OVERLAP"
            if "." in original_smiles or query["parent_isomeric_smiles"] in index.salt_parent_isomeric
            else "PARENT_FORM_OVERLAP"
        )
    elif query["parent_canonical_smiles"] in index.parent_canonical_to_isomeric:
        status = "STEREO_RELATED"
    else:
        status = "NO_IDENTITY_OVERLAP"
    return {"identity_status": status, **query}


def similarity_bin(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "UNRESOLVED"
    if value < 0.40:
        return "<0.40"
    if value < 0.60:
        return "0.40-<0.60"
    if value < 0.80:
        return "0.60-<0.80"
    if value < 0.90:
        return "0.80-<0.90"
    return ">=0.90"


def chemical_neighborhood(original_smiles: str, index: TrainingIndex) -> dict[str, Any]:
    query = structure_identifiers(original_smiles)
    if query["structure_parse_status"] != "PARSED" or not index.fingerprints:
        return {
            "scaffold_status": "UNRESOLVED",
            "maximum_training_similarity": None,
            "maximum_training_similarity_smiles": "",
            "similarity_bin": "UNRESOLVED",
        }
    mol = Chem.MolFromSmiles(query["parent_isomeric_smiles"])
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=MORGAN_RADIUS, fpSize=MORGAN_NBITS)
    fingerprint = generator.GetFingerprint(mol)
    similarities = DataStructs.BulkTanimotoSimilarity(fingerprint, index.fingerprints)
    maximum = max(similarities)
    max_index = similarities.index(maximum)
    scaffold = query["murcko_scaffold"]
    return {
        "scaffold_status": "SEEN_SCAFFOLD" if scaffold and scaffold in index.scaffolds else "UNSEEN_SCAFFOLD",
        "maximum_training_similarity": float(maximum),
        "maximum_training_similarity_smiles": index.fingerprint_smiles[max_index],
        "similarity_bin": similarity_bin(float(maximum)),
    }


def cohort_memberships(record: dict[str, Any]) -> tuple[str, ...]:
    """Return explicit nested cohorts, conservatively using multitask exposure."""
    if record.get("ground_truth_status") != "VALID_EXACT" or record.get("structure_parse_status") != "PARSED":
        return ()
    cohorts = ["ALL_COMPATIBLE_DATA"]
    endpoint_identity = record.get("endpoint_training_identity_status")
    multitask_identity = record.get("multitask_training_identity_status")
    exact = "EXACT_STRUCTURE_OVERLAP"
    if endpoint_identity == exact or multitask_identity == exact:
        return tuple(cohorts)
    cohorts.append("NO_EXACT_TRAINING_OVERLAP")
    parent_related = {"PARENT_FORM_OVERLAP", "SALT_FORM_OVERLAP"}
    if endpoint_identity in parent_related or multitask_identity in parent_related:
        return tuple(cohorts)
    cohorts.append("NO_PARENT_FORM_TRAINING_OVERLAP")
    identity_related = parent_related | {"EXACT_STRUCTURE_OVERLAP", "STEREO_RELATED"}
    if (
        endpoint_identity not in identity_related
        and multitask_identity not in identity_related
        and record.get("scaffold_status") == "UNSEEN_SCAFFOLD"
        and record.get("maximum_training_similarity") is not None
        and float(record["maximum_training_similarity"]) < REMOTE_SIMILARITY_THRESHOLD
    ):
        cohorts.append("STRUCTURALLY_REMOTE_SUBSET")
    return tuple(cohorts)


def regression_metrics(expected: Sequence[float], predicted: Sequence[float]) -> dict[str, float | int | None]:
    y = np.asarray(expected, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if y.shape != p.shape:
        raise ValueError("Expected and predicted values must have identical shapes")
    if y.ndim != 1 or len(y) == 0:
        raise ValueError("At least one one-dimensional observation is required")
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("Metrics require finite observations")
    errors = p - y
    abs_errors = np.abs(errors)
    n = len(y)
    denominator = float(np.sum((y - np.mean(y)) ** 2))
    r2 = None if denominator == 0 else float(1 - np.sum(errors**2) / denominator)
    pearson = None if n < 2 or np.std(y) == 0 or np.std(p) == 0 else float(stats.pearsonr(y, p).statistic)
    spearman = None if n < 2 or len(set(y)) < 2 or len(set(p)) < 2 else float(stats.spearmanr(y, p).statistic)
    return {
        "n": n,
        "mae": float(np.mean(abs_errors)),
        "median_absolute_error": float(np.median(abs_errors)),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "r2": r2,
        "pearson_r": pearson,
        "spearman_rho": spearman,
        "mean_error_bias": float(np.mean(errors)),
    }


def bootstrap_intervals(
    expected: Sequence[float],
    predicted: Sequence[float],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    confidence: float = BOOTSTRAP_CONFIDENCE,
) -> dict[str, dict[str, float | int | None]]:
    if replicates < 1:
        raise ValueError("At least one bootstrap replicate is required")
    y = np.asarray(expected, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if len(y) != len(p) or len(y) == 0:
        raise ValueError("Expected and predicted values must be non-empty and aligned")
    rng = np.random.default_rng(seed)
    sampled: dict[str, list[float]] = {key: [] for key in regression_metrics(y, p) if key != "n"}
    for _ in range(replicates):
        indices = rng.integers(0, len(y), size=len(y))
        metrics = regression_metrics(y[indices], p[indices])
        for key in sampled:
            value = metrics[key]
            if value is not None and math.isfinite(float(value)):
                sampled[key].append(float(value))
    alpha = (1 - confidence) / 2
    intervals: dict[str, dict[str, float | int | None]] = {}
    point = regression_metrics(y, p)
    for key, values in sampled.items():
        intervals[key] = {
            "point_estimate": point[key],
            "lower": float(np.quantile(values, alpha)) if values else None,
            "upper": float(np.quantile(values, 1 - alpha)) if values else None,
            "valid_replicates": len(values),
        }
    return intervals

