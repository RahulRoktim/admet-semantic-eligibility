# What survives? Semantic eligibility, distribution shift and metric interpretation in external validation of ADMET predictors

**Md. Rahul Reza Roktim**<sup>1</sup>

<sup>1</sup> Department of Pharmacy, Daffodil International University, Dhaka, Bangladesh

**Corresponding author:** Md. Rahul Reza Roktim — roktim2311091058@diu.edu.bd

**ORCID:** 0009-0003-6518-0495

**Version:** v1.0.0-preprint

**Code and data:** https://github.com/RahulRoktim/admet-semantic-eligibility —
archived at [[ZENODO_DOI]]

**Licences:** code MIT; manuscript, figures and tables CC BY 4.0; external
datasets retain their own upstream licences and are not relicensed by this work.

Every number in this manuscript is regenerated from committed artefacts by
`preprint/analysis/run_preprint_analysis.py` and checked against the generated
results by `preprint/analysis/verify_manuscript_claims.py`.

---

## Abstract

Machine-learning models for absorption, distribution, metabolism, excretion and
toxicity (ADMET) are usually reported on benchmark splits drawn from the same
curated collections used to train them. External validation is rarer, and when
it is attempted, the assumption that a public dataset carrying a matching
endpoint name is a valid comparator for a model output is seldom examined. We
applied a pre-specified, fail-closed semantic eligibility screen — ten declared
gates covering biological endpoint, matrix, species, assay family, measurement
direction, result semantics, units, transformation, classification threshold
and positive class — to twelve candidate pairings between three public
experimental datasets and the outputs of ADMET-AI 2.0.1. The screen was
executed before any metric was computed. Three pairings were accepted; nine
were rejected, each with a recorded reason, and no classification endpoint
qualified. On the three accepted pairings, after excluding exact structure
overlap with the endpoint training source and with the reconstructed regression
multitask universe, performance was poor to moderate: human liver microsomal
clearance R² = −0.156 (95% CI −0.217 to −0.108; n = 366), logD at pH 7.4
R² = 0.368 (0.261 to 0.456; n = 474), and human plasma protein binding
R² = 0.642 (0.543 to 0.732; n = 178). The model nevertheless outperformed both
a training-set-mean baseline and a 1-nearest-neighbour Morgan/Tanimoto baseline
on every accepted endpoint, including microsomal clearance, where the mean
baseline gave R² = −0.270 and the nearest-neighbour baseline R² = −0.278. Two
mechanisms accounted for the pattern. Label-distribution shift between the
reconstructed training labels and the external labels was severe for clearance
(Kolmogorov–Smirnov D = 0.446) and mild for logD (D = 0.095). Prediction-range
compression was extreme for clearance, where predictions had 9% of the observed
standard deviation and a calibration slope of 0.037, and moderate for logD
(0.781; slope 0.545) and plasma protein binding (0.725; slope 0.599). Chemical
novelty explained little (Spearman ρ between maximum training similarity and
absolute error, −0.13 to −0.28). Conclusions were unchanged by structure-level
aggregation, a structure-clustered bootstrap, restriction to stereochemically
unambiguous records, and the inclusion of low-clearance measurements that the
original benchmark had excluded before inference. We conclude that assay
semantics must be screened before external metrics are computed, and that under
strong label-distribution shift R² alone misrepresents model utility; rank
correlation, bias, calibration slope and baseline-relative performance should
be reported alongside it.

---

## 1. Introduction

Published ADMET models are typically characterised by performance on held-out
splits of curated benchmark collections such as the Therapeutics Data Commons
[2,3] and MoleculeNet [12]. Such numbers describe behaviour on data drawn from the same acquisition and
curation process as the training set. They are not, and are not intended to be,
estimates of how a model behaves on measurements generated elsewhere.

External validation would close that gap, and public experimental datasets to
attempt it with do exist. What is rarely examined is the step before the
metric: whether the external endpoint and the model output measure the same
quantity. Two records can share an endpoint name and still differ in the
species the measurement was taken in, the assay system that produced it, the
direction of the reported effect, the transformation applied to the reported
value, and the protocol that defines what the number means. An efflux ratio
from an MDR1-transfected MDCK monolayer and an apparent permeability
coefficient from a Caco-2 monolayer are both "permeability", yet the first is a
directional transporter-activity ratio and the second a passive-transport rate
constant [15,16]. A kinetic
solubility measured in a fixed buffer at a fixed timepoint and a thermodynamic
aqueous solubility aggregated across heterogeneous literature protocols are
both "solubility", and the two routinely disagree by orders of magnitude on the
same compound [20,21]. Computing an error between such pairs produces a number, and
the number is meaningless.

