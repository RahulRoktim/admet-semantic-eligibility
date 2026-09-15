"""Build and verify the public-release manifest.

Every file intended for the GitHub release, the Zenodo archive or the
supplementary-data package is classified into exactly one category:

    PROJECT_CODE                  authored here, MIT
    ORIGINAL_CONTENT              authored here, CC BY 4.0
    THIRD_PARTY_REDISTRIBUTABLE   third-party, released under its own licence
    DERIVED_RESULT                computed here from the above
    UPSTREAM_REFERENCE_ONLY       describes upstream material so a reader can obtain it
    EXCLUDED_FROM_REDISTRIBUTION  present locally, never packaged

Usage::

    PYTHONPATH=backend python preprint/analysis/release_package.py --build
    PYTHONPATH=backend python preprint/analysis/release_package.py --check
    PYTHONPATH=backend python preprint/analysis/release_package.py --check --archive dist/release.zip

``--check`` fails (non-zero exit) if any excluded file has entered the release
set, if a packaged archive contains one, or if a file is unclassified.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for candidate in (str(REPO_ROOT), str(REPO_ROOT / "backend")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

MANIFEST = REPO_ROOT / "preprint/release_manifest.json"
MANIFEST_ID = "preprint-v1.0-public-release-manifest"

# ---------------------------------------------------------------------------
# Redistribution boundary
# ---------------------------------------------------------------------------

#: Files that exist locally and are used by the study but must never be
#: packaged. See DATA_LICENSES.md section 3.
EXCLUDED_PATTERNS = (
    "validation/external_prediction/training_reference/*.csv",
)

EXCLUSION_REASON = (
    "Reconstructed Therapeutics Data Commons reference table. Upstream licensing provenance is "
    "ambiguous (TDC pages indicate CC BY 4.0; several endpoints originate from AstraZeneca "
    "depositions that ChEMBL distributes under CC BY-SA 3.0). Not redistributed. Rebuild "
    "instructions are in preprint/REPRODUCE.md Level 2; the exact file hashes used in this study "
    "are published in preprint/results/training_reference_summary.json."
)

#: Ordered classification rules. First match wins.
CLASSIFICATION_RULES: tuple[tuple[str, str], ...] = (
    ("validation/external_prediction/training_reference/*", "EXCLUDED_FROM_REDISTRIBUTION"),
    ("validation/external_prediction/source_snapshots/*", "THIRD_PARTY_REDISTRIBUTABLE"),
    ("validation/external_prediction/external_dataset_manifest.json", "UPSTREAM_REFERENCE_ONLY"),
    ("validation/external_prediction/admet_ai_training_manifest.json", "UPSTREAM_REFERENCE_ONLY"),
    ("validation/external_prediction/endpoint_compatibility.csv", "ORIGINAL_CONTENT"),
    ("validation/external_prediction/*.py", "PROJECT_CODE"),
    ("validation/external_prediction/results/*.csv", "DERIVED_RESULT"),
    ("validation/external_prediction/failure_analysis.csv", "DERIVED_RESULT"),
    ("validation/reports/v0102_external_*.json", "DERIVED_RESULT"),
    ("preprint/analysis/*.py", "PROJECT_CODE"),
    ("preprint/figures/*.py", "PROJECT_CODE"),
    ("preprint/tests/*.py", "PROJECT_CODE"),
    ("preprint/*.py", "PROJECT_CODE"),
    ("preprint/requirements-analysis.txt", "PROJECT_CODE"),
    ("preprint/CITATION.cff", "PROJECT_CODE"),
    ("preprint/manuscript/*", "ORIGINAL_CONTENT"),
    ("preprint/submission/chemrxiv/*.pdf", "ORIGINAL_CONTENT"),
    ("preprint/submission/chemrxiv/*.csv", "DERIVED_RESULT"),
    ("preprint/submission/chemrxiv/*.json", "ORIGINAL_CONTENT"),
    ("preprint/submission/chemrxiv/*", "ORIGINAL_CONTENT"),
    ("preprint/figures/*.png", "ORIGINAL_CONTENT"),
    ("preprint/figures/*.pdf", "ORIGINAL_CONTENT"),
    ("preprint/tables/*.csv", "DERIVED_RESULT"),
    ("preprint/results/*.json", "DERIVED_RESULT"),
    ("preprint/results/*.csv", "DERIVED_RESULT"),
    ("preprint/results/*.sha256", "DERIVED_RESULT"),
    ("preprint/results/*.md", "ORIGINAL_CONTENT"),
    ("preprint/*.md", "ORIGINAL_CONTENT"),
    ("LICENSE", "PROJECT_CODE"),
    ("COPYRIGHT", "ORIGINAL_CONTENT"),
    ("README.md", "ORIGINAL_CONTENT"),
    ("USER_INPUT_REQUIRED.md", "ORIGINAL_CONTENT"),
    ("requirements.txt", "PROJECT_CODE"),
    ("requirements-dev.txt", "PROJECT_CODE"),
    ("backend/app/**", "PROJECT_CODE"),
    ("backend/app/*", "PROJECT_CODE"),
    ("RELEASE_NOTES_v1.0.0-preprint.md", "ORIGINAL_CONTENT"),
    ("CONTENT_LICENSE.md", "ORIGINAL_CONTENT"),
    ("THIRD_PARTY_LICENSES.md", "ORIGINAL_CONTENT"),
    ("DATA_LICENSES.md", "ORIGINAL_CONTENT"),
)

#: Files gathered into the release set. Everything under these roots is
#: considered, then classified; excluded files are recorded but not packaged.
RELEASE_SOURCES = (
    "LICENSE",
    "COPYRIGHT",
    "CONTENT_LICENSE.md",
    "THIRD_PARTY_LICENSES.md",
    "DATA_LICENSES.md",
    "README.md",
    "USER_INPUT_REQUIRED.md",
    "RELEASE_NOTES_v1.0.0-preprint.md",
    "requirements.txt",
    "requirements-dev.txt",
    "backend/**/*",
    "preprint/**/*",
    "validation/external_prediction/**/*",
    "validation/reports/v0102_external_metrics.json",
    "validation/reports/v0102_external_overlap.json",
    "validation/reports/v0102_external_stratification.json",
    "validation/reports/v0102_external_run_summary.json",
)

SKIP_SUFFIXES = {".pyc"}
SKIP_PARTS = {"__pycache__", ".pytest_cache"}
#: Generated package-metadata files. Each describes the others, so hashing them
#: here would make the manifest depend on its own generation order. They are
#: covered by preprint/results/checksums.sha256 and by this file respectively.
SKIP_NAMES = {"release_manifest.json", "checksums.sha256", "checksums.json"}

LICENCE_BY_CATEGORY = {
    "PROJECT_CODE": "MIT (LICENSE)",
    "ORIGINAL_CONTENT": "CC BY 4.0 (CONTENT_LICENSE.md)",
    "THIRD_PARTY_REDISTRIBUTABLE": "upstream licence (DATA_LICENSES.md)",
    "DERIVED_RESULT": "CC BY 4.0 for this project's computation; underlying data per DATA_LICENSES.md",
    "UPSTREAM_REFERENCE_ONLY": "CC BY 4.0 (describes upstream material; contains none of it)",
    "EXCLUDED_FROM_REDISTRIBUTION": "not released",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_excluded(relative: str) -> bool:
    return any(fnmatch.fnmatch(relative, pattern) for pattern in EXCLUDED_PATTERNS)


def archive_entry_is_excluded(name: str) -> bool:
    """Is this archive member an excluded file, wherever it sits in the tree?

    Published archives are not flat. ``git archive --prefix=``, GitHub's
    auto-generated source tarballs and Zenodo's GitHub integration all wrap the
    tree in a top-level directory, so a member arrives as
    ``project-v1.0.0/validation/.../PPBR_AZ.csv``. Matching the exclusion
    patterns against that whole string fails -- fnmatch's ``*`` does not cross
    the leading segment -- so a prefix-naive check passes exactly the archives
    that actually get published.

    Every trailing path suffix is therefore tested, which catches the file at
    any depth and under any wrapper name.
    """
    normalised = name.replace("\\", "/").lstrip("./")
    if normalised.endswith("/"):
        return False  # a directory entry
    parts = normalised.split("/")
    return any(is_excluded("/".join(parts[i:])) for i in range(len(parts)))


def classify(relative: str) -> str | None:
    for pattern, category in CLASSIFICATION_RULES:
        if fnmatch.fnmatch(relative, pattern):
            return category
    return None


def collect_files() -> list[str]:
    seen: set[str] = set()
    for source in RELEASE_SOURCES:
        for path in sorted(REPO_ROOT.glob(source)):
            if not path.is_file():
                continue
            if path.suffix in SKIP_SUFFIXES or SKIP_PARTS & set(path.parts) or path.name in SKIP_NAMES:
                continue
            seen.add(path.relative_to(REPO_ROOT).as_posix())
    return sorted(seen)


def build() -> dict[str, Any]:
    files = collect_files()
    entries: list[dict[str, Any]] = []
    unclassified: list[str] = []
    for relative in files:
        category = classify(relative)
        if category is None:
            unclassified.append(relative)
            continue
        entry: dict[str, Any] = {
            "path": relative,
            "category": category,
            "licence": LICENCE_BY_CATEGORY[category],
            "in_public_release": category != "EXCLUDED_FROM_REDISTRIBUTION",
            "sha256": sha256_file(REPO_ROOT / relative),
        }
        if category == "EXCLUDED_FROM_REDISTRIBUTION":
            entry["exclusion_reason"] = EXCLUSION_REASON
        entries.append(entry)
    if unclassified:
        raise SystemExit(
            "Unclassified files would enter the release package. Add a rule for each:\n  "
            + "\n  ".join(unclassified)
        )
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
    return {
        "artifact_id": MANIFEST_ID,
        "schema_version": 1,
        "purpose": (
            "Classifies every file considered for the GitHub release, the Zenodo archive and the "
            "supplementary-data package. No third-party material is relicensed."
        ),
        "categories": LICENCE_BY_CATEGORY,
        "package_metadata_files": {
            "note": (
                "Released alongside the classified files. They are generated last and describe each "
                "other, so they are not hashed inside this manifest; each is self-describing."
            ),
            "files": [
                "preprint/release_manifest.json",
                "preprint/results/checksums.sha256",
                "preprint/results/checksums.json",
            ],
            "category": "DERIVED_RESULT",
            "licence": LICENCE_BY_CATEGORY["DERIVED_RESULT"],
        },
        "excluded_patterns": list(EXCLUDED_PATTERNS),
        "exclusion_reason": EXCLUSION_REASON,
        "counts": dict(sorted(counts.items())),
        "public_release_file_count": sum(1 for entry in entries if entry["in_public_release"]),
        "excluded_file_count": sum(1 for entry in entries if not entry["in_public_release"]),
        "files": entries,
    }


def check(archive: Path | None) -> int:
    if not MANIFEST.is_file():
        raise SystemExit(f"{MANIFEST} is missing. Run with --build first.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []

    excluded = {entry["path"] for entry in manifest["files"] if not entry["in_public_release"]}
    released = {entry["path"] for entry in manifest["files"] if entry["in_public_release"]}

    # 1. No excluded file may be marked for release.
    for path in sorted(excluded & released):
        failures.append(f"file is both excluded and released: {path}")

    # 2. Every file matching an exclusion pattern must be classified excluded.
    for relative in collect_files():
        if is_excluded(relative) and relative not in excluded:
            failures.append(f"matches an exclusion pattern but is not excluded: {relative}")

    # 3. The manifest must still describe reality.
    current = set(collect_files())
    listed = {entry["path"] for entry in manifest["files"]}
    for path in sorted(current - listed):
        failures.append(f"present on disk but missing from the manifest: {path}")
    # Excluded files are absent from a public clean clone by design, so their
    # absence is expected. Any other listed file must exist.
    absent_by_policy = sorted(path for path in (listed - current) if is_excluded(path))
    for path in sorted((listed - current) - set(absent_by_policy)):
        failures.append(f"listed in the manifest but missing on disk: {path}")

    # 4. The boundary must still be declared. Checking the declared patterns
    #    rather than the present files matters: in a public clean clone the
    #    excluded files are legitimately absent, so counting them would report a
    #    correctly enforced boundary as a failure.
    if not EXCLUDED_PATTERNS:
        failures.append("no exclusion pattern is declared; the redistribution boundary is not being enforced")
    if not manifest.get("excluded_patterns"):
        failures.append("the manifest declares no exclusion pattern; it was built without the boundary")

    # 5. If an archive is supplied, it must not contain an excluded file.
    archive_checked = False
    if archive is not None:
        if not archive.is_file():
            failures.append(f"archive not found: {archive}")
        else:
            archive_checked = True
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
            for name in names:
                normalised = name.replace("\\", "/").lstrip("./")
                # The manifest's own excluded set is empty in a clean public
                # clone, so it cannot be the only test here: the pattern check
                # is what has to hold.
                by_manifest = any(normalised.endswith("/" + path) or normalised == path
                                  for path in excluded)
                if archive_entry_is_excluded(name) or by_manifest:
                    failures.append(f"ARCHIVE CONTAINS EXCLUDED FILE: {name}")

    if failures:
        print(f"RELEASE CHECK FAILED: {len(failures)} problem(s)\n")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("RELEASE CHECK PASSED")
    if absent_by_policy:
        print(f"  absent by redistribution policy: {len(absent_by_policy)} (expected in a public clean clone)")
    print(f"  files classified            : {len(manifest['files'])}")
    for category, count in manifest["counts"].items():
        print(f"    {category:30s} {count}")
    print(f"  in public release           : {manifest['public_release_file_count']}")
    print(f"  excluded from redistribution: {manifest['excluded_file_count']}")
    if not excluded:
        print("    (none present on disk: expected in a public clean clone; patterns are still enforced)")
    for path in sorted(excluded):
        print(f"    excluded: {path}")
    print(f"  archive scanned             : {archive if archive_checked else 'none supplied'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="write preprint/release_manifest.json")
    parser.add_argument("--check", action="store_true", help="verify the redistribution boundary")
    parser.add_argument("--archive", type=Path, default=None, help="also scan a built .zip for excluded files")
    args = parser.parse_args(argv)

    if not args.build and not args.check:
        parser.error("choose --build, --check, or both")

    if args.build:
        manifest = build()
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(REPO_ROOT).as_posix()}")
        print(f"  classified {len(manifest['files'])} files")
        print(f"  excluded   {manifest['excluded_file_count']}")

    if args.check:
        return check(args.archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
