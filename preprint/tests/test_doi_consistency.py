"""The release must cite one DOI: this deposit's reserved version DOI.

The author has another Zenodo deposit (MolAudit, 10.5281/zenodo.22738114), and
this deposit also has a concept record that will acquire its own DOI on
publication. Either could be substituted here without looking wrong. These
tests pin the correct DOI and, more importantly, prove the guard fails when
each plausible substitution is made.
"""

from __future__ import annotations

import pytest

from preprint.analysis import check_doi_consistency as guard

MOLAUDIT_DOI = "10.5281/zenodo.22738114"
CONCEPT_DOI = "10.5281/zenodo.22765691"

CARRIERS = [
    "preprint/CITATION.cff",
    "preprint/submission/chemrxiv/zenodo_metadata.json",
    "preprint/manuscript/manuscript.md",
    "preprint/submission/chemrxiv/manuscript.md",
    "preprint/submission/chemrxiv/statements.md",
]


def test_expected_doi_is_the_reserved_version_doi():
    assert guard.ZENODO_DOI == "10.5281/zenodo.22765692"
    assert guard.ZENODO_DOI_URL == "https://doi.org/10.5281/zenodo.22765692"


def test_concept_doi_is_not_cited_anywhere():
    """The paper cites the exact artefact, never the moving concept record."""
    assert all(hit["found"].lower() != CONCEPT_DOI
               for hit in guard.find_wrong_zenodo_dois())
    for _, text in guard._scannable():
        assert CONCEPT_DOI not in text


def test_no_foreign_zenodo_doi_is_present():
    assert guard.find_wrong_zenodo_dois() == []


def test_no_doi_placeholder_remains():
    assert guard.find_doi_placeholders() == []


def test_doi_present_in_every_file_that_needs_it():
    assert guard.find_missing_doi() == []


def test_doi_url_forms_are_consistent():
    assert guard.find_inconsistent_doi_urls() == []


def test_overall_guard_passes():
    assert guard.run()["passed"] is True


def _corrupt(relative: str, old: bytes, new: bytes):
    """Swap bytes in a released file, returning a restore callback."""
    path = guard.REPO_ROOT / relative
    original = path.read_bytes()
    if old not in original:
        pytest.skip(f"{relative} does not contain {old!r}")
    path.write_bytes(original.replace(old, new))
    return path, original


@pytest.mark.parametrize("target", CARRIERS)
def test_guard_detects_altered_doi_digits(target):
    """A single wrong digit must fail, not pass quietly."""
    path, original = _corrupt(target, b"zenodo.22765692", b"zenodo.22765693")
    try:
        assert guard.run()["passed"] is False
        assert guard.find_wrong_zenodo_dois(), "altered digits not detected"
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


@pytest.mark.parametrize("target", CARRIERS)
def test_guard_detects_the_molaudit_doi(target):
    """The author's other paper's DOI must never stand in for this one."""
    path, original = _corrupt(target, b"10.5281/zenodo.22765692",
                              MOLAUDIT_DOI.encode())
    try:
        hits = guard.find_wrong_zenodo_dois()
        assert any(hit["found"].lower() == MOLAUDIT_DOI for hit in hits), hits
        assert any("MolAudit" in str(hit["reason"]) for hit in hits), hits
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


@pytest.mark.parametrize("target", CARRIERS)
def test_guard_detects_a_returned_placeholder(target):
    path, original = _corrupt(target, b"10.5281/zenodo.22765692", b"[[ZENODO_DOI]]")
    try:
        assert guard.find_doi_placeholders(), "placeholder not detected"
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


def test_guard_detects_the_concept_doi_being_substituted():
    """Substituting the concept DOI is the subtlest failure: it resolves fine."""
    target = "preprint/CITATION.cff"
    path, original = _corrupt(target, b"10.5281/zenodo.22765692", CONCEPT_DOI.encode())
    try:
        hits = guard.find_wrong_zenodo_dois()
        assert any(hit["found"].lower() == CONCEPT_DOI for hit in hits), hits
        assert any("concept DOI" in str(hit["reason"]) for hit in hits), hits
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


def test_guard_detects_a_doi_url_pointing_at_another_record():
    target = "preprint/manuscript/manuscript.md"
    path, original = _corrupt(
        target,
        b"https://doi.org/10.5281/zenodo.22765692",
        f"https://doi.org/{MOLAUDIT_DOI}".encode(),
    )
    try:
        assert guard.find_inconsistent_doi_urls(), "wrong DOI URL not detected"
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


def test_guard_detects_a_missing_doi():
    target = "preprint/CITATION.cff"
    path, original = _corrupt(target, b'doi: "10.5281/zenodo.22765692"', b"")
    try:
        assert guard.find_missing_doi(), "absent DOI not detected"
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


def test_release_date_placeholder_is_not_treated_as_a_doi_failure():
    """[[RELEASE_DATE]] is the one allowed pre-release placeholder."""
    assert guard.run()["passed"] is True
    assert any("[[RELEASE_DATE]]" in text for _, text in guard._scannable())