A second, distinct problem arises after a legitimate pairing has been
identified. The coefficient of determination compares a model's squared error
against the variance of the evaluated cohort. When the external cohort's label
distribution differs materially from the training distribution, that reference
changes, and R² can become negative for a model that still carries substantial
predictive information. Calibration — whether predicted values track observed
values in magnitude and not merely in rank order — is a distinct and frequently
neglected axis of predictive performance [14]. Reporting R² alone in that setting invites the reader
to conclude that a model is useless when the correct conclusion is that it is
miscalibrated for the population at hand.

This work addresses both points with one worked example. We contribute:

1. **A pre-specified, machine-validated, fail-closed semantic eligibility
   protocol** that decides which external dataset-to-model-output pairings may
   be scored, executed before any metric is computed, with a written reason
   recorded for every decision.
2. **A three-stage decomposition of external-validation failure** —
   ineligibility, label-distribution shift, and prediction-range compression —
   quantified on the pairings that survive the screen.
3. **A demonstration that R² is the wrong headline metric under label shift**,
   with a concrete replacement set: Spearman ρ, mean error, calibration slope,
   and performance relative to trivial baselines.

We deliberately do not attempt to characterise ADMET-AI overall. Three of its
forty-one learned outputs proved externally evaluable under our criteria, and
that restriction is itself one of our findings.

## 2. Methods

### 2.1 Model and prediction adapter

All predictions come from ADMET-AI 2.0.1 [1] (package version recorded per row),
executed locally through the same production output adapter (version `v2`) used
by the surrounding application, so that endpoint names, task types, units and
reference-percentile handling are identical to interactive use. ADMET-AI
comprises two multitask Chemprop [4,5] ensembles, one for regression and one
for classification, trained on Therapeutics Data Commons ADMET sources [2,3]. The adapter
reads task type from the installed package's own metadata; DrugBank
reference-percentile outputs are typed separately and are never treated as
predictions. Model weights were not modified, retrained or fine-tuned.

### 2.2 External datasets and provenance

Three public datasets were considered, each frozen as a byte-identical snapshot
with a recorded SHA-256, retrieval date, version or commit, and licence:

- **ASAP Discovery Antiviral ADMET 2025 (unblinded)** [7], released after the
  ASAP/Polaris/OpenADMET blind challenge; Polaris artifact created 2025-03-28,
  CC0-1.0, 560 rows (434 challenge-train, 126 challenge-test), 499 unique
  structures.
- **Biogen Computational-ADME public set** [6], commit `b00df00…af2d5`, MIT,
  3,521 rows, 3,521 unique structures.
- **A temporal ChEMBL [8] Caco-2 apparent-permeability set** (2022–2023 documents),
  hash-pinned but not redistributed because the source repository states no
  licence.

Transformations always create new files; raw source values are never
overwritten. Every processed artefact carries its own hash, asserted by test.

### 2.3 Semantic eligibility screen

Each candidate pairing of an external endpoint with an ADMET-AI output was
assessed against ten declared gates: same biological endpoint, same matrix,
same species, same assay family, same measurement direction, same result
semantics, compatible units, same transformation, same classification
threshold, and same positive class. Each gate takes one of `YES`, `NO`,
`UNKNOWN`, `NOT_APPLICABLE` or `DOCUMENTED_TRANSFORM`. A pairing is assigned
exactly one of five decisions: `EXACTLY_COMPATIBLE`,
`COMPATIBLE_WITH_DOCUMENTED_TRANSFORM`, `RELATED_NOT_COMPARABLE`,
`INCOMPATIBLE`, or `INSUFFICIENT_METADATA`.

The screen is fail-closed and enforced in code: a pairing accepted for
numerical evaluation must have no `NO` or `UNKNOWN` on the first seven gates,
must carry a written reason, and, if it relies on a transformation, must
declare that transformation explicitly and register a reverse transformation.
A decision inconsistent with its own gate values raises an error rather than
proceeding. The screen runs before predictions are compared to measurements.

These decisions are **pre-specified, explicit, auditable and fail-closed**.
They are not externally validated, and we make no claim that they are. They
rest on the declared protocol and on documented endpoint semantics from the
source datasets and the model's training-data descriptions.

### 2.4 Structure handling and stereochemistry

Structures were parsed with RDKit [9]. For each record we retain the original
string, a canonical SMILES, an isomeric SMILES, an InChIKey, the corresponding
parent (desalted, uncharged) forms, and a Bemis–Murcko scaffold [11]. Predictions
were made on the isomeric SMILES of the full submitted structure; no silent
desalting occurred before inference.

