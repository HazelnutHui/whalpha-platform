# Strong-Leader Pullback Reconstructed Development Statistics

This Dell-only operation evaluates the fixed 24-combination Strong-Leader
Pullback parameter budget against the immutable reconstructed-development
dataset. It is a bounded development operation, not Validation, Holdout,
Candidate activation, publication, or Production work.

Run it only from a clean canonical Dell repository after committing the exact
statistics implementation. Create a dedicated owner-only `0700` custody
directory first, then bind the report to that implementation revision and one
fixed UTC creation time:

```bash
scripts/admin/build-strong-leader-pullback-reconstructed-development-statistics.sh \
  --development-dataset-root /absolute/private/development-dataset/dataset=VERSION \
  --development-dataset-custody-root /absolute/private/development-dataset \
  --output-root /absolute/private/development-statistics/report=VERSION \
  --output-custody-root /absolute/private/development-statistics \
  --created-at 2026-09-15T00:00:00Z \
  --implementation-revision EXACT_40_CHARACTER_GIT_COMMIT
```

The runner disables network access, formally rereads the source dataset,
rejects any Validation or Holdout rows, evaluates the frozen statistics
policy, and atomically retains one canonical JSON report under `0700/0400`
owner-only custody. Replaying the identical report returns `already_present`;
changed content at the same version fails closed.

The report contains exactly 24 parameter combinations, three horizons, and
three frozen terminal-endpoint scenarios. It applies the registered evidence
floors, session-balanced contrast, deterministic block bootstrap, cost
scenarios, chronological and Regime slices, concentration diagnostics, and
the selection rule frozen before real aggregate outcomes were read.

Interpret the resulting status literally:

- `locked` means one development parameter won consistently across all three
  endpoint scenarios and passed the development evidence gates;
- `blocked_unavailable_evidence` means missing source evidence touched a
  primary-horizon signal or control cohort;
- `inconclusive_evidence_floor` means the registered sample floor failed; and
- `rejected_endpoint_instability` means the winner changed across bounded
  terminal-reference worlds.

Even `locked` does not authorize Validation access. A separate formal review
must verify the retained report, exact source and code bindings, method
compliance, and boundary invariants before any one-way Validation transition.
The report never authorizes Holdout access, performance claims, Candidate
activation, publication, deployment, or Production writes.

Before acceptance verify the report SHA-256 and logical fingerprint, exact
source dataset bindings, `216` summaries, owner-only custody, no staging
residue, and zero network, canonical-data, publication, deployment, and
Production writes.
