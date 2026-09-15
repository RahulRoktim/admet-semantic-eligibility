"""Guard the Zenodo DOI recorded across the release.

This project's author has more than one Zenodo deposit. Citing the wrong one
would send readers to an unrelated paper, and citing a concept DOI would send
them to whatever version happens to be newest rather than the artefact the
manuscript's numbers came from. Both failures are silent: the DOI still looks
well-formed and still resolves.

Four conditions are enforced:

1. Every Zenodo DOI mentioned in a released file is this deposit's reserved
   version DOI.
2. No ``[[ZENODO_DOI]]`` placeholder survives.
3. The DOI is actually present everywhere it belongs.
4. Bare and URL spellings denote the same DOI.

``[[RELEASE_DATE]]`` is the one placeholder allowed before release and is
ignored here; ``check_placeholders`` reports it separately.

    PYTHONPATH=backend python preprint/analysis/check_doi_consistency.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The reserved Zenodo VERSION DOI for v1.0.0-preprint (deposition 22765692).
ZENODO_DOI = "10.5281/zenodo.22765692"
ZENODO_DOI_URL = f"https://doi.org/{ZENODO_DOI}"

#: Minted only on publication, and deliberately never cited: the manuscript
#: must point at the exact artefact its numbers came from.
CONCEPT_RECORD_ID = "22765691"

#: Other Zenodo deposits by the same author. Present here only so the guard can
#: name them when one is confused for this paper's DOI.
FOREIGN_ZENODO_DOIS = {
    "10.5281/zenodo.22738114": "MolAudit / molecular-identity-benchmark-audit (version)",
    "10.5281/zenodo.22738113": "MolAudit / molecular-identity-benchmark-audit (concept)",
}

#: Files that must carry the DOI, and the spelling each one needs.
REQUIRED_BARE = (
    "preprint/CITATION.cff",
    "preprint/submission/chemrxiv/zenodo_metadata.json",
)
REQUIRED_ANY = (
    "preprint/manuscript/manuscript.md",
    "preprint/submission/chemrxiv/manuscript.md",
    "preprint/submission/chemrxiv/statements.md",
)

#: This module and its test necessarily contain the forbidden DOIs.
SELF_EXEMPT = ("preprint/analysis/check_doi_consistency.py",
               "preprint/tests/test_doi_consistency.py")

ZENODO_DOI_PATTERN = re.compile(r"10\.5281/zenodo\.(\d+)", re.IGNORECASE)
PLACEHOLDER = "[[ZENODO_DOI]]"
SKIP_DIRS = {".git", "__pycache__", "venv"}


def released_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                            capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return [REPO_ROOT / line for line in result.stdout.splitlines() if line.strip()]
    return [p for p in REPO_ROOT.rglob("*")
            if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(REPO_ROOT).parts)]


def _read_text(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _line_of(text: str, index: int) -> int:
    return text.count(chr(10), 0, index) + 1


def _scannable() -> list[tuple[str, str]]:
    out = []
    for path in released_files():
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in SELF_EXEMPT:
            continue
        text = _read_text(path)
        if text is not None:
            out.append((relative, text))
    return out


def find_wrong_zenodo_dois() -> list[dict[str, object]]:
    """Condition 1: every Zenodo DOI mentioned is this deposit's version DOI."""
    expected_suffix = ZENODO_DOI.split(".")[-1]
    hits: list[dict[str, object]] = []
    for relative, text in _scannable():
        for match in ZENODO_DOI_PATTERN.finditer(text):
            if match.group(1) == expected_suffix:
                continue
            found = match.group(0).lower()
            if match.group(1) == CONCEPT_RECORD_ID:
                reason = "concept DOI of this deposit; the manuscript must cite the version DOI"
            else:
                reason = FOREIGN_ZENODO_DOIS.get(found, "unrecognised Zenodo DOI")
            hits.append({"file": relative, "line": _line_of(text, match.start()),
                         "found": match.group(0), "reason": reason})
    return hits