The ASAP snapshot supplies structures as CXSMILES. Of its 560 records, 235
carry an enhanced-stereo group of the OR (`o`) or AND (`&`) type — 158
AND-only and 77 OR-only — which denote a racemate or an unknown single
enantiomer rather than the single drawn stereoisomer. A further 81 carry an
absolute (`a`) marker and 244 carry no enhanced-stereo block; these 325 are
unambiguous. RDKit does not preserve enhanced-stereo groups through a canonical
isomeric round-trip, so for those 235 records the structure carried into the
model is a specific stereoisomer while the measurement derives from a mixture
or an unspecified enantiomer. We report this explicitly and quantify its effect
in a sensitivity cohort (§2.8).

### 2.5 Training-overlap reconstruction and cohorts

ADMET-AI 2.0.1's regression multitask training universe was reconstructed from
the ten public Therapeutics Data Commons source datasets it uses [2,3], several
of which — including the Caco-2 [22], aqueous solubility [21] and AstraZeneca
DMPK sets deposited in ChEMBL [8] — originate from distinct primary sources, reproducing
the package's own deduplication (exact source SMILES, last target retained,
then sorted) before adding RDKit identifiers. Per-replicate Chemprop
train/validation/test membership is not published with the wheel and cannot be
recovered; exclusion against the broader public source universe is therefore
**conservative rather than exact**, and errs towards removing rows.

Four nested cohorts were defined:

- `ALL_COMPATIBLE_DATA` — every semantically compatible row with a valid exact
  experimental value, including rows with known training exposure. Reported for
  transparency only; never presented as external generalisation.
- `NO_EXACT_TRAINING_OVERLAP` — the **headline cohort**; excludes exact
  structure overlap with the endpoint source and with any reconstructed
  regression multitask source.
- `NO_PARENT_FORM_TRAINING_OVERLAP` — additionally excludes parent and salt
  forms.
- `STRUCTURALLY_REMOTE_SUBSET` — additionally requires no stereo relation, an
  unseen Murcko scaffold, and maximum Morgan/Tanimoto similarity below 0.60.

Similarity used Morgan/ECFP-style circular fingerprints [10], radius 2, 2,048
bits, Tanimoto coefficient, computed against parent isomeric structures. This
overlap-exclusion design follows the standard concern that benchmark splits
drawn from a single curated collection overstate generalisation [12].

### 2.6 Metrics

For each cohort we report n, unique structures, mean absolute error, median
absolute error, RMSE, R², Pearson r, Spearman ρ, mean error (prediction minus
observation), and two dispersion diagnostics: the ratio of prediction standard
deviation to observation standard deviation, and the calibration slope from an
ordinary least-squares regression of prediction on observation [14]. R² uses the
evaluated cohort's own mean as reference, which is the standard definition and
the reason it responds to label-distribution shift.

Degenerate inputs are handled explicitly: constant-prediction baselines have
undefined correlation and are reported as undefined rather than as zero.

### 2.7 Baselines

Two baselines were computed on the same rows as the model:

- **Training-set mean** — the mean of the reconstructed training labels for
  that endpoint, predicted for every row. This tests whether the model carries
  information beyond the training label distribution. A training-set median
  baseline is reported in supplementary data.
- **1-nearest-neighbour Morgan/Tanimoto** — the training label of the most
  similar training structure, using the same fingerprint parameters. This tests
  whether the model improves on trivial chemical-similarity lookup. The
  neighbour was resolvable for every row in all three endpoints.

No further baselines were added.

### 2.8 Sensitivity analyses

Four cohorts test whether the conclusions depend on specific analytical
choices:

- **B — low-clearance inclusion.** The original benchmark excluded 36 ASAP
  human liver microsomal values below the source's documented reliable exact
  bound of 10 µL/min/mg, and excluded them *before inference*, so their effect
  could not be assessed from the frozen artefacts. We predicted exactly those
  36 rows with the same adapter and package version, retained all predictions
  including negative ones, and recomputed.
- **C — structure-level aggregation.** Repeated structures are collapsed to one
  record; the observation is the median of repeated measurements and the
  prediction is deterministic per structure.
- **D — stereochemically unambiguous subset.** Restricted to records without an
  OR/AND enhanced-stereo group.
- **Structure-clustered bootstrap.** InChIKey clusters, rather than rows, are
  resampled with replacement.

### 2.9 Uncertainty and determinism

Confidence intervals are 95% percentile bootstrap [13] over 2,000 replicates with
seed 20260828, resampling source rows (headline) or structure clusters
(sensitivity). These describe uncertainty in aggregate benchmark estimates;
they are **not** per-molecule prediction uncertainty. Label-distribution
comparison used a two-sample Kolmogorov–Smirnov test; the association between
maximum training similarity and absolute error used Spearman ρ. No
significance testing was performed on the primary performance metrics, which
are reported descriptively with intervals.

The analysis is deterministic and offline. A reproduction gate recomputes every
previously published metric from the frozen prediction rows and aborts without
writing if any value differs by more than 1×10⁻⁹.

## 3. Results

