# Reproducing the external-validation preprint

Reproduction is offered at two levels.

| | Level 1 — reproduce the published paper | Level 2 — reconstruct from upstream data |
| --- | --- | --- |
| **Goal** | regenerate every manuscript number, table, figure and robustness output | independently rebuild the inputs that are not redistributed, and confirm they give the published results |
| **Inputs** | committed, redistributable artefacts only | official upstream datasets, obtained by you |
| **Network** | **not required** | required |
| **Model inference** | not required | optional (one 36-row sensitivity run) |
| **Runtime** | ~2 minutes | ~15 minutes plus download time |

Both levels are deterministic. Nothing under `validation/`, `docs/` or
`backend/` is modified by any command below; the analysis reads those paths and
writes only under `preprint/`.

---

## Why there are two levels

The reconstructed Therapeutics Data Commons reference tables
(`validation/external_prediction/training_reference/*.csv`) carry upstream
structure–target pairs whose licensing provenance we could not establish with
confidence. The TDC dataset pages indicate CC BY 4.0 at the collection level,
but several of the endpoints we use originate from AstraZeneca data deposited
in ChEMBL, which ChEMBL distributes under CC BY-SA 3.0, and the retrieved CSV
materialisations carry no embedded licence text.

Rather than assume a permissive licence and relicense third-party data, **we do
not redistribute those tables**. Structure-only variants are treated the same
way; we do not invent a distinction between structures and targets for this
source.

**This is a licensing-aware reproducibility boundary, not a reproducibility
failure.** Everything needed to verify the published results offline is
released, and everything needed to rebuild the withheld inputs from their
official source is documented. See `DATA_LICENSES.md` §3.

---

## Level 1 — Reproduce the published paper

Uses only committed, redistributable artefacts. No network access.

### 1.1 Environment

Python 3.12. From the repository root:

```
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements-dev.txt
venv/Scripts/python.exe -m pip install -r preprint/requirements-analysis.txt
```

Verified on Windows 11, Python 3.12.10, RDKit 2026.3.5, NumPy 2.5.2,
SciPy 1.18.1, matplotlib 3.11.1. All commands assume `PYTHONPATH=backend`.

### 1.2 Inputs consumed

| Input | Licence |
| --- | --- |
| `validation/external_prediction/results/asap_processed_predictions.csv` | derived from ASAP (CC0-1.0) |
| `validation/external_prediction/results/biogen_hppb_processed_predictions.csv` | derived from Biogen (MIT) |
| `validation/external_prediction/endpoint_compatibility.csv` | this project (CC BY 4.0) |
| `preprint/results/hlm_low_clearance_predictions.csv` | derived from ASAP (CC0-1.0) |
| `preprint/results/training_reference_summary.json` | derived aggregates computed by this project; contains no upstream structure or target |

### 1.3 Run the analysis

```
PYTHONPATH=backend python preprint/analysis/run_preprint_analysis.py
```

This verifies every frozen input against
`preprint/results/frozen_input_manifest.json`, then recomputes all previously
published v0.10.2 metrics from the frozen prediction rows and **aborts without
writing** if any value differs by more than 1e-9. On success it writes:

| Output | Contents |
| --- | --- |
| `preprint/results/preprint_analysis.json` | every cohort, metric, interval, baseline and shift statistic |
| `preprint/results/analysis_summary.md` | human-readable summary |
| `preprint/results/analysis_manifest.json` | input and output hashes |
| `preprint/tables/table1_compatibility.csv` | Table 1 |
| `preprint/tables/table2_external_results.csv` | Table 2 |
| `preprint/tables/supplementary_sensitivity.csv` | all sensitivity cohorts |

### 1.4 Generate figures

```
PYTHONPATH=backend python preprint/figures/make_figures.py
```

Figures 1–3 as PNG (300 dpi) and PDF, plus
`preprint/results/figure_manifest.json`. Every value and annotation is read
from `preprint_analysis.json`, the committed prediction CSVs or the derived
training summary. No scientific content is added or edited by hand.

### 1.5 Verify

```
PYTHONPATH=backend python -m pytest preprint/tests -q
PYTHONPATH=backend python preprint/analysis/verify_manuscript_claims.py
PYTHONPATH=backend python preprint/analysis/release_package.py --check
PYTHONPATH=backend python preprint/analysis/write_checksums.py
```

- The test suite covers metric definitions, degenerate inputs, structure
  aggregation, stereochemical flagging, bootstrap determinism, the reproduction
  gate (including that it aborts on a mutated prediction), the licensing
  boundary, and the release-package check.
- The claim verifier parses the numeric claims out of `manuscript.md` and
  compares each against `preprint_analysis.json`. It also fails if a forbidden
  claim appears or a required disclosure is missing.
- The release check fails if any non-redistributed file has entered the
  release set, or if a supplied `.zip` contains one.

To confirm nothing in the wider repository regressed:

```
PYTHONPATH=backend python -m pytest backend/tests validation/tests preprint/tests -q
```

