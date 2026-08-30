# ADR 0089: Publish Candidate Visual Context in Lazy Detail Shards

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0088 produced source-bound 20-session close paths and observed Candidate-
state age, but left them outside the product boundary. Copying the full audit
into the first-load Candidate summary would add several megabytes to every
visit. Fetching a separate visual file after opening a Candidate would add a
second request and weaken the existing summary/detail identity binding.

## Decision

Add `opportunity-candidate-detail-shard/1.1` and publish Visual Context records
beside the matching full Candidate rows in the existing 32 stable-ID shards.
The summary contract remains unchanged. The builder formally rereads the
Visual Context audit once, requires exact session, Universe, Candidate-batch,
and Entry-Geometry-batch lineage, and requires one visual record for every
published detail row. Each shard requires ordered stable IDs and exact per-row
Candidate-score and Entry-Geometry fingerprints.

Snapshot 1.10 pairs Dashboard 2.7 with Approval Plan 2.5. Its manifest and plan
freeze the Visual Context contract, audit-manifest SHA-256, audit logical
fingerprint, batch fingerprints, detail contract, filenames, and every file
hash. Snapshot 1.9 / Dashboard 2.6 remains readable and unchanged.

The browser downloads no visual history with the summary. Opening one Candidate
loads its already-required detail shard, validates Snapshot/audit/row lineage,
and draws the exact 20-session close path. Observed state age displays `N` or
`>=N` when left-censored. The browser does not reconstruct prices, scores,
states, support, or age.

## Consequences

- First-load Candidate bytes remain unchanged; visual bytes are paid only by
  an opened stable-ID shard and require no additional request.
- A detail shard is larger because it contains exact paths for every Candidate
  sharing that prefix.
- The path remains canonical close history, not total return, intraday
  execution, causality, forecast, or option return. Reference support remains
  descriptive and is not a stop.
- Direct Snapshot Plan/Apply and OCI bundle validation understand 1.10/2.7.
  Daily unattended automation still targets the deployed 1.9/2.6 chain until
  Visual Context generation is explicitly added and separately exercised.
- This ADR does not authorize publication or deployment.

## Alternatives Considered

### Put all paths in the summary

Rejected because every Candidate visit would pay the full history cost.

### Fetch a second visual resource per opened Candidate

Rejected because it adds a round trip and permits Candidate and visual details
to drift independently.

### Recompute paths or state age in the browser

Rejected because the browser does not possess the governed source ledgers and
must remain a strict renderer.
