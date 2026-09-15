"""Write SHA-256 checksums over every committed preprint artefact.

    PYTHONPATH=backend python preprint/analysis/write_checksums.py

Output: ``preprint/results/checksums.sha256`` in the standard
``<hash>  <path>`` format, plus a companion JSON grouping files by role.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PREPRINT = REPO_ROOT / "preprint"
OUTPUT = PREPRINT / "results/checksums.sha256"
OUTPUT_JSON = PREPRINT / "results/checksums.json"

# Frozen inputs the analysis reads but does not own. Hashed here so a verifier
# can confirm the whole chain, inputs included, from one file.
EXTERNAL_INPUTS = [
    "validation/external_prediction/results/asap_processed_predictions.csv",
    "validation/external_prediction/results/biogen_hppb_processed_predictions.csv",
    "validation/external_prediction/endpoint_compatibility.csv",
    "validation/external_prediction/external_dataset_manifest.json",
    "validation/external_prediction/admet_ai_training_manifest.json",
    "validation/external_prediction/source_snapshots/asap_antiviral_admet_2025_unblinded.csv",
    "validation/external_prediction/source_snapshots/biogen_ADME_public_set_3521.csv",
    "validation/reports/v0102_external_metrics.json",
]

SKIP_SUFFIXES = {".pyc"}
SKIP_PARTS = {"__pycache__", ".pytest_cache"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def role_for(relative: str) -> str:
    if relative.startswith("validation/"):
        return "frozen_input"
    if "/results/" in relative:
        return "result"
    if "/tables/" in relative:
        return "table"
    if "/figures/" in relative:
        return "figure_script" if relative.endswith(".py") else "figure"
    if "/manuscript/" in relative:
        return "manuscript"
    if "/tests/" in relative:
        return "test"
    if "/analysis/" in relative:
        return "analysis_code"
    return "package"


def collect() -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for path in sorted(PREPRINT.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix in SKIP_SUFFIXES or SKIP_PARTS & set(path.parts):
            continue
        # Generated package-metadata files describe each other; hashing them
        # here would make the output depend on generation order.
        if path.name in {"checksums.sha256", "checksums.json", "release_manifest.json"}:
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()
        entries.append((sha256_file(path), relative, role_for(relative)))
    for relative in EXTERNAL_INPUTS:
        path = REPO_ROOT / relative
        entries.append((sha256_file(path), relative, role_for(relative)))
    return sorted(entries, key=lambda item: item[1])


def main() -> int:
    entries = collect()
    OUTPUT.write_text("".join(f"{digest}  {relative}\n" for digest, relative, _ in entries), encoding="utf-8")
    grouped: dict[str, dict[str, str]] = {}
    for digest, relative, role in entries:
        grouped.setdefault(role, {})[relative] = digest
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "artifact_id": "preprint-v1.0-checksums",
                "algorithm": "sha256",
                "file_count": len(entries),
                "files_by_role": grouped,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    counts = {role: len(files) for role, files in sorted(grouped.items())}
    print(f"hashed {len(entries)} files")
    for role, count in counts.items():
        print(f"  {role:16s} {count}")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT).as_posix()}")
    print(f"wrote {OUTPUT_JSON.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