### 1.6 Determinism

Running 1.3, 1.4 and `write_checksums.py` twice in succession reproduces every
artefact **byte-for-byte**, verified on the reference environment. Figure
containers are written with pinned metadata so no creation timestamp is
embedded.

| Parameter | Value |
| --- | --- |
| Bootstrap seed | 20260828 |
| Bootstrap replicates | 2000 |
| Confidence level | 0.95 |
| Fingerprint | Morgan, radius 2, 2048 bits, Tanimoto |
| Structurally-remote similarity threshold | 0.60 |
| Reproduction tolerance | 1e-9 |

Seed, replicate count, fingerprint parameters and cohort rules are imported
from `validation/external_prediction/benchmark_core.py` rather than redefined,
so the preprint analysis cannot drift from the benchmark it re-analyses.

---

## Level 2 — Reconstruct from the original upstream datasets

Rebuilds the inputs that are not redistributed, then confirms they reproduce
the published results. Requires network access.

### 2.1 Obtain the upstream datasets

**Therapeutics Data Commons ADMET regression sources.** Ten datasets, retrieved
via PyTDC 1.1.15 from Harvard Dataverse. Dataset names, Dataverse file
identifiers, documented row counts, target semantics, units and species are all
published in `validation/external_prediction/admet_ai_training_manifest.json`:

| ADMET-AI output | Dataverse file id | Documented size | Target semantics | Units |
| --- | ---: | ---: | --- | --- |
| `Caco2_Wang` | 4259569 | 906 | Caco-2 apparent permeability | log10(cm/s) |
| `Clearance_Hepatocyte_AZ` | 4266187 | 1020 | intrinsic clearance, hepatocytes | µL/min/10⁶ cells |
| `Clearance_Microsome_AZ` | 4266186 | 1102 | intrinsic clearance, liver microsomes | µL/min/mg |
| `Half_Life_Obach` | 4266799 | 665 | in vivo elimination half-life | hours |
| `HydrationFreeEnergy_FreeSolv` | 4259594 | 642 | hydration free energy | kcal/mol |
| `LD50_Zhu` | 4267146 | 7342 | acute toxicity LD50 | log10(1/(mol/kg)) |
| `Lipophilicity_AstraZeneca` | 4259595 | 4200 | distribution coefficient at pH 7.4 | logD |
| `PPBR_AZ` | 6413140 | 1614 | plasma protein binding | % bound |
| `Solubility_AqSolDB` | 4259610 | 9980 | aqueous solubility | log10(mol/L) |
| `VDss_Lombardo` | 4267387 | 1111 | steady-state volume of distribution | L/kg |

Base URL: `https://dataverse.harvard.edu/api/access/datafile/<id>`.
Retrieval date used in this study: 2026-08-28. Observe each dataset's own
licence and cite its originating publication (see the manuscript references).

**ASAP and Biogen snapshots** are already committed under their own licences
and need not be re-obtained.

**Temporal ChEMBL Caco-2 set** (optional, contributes no reported metric):
`https://github.com/Duke-W91/Caco2_prediction` at commit
`a8eb8cf3c8841ceb5c545d403e35d7b3ade9ba0a`, path
`curated_caco2_data/external_set`. Not redistributed — no licence is stated in
that repository.

### 2.2 Verify dataset and version identity

Before reconstructing, confirm you have the same material:

- PyTDC version must be **1.1.15**; ADMET-AI **2.0.1** (source commit
  `c65bf0418e19c65d7228f9e40da5d0152aade756`).
- Row counts must match the "documented size" column above.
- After reconstruction (§2.3), the SHA-256 of each rebuilt table must match
  the corresponding entry in
  `preprint/results/training_reference_summary.json` → `upstream_tables_sha256`.
  Those hashes pin the exact files used in this study **without redistributing
  them**.

### 2.3 Reconstruct the reference tables

Schema, one row per deduplicated source structure:

```
source_dataset, source_row_id, source_raw_row_ids, source_duplicate_count,
original_smiles, canonical_smiles, isomeric_smiles, inchikey,
parent_canonical_smiles, parent_isomeric_smiles, parent_inchikey,
murcko_scaffold, structure_parse_status, source_target
```

Reconstruction procedure — this reproduces ADMET-AI's own preprocessing:

1. Deduplicate by **exact source SMILES**, retaining the last target
   (`dict(zip(smiles, targets))`), then sort by SMILES. This matches
   `prepare_tdc_admet_all.py` in the ADMET-AI source.
2. For each retained row derive the RDKit identifiers: canonical and isomeric
   SMILES; InChIKey; the parent form after `rdMolStandardize.Cleanup`,
   `FragmentParent` and `Uncharger().uncharge`, re-sanitised; and the
   Bemis–Murcko scaffold of the parent.
3. Write one CSV per endpoint into
   `validation/external_prediction/training_reference/<output_name>.csv`.

The code that performs steps 1–3 is released:
`validation/external_prediction/training_reference.py`.

