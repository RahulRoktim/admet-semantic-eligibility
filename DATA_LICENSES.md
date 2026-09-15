# Data licences and redistribution status

Every external dataset touched by this project is recorded separately below.
**No third-party dataset is relicensed by this project.** Each remains under its
own upstream terms. The MIT licence in `LICENSE` covers project code only, and
the CC BY 4.0 licence in `CONTENT_LICENSE.md` covers project-authored writing
and figures only.

Redistribution status uses these values:

| Status | Meaning |
| --- | --- |
| `REDISTRIBUTED` | the material is included in the public release under its upstream licence |
| `DERIVED_ONLY` | only this project's derived results are released; the source material is not |
| `UPSTREAM_REFERENCE_ONLY` | the material is not released at all; instructions to obtain it are provided |

---

## 1. ASAP Discovery Antiviral ADMET 2025 (unblinded)

| Field | Value |
| --- | --- |
| **Source** | Polaris Hub — <https://polarishub.io/datasets/asap-discovery/antiviral-admet-2025-unblinded> |
| **Authors / organisation** | ASAP Discovery Consortium / OpenADMET |
| **Version** | Polaris artifact created 2025-03-28; Zarr manifest md5 `aaa74d41fc3483acb7fd24458d7375d3` |
| **Retrieval date** | 2026-08-28 |
| **Original licence** | **CC0-1.0** (public domain dedication) |
| **Material included in our release** | the raw snapshot, byte-identical: `validation/external_prediction/source_snapshots/asap_antiviral_admet_2025_unblinded.csv` (560 rows, 499 unique structures), SHA-256 `07e7c68d59a720338ff44277625f0ff52be5e0a1afd556134807ba7530213582` |
| **Redistribution** | `REDISTRIBUTED` |
| **Attribution requirements** | None legally required under CC0. We nonetheless cite the dataset and credit ASAP Discovery / OpenADMET in the manuscript, as good scientific practice. |
| **Provenance** | Recorded in `validation/external_prediction/external_dataset_manifest.json` with raw and processed file hashes; hash equality is asserted by test. |
| **Notes** | Structures are supplied as CXSMILES; 235 of 560 records carry OR/AND enhanced-stereo groups. This is a scientific caveat discussed in the manuscript, not a licensing one. |

## 2. Biogen Computational-ADME public set

| Field | Value |
| --- | --- |
| **Source** | <https://github.com/molecularinformatics/Computational-ADME> |
| **Authors / organisation** | Biogen (Fang et al.) |
| **Version** | commit `b00df003de117ce9e5b381afd886095c5f2af2d5`, file `ADME_public_set_3521.csv` |
| **Retrieval date** | 2026-08-28 |
| **Original licence** | **MIT** |
| **Material included in our release** | the raw snapshot, byte-identical: `validation/external_prediction/source_snapshots/biogen_ADME_public_set_3521.csv` (3,521 rows), SHA-256 `2cfabc2667740c224487876c33b23124159ef43294e0f9e4d926cb6276c95a3b` |
| **Redistribution** | `REDISTRIBUTED` |
| **Attribution requirements** | The MIT licence requires the copyright notice and permission notice to accompany redistribution. The upstream notice is reproduced in `THIRD_PARTY_LICENSES.md`. The associated publication is cited in the manuscript. |
| **Provenance** | Recorded in `external_dataset_manifest.json` with raw and processed hashes; asserted by test. |
| **Notes** | Only the human plasma protein binding column passed the semantic eligibility screen. 3,327 of 3,521 rows carry no human PPB label. |

## 3. Reconstructed Therapeutics Data Commons ADMET regression reference tables

| Field | Value |
| --- | --- |
| **Source** | Therapeutics Data Commons (TDC), materialised via PyTDC 1.1.15 from Harvard Dataverse file identifiers recorded in `validation/external_prediction/admet_ai_training_manifest.json` |
| **Authors / organisation** | TDC (Huang et al.) as distributor; the ten underlying datasets have distinct originating authors, including AstraZeneca depositions routed through ChEMBL |
| **Version** | PyTDC 1.1.15; reconstruction reproduces ADMET-AI 2.0.1's own preprocessing (source commit `c65bf0418e19c65d7228f9e40da5d0152aade756`) |
| **Retrieval date** | 2026-08-28 |
| **Original licence** | **AMBIGUOUS.** The TDC dataset pages indicate CC BY 4.0 at the collection level, and the retrieved CSV materialisations carry no embedded licence text. Several endpoints (`Clearance_Microsome_AZ`, `Clearance_Hepatocyte_AZ`, `Lipophilicity_AstraZeneca`, `PPBR_AZ`) originate from AstraZeneca data deposited in ChEMBL, which ChEMBL distributes under **CC BY-SA 3.0**. We have not been able to establish, from an authoritative per-dataset source, which licence governs each file. |
| **Material included in our release** | **None of the source tables.** Only a derived summary: `preprint/results/training_reference_summary.json`, containing aggregate label statistics (n, mean, median, standard deviation), a 42-bin label density, this project's own baseline error metrics, the Kolmogorov–Smirnov label-shift statistic, and structural overlap annotation for 36 rows. It contains **no upstream structure, no upstream target value and no structure–target pair**; this is asserted by test. |
| **Redistribution** | `UPSTREAM_REFERENCE_ONLY` for the tables; `DERIVED_ONLY` for the summary. The ten files `validation/external_prediction/training_reference/*.csv` are **excluded from the public release**. |
| **Attribution requirements** | Cite TDC and the originating dataset publications; cite ChEMBL where applicable. All are cited in the manuscript. |
| **Provenance** | The excluded tables are hashed in `training_reference_summary.json` under `upstream_tables_sha256`, so a reconstruction can be verified against the exact files used in this study without those files being redistributed. Dataset names, Dataverse file identifiers, documented row counts and the reconstruction procedure are published in `admet_ai_training_manifest.json` and `preprint/REPRODUCE.md` (Level 2). |
| **Notes / ambiguities** | This is the one genuinely unresolved licensing question in the project. Rather than assume a permissive licence, we do not redistribute. This is a deliberate, documented boundary, not a reproducibility failure: Level 2 of `REPRODUCE.md` lets any reader obtain the upstream data themselves and rebuild the excluded tables, then verify the rebuild against the committed hashes and the committed derived summary. Structure-only variants of these tables are treated identically and are also not released; we do not distinguish between structures and targets for this source. |

