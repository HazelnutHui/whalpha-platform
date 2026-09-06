# Universe Membership Knowledge Time V1

## Status

Implemented as an offline immutable assessment contract and formal read-only
CLI. No assessment is published under `/data`.

## Purpose

Separate three timestamps that must not be conflated in end-of-day research:

1. the represented session close, which bounds market information;
2. the time at which all Membership sources and the completed decision ledger
   were actually available;
3. the next XNYS session open, which is the intended entry boundary.

## Eligibility Policy

A Membership partition is `signal_eligible` for a next-open strategy only
when:

- its canonical Identity source manifest says
  `eligible_at_source_observed_at`;
- the source manifest's exact logical fingerprint is present in the
  Membership partition's source lineage;
- `source_data_cutoff` is not earlier than the represented session close;
- both `source_data_cutoff` and `evaluated_at` are strictly earlier than the
  immediate next XNYS session open.

An Identity source marked `outcome_reconciliation_only`, or an evaluation that
does not finish before that open, produces
`outcome_reconciliation_only`. Such evidence remains useful for mechanics and
later outcome reconciliation but cannot enter a no-look-ahead signal
population.

## Bound Evidence

Each assessment binds:

- Membership logical fingerprint;
- Membership manifest and Parquet SHA-256;
- Identity source custody logical fingerprint and contract version;
- represented session, exact close, next session, and exact open;
- source cutoff, evaluation time, and assessment time;
- offline XNYS calendar version;
- eligibility state, reason codes, and assessment fingerprint.

The formal reader rereads and validates both physical data families. The CLI
blocks sockets and reports zero external requests and canonical writes.

## Current Proof

- 2026-09-04 assessment: `signal_eligible`, fingerprint
  `586cde811b9c26496584f56a89f489d6314dbc00e9ed7c112829238dfebdfedf`.
- corrected 2026-09-03 assessment: `outcome_reconciliation_only`, fingerprint
  `be8b100a0bf595d31032220d62325a909fe9488ef060b313a83d8813279463ce`.

These are disconnected read-only assessments. They do not authorize canonical
Membership Apply, Historical Coverage, strategy execution, performance
interpretation, or Production deployment.

## Administrator Entry Point

`scripts/admin/assess-universe-membership-knowledge-time.sh`

The command requires the canonical Dell data root, one exact Membership root
and partition, and an aware UTC assessment time. Temporary Membership roots
must be exact owner-owned mode `0700` paths below `/tmp`.
