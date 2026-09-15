"""The archive scanner must catch excluded files inside a real published archive.

Published archives are never flat. ``git archive --prefix=``, GitHub's
auto-generated source tarballs and Zenodo's GitHub integration all wrap the
tree in a top-level directory. Before these tests existed the scanner matched
the exclusion patterns against the whole member name, so a prefixed archive --
the only kind anyone actually publishes -- passed even while carrying an
excluded upstream table. The manifest-derived fallback could not save it
either: in a clean public clone the excluded set is empty by construction.

These tests pin the fix at both levels: the pure predicate, and the full
``check()`` against archives built the way the real ones are built.
"""

from __future__ import annotations

import zipfile

import pytest

from preprint.analysis import release_package

EXCLUDED_MEMBER = "validation/external_prediction/training_reference/PPBR_AZ.csv"
ALLOWED_MEMBER = "preprint/analysis/core.py"


@pytest.mark.parametrize("name", [
    EXCLUDED_MEMBER,
    f"admet-semantic-eligibility-v1.0.0-preprint/{EXCLUDED_MEMBER}",
    f"RahulRoktim-admet-semantic-eligibility-9b5e167/{EXCLUDED_MEMBER}",
    f"./{EXCLUDED_MEMBER}",
    f"some/deeply/nested/wrapper/{EXCLUDED_MEMBER}",
    "validation/external_prediction/training_reference/Caco2_Wang.csv",
    "pkg/validation/external_prediction/training_reference/LD50_Zhu.csv",
])
def test_excluded_member_detected_under_any_prefix(name):
    assert release_package.archive_entry_is_excluded(name), name


@pytest.mark.parametrize("name", [
    ALLOWED_MEMBER,
    f"admet-semantic-eligibility-v1.0.0-preprint/{ALLOWED_MEMBER}",
    "preprint/results/training_reference_summary.json",
    "validation/external_prediction/training_reference.py",
    "preprint/analysis/build_training_reference_summary.py",
    "admet-semantic-eligibility-v1.0.0-preprint/validation/external_prediction/",
])
def test_allowed_member_not_flagged(name):
    """The derived summary and the builder script are released; only the tables are not."""
    assert not release_package.archive_entry_is_excluded(name), name


def _build(path, members, prefix=""):
    with zipfile.ZipFile(path, "w") as bundle:
        for member in members:
            bundle.writestr(f"{prefix}{member}", "x,y\n1,2\n")
    return path


def test_check_passes_a_clean_prefixed_archive(tmp_path):
    archive = _build(tmp_path / "clean.zip", [ALLOWED_MEMBER, "README.md"],
                     prefix="admet-semantic-eligibility-v1.0.0-preprint/")
    assert release_package.check(archive) == 0


@pytest.mark.parametrize("prefix", [
    "",
    "admet-semantic-eligibility-v1.0.0-preprint/",
    "RahulRoktim-admet-semantic-eligibility-9b5e167/",
])
def test_check_rejects_a_leaked_archive_at_any_prefix(tmp_path, prefix):
    """The regression that shipped: a prefixed leak used to pass."""
    archive = _build(tmp_path / f"leaked{len(prefix)}.zip",
                     [ALLOWED_MEMBER, EXCLUDED_MEMBER], prefix=prefix)
    assert release_package.check(archive) == 1, f"leak at prefix {prefix!r} was not caught"


def test_every_excluded_table_is_caught(tmp_path):
    """All ten withheld tables, not just the one the old control happened to use."""
    tables = ["Caco2_Wang", "Clearance_Hepatocyte_AZ", "Clearance_Microsome_AZ",
              "Half_Life_Obach", "HydrationFreeEnergy_FreeSolv", "LD50_Zhu",
              "Lipophilicity_AstraZeneca", "PPBR_AZ", "Solubility_AqSolDB",
              "VDss_Lombardo"]
    for table in tables:
        member = f"validation/external_prediction/training_reference/{table}.csv"
        archive = _build(tmp_path / f"{table}.zip", [ALLOWED_MEMBER, member],
                         prefix="admet-semantic-eligibility-v1.0.0-preprint/")
        assert release_package.check(archive) == 1, f"{table}.csv was not caught"
