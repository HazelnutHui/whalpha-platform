# Strong-Leader Pullback Method Diagnostics — 2026-09-14

## Result

The first valid reconstructed-population diagnostic completed as
`report=20260914-v2` with no forward outcome, performance metric, parameter
selection, network request, canonical write, or Production write.

- interval: 287 sessions, 2025-06-23 through 2026-08-12;
- declared paths: 437,402;
- complete observations: 417,209 (95.38%);
- explicit exclusions: 20,193 (4.62%);
- known clear split-adjusted complete paths: 700;
- report SHA-256:
  `8bcd602c64c7a1ab403a9c97bea21c8edb1758b60d46f879cf23b4bf7c015b36`;
- logical fingerprint:
  `c082566f283516b9a93d5658832450fb85071a3b59892cb8d922c1f37af34bd8`;
  and
- custody modes: directory/report `0700/0400`.

An independent full replay formally reread the same 287 Membership partitions
and roughly 5.31 million decision rows, recomputed the complete feature
population, and returned the existing report with the identical logical
fingerprint and file SHA-256. No partial, staging, or symlink residue exists.
The complete backend regression passed 2,823 tests with only the two unchanged
dependency deprecation warnings.

The 20,193 exclusions reconcile exactly. Twelve unresolved split-evidence days
reject their complete cross-sections, accounting for 18,646 paths. The first
otherwise price-complete day cannot initialize the recomputed Regime, which
accounts for the remaining 1,547 paths. No unattributed exclusion remains.

## Outcome-blind observations

All four numeric features have nondegenerate populations. Relative-leadership
rank spans 0 to 1 with median 0.5; trend quality spans 0 to 100; ATR pullback
depth spans -8.7313 to 71.6230; and volume ratio spans 0.0430 to 82.6532. Close
is above its prior close on 50.58% and above its prior high on 25.80% of
complete observations.

The recomputed Regime proxy contains 210,001 Risk-on, 170,583 Balanced, and
36,625 Defensive paths, but no Stress paths. This is a material limitation for
later per-Regime sufficiency and prevents any claim of all-Regime coverage.
Session and stable-instrument concentration show no dominant group: maximum
shares are 0.43% and 0.06%, respectively.

Every one of the 24 preregistered parameter combinations produces at least one
outcome-blind trigger. Counts range from 86 to 3,326, or 0.30% to 5.71% of the
corresponding eligible-leader control. These counts only test mechanics. They
cannot rank combinations, change thresholds, or establish future sample-size
sufficiency.

Threshold-neighborhood rates are 4.02% for relative leadership, 3.21% for
trend quality, 26.86% across the six ATR boundaries, and 23.49% across the two
volume boundaries. These describe sensitivity surfaces; they are not evidence
for moving a boundary.

## Corrections and retained limitations

Observation contract 1.2 removes arbitrary ceilings that had mislabeled finite
extreme ATR and volume values as missing. Split hazard evaluation now treats a
quarantined adjustment row as hazardous only when the 21-session window also
contains an active split event. Feature-specific missing reasons are no longer
copied onto unrelated features.

An earlier `report=20260914-v1` was invalidated by those implementation defects
and is not evidence. It was removed from active custody after V2 was
independently verified; its failure rationale remains preserved here.

The valid report still uses reconstructed, not-as-operated Membership; sparse
known-split adjustment with unproven neutral rows; and a recomputed same-session
Regime proxy. Point-in-time sector concentration is unavailable. The formal
performance gate therefore remains `rejected_data_blocked`.

## Completion decision

The method implementation and reconstructed-population diagnostics are
`ready_for_lab_method_surface_with_limitations`. This authorizes presentation
of the registered logic, exact parameters, method-computability coverage,
explicit exclusions, and blockers in Quant Research Lab. It does not authorize
real labels, return metrics, parameter choice, validation, sealed holdout,
Candidate use, publication of a research result, or deployment.

The Lab model record was then upgraded to
`quant-research-lab-model-record/1.2`. An independent comparison between the
checked-in browser record and the owner-only report verified the same method,
input-feature, report, implementation, interval, and path-count identities.
The resulting Lab record fingerprint is
`ec6f8473d1824526bcdecffbc8044e82201e325e4f2036253378773f13443831`.
It contains zero outcomes, zero performance metrics, zero parameter-selection
authority, and zero Candidate authority.

The trilingual Lab evidence ladder passed all 126 frontend tests and a clean
production build. The first full regression exposed that the new coverage-
ratio validator leaked Decimal status flags into later fingerprint tests. The
calculation was moved into an isolated Decimal context and a dedicated
non-pollution regression was added. Sixty direct regression checks and the
complete 2,825-test backend suite then passed with only the two unchanged
dependency deprecation warnings. This completes the outcome-blind method-and-
surface phase without a Snapshot, bundle, deployment, or Production mutation.

A later same-day presentation alignment changed only the record's stale
`next_required_decision` after the method-and-diagnostics phase had completed.
The historical record fingerprint above remains the exact identity audited in
this section. The current checked-in record fingerprint is
`4622fb2fe86cc28249f53c89003f450a9e9d19c5696cd4eb865f413140b982c8`;
method, diagnostic, feature, evaluation, lifecycle, result, and Candidate
authority remained unchanged.
