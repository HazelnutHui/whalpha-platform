# Same-Day Identity and EOD Catch-Up V1

## Scope

This contract separates Massive acquisition from canonical publication. It
applies to one explicitly named XNYS session at a time. Instrument Master,
Provider Instrument Identity, Provider Ticker Resolver, normalized provider
Identity source observation, and their logical snapshot must complete before
the same session's Grouped Daily EOD can be planned or published.

The contract does not authorize a provider request or a production apply.
Those are separate bounded operations.

## Four stages

1. **Fetch-only** may call one approved endpoint class and writes only a
   caller-selected non-symlink directory below `/tmp`. Reference pagination is
   capped at 20 requests and 25,000 records, remains on HTTPS
   `api.massive.com/v3/reference/tickers`, and retains the requested date.
   Grouped Daily makes one `adjusted=false` request for the exact session.
   Responses are canonicalized, hashed, ordered, date-checked, and wrapped in a
   frozen package manifest. Authorization material and credential-bearing URLs
   are rejected or stripped in memory and never persisted.
2. **Offline plan** accepts only a frozen package below `/tmp`. It runs the
   existing mapping, quality, schema, and persistence code against temporary
   artifacts. The immutable plan binds the operation/session, package custody,
   production root, expected inventory fingerprint, same-day identity
   fingerprint where applicable, publication order, every source/target path,
   row counts, content fingerprints, file sizes and SHA-256 values, expected
   inventory delta, and recovery boundary. The plan has an independent file
   SHA-256 and internal content fingerprint. Identity Plan 1.1 also normalizes
   the already-frozen provider result rows into direct-bound Source Custody
   1.1; it makes no additional provider request.
3. **Approved apply** is offline. It requires the plan path, the separately
   approved plan SHA-256, and the plan's expected current-state fingerprint.
   Under an exclusive lock it repeats package, plan, path, source, target, and
   current-state checks before creating a production directory. Socket access
   is prohibited through publication and formal reread. Existing completed or
   partial targets fail closed.
4. **Formal reread** uses the production Identity, normalized source-custody,
   or EOD reader. Schema, business keys, logical references, row counts,
   content fingerprints, and physical hashes must match the approved artifacts
   before success is reported.

## Identity logical boundary

New Plan 1.1 order is Instrument Master, Provider Instrument Identity,
Provider Ticker Resolver, normalized source observation, then the logical
snapshot directory. Each component directory is immutable and atomically
renamed. The logical manifest is last; before it exists, formal readers must
not treat the date as Identity-ready. Legacy Plan 1.0 remains readable only
under its original four-target/seven-file contract and does not acquire the
new source target by inference.

If a process stops after one or more complete components, the explicit
`--verify-then-complete` mode can continue the same approved plan. It first
verifies exact file sets, sizes, hashes, the package and plan, and a baseline
inventory fingerprint that excludes only those approved component targets.
It never overwrites a component. A partial, changed, extra, symlinked, or
unrelated target fails closed.

## EOD dependency

An EOD plan and apply require the completed logical Identity snapshot for the
same date and bind its logical fingerprint. A previous, future, or `latest`
resolver is not accepted. Grouped payload timestamps must resolve to the
requested session, canonical business keys are unique, and existing OHLCV,
duplicate isolation, identity coverage, and quality gates remain unchanged.

## CLI contract

Both administrator scripts expose the same stages:

```text
scripts/admin/ingest-massive-instrument-master.sh \
  --fetch-only --session-date YYYY-MM-DD --package /tmp/PACKAGE
scripts/admin/ingest-massive-instrument-master.sh \
  --plan --session-date YYYY-MM-DD --package /tmp/PACKAGE \
  --approval-plan /tmp/PLAN.json --data-root /data/trading-intelligence-platform
scripts/admin/ingest-massive-instrument-master.sh \
  --apply --session-date YYYY-MM-DD --approved-plan /tmp/PLAN.json \
  --approved-plan-sha256 SHA256 \
  --expected-current-state-fingerprint FINGERPRINT \
  --data-root /data/trading-intelligence-platform
```

Grouped Daily uses the corresponding
`scripts/admin/ingest-massive-grouped-daily.sh` forms. Identity recovery
replaces `--apply` with `--verify-then-complete` and otherwise requires the
same approval arguments. Unknown, mixed, or incomplete arguments exit with
code 2. Fetch-only is the only mode that loads a credential. Plan and apply
are fully offline.

An already completed legacy Identity date whose retained sanitized package is
still custody-valid may use the separate append-only repair port:

```text
scripts/admin/repair-massive-identity-source.sh \
  --plan --session-date YYYY-MM-DD --package /tmp/PACKAGE \
  --approval-plan /tmp/PLAN.json --data-root /data/trading-intelligence-platform
scripts/admin/repair-massive-identity-source.sh \
  --apply --session-date YYYY-MM-DD --approved-plan /tmp/PLAN.json \
  --approved-plan-sha256 SHA256 \
  --expected-current-state-fingerprint FINGERPRINT \
  --data-root /data/trading-intelligence-platform
```

The repair has no fetch mode. It requires the existing canonical Identity to
match a `current_v1` rebuild from the package, requires the source target to be
absent, and publishes only the two-file normalized partition. Exact completed
repair targets may be formally recovered with `--verify-then-complete`; no
target is overwritten.

The old direct Python ingestion functions deliberately raise and no scheduler
or other repository caller can retain the network-to-production path.

## Recovery and rollback

Completed canonical datasets are never deleted, overwritten, or rolled back.
An EOD stop after its atomic target rename is resolved by formal read-only
inspection; it is not replayed. An Identity stop before its logical marker may
use verify-then-complete with the original approval. Any other recovery needs
a new offline diagnosis and separate authorization.

## Security and non-goals

- no raw package under `/data`; only governed typed source-result observations
- no Authorization header, API key, credential length, or credential-bearing URL in artifacts or logs
- no retry, concurrent provider request, `latest` identity, ticker-only fallback, or target overwrite
- no change to canonical schemas, numeric semantics, fingerprints, quality thresholds, calendars, Universe activation, Dashboard, snapshot, scheduler, or deployment
