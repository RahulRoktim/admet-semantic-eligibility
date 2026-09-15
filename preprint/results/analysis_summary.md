# External-validation preprint — analysis summary

Analysis id: `preprint-v1.0-external-validation-analysis`
Reproduction gate: **ALL_PUBLISHED_METRICS_REPRODUCED**

All numbers below are regenerated from committed artefacts by
`preprint/analysis/run_preprint_analysis.py`. No value in `validation/` or `docs/` is modified.

## Compatibility screening

- Candidate dataset-to-output pairings: 12
- Accepted for numerical evaluation: 3
- Rejected or not evaluable: 9

## Headline cohort (A)

| Endpoint | n | structures | MAE | R2 | Spearman | bias | slope | SD ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Human liver microsomal clearance | 366 | 313 | 125.655 | -0.156 | +0.446 | -111.640 | 0.037 | 0.087 |
| LogD (pH 7.4) | 474 | 413 | 0.729 | +0.368 | +0.684 | +0.386 | 0.545 | 0.781 |
| Human plasma protein binding | 178 | 178 | 10.538 | +0.642 | +0.807 | +5.118 | 0.599 | 0.725 |

## Baseline-relative performance (cohort A)

| Endpoint | ADMET-AI MAE | training-mean MAE | 1-NN MAE | ADMET-AI R2 | training-mean R2 | 1-NN R2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Human liver microsomal clearance | 125.655 | 133.337 | 137.547 | -0.156 | -0.270 | -0.278 |
| LogD (pH 7.4) | 0.729 | 0.943 | 1.287 | +0.368 | -0.002 | -0.963 |
| Human plasma protein binding | 10.538 | 19.879 | 20.456 | +0.642 | -0.121 | -0.307 |

## Label-distribution shift (cohort A)

| Endpoint | training mean +/- SD | external mean +/- SD | KS D | KS p |
| --- | --- | --- | ---: | ---: |
| Human liver microsomal clearance | 34.22 +/- 44.79 | 157.27 +/- 236.84 | 0.446 | 5.81e-50 |
| LogD (pH 7.4) | 2.19 +/- 1.20 | 2.13 +/- 1.15 | 0.095 | 8.27e-04 |
| Human plasma protein binding | 88.07 +/- 16.73 | 77.96 +/- 29.12 | 0.155 | 7.46e-04 |

## HLM range-restriction sensitivity (cohort B)

| Cohort | n | MAE | R2 | Spearman | bias | slope | SD ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_HEADLINE | 366 | 125.655 | -0.156 | +0.446 | -111.640 | 0.037 | 0.087 |
| B_HEADLINE_PLUS_LOW_CLEARANCE | 402 | 116.197 | -0.115 | +0.513 | -100.347 | 0.042 | 0.095 |
| C_STRUCTURE_AGGREGATED | 313 | 114.522 | -0.112 | +0.502 | -99.565 | 0.045 | 0.094 |
| D_STEREO_UNAMBIGUOUS | 217 | 121.300 | -0.108 | +0.548 | -105.973 | 0.047 | 0.090 |

