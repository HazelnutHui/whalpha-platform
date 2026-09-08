# ADR 0166: Apply Current Family Evidence as an Ordered Prefix

## Status

Accepted

## Date

2026-09-08

## Context

ADR 0165 freezes the exact current EOD and point-in-time Identity evidence
bytes in one deterministic plan, but deliberately provides no mutation path.
The two immutable evidence directories are independent filesystem targets, so
an interruption can occur after the first rename. Recovery must distinguish
that valid prefix from replay, corruption, staging residue, and impossible
publication order without deleting evidence or broadening the plan.

The plan does not bind the complete `/data` inventory because unrelated daily
partitions may legitimately arrive between planning and Apply. The executor
must nevertheless detect unrelated or concurrent changes during its own
critical section.

## Decision

Add one explicit, exact-plan-bound, network-prohibited Apply executor for the
two ADR 0165 family-evidence manifests.

Execution requires the reviewed plan file SHA-256, plan logical fingerprint,
family-set fingerprint, and approved Dell data root. It takes the same global
canonical-data lock as the daily Apply path, rereads the complete plan and all
transitively referenced source bytes under that lock, and permits only these
states:

1. both targets absent: ordinary Apply may start;
2. EOD present and Identity absent: `verify_then_complete` may verify and reuse
   EOD before publishing Identity;
3. both targets present: `verify_then_complete` may prove a zero-write
   completed result; or
4. EOD absent and Identity present: reject as an impossible out-of-order state.

Each family is one atomic unit: create an fsynced sibling staging directory,
write the one canonical mode-0644 manifest, fsync it, and rename the directory
atomically. EOD is always first and Identity second. A completed target must be
owner-held, mode 0755, contain exactly `manifest.json`, match the planned size
and SHA-256, and pass the existing semantic repository reader against every
bound source artifact.

Any matching staging residue blocks both ordinary Apply and recovery and is
preserved for diagnosis. The executor removes only a staging directory it
created in the current invocation and only while its filesystem identity still
matches. It never overwrites or deletes a completed canonical partition.

Immediately before the first target action and after the final formal reread,
the executor fingerprints all canonical files except the two exact targets and
their deterministic staging paths. A difference fails closed. This is a
critical-section drift check, not a retroactive whole-inventory binding added
to the reviewed plan.

The final result reports published versus reused families, exact added files
and bytes, both outside-target fingerprints, full post-state fingerprint, and
zero external requests, overwrites, deletions, final-Coverage authority, or
research/performance authority.

## Consequences

- Disconnected temporary-root tests prove ordinary ordered publication, EOD-
  only interruption recovery, completed zero-write recovery, no-prefix refusal,
  out-of-order refusal, corrupt-target preservation, staging-residue
  preservation, owned-staging cleanup, exact-binding rejection, outside-target
  drift detection, formal reread, and DNS/socket prohibition. The focused
  family-evidence suite passed 24 tests; 34 adjacent Coverage, Membership Apply,
  and same-day catch-up tests also passed.
- The administrator entry point accepts all three reviewed fingerprints
  explicitly and emits only compact, credential-free success or rejection
  evidence.
- A 2026-09-08 read-only reread of the retained real ADR 0165 plan again
  validated all 304 sessions, both absent targets, plan SHA-256
  `dced91a98cf4a71fe28748c241f83aa31dcdb588a9f322245a9b14de6d4511ae`,
  plan logical fingerprint
  `6ae6738181012b6f9364d5b624d7edaa81d992b7be623e6bd6b58c2854d5e663`,
  and family-set fingerprint
  `be67c6ec924809eca63dacf1130ec19d9df0d673f65b403a416de1f2be812377`.
- The separately reviewed real Apply subsequently published the exact two
  manifests / 675,569 bytes. Its outside-target fingerprint was unchanged,
  full post-state fingerprint is
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
  and a separate completed-state postflight reused both targets while writing
  zero files/bytes. The dated audit records the complete evidence.
- Final Historical Coverage, research development, performance interpretation,
  analytics, Snapshot, bundle, OCI, scheduler, and deployment remain outside
  this boundary.
- The complete API regression passed `2160 passed, 2 warnings`; both warnings
  are unchanged dependency deprecations.

## Alternatives Considered

### Publish both families through one combined directory rename

Rejected. The established canonical layout uses independently addressed,
family-specific immutable evidence IDs. A new wrapper directory would change
reader semantics and still require a separate completion contract.

### Treat Identity-first publication as recoverable

Rejected. Allowing both orders doubles the state space and removes the simple
prefix invariant without adding product value.

### Delete staging residue automatically during recovery

Rejected. Residue may be evidence of an interrupted or foreign invocation.
Only staging proven to belong to the current failing invocation is removable;
pre-existing residue requires operator diagnosis.

### Require the whole inventory to match its planning-time fingerprint

Rejected. Exact sources and targets are already plan-bound. A planning-time
whole-root CAS would make a valid plan expire on unrelated append-only daily
work; the before/after critical-section comparison provides the needed
concurrency check without that coupling.
