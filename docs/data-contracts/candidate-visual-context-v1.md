# Candidate Visual Context V1

## Purpose and status

`candidate-visual-context/1.0` is implemented as an offline, shadow-only Dell
contract, calculator, independent validator, formal `/tmp` audit, and
network-prohibited CLI. It is not yet part of Market Intelligence, Snapshot,
the public bundle, or Production.

It supplies visual evidence for a Candidate detail view. It changes no score,
rank, risk eligibility, Candidate state, Entry Geometry result, or strategy
channel. It does not predict returns and does not describe option performance.

## Grain and source binding

One record is keyed by:

`as_of_session + universe_id + stable instrument_id`

Every batch binds:

- the exact Candidate batch fingerprint;
- the exact Entry Geometry batch fingerprint;
- the formal panel history fingerprint;
- a deterministic fingerprint of the complete supplied Candidate state ledger.

Record identity and source fingerprints must agree across Candidate, current
state, and Entry Geometry. Any mismatch stops the batch.

## Price path

An available path contains exactly 20 ascending session dates ending on the
as-of session and one scale-10 canonical close per date. It additionally binds
the current Entry Geometry reference levels:

- current close;
- SMA10 and SMA20;
- prior five-session close high and low;
- selected reference-support kind and value, if one exists.

Missing sessions, nonpositive closes, unavailable Entry Geometry, or a current
close mismatch makes the complete path unavailable with an explicit reason. No
interpolation, zero-fill, forward-fill, or browser reconstruction is allowed.
The close path inherits the formal EOD panel's corporate-action and adjustment
semantics; it is not a total-return or option-return series.

## Observed Candidate-state age

State age is independently available or unavailable. For an available,
non-stale current Candidate state, the calculation walks backward over the
retained audit sessions while the same final stage remains available and
contiguous. It publishes:

- current final stage;
- first observed session in the contiguous run;
- observed session count;
- `left_censored`;
- exact current-state fingerprint.

`left_censored=true` means the run reaches the first retained state session, so
the value is a lower bound. The contract never labels this field as signal age
or success probability.

## Audit

The audit directory contains:

- `visual-context-batches.json`;
- `visual-context-oracle-reports.json`;
- last-written `visual-context-audit-manifest.json`.

All files are canonical JSON, hash/fingerprint bound, owner-read-only, and
inside one owner-controlled direct child of `/tmp`. Formal reread requires zero
Oracle mismatch, input-permutation equivalence, no production-calculator import
by the Oracle, zero external requests, and zero Production writes.
