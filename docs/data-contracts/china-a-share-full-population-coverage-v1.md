# China A-share Full-Population Coverage Diagnostic V1

## Purpose

Turn the completed 109-partition SSE/SZSE source expansion into an explicit
13-family admission map without overstating acquisition as backtest readiness.

## Bound scope

- frozen acquisition targets: 5,409;
- stable resolved occurrences: 5,296;
- quarantined source-keyed targets: 113;
- normalized states: 5,997,301;
- unadjusted bars: 5,987,288;
- provider adjustment observations: 62,272;
- scope excludes a qualified BSE daily-price route.

Every price-limit regime remains unknown and every historical
`source_available_at` remains null. Provider adjustment movement is a candidate
event index, not proof of corporate-action terms or return authorization.

## Thirteen families

The ordered report separately assesses identity, calendar, raw EOD,
price-limit state, suspension, risk warning, adjustment factors, corporate
actions, lifecycle, daily Universe, trading rules, fees, and overall Historical
Coverage. Each family is classified as source-complete, provisional
reconstruction only, or blocked by missing evidence.

## Authority

Historical Coverage, adjusted returns, backtesting, Factor Discovery,
canonical Apply, Product publication, and deployment remain closed. See
[ADR 0297](../decisions/0297-freeze-a-share-full-population-offline-coverage-diagnostic.md).

## Streaming diagnostic implementation

The next implementation binds the exact population, source plan/completion,
normalized run, and ordered source/normalized partition manifest identities in
one deterministic plan. Each exact-reader partition is reduced to bounded
state, warning, price-limit, source-time, and adjustment-transition counters;
only ordered aggregate identities are retained across partitions. The verifier
scans state Parquet in 65,536-row batches and does not materialize the full
5,997,301-state table or a full daily-Universe cross-product.

These contracts authorize no return read, adjusted return, backtest, canonical
Apply, or Product publication. The aggregate package, dynamic 13-family gaps,
and independent exact replay remain separate gates.

Owner-only plan and aggregate custody is implemented as a closed file set with
0700 directories, 0400 files, canonical JSON, physical hashes and sizes,
atomic publication, exact reread, and symlink/path/permission rejection. This
makes a real 109-partition diagnostic package safe to materialize; it does not
itself claim that such a package has run.