### 3.1 Nine of twelve candidate pairings failed the eligibility screen

Twelve candidate pairings were assessed (Table 1, Figure 1). Three were
accepted: ASAP human liver microsomal clearance to `Clearance_Microsome_AZ`
(`EXACTLY_COMPATIBLE`, identity transform, both µL/min/mg); ASAP logD to
`Lipophilicity_AstraZeneca` (`EXACTLY_COMPATIBLE`, both logD at pH 7.4); and
Biogen human plasma protein binding to `PPBR_AZ`
(`COMPATIBLE_WITH_DOCUMENTED_TRANSFORM`, source log₁₀ percent unbound converted
to percent bound as 100 − 10^raw, with the reverse transform registered).

Two of the three acceptances rest on declared endpoint identity rather than on
confirmed assay-protocol equivalence. Both are classified as **eligible under
the prespecified protocol, with unresolved assay-method metadata**, and we state
that explicitly rather than implying a stronger basis.

For logD, neither source documents whether the value was obtained by
shake-flask, chromatographic or potentiometric determination. The pairing is
accepted on the identity of the reported quantity (distribution coefficient at
pH 7.4) and of its scale, because no declared gate returned `NO` or `UNKNOWN`.
A stricter protocol that additionally required documented determination
methodology could reject this pairing, and a reader who prefers that stricter
criterion should treat the logD result as conditional.

For plasma protein binding, neither source states whether equilibrium dialysis
or ultrafiltration was used, and percent-bound values above roughly 90% carry
limited resolution because small absolute errors in the unbound fraction
translate into large relative ones [23]; the external distribution here is
concentrated in that region (median 91.8% bound; 56.2% of records above 90%).

Both caveats are recorded against the decisions in the released compatibility
matrix, and neither changes them.

Nine were rejected. Three failed on species. Mouse and rat liver microsomal
clearance cannot validate a human microsomal output, because cytochrome P450
isoform composition and catalytic activity differ appreciably between rodents
and humans for the CYP1A, 2C, 2D and 3A families [17]. Rat plasma protein
binding cannot validate a human plasma protein binding output, because unbound
fraction is not equivalent across species even for the same compound [19]. Two failed on assay system. An MDR1-MDCK efflux ratio is a directional,
transporter-driven ratio of basolateral-to-apical over apical-to-basolateral
transport, used to identify P-glycoprotein substrates [16]; a Caco-2 apparent
permeability coefficient is a rate constant for transport in a single stated
direction across a differentiated intestinal monolayer [15]. They are not the
same quantity and are not measured on the same scale. Two failed on result semantics. Kinetic solubility under a defined protocol and
fixed-pH mass solubility are not exchangeable with the heterogeneous aggregated
thermodynamic aqueous-solubility records that constitute the model's training
target [21]: kinetic assays commonly report an amorphous-phase value and yield
systematically higher solubilities than thermodynamic determinations on the
same compound [20]. Unit conversion does not resolve protocol meaning. One failed on unit scaling. A source reporting mL/min/kg cannot be reconciled
with a model target in µL/min/mg: converting between them requires microsomal
protein per gram of liver, liver weight per kilogram of body weight, and a
stated binding correction, none of which the source supplies [18]. One failed
on metadata sufficiency. The temporal Caco-2 set omits permeability direction —
apical-to-basolateral and basolateral-to-apical are distinct measurements within
the same assay [15] — and omits row-level assay context. Despite being
temporally later than the training data, chemically remote (median maximum
similarity 0.247) and free of exact overlap, it cannot be scored. Temporal
novelty and chemical non-overlap do not repair semantic ambiguity.

No classification endpoint passed the screen. No open candidate supplied
individual experimental labels together with documented threshold and
positive-class semantics and a defensible overlap status. We therefore report
no ROC-AUC, PR-AUC, confusion matrix or Brier score.

### 3.2 External performance on the accepted pairings is poor to moderate

On the headline cohort (Table 2, Figure 2a), human liver microsomal clearance
gave MAE 125.7 µL/min/mg (95% CI 104.0 to 149.2), median absolute error 34.2,
RMSE 254.6, R² −0.156 (−0.217 to −0.108), Pearson r 0.428, Spearman ρ 0.446
(0.358 to 0.524), and mean error −111.6 µL/min/mg (−135.9 to −89.5), from
n = 366 rows over 313 unique structures. LogD gave MAE 0.729 (0.681 to 0.779),
R² 0.368 (0.261 to 0.456), Spearman ρ 0.684, and mean error +0.386 log units,
from n = 474 over 413 structures. Human plasma protein binding gave MAE 10.5
percentage points (8.7 to 12.7), R² 0.642 (0.543 to 0.732), Spearman ρ 0.807,
and mean error +5.1 points, from n = 178 rows, all distinct structures.

