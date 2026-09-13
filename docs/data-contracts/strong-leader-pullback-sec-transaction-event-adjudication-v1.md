# Strong-Leader Pullback SEC Transaction Event Adjudication V1

## Purpose

`strong-leader-pullback-sec-transaction-event-adjudication/1.0` adjudicates
the issuer transaction-completion event and its calendar date for the 61
first-strategy cases whose common-equity identity was already matched to an
in-window Form 8-K cover.

The report is source evidence only. It is not a canonical lifecycle fact,
last-tradable-date decision, terminal return, Historical Coverage admission,
research input, model result, Candidate update, or Production publication.

## Input binding

The network-disabled builder formally rereads and cross-binds:

- the immutable 219-document plan and completed source package;
- the form-aware transaction-candidate package; and
- the point-in-time SEC cover-identity adjudication.

Only the 61 documents with both a registered Item 2.01 transaction structure
and a unique in-window common-equity cover match enter the report. Raw bytes,
normalized-text identity, accessions, instrument IDs, and prior report
fingerprints must agree.

## Bounded transaction scope

The parser combines the introduction and Item 2.01 sections while excluding
intervening Item 1.01, 1.02, and other sections. Sixty documents expose a
named Introductory or Explanatory Note. The one supported implicit
introduction is limited to a pre-item node that contains both a named closing
date and an explicit transaction-completion statement.

The scope deliberately excludes full-document dates such as financing,
agreement, filing, maturity, and historical-reference dates.

## Registered rule order

The first rule producing evidence wins. A selected rule must produce exactly
one unique date; multiple dates are `ambiguous`, and no date is `unsupported`.

1. a calendar date explicitly defined as the transaction `Closing Date` in
   the introduction;
2. an explicit `closing on DATE ... of the merger/transactions` statement;
3. `On DATE` or `Effective on DATE` preceding a registered completion,
   consummation, acquisition, or merger verb in the same semantic statement;
4. a dated tender acceptance followed by an explicit statement that the
   merger was effected.

The inline-XBRL `DocumentPeriodEndDate` is comparison-only. An offer expiry,
agreement date, filing date, or source-reference date is never substituted
for transaction completion.

## Authority boundary

A matched decision has issuer event type
`merger_or_acquisition_completion`, its exact source context, and the relation
between event date and cover report date. It does not by itself establish why
a particular listing terminated, when exchange trading ceased, the effective
delisting date, consideration, acquirer/successor relations, or terminal
return. Those fields require separate typed adjudication.

The canonical JSON report is stored in owner-only `0700/0400` custody and is
bound to code, source, prior evidence, and ruleset fingerprints.
