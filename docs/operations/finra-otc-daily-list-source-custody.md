# FINRA OTC Daily List Source Custody

## Scope

This runbook acquires official public FINRA OTC Daily List evidence into
owner-only Dell source custody. It does not write `/data`, normalize stable
identity, run analytics, publish, deploy, or change a scheduler.

## Exact five-year boundary

- Support start: 2021-08-11
- Evaluation start: 2021-09-09
- End: 2026-09-09
- Physical partition: one interval per calendar month; the first and last are
  partial months.

Each package must be named
`period=YYYY-MM-DD--YYYY-MM-DD` directly beneath the approved custody root.
The acquisition command refuses a dirty repository, requires `--execute`, and
records the clean implementation revision in progress output.

```bash
cd /home/hui/projects/trading-intelligence-platform/apps/api
PYTHONPATH=src ../../.venv/bin/python -m \
  tip_api.services.finra_otc_daily_list_source_cli \
  --start 2021-09-01 \
  --end 2021-09-30 \
  --custody-root /approved/owner-only/root \
  --package /approved/owner-only/root/period=2021-09-01--2021-09-30 \
  --execute
```

## Stop and resume

There is no automatic HTTP retry. A network, provider, schema, pagination, or
custody error stops the current partition while preserving its sealed pages
and mutable owner-only checkpoint. Reissuing the exact command first rereads
the checkpoint and every page, adopts at most one exact crash-window orphan,
and resumes at the next recorded offset.

Do not delete or edit a partial package to make it pass. Record the stop,
continue unrelated families or later months where safe, and reconcile the
source issue separately. A complete package is always reused after a full
readback and never refetched by default.

## Acceptance

A partition is complete only when:

1. provider row total, data version, and offset chain agree;
2. every source row falls within the exact interval;
3. all 60 requested fields are governed and no unexpected field appears;
4. record, event-code, duplicate-ID, and field-presence counts reconcile;
5. every file is owner-only and its physical hash matches; and
6. the completed checkpoint and manifest formally reread.

Full five-year source custody requires all monthly partitions and a separate
range-level inventory. It remains source evidence; research-ready lifecycle
still requires stable identity, cross-source resolution, availability clocks,
terminal facts, and explicit missingness.

The network-free range reader is:

```bash
PYTHONPATH=apps/api/src .venv/bin/python -m \
  tip_api.services.finra_otc_daily_list_range_census_cli \
  --start 2021-08-11 \
  --end 2026-09-09 \
  --custody-root /approved/owner-only/root
```

Add `--seal` only once after the entire range passes. It writes an immutable
range census and refuses replacement. A later audit uses the reader without
`--seal`; it does not refetch provider data.
