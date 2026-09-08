# Opportunity Candidate Segmented Chain Head V1

## Purpose and authority

`opportunity-candidate-segmented-chain-head/1.0` is a small immutable identity
checkpoint for a validated Candidate segmented lineage. It is Dell-local and
non-authoritative. It is not a Candidate audit, publication, Snapshot source,
canonical current pointer, research result, or Production input.

## Lineage identity

`opportunity-candidate-segmented-lineage-identity/1.0` starts from the exact
base shadow manifest, calculation-contract/Universe identity, session count,
and chain tip. Every append advances it with the prior lineage fingerprint and
the exact append manifest, session, source-audit, and chain-tip identities.
Paths and timestamps are excluded.

## Head content

The single canonical manifest binds:

- the base shadow contract and physical/logical manifest identity;
- base session count, source contract, Universe, and chain tip;
- the exact current parent manifest embedded as canonical JSON;
- current parent manifest SHA-256, as-of, session/append counts, source audit,
  Universe, and final chain tip;
- the cumulative lineage fingerprint; and
- zero external-request, Production-write, and publication authority.

The package is an owner-only direct child of `/tmp`, with directory mode `0700`
and one `0400` manifest. Exact file set, ownership, modes, canonical encoding,
logical fingerprint, and physical SHA-256 are mandatory. Completed staging may
be verified and atomically delivered; partial or ambiguous evidence fails
closed and is retained.

## Cold and incremental construction

Cold construction validates the base and every ordered append. Incremental
construction requires the exact expected prior head logical fingerprint and
validates only that small head plus the new append against its embedded parent.
Both methods must generate the same head bytes for the same lineage.

A fast read always requires the expected head logical fingerprint from an
independent trusted input. Reading the fingerprint from the same untrusted head
and passing it back is not a valid trust boundary.

## Current limits

ADR 0161 now defines and repository-tests a no-write immutable publication and
current-pointer plan with bounded-family CAS, rollback reference, recovery
states, and retain-all immutable-head policy. ADR 0162 proves the exact-plan
Apply/recovery mechanics only beneath a disconnected `/tmp` simulation root
and refuses the Production root by code. No `/data` canonical pointer has been
created. The CLI, daily executor, coordinator, scheduler, MI, Snapshot, and
Production do not consume the head. Periodic full-lineage verification remains
required.

## Real Dell evidence

For the real 2026-09-03 base and 2026-09-04 append, cold construction took
39.82 seconds, while base-head incremental advancement took 24.78 seconds. The
resulting head files were byte-identical. The final head is 4,962 bytes with
logical fingerprint
`653f6f3a47066094a32fbf5481e563eebb4a2c290344be7d5c6d20264c0400bc`,
physical SHA-256
`47c8636305f3f89f9fa03855e705b9063763313603b95ee7dc404a720d8e4ee0`,
and lineage fingerprint
`33971a2e205afec07aeadfbdcf4d00161bb555dfbb8dc2557f1654c4d3ca55a2`.
Expected-fingerprint reading took 1.08 seconds. The same head reduced isolated
real append composition from 36.70 to 21.18 seconds while preserving both
append files byte-for-byte.
