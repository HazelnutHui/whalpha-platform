# Five-Year Research Membership Collision Recovery — 2026-09-13

## Result

All 37 source-available Membership sessions previously rejected by the V3
global Identity join gate are now retained under ADR 0227's separately
versioned V4 research-only method. The research family contains 1,250 sessions;
together with three signal-eligible sessions, the rolling five-year census
covers 1,253 / 1,255 sessions and 21,323,450 decisions.

The only missing sessions are 2026-08-13 and 2026-08-19, for which retained
Identity source custody is unavailable. Neither date was inferred or filled.

This remains reconstructed latest-vintage evidence. It is not as-operated
Membership and grants no signal, validation, holdout, performance, Candidate,
Production, or web authority.

## Collision-scope correction

The first V4 pilot bound to revision
`5efb8fd83ce965f2820db26a391f913de3cd839e` correctly failed before any
canonical write. Its 2022-08-01 diagnostic showed:

- 8,341 canonical mappings / 8,353 join denominator;
- 12 stable-identifier collisions and a 0.9985633903986592 join ratio;
- zero ambiguous mappings and zero business-key conflicts;
- exact 12,165-row category reconciliation; and
- zero canonical quarantine IDs because every collision was confined to
  noncanonical Identity references.

The implementation was corrected before creating a new plan. Evidence now
counts collisions with and without canonical candidates separately. Their sum
must equal total collisions. Any canonical candidate must retain an explicit
stable-ID quarantine; a collision without a canonical candidate remains
separately counted outside the evaluated stable-ID base.

The corrected single-session diagnostic produced 16,682 complete decisions
over 8,341 evaluated IDs. Primary contained 1,226 included, 6,653 excluded,
and 462 quarantined decisions; Secondary contained 1,303 included, 6,548
excluded, and 490 quarantined decisions. No result was promoted from the
failed first pilot.

## Frozen corrected plan

The accepted plan is bound to:

- implementation revision:
  `4052ccc58a1a46f9d24a05fcadb45b121122a42e`;
- methodology:
  `provider-form-complete-base-localized-collision-v4`;
- evaluated time: `2026-09-13T13:02:02Z`;
- provider catalog date: 2026-08-14;
- initial combined coverage: 1,216 / 1,255 sessions;
- intended continuation: 37 sessions in 13 adjacent batches;
- target-session fingerprint:
  `5cce850e36bc506ddcacbba0213ab07451f0979e4504c5302cdf23e2f403826f`;
  and
- plan logical fingerprint:
  `c71c9e7cb08c019e4b05fb60531be5319a047b97297245248c79afa2624e38e1`.

Four Dell worker processes completed 13 / 13 batches and 37 / 37 sessions with
622,424 decisions. Failed batches, remaining sessions, external requests, and
canonical writes were zero during candidate construction.

## Archive and verification

The `2026-09-13T13:07:51Z` archive plan passed preview with 37 planned
sessions, zero conflict, zero overwrite, and zero deletion. Apply then archived
and formally reread all 37 sessions / 622,424 decisions. Reused, failed,
overwritten, deleted, and external-request counts were zero.

Postflight found:

- V3 research partitions: 1,213;
- V4 research partitions: 37;
- total research partitions: 1,250;
- signal-eligible partitions: three;
- staging/partial directories: zero;
- symlinks: zero; and
- residual archive processes: zero.

The fresh five-year census reports:

| Measure | Result |
| --- | ---: |
| Membership coverage | 1,253 / 1,255 sessions |
| Missing sessions | 2 |
| Combined decisions | 21,323,450 |
| Quarantined decisions | 850,251 |
| Census status | `quarantined` |
| Performance claims authorized | false |

Census logical fingerprint:
`1c75a304056c60f6a7c79f1f74797734aaa13ff87c31d130e05c57cc887557cd`.

The credential-free current-context report then verified 21,025 canonical
files / 7,397,444,417 bytes, zero symlinks, and inventory fingerprint
`b4f1dc83b5b26a6ccde3b5dffd47ac58de465fced41d129ef74c0e2282228ff7`.
It surfaces 1,250 research Membership partitions separately and retains the
Membership blocker.

All 67 focused Membership/evidence tests and all 2,635 API tests passed with
two unchanged dependency deprecation warnings before the corrected plan was
frozen.

## Remaining boundary

The reconstructed daily population coverage stage has reached its bounded
stop. Repeating attempts against the two absent source dates or rewriting the
1,213 V3 partitions would add no defensible evidence. The next database work is
the first strategy's exact lifecycle/terminal and action/adjustment evidence,
then calibrated costs and final Historical Coverage. Historical knowledge-time
authority for Membership remains separately unresolved.
