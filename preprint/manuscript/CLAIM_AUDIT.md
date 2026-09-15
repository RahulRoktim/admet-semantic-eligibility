# Manuscript claim audit

Every substantive scientific statement in `manuscript.md` is classified below.

| Class | Meaning |
| --- | --- |
| **S** | supported by this study (regenerated from committed artefacts; machine-verified) |
| **E** | supported by an external citation |
| **D** | common methodological definition; no citation required |
| **I** | interpretation or opinion by the authors, and labelled as such in the text |
| **⚠** | flagged: weaker support than the surrounding text might suggest |

The 115 numeric claims marked **S** are additionally checked automatically by
`preprint/analysis/verify_manuscript_claims.py`, which fails if any manuscript
number departs from `preprint/results/preprint_analysis.json`.

---

## 1. Introduction

| Claim | Class | Basis |
| --- | --- | --- |
| ADMET models are typically characterised on held-out splits of curated benchmark collections | E | [2,3,12] |
| Such numbers describe data from the same acquisition/curation process, not external measurements | D | definitional consequence of how the splits are constructed |
| MDR1-MDCK efflux ratio and Caco-2 Papp are different quantities despite both being "permeability" | E | [15,16] |
| Kinetic and thermodynamic solubility routinely disagree by orders of magnitude on the same compound | E | [20,21] |
| R² compares squared error against the evaluated cohort's variance, so it responds to label shift | D | definition of the coefficient of determination |
| Calibration is a distinct, frequently neglected axis of predictive performance | E | [14] |
| "Computing an error between such pairs produces a number, and the number is meaningless" | I | authors' interpretation; stated as argument, not result |

## 2. Methods

| Claim | Class | Basis |
| --- | --- | --- |
| ADMET-AI 2.0.1 comprises two multitask Chemprop ensembles (regression, classification) | E | [1,4,5] and the package's own training manifest |
| Predictions used the production adapter v2; weights unmodified | S | recorded per row in the frozen artefacts; asserted by test |
| Dataset versions, licences, row counts, retrieval date, hashes | S | `external_dataset_manifest.json`; hash equality asserted by test |
| ASAP comprises 434 challenge-train and 126 challenge-test records | S/E | recomputed from the snapshot; consistent with the challenge description [7] |
| Ten declared eligibility gates; five decision classes; fail-closed enforcement | S | `compatibility.py`; invalid decisions raise |
| 235 of 560 ASAP records carry OR/AND enhanced-stereo groups (158 AND-only, 77 OR-only, 0 both; 325 unambiguous) | S | recomputed from the source CXSMILES; asserted by test |
| RDKit does not preserve enhanced-stereo groups through a canonical isomeric round-trip | S | verified directly on the source records |
| Training universe reconstructed from ten TDC regression sources; several from distinct primary sources | E | [2,3,8,21,22] and the training manifest |
| Per-replicate Chemprop split membership is unavailable; exclusion is conservative not exact | E/S | stated by the package's own documentation; recorded in the training manifest |
| Fingerprint parameters (Morgan/ECFP-style, r=2, 2048 bits, Tanimoto) | D/E | [10] |
| Bemis–Murcko scaffold definition | E | [11] |
| Calibration slope defined as OLS slope of prediction on observation | D/E | [14] |
| Percentile bootstrap, 2,000 replicates, seed 20260828 | D/E | [13] |
| Constant-prediction baselines have undefined correlation and are reported as undefined | D | mathematical fact; asserted by test |

## 3. Results

| Claim | Class | Basis |
| --- | --- | --- |
| 12 candidates; 3 accepted; 9 rejected; no classification endpoint eligible | S | `preprint_analysis.json`; asserted by test |
| The three accepted pairings and their transforms | S | `endpoint_compatibility.csv` (Table 1) |
| logD acceptance is eligible under the prespecified protocol, with unresolved assay-method metadata | ⚠ | see "Flagged items" below; decision retained |
| PPB acceptance rests on declared endpoint identity; >90% bound has limited resolution; external median 91.8% bound, 56.2% above 90% | ⚠/E/S | resolution caveat from [23]; distribution recomputed from the frozen rows |
| Rodent vs human microsomal clearance: CYP isoform composition and activity differ | E | [17] |
| Rat vs human plasma protein binding: unbound fraction not equivalent across species | E | [19] |
| MDR1-MDCK efflux ratio is a directional transporter ratio; Caco-2 Papp is a single-direction rate constant | E | [15,16] |
| Kinetic assays commonly report amorphous-phase values, systematically higher than thermodynamic | E | [20] |
| AqSolDB target is a heterogeneous aggregated record set | E | [21] |
| mL/min/kg ↔ µL/min/mg requires microsomal protein per gram liver, liver weight per kg, binding correction | E | [18] |
| A→B and B→A are distinct measurements within the Caco-2 assay | E | [15] |
| Caco-2 set: median maximum similarity 0.247; no exact overlap; not scored | S | frozen overlap report; verified by the claim checker |
| All headline metrics, intervals, baselines, shift statistics, dispersion diagnostics | S | `preprint_analysis.json`; 115 values machine-verified |
| Model outperforms both baselines on all three endpoints | S | asserted by test |
| Endpoint performance orders the same way as label shift | S/I | the three KS values and the three R² values are measured (**S**); that they "order the same way" is a descriptive observation on n=3 endpoints (**I**) |
| Chemical novelty contributes little (ρ −0.13 to −0.28) | S | recomputed; reported as descriptive, not as an applicability domain |
| All sensitivity cohorts (B, C, D, clustered bootstrap) | S | `supplementary_sensitivity.csv`; asserted by test |
| Over-prediction of the low-clearance rows is "the expected signature of compression towards the training mean" | I | interpretation of a measured result; the measurement itself is **S** |

