# Candidate Visual Context Formal Audit — 2026-08-30

## Scope

The repository-only Candidate Visual Context 1.0 calculation was run on Dell
against the existing formally completed 2026-08-28 Candidate audit, Entry
Geometry audit, and content-addressed panel cache. The socket-guarded process
wrote only a new direct child of `/tmp`.

## Exact sources and result

- Candidate audit: `/tmp/whalpha-candidate-phase5c-20260828`
- Entry Geometry audit: `/tmp/whalpha-candidate-entry-20260828`
- Panel-cache key:
  `20c73271c49f870fd2d30372a00d65b1882669418d0d684278e9fba578e5c122`
- Output: `/tmp/whalpha-candidate-visual-context-20260828`
- Audit logical fingerprint:
  `3b8ddbf3cc7d35cf0ea2b8f257939d23cec6f1d463e0d16efce9b5fb1f23961f`
- Primary batch fingerprint:
  `eb810e7e66e55bfd32beaaca918f8daa669db5fb67c567b197c63e589d5151ec`
- Secondary batch fingerprint:
  `3018b39a577d8163013b5f0486297fb5a612d7bf47d6275502e6268d4709ac7c`

All 3,541 current Candidate records have a complete exact 20-session close
path: 1,714 Primary and 1,827 Secondary. Observed Candidate-state age is
available for 1,634 / 1,714 Primary and 1,748 / 1,827 Secondary records. The 80
/ 79 unavailable results are current unavailable or stale Candidate states;
they remain empty rather than receiving inferred ages.

Observed-age counts across both overlapping Universes are 372 at one session,
416 at two, 230 at three, 595 at four, 157 at five, and 1,612 at six. All 1,612
six-session values are left-censored and therefore mean at least six retained
Candidate sessions, not a known true start.

Both independent Oracle reports have zero mismatch and exact input-permutation
equivalence. The Oracle does not import the production calculator. Formal
reread passed. External request count and Production write count are both zero.

## Timing and size

- Candidate current batches plus cumulative state reread: 22.72 seconds
- Entry Geometry reread: 0.82 seconds
- Panel-cache reread: 9.25 seconds
- calculation plus independent validation: 4.00 seconds
- atomic audit write and formal reread: 1.97 seconds
- total: 38.81 seconds
- batch artifact: 9,177,600 bytes

The dominant cost is reading the existing large Candidate score/state JSON,
not the visual calculation. Future daily integration should create and retain a
small dedicated visual product once per session and add it to existing lazy
detail shards; publication and browsers must not reconstruct the parent audit.
The first equivalent 41.13-second pilot was moved to the workstation trash and
replaced at the same authoritative path by the optimized, formally reread audit;
business batch, Oracle, and audit logical fingerprints are unchanged.

## Boundary

No `/data`, active pointer, Market Intelligence, Snapshot, bundle, OCI,
scheduler, credential, or Production state changed. This audit provides source
evidence for a future product contract only and is not deployment authority.