Results were stable across the nested overlap cohorts. Requiring absence of
parent and salt forms changed nothing at any endpoint. The structurally remote
subset gave R² −0.158 (clearance, n = 364), 0.357 (logD, n = 470) and 0.661
(plasma protein binding, n = 168).

### 3.3 The model outperforms both baselines on every accepted endpoint

A negative R² invites the interpretation that the model is uninformative. It is
not (Figure 3). For microsomal clearance the training-set-mean baseline gave
MAE 133.3 and R² −0.270, and the 1-nearest-neighbour baseline MAE 137.5 and
R² −0.278, both worse than the model's MAE 125.7 and R² −0.156. For logD the
mean baseline gave R² −0.002 and the nearest-neighbour baseline R² −0.963,
against the model's +0.368. For plasma protein binding the baselines gave
R² −0.121 and −0.307 against the model's +0.642. The model also achieved
substantially higher rank correlation than the nearest-neighbour baseline at
every endpoint (0.446 vs 0.067; 0.684 vs 0.177; 0.807 vs 0.151); the
constant-prediction baselines have undefined rank correlation.

The model therefore carries real predictive information at all three endpoints,
including the one where R² is negative.

### 3.4 Label-distribution shift and prediction-range compression explain the pattern

The reconstructed training labels and the external labels differ markedly for
clearance and mildly for logD (Figure 2b). Training microsomal clearance
averaged 34.2 ± 44.8 µL/min/mg against an external mean of 157.3 ± 236.8
(Kolmogorov–Smirnov D = 0.446, p = 6 × 10⁻⁵⁰). LogD averaged 2.19 ± 1.20
against 2.13 ± 1.15 (D = 0.095, p = 8 × 10⁻⁴). Plasma protein binding averaged
88.1 ± 16.7 percent bound against 78.0 ± 29.1 (D = 0.155, p = 7 × 10⁻⁴).
Endpoint performance orders the same way as the shift.

The proximate mechanism is visible in the dispersion diagnostics. For
clearance, predictions had a standard deviation of 20.5 against an observed
standard deviation of 236.8, a ratio of 0.087, and a calibration slope of
0.037 (95% CI 0.029 to 0.046). Observed values spanned 10 to 1,620 µL/min/mg
while predictions spanned −27.9 to 102.8. The model cannot express the external
dynamic range, which produces both the large negative mean error and a squared
error exceeding the external cohort variance. LogD and plasma protein binding
showed the moderate compression typical of regression towards the training
mean: SD ratios 0.781 and 0.725, calibration slopes 0.545 (0.490 to 0.599) and
0.599 (0.499 to 0.701).

Chemical novelty contributed little. The Spearman association between maximum
training similarity and absolute error was −0.133 (p = 0.011) for clearance,
−0.282 (p < 0.001) for logD and −0.138 (p = 0.066) for plasma protein binding.
Median maximum similarity was 0.239, 0.307 and 0.291 respectively, so the
external sets are uniformly remote and similarity has little variation to
explain error with. We report these associations as descriptive; they do not
establish an applicability domain.

### 3.5 Conclusions survive every sensitivity analysis

Including the 36 previously excluded low-clearance measurements (cohort B, all
36 predicted, no failures, 6 negative predictions retained, all free of exact
training overlap) moved clearance from R² −0.156 to −0.115, mean error from
−111.6 to −100.3, Spearman ρ from 0.446 to 0.513, and the calibration slope
from 0.037 to 0.042 at n = 402. Range restriction therefore **exaggerated but
did not create** the negative coefficient of determination, the negative bias,
or the range compression. Notably, the model over-predicted these low-clearance
compounds — observed values 0 to 9.7 µL/min/mg, predictions −12.0 to 66.5 —
which is the expected signature of compression towards the training mean at the
opposite end of the range.

Structure-level aggregation (cohort C) gave R² −0.112, 0.353 and 0.642.
Restriction to stereochemically unambiguous records (cohort D) gave R² −0.108
at n = 217 for clearance and 0.335 at n = 274 for logD; plasma protein binding
is unaffected, its source supplying plain SMILES. The structure-clustered
bootstrap gave intervals nearly identical to the row-level bootstrap: R²
−0.217 to −0.104, 0.251 to 0.463, and 0.543 to 0.732.

No sensitivity analysis altered any qualitative conclusion.

## 4. Discussion

The practical message is ordered. Before computing an external metric,
establish that the external endpoint and the model output are the same
measurement. Here three of twelve apparently reasonable pairings survived that
test. A reader who skipped the screen would have obtained nine further error
statistics, all uninterpretable, and several would probably have looked
acceptable — rat and human plasma protein binding are correlated enough across
compounds [19] that such a comparison would not announce itself as invalid. We
did not compute them, since that would mean scoring pairings our own protocol
rejected; the point is that nothing in the numbers would have flagged the
problem.

