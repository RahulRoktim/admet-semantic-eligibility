# Content licence — original written and visual material

Copyright © 2026 Md. Rahul Reza Roktim.

The original written and visual material authored for this project is licensed
under the **Creative Commons Attribution 4.0 International licence (CC BY 4.0)**.

Full licence text: <https://creativecommons.org/licenses/by/4.0/legalcode>
Summary: <https://creativecommons.org/licenses/by/4.0/>

## What this covers

| Path | Material |
| --- | --- |
| `preprint/manuscript/**` | the manuscript and its reference list |
| `preprint/figures/*.png`, `preprint/figures/*.pdf` | Figures 1–3 as rendered |
| `preprint/tables/*.csv` | Tables 1–2 and the supplementary sensitivity table, as laid out by this project |
| `preprint/results/*.json`, `preprint/results/*.md` | derived result artefacts and summaries computed by this project |
| `preprint/REPRODUCE.md`, `preprint/LICENCE_REVIEW.md` | project documentation |
| `docs/**`, `README.md`, and other project-authored documentation | project documentation |

Attribution requirement: cite the preprint (see `preprint/CITATION.cff`) or,
where a citation is not practical, credit "Md. Rahul Reza Roktim, ADMET external
validation preprint" with a link to the source repository.

## What this does NOT cover

This licence applies **only to material authored by this project**. It confers
no rights over third-party material, and it does not and cannot relicense it.

- **Code** is licensed separately under MIT — see `LICENSE`.
- **Third-party datasets** remain under their own upstream licences — see
  `DATA_LICENSES.md`. This includes any third-party values that appear inside
  a project-authored artefact.
- **Third-party software dependencies** remain under their own licences — see
  `THIRD_PARTY_LICENSES.md`.

### Specific caveat for derived result artefacts

Files under `preprint/results/` and `preprint/tables/` are computed by this
project, but several of them contain values **derived from** third-party
datasets:

- experimental measurement values originating from the ASAP Discovery snapshot
  (CC0-1.0) and the Biogen Computational-ADME public set (MIT);
- aggregate statistics computed over the reconstructed Therapeutics Data
  Commons reference tables, whose upstream licensing provenance is ambiguous
  and which are **not redistributed** by this project.

The CC BY 4.0 grant above applies to this project's selection, arrangement,
computation and presentation. It does not extend to any underlying third-party
data, and it makes no claim of ownership over it. Anyone reusing these files
should also observe the upstream terms recorded in `DATA_LICENSES.md`.
