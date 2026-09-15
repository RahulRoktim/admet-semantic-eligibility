"""Check every numeric claim in the manuscript against the generated results.

Each claim below resolves a value from ``preprint_analysis.json`` (or from the
frozen source artefacts), formats it exactly as the manuscript writes it, and
asserts that string is present. If a result changes and the manuscript is not
updated, or the manuscript is edited to a value the analysis does not support,
this fails.

It also enforces the claim boundary for this preprint: a list of forbidden
phrases must not appear anywhere in the manuscript.

    PYTHONPATH=backend python preprint/analysis/verify_manuscript_claims.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for candidate in (str(REPO_ROOT), str(REPO_ROOT / "backend")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

MANUSCRIPT = REPO_ROOT / "preprint/manuscript/manuscript.md"
ANALYSIS = REPO_ROOT / "preprint/results/preprint_analysis.json"
COMPATIBILITY = REPO_ROOT / "validation/external_prediction/endpoint_compatibility.csv"
ASAP_SOURCE = REPO_ROOT / "validation/external_prediction/source_snapshots/asap_antiviral_admet_2025_unblinded.csv"
LOW_CLEARANCE_MANIFEST = REPO_ROOT / "preprint/results/hlm_low_clearance_manifest.json"

HLM = "Clearance_Microsome_AZ"
LOGD = "Lipophilicity_AstraZeneca"
PPB = "PPBR_AZ"

# Phrases that would take this preprint outside its declared scope. The
# comparability engine, the conflict engine, human adjudication and any
# platform-level validation claim are explicitly not part of this work.
FORBIDDEN = [
    "cohen",
    "kappa",
    "κ",
    "conflict engine",
    "comparability engine",
    "inter-rater reliability",
    "human adjudicat",
    "expert adjudicat",
    "validated ontology",
    "validated endpoint ontology",
    "validated platform",
    "clinically validated",
    "regulatory approval",
    "all 41",
    "all forty-one",
    "across all outputs",
]

# Phrases that must be present: the disclosures Phase 7 requires.
REQUIRED_DISCLOSURES = [
    "pre-specified",
    "fail-closed",
    "auditable",
    "not externally validated",
    "conservative rather than exact",
    "enhanced-stereo",
    "structure-clustered bootstrap",
    "not chemically representative",
    "source sparsity",
    "not clinical validation",
]


def load_analysis() -> dict:
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


def cohort(analysis: dict, endpoint: str, name: str = "A_HEADLINE") -> dict:
    return analysis["results"][endpoint]["cohorts"][name]


def build_claims(analysis: dict) -> list[tuple[str, str]]:
    """Return (claim description, exact string that must appear) pairs."""
    claims: list[tuple[str, str]] = []

    def add(description: str, text: str) -> None:
        claims.append((description, text))

    # --- compatibility screening -------------------------------------------
    compatibility = list(csv.DictReader(COMPATIBILITY.open(encoding="utf-8-sig", newline="")))
    accepted = [r for r in compatibility if r["numerical_validation_allowed"].lower() == "true"]
    # The compatibility counts are asserted directly against the frozen matrix;
    # the manuscript states them in prose, which is checked separately.
    assert analysis["compatibility"]["candidates"] == len(compatibility) == 12
    assert analysis["compatibility"]["accepted"] == len(accepted) == 3
    assert analysis["compatibility"]["rejected"] == len(compatibility) - len(accepted) == 9
    add("candidate pairings stated", "Twelve candidate pairings were assessed")
    add("accepted pairings stated", "Three were accepted")
    add("rejected pairings stated", "Nine were rejected")
    add("screening summary stated", "nine of twelve candidate pairings")

    # --- headline metrics ---------------------------------------------------
    for endpoint, label in ((HLM, "clearance"), (LOGD, "logD"), (PPB, "plasma protein binding")):
        block = cohort(analysis, endpoint)
        metrics = block["metrics"]
        intervals = block["bootstrap_rows"]["intervals"]
        add(f"{label} n", f"n = {metrics['n']}")
        add(f"{label} R2", f"{metrics['r2']:.3f}".replace("-", "−") if False else f"{metrics['r2']:.3f}")
        add(f"{label} R2 CI lower", f"{intervals['r2']['lower']:.3f}")
        add(f"{label} R2 CI upper", f"{intervals['r2']['upper']:.3f}")
        add(f"{label} spearman", f"{metrics['spearman_rho']:.3f}")
        add(f"{label} calibration slope", f"{metrics['calibration_slope']:.3f}")
        add(f"{label} sd ratio", f"{metrics['sd_ratio']:.3f}")
        add(f"{label} unique structures", str(block["unique_structures"]))

    hlm = cohort(analysis, HLM)
    add("clearance MAE", f"{hlm['metrics']['mae']:.1f}")
    add("clearance median AE", f"{hlm['metrics']['median_absolute_error']:.1f}")
    add("clearance RMSE", f"{hlm['metrics']['rmse']:.1f}")
    add("clearance pearson", f"{hlm['metrics']['pearson_r']:.3f}")
    add("clearance bias", f"{abs(hlm['metrics']['mean_error_bias']):.1f}")
    add("clearance prediction sd", f"{hlm['metrics']['prediction_sd']:.1f}")
    add("clearance truth sd", f"{hlm['metrics']['truth_sd']:.1f}")

    logd = cohort(analysis, LOGD)
    add("logD MAE", f"{logd['metrics']['mae']:.3f}")
    add("logD bias", f"{logd['metrics']['mean_error_bias']:.3f}")

    ppb = cohort(analysis, PPB)
    add("PPB MAE", f"{ppb['metrics']['mae']:.1f}")
    add("PPB bias", f"{ppb['metrics']['mean_error_bias']:.1f}")

    # Distribution caveat quoted for the plasma protein binding acceptance.
    import numpy as _np

    from preprint.analysis import core as _core

    ppb_rows = _core.successful(_core.load_prediction_rows(), PPB, _core.HEADLINE_COHORT)
    bound = _np.asarray(_core.observed(ppb_rows), dtype=float)
    add("PPB median percent bound", f"median {_np.median(bound):.1f}% bound")
    add("PPB fraction above 90 percent", f"{100 * float((bound > 90).mean()):.1f}% of records above 90%")

    # --- baselines ----------------------------------------------------------
    for endpoint, label in ((HLM, "clearance"), (LOGD, "logD"), (PPB, "plasma protein binding")):
        baselines = cohort(analysis, endpoint)["baselines"]
        add(f"{label} training-mean baseline R2", f"{baselines['training_mean']['r2']:.3f}")
        add(f"{label} 1-NN baseline R2", f"{baselines['nearest_neighbour_morgan_tanimoto']['r2']:.3f}")
    hlm_base = hlm["baselines"]
    add("clearance mean baseline MAE", f"{hlm_base['training_mean']['mae']:.1f}")
    add("clearance 1-NN baseline MAE", f"{hlm_base['nearest_neighbour_morgan_tanimoto']['mae']:.1f}")
    for endpoint in (HLM, LOGD, PPB):
        nn = cohort(analysis, endpoint)["baselines"]["nearest_neighbour_morgan_tanimoto"]
        add(f"{endpoint} 1-NN spearman", f"{nn['spearman_rho']:.3f}")

    # --- label shift --------------------------------------------------------
    for endpoint, label in ((HLM, "clearance"), (LOGD, "logD"), (PPB, "plasma protein binding")):
        shift = cohort(analysis, endpoint)["label_shift"]
        digits = 2 if endpoint == LOGD else 1
        add(f"{label} KS D", f"{shift['ks_statistic']:.3f}")
        add(f"{label} training mean", f"{shift['training_mean']:.{digits}f}")
        add(f"{label} training sd", f"{shift['training_sd']:.{digits}f}")
        add(f"{label} external mean", f"{shift['external_mean']:.{digits}f}")
        add(f"{label} external sd", f"{shift['external_sd']:.{digits}f}")

    # --- similarity association --------------------------------------------
    for endpoint, label in ((HLM, "clearance"), (LOGD, "logD"), (PPB, "plasma protein binding")):
        association = cohort(analysis, endpoint)["similarity_error_association"]
        add(f"{label} similarity-error rho", f"{abs(association['spearman_rho']):.3f}")
        add(f"{label} median similarity", f"{association['median_maximum_similarity']:.3f}")

    # --- sensitivity cohorts ------------------------------------------------
    combined = cohort(analysis, HLM, "B_HEADLINE_PLUS_LOW_CLEARANCE")
    add("cohort B rows added", str(combined["rows_added"]))
    add("cohort B n", f"n = {combined['metrics']['n']}")
    add("cohort B R2", f"{combined['metrics']['r2']:.3f}")
    add("cohort B bias", f"{abs(combined['metrics']['mean_error_bias']):.1f}")
    add("cohort B spearman", f"{combined['metrics']['spearman_rho']:.3f}")
    add("cohort B slope", f"{combined['metrics']['calibration_slope']:.3f}")

    low = json.loads(LOW_CLEARANCE_MANIFEST.read_text(encoding="utf-8"))
    add("low-clearance negatives retained", str(low["negative_predictions_retained"]))
    add("low-clearance prediction min", f"{low['prediction_min']:.1f}")
    add("low-clearance prediction max", f"{low['prediction_max']:.1f}")
    add("low-clearance ground truth max", f"{low['ground_truth_max']:.1f}")

    for endpoint, label in ((HLM, "clearance"), (LOGD, "logD"), (PPB, "plasma protein binding")):
        aggregated = cohort(analysis, endpoint, "C_STRUCTURE_AGGREGATED")["metrics"]
        add(f"{label} aggregated R2", f"{aggregated['r2']:.3f}")
    for endpoint, label in ((HLM, "clearance"), (LOGD, "logD")):
        stereo = cohort(analysis, endpoint, "D_STEREO_UNAMBIGUOUS")
        add(f"{label} stereo-unambiguous n", str(stereo["metrics"]["n"]))
        add(f"{label} stereo-unambiguous R2", f"{stereo['metrics']['r2']:.3f}")
    for endpoint, label in ((HLM, "clearance"), (LOGD, "logD"), (PPB, "plasma protein binding")):
        remote = cohort(analysis, endpoint, "STRUCTURALLY_REMOTE_SUBSET")["metrics"]
        add(f"{label} remote subset R2", f"{remote['r2']:.3f}")
        add(f"{label} remote subset n", str(remote["n"]))
    for endpoint, label in ((HLM, "clearance"), (LOGD, "logD"), (PPB, "plasma protein binding")):
        clustered = cohort(analysis, endpoint)["bootstrap_structures"]["intervals"]["r2"]
        add(f"{label} clustered R2 lower", f"{clustered['lower']:.3f}")
        add(f"{label} clustered R2 upper", f"{clustered['upper']:.3f}")

    # --- source counts ------------------------------------------------------
    for endpoint in (HLM, LOGD, PPB):
        counts = analysis["results"][endpoint]["source_row_counts"]
        if endpoint == PPB:
            add("PPB source rows", f"{counts['source_rows']:,}")
            add("PPB missing rows", f"{counts['excluded_missing']:,}")
        if endpoint == HLM:
            add("HLM censored rows", str(counts["excluded_censoring_or_bound"]))

    # --- ASAP stereochemistry -----------------------------------------------
    asap = list(csv.DictReader(ASAP_SOURCE.open(encoding="utf-8-sig", newline="")))
    ambiguous_pattern = re.compile(r"[o&]\d*:")
    and_only = or_only = absolute_only = none = 0
    for row in asap:
        cx = row["CXSMILES"]
        block = cx.split("|", 1)[1] if "|" in cx else ""
        has_and = bool(re.search(r"&\d*:", block))
        has_or = bool(re.search(r"o\d*:", block))
        if has_and and not has_or:
            and_only += 1
        elif has_or and not has_and:
            or_only += 1
        elif has_and and has_or:
            raise AssertionError("record carries both AND and OR groups; manuscript text assumes none do")
        elif re.search(r"a\d*:", block):
            absolute_only += 1
        else:
            none += 1
    ambiguous = sum(1 for row in asap if ambiguous_pattern.search(row["CXSMILES"].split("|", 1)[1] if "|" in row["CXSMILES"] else ""))
    # Congenericity and the Caco-2 chemical-remoteness figure, both quoted in
    # the manuscript, are re-derived here rather than trusted.
    from rdkit import Chem, RDLogger
    from rdkit.Chem.Scaffolds import MurckoScaffold

    RDLogger.DisableLog("rdApp.*")
    scaffolds: dict[str, int] = {}
    for row in asap:
        mol = Chem.MolFromSmiles(row["CXSMILES"])
        if mol is not None:
            key = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
            scaffolds[key] = scaffolds.get(key, 0) + 1
    add("ASAP scaffold count", f"{len(scaffolds)} Bemis")
    add("ASAP largest scaffold", f"largest scaffold {max(scaffolds.values())} records")

    overlap = json.loads((REPO_ROOT / "validation/reports/v0102_external_overlap.json").read_text(encoding="utf-8"))
    caco2_similarity = overlap["endpoints"]["Caco2_Wang"]["median_maximum_similarity"]
    add("Caco-2 median similarity", f"{caco2_similarity:.3f}")

    add("ASAP record count", f"{len(asap)} records")
    add("ASAP ambiguous stereo records", str(ambiguous))
    add("ASAP AND-only records", str(and_only))
    add("ASAP OR-only records", str(or_only))
    add("ASAP absolute-marker records", str(absolute_only))
    add("ASAP no-stereo-block records", str(none))
    add("ASAP unambiguous total", str(absolute_only + none))

    return claims


def normalise(text: str) -> str:
    """Make prose comparable to formatted numbers.

    The manuscript uses typographic minus signs and wraps lines, neither of
    which is a scientific difference. Both are normalised before matching so
    that a real value change is the only thing that can fail a claim.
    """
    for dash in ("−", "‑", "–"):
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text)


#: Fields that require the author and cannot be filled in from the repository.
#: They are listed in USER_INPUT_REQUIRED.md. Reported on every run; fatal only
#: under --submission-ready, which is the gate before ChemRxiv submission.
PLACEHOLDER_PATTERN = re.compile(r"\[\[([A-Z_]+)\]\]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--submission-ready",
        action="store_true",
        help="also fail if any [[PLACEHOLDER]] remains; use immediately before submission",
    )
    args = parser.parse_args(argv)
    if not ANALYSIS.is_file():
        raise SystemExit("Run preprint/analysis/run_preprint_analysis.py first.")
    raw = MANUSCRIPT.read_text(encoding="utf-8")
    text = normalise(raw)
    lowered = text.lower()

    failures: list[str] = []

    for description, needle in build_claims(load_analysis()):
        if normalise(needle) not in text:
            failures.append(f"MISSING VALUE  {description}: expected '{needle}' in manuscript")

    for phrase in FORBIDDEN:
        if phrase.lower() in lowered:
            for number, line in enumerate(raw.splitlines(), start=1):
                if phrase.lower() in normalise(line).lower():
                    failures.append(f"FORBIDDEN CLAIM line {number}: '{phrase}' -> {line.strip()[:110]}")

    for phrase in REQUIRED_DISCLOSURES:
        if phrase.lower() not in lowered:
            failures.append(f"MISSING DISCLOSURE: '{phrase}'")

    if failures:
        print(f"FAILED: {len(failures)} problem(s)\n")
        for failure in failures:
            print(f"  {failure}")
        return 1

    claim_count = len(build_claims(load_analysis()))
    print(f"PASS: {claim_count} numeric claims verified against preprint_analysis.json")
    print(f"PASS: {len(FORBIDDEN)} forbidden phrases absent")
    print(f"PASS: {len(REQUIRED_DISCLOSURES)} required disclosures present")

    placeholders = sorted(set(PLACEHOLDER_PATTERN.findall(raw)))
    if placeholders:
        label = "FAIL" if args.submission_ready else "PENDING"
        print(f"{label}: {len(placeholders)} author-supplied field(s) still unresolved -> {', '.join(placeholders)}")
        print("      see USER_INPUT_REQUIRED.md")
        if args.submission_ready:
            return 1
    else:
        print("PASS: no unresolved author-supplied placeholders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
