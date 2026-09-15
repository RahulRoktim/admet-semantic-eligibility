"""The released files must never point readers at the private repository.

The public export carries a "code and data" URL in the manuscript, both
ChemRxiv copies, the citation record and the Zenodo deposition draft. Those
URLs once pointed at the private development repository. These tests pin the
corrected state and, more importantly, prove the checker still fires when the
regression is reintroduced — a guard that only ever passes is not a guard.
"""

from __future__ import annotations

import pytest

from preprint.analysis import check_repository_urls as guard


def test_public_repository_url_is_the_clean_export():
    assert guard.PUBLIC_REPO_URL == "https://github.com/RahulRoktim/admet-semantic-eligibility"


def test_no_released_file_names_the_private_repository():
    hits = guard.find_private_repo_references()
    assert hits == [], f"private development repository named in released files: {hits}"


def test_every_referenced_repository_is_declared():
    hits = guard.find_foreign_repo_references()
    assert hits == [], f"undeclared repository referenced: {hits}"


def test_declared_repository_metadata_matches_the_public_url():
    problems = guard.check_declared_repository_metadata()
    assert problems == [], f"repository metadata problems: {problems}"


def test_overall_guard_passes():
    assert guard.run()["passed"] is True


@pytest.mark.parametrize("target", [
    "preprint/manuscript/manuscript.md",
    "preprint/submission/chemrxiv/manuscript.md",
    "preprint/submission/chemrxiv/statements.md",
    "preprint/CITATION.cff",
])
def test_guard_detects_a_reintroduced_private_url(tmp_path, monkeypatch, target):
    """Reintroduce the old URL in a scratch copy; the guard must fail."""
    path = guard.REPO_ROOT / target
    original = path.read_bytes()
    corrupted = original.replace(b"RahulRoktim/admet-semantic-eligibility",
                                 b"RahulRoktim/ADMET-Evidence-Graph")
    assert corrupted != original, f"{target} does not carry the public URL to corrupt"
    try:
        path.write_bytes(corrupted)
        assert guard.find_private_repo_references(), "private-repo reference not detected"
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original


def test_guard_detects_an_undeclared_third_party_repository(monkeypatch):
    path = guard.REPO_ROOT / "preprint/manuscript/manuscript.md"
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"\nhttps://github.com/someone-else/other-repo\n")
        hits = guard.find_foreign_repo_references()
        assert any(hit["slug"] == "someone-else/other-repo" for hit in hits), hits
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original


def test_self_exempt_files_exist():
    """The exemption must name real files or condition 1 quietly narrows."""
    for relative in guard.SELF_EXEMPT:
        assert (guard.REPO_ROOT / relative).is_file(), relative
