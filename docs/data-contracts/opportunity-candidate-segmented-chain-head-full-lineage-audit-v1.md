# Opportunity Candidate Segmented Chain-Head Full-Lineage Audit V1

## Purpose and authority

`opportunity-candidate-segmented-chain-head-full-lineage-audit/1.0` proves that
one externally expected current chain head is exactly reproducible from its
retained base shadow and complete ordered append lineage.

It is a deterministic, zero-write, network-prohibited, `/tmp`-only audit. It is
not a Candidate calculation, publication, current-pointer mutation, rollback,
repair, cutover approval, scheduler action, or Production input.

## Inputs

The caller supplies:

- owner-controlled simulated current root under `/tmp`;
- exact base-shadow path;
- complete explicitly ordered append paths;
- expected bounded-family inventory fingerprint;
- expected pointer-state fingerprint;
- expected active chain-head logical fingerprint; and
- expected active chain-head manifest SHA-256.

All four expected fingerprints must be independently known. Selecting them from
the same untrusted current state and passing them back is not a trust boundary.
The exact Production root is refused before filesystem inspection.

## Validation sequence

1. Formally read the complete bounded family and current pointer.
2. Require the expected inventory, pointer, active logical, and active physical
   identities.
3. Formally read the base and every append in the supplied order.
4. Reconstruct the chain-head manifest deterministically in memory.
5. Require exact parent dataclass identity, manifest mapping, canonical logical
   fingerprint, and manifest SHA-256 equality with the active release.
6. Formally reread the family and pointer and require an identical state under
   the same expected bindings.

The before/after read prevents a concurrent current transition from being
silently combined with a different cold lineage. The family fingerprint also
binds all retained immutable releases, paths, modes, and bytes.

## Success result

A result exists only for an exact match and records:

- contract, status, tier, and validation scope;
- current family/pointer and active physical/logical identities;
- independently reconstructed cold physical/logical identities;
- base, source-contract, source-audit, lineage, session, append, and Universe
  identities;
- two current-state reads and one complete-lineage read;
- exact manifest/parent booleans and zero mismatch count;
- a deterministic logical fingerprint over the complete result; and
- zero filesystem/canonical/Production writes and external requests, plus
  false publication, cutover, and code-change-completion authority.

There is no degraded success. A malformed expectation, missing or reordered
append, source/Universe drift, custody failure, corrupt byte, unexpected family
entry, current mismatch, or mid-audit state change fails closed.

## Validation-level policy

| Level | Required evidence |
| --- | --- |
| Daily | Expected-current/head fast read, exact successor, pointer CAS, and postflight; no full-lineage claim. |
| Periodic | This audit at least every five accepted append sessions or seven calendar days, and after recovery before another head. |
| Code change | This audit plus V1 `code_change` full semantic reconstruction, independent Oracle, and affected contract tests. |

The result is deliberately fixed to `validation_tier=periodic` and
`code_change_validation_complete=false`. A caller cannot relabel it as a
complete code-change gate without the separate V1/Oracle evidence.

## Failure handling

Failure freezes the optional segmented advance. V1 remains authoritative.
Evidence is retained for diagnosis; automatic cleanup, repair, rollback,
publication, and retry are prohibited. A later exact audit is required before
resuming the segmented path.
