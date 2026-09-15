# Deviations and open release issues

## Deviations from the scientific freeze

**None.** No scientific number, cohort definition, compatibility decision,
statistical method, figure or table has changed since
`preprint/SCIENTIFIC_FREEZE.md` was generated.

Any future change requires an entry here stating what changed, why, which
hashes in the freeze record are invalidated, and who authorised it.

Two non-scientific corrections have been made since the freeze and are recorded
below. Both changed the manuscript hash in the freeze record and nothing else.

---

## RESOLVED — excluded data and Git history

**Status: resolved by clean public export (Option 2).** No scientific result was
affected at any point.

### The problem

The ten reconstructed Therapeutics Data Commons reference tables were committed
early in the private development repository and were present in every commit up
to the frozen release commit. Deciding not to redistribute them did not by
itself remove them: they were already objects in that repository's history, and
`git clone` transfers full history.

### The resolution

The private repository remains **private** and unchanged. Its history is
preserved intact as the development and provenance record; nothing was rewritten
and no commit was discarded.

This public repository is a **clean export** built from the frozen private
release commit `bba8a77e388985c5a38a346338f432e3e0f93d39`. It was initialised
with `git init` and begins at a fresh root commit with **no parent relationship
to the private history**.

Verified before the root commit was created, and again from a fresh clone:

| Check | Result |
| --- | --- |
| Commits in this repository | 1 (root commit, no parents) |
| Private base and frozen commits reachable | No — absent from the object database |
| Remotes configured | None |
| Git alternates or borrowed object database | None |
| Excluded filenames in any Git object | None |
| Excluded file *content* hashes among Git blobs | None — all 10 upstream hashes searched against every blob |
| Excluded files in the working tree | None |
| Excluded files in the Git index | None |
| Excluded files in `git archive` output | None |
| Release scanner against a built archive | Clean; and correctly fails on a deliberately leaked archive (the control was originally run on an archive with no top-level prefix; see the correction below) |

A negative control was run before the root commit: a forbidden file was planted,
confirmed blocked by `.gitignore`, confirmed absent from the index, confirmed
classified as excluded and never released, and confirmed to make the scanner
exit non-zero when placed inside an archive. The control artefact was then
removed.

### What this does and does not claim

The omitted tables are **third-party material**, not proprietary to this project.
They are withheld because their upstream licensing provenance could not be
established with confidence, not because anyone here claims rights over them.
Their SHA-256 hashes and complete reconstruction instructions are published so
that an independent rebuild can be verified byte for byte.

No reported result depends on their redistribution: Level 1 reproduction was
confirmed to run, and to reproduce every published number, in a fresh clone in
which those files are absent.

---

## RESOLVED — released files pointed at the private development repository

**Status: corrected before the first push. Authorised by the author on
2026-09-15.**

### The problem

Six URLs across five released files still carried the **private** development
repository's path — its `ADMET-Evidence-Graph` name — rather than this public
export. The affected fields were the manuscript's "Code and data" line, the
ChemRxiv manuscript copy, the ChemRxiv statements file, the
`related_identifiers` entry in the Zenodo deposition draft, and both
`repository-code` and `license-url` in `preprint/CITATION.cff`.

The old URL is deliberately not written out in full anywhere in this
repository, because the guard described below treats any occurrence of it in a
released file as a release blocker — including an occurrence in this
explanation.

Published unchanged, that would have named the private repository in the paper
and in a public Zenodo record, and given every reader a link they cannot fetch.
No existing gate caught it: the claim verifier checks numbers, forbidden
phrases and disclosures, not URLs.

### The resolution

All six occurrences now point at this repository,
`RahulRoktim/admet-semantic-eligibility`.

A regression guard was added at `preprint/analysis/check_repository_urls.py`,
wired into `final_audit.py` as `repository_urls_point_to_public_export` and
covered by `preprint/tests/test_repository_urls.py`. It fails if any released
file names the private repository, if any released file references a GitHub
repository that is neither this one nor a declared upstream data source, or if
the declared `repository-code` metadata is not exactly the public URL. Five of
its eleven tests are negative controls that reintroduce the fault in each
affected file and confirm the guard fires.

### Effect on the scientific record

None. The correction changed URL text only.

| Freeze record group | Effect |
| --- | --- |
| `results` block SHA-256 | Unchanged |
| `compatibility` block SHA-256 | Unchanged |
| Figure hashes | Unchanged |
| Table hashes | Unchanged |
| Compatibility-matrix hash | Unchanged |
| Manuscript hash | **Invalidated and regenerated** — URL text only |

The Level 1 pipeline was re-run: its hard reproduction gate reported
`ALL_PUBLISHED_METRICS_REPRODUCED`, and every results and table artefact
regenerated byte-identically. The `scientific_results_unchanged` audit check
passes against the original pre-preparation baseline.

Two bare private commit identifiers remain recorded in
`preprint/SCIENTIFIC_FREEZE.md` as deliberate provenance. They are hashes, not
locations: they name no repository and resolve to nothing outside the private
object database.

---

## RESOLVED — reserved Zenodo DOI and corrected publication metadata

**Status: applied before the public release. Authorised by the author on
2026-09-15.**

### What changed

A Zenodo draft deposition was created on production Zenodo (deposition 22765692)
and a **version** DOI was reserved: `10.5281/zenodo.22765692`. The record remains
an unpublished draft. Three publication-metadata changes follow from it.

