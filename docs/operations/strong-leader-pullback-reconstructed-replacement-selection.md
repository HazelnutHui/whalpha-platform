# Strong-Leader Pullback Reconstructed Replacement Selection

This Dell-only operation executes the single coverage-corrected replacement
selection registered by ADR 0272. It reads one immutable V1 development report
and retains one immutable development decision. It does not access Validation
or Holdout data and cannot authorize Candidate activation, publication,
deployment, Production, or canonical `/data` writes.

Run it only from a clean canonical Dell repository after committing the exact
implementation. The source report must be the registered V1 report with
SHA-256
`c29f04b5e6da95e2256c137f23d00898b313325ac09e982a991bb823ce0f7852`.
Create the owner-only output custody directory with mode `0700`; the only
permitted result directory is `report=20260915-v1`:

```bash
scripts/admin/run-strong-leader-pullback-reconstructed-replacement-selection.sh \
  --development-statistics-root /absolute/private/development-statistics/report=20260915-v1 \
  --development-statistics-custody-root /absolute/private/development-statistics \
  --output-root /absolute/private/replacement-selection/report=20260915-v1 \
  --output-custody-root /absolute/private/replacement-selection \
  --created-at 2026-09-15T00:00:00Z \
  --implementation-revision EXACT_40_CHARACTER_GIT_COMMIT
```

The runner disables network access, validates the exact source and frozen
protocol, evaluates all 24 combinations, applies the three endpoint worlds and
six robustness gates, and atomically writes canonical JSON under `0700/0400`
owner-only custody. Replaying the identical command returns
`already_present`; different content at the fixed target fails closed.

Interpret the result literally:

- `locked` means one common eligible combination won in every endpoint world
  and passed all six gates;
- `blocked_source_evidence` means unavailable primary-family evidence prevents
  a decision;
- `rejected_no_common_eligible` means no combination met the common evidence
  floor;
- `rejected_endpoint_instability` means endpoint worlds selected different
  winners; and
- `rejected_robustness_gates` means the stable provisional winner failed at
  least one frozen economic or stability gate.

Even `locked` grants no Validation access. A separate formal review must
verify the source/report hashes, protocol and implementation revisions, one-run
budget, parameter lock, gate reconciliation, owner-only custody, exact replay,
and zero authority leakage. Failure retires this replacement attempt; it does
not authorize a third rule change on the same development outcomes.