Where a pairing is legitimate, the metric still requires care. Our clearance
result is the clean case: R² is negative, which in isolation reads as a failed
model, while the same predictions beat both trivial baselines and retain
moderate rank ordering. The correct description is that the model is
informative but severely miscalibrated for this population — a calibration
slope of 0.037 means that a tenfold increase in true clearance moves the
prediction by less than 4% of that amount. For a project team, that
distinction matters: a model that ranks compounds usefully but cannot express
their absolute range can support triage and should not be used to predict a
value.

This is not a property of one model. Any regression trained on a label
distribution unlike the deployment population will compress towards its
training mean, and any R² computed against a shifted cohort's own variance will
punish it for that. The reporting fix is cheap: alongside R², publish Spearman
ρ, mean error, calibration slope and the performance of a training-mean
baseline on the same rows. Those four numbers would have made our clearance
result unambiguous without any additional experiment.

The eligibility principle generalises beyond model evaluation. The same
distinctions — species, matrix, assay family, result semantics, transformation
— determine whether two experimental measurements of the "same" endpoint may be
compared to each other. We note that generality without claiming to have
demonstrated it here; testing it on experimental evidence integration is
separate work and is not evaluated in this manuscript.

A final observation concerns our own pipeline. The ASAP enhanced-stereochemistry
issue described in §2.4 is an instance of exactly the failure this paper is
about: a structure representation that looks equivalent, is silently normalised
by a standard toolkit, and thereby asserts a measurement identity the source
never claimed. We found it by auditing our own inputs against the source file
rather than the processed one. That audit is not optional.

## 5. Limitations

- Three of ADMET-AI's forty-one learned outputs were externally evaluable under
  our criteria. **No result here should be extrapolated to the other learned
  outputs, to the eleven deterministic physicochemical outputs, or to any
  DrugBank reference-percentile record.**
- No classification endpoint was evaluated, so nothing is claimed about
  classification performance.
- The ASAP dataset is a project-like antiviral medicinal-chemistry series (300
  Bemis–Murcko scaffolds across 560 records, largest scaffold 27 records), not a
  chemically uniform random benchmark. It reflects a realistic deployment
  setting but is not chemically representative, and two of our three endpoints
  derive from it.
- The plasma protein binding headline cohort contains 178 rows from 3,521
  source rows, because 3,327 source rows carry no human plasma protein binding
  label. This is source sparsity, not selection, but the resulting sample is
  small.
- Exact per-replicate Chemprop train/validation/test membership is unavailable,
  so exclusion against the reconstructed public source universe is conservative
  rather than exact and cannot prove absence from unpublished build inputs.
- 235 of 560 ASAP records carry OR/AND enhanced-stereo groups not preserved as
  a single stereochemical assignment through the modelling path. The
  sensitivity cohort shows conclusions are unchanged, but the affected rows
  assert more stereochemical precision than the source supports.
- ASAP repeats some structures, so the row-level bootstrap slightly overstates
  precision; the structure-clustered bootstrap is reported alongside it.
- 36 clearance measurements fall below the source's documented reliable exact
  bound and are excluded from the headline cohort; their effect is quantified
  in cohort B.
- The compatibility decisions are pre-specified, explicit, auditable and
  fail-closed. **They are not externally validated**, and no inter-rater
  agreement is claimed or measured.
- This is computational validation on public data. It is not clinical
  validation, not regulatory validation, and carries no regulatory status.
- A single model version (ADMET-AI 2.0.1) at a single point in time was
  assessed. The protocol is model-agnostic; the results are not.

## 6. Conclusion

Most apparent opportunities to externally validate an ADMET predictor are not
valid: nine of twelve candidate pairings in this study failed a pre-specified
semantic eligibility screen, and no classification endpoint survived at all. On
the three pairings that did survive, a widely used open model showed poor to
moderate external performance, and the single worst-looking result — a negative
coefficient of determination for microsomal clearance — turned out to reflect
severe label-distribution shift and prediction-range compression rather than an
absence of predictive signal, since the same predictions outperformed both a
training-mean and a nearest-neighbour baseline. Semantic eligibility should be
screened, and its outcome reported, before any external ADMET metric is
computed; and under distribution shift, R² should never be reported alone.

## 7. Data and code availability

All analysis code, frozen result artefacts, figure-generation scripts and the
machine-readable result set accompany this manuscript. Reproduction is offered
at two levels, documented in `preprint/REPRODUCE.md`. **Level 1** regenerates
every number, table and figure from committed, redistributable artefacts,
deterministically and offline; a reproduction gate independently recomputes each
previously published benchmark metric from the frozen prediction rows and aborts
if any value differs by more than 1×10⁻⁹, and running the pipeline twice
reproduces all artefacts byte-for-byte. **Level 2** documents how to obtain the
upstream datasets officially, rebuild the reference tables that are not
redistributed, and compare the rebuild against the committed results.

