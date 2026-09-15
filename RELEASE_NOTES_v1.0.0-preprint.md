# v1.0.0-preprint — external-validation and semantic-eligibility study

This release accompanies a preprint. It contains the analysis code, the frozen
result artefacts, the figures and tables, and the manuscript for a study of what
survives assay-semantic eligibility screening when a public ADMET predictor is
evaluated against public experimental data.

It is **not** a release of the surrounding ADMET Evidence Graph application. The
application's own scientific claims remain unvalidated and are out of scope
here.

## Research question

When a published ADMET predictor is evaluated against apparently suitable public
experimental datasets, how many candidate dataset-to-output pairings are
semantically eligible for comparison at all, and among eligible pairings, what
accounts for the difference between benchmark-reported and externally observed
performance?

## Eligibility screening: 12 candidates → 3 eligible

A pre-specified, fail-closed screen of ten declared gates (biological endpoint,
matrix, species, assay family, measurement direction, result semantics, units,
transformation, classification threshold, positive class) was applied to twelve
candidate pairings between three public datasets and the outputs of ADMET-AI
2.0.1. The screen ran **before** any metric was computed.

- **3 accepted.** Human liver microsomal clearance and logD (both
  `EXACTLY_COMPATIBLE`); human plasma protein binding
  (`COMPATIBLE_WITH_DOCUMENTED_TRANSFORM`).
- **9 rejected**, each with a written reason: 3 on species, 2 on assay system,
  2 on result semantics, 1 on unresolvable unit scaling, 1 on insufficient assay
  metadata.
- **No classification endpoint qualified.** No ROC-AUC, PR-AUC, confusion matrix
  or Brier score is reported anywhere in this work.

Two of the three acceptances are recorded as *eligible under the prespecified
protocol, with unresolved assay-method metadata* — logD and plasma protein
binding — because neither source documents the experimental determination
method. Both are disclosed in the manuscript; neither decision was changed.

## Endpoints evaluated

| Endpoint | Source | Transform |
| --- | --- | --- |
| Human liver microsomal clearance (µL/min/mg) | ASAP Discovery antiviral ADMET 2025 | identity |
| logD at pH 7.4 | ASAP Discovery antiviral ADMET 2025 | identity |
| Human plasma protein binding (% bound) | Biogen Computational-ADME public set | `100 − 10^raw` from log₁₀ % unbound |

## Headline results

Headline cohort excludes exact structure overlap with the endpoint training
source and with the reconstructed regression multitask universe. Intervals are
95% percentile bootstrap, 2,000 replicates, seed 20260828.

| Endpoint | n | MAE | R² (95% CI) | Spearman ρ | Mean error | Calibration slope | SD ratio |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Microsomal clearance | 366 | 125.7 | −0.156 (−0.217 to −0.108) | 0.446 | −111.6 | 0.037 | 0.087 |
| logD | 474 | 0.729 | 0.368 (0.261 to 0.456) | 0.684 | +0.386 | 0.545 | 0.781 |
| Plasma protein binding | 178 | 10.5 | 0.642 (0.543 to 0.732) | 0.807 | +5.1 | 0.599 | 0.725 |

## The microsomal-clearance finding

The negative R² for clearance is not evidence that the model is uninformative.
Two measured mechanisms explain it:

- **Label-distribution shift.** Reconstructed training labels average
  34.2 ± 44.8 µL/min/mg; the external labels average 157.3 ± 236.8
  (Kolmogorov–Smirnov D = 0.446). The corresponding shift is mild for logD
  (D = 0.095) and intermediate for plasma protein binding (D = 0.155).
- **Prediction-range compression.** Predictions have a standard deviation of
  20.5 against an observed 236.8 (ratio 0.087) and a calibration slope of 0.037.
  Observations span 10–1,620 µL/min/mg; predictions span −27.9 to 102.8. The
  model cannot express the external dynamic range.

Chemical novelty explains little: the Spearman association between maximum
training similarity and absolute error is −0.13 to −0.28, and median maximum
similarity is 0.24–0.31 across all three endpoints.

## Baseline comparison

ADMET-AI outperforms both trivial baselines on **all three** endpoints,
including the one with negative R².

