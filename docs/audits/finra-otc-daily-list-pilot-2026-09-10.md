# FINRA OTC Daily List Pilot — 2026-09-10

## Purpose

Verify one official/free lifecycle corroboration source before acquiring the
five-year interval. The pilot is source-only and does not modify `/data` or any
analytics, publication, deployment, scheduler, or Production state.

## Official interface evidence

The official metadata endpoint described `OTCDAILYLIST`, `calendarDay` as its
partition field, and 60 typed fields. A bounded public POST using an exact date
filter returned JSON plus `data-version`, record total, record offset, a
5,000-record maximum, and the documented 3-MiB response ceiling. A request
identifier and transport cookies were observed but deliberately not retained.

Sorting was rejected when `calendarDay` used a date-range filter rather than
an equality filter. The implementation therefore does not claim server-side
sorting: it binds page offsets, total records, and one data version instead.
No record order is used for identity or canonical resolution.

## Fixture and live result

Fixture tests covered two-page acquisition, interruption/resume, exact orphan
adoption, date and offset rejection, schema/bounds drift, data-version
retention, and tamper detection. All eight passed before the live package.
The repository-root API regression then passed 2,419 tests with two unchanged
dependency deprecation warnings.

The exact 2021-09-09 package was then retained at the approved owner-only Dell
pilot boundary and formally reread:

- requests: 1;
- records: 51;
- duplicate `OTCDailyListID`: 0;
- event counts: `DA=20`, `DC=12`, `SA=4`, `SC=8`, `SD=7`;
- manifest SHA-256:
  `ca1a49bc335932f44b68c55facfb86378089056cb952a33944aca2ce3cab050d`;
- logical fingerprint:
  `46fd2c963581925c430121dd5e759dd6984bfa7f440b49b82a86020b586a1c44`.

## Decision

The interface is accepted for exact monthly acquisition under the branch-local
decision later adopted by main ADR 0215.
Evidence remains `official_otc_corroboration_only`. The pilot does not prove
major-exchange completeness, historical source-availability time, stable
identity, last tradable session, successor, consideration, or terminal return.
Those unresolved facts remain quarantined and do not block independent source
custody work.
