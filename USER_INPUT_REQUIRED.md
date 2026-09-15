# Outstanding items before submission

Author metadata is resolved. **Two deferred fields remain, both created at the
same moment and neither able to exist before then.**

| Placeholder | Becomes available at | Appears in |
| --- | --- | --- |
| `[[ZENODO_DOI]]` | the Zenodo deposit, created from the GitHub release | manuscript title page, submission statements, `CITATION.cff` |
| `[[RELEASE_DATE]]` | the same deposit | `CITATION.cff`, Zenodo metadata draft |

**The manuscript itself contains exactly one placeholder, `[[ZENODO_DOI]]`.**
`[[RELEASE_DATE]]` appears only in metadata templates and instructions, never in
publication text.

The GitHub release URL needs no placeholder: the repository URL is already
written out in full.

## Gate

    PYTHONPATH=backend python preprint/analysis/verify_manuscript_claims.py --submission-ready

This exits non-zero while any placeholder remains. Run it immediately before
ChemRxiv submission; passing is the mechanical guarantee that no placeholder
reaches the posted preprint.

## Where the DOI goes

Insert it in all five places at once (release checklist step 6):

- `preprint/manuscript/manuscript.md` — title page
- `preprint/submission/chemrxiv/manuscript.md` — submission copy
- `preprint/submission/chemrxiv/statements.md` — Data and code availability
- `preprint/submission/chemrxiv/zenodo_metadata.json` — also `[[RELEASE_DATE]]`
- `preprint/CITATION.cff` — add `doi:` and `date-released:`

Then regenerate the freeze record, because the manuscript hash changes:

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
