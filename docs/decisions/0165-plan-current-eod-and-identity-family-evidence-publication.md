# ADR 0165: Plan Current EOD and Identity Family-Evidence Publication

## Status

Accepted

## Date

2026-09-08

## Context

ADR 0099 defines immutable family-evidence publication and transitive source
validation. ADR 0100 adapts current canonical EOD and EOD-bound Identity into
deterministic evidence without publishing it. Its 2026-09-08 full-content run
validated all 304 sessions, but an in-memory validation result is not an exact,
separately reviewable publication intent.

The next bounded step must bind the two evidence manifests and their absent
targets without implying that other research families, final Historical
Coverage, strategy development, or performance evaluation are ready.

## Decision

Add a typed, deterministic, network-prohibited publication-plan boundary for
exactly two families: `eod_price_bar` and `point_in_time_identity`.

The plan:

1. reconstructs both candidates through ADR 0100 and transitively validates
   every referenced source manifest and payload;
2. embeds both complete evidence contracts and records their canonical byte
   counts and SHA-256 digests;
3. derives each immutable target from the family and evidence logical
   fingerprint, and binds that target to an explicit `absent` state;
4. requires identical ordered session coverage across both families;
5. carries `verify_exact_then_complete` as a future recovery policy while
   leaving Apply, final Historical Coverage, research development, and
   performance authority false; and
6. writes only one new owner-read-only, canonical JSON plan as a direct child
   of `/tmp`.

The formal reader requires an optionally approved plan SHA-256, rereads every
source byte, recomputes the exact evidence target and manifest hash, and fails
if either target now exists. No Apply executor is part of this decision.

A whole-`/data` inventory compare-and-swap is intentionally not embedded. Each
evidence object already transitively binds every source file it consumes, and
both immutable targets are checked directly. Binding unrelated daily data
would make the plan expire without improving the safety of these two writes.

## Consequences

- The real Dell plan covers 304 sessions from 2025-06-23 through 2026-09-04.
  EOD binds 304 artifacts, 608 source files, and 2,816,903 rows. Identity binds
  304 artifacts, 2,128 source files, and 2,825,403 canonical Instrument rows.
- The proposed change is exactly two evidence manifests totaling 675,569
  bytes. The family-set fingerprint is
  `be67c6ec924809eca63dacf1130ec19d9df0d673f65b403a416de1f2be812377`.
- The retained `/tmp` plan has logical fingerprint
  `6ae6738181012b6f9364d5b624d7edaa81d992b7be623e6bd6b58c2854d5e663`
  and physical SHA-256
  `dced91a98cf4a71fe28748c241f83aa31dcdb588a9f322245a9b14de6d4511ae`.
  A separate exact-SHA formal reread passed with both targets still absent.
- Post-run context verification left `/data` unchanged at 4,058 files /
  2,009,024,076 bytes with fingerprint
  `d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`,
  zero symlinks, and zero publication residue. The formal evidence and final
  Coverage roots remain absent.
- Targeted coverage passed 13 tests. Source-byte drift, target collision,
  wrong plan SHA, noncanonical plan bytes, and out-of-custody paths fail
  closed. The complete API regression passed `2147 passed, 2 warnings`; both
  warnings are unchanged dependency deprecations.
- This is a GO for a later, separately reviewed two-file Apply design only. It
  is not publication, Historical Coverage, research readiness, strategy
  validation, deployment, or Production change.

## Alternatives Considered

### Publish both evidence manifests in the planning command

Rejected. Planning and mutation must remain separate, and no Apply or recovery
executor has yet been reviewed against the real immutable targets.

### Publish final Historical Coverage at the same time

Rejected. Historical Membership, corporate actions, lifecycle, adjustment,
cost, revision-lineage, and evaluation requirements remain incomplete.

### Bind the complete `/data` inventory

Rejected. It would couple this plan to unrelated canonical changes even though
the consumed sources and exact targets are already fully bound.
