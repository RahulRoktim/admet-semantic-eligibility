# Licence review for the external-validation preprint

> **SUPERSEDED — retained as the audit trail for a decision already taken.**
>
> This was the pre-decision analysis. The conservative split-licence option it
> recommends has since been implemented: MIT for code (`LICENSE`), CC BY 4.0 for
> original content (`CONTENT_LICENSE.md`), upstream terms preserved per dataset
> (`DATA_LICENSES.md`), dependency notices recorded
> (`THIRD_PARTY_LICENSES.md`), and the ten reconstructed Therapeutics Data
> Commons reference tables excluded from redistribution (Option B of §4).
>
> The quotations of the former `COPYRIGHT` file below describe the repository's
> state *before* that change and are preserved deliberately. For the licensing
> that actually applies, read `DATA_LICENSES.md`.

Original text follows.

---

Status at the time of writing: **PROPOSAL — no licence file has been changed.**

## 1. Current state

`COPYRIGHT` declares the whole repository proprietary:

> Copyright (c) 2026 Md. Rahul Reza Roktim. All rights reserved. ... No licence,
> express or implied, is granted to use, copy, modify, merge, publish,
> distribute, sublicense, or sell any part of this repository.

This is incompatible with a reproducibility package. A reader cannot legally
run the analysis, and *Journal of Cheminformatics* requires an open licence for
code. It is the single hardest blocker to release.

There is no `NOTICE` file anywhere in the repository, although `COPYRIGHT`
states that one accompanies redistributed third-party components.

## 2. What the preprint actually needs to ship

Only the Strategy B scope. The DILIrank bundle, the ChEMBL evidence pipeline,
the conflict engine and the frontend are **not** part of the reproducibility
package and their licensing does not need to be resolved for this release.

| Component | Path | Origin | Upstream licence | Redistributable? |
| --- | --- | --- | --- | --- |
| Preprint analysis, figures, tables, tests | `preprint/**` | this project | to be assigned | yes, once assigned |
| Benchmark machinery reused by the analysis | `validation/external_prediction/*.py` | this project | to be assigned | yes, once assigned |
| ASAP antiviral ADMET snapshot | `validation/external_prediction/source_snapshots/asap_antiviral_admet_2025_unblinded.csv` | Polaris / ASAP Discovery | **CC0-1.0** | **Yes**, unrestricted |
| Biogen Computational-ADME public set | `validation/external_prediction/source_snapshots/biogen_ADME_public_set_3521.csv` | molecularinformatics/Computational-ADME | **MIT** | **Yes**, with attribution |
| Reconstructed TDC training references (10 CSVs, includes `source_target` labels) | `validation/external_prediction/training_reference/*.csv` | Harvard Dataverse via PyTDC 1.1.15 | **AMBIGUOUS — see §4** | **Undetermined** |
| Frozen prediction rows | `validation/external_prediction/results/*.csv` | derived from the two snapshots above + local model inference | derivative | follows the source licences |
| New HLM sensitivity predictions | `preprint/results/hlm_low_clearance_predictions.csv` | derived from the ASAP CC0 snapshot + local inference | derivative of CC0 | yes |
| Duke temporal Caco-2 set | not committed (hash-pinned only) | GitHub repository with no stated licence | none stated | **No — correctly excluded** |
| ADMET-AI 2.0.1 model weights | not committed; installed from PyPI | Chemprop-based, MIT | MIT | not redistributed |

## 3. Third-party Python dependencies

All direct dependencies are permissive and impose no copyleft obligation on
this repository: httpx (BSD-3-Clause), RDKit (BSD-3-Clause), pandas (BSD),
SciPy (BSD), NumPy (BSD), Pint (BSD), PyYAML (MIT), SQLAlchemy (MIT), chemprop
(MIT), tenacity (Apache-2.0), matplotlib (PSF/matplotlib licence), plus
alembic, FastAPI, uvicorn and admet-ai, all permissive. **No dependency blocks
an MIT, BSD-3-Clause or Apache-2.0 release.**

## 4. Unresolved: the reconstructed TDC training references

`admet_ai_training_manifest.json` records:

> `"license": "CC BY 4.0 per TDC dataset pages; retrieved CSV materializations
> contain no embedded license text"`

That is a **collection-level statement about TDC's own pages, not a
per-dataset verification**, and it is the weakest licence claim in the package.
It matters because these ten CSVs carry the experimental `source_target`
values, not just structures.