## 4. Temporal ChEMBL Caco-2 apparent-permeability set (2022–2023)

| Field | Value |
| --- | --- |
| **Source** | <https://github.com/Duke-W91/Caco2_prediction>, `curated_caco2_data/external_set` |
| **Authors / organisation** | authors of the linked publication (see manuscript references) |
| **Version** | commit `a8eb8cf3c8841ceb5c545d403e35d7b3ade9ba0a` |
| **Retrieval date** | 2026-08-28 |
| **Original licence** | **None stated in the source repository.** |
| **Material included in our release** | None. The files are hash-pinned in `external_dataset_manifest.json` (raw `2caf3a…46cf6`, processed `4f62e9…c08a`) but their bytes are not committed. |
| **Redistribution** | `UPSTREAM_REFERENCE_ONLY` |
| **Attribution requirements** | Publication cited in the manuscript. |
| **Provenance** | Hash-pinned only. |
| **Notes** | This pairing was rejected by the eligibility screen as `INSUFFICIENT_METADATA` and contributes **no reported metric**. Excluding it costs the study nothing. |

## 5. ADMET-AI model weights

| Field | Value |
| --- | --- |
| **Source** | `admet-ai` 2.0.1 on PyPI |
| **Original licence** | MIT (see `THIRD_PARTY_LICENSES.md`) |
| **Material included in our release** | None. The package is installed from PyPI by the reader. |
| **Redistribution** | `UPSTREAM_REFERENCE_ONLY` |
| **Notes** | Model outputs computed by this project are released as derived results. |

---

## Derived artefacts containing third-party-derived values

These are released under `CONTENT_LICENSE.md` **as this project's arrangement
and computation only**, with no claim over the underlying data:

| Artefact | Derived from | Notes |
| --- | --- | --- |
| `validation/external_prediction/results/asap_processed_predictions.csv` | ASAP (CC0) + local model inference | Contains ASAP measurement values and, in `maximum_training_similarity_smiles`, the SMILES of the single nearest training structure per row — a structure identifier with no associated target value. See the open question below. |
| `validation/external_prediction/results/biogen_hppb_processed_predictions.csv` | Biogen (MIT) + local model inference | Same structure as above. |
| `preprint/results/hlm_low_clearance_predictions.csv` | ASAP (CC0) + local model inference | Derived from a CC0 source; no restriction. |
| `preprint/results/training_reference_summary.json` | TDC reference tables (ambiguous) | Aggregates only; verified free of upstream structures and targets. |
| `preprint/results/preprint_analysis.json`, `preprint/tables/*.csv` | all of the above | Metrics and summary statistics only. |

### Open question flagged for the copyright holder

The two frozen prediction tables inherited from the v0.10.2 benchmark contain a
derived column, `maximum_training_similarity_smiles`, which names the nearest
training structure for each external row (313 and 413 distinct structures
respectively, with **no target values attached**). These are structure
identifiers produced by an analysis, not an extract of the dataset, and they
cannot be used to reconstruct any label.

We judged this to fall outside the redistribution boundary that applies to the
reference tables themselves, and it is therefore released. If you prefer the
stricter reading, the column can be redacted from the release copies; doing so
would require regenerating the frozen input manifest and would break byte-level
continuity with the v0.10.2 artefacts, so it has not been done unilaterally.

---

## Summary

| Dataset | Licence | Redistributed? |
| --- | --- | --- |
| ASAP Discovery Antiviral ADMET 2025 | CC0-1.0 | Yes |
| Biogen Computational-ADME public set | MIT | Yes |
| TDC reconstructed reference tables | Ambiguous (CC BY 4.0 vs CC BY-SA 3.0) | **No** — derived summary only |
| Temporal ChEMBL Caco-2 set | None stated | **No** — hash-pinned only |
| ADMET-AI weights | MIT | No — installed from PyPI |
