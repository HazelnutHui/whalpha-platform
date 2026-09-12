# Five-Year Inactive-Lifecycle Resolution Shadow Audit — 2026-09-12

## Boundary

Re-resolve the two already retained Massive `active=false` source anchors
against every canonical Instrument snapshot no later than each anchor, then
retain the completed result in owner-only Dell custody. This work made no
external request and wrote no canonical `/data`, analytics, Snapshot, bundle,
OCI, scheduler, or website state.

The shadow is identity reconciliation evidence only. Ticker and CIK never
created a positive match. Every incomplete or conflicting observation remains
quarantined, and every review candidate retains explicit limitations for last
tradable session, provider-date semantics, source availability, successor or
consideration, and terminal reason.

## Full-history results

### Anchor 2026-07-16

- canonical history: 1,216 sessions, 2021-09-10 through 2026-07-16;
- canonical unique instruments: 13,442;
- source/decision rows: 23,260 / 23,260;
- dispositions: 2,206 review candidates / 21,054 quarantined;
- identity resolution: 2,938 resolved / 1,179 ambiguous / 19,143 unresolved;
- manifest SHA-256:
  `f1d3008156bafb1eb10ae7a09f6d09741d25b21274b63c7993f70692f7effdac`;
- logical fingerprint:
  `c1e198951f73456a87dc1fb7c7045f25909c6e7278795e649b0783136c19585d`.

### Anchor 2026-09-03

- canonical history: 1,251 sessions, 2021-09-10 through 2026-09-03;
- canonical Instrument row occurrences: 10,639,241;
- canonical unique instruments: 13,651;
- source/decision rows: 23,469 / 23,469;
- dispositions: 2,278 review candidates / 21,191 quarantined;
- identity resolution: 3,023 resolved / 1,222 ambiguous / 19,224 unresolved;
- manifest SHA-256:
  `0c7ec6904d13d6550522eb9edcd0de840f2c14571e65d3285ad0cd749df36240`;
- logical fingerprint:
  `ff57952511418baf1563d0322e6058365323884a206817ac4b757ce7320e2129`.

Across anchors, stable-ID deduplication yields 2,283 distinct review-candidate
instruments: 2,201 shared, five present only in the earlier anchor, and 77
present only in the later anchor.

## Improvement over the retained short-history diagnostics

The earlier 2026-09-03 diagnostic used 303 sessions and produced 547 review
candidates, 22,922 quarantines, 1,245 resolved identities, 3,466 stable IDs
absent from canonical history, and 496 ticker conflicts. The full-history run
uses 1,251 sessions and produces 2,278 review candidates, 21,191 quarantines,
3,023 resolved identities, 1,688 stable IDs absent from history, and 249 ticker
conflicts.

This is a real mapping improvement caused by the enlarged point-in-time
Identity history. It is not proof that any candidate's provider delisting date
is its last tradable session or that a terminal return has been reconstructed.

## Persistent custody verification

The completed `/tmp` build was formally reread before retention. The persistent
target was verified absent, copied into a new owner-only staging directory, and
atomically renamed without overwrite. The retained build contains exactly six
mode-0400 files / 9,005,301 bytes beneath mode-0700 owner-owned directories.

Streaming comparison of the sorted relative-path/file-hash lists found no
difference. The list fingerprint is
`10dbda320316af93399f91e707bff615e6800237f99f5ba3d2a82aed9568f004`.
No symlink, partial directory, or staging residue exists.

The ADR 0214 persistent reader then independently reproduced both source row
counts, decision row counts, disposition counts, manifest hashes, and logical
fingerprints. Implementation revision is
`0699d4f6e6febe05c96ab715cfd978c03d86843a`; the focused shadow/CLI suite
passed 12 tests. The complete API suite passed 2,540 tests in 268.29 seconds;
its two warnings are unchanged dependency deprecations.

## Authority

The persistent result is a durable review queue. It is not canonical
Lifecycle or Historical Coverage and does not admit any security/session to a
research dataset. Required corroboration of terminal outcomes, corporate
actions and adjustments, Membership, source availability, and final transitive
coverage remains separate and fail-closed.
