# ADR 0128: Separate daily Candidate commit from periodic semantic reread

## Status

Accepted.

## Date

2026-09-04.

## Context

The verified-prior Candidate daily calculation validates the complete
cumulative typed batches, state history, risk results, raw and normalization
prefixes, source lineage, parameters, equivalence gates, and independent
current-session Oracle before writing. Its resumable writer then emits
canonical artifacts in a fixed order, computes byte counts and SHA-256 while
streaming, binds every logical fingerprint into an owner-only recovery journal,
fsyncs each transition, and prepares a completed manifest before atomic
delivery.

ADR 0026 additionally required the same process to parse and semantically
reconstruct all newly written cumulative artifacts immediately before the
directory rename. ADRs 0060 and 0065 then allowed later publication and
planning to rely on bounded completion evidence because that full reread had
occurred.

The now 10-session 2026-09-03 Candidate audit is 804 MB. A clean exact daily
replay took 521.21 seconds and peaked at 8,886,376 KiB RSS. Calculation through
the pre-write boundary took 95.365 seconds and streaming write took 44.104
seconds. The remaining interval combined artifact projection, object lifetime,
completion work, and the final complete semantic reread; the available stage
counters do not support assigning that whole interval to any one cause. All ten
business artifacts were byte-identical to the prior audit and the logical
fingerprint and zero-mismatch Oracle were unchanged.

The existing completion/publication evidence reader rehashed the complete
804 MB artifact set, validated its manifest, exact files, ownership, modes,
sizes, SHA-256 descriptors, parameter contract, session, Universe order,
Oracle result, and equivalence gates in 1.595 seconds with 152,816 KiB peak
RSS. Repeating the already completed in-memory semantic validation immediately
after deterministic write is therefore a material daily cost, not an
independent model calculation.

## Decision

- Introduce two explicit resumable finalization scopes:
  `validated_write_plus_physical_custody` and `full_semantic_reread`.
- A `daily` verified-prior calculation uses
  `validated_write_plus_physical_custody`. Before atomic directory delivery it
  must validate the completed manifest, exact artifact order and file set,
  owner/mode/symlink custody, byte counts, SHA-256 of every artifact, parameter
  contract, session and Universe shape, all-true equivalence gates, and the
  zero-mismatch Oracle fields.
- This physical completion is valid only after the writer has already
  validated the complete cumulative in-memory business objects and produced
  the recovery journal and pending manifest. It is not a replacement for
  calculation, Oracle, source, prefix, or writer validation.
- `periodic` and `code_change` calculations retain
  `full_semantic_reread`, including canonical reconstruction, typed contracts,
  record and history fingerprints, source/session/Universe bindings,
  transition equivalence, incremental ledger validation where applicable, and
  Oracle reconstruction.
- The standalone finalizer defaults to `full_semantic_reread`; callers must
  explicitly request the daily scope. Unknown scope values fail closed.
- Record the selected scope as physical runtime counters excluded from the
  Candidate business logical fingerprint.
- Planning, publication, Entry, Strategy, Visual Context, periodic comparison,
  and explicit full verification retain their existing readers. Every
  downstream path still rehashes the immutable bytes it consumes or binds.

This decision supersedes only ADR 0026's requirement that every freshly
calculated daily audit receive an immediate second complete semantic
reconstruction. Its streaming, recovery, journal, fsync, exact-path, and
atomic-delivery rules remain in force. It clarifies the full-finalization
premise in ADRs 0060 and 0065: daily completion is now the conjunction of full
write-time semantic validation and post-write physical custody; periodic and
code-change tiers retain the independent full semantic reread.

## Consequences

- On the same unchanged 2026-09-03 inputs, daily-scope completion took 294.99
  seconds and peaked at 7,534,432 KiB, a 226.22-second or 43.4% wall-time
  reduction. All ten business artifacts were byte-identical to the prior
  audit; logical fingerprint
  `b6945f58b4766fd2e110415a7fa45816447205a61caf1085f9fe759c2d89f12f`
  and zero-mismatch Oracle evidence were unchanged.
- A separate explicit full semantic reread of that delivered daily-scope audit
  passed in 228.285 seconds with 8,737,080 KiB peak RSS, the same logical
  fingerprint, zero Oracle mismatches, and completed status.
- A corrupted or incomplete written artifact cannot be delivered: its file
  set, custody, size, or SHA-256 must differ from the pending completed
  manifest and fail closed.
- A calculation, semantic, source-lineage, prefix, parameter, equivalence, or
  Oracle defect still fails before artifact completion. Periodic/code-change
  and explicit full readers continue to independently reconstruct completed
  semantics.
- No artifact schema, formula, parameter, score, state, rank, Universe,
  publication, Snapshot, canonical `/data`, scheduler, OCI, or network boundary
  changes.
- Real daily-scope replay matched all prior business bytes and passed a
  separate explicit full semantic reread before this decision was accepted.

## Alternatives Considered

### Remove semantic validation from Candidate calculation

Rejected. The speedup is permitted only because complete typed validation and
the independent current-session Oracle already finish before write.

### Keep the immediate full reread every day

Rejected. The measured 228.285-second reread is larger than the approximately
139-second named calculation-plus-stream-write path and rechecks the same
semantics in the same process rather than providing a separate chronological
or independent-model test.

### Change Candidate storage to Parquet, deltas, or pointer chains now

Deferred. Those may improve cumulative storage and research access later, but
they would change mature audit and consumer contracts. The explicit
finalization scopes address the measured daily bottleneck with smaller scope.

### Make custody-only finalization the default

Rejected. Default-full preserves conservative behavior for direct callers and
ensures only the explicit daily tier can select the bounded fast path.