The specific concern: several of these endpoints originate from AstraZeneca
data deposited in ChEMBL, which ChEMBL distributes under **CC BY-SA 3.0** — a
share-alike licence, not CC BY 4.0. That affects at least
`Clearance_Microsome_AZ`, `Clearance_Hepatocyte_AZ`, `Lipophilicity_AstraZeneca`
and `PPBR_AZ`. Redistributing share-alike labels inside an otherwise
permissively licensed repository is a licence-compatibility question that
should not be answered by assumption.

**This must not be resolved by relicensing. It must be resolved by checking.**

### What is actually required, and why the exposure is small

The ten CSVs serve two distinct purposes with different needs:

1. **Training-overlap detection** (all ten datasets) needs only **structures** —
   SMILES, InChIKey, parent forms, Murcko scaffolds. It does **not** need
   `source_target`.
2. **The two baselines** (training-set mean, 1-NN) need `source_target`, and
   only for the **three** evaluated endpoints: `Clearance_Microsome_AZ`,
   `Lipophilicity_AstraZeneca`, `PPBR_AZ`.

So the exposure is three label columns, not ten datasets.

### Options, in order of preference

- **Option A (recommended).** Verify the licence of those three datasets at
  source (TDC dataset page, the Harvard Dataverse record, and the originating
  publication or ChEMBL deposition). Redistribute under whichever upstream
  licence actually applies, recorded per dataset in a `NOTICE` file. If any is
  CC BY-SA, keep that file under CC BY-SA and say so explicitly — mixed
  licensing of separate data files is normal and legally clean.
- **Option B.** Ship structures and identifiers only, drop `source_target` from
  the committed CSVs, and provide a small PyTDC fetch script that regenerates
  the labels locally. This makes the package fully permissive but breaks the
  "no network access" reproduction guarantee for the two baselines. Overlap
  detection and all headline metrics would still reproduce offline.
- **Option C.** Ship only the derived baseline constants (training mean and
  median per endpoint) plus the nearest-neighbour target lookup restricted to
  the structures actually matched. This is a much smaller derivative but is
  still a derivative, so it does not remove the question — only shrinks it.

Option B is the safe fallback if the upstream licence cannot be established
before release.

## 5. Proposed licence structure

Subject to §4 being resolved:

| Scope | Proposed licence |
| --- | --- |
| All source code (`preprint/**`, `validation/**`, `backend/**`, `scripts/**`, `frontend/**`) | **MIT** — simplest, imposes no obligation on downstream reviewers, and is compatible with every dependency above. BSD-3-Clause or Apache-2.0 are equally acceptable; Apache-2.0 additionally grants patent rights, which is irrelevant here. |
| Manuscript, documentation, figures, generated tables and result JSON | **CC BY 4.0** |
| `validation/external_prediction/source_snapshots/asap_*.csv` | remains **CC0-1.0** (upstream), recorded in `NOTICE` |
| `validation/external_prediction/source_snapshots/biogen_*.csv` | remains **MIT** (upstream), recorded in `NOTICE` |
| `validation/external_prediction/training_reference/*.csv` | **upstream licence, per dataset, once verified** — recorded individually in `NOTICE`. Not relicensed. |
| Bundled DILIrank data and the rest of the platform | out of scope for this release; licensing unchanged and undecided |

Implementation, when approved:

1. Add `LICENSE` (MIT) covering code.
2. Add `LICENSE-DOCS` or a header note applying CC BY 4.0 to `preprint/manuscript/**`, `preprint/figures/**`, `preprint/tables/**`, `preprint/results/**`.
3. Add `NOTICE` listing every redistributed third-party file with origin, version or commit, SHA-256 and its own licence.
4. Rewrite `COPYRIGHT` to point at the above rather than asserting all rights reserved, **or** narrow its scope explicitly to the components not covered by the new licences.
5. Add `CITATION.cff`.

## 6. Decisions required from the copyright holder

1. **Which code licence?** MIT (recommended), BSD-3-Clause, or Apache-2.0.
2. **Does the permissive licence cover the whole repository or only the
   preprint-relevant subset?** Relicensing only `preprint/**` and
   `validation/external_prediction/**` is defensible and lower-commitment, but
   a reviewer cloning the repo will see a proprietary `COPYRIGHT` at the root
   and may treat the whole package as unusable. Whole-repository relicensing is
   cleaner for the preprint.
3. **How to resolve §4** — Option A (verify), B (drop labels, add fetch script),
   or C (ship derived constants).

Nothing in this file has been applied. No licence file was created, modified or
deleted.
