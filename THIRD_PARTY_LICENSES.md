# Third-party software licences

The MIT licence in `LICENSE` applies to source code authored in this repository
only. **It does not change the licence of any dependency.** Every package below
remains under its own licence, held by its own copyright holders.

Licence identifiers were read from the installed package metadata in the
verified environment (Python 3.12.10, Windows 11), not assumed. Where a package
declares a composite expression, it is reproduced verbatim.

## Runtime dependencies used by the preprint analysis

| Package | Version | Licence |
| --- | --- | --- |
| `admet-ai` | 2.0.1 | MIT |
| `chemprop` | 2.3.1 | MIT |
| `rdkit` | 2026.3.5 | BSD-3-Clause |
| `numpy` | 2.5.2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| `scipy` | 1.18.1 | BSD-3-Clause |
| `pandas` | 3.0.5 | BSD-3-Clause |
| `matplotlib` | 3.11.1 | Matplotlib licence (PSF-derived, BSD-compatible) |
| `torch` | 2.13.0 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT |
| `lightning` | 2.6.5 | Apache-2.0 |

## Additional dependencies of the surrounding application

Present in the repository but not required to reproduce the preprint.

| Package | Version | Licence |
| --- | --- | --- |
| `SQLAlchemy` | 2.0.52 | MIT |
| `alembic` | 1.19.1 | MIT |
| `fastapi` | 0.141.1 | MIT |
| `uvicorn` | 0.52.4 | BSD-3-Clause |
| `httpx` | 0.28.1 | BSD-3-Clause |
| `pint` | 0.25.3 | BSD-3-Clause |
| `PyYAML` | 6.0.3 | MIT |
| `tenacity` | 9.1.4 | Apache-2.0 |
| `pytest` | 9.1.1 | MIT |

No dependency imposes a copyleft obligation on this repository's own code.

## Third-party data

Datasets are governed separately. See `DATA_LICENSES.md`, which records each
dataset's source, licence, redistribution status and attribution requirements
individually. Two datasets are redistributed here under their upstream terms:

### ASAP Discovery Antiviral ADMET 2025 (unblinded)

Released by the ASAP Discovery Consortium / OpenADMET under **CC0-1.0**, a
public domain dedication. No attribution is legally required; this project
cites the dataset as a matter of scientific practice.

### Biogen Computational-ADME public set

Distributed under the **MIT licence** from
<https://github.com/molecularinformatics/Computational-ADME>. MIT requires that
the copyright notice and permission notice accompany redistribution. The
upstream `LICENSE` file at commit `b00df003de117ce9e5b381afd886095c5f2af2d5`
governs the redistributed file
`validation/external_prediction/source_snapshots/biogen_ADME_public_set_3521.csv`,
and its terms are preserved by this notice and by the dataset record in
`DATA_LICENSES.md`.

### Not redistributed

The reconstructed Therapeutics Data Commons reference tables and the temporal
ChEMBL Caco-2 set are **not** included in the public release. See
`DATA_LICENSES.md` §3 and §4 for the reasons and for how to obtain them.
