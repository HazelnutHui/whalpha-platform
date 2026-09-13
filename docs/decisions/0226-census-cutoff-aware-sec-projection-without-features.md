# ADR 0226: Census Cutoff-Aware SEC Projection Without Features

- Status: Accepted
- Date: 2026-09-13

## Context

The first four issuer-level SEC queries now have exact source semantics and
measured clean-period coverage. They are not yet historical security features.
Selection must respect filing availability, and CIK-to-security projection
must preserve ADR 0224's share-class and knowledge-time limits.

Materializing every fact for every security and day would be expensive and
would prematurely create a feature surface before coverage is understood. A
coverage census can instead evaluate one query status for each structurally
eligible issuer/session and retain only aggregates.

## Decision

1. Implement one deterministic issuer selector for the registered query set.
   At a caller-supplied UTC cutoff and evaluated XNYS session it may consider
   only query-eligible occurrences whose period end is not after the cutoff,
   whose source availability is not after the cutoff, and whose filing-clock
   eligible session is not after the evaluated session.
2. Within the latest visible period end, exact duplicates may collapse.
   Different values or availability times within an accession, different
   values at one availability time, or multiple visible duration starts for
   one period end return an explicit quarantine result. Row order never
   selects a value.
3. For the first projection census, the link `as_of_date` is the signal
   session and the evaluated filing-clock session is the following XNYS
   session. The cutoff is that following session's open. The filing-clock rule
   already maps an accession to the first XNYS open strictly after conservative
   SEC acceptance, so an acceptance exactly at the open cannot enter that
   session.
4. Apply only `single_common_security_per_cik_v1`: admitted link, common stock,
   non-null CIK, and exactly one admitted common stock for that CIK/session.
   ETF, missing/conflicting CIK, missing source, identity mismatch, and
   multi-common-stock groups stay in explicit denominators.
5. Assign structurally eligible rows to exactly one evidence tier:
   - `as_operated_next_open` only when retained link source evidence was
     observed no later than the evaluated next open; or
   - `reconstructed_latest_vintage_development_only` when the exact dated link
     exists but its retained knowledge time does not qualify.
6. Retain query/tier/session aggregate selected, unavailable, and quarantined
   counts plus age buckets. Do not retain or publish security-level values,
   ranks, signals, labels, or outcomes in the census.
7. A selected reconstructed row remains development sensitivity only. Neither
   coverage percentage nor structural projection authorizes validation,
   holdout, headline performance, activation, Candidate, or Production use.

## Consequences

- The project can measure exact point-in-time fact availability and staleness
  without creating a broad daily fundamental panel.
- Strict knowledge-time coverage is expected to be sparse because only 11
  retained link sessions currently qualify; the census must expose that rather
  than merge it with reconstructed history.
- The issuer selector becomes reusable for a later registered feature, but a
  feature still requires a separate contract, cohort coverage decision, and
  research admission.
- Full transitive input validation occurs once per immutable stage acceptance.
  The projection scan may then use bound, selected-column reads of the same
  immutable packages; repeated full validation inside every substep is not a
  measure of rigor.

## Rejected alternatives

### Use the latest fact currently present for every historical date

Rejected as direct look-ahead leakage.

### Treat all exact dated link reconstructions as historically known

Rejected because effective date does not prove knowledge time.

### Publish the security-by-session fact panel during the coverage scan

Rejected because it creates unnecessary data volume and implied feature
authority before admission.
