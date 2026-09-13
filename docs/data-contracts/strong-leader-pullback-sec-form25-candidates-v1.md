# Strong-Leader Pullback SEC Form 25 Candidates V1

## Purpose

`strong-leader-pullback-sec-form25-candidates/1.0` extracts standardized source
fields from every Form 25-NSE document in the frozen transition-period
package. It produces structured candidates, not canonical lifecycle facts.

## Inputs

The network-disabled builder formally rereads and binds the ADR 0229 plan, ADR
0230 source package, and ADR 0231 content census. The source/census and
source/plan identities must reconcile exactly.

## Record fields

Each of the 64 records retains:

- request sequence, stable-ID locator, issuer CIK locator, accession, filing
  and acceptance time, and physical document hash;
- Commission file number, issuer name, exchange name, security class
  descriptions, selected rule provision, and notice signature date; and
- explicit nulls for last tradable date, effective delisting date, termination
  reason, predecessor/successor/acquirer, consideration, and OTC/liquidation
  continuation.

CIK must come from the issuer link and match the plan. A rule is retained only
when its actual HTML checkbox is selected. Exactly one ISO signature date must
equal the filing date. Missing, repeated, or ambiguous required structure
rejects the complete report.

## Population and authority

Completion requires 64 documents, 62 stable-ID locators, exactly two IDs with
two records, full aggregate reconciliation, canonical JSON, and `0700/0400`
custody. Multiple records are never silently merged.

Source availability/revision, security/listing identifiers, and exchange-
removal status/date families are marked only as partial candidate evidence.
All eight complete field-support counts, identity assignments, lifecycle
facts, terminal outcomes, strategy outcomes, `/data`, Historical Coverage,
research admission, Candidate, publication, deployment, and scheduler counts
remain zero.
