"""The author's name must appear in one form, with the honorific intact.

Two prepared files had already dropped "Md." before this guard existed. These
tests pin the corrected state and prove the guard fires when the honorific is
dropped again, when the ORCID drifts, or when the two citation-metadata files
disagree with each other.
"""

from __future__ import annotations

import pytest

from preprint.analysis import check_author_metadata as guard


def test_canonical_values():
    assert guard.RENDERED_NAME == "Md. Rahul Reza Roktim"
    assert guard.INVERTED_NAME == "Roktim, Md. Rahul Reza"
    assert guard.ORCID == "0009-0003-6518-0495"


def test_no_truncated_author_form_anywhere():
    hits = guard.find_truncated_author_forms()
    assert hits == [], f"author name missing the honorific: {hits}"


def test_declared_citation_fields_are_canonical():
    problems = guard.check_declared_author_fields()
    assert problems == [], f"author metadata problems: {problems}"


def test_no_foreign_orcid_or_email():
    assert guard.find_foreign_author_identifiers() == []


def test_overall_guard_passes():
    assert guard.run()["passed"] is True


def test_full_rendered_name_is_not_flagged_as_truncated():
    """"Md. Rahul Reza Roktim" contains "Rahul Reza Roktim" and must not fail."""
    text = "Corresponding author: Md. Rahul Reza Roktim — x@y.z"
    assert "Rahul Reza Roktim" in text
    assert guard.find_truncated_author_forms() == []


def _corrupt(relative: str, old: bytes, new: bytes):
    path = guard.REPO_ROOT / relative
    original = path.read_bytes()
    if old not in original:
        pytest.skip(f"{relative} does not contain {old!r}")
    path.write_bytes(original.replace(old, new, 1))
    return path, original


@pytest.mark.parametrize("target", [
    "preprint/manuscript/manuscript.md",
    "preprint/submission/chemrxiv/manuscript.md",
    "README.md",
    "LICENSE",
])
def test_guard_detects_a_dropped_honorific(target):
    path, original = _corrupt(target, b"Md. Rahul Reza Roktim", b"Rahul Reza Roktim")
    try:
        assert guard.find_truncated_author_forms(), "dropped honorific not detected"
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


def test_guard_detects_the_old_zenodo_creator_form():
    """The exact regression that was present before this phase."""
    path, original = _corrupt("preprint/submission/chemrxiv/zenodo_metadata.json",
                              b'"Roktim, Md. Rahul Reza"', b'"Roktim, Rahul Reza"')
    try:
        assert guard.find_truncated_author_forms(), "truncated creator not detected"
        problems = guard.check_declared_author_fields()
        assert any("creators[0].name" in str(p.get("field")) for p in problems), problems
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


def test_guard_detects_the_old_citation_given_names():
    path, original = _corrupt("preprint/CITATION.cff",
                              b"given-names: Md. Rahul Reza", b"given-names: Rahul Reza")
    try:
        problems = guard.check_declared_author_fields()
        assert any("given-names" in str(p.get("field")) for p in problems), problems
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


def test_guard_detects_a_drifted_orcid():
    path, original = _corrupt("preprint/CITATION.cff",
                              b"0009-0003-6518-0495", b"0009-0003-6518-0496")
    try:
        assert guard.find_foreign_author_identifiers(), "wrong ORCID not detected"
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True


def test_guard_detects_a_wrong_corresponding_email():
    path, original = _corrupt("preprint/manuscript/manuscript.md",
                              b"roktim2311091058@diu.edu.bd", b"someone.else@diu.edu.bd")
    try:
        assert guard.find_foreign_author_identifiers(), "wrong email not detected"
        assert guard.run()["passed"] is False
    finally:
        path.write_bytes(original)
    assert guard.run()["passed"] is True
