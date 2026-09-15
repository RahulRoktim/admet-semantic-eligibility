# Submission statements

Copy these verbatim into the ChemRxiv submission form. They match the manuscript.

## Data and code availability

All analysis code, frozen result artefacts, figure-generation scripts and the
machine-readable result set are available at
https://github.com/RahulRoktim/ADMET-Evidence-Graph and archived at
[[ZENODO_DOI]]. Reproduction is offered at two levels. Level 1 regenerates every
number, table and figure from committed, redistributable artefacts,
deterministically and without network access; a reproduction gate independently
recomputes each previously published benchmark metric and aborts if any value
differs by more than 1e-9. Level 2 documents how to obtain the upstream datasets
from their official sources, rebuild the reference tables that are not
redistributed, and compare the rebuild against the committed results.

The ASAP Discovery Antiviral ADMET 2025 unblinded snapshot (CC0-1.0) and the
Biogen Computational-ADME public set (MIT) are redistributed unchanged under
their own licences with recorded SHA-256 hashes. Ten reconstructed Therapeutics
Data Commons reference tables are not redistributed because their upstream
licensing provenance could not be established with confidence; dataset names,
source identifiers, versions, expected row counts, schema, reconstruction code
and the SHA-256 of each table as used are published instead. No reported result
depends on those files being redistributed. Project code is released under MIT;
the manuscript, figures, tables and derived results under CC BY 4.0. External
datasets retain their own upstream licences and are not relicensed by this work.

## Competing interests

The author declares no competing interests.

## Funding

This research received no specific grant from any funding agency in the public,
commercial, or not-for-profit sectors.

## Acknowledgements

The author thanks the ASAP Discovery Consortium, OpenADMET and Polaris for
releasing the antiviral ADMET dataset under a CC0 public-domain dedication, and
the authors of the Biogen Computational-ADME public set for releasing it under
an open licence. This work relies on ADMET-AI, Chemprop, the Therapeutics Data
Commons, ChEMBL and RDKit.

## Author contributions

R.R.R. designed the study, implemented the analysis, performed the evaluation,
and wrote the manuscript.

## Suggested category

Theoretical and Computational Chemistry -> Cheminformatics

Secondary, if a second category is permitted: Pharmaceutical Science and Drug
Discovery.