Licensing is deliberately not uniform, and no third-party material is
relicensed. Project code is MIT; the manuscript, figures, tables and derived
results are CC BY 4.0. The ASAP snapshot (CC0-1.0) and the Biogen public set
(MIT) are redistributed unchanged under their own licences with recorded
SHA-256 hashes. The temporal ChEMBL Caco-2 set is hash-pinned but not
redistributed, its source repository stating no licence; it contributes no
reported metric.

The ten reconstructed Therapeutics Data Commons reference tables are **not
redistributed**, because their upstream provenance could not be established with
confidence: the collection pages indicate CC BY 4.0, while several endpoints
used here derive from AstraZeneca depositions that ChEMBL distributes under
CC BY-SA 3.0, and the retrieved materialisations carry no embedded licence text.
Rather than assume a permissive licence, we publish the dataset names, source
identifiers, versions, expected row counts, schema, reconstruction code and
procedure, and the SHA-256 of each table as used here, so a reader can obtain
the data officially and verify an identical rebuild. This is a licensing
boundary, not a gap in reproducibility: no reported number depends on those
files being redistributed, because everything downstream reads a derived summary
containing no upstream structure, target value or structure–target pair.
Per-dataset records are in `DATA_LICENSES.md`; `preprint/release_manifest.json`
classifies every released file.

## Acknowledgements

The author thanks the ASAP Discovery Consortium, OpenADMET and Polaris for
releasing the antiviral ADMET dataset under a CC0 public-domain dedication, and
the authors of the Biogen Computational-ADME public set for releasing it under
an open licence. This work relies on ADMET-AI, Chemprop, the Therapeutics Data
Commons, ChEMBL and RDKit, and would not have been possible without them.

## Funding

This research received no specific grant from any funding agency in the public,
commercial, or not-for-profit sectors.

## Competing interests

The author declares no competing interests.

## Author contributions

R.R.R. designed the study, implemented the analysis, performed the evaluation,
and wrote the manuscript.

## References

All bibliographic fields below were verified against an authoritative record —
the publisher page, the PubMed entry, or the DOI metadata — at the time of
writing. No field is reconstructed from memory.

1. Swanson K, Walther P, Leitz J, Mukherjee S, Wu JC, Shivnaraine RV, Zou J.
   ADMET-AI: a machine learning ADMET platform for evaluation of large-scale
   chemical libraries. *Bioinformatics*. 2024;40(7):btae416.
   doi:10.1093/bioinformatics/btae416
2. Huang K, Fu T, Gao W, Zhao Y, Roohani Y, Leskovec J, Coley CW, Xiao C, Sun J,
   Zitnik M. Therapeutics Data Commons: Machine Learning Datasets and Tasks for
   Drug Discovery and Development. *Proceedings of the Neural Information
   Processing Systems Track on Datasets and Benchmarks*. 2021.
   arXiv:2102.09548. doi:10.48550/arXiv.2102.09548
3. Huang K, Fu T, Gao W, Zhao Y, Roohani Y, Leskovec J, Coley CW, Xiao C, Sun J,
   Zitnik M. Artificial intelligence foundation for therapeutic science.
   *Nature Chemical Biology*. 2022;18(10):1033–1036.
   doi:10.1038/s41589-022-01131-2
4. Yang K, Swanson K, Jin W, Coley C, Eiden P, Gao H, Guzman-Perez A, Hopper T,
   Kelley B, Mathea M, Palmer A, Settels V, Jaakkola T, Jensen K, Barzilay R.
   Analyzing Learned Molecular Representations for Property Prediction.
   *Journal of Chemical Information and Modeling*. 2019;59(8):3370–3388.
   doi:10.1021/acs.jcim.9b00237
5. Heid E, Greenman KP, Chung Y, Li S-C, Graff DE, Vermeire FH, Wu H, Green WH,
   McGill CJ. Chemprop: A Machine Learning Package for Chemical Property
   Prediction. *Journal of Chemical Information and Modeling*. 2024;64(1):9–17.
   doi:10.1021/acs.jcim.3c01250
6. Fang C, Wang Y, Grater R, Kapadnis S, Black C, Trapa P, Sciabola S.
   Prospective Validation of Machine Learning Algorithms for Absorption,
   Distribution, Metabolism, and Excretion Prediction: An Industrial
   Perspective. *Journal of Chemical Information and Modeling*.
   2023;63(11):3263–3274. doi:10.1021/acs.jcim.3c00160
