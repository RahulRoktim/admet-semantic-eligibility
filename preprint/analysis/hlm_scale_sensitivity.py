"""Post-freeze sensitivity: does the HLM clearance result depend on the evaluation scale?

The frozen v0.10.2 headline evaluates ``Clearance_Microsome_AZ`` on the native
uL/min/mg scale.  Human liver microsomal clearance is strongly right-skewed --
``build_training_reference_summary`` already bins it logarithmically for
display -- so a coefficient of determination computed on the native scale is
dominated by a small number of high-clearance records.  The frozen sensitivity
cohorts (``ALL_COMPATIBLE_DATA``, ``NO_PARENT_FORM_TRAINING_OVERLAP``,
``STRUCTURALLY_REMOTE_SUBSET``, A-D) all vary *which rows* are evaluated.  None
varies *which scale*, so the frozen artefacts cannot by themselves establish
that the reported negative R-squared is not an artefact of the scale choice.

This module answers that question and nothing else.  It reads the frozen
headline cohort, recomputes the same metric set under monotone
re-expressions of the same values, and writes a separately versioned artefact.
It never rewrites a frozen file and never changes a published number.

Three re-expressions are reported because the choice of non-positive handling
is itself a researcher degree of freedom:

``V1_LOG10_POSITIVE_PAIRS``
    log10 applied to rows where both observation and prediction are strictly
    positive.  Standard, but it drops rows non-randomly: the excluded rows are
    exactly the most severely under-predicted ones, so this variant is biased
    *in the model's favour* and is reported with that caveat.

``V2_ASINH``
    ``asinh(x / s)`` with ``s = 1`` uL/min/mg.  Defined for every real value,
    linear near zero and logarithmic in the tails.  No row is dropped and no
    value is clipped, so this is the primary variant.

``V3_LOG10_FLOORED``
    log10 after flooring both observation and prediction at 10 uL/min/mg, the
    source dataset's own documented reliable exact bound and the effective
    lower bound of the observations.  Keeps every row by clipping rather than
    dropping.

Spearman's rho is invariant under a strictly increasing transform, so V1 and V2
must reproduce the frozen rho exactly.  That identity is asserted as a
correctness gate; V3 is exempt because flooring introduces ties.

Run from the repository root:

    python preprint/analysis/hlm_scale_sensitivity.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from preprint.analysis import core  # noqa: E402

ENDPOINT = "Clearance_Microsome_AZ"

# The source dataset documents 10 uL/min/mg as the lower bound below which an
# exact human liver microsomal value is not considered reliable.  It is also the
# observed minimum of the frozen headline cohort, which makes it the natural
# floor for V3 rather than an arbitrary epsilon.
RELIABLE_LOWER_BOUND = 10.0

ASINH_SCALE = 1.0

OUTPUT_CSV = REPO_ROOT / "preprint/results/hlm_scale_sensitivity.csv"
OUTPUT_MANIFEST = REPO_ROOT / "preprint/results/hlm_scale_sensitivity_manifest.json"

REPORTED_FIELDS = (
    "variant",
    "transform",
    "n",
    "rows_dropped",
    "rows_floored",
    "mae",
    "median_absolute_error",
    "rmse",
    "r2",
    "r2_ci_low",
    "r2_ci_high",
    "pearson_r",
    "spearman_rho",
    "mean_error_bias",
    "calibration_slope",
    "calibration_slope_ci_low",
    "calibration_slope_ci_high",
    "truth_sd",
    "prediction_sd",
    "sd_ratio",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _interval(bootstrap: dict[str, Any], metric: str) -> tuple[float | None, float | None]:
    entry = bootstrap["intervals"].get(metric)
    if entry is None:
        return None, None
    return entry.get("lower"), entry.get("upper")


def _evaluate(
    label: str,
    transform: str,
    y: np.ndarray,
    p: np.ndarray,
    *,
    rows_dropped: int,
    rows_floored: int,
) -> dict[str, Any]:
    point = core.regression_metrics(y.tolist(), p.tolist())
    bootstrap = core.bootstrap_rows(y.tolist(), p.tolist())
    r2_low, r2_high = _interval(bootstrap, "r2")
    slope_low, slope_high = _interval(bootstrap, "calibration_slope")
    return {
        "variant": label,
        "transform": transform,
        "n": point["n"],
        "rows_dropped": rows_dropped,
        "rows_floored": rows_floored,
        "mae": point["mae"],
        "median_absolute_error": point["median_absolute_error"],
        "rmse": point["rmse"],
        "r2": point["r2"],
        "r2_ci_low": r2_low,
        "r2_ci_high": r2_high,
        "pearson_r": point["pearson_r"],
        "spearman_rho": point["spearman_rho"],
        "mean_error_bias": point["mean_error_bias"],
        "calibration_slope": point["calibration_slope"],
        "calibration_slope_ci_low": slope_low,
        "calibration_slope_ci_high": slope_high,
        "truth_sd": point["truth_sd"],
        "prediction_sd": point["prediction_sd"],
        "sd_ratio": point["sd_ratio"],
    }


def build_variants(y: np.ndarray, p: np.ndarray) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    # Control: reproduces the frozen headline numbers from the same inputs.
    results.append(
        _evaluate(
            "A_HEADLINE_NATIVE",
            "identity (uL/min/mg)",
            y,
            p,
            rows_dropped=0,
            rows_floored=0,
        )
    )

    positive = (y > 0) & (p > 0)
    results.append(
        _evaluate(
            "V1_LOG10_POSITIVE_PAIRS",
            "log10(x), strictly positive pairs only",
            np.log10(y[positive]),
            np.log10(p[positive]),
            rows_dropped=int((~positive).sum()),
            rows_floored=0,
        )
    )

    results.append(
        _evaluate(
            "V2_ASINH",
            f"asinh(x / {ASINH_SCALE:g})",
            np.arcsinh(y / ASINH_SCALE),
            np.arcsinh(p / ASINH_SCALE),
            rows_dropped=0,
            rows_floored=0,
        )
    )

    floored_y = np.maximum(y, RELIABLE_LOWER_BOUND)
    floored_p = np.maximum(p, RELIABLE_LOWER_BOUND)
    results.append(
        _evaluate(
            "V3_LOG10_FLOORED",
            f"log10(max(x, {RELIABLE_LOWER_BOUND:g}))",
            np.log10(floored_y),
            np.log10(floored_p),
            rows_dropped=0,
            rows_floored=int((p < RELIABLE_LOWER_BOUND).sum()),
        )
    )
    return results


def assert_rank_invariance(results: Sequence[dict[str, Any]]) -> None:
    """Spearman must survive a strictly increasing transform unchanged."""
    native = next(r for r in results if r["variant"] == "A_HEADLINE_NATIVE")
    for variant in ("V1_LOG10_POSITIVE_PAIRS", "V2_ASINH"):
        row = next(r for r in results if r["variant"] == variant)
        if variant == "V1_LOG10_POSITIVE_PAIRS" and row["rows_dropped"]:
            # Dropping rows changes the sample, so invariance is not required.
            continue
        if abs(row["spearman_rho"] - native["spearman_rho"]) > 1e-9:
            raise AssertionError(
                f"{variant} changed Spearman rho from {native['spearman_rho']!r} "
                f"to {row['spearman_rho']!r}; a monotone transform cannot do that, "
                "so the transform or the pairing is wrong."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="suppress the summary table")
    args = parser.parse_args()

    rows = core.load_prediction_rows()
    selected = core.successful(rows, ENDPOINT, core.HEADLINE_COHORT)
    if not selected:
        raise SystemExit("No frozen headline rows found for " + ENDPOINT)

    y = np.asarray(core.observed(selected), dtype=float)
    p = np.asarray(core.predicted(selected), dtype=float)

    results = build_variants(y, p)
    assert_rank_invariance(results)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORTED_FIELDS)
        writer.writeheader()
        for row in results:
            writer.writerow({key: row[key] for key in REPORTED_FIELDS})

    manifest = {
        "analysis": "hlm_scale_sensitivity",
        "status": "POST-FREEZE SENSITIVITY. Does not supersede any frozen headline value.",
        "endpoint": ENDPOINT,
        "cohort": f"{core.HEADLINE_COHORT} (frozen v0.10.2 headline rows)",
        "question": (
            "Is the frozen native-scale R-squared for human liver microsomal "
            "clearance an artefact of the evaluation scale?"
        ),
        "reliable_lower_bound_uL_min_mg": RELIABLE_LOWER_BOUND,
        "asinh_scale": ASINH_SCALE,
        "bootstrap": {
            "replicates": core.BOOTSTRAP_REPLICATES,
            "seed": core.BOOTSTRAP_SEED,
            "confidence": core.BOOTSTRAP_CONFIDENCE,
            "resampling_unit": "external source row",
        },
        "inputs": {
            str(core.ASAP_PREDICTIONS.relative_to(REPO_ROOT)): _sha256(core.ASAP_PREDICTIONS),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "results": results,
    }
    OUTPUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        header = f"{'variant':<26}{'n':>5}{'R2':>9}{'slope':>9}{'rho':>8}{'sd_ratio':>10}"
        print(header)
        print("-" * len(header))
        for row in results:
            print(
                f"{row['variant']:<26}{row['n']:>5}"
                f"{row['r2']:>9.3f}{row['calibration_slope']:>9.3f}"
                f"{row['spearman_rho']:>8.3f}{row['sd_ratio']:>10.3f}"
            )
        print(f"\nWrote {OUTPUT_CSV.relative_to(REPO_ROOT)}")
        print(f"Wrote {OUTPUT_MANIFEST.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
