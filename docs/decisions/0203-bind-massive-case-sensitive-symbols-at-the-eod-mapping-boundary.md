# ADR 0203: Bind Massive case-sensitive symbols at the EOD mapping boundary

- Status: Accepted
- Date: 2026-09-10

## Context

The five-year continuation stopped while constructing 2022-10-07 EOD. The
Grouped Daily package has 10,914 rows. Massive symbols are case-sensitive;
lower-case characters can distinguish a preferred share or another security
form from the upper-case common-stock or fund symbol. The V1 canonical ticker
Resolver upper-cases provider tickers, so grouping Grouped Daily rows by that
normalized value falsely merged six exact provider-symbol pairs and produced
12 conflicting rows above the 0.1% duplicate gate.

The provider's published symbol guidance explicitly states that symbols are
case-sensitive and documents lower-case `p` for preferred shares:
<https://massive.com/knowledge-base/article/why-are-ticker-symbols-with-dashes-not-showing-in-polygons-system>.

Raising the duplicate gate would hide a semantic error. Sending every
mixed-case row to quarantine would also be too broad: retained Identity source
custody contains mixed-case eligible common-stock and ADR records as well as
preferred shares, rights, structured products, and other exclusions.

A direct bounded census of retained Grouped Daily packages found this is not a
single-session anomaly. Across 676 already-published sessions whose source
packages were available, at least 1,862 resolved upper-case securities are
absent because they collided with a distinct mixed-case provider symbol. A
direct latest-session check also found affected resolved bars. This is a
confirmed lower bound, not a complete historical repair census.

## Decision

Massive Grouped Daily mapping now binds the exact same-session Identity source
custody before classifying provider symbols:

- group and deduplicate bars by the exact trimmed provider symbol;
- derive the exact-symbol category from the retained source security type and
  the existing stable-identity policy;
- resolve an exact symbol only when the computed `instrument_id` already exists
  in the same canonical Identity snapshot and the V1 normalized Resolver
  points to that same ID;
- retain excluded, unresolved, ambiguous, malformed, and missing evidence as
  their existing fail-closed categories;
- record the exact Identity-source logical fingerprint and exact-symbol counts
  in the EOD plan and session quality evidence; and
- when exact source custody is unavailable, never project a mixed-case Massive
  symbol through the upper-case V1 Resolver.

This projection does not mint an instrument, alter stable-ID rules, infer
security form from ticker spelling, or change the canonical V1 Identity
snapshot. It uses ticker case only to preserve the provider's exact join key;
eligibility still comes from retained source evidence.

The duplicate-conflict gate remains unchanged. Exact Identity source evidence
is mandatory whenever a Grouped Daily payload contains a mixed-case symbol.

## Existing-history treatment

Canonical partitions are immutable and are not overwritten in place. Existing
EOD V1 history predating this mapping rule remains quarantined from model
admission because the confirmed missing-bar family is incomplete. Completion
of source acquisition may continue, but research eligibility requires a new
immutable corrected EOD physical version or append-only correction family,
followed by full formal reconciliation. The 1,862-row retained-package census
is audit evidence and not a substitute for that repair.

## Consequences

- Common securities no longer disappear because a case-distinct preferred
  share, right, or structured product traded under the normalized same ticker.
- Genuine exact-symbol duplicates still pass through the existing equivalent
  or conflicting duplicate logic.
- Every resolved bar remains bound to an already-published stable
  `instrument_id`; provider symbol case alone can never establish eligibility.
- Historical source gaps remain explicit and fail closed for affected payloads.
- The V1 Identity Resolver's loss of provider-symbol case is not silently
  redefined. A future case-preserving Resolver contract is a separate migration.

## Supersession scope

This decision refines Massive Grouped Daily-to-EOD mapping and the five-year
backfill continuation. It does not supersede Identity classification,
instrument-ID governance, immutable publication, corporate-action handling,
or research-admission requirements.
