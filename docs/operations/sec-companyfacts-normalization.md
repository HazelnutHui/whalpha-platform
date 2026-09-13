# SEC Company Facts Normalization

## Boundary

Run only from a clean revision after the final Company Facts source/census and
the final filing-clock package pass formal reread. This is a network-free,
credential-free Dell computation. It does not write `/data` and can run while
the separately bounded EOD/Identity writer is active.

The target parent must be an owner-only normalized-source state root. The
exact target and its partial sibling must not already exist; any interruption
leaves the exact partial for inspection rather than silently deleting it.

```bash
PYTHONPATH=apps/api/src .venv/bin/python \
  -m tip_api.providers.sec.companyfacts_normalized_source_cli \
  --companyfacts-package <companyfacts-package> \
  --companyfacts-custody-root <companyfacts-root> \
  --companyfacts-census-root <final-companyfacts-census-root> \
  --filing-clock-package <filing-clock-package> \
  --output-package <normalized-root>/build=<id> \
  --range-start YYYY-MM-DD \
  --range-end YYYY-MM-DD \
  --workers 8 \
  --execute
```

For a multi-process Dell run, cap numerical-library threads before Python
starts so each process remains one CPU worker rather than recursively creating
one BLAS pool per worker:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 <command-above>
```

An 8-worker attempt without these caps exceeded the bounded transient
service's task count while importing PyArrow/Numpy and stopped before writing
an artifact. The thread caps preserve eight-way process parallelism and avoid
oversubscription; they do not change normalized content.

## Required stops and local quarantines

Stop the whole build on source/census/clock lineage drift, archive read/CRC
failure, unsafe path or mode, worker/member overlap, missing worker artifact,
schema/hash/count/fingerprint mismatch, or failure to reproduce the exact
41,619,407 in-range occurrence count.

Do not stop unrelated rows for a missing accession clock or an isolated field
normalization problem. Preserve the occurrence, null only the unsupported
derived fields, add deterministic quarantine reasons, and include it in all
denominators.

After atomic publication, formally reread every Parquet artifact and record
the exact package identity, artifact sizes, occurrence/catalog counts,
clock/quarantine residuals, tests, and zero-authority boundary in a dated
audit and current status.
