# China A-share Five-Year Source Expansion

This operation captures raw, source-keyed BaoStock daily rows and complete
listing-to-end adjustment-factor history for the exact frozen five-year
population. It writes immutable Parquet partitions under owner-only
workstation custody and grants no stable-ID research, canonical Apply,
backtest, Product, publication, or deployment authority.

```bash
scripts/admin/capture-china-ashare-five-year-source-expansion.sh \
  --population-package /absolute/population-package \
  --custody-root /absolute/private/source-expansion-custody \
  --partition-size 50 \
  --maximum-new-partitions 0 \
  --maximum-attempts-per-partition 3
```

`--maximum-new-partitions 0` processes every remaining partition. A positive
value bounds one invocation. Every completed partition is exactly reread
before the next begins; restarting the same command verifies and skips all
completed partitions. Each partition permits at most three connection attempts
by default and remains absent unless every request, Parquet file, manifest,
hash, scope, key, row count, permission, and closed file-set check passes.

Run only one acquisition process. A bounded two-process experiment caused one
BaoStock adjustment request and logout state to fail while the other process
completed; the failed partition was never published. The source therefore
remains serial even though later workstation normalization and reconciliation
may use CPU parallelism.

Rows for unresolved occurrences remain keyed only by provider security ID.
They may be retained for later recovery but cannot receive a stable identity
or enter a research panel until separate evidence resolves them.

Normalize every currently complete raw partition into separately governed
stable-ID source observations with:

```bash
scripts/admin/normalize-china-ashare-five-year-source-expansion.sh \
  --population-package /absolute/population-package \
  --plan-root /absolute/private/source-expansion-custody/plan=FINGERPRINT \
  --custody-root /absolute/private/normalized-expansion-custody \
  --maximum-new-partitions 0
```

This command may run while later raw partitions are still being acquired. It
exactly rereads and skips existing normalized partitions, processes each next
complete raw partition, and stops at the first unavailable raw partition.
Resolved targets become typed unadjusted bars, daily states, and provider
adjustment observations. Quarantined targets remain source-keyed in raw
custody and contribute only explicit quarantine counts. Normalization does not
resolve official price limits, adjustment economics, canonical data, return
labels, research admission, Product publication, or deployment.

After every planned partition is present, finalize the source-only census:

```bash
scripts/admin/finalize-china-ashare-five-year-source-expansion.sh \
  --plan-root /absolute/private/source-expansion-custody/plan=FINGERPRINT
```

Finalization fails while any partition is absent. It exactly rereads every
partition and binds total rows, zero-row targets, suspensions, risk-warning
observations, target dispositions, date bounds, request counts, and the ordered
partition-manifest set into one immutable completion report. This closes only
raw-source acquisition; normalization, cross-family coverage, and research
admission remain separate gates.
