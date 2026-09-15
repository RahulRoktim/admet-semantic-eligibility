"""Stage A (Level 2): derive the training-reference summary from upstream data.

The reconstructed Therapeutics Data Commons reference tables carry upstream
structure-target pairs whose licensing provenance is ambiguous (see
``DATA_LICENSES.md``), so they are **not redistributed**. This script is the
only consumer of those tables. It writes a derived summary containing:

* aggregate training-label statistics (n, mean, median, standard deviation);
* a binned label density used for one figure panel;
* this project's own baseline error metrics (training mean, training median,
  1-nearest-neighbour Morgan/Tanimoto) computed against the external rows;
* the Kolmogorov-Smirnov label-shift statistic;
* structural overlap annotation for the 36 low-clearance sensitivity rows.

No upstream structure, no upstream target value and no structure-target pair is
written to the summary. Everything downstream reads the summary, so Level 1
reproduction runs offline without the upstream tables present.

    PYTHONPATH=backend python preprint/analysis/build_training_reference_summary.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for candidate in (str(REPO_ROOT), str(REPO_ROOT / "backend")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import numpy as np  # noqa: E402

from preprint.analysis import core  # noqa: E402
from validation.external_prediction.benchmark_core import (  # noqa: E402
    chemical_neighborhood,
    cohort_memberships,
    combine_training_indexes,
    identity_overlap,
    load_training_index,
)

OUTPUT = core.PREPRINT_RESULTS / "training_reference_summary.json"
SUMMARY_ID = "preprint-v1.0-training-reference-summary"

#: Annotation fields written to the published summary.
#: ``maximum_training_similarity_smiles`` is deliberately excluded here because
#: it would name an upstream training structure. It is still carried in memory
#: within this script so the nearest-neighbour baseline resolves every row; only
#: the serialised summary is redacted.
ANNOTATION_FIELDS = (
    "endpoint_training_identity_status",
    "multitask_training_identity_status",
    "scaffold_status",
    "maximum_training_similarity",
    "similarity_bin",
    "cohorts",
)

#: Carried in memory for baseline resolution, never serialised.
REDACTED_ANNOTATION_FIELD = "maximum_training_similarity_smiles"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def annotate_low_clearance(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Give the sensitivity rows the benchmark's overlap and neighbourhood annotation."""
    all_indexes = {path.stem: load_training_index(path) for path in sorted(core.TRAINING_DIR.glob("*.csv"))}
    endpoint_index = all_indexes["Clearance_Microsome_AZ"]
    multitask_index = combine_training_indexes(all_indexes.values())
    for row in rows:
        if row["prediction_status"] != "SUCCESS":
            row.update({field: "" for field in ANNOTATION_FIELDS})
            row[REDACTED_ANNOTATION_FIELD] = ""
            row["scaffold_status"] = "NOT_EVALUATED"
            row["similarity_bin"] = "NOT_EVALUATED"
            continue
        endpoint_identity = identity_overlap(row["original_smiles"], endpoint_index)
        multitask_identity = identity_overlap(row["original_smiles"], multitask_index)
        neighbourhood = chemical_neighborhood(row["original_smiles"], endpoint_index)
        row.update(
            {
                "endpoint_training_identity_status": endpoint_identity["identity_status"],
                "multitask_training_identity_status": multitask_identity["identity_status"],
                "scaffold_status": neighbourhood["scaffold_status"],
                "maximum_training_similarity": neighbourhood["maximum_training_similarity"],
                "similarity_bin": neighbourhood["similarity_bin"],
                # In memory only; redacted from the serialised summary.
                REDACTED_ANNOTATION_FIELD: neighbourhood[REDACTED_ANNOTATION_FIELD],
            }
        )
        probe = dict(row)
        probe["ground_truth_status"] = "VALID_EXACT"
        row["cohorts"] = ";".join(cohort_memberships(probe))
    return rows


