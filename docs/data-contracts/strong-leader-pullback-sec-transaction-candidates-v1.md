# Strong-Leader Pullback SEC Transaction Candidates V1

## Purpose

`strong-leader-pullback-sec-transaction-candidates/1.0` classifies and
localizes source candidates in the 89 non-Form-25/non-Form-15 documents from
the frozen transition package. It is a form-aware evidence index, not a
transaction-completion or security-lifecycle fact table.

## Inputs and population

The network-disabled builder formally rereads and binds the ADR 0229 plan, ADR
0230 source package, and ADR 0231 content census. Completion requires:

- 62 Form 8-K documents;
- 12 Schedule TO tender-offer amendments;
- 12 Schedule 14D-9 amendments;
- two definitive additional proxy materials; and
- one Form 6-K.

The 89 records cover 63 stable-ID locators. Fourteen IDs have more than one
record and the maximum is three. CIK and stable ID remain locators inherited
from the bound plan, not identities proven by document text.

## Form-aware structure

Each record has one explicit structure state:

- `8k_item_2_01_candidate_scope`: exactly one Item 2.01; scope begins at the
  last preceding Introductory/Explanatory Note when present and ends at the
  next Item heading;
- `8k_without_item_2_01_scope`: no Item 2.01; the primary document remains
  visible but is not silently treated as common-equity completion evidence;
- `tender_amendment_primary_document`: Schedule TO or 14D-9 amendment;
- `foreign_report_referenced_exhibit_only`: the 6-K primary document names a
  completion exhibit but does not contain the exhibit body; or
- `proxy_material_no_registered_completion_scope`: no registered transaction-
  completion structure in the two DEFA14A primary documents.

Core transaction markers in structured 8-K records are scanned only inside
the bounded transaction scope. Delisting/trading and tender-status markers are
scanned across the primary document. Other forms use their full primary
document.

## Candidate fields

Six fixed marker families retain occurrence counts, at most three bounded
contexts, exact context hashes, and date tokens visible in those contexts:

- cash/stock consideration;
- predecessor, successor, and acquirer;
- suspension and delisting status;
- tender acceptance or expiration;
- transaction completion or closing; and
- transaction effective time.

An absent marker means only `absent_from_primary_document`; it does not prove
event absence. A referenced exhibit is not downloaded or treated as if its
body were present. Full document text is not duplicated into the report.

## Authority

All contexts remain `unresolved_source_candidate_only`. The contract creates
zero security-identity assignments, transaction-completion facts, lifecycle
facts, terminal outcomes, strategy outcomes, `/data` writes, Historical
Coverage writes, research admissions, Candidate writes, publications,
deployments, or scheduler changes. Canonical JSON and owner-only `0700/0400`
custody are mandatory.
