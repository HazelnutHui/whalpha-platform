# Dashboard Snapshot V2

## Status

Implemented. Active Production Snapshot
`2026-08-28T141747Z-83f9b629279c` uses Snapshot 1.11 / Dashboard 2.8 and binds
Market Intelligence `2026-08-28T135850Z-f483d6999a3e`. It was published under
ordinary lag-zero freshness. It includes the split Candidate consumer, lazy
strategy-channel and Visual Context products, and the lazy Sector Rotation
resource. Earlier releases remain immutable, readable historical/rollback
contracts, not the active state.

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

All later supported Snapshot pairs may also carry the separately approved
`production-review-deployment/1.1` binding only for actual/analysis
`2026-08-26`, expected `2026-08-27`, lag one, and its exact acknowledgement.
The browser, formal reader, plan, and apply gate validate the same binding;
version 1.0 remains rollback-readable.

## Contract 1.6 Candidate extension

The active Snapshot 1.6 / Dashboard 2.3 is an additive
consumer of Market Intelligence 1.1. It retains the 1.5 files and adds exactly
`opportunity-candidates.json`, whose bounded language-neutral payload is
described in the [Candidate publication contract](opportunity-candidate-publication-v1.md).
The manifest and approval plan freeze the Candidate analytics, audit, scoring-
parameter, state-parameter, displayed-count, Market Intelligence, and file-hash
bindings. Snapshot 1.5 / Dashboard 2.2 remains formally readable and cannot
silently acquire Candidate data.

The OCI builder accepts only the exact 1.5/2.2 or 1.6/2.3 pair. For 1.6 it
requires the Candidate file and cross-checks its Market Intelligence and audit
lineage; deployment postflight gives a temporary guest Session the same
Candidate resource as a credential Session, then logs out and reconfirms the
unauthenticated boundary.

## Contract 1.7 entry-location extension

Snapshot 1.7 pairs Dashboard 2.4 with Market Intelligence 1.2 and Candidate
publication 1.1. It retains the exact file set introduced by Snapshot 1.6, but
upgrades the Candidate envelope to `opportunity-candidate-snapshot/1.1` and
adds manifest/plan bindings for the entry contract, audit logical fingerprint,
entry parameter fingerprint, and lane-consumer parameter fingerprint.

The reader validates all nested bindings and fails closed on a mixed 1.0/1.1
Candidate envelope, changed lane IDs/counts/order, or missing entry geometry.
The OCI builder and deployment postflight accept and validate the 1.7/2.4 pair
while retaining old 1.5/2.2 and 1.6/2.3 rollback compatibility. Freshness,
approval, guest-equality, and no-demo boundaries are unchanged.

## Contract 1.8 split Candidate delivery

Snapshot 1.8 pairs Dashboard 2.5 with the same Market Intelligence 1.2 and
Candidate publication 1.1 used by Snapshot 1.7. It replaces the monolithic
Candidate snapshot file with one summary file and deterministic stable-ID
detail shards. The manifest freezes the summary contract/fingerprint, detail
contract, ordered filenames, and SHA-256 of every file.

Approval plan 2.3 carries those bindings through atomic publication. Formal
validation reads every shard and losslessly reconstructs the full Candidate
publication before accepting a release. The browser loads the summary first
and one declared shard per opened security. Older Snapshot contracts remain
readable and do not silently acquire split files.

## Contract 1.9 lazy strategy-channel delivery

Snapshot 1.9 pairs Dashboard 2.6 with the unchanged Snapshot 1.8 Candidate
summary and detail shards and adds exactly `candidate-strategy-channels.json`.
The manifest freezes its contract, SHA-256, product/audit/parameter logical
fingerprints, and exact Candidate/Entry Geometry lineage. Formal validation
rereads the typed product and rejects mixed contracts, changed sources,
nonzero Oracle mismatch, reordered Universes/channels, inconsistent counts or
ranks, and changed guest/credential capability policy.

The browser requests this file only when Strategy Channels is selected. It
renders no synthetic fallback and performs no scoring. Repository build/read
and bilingual browser support are implemented. ADR 0058 additionally implements
Approval Plan 2.4 and OCI bundle/postflight validation while preserving every
older plan and contract. The historical 2026-08-28 analysis release passed Plan
2.4, Apply, bundle validation, OCI deployment, and guest postflight. Snapshot
1.8 and older releases remain readable unchanged.

## Contract 1.10 lazy visual-context delivery

Repository Snapshot 1.10 pairs Dashboard 2.7 with the unchanged Candidate
summary and strategy product. It upgrades only the 32 detail shards to
`opportunity-candidate-detail-shard/1.1`, placing each exact source-bound Visual
Context record beside its matching Candidate row. The summary remains 1.0 and
contains no historical arrays.

The manifest and Approval Plan 2.5 freeze the Visual Context contract, audit-
manifest SHA-256, audit logical fingerprint, two batch fingerprints, detail
contract, filenames, and every file hash. Formal reread requires exact stable-
ID coverage and per-row Candidate/Entry Geometry lineage. OCI bundle and guest
postflight validators understand 1.10/2.7. Snapshot 1.11 / Dashboard 2.8 adds
the separately bound Sector Rotation resource and is the active Production
pair; publication and deployment remain separately authorized operations.
