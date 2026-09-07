# ADR 0152: Plan Membership with a Last Publication Marker

## Status

Accepted

## Date

2026-09-06

## Context

ADR 0151 proves that the 2026-09-04 disconnected Membership partition is
eligible for a next-open strategy. Copying its Parquet and physical manifest
directly into `/data` would still be incomplete governance: directory presence
would not prove the knowledge-time assessment, and a crash between multiple
files could expose a partially published family.

The existing Membership physical manifest is immutable and already formally
validated. Rewriting it to add new timing fields would change evidence bytes
and introduce a circular hash between the physical manifest and its timing
assessment.

## Decision

Add a distinct canonical Membership publication marker and a no-write Apply
plan.

The Apply plan binds:

- the exact candidate Membership manifest and Parquet source/target paths,
  sizes, and SHA-256 values;
- the complete ADR-0151 knowledge-time assessment;
- the candidate inventory fingerprint;
- the exact pre-Apply `/data` inventory fingerprint;
- an immutable canonical publication marker and its prospective byte hash;
- absent Membership and publication-marker target partitions;
- exactly three prospective files and their aggregate byte count.

The publication marker repeats the exact Membership logical/physical bindings
and embeds the complete signal-eligible timing assessment. It sets Historical
Coverage and research-performance authorization to false.

A future Apply must publish the Membership physical partition first and the
logical publication marker last. Consumers must treat the last marker—not raw
directory presence—as canonical completion. If interrupted after the physical
partition but before the marker, recovery may reuse only exact planned bytes
and finish the marker; no incomplete partition may be consumed.

No-write planning formally rereads Membership and canonical Identity custody,
repeats the timing gate, checks target absence, and compares the full canonical
inventory. It cannot create a plan for an outcome-only partition.

## Consequences

- The real 9/4 no-write plan is stored owner-only at
  `/tmp/whalpha-membership-20260904-signal-eligible.plan.json` with file SHA-256
  `67cf92606ddc5a314a30df304d568f93c7c051d09925d89b81f3b20a964833c8`
  and logical fingerprint
  `57a59eaf9bfe0b44ba3cf2257e710a59c8f90b6a93b7c34d34dd064bf77c30c4`.
- It is bound to `/data` inventory
  `a49348fc48219771d96ddc8bafed4fc3d5b32774ac61e45f102eef4fc0bb4f56`
  and proposes exactly 3 files / 463,460 bytes across two absent partitions.
- A real attempt to plan corrected 9/3 stopped with
  `UniverseMembershipApplyPlanError`; no plan file or canonical write was
  produced.
- The plan remains `ready_for_separate_review` with `apply_authorized=false`.
  It does not itself authorize Apply, Historical Coverage, research results,
  analytics changes, or deployment.

## Alternatives Considered

### Modify the existing Membership physical manifest

Rejected because its exact bytes are already evidence-bound and embedding an
assessment that hashes the manifest would create a circular dependency.

### Publish timing evidence before Membership without a final marker

Rejected because a timing record referring to absent Membership is harmless
but does not let consumers distinguish a later complete pair from an
unreviewed raw partition.

### Treat the plan file outside `/data` as the permanent completion record

Rejected because durable canonical consumers and Historical Coverage need a
formal marker below the governed data root.
