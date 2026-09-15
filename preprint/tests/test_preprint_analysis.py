"""Tests for the external-validation preprint analysis.

These cover the calculations the manuscript depends on: metric definitions,
degenerate-input handling, structure aggregation, stereochemical flagging,
bootstrap determinism, and the hard gate that stops the pipeline if any
published v0.10.2 number fails to reproduce.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from preprint.analysis import core
from preprint.analysis import run_preprint_analysis as runner

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_JSON = REPO_ROOT / "preprint/results/preprint_analysis.json"
V0102_METRICS = REPO_ROOT / "validation/reports/v0102_external_metrics.json"


# --------------------------------------------------------------------------
# Metric definitions
# --------------------------------------------------------------------------


def test_perfect_prediction_gives_unit_slope_and_unit_sd_ratio():
    y = [1.0, 2.0, 3.0, 4.0]
    metrics = core.regression_metrics(y, y)
    assert metrics["r2"] == pytest.approx(1.0)
    assert metrics["mae"] == pytest.approx(0.0)
    assert metrics["mean_error_bias"] == pytest.approx(0.0)
    assert metrics["calibration_slope"] == pytest.approx(1.0)
    assert metrics["sd_ratio"] == pytest.approx(1.0)


def test_r2_is_negative_when_error_exceeds_cohort_variance():
    y = [1.0, 2.0, 3.0]
    p = [10.0, 11.0, 12.0]
    metrics = core.regression_metrics(y, p)
    assert metrics["r2"] < 0
    # Rank information is fully preserved even though R2 is negative: this is
    # the exact situation the manuscript describes for microsomal clearance.
    assert metrics["spearman_rho"] == pytest.approx(1.0)
    assert metrics["mean_error_bias"] == pytest.approx(9.0)


def test_calibration_slope_detects_range_compression():
    y = [0.0, 10.0, 20.0, 30.0, 40.0]
    compressed = [20.0, 21.0, 22.0, 23.0, 24.0]
    metrics = core.regression_metrics(y, compressed)
    assert metrics["calibration_slope"] == pytest.approx(0.1)
    assert metrics["sd_ratio"] == pytest.approx(0.1)


def test_constant_prediction_baseline_yields_no_nan():
    """Constant baselines must return None, not NaN, or the JSON write fails."""
    y = [1.0, 5.0, 9.0]
    metrics = core.regression_metrics(y, [3.0, 3.0, 3.0])
    assert metrics["pearson_r"] is None
    assert metrics["spearman_rho"] is None
    assert metrics["prediction_sd"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["calibration_slope"] == pytest.approx(0.0)


def test_metrics_reject_non_finite_and_misaligned_input():
    with pytest.raises(ValueError):
        core.regression_metrics([1.0, 2.0], [1.0, float("nan")])
    with pytest.raises(ValueError):
        core.regression_metrics([1.0, 2.0], [1.0])
    with pytest.raises(ValueError):
        core.regression_metrics([], [])


# --------------------------------------------------------------------------
# Structure aggregation
# --------------------------------------------------------------------------


def _row(inchikey: str, observation: float, prediction: float) -> dict[str, str]:
    return {
        "inchikey": inchikey,
        "ground_truth_normalized_value": str(observation),
        "normalized_prediction": str(prediction),
    }


def test_structure_aggregation_takes_median_observation_per_structure():
    rows = [_row("A", 10.0, 5.0), _row("A", 20.0, 5.0), _row("A", 60.0, 5.0), _row("B", 1.0, 2.0)]
    y, p, clusters = core.aggregate_by_structure(rows)
    assert clusters == 2
    assert sorted(y) == [1.0, 20.0]
    assert sorted(p) == [2.0, 5.0]


def test_structure_aggregation_refuses_divergent_predictions():
    rows = [_row("A", 10.0, 5.0), _row("A", 20.0, 7.0)]
    with pytest.raises(ValueError):
        core.aggregate_by_structure(rows)


# --------------------------------------------------------------------------
# Stereochemical flagging
# --------------------------------------------------------------------------


def test_enhanced_stereo_regex_distinguishes_absolute_from_or_and_groups():
    assert core._AMBIGUOUS_STEREO.search("&1:7") is not None
    assert core._AMBIGUOUS_STEREO.search("o1:3") is not None
    # "a:" marks an absolute assignment and leaves the structure unambiguous.
    assert core._AMBIGUOUS_STEREO.search("a:16") is None


def test_biogen_rows_are_unambiguous_by_construction():
    row = {"external_dataset_id": "biogen-adme-fang-3521", "external_row_id": "X:hPPB"}
    assert core.is_stereo_unambiguous(row, {}) is True


def test_asap_stereo_flags_cover_the_source_snapshot():
    flags = core.asap_stereo_ambiguity()
    assert len(flags) == 560
    # 158 records carry an AND-group only and 77 carry an OR-group only; none
    # carry both. The remaining 325 are unambiguous (81 absolute-marked plus
    # 244 with no enhanced-stereo block). Counting marker tokens rather than
    # records gives 245 and is not the quantity reported in the manuscript.
    assert sum(flags.values()) == 235


# --------------------------------------------------------------------------
# Bootstrap behaviour
# --------------------------------------------------------------------------


def test_row_bootstrap_is_deterministic_under_a_fixed_seed():
    rng = np.random.default_rng(7)
    y = rng.normal(size=60).tolist()
    p = (np.asarray(y) * 0.5 + rng.normal(scale=0.2, size=60)).tolist()
    first = core.bootstrap_rows(y, p, replicates=200)
    second = core.bootstrap_rows(y, p, replicates=200)
    assert first["intervals"]["mae"] == second["intervals"]["mae"]
    assert first["intervals"]["r2"] == second["intervals"]["r2"]


def test_cluster_bootstrap_resamples_structures_not_rows():
    rows = [_row("A", 1.0, 1.1), _row("A", 1.2, 1.1), _row("B", 5.0, 4.8), _row("C", 9.0, 9.4)]
    result = core.bootstrap_structures(rows, replicates=50)
    assert result["clusters"] == 3
    assert result["resampling_unit"] == "unique structure (InChIKey cluster)"


# --------------------------------------------------------------------------
# Reproduction gate and generated artefacts
# --------------------------------------------------------------------------


def test_reproduction_gate_passes_on_the_frozen_artifacts():
    rows = core.load_prediction_rows()
    result = runner.reproduce_headline(rows)
    assert result["status"] == "ALL_PUBLISHED_METRICS_REPRODUCED"


def test_reproduction_gate_aborts_when_a_prediction_is_altered():
    rows = core.load_prediction_rows()
    mutated = [dict(row) for row in rows]
    for row in mutated:
        if row["prediction_status"] == "SUCCESS":
            row["normalized_prediction"] = str(float(row["normalized_prediction"]) + 1.0)
            break
    with pytest.raises(SystemExit):
        runner.reproduce_headline(mutated)


@pytest.mark.skipif(not ANALYSIS_JSON.is_file(), reason="analysis has not been run yet")
def test_generated_analysis_matches_published_headline_values():
    generated = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    published = json.loads(V0102_METRICS.read_text(encoding="utf-8"))["endpoints"]
    for endpoint in core.ENDPOINTS:
        produced = generated["results"][endpoint]["cohorts"]["A_HEADLINE"]["metrics"]
        reference = published[endpoint]["cohorts"]["NO_EXACT_TRAINING_OVERLAP"]["metrics"]
        for key in ("n", "mae", "rmse", "r2", "pearson_r", "spearman_rho", "mean_error_bias"):
            assert produced[key] == pytest.approx(reference[key], abs=1e-9), f"{endpoint}.{key} drifted"


@pytest.mark.skipif(not ANALYSIS_JSON.is_file(), reason="analysis has not been run yet")
def test_generated_analysis_contains_no_non_finite_values():
    text = ANALYSIS_JSON.read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, float):
            assert math.isfinite(node)

    walk(json.loads(text))


@pytest.mark.skipif(not ANALYSIS_JSON.is_file(), reason="analysis has not been run yet")
def test_low_clearance_cohort_adds_every_excluded_row_and_keeps_r2_negative():
    generated = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    cohorts = generated["results"]["Clearance_Microsome_AZ"]["cohorts"]
    headline = cohorts["A_HEADLINE"]["metrics"]
    combined = cohorts["B_HEADLINE_PLUS_LOW_CLEARANCE"]
    assert combined["rows_added"] == 36
    assert combined["rows_available_below_bound"] == 36
    assert combined["metrics"]["n"] == headline["n"] + 36
    # The manuscript claim is that range restriction exaggerated but did not
    # create the negative coefficient of determination or the negative bias.
    assert combined["metrics"]["r2"] < 0
    assert combined["metrics"]["mean_error_bias"] < -50
    assert combined["metrics"]["calibration_slope"] < 0.1


@pytest.mark.skipif(not ANALYSIS_JSON.is_file(), reason="analysis has not been run yet")
def test_admet_ai_outperforms_both_baselines_on_every_accepted_endpoint():
    generated = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    for endpoint in core.ENDPOINTS:
        cohort = generated["results"][endpoint]["cohorts"]["A_HEADLINE"]
        model = cohort["metrics"]
        mean_baseline = cohort["baselines"]["training_mean"]
        nn_baseline = cohort["baselines"]["nearest_neighbour_morgan_tanimoto"]
        assert model["mae"] < mean_baseline["mae"], endpoint
        assert model["mae"] < nn_baseline["mae"], endpoint
        assert model["r2"] > mean_baseline["r2"], endpoint
        assert model["r2"] > nn_baseline["r2"], endpoint
        assert cohort["baselines"]["nearest_neighbour_unresolved_rows"] == 0, endpoint


@pytest.mark.skipif(not ANALYSIS_JSON.is_file(), reason="analysis has not been run yet")
def test_compatibility_screening_counts_are_stable():
    generated = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    compatibility = generated["compatibility"]
    assert compatibility["candidates"] == 12
    assert compatibility["accepted"] == 3
    assert compatibility["rejected"] == 9
    assert set(compatibility["accepted_mapping_ids"]) == {
        "ASAP_HLM_MICROSOME",
        "ASAP_LOGD_LIPOPHILICITY",
        "BIOGEN_HPPB_PPBR",
    }


# --------------------------------------------------------------------------
# Manuscript binding
# --------------------------------------------------------------------------


@pytest.mark.skipif(not ANALYSIS_JSON.is_file(), reason="analysis has not been run yet")
def test_every_manuscript_number_matches_the_generated_results():
    """Binds the manuscript to the analysis so neither can drift alone."""
    from preprint.analysis import verify_manuscript_claims as verifier

    # Explicit empty argv: main() parses sys.argv by default, which under
    # pytest contains pytest's own arguments.
    assert verifier.main([]) == 0


@pytest.mark.skipif(not ANALYSIS_JSON.is_file(), reason="analysis has not been run yet")
def test_claim_verifier_is_not_vacuous():
    """A perturbed result must make exactly the corresponding claim fail."""
    import json as _json

    from preprint.analysis import verify_manuscript_claims as verifier

    text = verifier.normalise(verifier.MANUSCRIPT.read_text(encoding="utf-8"))
    generated = _json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    generated["results"]["Clearance_Microsome_AZ"]["cohorts"]["A_HEADLINE"]["metrics"]["r2"] = -0.2
    failing = [
        description
        for description, needle in verifier.build_claims(generated)
        if verifier.normalise(needle) not in text
    ]
    assert failing == ["clearance R2"]


# --------------------------------------------------------------------------
# Level 1 / Level 2 licensing boundary
# --------------------------------------------------------------------------


def test_derived_summary_contains_no_upstream_structures_or_targets():
    """The published summary must not redistribute the upstream reference tables."""
    summary = core.load_derived_training_summary()
    text = json.dumps(summary)
    assert summary["contains_upstream_structures"] is False
    assert summary["contains_upstream_target_values"] is False
    assert "maximum_training_similarity_smiles" not in text
    assert "source_target" not in text
    # No SMILES-shaped strings anywhere in the summary.
    import re as _re

    suspects = [
        token
        for token in _re.findall(r'"[^"]{12,}"', text)
        if _re.search(r"\[C@|c1cc|\)\(|CC\(=O\)", token)
    ]
    assert suspects == []


@pytest.mark.skipif(not ANALYSIS_JSON.is_file(), reason="analysis has not been run yet")
def test_level_one_runs_without_the_upstream_training_tables(monkeypatch, tmp_path):
    """Level 1 must reproduce the published results with the upstream tables absent."""
    from preprint.analysis import run_preprint_analysis as runner_module

    missing = tmp_path / "absent_training_reference"
    monkeypatch.setattr(core, "TRAINING_DIR", missing)
    assert core.training_reference_available() is False

    published = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    summary = core.load_derived_training_summary()
    rows = core.load_prediction_rows()
    low_clearance = core.load_low_clearance_rows()
    for row in low_clearance:
        row.update(summary["low_clearance_annotation"][row["external_row_id"]])

    rebuilt = runner_module.build_results(rows, low_clearance, summary)
    assert rebuilt == published["results"]


def test_upstream_tables_are_only_read_by_the_summary_builder():
    """Only the Level 2 builder may call into the non-redistributed reference tables.

    ``core.py`` defines the readers; no Level 1 module may call them.
    """
    level_one_modules = [
        REPO_ROOT / "preprint/analysis/run_preprint_analysis.py",
        REPO_ROOT / "preprint/analysis/verify_manuscript_claims.py",
        REPO_ROOT / "preprint/analysis/write_checksums.py",
        REPO_ROOT / "preprint/analysis/hlm_low_clearance_sensitivity.py",
        REPO_ROOT / "preprint/figures/make_figures.py",
    ]
    forbidden = ("load_training_targets", "load_training_index", "combine_training_indexes", "TRAINING_DIR")
    offenders = []
    for path in level_one_modules:
        source = path.read_text(encoding="utf-8")
        for name in forbidden:
            if name in source:
                offenders.append(f"{path.name}: {name}")
    assert offenders == []


# --------------------------------------------------------------------------
# Public release package
# --------------------------------------------------------------------------


def test_release_manifest_classifies_every_file_and_excludes_the_reference_tables():
    """The invariant is that no excluded file is ever released.

    The *count* of excluded files is environment-dependent: a development
    working copy holds all ten reference tables, while a public clean clone
    holds none. Asserting a count would make a correctly enforced boundary look
    like a failure in the public repository, so the boundary itself is asserted
    instead.
    """
    from preprint.analysis import release_package

    manifest = json.loads((REPO_ROOT / "preprint/release_manifest.json").read_text(encoding="utf-8"))
    excluded = {entry["path"] for entry in manifest["files"] if not entry["in_public_release"]}
    released = {entry["path"] for entry in manifest["files"] if entry["in_public_release"]}

    # The boundary must be declared, whether or not any file currently matches.
    assert manifest["excluded_patterns"]
    assert release_package.EXCLUDED_PATTERNS

    # Nothing under the excluded path may ever be released.
    assert not excluded & released
    assert all(path.startswith("validation/external_prediction/training_reference/") for path in excluded)
    assert not any(
        path.startswith("validation/external_prediction/training_reference/") for path in released
    )

    assert all(entry["category"] in manifest["categories"] for entry in manifest["files"])
    # Every classified file carries a licence statement and a hash.
    assert all(entry["licence"] and entry["sha256"] for entry in manifest["files"])
    assert release_package.check(None) == 0


def test_release_check_fails_when_an_excluded_file_is_packaged(tmp_path):
    """Negative control: a leaked reference table must fail the release check."""
    import zipfile as _zipfile

    from preprint.analysis import release_package

    archive = tmp_path / "leaky.zip"
    with _zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("preprint/manuscript/manuscript.md", "ok")
        bundle.writestr("validation/external_prediction/training_reference/PPBR_AZ.csv", "leaked")
    assert release_package.check(archive) == 1

    clean = tmp_path / "clean.zip"
    with _zipfile.ZipFile(clean, "w") as bundle:
        bundle.writestr("preprint/manuscript/manuscript.md", "ok")
    assert release_package.check(clean) == 0
