# Opportunity Candidate Segmented Chain-Head Publication V1

## Purpose and authority

This boundary plans, but does not execute, canonical publication of one exact
segmented Candidate chain head. It introduces:

- `opportunity-candidate-segmented-chain-head-publication-plan/1.0`;
- `opportunity-candidate-segmented-chain-head-current-pointer/1.0`;
- `opportunity-candidate-segmented-chain-head-current-state/1.0`; and
- `opportunity-candidate-segmented-chain-head-family-inventory/1.0`.

The plan is review evidence only. It has zero canonical/Production writes and
does not authorize Apply, rollback, executor, scheduler, downstream Candidate
consumption, Snapshot publication, or deployment.

## Canonical layout

The proposed family is bounded below:

```text
analytics/opportunity-candidate/segmented-chain-head/
  current.json
  releases/<chain-head-logical-fingerprint>/
    candidate-segmented-chain-head.json
```

Release directories are immutable and content addressed by the chain-head
logical fingerprint. `current.json` is the only mutable selection boundary.
The immutable release must be published first and the pointer last.

## Release reference

Each active or rollback reference binds:

- normalized release and manifest paths;
- chain-head contract, physical SHA-256, and logical fingerprint;
- lineage fingerprint, session and append counts, and as-of session;
- calculation/source-audit, Universe, lineage-tip-manifest, and final chain
  identities.

The referenced manifest is reread canonically and must reproduce every field.

## Current pointer and CAS

The pointer contains one active reference, an optional rollback reference, the
prior pointer-state fingerprint, and its own logical fingerprint. A bootstrap
has no rollback. A successor moves the prior active reference to rollback.

Planning fingerprints only this bounded family, including directory modes and
every immutable file hash. It also binds a separate pointer-state fingerprint
and pointer physical SHA. Any target appearance, unexpected file, symlink,
custody change, pointer change, release-byte change, or family-inventory drift
invalidates the plan before Apply.

A successor must advance exactly one append and one session over the current
active head. Its base identity must remain exact; its embedded append parent,
prior chain tip, lineage-tip manifest, and incrementally recomputed lineage
fingerprint must all bind the current active reference.

## Recovery, rollback, and retention policy

- Neither target present means Apply did not start.
- The exact immutable release alone may only become a pointer-completion
  candidate after a fresh CAS check.
- The exact planned pointer selecting the exact release means completion.
- Every other partial, conflicting, or ambiguous state blocks for diagnosis.
- Rollback is never automatic and requires a separate exact pointer CAS.
- All tiny immutable head releases are retained; automatic pruning is not
  authorized. Only the pointer keeps one immediate rollback reference.

The plan itself grants no Apply authority. ADR 0162 implements these mechanics
only for a disconnected `/tmp` simulation; it explicitly refuses the
Production root and does not authorize canonical publication.

## Custody

The source remains an expected-fingerprint `/tmp` chain-head package. The
review plan is one canonical owner-read-only file directly beneath `/tmp`.
The plan reader rehashes and semantically rereads the source, current pointer,
active/rollback releases, bounded family inventory, target absence, successor
relationship, planned pointer bytes, and the complete plan fingerprint.

## Real disconnected evidence

The real 2026-09-04 11-session head produced a bootstrap plan against a new
owner-only simulated `/tmp` root. The plan is 0-request, 0-canonical-write and
`apply_authorized=false`; it proposes one 4,962-byte immutable release plus a
1,712-byte pointer. Plan SHA-256 is
`d4785ff7526f65c4b91bc96d2e217f6b11ec21d4c6b86cbf99de4acb27f536c2`
and logical fingerprint is
`fc155109b92a5b5e00f54ae9e2121f0330639866af3c26753534488d94c9797c`.
No `/data` or Production state was read or changed.