**1. The reserved DOI was inserted.** It replaces the former placeholder in the
manuscript title page, the ChemRxiv manuscript copy, the ChemRxiv data and code
availability statement, `preprint/CITATION.cff` and the Zenodo metadata source.
The concept DOI is deliberately not used anywhere: the paper cites the specific
version so that a reader retrieves the exact artefact the reported numbers came
from.

**2. The author's name was corrected.** Two prepared files had dropped the
honorific: the Zenodo metadata source recorded the inverted name without it, and
`CITATION.cff` split the name so that the given-names field omitted it. Both now
read `Roktim, Md. Rahul Reza`, rendering as **Md. Rahul Reza Roktim**, which is
the name on the manuscript and on the ORCID record. Nothing else in the
repository used a truncated form.

The truncated spellings are deliberately not written out here, because
`check_author_metadata.py` treats any occurrence of one in a released file as a
failure — including an occurrence in this explanation.

**3. Licensing metadata now records two licences.** The prepared metadata
asserted that "Zenodo accepts one licence identifier" and specified MIT alone.
That assertion was wrong for the production interface, which accepted both
**CC BY 4.0** and **MIT**, and both are recorded on the draft and in the local
source. This is not a blanket licence over the package: project-authored code is
MIT, original manuscript and derived content are CC BY 4.0, third-party datasets
retain their own upstream terms and are not relicensed, and the ten
upstream-derived training-reference tables are excluded from redistribution
altogether. Neither licence entry applies to third-party material.

### New guards

Two checks were added, each wired into `final_audit.py` and covered by its own
negative controls:

| Guard | Fails when |
| --- | --- |
| `preprint/analysis/check_doi_consistency.py` | a DOI digit is altered, the placeholder returns, the concept DOI is substituted, the DOI of the author's other Zenodo deposit is used, a DOI URL points elsewhere, or the DOI is missing where it belongs |
| `preprint/analysis/check_author_metadata.py` | the honorific is dropped, either citation-metadata file disagrees with the canonical values, or a foreign ORCID or corresponding email appears |

The DOI guard tolerates the release-date placeholder, which was the single
placeholder allowed before release. It was resolved to 2026-09-15 when
v1.0.0-preprint was released.

### Effect on the scientific record

None. Publication metadata only.

| Freeze record group | Effect |
| --- | --- |
| `results` block SHA-256 | Unchanged |
| `compatibility` block SHA-256 | Unchanged |
| Figure hashes | Unchanged |
| Table hashes | Unchanged |
| Compatibility-matrix hash | Unchanged |
| Manuscript hash | **Invalidated and regenerated** — DOI text only |

No cohort definition, compatibility decision, statistical method, figure, table
or reported number was touched. The Level 1 pipeline was re-run and its hard
reproduction gate reported `ALL_PUBLISHED_METRICS_REPRODUCED`.

Neither the other deposit's DOI nor this deposit's concept DOI is written out
anywhere in the repository. The guard knows both, and any appearance of either
in a released file is a release blocker — so naming them here would itself be
one.

---

## RESOLVED — the archive scanner did not catch leaks in a prefixed archive

**Status: found and fixed while building the v1.0.0-preprint package, before
anything was published. Authorised by the author on 2026-09-15.**

### The problem

`release_package.py --check --archive` is the last gate between the excluded
upstream tables and a published artefact. It did not work on the kind of
archive that actually gets published.

Published archives are never flat. `git archive --prefix=`, GitHub's
auto-generated source tarballs and Zenodo's GitHub integration all wrap the
tree in a top-level directory, so a member arrives as
`project-v1.0.0/validation/.../PPBR_AZ.csv`. The scanner matched the exclusion
patterns against that whole string, and `fnmatch`'s `*` does not cross the
leading segment, so the match failed.

The manifest-derived fallback could not compensate. It compared members against
the set of files the manifest marks as excluded, and in a clean public clone
that set is **empty by construction** — the excluded files are not present, so
nothing is classified as excluded. The one check that had to hold was the
pattern check, and that was the broken one.

A release archive built from the tag, with one excluded table deliberately
planted inside it, **passed with exit code 0**.

The earlier control recorded in the table above was genuine but was run against
an archive with no top-level prefix, which is not the shape of any archive that
is actually distributed. That is why the gap survived.

### The resolution

`archive_entry_is_excluded()` now tests every trailing path suffix of each
member, so an excluded file is caught under any wrapper directory and at any
depth. The manifest-derived test is kept as a secondary signal and is explicitly
documented as unable to stand alone.

`preprint/tests/test_archive_boundary.py` pins this with 18 tests: the predicate
under six prefix shapes, six allowed paths that must not be flagged (including
`training_reference.py` and the derived summary, which *are* released), a clean
prefixed archive that must pass, leaked archives at three prefix shapes that
must all fail, and one archive per withheld table so the coverage is not resting
on whichever file the control happened to pick.

### Effect on the scientific record

None. No number, cohort, figure, table or decision is involved. The results and
compatibility block hashes are unchanged and Level 1 reports
`ALL_PUBLISHED_METRICS_REPRODUCED`.

Nothing had been published when this was found: the repository was still
private, no GitHub Release existed, and the Zenodo record was still an
unpublished draft. **No archive containing an excluded file was ever
distributed** — the planted file existed only in a scratch copy used as the
control, and the real package was verified clean both before and after the fix.
