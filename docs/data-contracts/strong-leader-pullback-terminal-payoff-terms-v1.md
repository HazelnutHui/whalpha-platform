# Strong-Leader Pullback Terminal Payoff Terms V1

## Purpose

`strong-leader-pullback-terminal-payoff-terms/1.0` normalizes exact source
terms needed for terminal-payoff research across the fixed 61-case lifecycle
population.

It is a source-term layer, not a terminal-outcome, return, or lifecycle-fact
publication.

## Inputs and binding

The network-disabled builder formally rereads and binds the common-share
consideration, source-party relation, and trading-cessation reports. Every
case must retain the same stable `instrument_id`, decision sequence, source
fingerprints, consideration structure, and listed-equity flag.

The finite registry must cover exactly 61 reviewed cases. A changed source
literal, structure, input fingerprint, or unregistered case fails closed.

## Normalized terms

Each term retains a unique key, economic kind, exact source literal and span,
source-literal SHA-256, normalized decimal string, and logical fingerprint.
The supported kinds are:

- USD cash per target share;
- listed-equity shares per target share;
- CVR units per target share;
- stated maximum CVR cash per target share; and
- unlisted-equity units per target share.

Cash uses two decimal places. Ratios and units use six. Binary-float input is
never used. Par values, preferred securities, awards, financing, and cash in
lieu of fractional shares cannot become the primary ordinary-share payoff.

Holder elections retain separate alternatives, default treatment, and
proration flags. A source-local listed-equity issuer name is a locator, not an
identity assignment.

## Candidate states and authority

The report distinguishes fixed cash plus matched cessation timing from cases
blocked by timing, listed-security identity/market value, contingent-value
realization, holder election/proration, or an unlisted unit.

All successor and consideration-issuer stable-ID assignments, canonical
lifecycle facts, terminal outcomes, strategy triggers, forward outcomes,
performance metrics, `/data` writes, Historical Coverage writes, research
admissions, Candidate writes, publications, deployments, and scheduler changes
remain zero.

The canonical JSON report is immutable in owner-only `0700/0400` private
custody and binds implementation, ruleset, and every source report.
