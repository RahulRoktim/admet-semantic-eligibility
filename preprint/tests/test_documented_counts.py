"""Documented verification counts must match what the suite actually produces.

The release notes claimed "294 passed" for a package that runs 95 tests. That
figure came from the private development repository's full application suite --
a number no reader of this public repository could ever reproduce. The same
stale value had propagated into the ChemRxiv AI-assistance note, and
REPRODUCE.md and RELEASE_CHECKLIST.md still quoted 26 tests, 66/66 files and a
16-check audit from an earlier state.

None of that is scientific content, and none of it was caught by any gate: the
claim verifier checks numbers in the manuscript against generated artefacts,
not numbers in the surrounding documentation. These tests close that gap by
deriving each figure at run time and comparing it to what the documents say, so
the documentation cannot silently drift from the package again.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def actual_test_count() -> int:
    """How many tests this suite collects, asked of pytest itself."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "preprint/tests", "--collect-only", "-q"],
        cwd=REPO_ROOT, capture_output=True, text=True,
        env={**__import__("os").environ, "PYTHONPATH": "backend", "PYTHONUTF8": "1"},
    )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    if match is None:
        pytest.skip(f"could not read a collection count from pytest: {result.stdout[-200:]}")
    return int(match.group(1))


def actual_checksum_entries() -> int:
    return len([l for l in _read("preprint/results/checksums.sha256").splitlines() if l.strip()])


def actual_audit_check_count() -> int:
    import json
    return json.loads(_read("preprint/results/final_audit.json"))["checks_run"]


def actual_figure_file_count() -> int:
    figures = REPO_ROOT / "preprint/figures"
    return len([p for p in figures.iterdir() if p.suffix in {".png", ".pdf"}])


@pytest.mark.parametrize("relative,pattern", [
    ("RELEASE_NOTES_v1.0.0-preprint.md", r"\|\s*Test suite\s*\|\s*(\d+) passed\s*\|"),
    ("preprint/REPRODUCE.md", r"\|\s*Tests\s*\|\s*(\d+) passed\s*\|"),
    ("preprint/RELEASE_CHECKLIST.md", r"(\d+) tests pass"),
    ("preprint/submission/chemrxiv/ai_assistance_note.md", r"-\s*(\d+) tests, including negative controls"),
])
def test_documented_test_count_matches_the_suite(relative, pattern):
    match = re.search(pattern, _read(relative))
    assert match, f"{relative}: no documented test count found (pattern changed?)"
    documented = int(match.group(1))
    actual = actual_test_count()
    assert documented == actual, (
        f"{relative} claims {documented} tests; the suite collects {actual}. "
        f"Update the document, not this test."
    )


def test_documented_checksum_counts_match():
    actual = actual_checksum_entries()
    for relative, pattern in [
        ("preprint/REPRODUCE.md", r"checksums\.sha256`\s*\|\s*\*\*(\d+)\s*/\s*\d+\*\*"),
        ("preprint/REPRODUCE.md", r"Regenerated artefacts vs committed\s*\|\s*\*\*(\d+)\s*/\s*\d+"),
        ("preprint/RELEASE_CHECKLIST.md", r"(\d+)/\d+ files byte-identical on checkout"),
    ]:
        match = re.search(pattern, _read(relative))
        assert match, f"{relative}: pattern not found"
        assert int(match.group(1)) == actual, (
            f"{relative} claims {match.group(1)} checksum entries; there are {actual}."
        )


def test_documented_audit_check_count_matches():
    match = re.search(r"\|\s*Final audit\s*\|\s*(\d+) checks", _read("preprint/REPRODUCE.md"))
    assert match, "REPRODUCE.md: final audit row not found"
    assert int(match.group(1)) == actual_audit_check_count()

    match = re.search(r"final audit\s*\n?(\d+)/\d+", _read("preprint/RELEASE_CHECKLIST.md"))
    assert match, "RELEASE_CHECKLIST.md: final audit gate not found"
    assert int(match.group(1)) == actual_audit_check_count()


def test_documented_figure_count_matches():
    match = re.search(r"\*\*(\d+)/\d+ image files byte-identical\*\*", _read("preprint/REPRODUCE.md"))
    assert match, "REPRODUCE.md: figure row not found"
    assert int(match.group(1)) == actual_figure_file_count()


def test_no_document_quotes_the_private_suite_size():
    """The private application suite is far larger; its size must never be cited."""
    for relative in ("RELEASE_NOTES_v1.0.0-preprint.md",
                     "preprint/REPRODUCE.md",
                     "preprint/RELEASE_CHECKLIST.md",
                     "preprint/submission/chemrxiv/ai_assistance_note.md"):
        text = _read(relative)
        for stale in ("294 tests", "294 passed", "296 tests", "296 passed"):
            assert stale not in text, f"{relative} quotes the private development suite: {stale}"
