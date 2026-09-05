# ADR 0143: Separate Identity Observation and Replay Time

- Status: Accepted
- Date: 2026-09-05

## Context

ADR 0141 reacquired 24 historical Identity reference packages on 2026-09-04.
The first dual-profile census classified all 24 as mismatches because the
equivalence builder used each newly acquired package's `fetched_at` as the
canonical Identity `ingested_at`. Those clocks happen to agree for an original
same-run package, but they are different facts during later reacquisition.

An anonymous row-level comparison for 2026-07-17 proved that the accepted
Instrument Master, Provider Identity, and Resolver families share one earlier
row-level ingestion timestamp. Rebuilding with that accepted timestamp and the
pre-ETV profile reproduced all three families exactly. A full 303-session
dual-profile rerun then proved 301 exact sessions. The reacquired 2026-08-13
and 2026-08-19 packages remained non-equivalent under both profiles because
the provider result sets and stable-identity fields had changed; their
differences cannot be explained by a replay timestamp or the governed ETV
classification transition.

The 1.0 profile map could represent only exact bindings or physically absent
packages. Treating a discovered, custody-valid but non-equivalent package as
physically missing would lose material evidence; binding it would weaken the
exactness contract.

## Decision

Keep source observation time and accepted Identity replay time separate:

- `package_fetched_at` / `source_observed_at` remains the actual Dell package
  observation time and is never backdated;
- exact Identity replay reads `ingested_at` from each accepted canonical
  family, requires one non-null value per family and the same value across all
  three families, then uses only that value to reproduce canonical provenance;
- all canonical Instrument, Identity, and Resolver fingerprints remain exact
  SHA-256 gates. The timestamp rule does not ignore, normalize, or tolerate any
  provider-content difference.

Advance the profile map to
`historical-identity-rebuild-profile-map/1.1`. It adds ordered
`unbound_identity_mismatch_session_dates` for custody-valid packages that are
non-equivalent under every governed profile. Such packages stay inside the
complete package-inventory fingerprint but receive no profile binding.
Profile selection for an unbound date continues to fail closed.

The normalized source runner must discover exactly the complete bound plus
declared-unbound inventory. It may normalize only bound sessions and must
verify that every unbound date occurs exactly once. Existing 1.0 profile maps
remain readable and retain their original logical-fingerprint calculation.

## Consequences

- Twenty-two reacquired sessions are exactly reconstructable under
  `pre_etv_governance_v1` without falsifying when their source was observed.
- The 2026-08-13 and 2026-08-19 packages remain visible evidence of later
  provider revision but cannot enter canonical historical source custody under
  the exact-reconstruction contract.
- A profile map can now truthfully distinguish physical absence from a
  discovered non-equivalent source while keeping both states unbound.
- Existing 279 canonical source partitions and 1.0 maps remain valid.
- This decision grants no Historical Coverage, point-in-time availability,
  membership, research, performance, publication, deployment, or scheduler
  authority.

## Alternatives Considered

### Continue rebuilding with the new package fetch time

Rejected because package observation time is not the original canonical
Identity build time and creates false mismatches in every fingerprint family.

### Rewrite the reacquired package time to the historical value

Rejected because it would misstate source custody. The new observation time is
preserved while canonical replay provenance is read independently.

### Ignore changed fields or accept business-key similarity

Rejected because the two revised dates contain record-count and stable-
identity changes. They are not exact sources for the accepted snapshots.

### Omit the two revised packages and call them physically missing

Rejected because the packages exist and carry useful revision evidence. They
must be reported as discovered but non-equivalent.