```
PYTHONPATH=backend python validation/external_prediction/training_reference.py --help
```

### 2.4 Rebuild overlap annotation and baselines

```
PYTHONPATH=backend python preprint/analysis/build_training_reference_summary.py
```

This is the **only** consumer of the reference tables. It recomputes the
training-label aggregates, the binned label density, the Kolmogorov–Smirnov
label-shift statistic, the training-mean / training-median /
1-nearest-neighbour baseline metrics, and the structural overlap annotation for
the 36 low-clearance sensitivity rows. It writes
`preprint/results/training_reference_summary.json`, which contains no upstream
structure, no upstream target value and no structure–target pair.

### 2.5 Compare against the frozen published results

```
PYTHONPATH=backend python preprint/analysis/build_training_reference_summary.py --compare
```

Compares a freshly rebuilt summary against the committed one, field by field,
to 1e-9, and reports any difference instead of overwriting. Then re-run Level 1
(§1.3–1.5): the reproduction gate independently re-checks every published
v0.10.2 metric.

### 2.6 Optional — regenerate the low-clearance predictions

The only step that performs model inference. Its output is already committed,
so this is needed only to verify it independently.

```
PYTHONPATH=backend python preprint/analysis/hlm_low_clearance_sensitivity.py
```

Requires `admet-ai==2.0.1` installed locally. It downloads no data but loads
local model weights, and refuses to run on any row the frozen benchmark already
predicted.

---

## What is and is not redistributed

| Item | Status |
| --- | --- |
| ASAP Discovery Antiviral ADMET 2025 unblinded snapshot | redistributed, CC0-1.0, SHA-256 recorded |
| Biogen Computational-ADME public set | redistributed, MIT, SHA-256 recorded |
| Reconstructed TDC reference tables (10 files) | **not redistributed** — ambiguous upstream provenance; rebuild via Level 2, hashes published |
| Temporal ChEMBL Caco-2 set | **not redistributed** — no licence stated upstream; contributes no reported metric |
| ADMET-AI 2.0.1 model weights | not redistributed; installed from PyPI |

`preprint/release_manifest.json` classifies every file in the release, and
`release_package.py --check` fails if an excluded file is ever packaged.

## Verified clean-clone sequence

This exact sequence was executed against a fresh clone of this repository at its
root commit, with the non-redistributed reference tables absent — the state every
reader is in.

```
git clone https://github.com/<owner>/admet-semantic-eligibility
cd admet-semantic-eligibility

python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements-dev.txt
venv/Scripts/python.exe -m pip install -r preprint/requirements-analysis.txt

export PYTHONUTF8=1
export PYTHONPATH=backend

python preprint/analysis/run_preprint_analysis.py
python preprint/figures/make_figures.py
python preprint/analysis/verify_manuscript_claims.py
python preprint/analysis/release_package.py --check
python preprint/analysis/write_checksums.py
python preprint/analysis/final_audit.py
python -m pytest preprint/tests -q
```

Observed result:

| Check | Outcome in the fresh clone |
| --- | --- |
| Files checked out byte-identical to `checksums.sha256` | **74 / 74** |
| Frozen inputs | 10 verified, 10 absent by redistribution policy (expected) |
| Reproduction gate | `ALL_PUBLISHED_METRICS_REPRODUCED` |
| Compatibility screening | 3/12 accepted |
| Headline metrics | clearance n=366 R² −0.156; logD n=474 R² +0.368; PPB n=178 R² +0.642 |
| Tables 1–2 and supplementary sensitivity | regenerated |
| Figures 1–3 | regenerated, **6/6 image files byte-identical** |
| Regenerated artefacts vs committed | **74 / 74 byte-identical** |
| Manuscript claims | 115 verified, 16 forbidden phrases absent, 10 disclosures present |
| Release check | passed; 10 files absent by redistribution policy |
| Final audit | 19 checks, 0 failed |
| Tests | 103 passed |

`preprint/analysis/build_training_reference_summary.py` correctly refuses to run
in this environment, naming `DATA_LICENSES.md` and Level 2 of this document. That
is intended: Level 2 requires data the reader must obtain themselves.

The whole package is checked out verbatim — `.gitattributes` disables end-of-line
translation — so `preprint/results/checksums.sha256` is meaningful on every
platform, and Level 1's SHA-256 verification of frozen inputs cannot fail for
line-ending reasons.

Two files legitimately differ if you re-run the audit: `preprint/FINAL_AUDIT.md`
and `preprint/results/final_audit.json` record the timestamp and commit at which
the audit ran.

## Known environment sensitivities

- RDKit emits `Unusual charge on atom 0 number of radical electrons set to
  zero` for a small number of structures during standardisation. This is
  informational and does not change identifiers or predictions.
- Bootstrap intervals are reproducible bit-for-bit on the same NumPy version.
  A different NumPy generator implementation could shift interval endpoints in
  the last decimal places; point estimates are unaffected.
- Figures render with the DejaVu Sans font bundled with matplotlib. A different
  font changes glyph metrics only.
