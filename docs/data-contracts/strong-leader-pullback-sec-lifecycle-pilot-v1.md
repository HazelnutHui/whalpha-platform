# Strong-Leader Pullback SEC Lifecycle Pilot V1

## Purpose

`strong-leader-pullback-sec-lifecycle-pilot/1.0` inventories official SEC
filing-document locators for the exact ADR 0223 lifecycle sample. It is a
source-acceptance diagnostic, not canonical Lifecycle, a terminal-outcome
ledger, Historical Coverage, or a backtest.

## Inputs and population

The pilot formally rereads and binds:

- the immutable Strong-Leader Pullback source-acceptance sample;
- one immutable SEC Submissions source package; and
- the matching full-payload SEC Submissions census.

All 64 lifecycle cases must have exactly one distinct CIK locator. Every root
member and referenced historical shard must exist and pass structural checks.
A missing case or source member rejects the whole report.

## Candidate rules

Within the census range, a filing is retained as a document candidate when it
is:

- Form 25/25-NSE, Form 15/15F variants, S-4/F-4, merger proxy, tender, 425, or
  related transaction filing;
- an 8-K/8-K-A containing structured item 1.03, 2.01, 3.01, 5.01, or 8.01; or
- a 6-K filed on or after the instrument's last canonical observation.

Each candidate retains CIK, accession, form, filing/acceptance time, document
locator, description, structured items, source member, and date relation to
the last observation and provider delisting candidate. Accession and CIK are
not required to share a numeric prefix.

## Result semantics

The report retains complete per-case candidates plus reconciled form,
category, date-relation, and required-field aggregates. All eight ADR 0223
security-level lifecycle fields remain `unsupported` at the Submissions
metadata layer. A primary-document locator means only that a later bounded
document review is possible.

The report must contain 64 distinct cases and CIKs, a candidate filing for
every case, and at least one candidate on or after every last canonical
observation. Those are structural pilot gates, not claims that every terminal
event has been resolved.

## Custody and authority

One canonical `pilot.json` is written into a new owner-only `build=*` child of
the declared private custody root. Directory/file modes are `0700/0400`; the
write is exclusive, atomic, deterministic, and followed by typed canonical-
byte reread.

Document requests, credentials, stable-security assignments, terminal facts,
strategy triggers, forward outcomes, metrics, parameter choices, `/data`,
Historical Coverage, research admission, Candidate use, publication,
deployment, and scheduler change are fixed to zero or false.
