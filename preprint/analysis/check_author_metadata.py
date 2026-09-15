"""Guard the author's name, ORCID, affiliation and email across the release.

The author's name carries an honorific that is easy to drop. Two prepared files
had already lost it — ``zenodo_metadata.json`` recorded "Roktim, Rahul Reza"
and ``CITATION.cff`` split it as given-names "Rahul Reza" — which would have
produced a citation under a different name from the one on the paper, and an
ORCID record that disagreed with both.

Three conditions are enforced:

1. No released file uses a truncated form of the author's name.
2. The declared author metadata fields hold exactly the canonical values.
3. Every ORCID, affiliation and corresponding email that appears is the
   canonical one.

    PYTHONPATH=backend python preprint/analysis/check_author_metadata.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Canonical author metadata. The rendered form is what a reader sees; the
#: inverted form is what citation metadata stores.
RENDERED_NAME = "Md. Rahul Reza Roktim"
INVERTED_NAME = "Roktim, Md. Rahul Reza"
FAMILY_NAME = "Roktim"
GIVEN_NAMES = "Md. Rahul Reza"
ORCID = "0009-0003-6518-0495"
AFFILIATION = "Department of Pharmacy, Daffodil International University, Dhaka, Bangladesh"
EMAIL = "roktim2311091058@diu.edu.bd"

#: Forms that drop the honorific. Each is a real mistake that was present in
#: this repository, not a hypothetical.
TRUNCATED_FORMS = (
    "Roktim, Rahul Reza",
    "Rahul Reza Roktim",  # only counted when not preceded by "Md. "
)

SELF_EXEMPT = ("preprint/analysis/check_author_metadata.py",
               "preprint/tests/test_author_metadata.py")

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


def find_truncated_author_forms() -> list[dict[str, object]]:
    """Condition 1: the honorific is never dropped.

    A bibliography entry for some other person may legitimately contain similar
    text, so a match is only a failure when it refers to this author: it is
    checked against the preceding characters so that "Md. Rahul Reza Roktim"
    never counts as a truncated "Rahul Reza Roktim".
    """
    hits: list[dict[str, object]] = []
    for relative, text in _scannable():
        for form in TRUNCATED_FORMS:
            start = 0
            while (index := text.find(form, start)) != -1:
                start = index + 1
                preceding = text[max(0, index - 4):index]
                if preceding.endswith("Md. "):
                    continue  # the full, correct rendered name
                hits.append({"file": relative, "line": _line_of(text, index), "form": form})
    return hits


def check_declared_author_fields() -> list[dict[str, object]]:
    """Condition 2: declared citation metadata holds the canonical values."""
    problems: list[dict[str, object]] = []

    citation = _read_text(REPO_ROOT / "preprint/CITATION.cff") or ""
    for field, expected in (("family-names", FAMILY_NAME),
                            ("given-names", GIVEN_NAMES),
                            ("orcid", ORCID),
                            ("affiliation", AFFILIATION),
                            ("email", EMAIL)):
        match = re.search(rf'^\s*-?\s*{re.escape(field)}:\s*"?(.+?)"?\s*$',
                          citation, re.MULTILINE)
        if match is None:
            problems.append({"field": f"CITATION.cff:{field}", "problem": "absent"})
        elif match.group(1).strip() != expected:
            problems.append({"field": f"CITATION.cff:{field}",
                             "expected": expected, "actual": match.group(1).strip()})

    zenodo = REPO_ROOT / "preprint/submission/chemrxiv/zenodo_metadata.json"
    if zenodo.is_file():
        creators = json.loads(zenodo.read_text(encoding="utf-8"))["metadata"]["creators"]
        if len(creators) != 1:
            problems.append({"field": "zenodo_metadata.json:creators",
                             "problem": f"expected 1 creator, found {len(creators)}"})
        else:
            for key, expected in (("name", INVERTED_NAME),
                                  ("orcid", ORCID),
                                  ("affiliation", AFFILIATION)):
                actual = creators[0].get(key)
                if actual != expected:
                    problems.append({"field": f"zenodo_metadata.json:creators[0].{key}",
                                     "expected": expected, "actual": actual})
    return problems


def find_foreign_author_identifiers() -> list[dict[str, object]]:
    """Condition 3: no other ORCID or corresponding email appears."""
    hits: list[dict[str, object]] = []
    orcid_pattern = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
    email_pattern = re.compile(r"\b[\w.+-]+@diu\.edu\.bd\b", re.IGNORECASE)
    for relative, text in _scannable():
        for match in orcid_pattern.finditer(text):
            if match.group(0) != ORCID:
                hits.append({"file": relative, "line": _line_of(text, match.start()),
                             "kind": "orcid", "found": match.group(0)})
        for match in email_pattern.finditer(text):
            if match.group(0).lower() != EMAIL:
                hits.append({"file": relative, "line": _line_of(text, match.start()),
                             "kind": "email", "found": match.group(0)})
    return hits


def run() -> dict[str, object]:
    for relative in SELF_EXEMPT:
        if not (REPO_ROOT / relative).is_file():
            raise FileNotFoundError(f"self-exempt file missing: {relative}")
    truncated = find_truncated_author_forms()
    declared = check_declared_author_fields()
    foreign = find_foreign_author_identifiers()
    return {
        "rendered_name": RENDERED_NAME,
        "inverted_name": INVERTED_NAME,
        "orcid": ORCID,
        "files_scanned": len(_scannable()),
        "truncated_author_forms": truncated,
        "declared_field_problems": declared,
        "foreign_identifiers": foreign,
        "passed": not (truncated or declared or foreign),
    }


def main(argv: list[str] | None = None) -> int:
    report = run()
    print(f"author  : {report['rendered_name']}  ({report['inverted_name']})")
    print(f"orcid   : {report['orcid']}")
    print(f"released files scanned: {report['files_scanned']}")
    for label, key in (("truncated author forms", "truncated_author_forms"),
                       ("declared field problems", "declared_field_problems"),
                       ("foreign ORCIDs or emails", "foreign_identifiers")):
        entries = report[key]
        print(f"  [{'PASS' if not entries else 'FAIL'}] {label}: {len(entries)}")
        for entry in entries:
            print(f"        {entry}")
    print("OVERALL:", "PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
