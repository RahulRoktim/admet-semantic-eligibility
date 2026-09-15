# Release checklist — v1.0.0-preprint

Strictly ordered. Each step has a gate that must pass before the next is
started. **Steps 3–9 have not been performed.** Nothing has been pushed, tagged,
released, deposited or submitted.

Do these one at a time, deliberately. Several are irreversible: a published
Zenodo DOI cannot be withdrawn, and a posted ChemRxiv preprint cannot be
unposted, only superseded by a new version.

---

## ✅ Step 1 — Clean public export and root commit *(done)*

Built from the frozen private release commit
`bba8a77e388985c5a38a346338f432e3e0f93d39` and committed to a fresh repository
with no parent relationship to the private history.

**Gate:** working tree clean; one root commit, no parents; no remote; no Git
alternates; private commits unreachable; excluded files absent from the working
tree, the index, every Git object and every archive. All verified.

## ✅ Step 2 — Clean-clone reproduction *(done)*

Level 1 reproduced from a fresh clone with the excluded tables absent.

**Gate:** 66/66 files byte-identical on checkout; every manuscript number,
Figures 1–3, Tables 1–2, the supplementary sensitivity table and the claim audit
regenerate; 66/66 byte-identical after regeneration; 26 tests pass; final audit
16/16.

## ✅ Step 3a — Author metadata *(done)*

Author, affiliation, corresponding email and ORCID are populated throughout. The
Zenodo DOI and the release date are both inserted. No unresolved publication
placeholder remains in any release-facing file.

---

## ⬜ Step 3b — Create the public GitHub repository and push

Create an **empty** public repository named `admet-semantic-eligibility` under
your account. Do not initialise it with a README, licence or `.gitignore` —
anything it creates would become a parent commit and defeat the clean history.

```
git remote add origin https://github.com/<owner>/admet-semantic-eligibility.git
git push -u origin main
```

**Gate:** the pushed repository contains exactly one commit; the private
repository remains private and untouched.

> **The private repository must stay private.** It retains the ten excluded
> reference tables in its history. Making it public would redistribute them and
> defeat this entire boundary.

## ⬜ Step 3c — Tag

```
git tag -a v1.0.0-preprint -m "Focused ADMET external-validation preprint"
git push origin v1.0.0-preprint
```

**Gate:** the tag points at the root commit.

> **Enable the Zenodo–GitHub integration BEFORE step 4** if you want the DOI
> minted automatically. Zenodo only archives releases created *after* the
> repository is switched on at <https://zenodo.org/account/settings/github/>.
> Turning it on afterwards will not capture this release.

## ⬜ Step 4 — GitHub release

Create the release from tag `v1.0.0-preprint`, using
`RELEASE_NOTES_v1.0.0-preprint.md` as the body.

**Gate:** release page loads publicly; the source archive it generates does
**not** contain `validation/external_prediction/training_reference/*.csv`.
Verify by downloading it and running:

    PYTHONPATH=backend python preprint/analysis/release_package.py --check --archive <downloaded>.zip

This is the single most important check in the sequence. It exits non-zero if a
non-redistributed file is present.

## ⬜ Step 5 — Zenodo archive and DOI

Either automatic, if the integration was enabled at step 3, or manual upload.
Metadata to use is in `preprint/submission/chemrxiv/zenodo_metadata.json`.

**Gate:** DOI resolves; deposit metadata matches the JSON; deposited archive
contains no excluded file — re-run the archive check above against the Zenodo
download.

## ⬜ Step 6 — Insert the DOI and release URL

Done: the reserved version DOI `10.5281/zenodo.22765692` is inserted in:

- `preprint/manuscript/manuscript.md` (title page)
- `preprint/submission/chemrxiv/statements.md`
- `preprint/submission/chemrxiv/manuscript.md` (the submission copy)
- `preprint/CITATION.cff` — also add `doi:` and `date-released:`
- `preprint/submission/chemrxiv/zenodo_metadata.json` — release date `2026-09-15`

Commit as a metadata-only change. It alters no number, so it needs no deviation
record — but it does invalidate the manuscript hash in `SCIENTIFIC_FREEZE.md`,
so regenerate:

    PYTHONPATH=backend python preprint/analysis/write_scientific_freeze.py

## ⬜ Step 7 — Rerun the final verifier

    PYTHONPATH=backend python preprint/analysis/run_preprint_analysis.py
    PYTHONPATH=backend python preprint/figures/make_figures.py
    PYTHONPATH=backend python preprint/analysis/verify_manuscript_claims.py --submission-ready
    PYTHONPATH=backend python preprint/analysis/release_package.py --build --check
    PYTHONPATH=backend python preprint/analysis/write_checksums.py
    PYTHONPATH=backend python -m pytest backend/tests validation/tests preprint/tests -q

**Gate:** `--submission-ready` exits 0, meaning no placeholder remains. All
tests pass. **If any scientific number has changed, stop** and record a
deviation in `preprint/DEVIATIONS.md` before going further.

## ⬜ Step 8 — Generate the submission PDF

See `preprint/submission/chemrxiv/SUBMISSION_CHECKLIST.md`. No PDF toolchain is
bundled.

**Gate:** all three figures present; superscripts, Unicode minus signs and wide
tables render correctly; spot-check at least five numbers in the PDF against
`preprint/results/analysis_summary.md`.

## ⬜ Step 9 — ChemRxiv submission

Category: Theoretical and Computational Chemistry → Cheminformatics. Statements
to paste are in `preprint/submission/chemrxiv/statements.md`.

**Gate:** every box in `SUBMISSION_CHECKLIST.md` ticked.

---

## If something goes wrong

| Situation | Action |
| --- | --- |
| A scientific number changes at any step | **Stop.** Record the change and its cause in `preprint/DEVIATIONS.md`, regenerate the freeze, and re-verify before continuing. |
| An excluded file appears in a release or Zenodo archive | **Stop.** Delete the release/deposit, fix the packaging, re-verify, start again from step 3. |
| The Zenodo integration was not enabled before the release | Do not re-tag. Deposit manually at step 5 instead. |
| A placeholder reaches the posted preprint | Post a corrected version; ChemRxiv supports versioning. |
