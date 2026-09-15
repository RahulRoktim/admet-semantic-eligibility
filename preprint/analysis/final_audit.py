"""Final release audit of the manuscript and package.

Runs every check required before release and writes both a machine-readable and
a human-readable report. Exits non-zero if any check fails.

    PYTHONPATH=backend python preprint/analysis/final_audit.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for candidate in (str(REPO_ROOT), str(REPO_ROOT / "backend")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from preprint.analysis import (  # noqa: E402
    check_repository_urls,
    core,
    release_package,
    verify_manuscript_claims,
)

MANUSCRIPT = REPO_ROOT / "preprint/manuscript/manuscript.md"
ANALYSIS = REPO_ROOT / "preprint/results/preprint_analysis.json"
OUT_JSON = REPO_ROOT / "preprint/results/final_audit.json"
OUT_MD = REPO_ROOT / "preprint/FINAL_AUDIT.md"

#: Values known to have been wrong at some point during preparation. They must
#: never reappear in the manuscript.
RETIRED_VALUES = {
    "245 of 560": "stereochemistry: marker-token count, not record count; correct value is 235",
    "245 records": "stereochemistry: marker-token count, not record count; correct value is 235",
    "92.4%": "plasma protein binding median asserted before computation; correct value is 91.8%",
    "median 92.4": "plasma protein binding median asserted before computation; correct value is 91.8%",
}

#: Causal phrasing that the analyses do not support. The study is descriptive.
CAUSAL_PATTERNS = [
    r"\bcaused by\b",
    r"\bcauses\b",
    r"\bbecause the model (?:is|was) trained\b",
    r"\bproves that\b",
    r"\bdemonstrates causation\b",
    r"\bcausal(?:ly)?\b",
]
CAUSAL_ALLOWED = {
    # Permitted: an explicit denial of causal interpretation.
    "not causal",
    "descriptive, not causal",
    "does not establish",
}


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def add(self, name: str, passed: bool, detail: str, evidence: Any = None) -> None:
        self.checks.append(
            {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail, "evidence": evidence}
        )

    @property
    def failed(self) -> list[dict[str, Any]]:
        return [c for c in self.checks if c["status"] == "FAIL"]


def run(audit: Audit) -> dict[str, Any]:
    raw = MANUSCRIPT.read_text(encoding="utf-8")
    text = verify_manuscript_claims.normalise(raw)
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))

    # 1. Every number against generated artefacts.
    claims = verify_manuscript_claims.build_claims(analysis)
    missing = [d for d, needle in claims if verify_manuscript_claims.normalise(needle) not in text]
    audit.add(
        "every_number_matches_generated_artefacts",
        not missing,
        f"{len(claims) - len(missing)}/{len(claims)} numeric claims verified against preprint_analysis.json",
        missing or None,
    )

    # 2/3/4. Citations: resolvable, all used, none uncited.
    body, _, bibliography = raw.partition("## References")
    cited = {int(n) for m in re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", body) for n in m.group(1).split(",")}
    defined = {int(m.group(1)) for m in re.finditer(r"^(\d+)\. ", bibliography, flags=re.M)}
    audit.add("every_citation_resolves_to_bibliography", not (cited - defined),
              f"{len(cited)} citations used, {len(defined)} references defined",
              sorted(cited - defined) or None)
    audit.add("no_uncited_references", not (defined - cited),
              "every reference is cited at least once", sorted(defined - cited) or None)
    audit.add("bibliography_complete", len(defined) == 23,
              f"{len(defined)} references (expected 23)")

    # 5. Placeholders: expected before release, reported not failed.
    placeholders = sorted(set(re.findall(r"\[\[([A-Z_]+)\]\]", raw)))
    audit.add("placeholders_are_declared_author_fields", True,
              f"{len(placeholders)} unresolved author-supplied field(s); tracked in USER_INPUT_REQUIRED.md",
              placeholders or None)

    # 6. Retired / outdated numbers.
    found_retired = {value: reason for value, reason in RETIRED_VALUES.items() if value.lower() in text.lower()}
    audit.add("no_retired_or_outdated_values", not found_retired,
              "known-wrong values absent (245-vs-235 stereochemistry; 92.4% PPB median)",
              found_retired or None)

    # 7. Out-of-scope claims.
    forbidden = [p for p in verify_manuscript_claims.FORBIDDEN if p.lower() in text.lower()]
    audit.add("no_out_of_scope_claims", not forbidden,
              "no conflict-engine, comparability-engine, kappa, human-adjudication or "
              "platform-validation claim; no extrapolation to all ADMET-AI outputs",
              forbidden or None)

    # 8. Required disclosures.
    absent = [p for p in verify_manuscript_claims.REQUIRED_DISCLOSURES if p.lower() not in text.lower()]
    audit.add("required_disclosures_present", not absent,
              f"{len(verify_manuscript_claims.REQUIRED_DISCLOSURES)} required disclosures checked",
              absent or None)

    # 9. Compatibility decisions never described as independently validated.
    validated_claims = [
        phrase for phrase in ("independently validated", "externally validated compatibility",
                              "validated compatibility", "compatibility decisions were validated")
        if phrase.lower() in text.lower()
    ]
    audit.add("compatibility_not_claimed_validated", not validated_claims,
              "compatibility decisions described as pre-specified/auditable/fail-closed, not validated",
              validated_claims or None)

    # 10. LogD assay methodology never claimed known.
    logd_ok = "neither source documents whether the value was obtained by" in text
    logd_overclaim = [p for p in ("logD was determined by", "logD assay method is", "shake-flask was used")
                      if p.lower() in text.lower()]
    audit.add("logd_assay_method_not_claimed_known", logd_ok and not logd_overclaim,
              "logD recorded as eligible under the prespecified protocol with unresolved assay-method metadata",
              logd_overclaim or None)
    audit.add("logd_status_wording_present",
              "eligible under\nthe prespecified protocol, with unresolved assay-method metadata" in raw
              or "eligible under the prespecified protocol, with unresolved assay-method metadata" in text,
              "required LogD status wording present verbatim")

    # 11. Causal language.
    causal_hits = []
    for pattern in CAUSAL_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.I):
            window = text[max(0, match.start() - 120): match.end() + 120].lower()
            if any(allowed in window for allowed in CAUSAL_ALLOWED):
                continue
            causal_hits.append({"pattern": pattern, "context": text[max(0, match.start() - 90): match.end() + 90]})
    audit.add("no_unsupported_causal_language", not causal_hits,
              "no causal phrasing beyond what the analyses support",
              causal_hits or None)

    # 12. Figure and table paths referenced by the manuscript exist.
    expected_artifacts = [
        "preprint/figures/figure1_eligibility_funnel.png",
        "preprint/figures/figure2_shift_and_compression.png",
        "preprint/figures/figure3_baseline_relative.png",
        "preprint/tables/table1_compatibility.csv",
        "preprint/tables/table2_external_results.csv",
        "preprint/tables/supplementary_sensitivity.csv",
    ]
    absent_artifacts = [p for p in expected_artifacts if not (REPO_ROOT / p).is_file()]
    audit.add("figure_and_table_artifacts_exist", not absent_artifacts,
              f"{len(expected_artifacts)} referenced artefacts present", absent_artifacts or None)

    # 13. Scientific invariance against the pre-work baseline.
    import hashlib

    baselines = {
        "results": "c15305d0586730f60761e98a4ba21cf187fbe32e65471567eb38f93f79df9bbe",
        "compatibility": "de0b8698bbaa2b399283e9f2d04b8020518a3b7fe43465dbe06aabe41dc13700",
    }
    drift = {}
    for block, expected in baselines.items():
        actual = hashlib.sha256(json.dumps(analysis[block], sort_keys=True).encode()).hexdigest()
        if actual != expected:
            drift[block] = {"expected": expected, "actual": actual}
    audit.add("scientific_results_unchanged", not drift,
              "results and compatibility blocks identical to the pre-preparation baseline", drift or None)

    # 14. Release licence boundary.
    audit.add("release_licence_check", release_package.check(None) == 0,
              "no excluded file has entered the release set")

    # 14b. Repository URLs. Released files must not name the private
    # development repository, must not point at an undeclared repository, and
    # must declare this public repository as repository-code.
    url_report = check_repository_urls.run()
    url_failures = (url_report["private_repo_references"]
                    + url_report["undeclared_repo_references"]
                    + url_report["declared_metadata_problems"])
    audit.add("repository_urls_point_to_public_export", url_report["passed"],
              f"{url_report['files_scanned']} released files scanned; "
              f"repository-code is {url_report['public_repository_url']}",
              url_failures or None)

    # 15. Freeze record consistency.
    freeze = json.loads((REPO_ROOT / "preprint/results/scientific_freeze.json").read_text(encoding="utf-8"))
    stale = {
        path: digest
        for group in ("manuscript", "figures", "tables", "compatibility_matrix")
        for path, digest in freeze["artifact_hashes"][group].items()
        if (REPO_ROOT / path).is_file()
        and hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest() != digest
    }
    audit.add("freeze_hashes_current", not stale,
              "manuscript, figure, table and compatibility-matrix hashes match the freeze record",
              sorted(stale) or None)

    return {
        "artifact_id": "preprint-v1.0.0-final-audit",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                                 capture_output=True, text=True).stdout.strip(),
        "manuscript_words_excluding_references": len(
            re.findall(r"[A-Za-z0-9µ²⁻][A-Za-z0-9µ²⁻'’\-\.]*", body)
        ),
        "checks_run": len(audit.checks),
        "checks_failed": len(audit.failed),
        "overall": "PASS" if not audit.failed else "FAIL",
        "unresolved_author_fields": placeholders,
        "checks": audit.checks,
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        "# Final release audit",
        "",
        f"**Overall:** {report['overall']}  ",
        f"**Generated:** {report['generated_at_utc']}  ",
        f"**Commit:** `{report['commit']}`  ",
        f"**Manuscript length:** {report['manuscript_words_excluding_references']} words excluding references  ",
        f"**Checks:** {report['checks_run']} run, {report['checks_failed']} failed",
        "",
        "Generated by `preprint/analysis/final_audit.py`. Every check reads the",
        "generated artefacts; nothing is asserted from memory.",
        "",
        "| # | Check | Status | Detail |",
        "| ---: | --- | --- | --- |",
    ]
    for index, check in enumerate(report["checks"], start=1):
        mark = "✅" if check["status"] == "PASS" else "❌"
        lines.append(f"| {index} | `{check['check']}` | {mark} {check['status']} | {check['detail']} |")
    failures = [c for c in report["checks"] if c["status"] == "FAIL"]
    if failures:
        lines += ["", "## Failures", ""]
        for check in failures:
            lines.append(f"### `{check['check']}`")
            lines.append("")
            lines.append(f"{check['detail']}")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(check["evidence"], indent=2))
            lines.append("```")
            lines.append("")
    if report["unresolved_author_fields"]:
        lines += ["", "## Author-supplied fields still open", "",
                  "Expected at this stage. These are tracked in `USER_INPUT_REQUIRED.md` and",
                  "are enforced by `verify_manuscript_claims.py --submission-ready`.", ""]
        for field in report["unresolved_author_fields"]:
            lines.append(f"- `[[{field}]]`")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    audit = Audit()
    report = run(audit)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render(report), encoding="utf-8")
    for check in report["checks"]:
        mark = "PASS" if check["status"] == "PASS" else "FAIL"
        print(f"  [{mark}] {check['check']}: {check['detail']}")
        if check["status"] == "FAIL":
            print(f"         evidence: {json.dumps(check['evidence'])[:300]}")
    print()
    print(f"OVERALL: {report['overall']}  ({report['checks_run']} checks, {report['checks_failed']} failed)")
    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT).as_posix()}")
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT).as_posix()}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
