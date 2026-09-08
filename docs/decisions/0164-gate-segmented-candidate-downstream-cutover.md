# ADR 0164: Gate Segmented Candidate Downstream Cutover

## Status

Accepted

## Date

2026-09-08

## Context

ADRs 0130 and 0155–0163 prove segmented Candidate construction, append
lineage, checkpoint identity, disconnected publication mechanics, and periodic
full-lineage audit. They do not prove that actual current consumers can replace
V1 safely or quickly. A bounded downstream test is required before exposing
the path to the executor or adding more custody machinery.

Entry Geometry and Strategy Channels require the current source panel,
Candidate batches, and current state rows. Candidate Visual Context additionally
uses cumulative state history to calculate observed state age, which the
current-session append does not contain.

## Decision

Add one read-only current-consumer boundary. It requires externally supplied
expected append and source-audit logical fingerprints, formally validates the
explicit base-plus-append lineage, returns typed current Candidate/state/risk
records, and requires exact batch, panel, membership, session, and state
coverage. Incomplete legacy append fixtures fail closed.

The code-change gate then:

1. formally rereads the exact V1 source and requires both its logical identity
   and manifest SHA-256 to match the append binding;
2. compares the source panel, current Candidate batches, and current state rows
   exactly;
3. recalculates Entry Geometry and Strategy Channels from the segmented inputs,
   runs both independent Oracles, and optionally requires known result
   fingerprints; and
4. reports Visual Context and whole-V1 replacement as not ready because the
   current projection does not supply cumulative state history.

This is a go decision only for the correctness of current-session Entry and
Strategy inputs. It is a no-go for V1 cutover, CLI/executor exposure, canonical
custody, scheduler integration, or publication.

## Consequences

- The real 2026-09-04 append produced two ordered Universe batches and 3,549
  complete current state rows. Its formally validated segmented read took
  43.43 seconds because the present reader still rehashes the approximately
  840 MB base.
- Exact V1 comparison took 86.02 seconds and returned zero mismatches. The
  bound panel cache read took 9.35 seconds.
- Entry Geometry and Strategy Channels recalculated in 14.45 seconds. Their
  four batch fingerprints exactly matched the retained 2026-09-04 audits, and
  both independent Oracles returned zero mismatches.
- These results prove downstream correctness but not a useful bounded daily
  read. The next design, if resumed, must solve expected-head-to-current-payload
  resolution without rehashing the base and must define the cumulative-state
  input required by Visual Context. It should be one reviewed design, not
  another sequence of disconnected micro-contracts.
- V1 remains authoritative. No formula, parameter, rank, state, `/data`, MI,
  Snapshot, bundle, OCI, executor, coordinator, scheduler, or Production state
  changed. The validation made no external requests and no filesystem or
  Production writes.
- Targeted coverage passed, and the complete API regression finished at
  `2136 passed, 2 warnings`; both warnings are unchanged dependency
  deprecations.

## Alternatives Considered

### Cut over Entry and Strategy immediately

Rejected. Correct outputs alone do not solve current payload discovery,
persistent custody, or the 43-second base rehash, and would create two active
Candidate authorities.

### Add a new cumulative-state checkpoint in this change

Rejected. The missing Visual input is now precisely identified. Designing its
state semantics before deciding the final current-payload layout would extend
the experiment without a bounded exit condition.

### Abandon segmentation because the current read is slow

Rejected. Direct segment construction and exact downstream results remain
useful evidence. The no-go applies to cutover readiness, not to the underlying
lossless representation.
