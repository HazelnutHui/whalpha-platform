# Dashboard Snapshot V2

## Status

Implemented and active. Production Snapshot
`2026-08-24T045652Z-aee1a6ab0f67` uses Snapshot 1.5 / Dashboard 2.2 and binds
Market Intelligence `2026-08-24T043223Z-aee1a6ab0f67`. It is the exact
user-approved `stale_review` for actual 2026-08-24 versus expected 2026-08-25,
lag one. Snapshot 1.4 / Dashboard 2.1 and the 1.3 compatibility release remain
historical/rollback contracts, not the active state.

## Contracts

Snapshot contract 1.4 carries Dashboard contract 2.1. It retains the four private JSON payloads from 1.3 and adds 20 formal Funnel records: ten ordered stages for each active public Universe. Every record binds Universe ID, stage index/stable ID, display label, input/excluded/remaining counts, source revision, source session, and source logical fingerprint.

Each stage satisfies `input_count - excluded_count = remaining_count`; the next stage input equals the preceding remaining count. The manifest requires exactly 20 records and one source fingerprint. Contract 1.3 remains readable and renders an unavailable state rather than reconstructing a pseudo-funnel.

## Versioned publication

```text
market-data/snapshots/private-dashboard-v2/
  revision=universe-funnel-v2/
    release_id=<frozen-release-id>/

market-data/snapshots/private-dashboard-active/active.json
```

When the pointer is absent, the formal reader resolves the reviewed legacy release. A malformed, dangling, escaped, symlinked, or hash-inconsistent pointer fails closed; it never falls back.

The default CLI is dry-run. A writable operation requires a canonical approval plan, its separately approved SHA-256, and the expected current-state fingerprint. The plan freezes the release time/ID, Activation pointer/logical fingerprints, EOD freshness, all snapshot file hashes, aggregate hash, exact target/pointer paths, planned pointer hash/fingerprint, and rollback reference. Apply revalidates the plan, candidate, Activation source, current state, and freshness inside the exclusive lock before creating production paths.

Publication writes and fsyncs staged files and newly created directory entries, formally rereads staging, atomically renames the completed target, rereads it, then atomically writes/fsyncs the pointer. A completed target left before pointer switch is recoverable only with the same approved plan and `--verify-then-link`; it is never overwritten.

Rollback is a separate default-dry-run CLI. Apply requires the exact active pointer fingerprint approved from rollback dry-run and rechecks it under lock. Old releases remain immutable.

## Freshness gate

Approval-plan creation requires `fresh`, lag zero, and exact expected/actual session equality. Apply and verify-then-link recompute the formal XNYS gate under lock. A stale candidate may be built under `/tmp` for review but cannot produce a production approval plan or be applied.

## Consumers

- API and snapshot export obtain memberships/catalog order from the active Activation resolver.
- Snapshot-mode React reads only manifest-listed fixed resources and directly renders the selected Universe's formal Funnel.
- The snapshot active reader resolves a versioned target or the no-pointer compatibility release.
- OCI bundle construction requires an explicitly named immutable snapshot release; it does not select a latest directory or pointer implicitly.

No production bundle or OCI deployment belongs to this boundary.

## Contract 1.5 Market Intelligence extension

Snapshot 1.5 pairs Dashboard contract 2.2 with the 1.4 Activation/Funnel data
and adds `market-regime-overviews.json`. The language-neutral envelope contains
two stable-order API records, 30 ETFs, and all 16 pairs. Its manifest freezes an
explicit Market Intelligence publication ID, payload SHA, publication logical
fingerprint, and nested analytics logical fingerprint.

The builder accepts only a formally readable active Market Intelligence release
whose session, Activation, catalog, counts, and memberships match the Snapshot.
Contract 1.4 stays readable unchanged and does not claim analytics exist.
Snapshot 1.5 never reads `/tmp`, recomputes analytics, or mixes the old
1,641/1,747 fallback data with the new page.

Snapshot 1.5 may carry the exact `production-review-deployment/1.0`
authorization already bound by its active Market Intelligence source. In that
case its overview, analytics envelope, manifest, and plan all report
`stale_review`, approved as-of `2026-08-24`, expected `2026-08-25`, and lag
one. The normal lag-zero gate is unchanged; review plan/apply requires the
same explicit acknowledgement and rejects changed freshness under lock.
