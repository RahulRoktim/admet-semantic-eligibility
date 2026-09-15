# Deviations and open release issues

## Deviations from the scientific freeze

**None.** No scientific number, cohort definition, compatibility decision,
statistical method, figure or table has changed since
`preprint/SCIENTIFIC_FREEZE.md` was generated.

Any future change requires an entry here stating what changed, why, which
hashes in the freeze record are invalidated, and who authorised it.

One non-scientific correction has been made since the freeze and is recorded
below. It changed the manuscript hash in the freeze record and nothing else.

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
| Release scanner against a built archive | Clean; and correctly fails on a deliberately leaked archive |

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
