# SEC Point-in-Time Fundamental Selection V1

## Purpose

`sec-point-in-time-fundamental-selection/1.0` defines how a registered
fundamental feature may select one SEC fact state without leaking a later
filing or silently resolving a source conflict. It is a query/result boundary,
not a second copy of the complete Company Facts source.

## Registered query

Each query binds:

- filer CIK;
- namespace, concept, and exact unit;
- instant or duration period method;
- exact period boundary or versioned fiscal-period rule;
- admitted filing-form families;
- UTC signal cutoff and evaluated XNYS session;
- normalized source package fingerprint;
- filer-security link fingerprint when a listed-security feature is requested;
  and
- feature-method/version identity.

No field defaults to today's latest value. Namespace/concept aliases, unit
conversion, cumulative-to-quarter derivation, trailing aggregation, and
security projection must be explicit parts of the registered method.

For an evaluated session, `source_available_at_utc` must not follow the caller
cutoff and `signal_eligible_session` must not follow the evaluated session. The
latter is assigned by the filing-clock ledger as the first XNYS open strictly
after conservative SEC acceptance. Period end must not follow the cutoff date.

## Revision selection

1. Exclude quarantined occurrences and any fact whose conservative source
   availability is later than the signal cutoff.
2. Match the exact semantic key: CIK, namespace, concept, unit, start, and end.
3. Group occurrences within each accession. Exact repeated values remain one
   candidate with retained occurrence count and source-occurrence
   fingerprints. Different values in the same accession/key quarantine the
   selection.
4. Determine the latest visible period end. Multiple visible duration starts
   for that end quarantine the selection instead of guessing a fiscal shape.
5. Order candidate accessions for the sole latest semantic period by source
   availability. Select only the latest uniquely valued availability state at
   the cutoff. Multiple accessions at that time may be retained together only
   when their value is identical.
6. A tie with different values, an internally inconsistent accession, missing
   required period fields, unsupported form, or unresolved filer-security
   projection returns an explicit quarantine result rather than a value.

## Result

The issuer result records selected value kind/text, semantic key,
accession-number set, form/filed-date set, effective period, selected
availability, eligible session, revision and occurrence counts, all selected
source occurrence IDs, query fingerprint, and one of `selected`,
`not_available`, or `quarantined` with deterministic reasons. Security
projection is a separate result and never changes the economic grain of the
selected issuer fact.

Selection does not authorize model use. A model input must additionally pass
feature coverage, cross-sectional missingness, revision stability, chronology,
and the registered research admission boundary.
