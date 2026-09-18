# What survives? Semantic eligibility in external validation of ADMET predictors

Reproducibility companion for the preprint:

> **What survives? Semantic eligibility, distribution shift and metric
> interpretation in external validation of ADMET predictors**
> Md. Rahul Reza Roktim, Department of Pharmacy, Daffodil International
> University, Dhaka, Bangladesh.

This repository contains the analysis code, the frozen result artefacts, the
figures, the tables and the manuscript. Everything reported in the paper
regenerates from committed files, offline, in about two minutes.

---

## The question

When a published ADMET predictor is evaluated against apparently suitable public
experimental datasets, **how many candidate dataset-to-output pairings are
semantically eligible for comparison at all** — and among those that are, what
explains the gap between benchmark-reported and externally observed performance?

Two records can share an endpoint name and still differ in species, assay
system, measurement direction, reported transformation and protocol. Computing
an error between such a pair produces a number, and the number is meaningless.

## The main result

**Of 12 candidate pairings, 3 were semantically eligible. 9 were not.**

A pre-specified, fail-closed screen of ten declared gates — biological endpoint,
matrix, species, assay family, measurement direction, result semantics, units,
transformation, classification threshold, positive class — was applied to twelve
candidate pairings between three public datasets and the outputs of ADMET-AI
2.0.1. **The screen ran before any metric was computed.**

Rejections, each with a written reason: 3 on species, 2 on assay system, 2 on
result semantics, 1 on unresolvable unit scaling, 1 on insufficient assay
metadata. **No classification endpoint qualified**, so no ROC-AUC, PR-AUC,
confusion matrix or Brier score appears anywhere in this work.

## The three evaluated endpoints

| Endpoint | External source | n | R² (95% CI) | Spearman ρ | Calibration slope |
| --- | --- | ---: | --- | ---: | ---: |
| Human liver microsomal clearance | ASAP Discovery antiviral ADMET 2025 | 366 | −0.156 (−0.217 to −0.108) | 0.446 | 0.037 |
| logD at pH 7.4 | ASAP Discovery antiviral ADMET 2025 | 474 | 0.368 (0.261 to 0.456) | 0.684 | 0.545 |
| Human plasma protein binding | Biogen Computational-ADME public set | 178 | 0.642 (0.543 to 0.732) | 0.807 | 0.599 |

Headline cohort excludes exact structure overlap with the endpoint training
source and with the reconstructed regression multitask universe.

## The framework: eligibility → distribution shift → range compression

External validation fails at three sequential points, and the paper quantifies
each.

**1. Eligibility.** Most apparent opportunities are not valid comparisons at all
(9 of 12 here).

**2. Label-distribution shift.** Among eligible pairings, the external labels can
come from a different regime than the training labels. For clearance, training
labels average 34.2 ± 44.8 µL/min/mg against an external 157.3 ± 236.8
(Kolmogorov–Smirnov D = 0.446). The shift is mild for logD (D = 0.095) and
intermediate for plasma protein binding (D = 0.155) — and performance orders the
same way.

**3. Prediction-range compression.** For clearance, predictions have a standard
deviation of 20.5 against an observed 236.8 (ratio 0.087) and a calibration
slope of 0.037. Observations span 10–1,620 µL/min/mg; predictions span
−27.9 to 102.8. The model cannot express the external dynamic range.

**The negative R² is not evidence the model is uninformative.** It outperforms
both a training-set-mean baseline (R² −0.270) and a 1-nearest-neighbour
Morgan/Tanimoto baseline (R² −0.278) on that same endpoint, and beats both on
all three. R² measured against a shifted cohort's own variance misrepresents
utility; rank correlation, mean error, calibration slope and baseline-relative
performance should be reported alongside it.

Chemical novelty explains little: Spearman association between maximum training
similarity and absolute error is −0.13 to −0.28.

## Reproducing the paper

Full detail in [`preprint/REPRODUCE.md`](preprint/REPRODUCE.md).

