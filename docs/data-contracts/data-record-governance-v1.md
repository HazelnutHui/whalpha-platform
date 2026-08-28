# Data Record Governance V1

## Status

Implemented as immutable Python/Pydantic contracts and an executable standard
family registry. No existing dataset was rewritten or reclassified, and no
provider, `/data`, publication, deployment, or authentication state changed.

## Purpose

This contract provides one vocabulary for governing records across market
data, classification, Universe decisions, corporate actions, analytics,
research, and product publications. It is a crosswalk, not a replacement for
domain-specific contracts.

## Orthogonal dimensions

| Dimension | Question answered |
| --- | --- |
| Data layer | Is this source evidence, a canonical fact, a methodology decision, a derived fact, an analytic result, a signal, an outcome, a product publication, or a coverage manifest? |
| Record disposition | Is this revision accepted, explicitly excluded, quarantined, or superseded? |
| Evidence status | Is the supporting evidence sufficient, insufficient, conflicting, unknown, or inapplicable? |
| Quality status | Did structural/data-quality validation pass, warn, reject, or await review? |
| Coverage status | Is the declared bounded scope complete, partial, missing, unassessed, or inapplicable? |
| Point-in-time eligibility | Was it knowable at the signal cutoff, usable only for later outcome reconciliation, unavailable historically, or inapplicable? |
| Retention class | Is it canonical, append-only event history, sealed research evidence, rebuildable cache, bounded staging, or a raw body that should not be retained? |
| Content scope | Is it shared product content, Dell-internal data, or future user-private data? |
| Web-serving policy | Is shared content eligible for identical Sessions, blocked for all shared Sessions, unassessed, or dependent on a future real user identity? |

The contract deliberately contains no guest-only, member-only, owner-only, or
premium market-analysis state.

## Required invariants

- Accepted records cannot have rejected quality or unresolved evidence.
- Exclusion requires sufficient or inapplicable evidence; omission is not
  exclusion.
- Quarantine requires an explicit reason, unresolved evidence, and non-valid
  quality.
- Superseded revisions name a distinct replacement fingerprint and remain
  retained.
- Signal eligibility requires source availability no later than the sealed
  signal cutoff and excludes quarantined, superseded, rejected, and pending
  records.
- Unknown source availability remains null with a reason and is not signal
  eligible.
- Shared content cannot require a user identity. If it is eligible for web
  serving, guest and credential Sessions receive the same content.
- User-private data requires a future identity-isolation boundary; it is not a
  market-data entitlement tier.
- Internal-only records cannot be directly marked web eligible.

## Standard family registry

`STANDARD_DATA_FAMILY_REGISTRY_V1` currently registers the implemented or
accepted core families: Instrument Master, point-in-time Identity, ticker
resolver, raw EOD, security classification, daily Universe membership,
corporate-action source and canonical facts, lifecycle, adjustment ledger,
Market Regime, Opportunity Candidate, sealed strategy signals, matured stock
outcomes, Dashboard Snapshot, and Historical Coverage.

The executable registry is authoritative for exact family IDs, layers, key
grains, retention classes, and allowed scopes. A new fundamental, valuation,
news/event, options, or portfolio family requires a reviewed registry revision
and its own domain contract; it must not reuse a nearby family by convenience.

## Mapping existing domain states

- Security `unknown`, `ambiguous`, or `malformed` remains domain evidence and
  maps to governance quarantine; it does not become exclusion.
- Universe `included`, `excluded`, and `quarantined` map to record disposition,
  while their reason and evidence fields remain in the Universe contract.
- Corporate-action active/corrected/cancelled state remains event lifecycle;
  unresolved evidence maps separately to governance quarantine.
- Historical `mechanics_only`, `source_incomplete`, `quarantined`, and
  `research_ready` remain bounded readiness outcomes and map primarily to
  coverage, not individual record quality.
- Candidate passed/degraded/quarantined/failed remains analytic quality; it
  does not establish source permission or point-in-time research eligibility.

## Public import path

```python
from tip_api.contracts.data_governance.v1 import (
    STANDARD_DATA_FAMILY_REGISTRY_V1,
    GovernedRecordClassificationV1,
    validate_governance_registry,
)
```

## Current implementation boundary

The registry and validation contracts are covered by synthetic tests. They do
not yet create a governance Parquet family, migration, catalog service, API,
or product payload. Existing datasets remain unchanged. The next physical
family or schema revision must decide where its governance envelope is bound
and how formal readers verify the mapping.
