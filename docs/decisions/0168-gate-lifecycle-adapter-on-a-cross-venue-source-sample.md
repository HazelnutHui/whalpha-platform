# ADR 0168: Gate lifecycle adapter on a cross-venue source sample

- Status: Accepted
- Date: 2026-09-08

## Context

ADR 0167 converts the latest inactive-source shadow into 547 exact review
items without promoting any lifecycle fact. The required evidence is not just
a delisting date. It includes stable listed-security identity, effective date,
last tradable session, terminal classification, conditional successor and
consideration facts, source-availability semantics, and revision history.

Official public documentation shows several plausible sources. Nasdaq Daily
List, NYSE Corporate Actions, and Cboe BZX Listings/Corporate Actions provide
exchange-grade event evidence for their respective listing venues. A
cross-venue source such as LSEG Corporate Actions may reduce adapter and
reconciliation fragmentation. Public product descriptions do not establish
the exact licensed payload, account entitlement, identifier coverage,
availability timestamps, corrections, delivery behavior, retention rights, or
equal-capability derived-display permission that WH Alpha requires.

Implementing an adapter from marketing pages or public field descriptions
would freeze guessed semantics and create code that cannot yet be validated.
Ticker and name cannot close the identity gap, and a last EOD bar cannot by
itself prove the last tradable session.

## Decision

Do not implement or select a lifecycle source adapter until one real,
documented sample and its applicable delivery/license specification have been
reviewed.

Use a cross-venue corporate-action and trading-status product as the preferred
first inquiry/sample route. LSEG is the first candidate to evaluate because
its official public material documents cross-venue coverage, deep history,
corporate actions, trading-status events, and machine-readable delivery. This
is an evaluation order, not source selection, purchase authority, entitlement,
or permission approval.

Retain Nasdaq Daily List, NYSE Corporate Actions/Market Event Feed, and Cboe
BZX Listings/Corporate Actions as official exchange benchmarks and possible
corroborating sources. Do not initially build three exchange-specific
production adapters merely because their specifications are public.

The first real sample review must use a deterministic 30-item diagnostic set
from the exact ADR 0167 queue: for each non-empty
`exchange_locator x effective_year x canonical_observation_gap_class` stratum,
select the earliest and latest candidate ordered by effective date and
`instrument_id`. The current queue has 15 non-empty strata, producing 30
items: six per exchange locator, ten from 2025, and twenty from 2026. The
sample diagnoses semantics and failure modes; it is not a statistical
coverage estimate.

An adapter may become a sole-primary source candidate only if the diagnostic
review establishes all of the following for every item:

- a safe stable-security crosswalk to canonical `instrument_id`, with no
  ticker- or name-only positive match;
- explicit returned/not-covered disposition, without silent omission;
- event type, effective date, status/cancellation, and append-only revision
  semantics;
- a documented source-published or source-available clock distinct from
  provider update and Dell ingestion time;
- last-tradable-session resolution using canonical EOD plus governed
  suspension/trading-status evidence, never the last bar alone; and
- explicit applicability and facts for successor and cash/stock consideration,
  rather than treating missing fields as not applicable.

There is no invented percentage pass threshold. A source that is useful but
cannot meet every sole-primary gate may be classified only as a bounded
corroborator with its missing scopes explicit. A false identity match, silent
omission, fabricated knowledge timestamp, destructive revision, or license
incompatibility rejects the proposed role.

The review must separately confirm Dell acquisition/retention, research use,
equal guest/credential derived display, attribution, redistribution, and
termination/deletion obligations. Raw vendor bodies remain temporary and
owner-only by default unless an approved source-custody contract requires
otherwise.

## Consequences

- The repository does not gain a speculative adapter, request runner, or
  duplicate pilot-planning layer.
- Paid-source evaluation is now the next external dependency for lifecycle
  progress; the user must be shown the exact candidate, price, terms, and
  remaining gaps before purchase or access.
- Exchange feeds remain available for authoritative comparison without forcing
  a fragmented initial production design.
- Same-close research cannot use an event first published after the close; it
  becomes eligible only at the next defensible cutoff.
- The 547 ADR 0167 items remain noncanonical, `first_observed_only`, and
  point-in-time ineligible. No lifecycle, Corporate Action, Historical
  Coverage, research-readiness, analytics, or Production state changes.

