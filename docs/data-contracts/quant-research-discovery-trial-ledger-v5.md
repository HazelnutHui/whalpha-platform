# Quant Research Discovery Trial Ledger V5

## Purpose

`quant-research-discovery-trial-ledger/5.0` is the append-only cumulative state
after the formal Campaign Three Development screen and its exact replay.

## Closed content

- binds Ledger V4 as its immutable predecessor and carries the completed V1
  and V2 campaigns forward without changing their 14 consumed trials;
- replaces Campaign Three's unread registration state with the completed
  disposition of the same two candidate-Alpha interactions and one risk guard;
- records all three Campaign Three trials as `rejected_screen` after one formal
  run and one byte-identical exact replay;
- records 17 cumulative formal trials: 11 candidate Alpha and 6 risk guard;
- retains both Campaign Three before-outcomes rejections outside the formal
  outcome budget;
- records zero admitted Alpha, zero newly qualified risk evidence, and zero
  model inputs; and
- requires another new ledger version before any successor campaign may read
  Development outcomes.

Logical fingerprint:
`424da475ee8aa87a7b54eac8c9eec64f32035d7ae1a7d491b90604863edc5df1`.

## Authority boundary

Campaign Three is closed at `closed_no_candidate_alpha`. Its failures cannot be
retuned inside the consumed campaign or promoted into Model Construction.
Validation, Holdout, Strategy Expression, Candidate activation, publication,
broker access, and trading remain closed.
