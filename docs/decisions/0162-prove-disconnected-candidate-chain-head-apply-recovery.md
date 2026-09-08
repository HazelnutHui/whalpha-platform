# ADR 0162: Prove Disconnected Candidate Chain-Head Apply and Recovery

## Status

Accepted

## Date

2026-09-08

## Context

ADR 0161 binds one segmented Candidate chain head to an exact immutable
release and pointer-last publication plan. The plan deliberately supplied no
executor. Before considering `/data`, daily CLI, or coordinator integration,
the physical ordering and crash states need to be executable and recoverable
without weakening the plan's bounded-family CAS.

A test-only file copier would not be sufficient evidence. The proof must read
the exact frozen plan and source again, reject the Production root by code,
serialize competing writers, preserve ambiguous residue, and distinguish a
completed immutable release from a logically active pointer.

## Decision

Add a disconnected exact-plan Apply and recovery boundary that can operate
only beneath an owner-controlled `0700` root in `/tmp`. It explicitly refuses
the Production `/data` root before reading the plan.

Every invocation supplies and revalidates the plan SHA-256, plan logical
fingerprint, source logical fingerprint, expected bounded-family inventory
fingerprint, expected pointer-state fingerprint, and simulated root. The
executor:

1. classifies the pre-state without writing;
2. acquires an owner-controlled root-specific lock and repeats the complete
   classification;
3. publishes one exact content-addressed immutable release through a
   same-parent staging directory and atomic rename;
4. freshly verifies the original family/pointer CAS with only that separately
   verified target excluded;
5. publishes the exact planned `current.json` bytes last through atomic
   replacement; and
6. formally rereads the complete family and planned pointer.

The only accepted recovery states are:

- `not_started`: no target release exists and the original plan still reads;
- `release_published_pointer_pending`: the immutable target is exact and the
  family outside it still equals the plan pre-state; and
- `complete`: the full current reader selects the exact planned pointer.

Ordinary Apply refuses a partial or already complete state. Explicit
`verify_then_complete` may publish only the missing pointer from the exact
release-only state, or prove an already complete result with zero writes. A
staging path, corrupt release, conflicting pointer, family drift, malformed
plan/source, or ambiguous state blocks without cleanup, deletion, overwrite,
or rollback.

The result reports simulated writes separately while keeping external request,
canonical write, Production write, immutable overwrite, deletion, rollback,
and Production authorization at zero/false. No CLI or runtime integration is
added.

## Consequences

- The three-session fixture now proves bootstrap, zero-write completed replay,
  exact successor advancement with prior active rollback, release-only
  interruption recovery, corrupt-release preservation, and fail-closed
  pointer-staging residue.
- A separate test proves the simulation boundary refuses the Production root
  before any plan or canonical I/O.
- The retained real ADR 0161 plan applied only to its empty `/tmp` simulation
  root. It published the exact 4,962-byte release and 1,712-byte pointer, for
  two simulated writes / 6,674 bytes.
- The real post-family inventory fingerprint is
  `ab5ccd10017c7f14087c50f455a3212d3278e55d2efef1e8b7a4c2da92f30dac`;
  the post-pointer-state fingerprint is
  `02dfb715872bec8cb11c1b51f7791b95fe24ede244f1d7d28da9f12dcab9a476`.
  An immediate `verify_then_complete` postflight reused both exact objects and
  wrote zero files/bytes.
- `/data`, the authoritative V1 Candidate, formulas, parameters, ranks,
  states, publication, MI, Snapshot, bundle, OCI, executor, coordinator, and
  scheduler remain unchanged. No canonical Candidate chain-head pointer exists.
- ADR 0163 subsequently satisfies the periodic full-lineage prerequisite in
  the same disconnected boundary. Reviewed CLI/executor exposure and
  downstream compatibility remain later gates.
- Candidate-focused coverage passed, and the complete API regression finished
  at `2136 passed, 2 warnings`. Both warnings are the unchanged Python `crypt`
  and Starlette/httpx deprecations.

## Alternatives Considered

### Publish the pointer and release in one directory rename

Rejected because a mutable selector and retained immutable history have
different lifecycles. Pointer-last makes logical activation explicit and
leaves a safely inactive release-only crash state.

### Delete staging or partial evidence automatically

Rejected because unexplained residue may represent an interrupted or competing
operation. Preserving it is safer than guessing ownership or intent.

### Reuse the executor immediately against `/data`

Rejected. Simulation proves mechanics, not Production authorization, daily
integration, periodic semantic equivalence, or cutover readiness.
