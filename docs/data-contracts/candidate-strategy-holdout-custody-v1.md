# Candidate Strategy Holdout Custody V1

## Purpose

`candidate-strategy-holdout-custody/1.0` provides durable single-consumption
custody for one passed, locked Strong-Leader Pullback validation identity. It
does not evaluate real data and cannot create a performance claim.

## Identity

One custody ID binds:

- experiment fingerprint;
- mechanics-batch fingerprint;
- passed validation-report fingerprint;
- parameter-lock fingerprint; and
- the selected parameter-combination ID.

Changed validation, mechanics, lock or selection produces another identity and
requires a separate research version/holdout policy review before use; callers
cannot substitute those values inside retained evidence.

## Event sequence

The only legal sequence is:

1. `holdout_reserved`; then
2. exactly one `holdout_completed` or `holdout_failed`.

Reservation is durably written before the evaluation capability is invoked.
An isolated reservation is an ambiguous consumption and permanently blocks
replay. Failure also blocks replay. Completed custody returns the retained
result fingerprint without invoking evaluation again.

Every event uses owner-only custody, canonical JSON, a content fingerprint and
the preceding event fingerprint. Unexpected files, missing sequence numbers,
changed permissions, symlinks, changed bindings and malformed terminal evidence
are rejected.

## Authority boundary

The result always records zero Production writes and zero external requests,
and denies stage-transition and performance-claim authority. Current tests use
only synthetic fixture reports under temporary roots. There is no installed
root, CLI, real input adapter, canonical result writer, publication, deployment
or scheduler integration.
