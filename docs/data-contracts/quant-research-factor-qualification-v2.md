# Quant Research Factor Qualification V2

## Purpose

This contract qualifies the data and implementation of Factor Catalog V2
without reading forward outcomes. It answers whether the eight registered
measurements are computable, sufficiently populated, variable, and distinct
enough to justify designing a separate Development screen.

The protocol version is `quant-research-factor-qualification/2.0.0`; logical
fingerprint:
`b74214155cc148d1e0d37c530ab4fea2f385af1a81237b901eec45e1fee2eb0b`.

## Fixed population and timing

- 287 contiguous XNYS signal sessions;
- 437,402 signal-date Membership paths;
- 127 source sessions ending at each completed signal close;
- stable `instrument_id` ordering; ticker is display only;
- no backward projection of signal-date Membership;
- no forward outcome, performance statistic, or validation field.

The population fingerprint is built from every signal date, its Membership
manifest fingerprint, and its ordered stable IDs. The chronology, Membership,
EOD, action, adjustment, calculator, and diagnostic implementations are
independently fingerprinted in the report.

## Missingness and isolation

- a missing, malformed, or split-quarantined stock path makes only that stable
  ID unavailable for the affected signal;
- a missing, malformed, or split-quarantined SPY path makes every factor
  unavailable for the complete signal session;
- formula-specific denominator, sample-size, and variance failures carry
  explicit reason codes;
- unavailable values are never zero-filled.

## Qualification gates

Each factor must meet all of these outcome-free gates:

- availability rate at least 0.90;
- at least 250 eligible sessions with at least 100 instruments;
- at least 120 eligible sessions in each chronological half;
- at least 100 distinct values;
- same-session tie-excess rate no greater than 0.95.

The report also retains fixed quantiles, three-IQR outer-tail counts,
session/instrument concentration, and all 28 same-session Spearman pair
diagnostics.

## Redundancy

A pair is a near-duplicate only when it has at least 60 eligible sessions,
absolute Spearman correlation at least 0.90 in at least 80% of sessions, and a
dominant sign share at least 0.90. Within a preregistered related group, the
lower numerical `redundancy_priority` survives. A cross-group near-duplicate
produces `requires_outcome_blind_redundancy_adjudication` and blocks the next
outcome protocol.

The terminal statuses are:

- `ready_for_screening_protocol_review`;
- `requires_outcome_blind_redundancy_adjudication`; or
- `rejected_data_or_implementation`.

None of them admits Alpha or grants Model Construction authority.

## Reproducibility and custody

The implementation must write one canonical JSON report to an owner-only
directory outside `/data`, reread it through the typed contract, and perform
one exact full replay. Network access, canonical-data writes, and production
writes remain zero.
