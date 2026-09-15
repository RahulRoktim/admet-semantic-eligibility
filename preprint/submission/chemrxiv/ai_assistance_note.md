# Note on AI assistance

Prepared so it can be supplied if the venue asks. ChemRxiv does not currently
mandate such a statement; several journals require one at peer review.

## Statement

> An AI coding assistant (Anthropic Claude, accessed through Claude Code) was
> used during this work to help write and refactor analysis and figure-generation
> code, to help draft and edit manuscript prose, and to help locate and verify
> bibliographic metadata. All scientific decisions were made by the author: the
> choice of research question, the datasets considered, the ten semantic
> eligibility gates and every accept/reject decision recorded in the
> compatibility matrix, the cohort definitions, the choice of metrics and
> baselines, the sensitivity analyses, and the interpretation of the results.
> Every reported number is regenerated from committed artefacts by released code
> and is checked automatically against those artefacts; every bibliographic entry
> was verified against an authoritative record. The assistant is not an author
> and made no scientific claim on its own authority.

## What this does and does not say

**Used for:**

- writing and refactoring Python for the analysis, figures, tables and tests;
- drafting and editing manuscript prose;
- searching for and cross-checking bibliographic metadata, which was then
  verified against publisher pages, PubMed records or DOI metadata;
- building the verification tooling — the reproduction gate, the claim checker,
  the release licence check.

**Not used for:**

- deciding which pairings are semantically eligible;
- selecting or excluding data;
- choosing statistical methods or thresholds;
- interpreting the results or forming the conclusions;
- generating, imputing or adjusting any experimental or predicted value.

## Why the safeguards matter more than the disclosure

The substantive protection is not the statement above; it is that the work is
checkable without trusting anyone's account of how it was produced:

- 115 manuscript numbers are machine-verified against the generated results, and
  the checker fails if a number in the text departs from the artefacts;
- a reproduction gate recomputes every previously published benchmark metric and
  aborts if any differs by more than 1e-9;
- the full pipeline reproduces byte-for-byte across independent runs;
- 294 tests, including negative controls that confirm the verifier and the
  release check actually fail when they should;
- 23 references, each verified against an authoritative record.

Errors introduced during the work were caught by these checks rather than by
inspection, and two are documented: a miscounted stereochemistry figure (marker
tokens rather than records; 245 corrected to 235) and a plasma protein binding
median asserted before it was computed (92.4% corrected to 91.8%). Both were
corrected before freeze. Recording them is the point — the checks work.

Consistent with ICMJE and COPE positions, no AI tool is listed as an author or
credited with a scientific contribution.
