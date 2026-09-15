# ADR 0269: Bound Reconstructed Terminal References with Frozen Gross-Value Intervals

- Status: Accepted
- Date: 2026-09-15

## Context

ADR 0268 permits a clearly disclosed latest-vintage reconstructed research
lane only when every terminal-crossing path has an exact reference or a finite
interval. The corrected terminal census contains 302 five-session crossing
paths. Existing evidence supplies 214 exact daily references; 88 paths across
18 securities previously remained unresolved for reasons including CVR value,
holder election, successor identity, cessation timing, an unlisted unit, and
foreign-listing continuation.

Those unresolved facts are not all necessary to make a conservative research
decision. Contractual cash, maximum CVR proceeds, listed consideration ratios,
and independently read successor closes can support finite gross-value
intervals without pretending to know the realized holder election or eventual
CVR payment. A bounded interval is materially different from a point estimate
and must remain so throughout selection and evaluation.

## Decision

Freeze one outcome-blind terminal-reference policy before any real return is
constructed or performance metric is read.

1. The unit is gross USD reference value per target common share, not a return,
   execution price, option payoff, tax result, or realized holder proceeds.
2. An unresolved long-equity reference uses zero as its conservative lower
   gross-value bound. Zero is a stress endpoint, not a claim that the issuer or
   consideration became worthless.
3. Fixed cash uses the source-stated cash amount as the upper bound. Cash plus
   a CVR uses guaranteed cash plus the source-stated aggregate CVR cap. No CVR
   probability, discount, or expected value is imputed.
4. Listed-equity elections use the greatest gross value among the legally
   stated alternatives, calculated from the frozen ratio and the canonical
   successor close at the registered daily reference boundary. This is an
   upper sensitivity bound, not a claim about election, proration, execution,
   or fractional-share cash.
5. An unlisted unit remains unbounded until an official retained source states
   a reproducible transaction-date or acquisition-accounting value. Marketing,
   names, later private marks without a documented basis, and guessed discounts
   are insufficient.
6. A voluntary migration from a U.S. listing to a continuing foreign listing
   may use the exact last U.S. close only under an explicitly U.S.-venue-scoped
   strategy exit rule and an official retained timetable. It is neither a
   company-termination fact nor a zero terminal value.
7. Evidence retrieved later is labelled latest-vintage retrospective evidence.
   “Frozen before outcomes” means the interval rule and evidence set are fixed
   before this study reads or constructs outcome labels; it does not claim the
   source was available to a historical live system.
8. Missing cases remain `source_evidence_pending`. They may not be dropped,
   point-imputed, or replaced by a ticker heuristic. Development selection and
   later validation must be invariant under adverse assignment of every
   interval endpoint.

## Consequences

The first bounded review converts 63 of the 88 residual paths into finite
intervals using already retained evidence. Twenty-five paths across five
securities remain unbounded pending five exact official documents. The
reconstructed research gate therefore remains blocked and opens no real
labels, parameter selection, validation, holdout, performance claim, Candidate
activation, or Production action.

The remaining sources are available from free official SEC filings; no LSEG or
other named vendor is required for this bounded step. Official availability is
not custody: the files must still pass the existing frozen-plan, private
User-Agent, response-validation, hashing, retention, and adjudication rules
before they can affect the gate. If a source does not prove its named field,
that case remains unbounded.
