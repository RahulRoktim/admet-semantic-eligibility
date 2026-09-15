# Cover note draft

Short covering statement for the ChemRxiv submission form, if one is requested.
Edit freely; this is not part of the manuscript.

---

Dear Editors,

I am submitting *What survives? Semantic eligibility, distribution shift and
metric interpretation in external validation of ADMET predictors* for posting as
a preprint.

Machine-learning ADMET models are usually reported on held-out splits of the
same curated collections used to train them. External validation is rarer, and
when it is attempted the step before the metric — establishing that the external
endpoint and the model output actually measure the same quantity — is seldom
examined. This work applies a pre-specified, fail-closed semantic eligibility
screen to twelve candidate pairings between three public experimental datasets
and the outputs of ADMET-AI 2.0.1, executed before any metric is computed. Nine
of the twelve fail, each for a recorded reason, and no classification endpoint
qualifies at all.

On the three pairings that survive, the paper does something I think is more
useful than reporting that external performance is poor. The worst-looking
result — a negative coefficient of determination for human liver microsomal
clearance — turns out to reflect severe label-distribution shift and
prediction-range compression rather than an absence of predictive signal: the
same predictions outperform both a training-mean and a nearest-neighbour
baseline. The practical recommendation follows from that: rank correlation,
mean error, calibration slope and baseline-relative performance should accompany
R², which is unstable under distribution shift.

The work is deliberately bounded. Three of ADMET-AI's forty-one learned outputs
proved externally evaluable under these criteria, and nothing here extrapolates
beyond them. The compatibility decisions are pre-specified, explicit, auditable
and fail-closed, but they are not externally validated and the manuscript says
so. Two accepted pairings are recorded as eligible under the prespecified
protocol with unresolved assay-method metadata, and that limitation is stated in
the text rather than left implicit.

Everything is reproducible. All analysis code, frozen artefacts, figures and
tables are released; a clean clone regenerates every reported number offline and
byte-for-byte, and a machine check fails if any number in the manuscript departs
from the generated results. A small set of upstream reference tables is
deliberately not redistributed because their licensing provenance could not be
established with confidence; their hashes and full reconstruction instructions
are published instead, and no reported result depends on their redistribution.

Thank you for considering this submission.

Yours sincerely,
Md. Rahul Reza Roktim
