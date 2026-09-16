# Campaign Three Input Qualification Operations

## Scope

This workstation-only operation builds one outcome-blind alignment and input-
support report for the four accepted Campaign Three proposals. It reads the
frozen source reports and canonical input bars, replays only the two required
V2 factors over the 106-session Development intersection, and writes one
owner-only report outside `/data`.

It does not read returns, labels, old screening outcomes, Validation, Holdout,
or Production data. It performs no network request and no canonical or
Production write.

## Preconditions

1. Use a clean, committed canonical source revision on the research
   workstation.
2. Reread every source report and data root through its formal reader.
3. Use the frozen V1 diagnostics, V2 qualification, Market-State qualification,
   development census, Membership, split-action, split-adjustment, and private
   historical split-extension roots.
4. Use a real non-symlinked owner-only `0700` output custody directory.
5. Give each retained execution a new direct child named `report=<bounded-id>`.

## Execution

Run:

```bash
scripts/admin/run-quant-research-campaign-three-input-qualification.sh \
  --data-root /absolute/canonical/data \
  --membership-shadow-root /absolute/reconstructed/membership \
  --development-census-root /absolute/development/census \
  --split-action-publication-root /absolute/canonical/split/actions \
  --split-adjustment-publication-root /absolute/canonical/split/adjustments \
  --historical-split-candidate-root /absolute/private/split-candidate/build=VERSION \
  --historical-split-candidate-custody-root /absolute/private/split-candidate \
  --v1-diagnostics-root /absolute/private/factor-diagnostics/report=VERSION \
  --v1-diagnostics-custody-root /absolute/private/factor-diagnostics \
  --v2-qualification-root /absolute/private/factor-qualification-v2/report=VERSION \
  --v2-qualification-custody-root /absolute/private/factor-qualification-v2 \
  --market-state-root /absolute/private/market-state/report=VERSION \
  --market-state-custody-root /absolute/private/market-state \
  --output-root /absolute/private/campaign-three-input/report=VERSION \
  --output-custody-root /absolute/private/campaign-three-input \
  --created-at 2026-09-16T00:00:00Z \
  --implementation-revision EXACT_40_CHARACTER_GIT_COMMIT
```

The implementation revision must be the current clean commit. The runner
disables network access before reading sources. It verifies the full V2 source
identity, but the bar replay stops at the last required Development session;
later signal partitions are not reread for this bounded task.

## Replay and verification

1. Preserve the first report unchanged.
2. Execute once more to a distinct new report directory with the same source
   revision and `created-at` value.
3. Require identical canonical bytes, SHA-256, and logical fingerprint.
4. Confirm 106 Development sessions, four decisions, zero outcome reads, zero
   external requests, zero `/data` writes, and zero Production writes.
5. Retain rejected designs and reason codes; do not relax a gate after seeing
   the result.

A ready result permits the frozen Campaign Three screening protocol and Ledger
V4 to be drafted. It does not grant the separate authority needed to read
Development outcomes.
