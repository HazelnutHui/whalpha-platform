# Opportunity Candidate Segmented Session Candidate V1

## Status and purpose

`opportunity-candidate-segmented-session-candidate/1.0` is a Dell-local,
non-authoritative bridge from a verified-prior Candidate calculation's current
objects to one immutable session payload. It avoids immediately rebuilding the
same session from the cumulative V1 audit. It is not an append package,
Candidate publication, Snapshot source, research result, or Production input.

## Inputs and exact bindings

The writer requires:

- one formally valid `opportunity-candidate-segmented-shadow/1.0` parent and
  its `opportunity-candidate-segmented-chain-identity/1.0` tip;
- the prepared Candidate Audit V1.1 manifest for a daily
  `verified_prior_incremental` calculation;
- the exact incremental-validation record whose logical identity is already
  bound by that prepared manifest; and
- the calculation's current panel, two typed Universe batches, current typed
  state rows, six risk-mode results, zero-mismatch Oracle, raw facts, and
  normalization records.

The parent/source calculation versions, parameter fingerprints, Universe
order, prior audit identity, prior session, current session, and every reuse
gate must match. A caller cannot substitute a fabricated validation record
even when its fields appear plausible.

## Output

The new owner-only direct child of `/tmp` contains exactly:

- `candidate-session-candidate-manifest.json`; and
- `candidate-session.json`, contract
  `opportunity-candidate-segmented-session/1.0`.

The payload contains the current source panel, Candidate batches, states,
derived transitions, raw facts, normalization records, risk results, and
Oracle. It records `raw_fact_session_ordinals` in
`session_local_canonical` order. It intentionally does not copy the cumulative
V1 `raw_fact_source_ordinals`, whose whole-history positions can change when a
later session is appended.

The manifest binds the parent manifest and chain tip, intended V1 audit,
incremental validation, session ordinal, Universe order, payload logical and
physical identity, record counts, and eight current-projection fingerprints.
It states `physical_completion_required_before_append=true` and
`finalization_scope=validated_write_plus_physical_custody`.

## Custody and recovery

The target must be a new visible direct child of `/tmp`, owned by the current
user with directory mode `0700`; both completed files use mode `0400` and may
not be symlinks. The writer serializes into one deterministic hidden staging
directory, fsyncs the files and directory, verifies exact file set, custody,
sizes, and SHA-256, then atomically renames the stage and fsyncs `/tmp`.

A normal new write returns the already validated manifest after physical
custody and does not immediately parse the same payload again. A completed
stage after interruption is fully and semantically reread before recovery. An
existing target is fully reread and must equal the requested in-memory payload
and bindings for idempotent reuse. Incomplete, ambiguous, unsafe, or changed
evidence is preserved and rejected.

## CLI boundary

The Candidate CLI accepts the paired options
`--segmented-parent-shadow` and `--segmented-session-output` only for a
calculated `daily` run with an immediately prior Candidate audit. Verify-only,
cold periodic, and code/model-change runs reject the pair. If deferred V1 work
is already complete on restart, the exact paired sidecar must also exist and
bind that completed V1 fingerprint.

## Explicit non-authority

The contract performs zero network requests and zero canonical or Production
writes, and grants no publication or scheduler authority. A later append
composer must formally verify physical completion of the exact intended V1
audit before promoting the payload into an ADR 0156 append. V1 remains the
authoritative Candidate source until repeated append, downstream, retention,
periodic-cold, and cutover gates are separately accepted.

## Real Dell proof

For the real 2026-09-03 parent and 2026-09-04 current session, the final writer
produced an 86,608,577-byte payload in 38.907 seconds. The complete proof
process took 76.95 seconds and peaked at 2,079,760 KiB because it first rebuilt
runtime objects from retained evidence. All eight current projections matched
the ADR 0156 cold append exactly. A final full semantic read with the completed
validation set took 32.831 seconds; field-by-field comparison found zero
mismatches.

The payload logical fingerprint is
`a62455909c0436ad07e4024c329c961dfec8e8cd85b9aa507f0b1144037cb515`,
its physical SHA-256 is
`9c9af6fa03357f6135e83568d48c5c6f4355df7e9a903d5db8547e2a9642f967`,
and the manifest logical fingerprint is
`232ecb6de9fcf412e6c532b8bb70127eac5330e87a57f9e812137dcb4b2b0359`.