## 4. Discussion

| Claim | Class | Basis |
| --- | --- | --- |
| A reader skipping the screen could have produced nine additional uninterpretable statistics | I | argument; the 9 rejections are **S** |
| Rat and human plasma protein binding "are correlated enough across compounds that such a comparison would not announce itself as invalid" | ⚠ I | consistent with [19]; explicitly labelled in the text as not computed here; see below |
| The clearance result is "informative but severely miscalibrated for this population" | I | interpretation of **S** results |
| "A calibration slope of 0.037 means a tenfold increase in true clearance moves the prediction by less than 4% of that amount" | D | arithmetic restatement of the measured slope |
| A model that ranks usefully but cannot express absolute range can support triage, not value prediction | I | authors' recommendation |
| Any regression trained on a label distribution unlike deployment will compress towards its training mean | E/I | standard regression-to-the-mean reasoning, consistent with [14]; stated generally, not measured here |
| Reporting recommendation (ρ, mean error, calibration slope, baseline-relative performance) | I | authors' recommendation |
| The eligibility principle generalises to experimental evidence integration | I | explicitly labelled as not demonstrated here |
| Our own stereochemistry issue is an instance of the failure the paper describes | I | interpretation of an **S** finding |

## 5. Limitations, 6. Conclusion, 7. Data availability

| Claim | Class | Basis |
| --- | --- | --- |
| 3 of 41 learned outputs evaluable; no extrapolation to the rest | S | automatically enforced: "all 41" is a forbidden phrase in the claim checker |
| ASAP is a project-like series: 300 Murcko scaffolds over 560 records, largest 27 | S | recomputed; verified by the claim checker |
| PPB: 178 of 3,521 rows, because 3,327 lack the label | S | recomputed |
| Compatibility decisions are pre-specified, explicit, auditable, fail-closed, and **not** externally validated | S | required disclosure enforced by the claim checker |
| Computational validation only; not clinical, not regulatory | D | required disclosure enforced by the claim checker |
| Licence structure and non-redistribution rationale | S | `DATA_LICENSES.md`, `release_manifest.json`; release check enforced |

---

## Flagged items

Three statements have weaker support than their surroundings. All three are now
marked in the manuscript itself; none changes a decision or a number.

**F1 — logD acceptance (`ASAP_LOGD_LIPOPHILICITY`).** Status:
**eligible under the prespecified protocol, with unresolved assay-method
metadata.** Accepted as `EXACTLY_COMPATIBLE` because both sides report a
distribution coefficient at pH 7.4 on the same scale and no declared gate
returned `NO` or `UNKNOWN`. Neither source documents the determination method
(shake-flask, chromatographic, potentiometric), which can shift absolute values.
**This is the weakest of the three acceptances.** The decision is retained; the
manuscript states the limitation explicitly and notes that a stricter protocol
additionally requiring documented determination methodology could reject the
pairing, so a reader preferring that criterion should treat the logD result as
conditional. This is a disclosed boundary of the prespecified protocol, not an
undisclosed weakness.

**F2 — plasma protein binding acceptance (`BIOGEN_HPPB_PPBR`).** Status:
**eligible under the prespecified protocol, with unresolved assay-method
metadata.** The transform is arithmetically exact, but neither source states whether equilibrium dialysis
or ultrafiltration was used, and percent-bound values above ~90% carry limited
resolution [23]. The headline cohort's median is 91.8% bound with 56.2% of
records above 90%, so most of the cohort sits in that region. Disclosed in the
text; decision unchanged.

**F3 — the rat/human PPB scatter remark in the Discussion.** The manuscript
states that rat plasma protein binding "correlates well enough with human
plasma protein binding to yield a plausible-looking scatter". This is a
rhetorical illustration of why a rejected pairing can look acceptable. **We did
not compute it** — computing it would mean scoring a pairing our own protocol
rejected. The sentence is phrased as a hypothetical and is consistent with the
species-difference literature [19], but it is not a result of this study. If a
reviewer objects, it should be deleted rather than defended; nothing depends
on it.

## Unsupported claims remaining

**None.** Every substantive statement is classified above as supported by this
study, supported by a verified citation, a common methodological definition, or
an explicitly labelled interpretation. The three flagged items are disclosed in
the manuscript rather than left implicit.

## Separation of result, literature and interpretation

The manuscript keeps the three apart structurally:

- **Our results** appear in Section 3 with n, interval and cohort attached, and
  are machine-verified against the generated artefacts.
- **Previous literature** is confined to Section 1, Section 2 and the
  eligibility rationales in Section 3.1, always with a bracketed citation.
- **Our interpretation** is confined to Section 4 and the closing sentence of
  Section 6, and is written in the first person plural ("we conclude", "we
  argue", "the correct description is") so the reader can separate it from the
  measurements.