7. ASAP Discovery Consortium, OpenADMET, Polaris. *antiviral-admet-2025-unblinded*
   [dataset]. Polaris Hub; artifact created 2025-03-28. CC0-1.0. Released after
   the ASAP/Polaris/OpenADMET antiviral blind challenge (434 challenge-train and
   126 challenge-test records).
   https://polarishub.io/datasets/asap-discovery/antiviral-admet-2025-unblinded
8. Zdrazil B, Felix E, Hunter F, Manners EJ, Blackshaw J, Corbett S, de Veij M,
   Ioannidis H, Mendez Lopez D, Mosquera JF, Magarinos MP, Bosc N, Arcila R,
   Kizilören T, Gaulton A, Bento AP, Adasme MF, Monecke P, Landrum GA, Leach AR.
   The ChEMBL Database in 2023: a drug discovery platform spanning multiple
   bioactivity data types and time periods. *Nucleic Acids Research*.
   2024;52(D1):D1180–D1192. doi:10.1093/nar/gkad1004
9. RDKit: Open-source cheminformatics. Version 2026.03.5. https://www.rdkit.org
10. Rogers D, Hahn M. Extended-Connectivity Fingerprints. *Journal of Chemical
    Information and Modeling*. 2010;50(5):742–754. doi:10.1021/ci100050t
11. Bemis GW, Murcko MA. The Properties of Known Drugs. 1. Molecular Frameworks.
    *Journal of Medicinal Chemistry*. 1996;39(15):2887–2893.
    doi:10.1021/jm9602928
12. Wu Z, Ramsundar B, Feinberg EN, Gomes J, Geniesse C, Pappu AS, Leswing K,
    Pande V. MoleculeNet: a benchmark for molecular machine learning.
    *Chemical Science*. 2018;9(2):513–530. doi:10.1039/C7SC02664A
13. Efron B. Bootstrap Methods: Another Look at the Jackknife. *The Annals of
    Statistics*. 1979;7(1):1–26. doi:10.1214/aos/1176344552
14. Van Calster B, McLernon DJ, van Smeden M, Wynants L, Steyerberg EW.
    Calibration: the Achilles heel of predictive analytics. *BMC Medicine*.
    2019;17:230. doi:10.1186/s12916-019-1466-7
15. Hubatsch I, Ragnarsson EGE, Artursson P. Determination of drug permeability
    and prediction of drug absorption in Caco-2 monolayers. *Nature Protocols*.
    2007;2(9):2111–2119. doi:10.1038/nprot.2007.303
16. Polli JW, Wring SA, Humphreys JE, Huang L, Morgan JB, Webster LO,
    Serabjit-Singh CS. Rational use of in vitro P-glycoprotein assays in drug
    discovery. *Journal of Pharmacology and Experimental Therapeutics*.
    2001;299(2):620–628. PMID:11602674
17. Martignoni M, Groothuis GMM, de Kanter R. Species differences between mouse,
    rat, dog, monkey and human CYP-mediated drug metabolism, inhibition and
    induction. *Expert Opinion on Drug Metabolism & Toxicology*.
    2006;2(6):875–894. doi:10.1517/17425255.2.6.875
18. Obach RS. Prediction of human clearance of twenty-nine drugs from hepatic
    microsomal intrinsic clearance data: An examination of in vitro half-life
    approach and nonspecific binding to microsomes. *Drug Metabolism and
    Disposition*. 1999;27(11):1350–1359. PMID:10534321
19. Berry LM, Li C, Zhao Z. Species differences in distribution and prediction of
    human V(ss) from preclinical data. *Drug Metabolism and Disposition*.
    2011;39(11):2103–2116. doi:10.1124/dmd.111.040766
20. Saal C, Petereit AC. Optimizing solubility: Kinetic versus thermodynamic
    solubility temptations and risks. *European Journal of Pharmaceutical
    Sciences*. 2012;47(3):589–595. doi:10.1016/j.ejps.2012.07.019
21. Sorkun MC, Khetan A, Er S. AqSolDB, a curated reference set of aqueous
    solubility and 2D descriptors for a diverse set of compounds. *Scientific
    Data*. 2019;6:143. doi:10.1038/s41597-019-0151-1
22. Wang N-N, Dong J, Deng Y-H, Zhu M-F, Wen M, Yao Z-J, Lu A-P, Wang J-B,
    Cao D-S. ADME Properties Evaluation in Drug Discovery: Prediction of Caco-2
    Cell Permeability Using a Combination of NSGA-II and Boosting. *Journal of
    Chemical Information and Modeling*. 2016;56(4):763–773.
    doi:10.1021/acs.jcim.5b00642
23. Kratochwil NA, Huber W, Müller F, Kansy M, Gerber PR. Predicting plasma
    protein binding of drugs: a new approach. *Biochemical Pharmacology*.
    2002;64(9):1355–1374. doi:10.1016/S0006-2952(02)01074-2