def label_histogram(values: np.ndarray, external: np.ndarray, endpoint: str) -> dict[str, Any]:
    """Binned training-label density for the distribution panel of Figure 2.

    Bin edges deliberately span the union of the training and external label
    ranges so that neither distribution is visually truncated when the two are
    overlaid. Clearance is strongly right-skewed and is binned logarithmically;
    the other endpoints use linear bins on their native scale.
    """
    log_scale = endpoint == "Clearance_Microsome_AZ"
    if log_scale:
        positive = values[values > 0]
        positive_external = external[external > 0]
        low = float(min(positive.min(), positive_external.min()))
        high = float(max(positive.max(), positive_external.max()))
        edges = np.logspace(np.log10(low), np.log10(high), core.SUMMARY_HISTOGRAM_BINS)
        density, _ = np.histogram(positive, bins=edges, density=True)
        kept = int(positive.size)
    else:
        low = float(min(values.min(), external.min()))
        high = float(max(np.quantile(values, 0.995), np.quantile(external, 0.995)))
        edges = np.linspace(low, high, core.SUMMARY_HISTOGRAM_BINS)
        density, _ = np.histogram(values, bins=edges, density=True)
        kept = int(values.size)
    return {
        "scale": "log10" if log_scale else "linear",
        "bins": core.SUMMARY_HISTOGRAM_BINS,
        "values_binned": kept,
        "edge_range_source": "union of training and headline-cohort external label ranges",
        "edges": [float(value) for value in edges],
        "density": [float(value) for value in density],
        "note": "Aggregate binned density derived by this project. Not a redistribution of upstream label values.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", action="store_true", help="compare against the committed summary instead of writing")
    args = parser.parse_args(argv)

    if not core.training_reference_available():
        raise SystemExit(
            "Upstream Therapeutics Data Commons reference tables are not present.\n"
            "They are not redistributed with this release; see DATA_LICENSES.md and REPRODUCE.md (Level 2)\n"
            f"for how to obtain and reconstruct them into {core.TRAINING_DIR.relative_to(REPO_ROOT).as_posix()}/."
        )

    rows = core.load_prediction_rows()
    low_clearance = annotate_low_clearance(core.load_low_clearance_rows())
    stereo_flags = core.asap_stereo_ambiguity()
    cohorts = core.select_cohort_rows(rows, low_clearance, stereo_flags)

    endpoints: dict[str, Any] = {}
    for endpoint in core.ENDPOINTS:
        training = core.load_training_targets(endpoint)
        block: dict[str, Any] = {
            "training_labels": {
                "n": training["n"],
                "mean": training["mean"],
                "median": training["median"],
                "sd": training["sd"],
            },
            "label_histogram": label_histogram(
                training["values"],
                np.asarray(core.observed(cohorts[(endpoint, "A_HEADLINE")]), dtype=float),
                endpoint,
            ),
            "cohorts": {},
        }
        for cohort in core.TRAINING_DEPENDENT_COHORTS:
            selected = cohorts.get((endpoint, cohort))
            if not selected:
                continue
            y = core.observed(selected)
            baselines = core.baseline_predictions(selected, training)
            block["cohorts"][cohort] = {
                "n": len(selected),
                "baselines": {
                    "training_mean": core.regression_metrics(y, baselines["training_mean"]),
                    "training_median": core.regression_metrics(y, baselines["training_median"]),
                    "nearest_neighbour_morgan_tanimoto": core.regression_metrics(y, baselines["nearest_neighbour"]),
                    "nearest_neighbour_unresolved_rows": baselines["nearest_neighbour_unresolved_rows"],
                },
                "label_shift": core.label_shift(training, y),
            }
        endpoints[endpoint] = block

    payload = {
        "artifact_id": SUMMARY_ID,
        "schema_version": 1,
        "purpose": (
            "Derived aggregate statistics and this project's own baseline error metrics, computed from the "
            "reconstructed Therapeutics Data Commons reference tables. Those tables are not redistributed "
            "because their upstream licensing provenance is ambiguous; see DATA_LICENSES.md."
        ),
        "contains_upstream_structures": False,
        "contains_upstream_target_values": False,
        "upstream_tables_sha256": {
            path.name: sha256_file(path) for path in sorted(core.TRAINING_DIR.glob("*.csv"))
        },
        "low_clearance_annotation": {
            row["external_row_id"]: {field: row[field] for field in ANNOTATION_FIELDS}
            for row in low_clearance
        },
        "endpoints": endpoints,
    }

    serialised = json.dumps(payload, indent=2, allow_nan=False, sort_keys=False) + "\n"

    if args.compare:
        if not OUTPUT.is_file():
            raise SystemExit(f"{OUTPUT} does not exist; nothing to compare against.")
        committed = json.loads(OUTPUT.read_text(encoding="utf-8"))
        differences = []
        for endpoint, block in endpoints.items():
            reference = committed["endpoints"][endpoint]
            for key in ("n", "mean", "median", "sd"):
                a, b = block["training_labels"][key], reference["training_labels"][key]
                if a != b:
                    differences.append(f"{endpoint}.training_labels.{key}: rebuilt {a} vs committed {b}")
            for cohort, payload_block in block["cohorts"].items():
                reference_cohort = reference["cohorts"][cohort]
                for family in ("training_mean", "training_median", "nearest_neighbour_morgan_tanimoto"):
                    for metric, value in payload_block["baselines"][family].items():
                        other = reference_cohort["baselines"][family][metric]
                        if value is None and other is None:
                            continue
                        if value is None or other is None or abs(float(value) - float(other)) > 1e-9:
                            differences.append(f"{endpoint}.{cohort}.{family}.{metric}: rebuilt {value} vs committed {other}")
                for metric in ("ks_statistic", "ks_p_value", "training_mean", "training_sd", "external_mean", "external_sd"):
                    value = payload_block["label_shift"][metric]
                    other = reference_cohort["label_shift"][metric]
                    if abs(float(value) - float(other)) > 1e-9:
                        differences.append(f"{endpoint}.{cohort}.label_shift.{metric}: rebuilt {value} vs committed {other}")
        if differences:
            print(f"MISMATCH: {len(differences)} difference(s) between rebuilt and committed summary\n")
            for difference in differences:
                print(f"  {difference}")
            return 1
        print("MATCH: rebuilt summary agrees with the committed summary to within 1e-9")
        print(f"  endpoints compared     : {len(endpoints)}")
        print(f"  cohort blocks compared : {sum(len(block['cohorts']) for block in endpoints.values())}")
        return 0

    OUTPUT.write_text(serialised, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT).as_posix()}")
    print(f"  endpoints              : {len(endpoints)}")
    print(f"  cohort blocks          : {sum(len(block['cohorts']) for block in endpoints.values())}")
    print(f"  low-clearance rows      : {len(payload['low_clearance_annotation'])}")
    print(f"  upstream tables hashed  : {len(payload['upstream_tables_sha256'])}")
    print("  contains upstream structures or targets: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
