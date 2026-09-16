# Campaign Three Development Screening

This is the owner-only, network-disabled procedure for the frozen Campaign
Three screen. It does not itself authorize Development outcomes. Run it only
from the canonical workstation repository after the complete implementation is
committed and the worktree is clean.

## Boundaries

- exactly one formal run and one exact replay;
- Development only; Validation and Holdout remain closed;
- no provider request, canonical `/data` write, Production write, publication,
  deployment, Candidate activation, broker access, or trading;
- all feature and market-state reconstruction completes before the execution
  slot is reserved;
- terminal-reference and future-EOD label reads begin only after reservation;
- a reserved or failed slot is consumed; and
- formal and replay outputs use distinct owner-only roots but must contain
  byte-identical reports.

## 1. Preflight

1. Confirm the canonical branch, exact HEAD, and clean worktree.
2. Run the focused Campaign Three tests and the full backend suite.
3. Verify the exact V1 diagnostics, V2 qualification, Campaign Three input
   qualification, Market-State qualification, census, Membership, canonical
   split publications, historical split candidate, and terminal-reference
   roots.
4. Prepare separate `0700` custody roots for request, grant, execution events,
   formal report, and replay report. Do not place them in `/data` or Git.

## 2. Create the closed request

```bash
scripts/admin/run-quant-research-campaign-three-development-access.sh request \
  --implementation-revision EXACT_40_CHARACTER_COMMIT \
  --output-root /absolute/private/requests/request=VERSION \
  --output-custody-root /absolute/private/requests
```

The command emits the request fingerprint and exact authorization phrase. It
does not open outcomes. Stop and obtain the user's exact phrase; do not infer,
shorten, reuse, or auto-generate authorization.

## 3. Persist the exact grant

```bash
scripts/admin/run-quant-research-campaign-three-development-access.sh grant \
  --implementation-revision EXACT_40_CHARACTER_COMMIT \
  --request-root /absolute/private/requests/request=VERSION \
  --request-custody-root /absolute/private/requests \
  --output-root /absolute/private/grants/grant=VERSION \
  --output-custody-root /absolute/private/grants \
  --authorization-phrase EXACT_USER_PHRASE \
  --granted-at EXACT_UTC_TIMESTAMP
```

The grant opens only the two Campaign Three Development executions. It grants
no later research or Product phase.

## 4. Formal run

Invoke `scripts/admin/run-quant-research-campaign-three-screening.sh` with the
same source roots used by the completed V2 screen, plus the exact V1
diagnostics, V2 qualification, Market-State qualification, Campaign Three
input qualification, request, grant, execution custody, and a fresh formal
report root. Set:

```text
--execution-kind formal
--created-at EXACT_SHARED_UTC_TIMESTAMP
--implementation-revision EXACT_40_CHARACTER_COMMIT
```

The runner first reconstructs the 106-session V1 and V2 feature panels and
requires an exact V2 qualification replay. Only then does it reserve the formal
slot, read terminal evidence and registered future EOD paths, construct the
503,580 labels, evaluate the three frozen trials, persist the canonical report,
and append the formal completion event.

## 5. Exact replay

Run the same command again with every source, request, grant, revision, and
`created-at` unchanged. Change only:

```text
--execution-kind exact_replay
--output-root /absolute/private/campaign-three/report=REPLAY_VERSION
```

The replay report root must differ from the formal root. Completion succeeds
only when report SHA-256 and logical fingerprint exactly match the formal
completion record.

## 6. Close or advance

- If no Alpha survives, close Campaign Three, append the decisions to the next
  ledger edition, retain every failure, and return to outcome-blind intake.
- If an Alpha survives, stop at `ready_for_model_protocol_review`. Draft and
  approve a separate Model Construction protocol before any model fitting.
- A risk guard alone cannot open Model Construction.
- Do not publish results or update the website until the formal/replay pair,
  adversarial review, ledger close, status documentation, and separate
  deployment decision are complete.

Any preflight, lineage, custody, label, statistical, or replay mismatch fails
closed. Do not delete execution records or retry a consumed slot.
