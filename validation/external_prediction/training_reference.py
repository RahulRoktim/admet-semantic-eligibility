"""Reconstruct validation-only structure indexes from ADMET-AI's TDC sources.

The ADMET-AI v2.0.1 reproduction scripts deduplicate each endpoint by exact
source SMILES using ``dict(zip(smiles, targets))`` and then sort the resulting
SMILES.  This module intentionally reproduces that behavior before adding
RDKit identifiers.  It does not claim to recover Chemprop's per-replicate
train/validation/test assignments, which are not published with the wheel.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.Chem.MolStandardize import rdMolStandardize


PYTDC_VERSION = "1.1.15"
ADMET_AI_VERSION = "2.0.1"
ADMET_AI_SOURCE_COMMIT = "c65bf0418e19c65d7228f9e40da5d0152aade756"
RETRIEVAL_DATE = "2026-08-28"


@dataclass(frozen=True)
class TrainingDataset:
    output_name: str
    raw_filename: str
    dataverse_file_id: int
    package_documented_size: int
    target_semantics: str
    target_units: str
    target_transform: str
    species: str

    @property
    def source_url(self) -> str:
        return f"https://dataverse.harvard.edu/api/access/datafile/{self.dataverse_file_id}"


TRAINING_DATASETS: tuple[TrainingDataset, ...] = (
    TrainingDataset("Caco2_Wang", "Caco2_Wang_get_data.csv", 4259569, 906, "Caco-2 apparent permeability", "log10(cm/s)", "Source target used as supplied", "human cell line"),
    TrainingDataset("Clearance_Hepatocyte_AZ", "Clearance_Hepatocyte_AZ_get_data.csv", 4266187, 1020, "Intrinsic clearance in hepatocytes", "uL/min/10^6 cells", "Source target used as supplied", "human and rat"),
    TrainingDataset("Clearance_Microsome_AZ", "Clearance_Microsome_AZ_get_data.csv", 4266186, 1102, "Intrinsic clearance in liver microsomes", "uL/min/mg", "Source target used as supplied", "human"),
    TrainingDataset("Half_Life_Obach", "Half_Life_Obach_get_data.csv", 4266799, 665, "In-vivo elimination half-life", "hours", "Source target used as supplied", "human"),
    TrainingDataset("HydrationFreeEnergy_FreeSolv", "HydrationFreeEnergy_FreeSolv_get_data.csv", 4259594, 642, "Hydration free energy", "kcal/mol", "Source target used as supplied", "not applicable"),
    TrainingDataset("LD50_Zhu", "LD50_Zhu_get_data.csv", 4267146, 7342, "Acute toxicity LD50", "log10(1/(mol/kg))", "Source target used as supplied", "rat"),
    TrainingDataset("Lipophilicity_AstraZeneca", "Lipophilicity_AstraZeneca_get_data.csv", 4259595, 4200, "Distribution coefficient at pH 7.4", "logD", "Source target used as supplied", "not applicable"),
    TrainingDataset("PPBR_AZ", "PPBR_AZ_get_data.csv", 6413140, 1614, "Plasma protein binding", "% bound", "Source target used as supplied", "human"),
    TrainingDataset("Solubility_AqSolDB", "Solubility_AqSolDB_get_data.csv", 4259610, 9980, "Aqueous solubility", "log10(mol/L)", "Source target used as supplied", "not applicable"),
    TrainingDataset("VDss_Lombardo", "VDss_Lombardo_get_data.csv", 4267387, 1111, "Steady-state volume of distribution", "L/kg", "Source target used as supplied", "human"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_parent(mol: Chem.Mol) -> Chem.Mol:
    cleaned = rdMolStandardize.Cleanup(mol)
    parent = rdMolStandardize.FragmentParent(cleaned)
    parent = rdMolStandardize.Uncharger().uncharge(parent)
    # Some recent RDKit builds return an unsanitized molecule from Uncharger.
    # Re-sanitizing makes ring-dependent Murcko extraction deterministic.
    Chem.SanitizeMol(parent)
    return parent


def structure_identifiers(original_smiles: str) -> dict[str, str]:
    """Return deterministic identifiers without changing the source string."""
    mol = Chem.MolFromSmiles(original_smiles)
    if mol is None:
        return {
            "canonical_smiles": "",
            "isomeric_smiles": "",
            "inchikey": "",
            "parent_canonical_smiles": "",
            "parent_isomeric_smiles": "",
            "parent_inchikey": "",
            "murcko_scaffold": "",
            "structure_parse_status": "INVALID_SMILES",
        }

    parent = _clean_parent(mol)
    scaffold_mol = MurckoScaffold.GetScaffoldForMol(parent)
    return {
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True, isomericSmiles=False),
        "isomeric_smiles": Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True),
        "inchikey": Chem.MolToInchiKey(mol),
        "parent_canonical_smiles": Chem.MolToSmiles(parent, canonical=True, isomericSmiles=False),
        "parent_isomeric_smiles": Chem.MolToSmiles(parent, canonical=True, isomericSmiles=True),
        "parent_inchikey": Chem.MolToInchiKey(parent),
        "murcko_scaffold": Chem.MolToSmiles(scaffold_mol, canonical=True, isomericSmiles=False),
        "structure_parse_status": "PARSED",
    }


def reconstruct_endpoint_rows(raw_path: Path, source_dataset: str) -> list[dict[str, Any]]:
    """Reproduce ADMET-AI source-SMILES deduplication and annotate structures."""
    with raw_path.open("r", encoding="utf-8-sig", newline="") as handle:
        raw_rows = list(csv.DictReader(handle))
    required = {"Drug", "Y"}
    if not raw_rows or not required.issubset(raw_rows[0]):
        raise ValueError(f"{raw_path} must contain Drug and Y columns")

    last_target: dict[str, str] = {}
    source_ids: dict[str, list[str]] = {}
    for row_number, row in enumerate(raw_rows, start=1):
        smiles = row["Drug"]
        last_target[smiles] = row["Y"]
        source_ids.setdefault(smiles, []).append(str(row_number))

    records: list[dict[str, Any]] = []
    for position, smiles in enumerate(sorted(last_target), start=1):
        records.append(
            {
                "source_dataset": source_dataset,
                "source_row_id": f"{source_dataset}:{position:05d}",
                "source_raw_row_ids": ";".join(source_ids[smiles]),
                "source_duplicate_count": len(source_ids[smiles]),
                "original_smiles": smiles,
                "source_target": last_target[smiles],
                **structure_identifiers(smiles),
            }
        )
    return records


INDEX_FIELDS = (
    "source_dataset",
    "source_row_id",
    "source_raw_row_ids",
    "source_duplicate_count",
    "original_smiles",
    "canonical_smiles",
    "isomeric_smiles",
    "inchikey",
    "parent_canonical_smiles",
    "parent_isomeric_smiles",
    "parent_inchikey",
    "murcko_scaffold",
    "structure_parse_status",
    "source_target",
)


def _write_rows(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_training_reference(raw_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Build all regression-task source indexes and a hash manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets: list[dict[str, Any]] = []
    for definition in TRAINING_DATASETS:
        raw_path = raw_dir / definition.raw_filename
        if not raw_path.is_file():
            raise FileNotFoundError(f"Missing pinned PyTDC materialization: {raw_path}")
        rows = reconstruct_endpoint_rows(raw_path, definition.output_name)
        output_path = output_dir / f"{definition.output_name}.csv"
        _write_rows(output_path, rows)
        datasets.append(
            {
                "admet_ai_output_name": definition.output_name,
                "prediction_type": "regression",
                "source_training_dataset": definition.output_name,
                "training_dataset_version": f"PyTDC {PYTDC_VERSION} retrieval on {RETRIEVAL_DATE}",
                "training_smiles_available": True,
                "training_split_available": False,
                "training_structure_count": len(rows),
                "package_documented_size": definition.package_documented_size,
                "raw_row_count": sum(int(row["source_duplicate_count"]) for row in rows),
                "valid_structure_count": sum(row["structure_parse_status"] == "PARSED" for row in rows),
                "target_semantics": definition.target_semantics,
                "target_units": definition.target_units,
                "target_transform": definition.target_transform,
                "positive_class_definition_if_classification": "NOT_APPLICABLE",
                "species": definition.species,
                "source_url": definition.source_url,
                "raw_path": str(raw_path),
                "raw_sha256": sha256_file(raw_path),
                "reference_path": str(output_path),
                "reference_sha256": sha256_file(output_path),
            }
        )

    manifest = {
        "schema_version": "v0.10.2-training-reference-1",
        "generated_at": RETRIEVAL_DATE,
        "admet_ai": {
            "package_version": ADMET_AI_VERSION,
            "source_commit": ADMET_AI_SOURCE_COMMIT,
            "training_architecture": "Two multitask Chemprop ensembles (regression and classification), five replicates each",
            "preprocessing_reconstruction": "Exact source SMILES deduplicated with last target retained, then sorted, matching prepare_tdc_admet_all.py",
            "split_status": "UNKNOWN_PER_REPLICATE",
            "split_reason": "Public scripts invoke Chemprop defaults and published wheel checkpoints do not retain row-level split assignments.",
            "multitask_exposure_note": "Each regression checkpoint was trained on the union of regression-task structures with sparse endpoint labels. Endpoint source overlap and any-regression-task structure exposure must be reported separately.",
        },
        "pytdc_version": PYTDC_VERSION,
        "license": "CC BY 4.0 per TDC dataset pages; retrieved CSV materializations contain no embedded license text",
        "datasets": datasets,
    }
    manifest_path = output_dir.parent / "admet_ai_training_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_training_reference(args.raw_dir, args.output_dir)
    print(json.dumps({"datasets": len(manifest["datasets"]), "manifest": str(args.output_dir.parent / "admet_ai_training_manifest.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