```bash
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements-dev.txt
venv/Scripts/python.exe -m pip install -r preprint/requirements-analysis.txt

export PYTHONUTF8=1
export PYTHONPATH=backend

python preprint/analysis/run_preprint_analysis.py   # all metrics, Tables 1-2, supplementary
python preprint/figures/make_figures.py             # Figures 1-3
python preprint/analysis/verify_manuscript_claims.py
python preprint/analysis/final_audit.py
python -m pytest preprint/tests -q
```

**Level 1** — the above — regenerates every reported number offline from
committed, redistributable artefacts. A reproduction gate independently
recomputes each previously published benchmark metric and **aborts** if any value
differs by more than 1×10⁻⁹. Running the pipeline twice reproduces artefacts
byte-for-byte.

**Level 2** documents how to obtain the upstream datasets from their official
sources and rebuild the reference tables that are not redistributed here, then
compare the rebuild against the committed results. It requires network access
and the datasets' own licence terms apply. **This repository never downloads
anything automatically.**

## Archive and preprint status

The versioned reproducibility archive is published at
[`10.5281/zenodo.22765692`](https://doi.org/10.5281/zenodo.22765692). A ChemRxiv link will be added
only after posting is independently confirmed. Pre-publication wording in frozen audit and
submission-history files is retained as provenance and is superseded by this status note.

## Licensing

Not a single blanket licence, and **no third-party material is relicensed here**.

| Material | Licence |
| --- | --- |
| Source code authored here | MIT — [`LICENSE`](LICENSE) |
| Manuscript, figures, tables, derived results | CC BY 4.0 — [`CONTENT_LICENSE.md`](CONTENT_LICENSE.md) |
| Third-party dependencies | their own — [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) |
| External datasets | their own, per dataset — [`DATA_LICENSES.md`](DATA_LICENSES.md) |

Redistributed under their upstream terms with recorded SHA-256 hashes: the ASAP
Discovery Antiviral ADMET 2025 unblinded snapshot (CC0-1.0) and the Biogen
Computational-ADME public set (MIT).

**Not redistributed:** ten reconstructed Therapeutics Data Commons reference
tables. Their upstream provenance could not be established with confidence — the
collection pages indicate CC BY 4.0, while several endpoints used here derive
from AstraZeneca depositions that ChEMBL distributes under CC BY-SA 3.0, and the
retrieved materialisations carry no embedded licence text. Rather than assume a
permissive licence, this repository publishes the dataset names, source
identifiers, versions, expected row counts, schema, reconstruction code and the
SHA-256 of each table as used, so a reader can obtain them officially and verify
an identical rebuild. **No reported result depends on their redistribution.**

This is a licensing boundary, not a gap in reproducibility.

## What this repository is not

- It is **not** a software product, and nothing here is offered as a tool for
  ADMET assessment.
- It makes **no** claim about the conflict-detection or comparability-grouping
  components of the wider application from which the prediction adapter is
  drawn. Those are unvalidated and out of scope.
- The compatibility decisions are pre-specified, explicit, auditable and
  fail-closed. **They are not externally validated**, and no inter-rater
  agreement is claimed or measured.
- Three of ADMET-AI's forty-one learned outputs proved externally evaluable
  under these criteria. **Nothing here extrapolates to the others.**
- This is computational validation on public data. Not clinical validation, not
  regulatory validation, no regulatory status.

## Provenance

This is a clean, redistribution-safe export of a frozen private development
repository. The public Git history intentionally begins at the release snapshot,
because upstream-derived reference tables used during development are not
redistributed. Frozen commit identifiers, data hashes, analysis hashes and model
versions are recorded in
[`preprint/SCIENTIFIC_FREEZE.md`](preprint/SCIENTIFIC_FREEZE.md).

## Citation

See [`preprint/CITATION.cff`](preprint/CITATION.cff). Please cite the preprint;
for the archived software and reproducibility package, cite the published version DOI
[`10.5281/zenodo.22765692`](https://doi.org/10.5281/zenodo.22765692).

## Contact

Md. Rahul Reza Roktim — roktim2311091058@diu.edu.bd
ORCID [0009-0003-6518-0495](https://orcid.org/0009-0003-6518-0495)