| Endpoint | ADMET-AI R² | Training-mean R² | 1-NN Morgan R² |
| --- | ---: | ---: | ---: |
| Microsomal clearance | −0.156 | −0.270 | −0.278 |
| logD | +0.368 | −0.002 | −0.963 |
| Plasma protein binding | +0.642 | −0.121 | −0.307 |

## Robustness

No sensitivity analysis changed a qualitative conclusion.

- **Low-clearance inclusion.** The 36 ASAP clearance rows below the source's
  documented reliable bound were excluded before inference in the original
  benchmark. All 36 were predicted here with the same adapter and package
  version (0 failures, 6 negative predictions retained). Adding them moves
  clearance R² from −0.156 to −0.115 and bias from −111.6 to −100.3 at n = 402.
  Range restriction **exaggerated but did not create** the negative R² or the
  negative bias.
- **Structure-level aggregation.** R² −0.112 / +0.353 / +0.642.
- **Stereochemically unambiguous subset.** 235 of 560 ASAP records carry OR/AND
  enhanced-stereo groups that RDKit does not preserve through a canonical
  round-trip. Restricting to the unambiguous records gives R² −0.108 (n = 217)
  and +0.335 (n = 274); plasma protein binding is unaffected.
- **Structure-clustered bootstrap.** Intervals essentially identical to the
  row-level bootstrap.

## Licensing-aware reproducibility

Reproduction is offered at two levels, both documented in
`preprint/REPRODUCE.md`.

- **Level 1** regenerates every manuscript number, table, figure and robustness
  output from committed, redistributable artefacts — offline, deterministic, and
  byte-for-byte reproducible across runs. A hard reproduction gate recomputes
  each previously published benchmark metric and aborts if any value differs by
  more than 1×10⁻⁹.
- **Level 2** documents how to obtain the upstream datasets officially,
  reconstruct the reference tables that are **not** redistributed, and compare
  the rebuild against the committed results.

Ten reconstructed Therapeutics Data Commons reference tables are deliberately
excluded from this release because their upstream licensing provenance could not
be established with confidence. Dataset names, source identifiers, versions, row
counts, schema, reconstruction code and the exact SHA-256 of each table as used
are published instead. No reported number depends on those files being
redistributed. `preprint/release_manifest.json` classifies every released file,
and `release_package.py --check` fails if an excluded file is ever packaged.

Licences are split by material type and no third-party data is relicensed: code
MIT, original content CC BY 4.0, external datasets under their own upstream
terms (`LICENSE`, `CONTENT_LICENSE.md`, `THIRD_PARTY_LICENSES.md`,
`DATA_LICENSES.md`).

## Important limitations

- **Three of ADMET-AI's forty-one learned outputs** were externally evaluable
  under these criteria. Nothing here extrapolates to the other learned outputs,
  the deterministic physicochemical outputs, or the DrugBank percentile records.
- **No classification endpoint was evaluated.**
- **The ASAP dataset is a project-like antiviral series**, not a chemically
  representative benchmark (300 Bemis–Murcko scaffolds over 560 records, largest
  scaffold 27). Two of the three endpoints derive from it.
- **Plasma protein binding rests on 178 rows** from 3,521 source rows, because
  3,327 carry no human PPB label.
- **Exact per-replicate Chemprop split membership is unavailable**, so overlap
  exclusion is conservative rather than exact.
- **Compatibility decisions are pre-specified, explicit, auditable and
  fail-closed — but not externally validated.** No inter-rater agreement is
  claimed or measured.
- **This is computational validation on public data.** Not clinical validation,
  not regulatory validation, no regulatory status.
- A **single model version** at a single point in time was assessed. The
  protocol is model-agnostic; the results are not.

## Verification shipped with this release

| Check | Result |
| --- | --- |
| Test suite | 103 passed |
| Manuscript numeric claims verified against generated results | 115 |
| Forbidden out-of-scope claims absent | 16 checked |
| Required disclosures present | 10 checked |
| References, all verified against an authoritative record | 23 |
| Release licence check | passes; fails correctly on a leaked archive |
| Full-pipeline determinism | byte-identical across independent runs |
