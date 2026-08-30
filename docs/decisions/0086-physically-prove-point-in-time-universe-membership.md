# ADR 0086: Physically Prove Point-in-Time Universe Membership

## Status

Accepted

## Date

2026-08-30

## Context

Historical research cannot use the current activated Universe as if it had
existed on prior sessions. The repository already had a typed three-state
membership row and generic Parquet mechanics, but its manifest did not prove
that every Universe evaluated the same complete stable-ID base. There was also
no formal bridge from an existing reviewed point-in-time calculation to this
historical family.

The only completed reviewed full-base source currently retained is the
2026-08-19 superseding security-form revision. It contains one metric row per
CS/ADRC union instrument and complete Primary/Secondary decisions. It is valid
for a bounded reconstruction pilot, but it does not justify inventing daily
membership for any other session.

## Decision

Advance the Universe Membership partition manifest to `1.1`. One immutable
partition now binds its methodology/session, reconstruction origin, exact
stable-ID evaluated-base count and fingerprint, sorted source fingerprints,
uniform cutoff/evaluation clocks, and included/excluded/quarantined totals for
each Universe. Every Universe must contain one decision for every base ID;
omission fails before publication.

Add a provider-neutral reconstruction service and a reviewed-full-base adapter.
The adapter maps the completed 2026-08-19 Primary/Secondary decision ledgers to
the public Universe IDs and labels every row
`reconstructed_point_in_time`. Missing bars, insufficient history, invalid
input, outlier quarantine, and reviewed quarantine remain quarantined rather
than being converted to exclusions. Future-dated membership evidence is
rejected. If the retained source cutoff is later than the session, all
otherwise valid rows carry a warning and explicit late-cutoff reason; the
partition remains mechanics-only for chronological evaluation.

The operational pilot CLI requires explicit source, output, session, and
evaluation time. Its output must be below `/tmp`, disjoint from the source
root, and is formally reread. It has no provider, credential, canonical
`/data`, active-pointer, publication, deployment, or scheduler authority.

## Consequences

- The real 2026-08-19 pilot proves 4,565 evaluated stable IDs for each of two
  Universes and 9,130 explicit decisions.
- Reconstructed membership is now physically auditable without claiming it was
  the Universe actually operated on that date.
- Canonical daily history remains absent for all other sessions; the current
  Activation is still forbidden as a backward-fill source.
- Corporate actions, lifecycle/terminal evidence, adjustment reconciliation,
  and the 252-session minimum remain blockers for performance evaluation.

## Alternatives Considered

### Project the current Activation backward

Rejected because it creates survivorship and future-information leakage.

### Persist only included members

Rejected because omission cannot distinguish an evaluated exclusion from
missing or ambiguous evidence.

### Treat missing critical inputs as exclusions

Rejected because it turns data-quality failure into a false policy decision.
