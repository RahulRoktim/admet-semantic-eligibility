# Deviations and open release issues

## Deviations from the scientific freeze

**None.** No scientific number, cohort definition, compatibility decision,
statistical method, figure or table has changed since
`preprint/SCIENTIFIC_FREEZE.md` was generated.

Any future change requires an entry here stating what changed, why, which
hashes in the freeze record are invalidated, and who authorised it.

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

