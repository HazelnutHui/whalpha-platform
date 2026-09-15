# ADR 0277: Establish Cumulative Factor-Discovery Trial Accounting

## Status

Accepted

## Date

2026-09-15

## Context

Factor Discovery V1 consumed Development outcomes for five candidate-Alpha and
three risk-guard hypotheses. All candidate-Alpha hypotheses failed and one
risk guard was retained. A later campaign will be designed with knowledge of
that result, so it is adaptive even when it uses different formulas. Treating
each new batch as statistically fresh would hide research degrees of freedom
and eventually turn bounded campaigns into an unbounded factor search.

The project previously required an append-only trial ledger in prose but did
not yet have a machine-verifiable cumulative record.

## Decision

Create the immutable
`quant-research-discovery-trial-ledger/1.0` contract before registering the
next Factor Discovery campaign.

The first version binds all eight consumed V1 trials to their factor version,
definition fingerprint, role, target, related-factor group, three-session
primary horizon, screening protocol, result report, disposition, and evidence
partition. It records five candidate-Alpha trials, three risk-guard trials,
zero outcome-tested conditioner interactions, zero admitted Alpha factors, and
one retained risk guard. Removing a failure or relabeling its disposition
invalidates the contract.

Strong-Leader Pullback remains a separate strategy-program ledger. It is not
silently recounted as a factor trial, but its consumed Development outcome is
an explicit contamination boundary and may not be used as independent factor
evidence.

Every later outcome-reading Factor Discovery campaign must create a new ledger
version that carries all earlier entries forward and appends its registered
trials before reading outcomes. A consumed campaign is never edited in place.
Factor variants and registered conditioner interactions each count as trials;
renaming or regrouping does not reset the count.

Within-campaign multiplicity correction remains necessary but does not make
successive adaptive campaigns globally independent. Development statistics
are selection evidence only. Any eventual Alpha claim requires a complete
factor-model-expression lineage locked before chronological Validation, one
sealed Holdout, independent reproduction, and prospective shadow evidence.
The cumulative ledger must accompany that lineage so the strength of the
claim reflects the full search history.

The ledger grants no new outcome, Model Construction, Strategy Expression,
Validation, Holdout, Candidate, Product, broker, or execution authority.

## Consequences

- Failed hypotheses remain visible to code and reviewers rather than only to
  narrative history.
- A new campaign cannot present itself as the first attempt after learning
  from V1.
- Campaign-level adjusted probabilities remain useful screens but cannot be
  marketed as globally independent discovery statistics.
- The next campaign must define economically distinct hypotheses and append
  them before any new Development outcome is read.
- Validation and Holdout custody remain unchanged.

## Alternatives considered

### Keep trial history only in audits

Rejected because prose cannot prevent a runner or later task from omitting an
unfavorable attempt.

### Retroactively apply one global p-value correction

Rejected because later campaigns are adaptive and their hypotheses were not
jointly registered before V1 outcomes were seen. The honest remedy is to
retain cumulative selection history and require locked independent evidence.

### Stop all factor research after one failed batch

Rejected because a finite failed campaign is not evidence that all distinct
mechanisms are null. It is evidence against those exact registered
hypotheses.
