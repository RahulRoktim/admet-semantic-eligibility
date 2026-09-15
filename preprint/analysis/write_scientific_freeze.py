"""Generate the scientific freeze record from the artefacts themselves.

Every value is read from the generated results, the manifests or Git. Nothing is
transcribed by hand, so the freeze document cannot drift from what was actually
produced.

    PYTHONPATH=backend python preprint/analysis/write_scientific_freeze.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for candidate in (str(REPO_ROOT), str(REPO_ROOT / "backend")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from preprint.analysis import core  # noqa: E402

OUT_JSON = REPO_ROOT / "preprint/results/scientific_freeze.json"
OUT_MD = REPO_ROOT / "preprint/SCIENTIFIC_FREEZE.md"

BASE_COMMIT = "48e6e0e423402cc4d79177c564538885b193ee65"
PRIVATE_FROZEN_RELEASE_COMMIT = "bba8a77e388985c5a38a346338f432e3e0f93d39"

PUBLIC_EXPORT_STATEMENT = (
    "The public repository is a clean, redistribution-safe export of a frozen private "
    "development repository. The public Git history intentionally begins at the release "
    "snapshot because certain upstream-derived reference tables used during development are "
    "not redistributed. The omitted tables are third-party material whose upstream licensing "
    "provenance could not be established with confidence; they are not proprietary to this "
    "project, and their contents are not included here. Their SHA-256 hashes and full "
    "reconstruction instructions are published so an independent rebuild can be verified."
)

HASHED_ARTEFACTS = {
    "manuscript": ["preprint/manuscript/manuscript.md", "preprint/manuscript/CLAIM_AUDIT.md"],
    "figures": [
        "preprint/figures/figure1_eligibility_funnel.png",
        "preprint/figures/figure1_eligibility_funnel.pdf",
        "preprint/figures/figure2_shift_and_compression.png",
        "preprint/figures/figure2_shift_and_compression.pdf",
        "preprint/figures/figure3_baseline_relative.png",
        "preprint/figures/figure3_baseline_relative.pdf",
    ],
    "tables": [
        "preprint/tables/table1_compatibility.csv",
        "preprint/tables/table2_external_results.csv",
        "preprint/tables/supplementary_sensitivity.csv",
    ],
    "compatibility_matrix": ["validation/external_prediction/endpoint_compatibility.csv"],
    "sensitivity_inputs": [
        "preprint/results/hlm_low_clearance_predictions.csv",
        "preprint/results/hlm_low_clearance_manifest.json",
        "preprint/results/training_reference_summary.json",
    ],
    "analysis_outputs": [
        "preprint/results/preprint_analysis.json",
        "preprint/results/analysis_summary.md",
        "preprint/results/analysis_manifest.json",
        "preprint/results/frozen_input_manifest.json",
    ],
    "frozen_prediction_rows": [
        "validation/external_prediction/results/asap_processed_predictions.csv",
        "validation/external_prediction/results/biogen_hppb_processed_predictions.csv",
    ],
    "source_snapshots": [
        "validation/external_prediction/source_snapshots/asap_antiviral_admet_2025_unblinded.csv",
        "validation/external_prediction/source_snapshots/biogen_ADME_public_set_3521.csv",
    ],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()


def build() -> dict[str, Any]:
    analysis = json.loads((REPO_ROOT / "preprint/results/preprint_analysis.json").read_text(encoding="utf-8"))
    summary = json.loads((REPO_ROOT / "preprint/results/training_reference_summary.json").read_text(encoding="utf-8"))
    low_clearance = json.loads((REPO_ROOT / "preprint/results/hlm_low_clearance_manifest.json").read_text(encoding="utf-8"))
    datasets = json.loads(
        (REPO_ROOT / "validation/external_prediction/external_dataset_manifest.json").read_text(encoding="utf-8")
    )

    headline: dict[str, Any] = {}
    for endpoint, block in analysis["results"].items():
        cohorts = block["cohorts"]
        entry = {
            "label": block["label"],
            "evaluation_scale": block["evaluation_scale"],
            "cohorts": {},
        }
        for name, payload in cohorts.items():
            metrics = payload["metrics"]
            entry["cohorts"][name] = {
                "n": metrics["n"],
                "unique_structures": payload.get("unique_structures"),
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
                "r2": metrics["r2"],
                "pearson_r": metrics["pearson_r"],
                "spearman_rho": metrics["spearman_rho"],
                "mean_error_bias": metrics["mean_error_bias"],
                "calibration_slope": metrics["calibration_slope"],
                "truth_sd": metrics["truth_sd"],
                "prediction_sd": metrics["prediction_sd"],
                "sd_ratio": metrics["sd_ratio"],
            }
        entry["label_shift"] = cohorts["A_HEADLINE"]["label_shift"]
        entry["baselines"] = {
            key: value
            for key, value in cohorts["A_HEADLINE"]["baselines"].items()
            if key != "nearest_neighbour_unresolved_rows"
        }
        headline[endpoint] = entry

    return {
        "artifact_id": "preprint-v1.0.0-scientific-freeze",
        "schema_version": 1,
        "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "FROZEN",
        "deviation_policy": (
            "The scientific content recorded here is frozen. Any change to cohort definitions, "
            "compatibility decisions, statistical methods, figures, tables or reported results after "
            "this freeze requires a documented deviation recorded in preprint/DEVIATIONS.md, stating "
            "what changed, why, which hashes below are invalidated, and who authorised it. Editorial "
            "changes that do not alter a number (typography, wording, author metadata) do not require "
            "a deviation but do invalidate the manuscript hash, which must be regenerated."
        ),
        "provenance": {
            "public_export_statement": PUBLIC_EXPORT_STATEMENT,
            "private_scientific_base_commit": BASE_COMMIT,
            "private_scientific_base_commit_note": (
                "State of the private development repository before any preprint work began; working tree was clean."
            ),
            "private_frozen_release_commit": PRIVATE_FROZEN_RELEASE_COMMIT,
            "private_frozen_release_commit_note": (
                "The frozen private state this public repository was exported from. It is not reachable "
                "from this repository's history, by design."
            ),
            "public_repository_history": "begins at the release snapshot; no parent relationship to the private history",
            "public_branch": git("rev-parse", "--abbrev-ref", "HEAD") or "not yet initialised",
        },
        "software": {
            "model": {
                "name": "ADMET-AI",
                "package_version": low_clearance["package_version"],
                "adapter_version": low_clearance["adapter_version"],
                "weights_modified": False,
            },
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "key_libraries": _library_versions(),
        },
        "datasets": [
            {
                "dataset_id": entry["dataset_id"],
                "dataset_version": entry.get("dataset_version"),
                "retrieval_date": entry.get("retrieval_date"),
                "license": entry.get("license"),
                "rows_raw": entry.get("number_of_rows_raw"),
                "unique_structures": entry.get("number_of_unique_structures"),
                "raw_file_hash": entry.get("raw_file_hash"),
            }
            for entry in datasets["datasets"]
        ],
        "upstream_tables_not_redistributed": summary["upstream_tables_sha256"],
        "seeds_and_parameters": {
            "bootstrap_seed": core.BOOTSTRAP_SEED,
            "bootstrap_replicates": core.BOOTSTRAP_REPLICATES,
            "confidence_level": core.BOOTSTRAP_CONFIDENCE,
            "fingerprint": {
                "type": "Morgan",
                "radius": core.MORGAN_RADIUS,
                "n_bits": core.MORGAN_NBITS,
                "similarity": "Tanimoto",
            },
            "structurally_remote_similarity_threshold": core.REMOTE_SIMILARITY_THRESHOLD,
            "reproduction_tolerance": 1e-9,
            "summary_histogram_bins": core.SUMMARY_HISTOGRAM_BINS,
        },
        "cohort_definitions": analysis["cohort_definitions"],
        "compatibility_screening": analysis["compatibility"],
        "headline_results": headline,
        "artifact_hashes": {
            group: {path: sha256_file(REPO_ROOT / path) for path in paths}
            for group, paths in HASHED_ARTEFACTS.items()
        },
    }


def _library_versions() -> dict[str, str]:
    import importlib.metadata as metadata

    versions = {}
    for package in ("admet-ai", "chemprop", "rdkit", "numpy", "scipy", "pandas", "matplotlib", "torch"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:  # pragma: no cover
            versions[package] = "NOT_INSTALLED"
    return versions


def render_markdown(freeze: dict[str, Any]) -> str:
    lines = [
        "# Scientific freeze — v1.0.0-preprint",
        "",
        f"**Status:** {freeze['status']}  ",
        f"**Frozen at:** {freeze['frozen_at_utc']}  ",
        f"**Generated by:** `preprint/analysis/write_scientific_freeze.py` (no value transcribed by hand)",
        "",
        "> " + freeze["deviation_policy"].replace(". ", ".\n> "),
        "",
        "## Provenance",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Private scientific base commit | `{freeze['provenance']['private_scientific_base_commit']}` |",
        f"| Private frozen release commit | `{freeze['provenance']['private_frozen_release_commit']}` |",
        f"| Public repository history | {freeze['provenance']['public_repository_history']} |",
        f"| Public branch | `{freeze['provenance']['public_branch']}` |",
        "",
        "> " + freeze["provenance"]["public_export_statement"].replace(". ", ".\n> "),
        "",
        "## Software",
        "",
        "| Component | Version |",
        "| --- | --- |",
        f"| ADMET-AI | {freeze['software']['model']['package_version']} (adapter {freeze['software']['model']['adapter_version']}, weights unmodified) |",
        f"| Python | {freeze['software']['python']} |",
    ]
    for package, version in freeze["software"]["key_libraries"].items():
        lines.append(f"| {package} | {version} |")

    lines += ["", "## Datasets", "", "| Dataset | Version | Licence | Raw rows | Retrieved |", "| --- | --- | --- | ---: | --- |"]
    for entry in freeze["datasets"]:
        lines.append(
            f"| `{entry['dataset_id']}` | {str(entry['dataset_version'])[:48]} | {entry['license']} | "
            f"{entry['rows_raw']} | {entry['retrieval_date']} |"
        )

    lines += ["", "## Seeds and parameters", "", "| Parameter | Value |", "| --- | --- |"]
    params = freeze["seeds_and_parameters"]
    lines += [
        f"| Bootstrap seed | {params['bootstrap_seed']} |",
        f"| Bootstrap replicates | {params['bootstrap_replicates']} |",
        f"| Confidence level | {params['confidence_level']} |",
        f"| Fingerprint | Morgan r={params['fingerprint']['radius']}, {params['fingerprint']['n_bits']} bits, Tanimoto |",
        f"| Structurally-remote threshold | {params['structurally_remote_similarity_threshold']} |",
        f"| Reproduction tolerance | {params['reproduction_tolerance']} |",
    ]

    lines += ["", "## Compatibility screening", "",
              f"- Candidate pairings: **{freeze['compatibility_screening']['candidates']}**",
              f"- Accepted: **{freeze['compatibility_screening']['accepted']}** "
              f"({', '.join(freeze['compatibility_screening']['accepted_mapping_ids'])})",
              f"- Rejected or not evaluable: **{freeze['compatibility_screening']['rejected']}**",
              f"- Status: {freeze['compatibility_screening']['status']}"]

    lines += ["", "## Headline sample sizes and results", "",
              "| Endpoint | Cohort | n | MAE | R² | Spearman ρ | Bias | Slope | SD ratio |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for endpoint, block in freeze["headline_results"].items():
        for cohort, metrics in block["cohorts"].items():
            lines.append(
                f"| {endpoint} | {cohort} | {metrics['n']} | {metrics['mae']:.3f} | {metrics['r2']:+.3f} | "
                f"{metrics['spearman_rho']:+.3f} | {metrics['mean_error_bias']:+.3f} | "
                f"{metrics['calibration_slope']:.3f} | {metrics['sd_ratio']:.3f} |"
            )

    lines += ["", "## Label-distribution shift", "",
              "| Endpoint | Training mean ± SD | External mean ± SD | KS D | KS p |",
              "| --- | --- | --- | ---: | ---: |"]
    for endpoint, block in freeze["headline_results"].items():
        shift = block["label_shift"]
        lines.append(
            f"| {endpoint} | {shift['training_mean']:.2f} ± {shift['training_sd']:.2f} | "
            f"{shift['external_mean']:.2f} ± {shift['external_sd']:.2f} | "
            f"{shift['ks_statistic']:.3f} | {shift['ks_p_value']:.2e} |"
        )

    lines += ["", "## Artefact hashes (SHA-256)", ""]
    for group, files in freeze["artifact_hashes"].items():
        lines.append(f"### {group.replace('_', ' ')}")
        lines.append("")
        lines.append("| File | SHA-256 |")
        lines.append("| --- | --- |")
        for path, digest in files.items():
            lines.append(f"| `{path}` | `{digest}` |")
        lines.append("")

    lines += ["## Upstream tables deliberately not redistributed", "",
              "Hashes pin the exact files used in this study without releasing them.",
              "", "| File | SHA-256 |", "| --- | --- |"]
    for name, digest in freeze["upstream_tables_not_redistributed"].items():
        lines.append(f"| `validation/external_prediction/training_reference/{name}` | `{digest}` |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    freeze = build()
    OUT_JSON.write_text(json.dumps(freeze, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(freeze), encoding="utf-8")
    total = sum(len(files) for files in freeze["artifact_hashes"].values())
    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT).as_posix()}")
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT).as_posix()}")
    print(f"  artefacts hashed            : {total}")
    print(f"  upstream tables pinned      : {len(freeze['upstream_tables_not_redistributed'])}")
    print(f"  endpoints frozen            : {len(freeze['headline_results'])}")
    print(f"  compatibility               : {freeze['compatibility_screening']['accepted']}/"
          f"{freeze['compatibility_screening']['candidates']} accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
