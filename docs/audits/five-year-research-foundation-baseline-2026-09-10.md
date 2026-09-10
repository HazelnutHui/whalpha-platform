# Five-Year Research Foundation Baseline — 2026-09-10

## Outcome

The first ADR 0196 network-disabled census completed against the Dell
application data root. The declared interval is 2021-09-09 through 2026-09-09,
exactly 1,255 XNYS sessions under `exchange-calendars` 4.13.2.

Status is `quarantined`. Neither the price-strategy foundation nor the complete
research-data program is ready. No performance claim is authorized.

Logical fingerprint:
`c19c520f202aacef0dada46cf82e984ccba6b77078d667363eccfcc152a81bfb`.

## Exact session coverage

| Family | Covered | Missing | Observed interval | Evidence tier |
| --- | ---: | ---: | --- | --- |
| EOD Price Bar | 306 | 949 | 2025-06-23–2026-09-09 | mixed |
| Point-in-time Identity | 306 | 949 | 2025-06-23–2026-09-09 | mixed |
| Identity source observation | 304 | 951 | 2025-06-23–2026-09-09 | reconstructed latest vintage |
| Universe Membership | 3 | 1,252 | 2026-09-04–2026-09-09 | as operated |

Identity source custody is absent for 2026-08-13 and 2026-08-19 even though
canonical same-session Identity exists. The census preserves that distinction.

## Sparse and absent families

| Family | Current evidence | Material limitation |
| --- | --- | --- |
| Corporate-action source | 70,099 observations; 28,043 quarantined | bounded outcome-reconciliation query, not complete PIT actions |
| Canonical corporate action | 709 records; 2 quarantined | split-only |
| Adjustment ledger | 101,321 rows; 3,030 quarantined | sparse split-only; neutral omissions and total return unresolved |
| Instrument lifecycle | absent | no canonical family |
| PIT classification | absent | no canonical family |
| PIT fundamentals | absent | no canonical family |
| Historical Coverage Evidence | partial physical evidence | required families not published |
| Historical Coverage | absent | no transitive complete publication |

The 59,892 Membership rows across three sessions do not establish historical
population coverage. Current membership, classification, liquidity, or listing
state will not be projected backward.

## Blocking families

The price-strategy foundation remains blocked by EOD, Identity, Membership,
canonical corporate actions, lifecycle, adjustment ledger, and Historical
Coverage. The complete program additionally remains blocked by point-in-time
classification and fundamentals.

The next bounded stage is an exact Massive Starter depth/pagination pilot for
the oldest required EOD and dated Identity sessions, followed by a deterministic
949-session acquisition plan if entitlement and semantics pass. Lifecycle,
actions, membership, classification, and fundamentals proceed as independent
families so a hard exception cannot hide or block unrelated construction.

## Safety evidence

The successful census made zero external requests, zero canonical writes, and
zero Production writes. It did not read credentials. The administrator entry
point enforced a process-local network socket guard. The application data root
is `/data/trading-intelligence-platform`; passing the parent `/data` correctly
failed closed because it contains no canonical EOD completion index.

