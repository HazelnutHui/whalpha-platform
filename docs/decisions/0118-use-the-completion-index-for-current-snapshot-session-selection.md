# ADR 0118: Use the completion index for current Snapshot session selection

## Status

Accepted.

## Date

2026-09-01.

## Context

Dashboard Snapshot planning needs the latest two completed EOD session dates
before it fully reads those two partitions. The Overview service and the CLI
freshness gate both used `list_sessions()`. That reader reconstructs and
fingerprints every completed Parquet partition, so the 32-session history was
fully reread twice merely to select two dates.

The canonical repository already has `list_session_index()`. It validates the
bounded partition names, completion manifests, schema/session/completion
fields, symlink boundary, and required manifest/Parquet file presence without
reconstructing historical rows.

## Decision

Use `list_session_index()` when the canonical repository exposes it to select
the latest two dates and evaluate current freshness. Keep the existing
descriptor-based fallback for provider-neutral repositories that do not expose
the optimized index.

After selection, continue to fully read and validate the current and previous
Parquet partitions used by the Dashboard. Do not use the completion index as
a substitute for content validation of an input partition. Activation, Market
Intelligence, Snapshot staging/completion, checksums, and approval-plan gates
remain unchanged.

## Consequences

- On identical 2026-08-31 inputs, deployed source `44b052419be8` took 251.79
  seconds and the indexed path took 121.43 seconds: 130.36 seconds or about
  51.8% less wall time.
- Candidate summary/detail shards, strategy channels, Market Regime, Market
  Summary, movers, liquidity map, and Sector Rotation were byte-identical.
  Market Overview was identical after excluding the deliberately different
  generation and freshness-check timestamps.
- The current/previous EOD inputs still undergo complete Parquet schema, row,
  fingerprint, identity, resolver, and business-key validation.
- A same-process Activation reuse prototype improved 121.43 seconds to only
  119.65 seconds. It was rejected and removed because the 1.5% saving did not
  justify coupling two formal readers.
- No formula, parameter, Universe, contract, `/data`, pointer, scheduler,
  publication, bundle, OCI, or frontend change.

