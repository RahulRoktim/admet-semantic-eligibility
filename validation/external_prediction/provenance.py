"""Build and verify the v0.10.2 external-dataset provenance manifest."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from validation.external_prediction.training_reference import sha256_file, structure_identifiers


EXPECTED_HASHES = {
    "asap_antiviral_admet_2025_unblinded.csv": "07e7c68d59a720338ff44277625f0ff52be5e0a1afd556134807ba7530213582",
    "biogen_ADME_public_set_3521.csv": "2cfabc2667740c224487876c33b23124159ef43294e0f9e4d926cb6276c95a3b",
    "chembl_Papp_2022_2023_raw.txt": "2caf3a0805ae1c50a45144fee8d19dba9bd6a4c25b8636ef63cb70b34d146cf6",
    "logPapp_external_set.csv": "4f62e941808834376f1c6b2f92d030f398889e4446ccdd1d33d30e88e288c08a",
}


def _read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def _unique_structures(rows: list[dict[str, str]], smiles_field: str) -> tuple[int, int]:
    parsed: set[str] = set()
    invalid = 0
    for row in rows:
        identifiers = structure_identifiers(row[smiles_field])
        if identifiers["structure_parse_status"] == "PARSED":
            parsed.add(identifiers["isomeric_smiles"])
        else:
            invalid += 1
    return len(parsed), invalid


def _verified_hash(path: Path) -> str:
    actual = sha256_file(path)
    expected = EXPECTED_HASHES[path.name]
    if actual != expected:
        raise ValueError(f"Raw source changed: {path.name}; expected {expected}, got {actual}")
    return actual


def build_source_manifest(snapshot_dir: Path, caco2_dir: Path, output: Path) -> dict[str, Any]:
    asap_path = snapshot_dir / "asap_antiviral_admet_2025_unblinded.csv"
    biogen_path = snapshot_dir / "biogen_ADME_public_set_3521.csv"
    caco_raw_path = caco2_dir / "chembl_Papp_2022_2023_raw.txt"
    caco_processed_path = caco2_dir / "logPapp_external_set.csv"
    for path in (asap_path, biogen_path, caco_raw_path, caco_processed_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing external source snapshot: {path}")
        _verified_hash(path)

    asap = _read_csv(asap_path)
    biogen = _read_csv(biogen_path)
    caco_raw = _read_csv(caco_raw_path, delimiter="\t")
    caco_processed = _read_csv(caco_processed_path)
    asap_unique, asap_invalid = _unique_structures(asap, "CXSMILES")
    biogen_unique, biogen_invalid = _unique_structures(biogen, "SMILES")
    caco_unique, caco_invalid = _unique_structures(caco_raw, "Smiles")
    caco_processed_unique, caco_processed_invalid = _unique_structures(caco_processed, "smiles")

    manifest = {
        "schema_version": "v0.10.2-external-provenance-1",
        "retrieval_date": "2026-08-28",
        "datasets": [
            {
                "dataset_id": "asap-antiviral-admet-2025-unblinded",
                "dataset_name": "ASAP Discovery Antiviral ADMET 2025 Unblinded",
                "dataset_version": "Polaris artifact created 2025-03-28; Zarr manifest md5 aaa74d41fc3483acb7fd24458d7375d3",
                "source": "https://polarishub.io/datasets/asap-discovery/antiviral-admet-2025-unblinded",
                "retrieval_date": "2026-08-28",
                "license": "CC0-1.0",
                "publication": "ASAP/OpenADMET blind prediction challenge and linked experimental protocols",
                "raw_file": str(asap_path),
                "raw_file_hash": _verified_hash(asap_path),
                "processed_file_hash": "PENDING_BENCHMARK_PROCESSING",
                "experimental_origin": "Experimentally measured HLM, MLM, KSOL, LogD and MDR1-MDCKII values supplied by the challenge organizers",
                "number_of_rows_raw": len(asap),
                "number_of_unique_structures": asap_unique,
                "invalid_structure_rows": asap_invalid,
                "endpoint_list": ["HLM", "MLM", "KSOL", "LogD", "MDR1-MDCKII"],
                "known_limitations": ["Sparse endpoint labels", "HLM values below 10 uL/min/mg are not reliable exact measurements", "Original Set field must be retained"],
            },
            {
                "dataset_id": "biogen-adme-fang-3521",
                "dataset_name": "Computational-ADME public set",
                "dataset_version": "Git commit b00df003de117ce9e5b381afd886095c5f2af2d5",
                "source": "https://github.com/molecularinformatics/Computational-ADME/blob/b00df003de117ce9e5b381afd886095c5f2af2d5/ADME_public_set_3521.csv",
                "retrieval_date": "2026-08-28",
                "license": "MIT",
                "publication": "https://doi.org/10.1021/acs.jcim.3c00160",
                "raw_file": str(biogen_path),
                "raw_file_hash": _verified_hash(biogen_path),
                "processed_file_hash": "PENDING_BENCHMARK_PROCESSING",
                "experimental_origin": "Biogen experimental ADME assays disclosed with the publication",
                "number_of_rows_raw": len(biogen),
                "number_of_unique_structures": biogen_unique,
                "invalid_structure_rows": biogen_invalid,
                "endpoint_list": ["HLM", "RLM", "MDR1-MDCK efflux ratio", "solubility pH 6.8", "human PPB", "rat PPB"],
                "known_limitations": ["Endpoint coverage is sparse", "Human and rat measurements must remain distinct", "Several units/assay definitions are not compatible with ADMET-AI targets"],
            },
            {
                "dataset_id": "duke-caco2-2022-2023",
                "dataset_name": "Temporal ChEMBL Caco-2 Papp external set",
                "dataset_version": "Git commit a8eb8cf3c8841ceb5c545d403e35d7b3ade9ba0a",
                "source": "https://github.com/Duke-W91/Caco2_prediction/tree/a8eb8cf3c8841ceb5c545d403e35d7b3ade9ba0a/curated_caco2_data/external_set",
                "retrieval_date": "2026-08-28",
                "license": "NOT_STATED_IN_REPOSITORY",
                "publication": "https://doi.org/10.1186/s13321-025-00947-z",
                "raw_file": str(caco_raw_path),
                "raw_file_hash": _verified_hash(caco_raw_path),
                "processed_file": str(caco_processed_path),
                "processed_file_hash": _verified_hash(caco_processed_path),
                "experimental_origin": "ChEMBL Papp records with Document_Year 2022 or 2023",
                "number_of_rows_raw": len(caco_raw),
                "number_of_unique_structures": caco_unique,
                "invalid_structure_rows": caco_invalid,
                "number_of_rows_author_processed": len(caco_processed),
                "number_of_unique_structures_author_processed": caco_processed_unique,
                "author_processed_invalid_structure_rows": caco_processed_invalid,
                "endpoint_list": ["Papp", "author-processed logPapp"],
                "known_limitations": ["Repository has no stated data/code license", "Raw rows omit permeability direction and assay identifier/context", "Author processing excludes high-variance duplicate groups"],
                "redistribution_status": "NOT_COMMITTED; hash-pinned local audit copy only",
            },
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--caco2-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_source_manifest(args.snapshot_dir, args.caco2_dir, args.output)
    print(json.dumps({"datasets": len(manifest["datasets"]), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

