"""Guard the repository URLs that appear in released files.

The public export is a clean, redistribution-safe copy of a private development
repository. Several released files — the manuscript, the ChemRxiv copies, the
citation record and the Zenodo deposition draft — carry a "code and data" URL.
Before this check existed, those URLs still pointed at the private development
repository, which would have published its name and given every reader a link
they cannot fetch.

Three conditions are enforced:

1. No released file mentions a known name of the private development
   repository.
2. Every GitHub repository referenced by a released file is either this public
   repository or a declared third-party upstream source.
3. The declared repository-code metadata is exactly the public repository URL.

    PYTHONPATH=backend python preprint/analysis/check_repository_urls.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PUBLIC_REPO_SLUG = "RahulRoktim/admet-semantic-eligibility"
PUBLIC_REPO_URL = f"https://github.com/{PUBLIC_REPO_SLUG}"

#: Every name the private development repository has been known by. An
#: occurrence in a released file is a release-blocking leak, not a typo.
PRIVATE_REPO_SLUGS = frozenset({"rahulroktim/admet-evidence-graph"})

#: Upstream repositories legitimately cited as data provenance. These belong to
#: other people and are recorded in DATA_LICENSES.md and REPRODUCE.md.
THIRD_PARTY_REPO_SLUGS = frozenset({
    "molecularinformatics/computational-adme",  # Biogen Computational-ADME public set
    "duke-w91/caco2_prediction",                # temporal ChEMBL Caco-2 set (rejected candidate)
})

#: This module and its test necessarily contain the forbidden name, so they are
#: the only files exempt from condition 1. The exemption is asserted in run() so
#: a rename cannot silently widen it.
SELF_EXEMPT = ("preprint/analysis/check_repository_urls.py",
               "preprint/tests/test_repository_urls.py")

REPO_URL_PATTERN = re.compile(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")
SKIP_DIRS = {".git", "__pycache__", "venv"}
TRAILING_PUNCTUATION = ".,)>\"'`"
REDACTED = "<private-development-repository>"


def released_files() -> list[Path]:
    """Every file that ships in the public release."""
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
        return None  # binary or unreadable: carries no URL text


def _line_of(text: str, index: int) -> int:
    return text.count(chr(10), 0, index) + 1


def _redact(slug: str) -> str:
    """Never echo a forbidden name into a report that is itself released.

    ``final_audit.py`` persists failure details into ``FINAL_AUDIT.md`` and
    ``final_audit.json``, both of which ship in the release. Echoing the raw
    slug into them would turn one violation into three and leave the guard
    unable to return to a passing state even after the original fault was
    fixed. The file and line locate the problem exactly; the name itself adds
    nothing an author cannot see by opening that line.
    """
    return REDACTED if slug.lower() in PRIVATE_REPO_SLUGS else slug


def find_private_repo_references() -> list[dict[str, object]]:
    """Condition 1: no released file names the private development repository."""
    hits: list[dict[str, object]] = []
    for path in released_files():
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in SELF_EXEMPT:
            continue
        text = _read_text(path)
        if text is None:
            continue
        lowered = text.lower()
        for slug in PRIVATE_REPO_SLUGS:
            start = 0
            while (index := lowered.find(slug, start)) != -1:
                hits.append({"file": relative, "line": _line_of(text, index),
                             "slug": _redact(slug)})
                start = index + 1
    return hits


def find_foreign_repo_references() -> list[dict[str, object]]:
    """Condition 2: no released file points at an undeclared repository."""
    allowed = {PUBLIC_REPO_SLUG.lower()} | THIRD_PARTY_REPO_SLUGS
    hits: list[dict[str, object]] = []
    for path in released_files():
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in SELF_EXEMPT:
            continue
        text = _read_text(path)
        if text is None:
            continue
        for match in REPO_URL_PATTERN.finditer(text):
            slug = match.group(1).rstrip(TRAILING_PUNCTUATION).lower()
            if slug.endswith(".git"):
                slug = slug[:-4]
            if slug not in allowed:
                hits.append({"file": relative,
                             "line": _line_of(text, match.start()),
                             "slug": _redact(match.group(1))})
    return hits


def check_declared_repository_metadata() -> list[dict[str, object]]:
    """Condition 3: declared repository metadata is exactly the public URL."""
    problems: list[dict[str, object]] = []

    citation_text = _read_text(REPO_ROOT / "preprint/CITATION.cff") or ""
    match = re.search(r'^repository-code:\s*"?([^"\n]+?)"?\s*$', citation_text, re.MULTILINE)
    if match is None:
        problems.append({"field": "CITATION.cff:repository-code", "problem": "field absent"})
    elif match.group(1).strip() != PUBLIC_REPO_URL:
        problems.append({"field": "CITATION.cff:repository-code",
                         "expected": PUBLIC_REPO_URL,
                         "actual": _redact(match.group(1).strip())})

    zenodo = REPO_ROOT / "preprint/submission/chemrxiv/zenodo_metadata.json"
    if zenodo.is_file():
        related = json.loads(zenodo.read_text(encoding="utf-8"))["metadata"]["related_identifiers"]
        urls = [entry["identifier"] for entry in related if entry.get("scheme") == "url"]
        if PUBLIC_REPO_URL not in urls:
            problems.append({"field": "zenodo_metadata.json:related_identifiers",
                             "expected": PUBLIC_REPO_URL,
                             "actual": [_redact(url) for url in urls]})

    for name in ("preprint/manuscript/manuscript.md",
                 "preprint/submission/chemrxiv/manuscript.md"):
        body = _read_text(REPO_ROOT / name) or ""
        line = next((l for l in body.splitlines() if "Code and data" in l), None)
        if line is None:
            problems.append({"field": f"{name}:code-and-data", "problem": "line absent"})
        elif PUBLIC_REPO_URL not in line:
            problems.append({"field": f"{name}:code-and-data",
                             "expected": PUBLIC_REPO_URL, "problem": "does not carry the public URL"})

    return problems


def run() -> dict[str, object]:
    for relative in SELF_EXEMPT:
        if not (REPO_ROOT / relative).is_file():
            raise FileNotFoundError(
                f"self-exempt file missing: {relative}. The exemption list must name "
                f"real files, otherwise condition 1 silently stops covering something."
            )
    private = find_private_repo_references()
    foreign = find_foreign_repo_references()
    metadata = check_declared_repository_metadata()
    return {
        "public_repository_url": PUBLIC_REPO_URL,
        "files_scanned": len(released_files()),
        "private_repo_references": private,
        "undeclared_repo_references": foreign,
        "declared_metadata_problems": metadata,
        "passed": not (private or foreign or metadata),
    }


def main(argv: list[str] | None = None) -> int:
    report = run()
    print(f"public repository URL : {report['public_repository_url']}")
    print(f"released files scanned: {report['files_scanned']}")
    for label, key in (("private-repo references", "private_repo_references"),
                       ("undeclared repositories", "undeclared_repo_references"),
                       ("declared metadata problems", "declared_metadata_problems")):
        entries = report[key]
        print(f"  [{'PASS' if not entries else 'FAIL'}] {label}: {len(entries)}")
        for entry in entries:
            print(f"        {entry}")
    print("OVERALL:", "PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
