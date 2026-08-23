# Dashboard Snapshot V2

## Status

Implemented and verified offline. No production Snapshot V2 has been published. Production remains release `2026-08-19T083341Z-7ed7fdc21686` on contract 1.3. Canonical EOD is stale at 2026-08-19 versus XNYS expected latest completed session 2026-08-21, so publication fails closed.

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
