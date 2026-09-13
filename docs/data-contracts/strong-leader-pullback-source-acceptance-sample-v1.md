# Strong-Leader Pullback Source Acceptance Sample V1

## Purpose

`strong-leader-pullback-source-acceptance-sample/1.0` is the frozen,
outcome-blind query population for comparing cross-venue corporate-action and
lifecycle sources. It is not a provider result, canonical fact, Historical
Coverage publication, or strategy result.

## Population

The sample must include, without ranking or omission:

- every `history_candidate_unassigned` action exposure in the exact ADR 0221
  blocker census; and
- every lifecycle exposure whose five-session label window crosses its last
  canonical observation.

The initial fixed population is 20 action cases across four candidate stable
IDs and 64 lifecycle cases, with zero overlapping IDs and 68 combined IDs.

## Action case

Each action case preserves the source action ID/revision, ticker locator,
effective date, action type, candidate stable ID, candidate multiplicity,
exact-date failure, retained inactive/FINRA leads, and feature/1/3/5-session
path counts. `stable_identity_assignment_authorized` is always false.

## Lifecycle case

Each lifecycle case preserves the stable ID, source anchors/occurrence hashes,
available FIGI, CIK, ticker, name, exchange and source-type locators, canonical
first/last observed dates, provider delisting-date candidate, included paths,
and 1/3/5-session crossings. `terminal_outcome_authorized` is always false.

All repeated locators are deduplicated and bytewise sorted. Missing required
source occurrence lineage rejects the whole sample.

## Acceptance requirements

The report freezes field-level requirements for action identity/revisions and
lifecycle/terminal outcomes. A later provider result must distinguish matched,
absent, unsupported, and conflicting states for every case. A locator match is
never an assignment, and a missing response is never a neutral fact.

## Custody and non-authority

The output is one canonical JSON report in a new owner-only `build=*` directory
outside `/data`. Directory/file modes are `0700/0400`; creation is exclusive,
atomic, deterministic, and followed by a full formal reread. The report binds
all upstream manifests, its implementation revision, fixed requested fields,
case counts, case fingerprints, and its own logical fingerprint.

Strategy triggers, outcomes, metrics, parameter/cohort selection, stable-ID
assignment, terminal facts, provider requests, credentials, canonical writes,
Historical Coverage, research admission, Candidate writes, publication,
deployment, and scheduler changes are fixed to zero or false.