def find_doi_placeholders() -> list[dict[str, object]]:
    """Condition 2: no unresolved DOI placeholder survives."""
    hits: list[dict[str, object]] = []
    for relative, text in _scannable():
        start = 0
        while (index := text.find(PLACEHOLDER, start)) != -1:
            hits.append({"file": relative, "line": _line_of(text, index)})
            start = index + 1
    return hits


def find_missing_doi() -> list[dict[str, object]]:
    """Condition 3: the DOI is present everywhere it belongs."""
    missing: list[dict[str, object]] = []
    for relative in REQUIRED_BARE:
        text = _read_text(REPO_ROOT / relative) or ""
        if ZENODO_DOI not in text:
            missing.append({"file": relative, "problem": f"does not contain {ZENODO_DOI}"})
    for relative in REQUIRED_ANY:
        text = _read_text(REPO_ROOT / relative) or ""
        if ZENODO_DOI not in text and ZENODO_DOI_URL not in text:
            missing.append({"file": relative,
                            "problem": "contains neither the bare DOI nor its URL form"})
    return missing


def find_inconsistent_doi_urls() -> list[dict[str, object]]:
    """Condition 4: every doi.org URL denotes this same DOI."""
    hits: list[dict[str, object]] = []
    # Match the DOI greedily. A lazy \S+? stops at the first "." inside
    # "10.5281", capturing just "10" and silently checking nothing.
    pattern = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/[^\s\"'<>)\]]+)",
                         re.IGNORECASE)
    for relative, text in _scannable():
        for match in pattern.finditer(text):
            target = match.group(1).rstrip(".,);:\"'")
            if not target.lower().startswith("10.5281/zenodo."):
                continue  # a non-Zenodo DOI URL: not this guard's business
            if target.lower() != ZENODO_DOI.lower():
                hits.append({"file": relative, "line": _line_of(text, match.start()),
                             "found": target, "expected": ZENODO_DOI})
    return hits


def redacted_failures(report: dict[str, object]) -> list[dict[str, object]]:
    """Failure details safe to persist into a file that is itself released.

    ``final_audit.py`` writes failures into FINAL_AUDIT.md and final_audit.json,
    both of which ship. Echoing a forbidden DOI into them would turn one
    violation into three and leave the guard unable to pass again once the
    original fault was fixed. File and line locate the problem exactly.
    """
    safe: list[dict[str, object]] = []
    for key in ("wrong_zenodo_dois", "doi_placeholders", "missing_doi",
                "inconsistent_doi_urls"):
        for entry in report[key]:  # type: ignore[index]
            safe.append({k: ("<redacted-doi>" if k in ("found", "expected") else v)
                         for k, v in entry.items()} | {"check": key})
    return safe


def run() -> dict[str, object]:
    for relative in SELF_EXEMPT:
        if not (REPO_ROOT / relative).is_file():
            raise FileNotFoundError(f"self-exempt file missing: {relative}")
    wrong = find_wrong_zenodo_dois()
    placeholders = find_doi_placeholders()
    missing = find_missing_doi()
    urls = find_inconsistent_doi_urls()
    return {
        "expected_doi": ZENODO_DOI,
        "expected_doi_url": ZENODO_DOI_URL,
        "files_scanned": len(_scannable()),
        "wrong_zenodo_dois": wrong,
        "doi_placeholders": placeholders,
        "missing_doi": missing,
        "inconsistent_doi_urls": urls,
        "passed": not (wrong or placeholders or missing or urls),
    }


def main(argv: list[str] | None = None) -> int:
    report = run()
    print(f"expected DOI          : {report['expected_doi']}  (version, deposition 22765692)")
    print(f"released files scanned: {report['files_scanned']}")
    for label, key in (("wrong or foreign Zenodo DOIs", "wrong_zenodo_dois"),
                       ("unresolved DOI placeholders", "doi_placeholders"),
                       ("files missing the DOI", "missing_doi"),
                       ("inconsistent DOI URL forms", "inconsistent_doi_urls")):
        entries = report[key]
        print(f"  [{'PASS' if not entries else 'FAIL'}] {label}: {len(entries)}")
        for entry in entries:
            print(f"        {entry}")
    print("OVERALL:", "PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
