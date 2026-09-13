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

## Revision selection

1. Exclude quarantined occurrences and any fact whose conservative source
   availability is later than the signal cutoff.
2. Match the exact semantic key: CIK, namespace, concept, unit, start, and end.
3. Group occurrences within each accession. Exact repeated values remain one
   candidate with retained occurrence count and source-occurrence
   fingerprints. Different values in the same accession/key quarantine the
   selection.
4. Order candidate accessions by source availability. Select only the latest
   uniquely valued candidate at the cutoff.
5. A tie with different values, missing required period fields, unsupported
   form, or unresolved filer-security projection returns an explicit
   quarantine result rather than a value.

## Result

The result records selected value kind/text, semantic key, accession, form,
filed/effective period, selected availability, eligible session, revision and
repeat counts, all source occurrence IDs, query/method fingerprints, and one
of `selected`, `not_available`, or `quarantined` with deterministic reasons.

Selection does not authorize model use. A model input must additionally pass
feature coverage, cross-sectional missingness, revision stability, chronology,
and the registered research admission boundary.
