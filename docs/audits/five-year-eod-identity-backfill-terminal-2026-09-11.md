# Five-Year EOD/Identity Backfill Terminal Audit — 2026-09-11

## Scope

This audit records the terminal state of the sole bounded
`whalpha-five-year-backfill-20260911g.service`. It does not authorize a new
provider request, canonical write, corrected-edition build, research run,
publication, or deployment.

## Execution outcome

- The service started from clean source
  `6851d005bd9808d970e49988000223ff4898dd16` at 00:20:35 UTC.
- Eleven complete 20-session batches finished. Their retained results report
  zero transient retries and formally verified EOD and Identity publication.
- Batch 11 completed at 05:13:02 UTC with 1,237 aligned canonical sessions and
  next session 2021-10-04.
- The final partial batch safely advanced canonical EOD through 2021-09-13 and
  canonical Identity through 2021-09-10.
- At 05:35:28 UTC the next Grouped Daily EOD request, for 2021-09-10, returned
  HTTP 403. The process failed closed with status 1; it did not retry a
  permanent response or continue to 2021-09-09.
- The service consumed 4h37m10s of CPU time, reached the fixed 2 GiB cgroup
  memory ceiling without swap, and left no running writer.

The denial is consistent with the independently retained 2026-09-10 exact-date
probe: Grouped Daily REST denied both 2021-09-09 and 2021-09-10, while
point-in-time Tickers remained accessible. Repeating the REST requests cannot
close the price gap.

## Quiescent state

The network-disabled five-year census completed after the writer stopped and
produced logical fingerprint
`c6a49fa8bbe67acb2134f8223fb65f249aeab1022c805320bb63d522c26303fc`.

| Family | Actual state in the 1,255-session evaluation interval |
| --- | --- |
| Canonical EOD | 1,253 sessions; 2021-09-13 through 2026-09-09; missing 2021-09-09 and 2021-09-10 |
| Canonical Identity | 1,254 physical session partitions; 2021-09-10 through 2026-09-09; only 1,253 align to existing EOD; missing 2021-09-09 |
| Identity source observation | 1,251 sessions aligned to the evaluation target; the two prior unbound EOD dates remain 2026-08-13 and 2026-08-19 |
| Research-only plus signal Membership | 303 sessions; 952 evaluation sessions missing |

The evaluation source workspace contains an Identity acquisition package and
Apply plan for 2021-09-10 but no EOD package or plan for that date. It contains
no 2021-09-09 session workspace. Direct post-stop checks found zero symlinks,
zero staging/partial directories under the canonical data root, and no active
historical backfill writer.

## Disposition

1. Do not restart Grouped Daily REST for 2021-09-09 or 2021-09-10.
2. Use the fixture-tested Massive Day Aggregates Flat File path for those two
   EOD dates after the separate dashboard S3 credential is provisioned and one
   non-retaining entitlement/schema pilot passes.
3. Reuse the retained 2021-09-10 Identity evidence; acquire only 2021-09-09
   Identity when its matching EOD source route is ready.
4. Keep the evaluation interval incomplete until both canonical families
   contain all 1,255 sessions and formal readback passes.
5. Only then acquire the separate 20-session warm-up and run formal Reconciled
   EOD Source Coverage.

The legacy count-based planning CLI is capped at 504 sessions and is not a
post-run verifier for this frozen 1,255-session interval. Use the five-year
census and exact-interval execution/readback tools instead.
