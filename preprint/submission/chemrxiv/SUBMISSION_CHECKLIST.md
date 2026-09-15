# ChemRxiv submission checklist

Fields you will enter manually on the submission form. Everything marked
"prepared" exists in this folder and can be pasted verbatim.

Run the submission gate first — it refuses to pass while any placeholder
remains:

    PYTHONPATH=backend python preprint/analysis/verify_manuscript_claims.py --submission-ready

## Fields requiring your input

| Field | Status | Source |
| --- | --- | --- |
| Author affiliation | **REQUIRED FROM YOU** | `USER_INPUT_REQUIRED.md` §1 |
| Corresponding-author email | **REQUIRED FROM YOU** | `USER_INPUT_REQUIRED.md` §2 |
| ORCID | **REQUIRED FROM YOU**, or tell me to remove the field | `USER_INPUT_REQUIRED.md` §3 |
| Zenodo DOI | inserted at release checklist step 6 | not yet minted |

## Fields prepared

| Field | Value or file |
| --- | --- |
| Title | *What survives? Semantic eligibility, distribution shift and metric interpretation in external validation of ADMET predictors* |
| Author name | Md. Rahul Reza Roktim |
| Abstract | `abstract.txt` (also manuscript §Abstract) |
| Keywords | `keywords.txt` (8) |
| Primary category | Theoretical and Computational Chemistry → Cheminformatics |
| Secondary category | Pharmaceutical Science and Drug Discovery |
| Data and code availability | `statements.md` |
| Competing interests | `statements.md` |
| Funding | `statements.md` |
| Acknowledgements | `statements.md` |
| Author contributions | `statements.md` |
| Cover note | `cover_note.md` |
| AI-assistance note | `ai_assistance_note.md` — supply only if asked |
| Licence for the posted preprint | CC BY 4.0, matching `CONTENT_LICENSE.md` |

## Files to upload

| File | Role |
| --- | --- |
| `manuscript.md`, or the PDF you generate from it | main text |
| `figure1_eligibility_funnel.pdf` | Figure 1 |
| `figure2_shift_and_compression.pdf` | Figure 2 |
| `figure3_baseline_relative.pdf` | Figure 3 |
| `table1_compatibility.csv` | Table 1 |
| `table2_external_results.csv` | Table 2 |
| `supplementary_sensitivity.csv` | supplementary |
| `CLAIM_AUDIT.md` | supplementary, optional but recommended |

## Before you click submit

- [ ] `--submission-ready` gate passes, i.e. no placeholders remain
- [ ] Zenodo DOI present in the manuscript title page and in `statements.md`
- [ ] GitHub release URL resolves publicly
- [ ] PDF renders correctly: no broken mathematics, all three figures present,
      tables legible
- [ ] Competing-interests declaration still accurate on the day of submission
- [ ] Anyone named in the acknowledgements has consented
- [ ] You have read `ai_assistance_note.md` and agree it is accurate

## PDF generation

The repository has **no PDF toolchain**, and none was added — that would pull in
a large dependency for a single artefact. Generate the PDF with whatever you
already have, for example:

    pandoc preprint/manuscript/manuscript.md -o manuscript.pdf --resource-path=preprint/figures --pdf-engine=xelatex

Or paste the Markdown into a word processor and export. ChemRxiv accepts PDF and
Word.

After generating, work through the rendering checkbox above. Markdown-to-PDF
converters commonly mangle the superscripts, the Unicode minus signs and the
wide tables in this manuscript, and those are exactly the places where a
silently corrupted number would be hardest to notice.
