# Outstanding items before submission

Author metadata is resolved. The Zenodo DOI is resolved. **One deferred field
remains.**

| Placeholder | Status | Appears in |
| --- | --- | --- |
| Zenodo DOI | **Resolved** to `10.5281/zenodo.22765692` | recorded; the placeholder is gone |
| `[[RELEASE_DATE]]` | Outstanding until public release | `CITATION.cff`, Zenodo metadata draft, release checklist |

**The manuscript now contains no placeholder at all.** The DOI placeholder token
is deliberately not written out anywhere in this repository any more, because
`check_doi_consistency.py` treats any occurrence of it as a release blocker. `[[RELEASE_DATE]]` appears
only in metadata templates and instructions, never in publication text, and is
the single allowed pre-release placeholder.

The GitHub release URL needs no placeholder: the repository URL is already
written out in full.

## Gate

    PYTHONPATH=backend python preprint/analysis/verify_manuscript_claims.py --submission-ready

This exits non-zero while any placeholder remains. Run it immediately before
ChemRxiv submission; passing is the mechanical guarantee that no placeholder
reaches the posted preprint.

## Where the DOI went

The reserved Zenodo **version** DOI `10.5281/zenodo.22765692` (deposition 22765692, still an
unpublished draft) is now recorded in:

- `preprint/manuscript/manuscript.md` — title page
- `preprint/submission/chemrxiv/manuscript.md` — submission copy
- `preprint/submission/chemrxiv/statements.md` — Data and code availability
- `preprint/submission/chemrxiv/zenodo_metadata.json` — deposition metadata
- `preprint/CITATION.cff` — `doi:`

The concept DOI is deliberately **not** used: the paper cites the specific
version so a reader retrieves this exact reproducibility artefact.
`preprint/analysis/check_doi_consistency.py` enforces all of this.

The freeze record was regenerated because the manuscript hash changed:

    PYTHONPATH=backend python preprint/analysis/write_scientific_freeze.py

## Resolved author metadata

| Field | Value |
| --- | --- |
| Author | Md. Rahul Reza Roktim |
| Affiliation | Department of Pharmacy, Daffodil International University, Dhaka, Bangladesh |
| Corresponding email | roktim2311091058@diu.edu.bd |
| ORCID | 0009-0003-6518-0495 |

## Confirm before submitting

- [ ] Funding statement is accurate: *This research received no specific
      external funding.*
- [ ] Competing-interests declaration is accurate: *The author declares no
      competing interests.*
- [ ] You have read `preprint/submission/chemrxiv/ai_assistance_note.md` and
      agree it is factually correct.
