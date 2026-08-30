# ADR 0101: Bind Current History to a Blocked Pilot Review

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0100 proves that current Dell EOD and Identity bytes can enter the future
Historical Coverage trust chain. The existing pilot planner and approval
review remain pure fixture-driven boundaries: neither has a current-state
adapter that binds the real inventory, exact preceding dates, repository
evidence, and the dated source-permission conclusion into one operator report.

This missing adapter creates two risks. A future task could reuse the old
31-session count without binding the current physical inventory, or it could
mistake a mechanically valid 75-request plan for permission to use Massive.
The dated 2026-08-28 source reviews explicitly conclude that Massive is not
cleared for the guest/credential equal-capability product and that account
entitlement plus complete lifecycle/terminal coverage are unresolved.

Review also found that approval 1.1 required one permission source but did not
require its `source_id` to equal the pilot plan's `provider_id`.

## Decision

Add `current-historical-pilot-baseline/1.0` and a network-prohibited CLI. It
requires a clean Dell `main`, an exact timezone-aware review time, the canonical
data root, and the authoritative repository root. It:

- formally reruns current EOD/Identity mechanics validation;
- binds the full physical inventory fingerprint, file count, and bytes;
- formally counts any existing historical action, lifecycle, membership,
  adjustment, and Coverage partitions;
- chooses exactly the three XNYS sessions preceding the contiguous inventory;
- binds the exact current implementation revision and file-set fingerprints for
  synthetic action mapping and adjustment invariants;
- converts the unchanged dated Massive reviews into a typed, non-authorizing
  `SourcePermissionReviewV1` with their exact repository evidence fingerprint;
- satisfies only the fresh-inventory gate; and
- emits no authorization acknowledgement while account entitlement,
  equal-capability permission, and lifecycle coverage remain unresolved.

The dated permission evidence is fixed to repository-record time
2026-08-28T08:10:57Z, the later Git record containing the combined source
conclusion. Any byte change in the two bound review documents fails closed and
requires an explicit new review instead of silently retaining the old date.

Approval review now also requires
`source_permission_review.source_id == plan.provider_id`. The current plan uses
the real provider identifier `massive_stocks_basic` throughout.

The command is:

```text
scripts/admin/assess-current-historical-pilot-baseline.sh \
  --data-root /data/trading-intelligence-platform \
  --repository-root /home/hui/projects/trading-intelligence-platform \
  --reviewed-at <exact-ISO-8601-time>
```

## Authority Boundary

The report always preserves acquisition, Apply, publication, deployment, and
scheduler authority as false. It performs zero external requests and zero data
writes. It cannot emit an acknowledgement while the current blocked evidence
remains unchanged.

The plan may still describe the bounded hypothetical request scope because
scope review and execution authority are separate facts. Resolving a gate
requires new evidence; it cannot be changed by a command-line flag.

## Real Dell Evidence

The first clean-main run was reviewed at 2026-08-30T17:02:52Z against
implementation revision `017ab5657edaa4bf3bd90ac2437448a7486f7b4b`.

- current mechanics fingerprint:
  `6ef8da023b0b92c96147e9e11f530c361a3c24a23ff4b6c8a39ec38d6bc12228`;
- exact 694-file / 503,568,026-byte inventory fingerprint:
  `b32d70ae94098bf753282ff2eaa89f241bedc469995bfcd2ac97c2568ddb35ca`;
- target sessions: 2026-07-14, 2026-07-15, and 2026-07-16;
- plan fingerprint:
  `ea6faae1d7f5cd3cd80ce349915a8094bc9e78e7e201f72638a06773f4e01899`;
- typed permission-review fingerprint:
  `4294c5e8f56c2f623ac4d9587650e88b21cafb5f7eb6884c93da21c5a09b4dae`;
- final baseline fingerprint:
  `7a8ab595707844fb57f4e64651a9e2db16f16246984a945cce3897ee031d7f28`.

The hypothetical ceiling is 75 serial requests: 3 Grouped Daily, 60 active
All Tickers, 6 inactive All Tickers, 2 Splits, 4 Dividends, and zero Ticker
Events. At the fixed 15-second pace the transport-only floor is 1,125 seconds.

The exact unresolved gates are `account_endpoint_entitlement`,
`equal_capability_source_permission`, and `lifecycle_source_coverage`. All
three source-family permission assessments are `blocked_by_permission`.
Status is `blocked`, acknowledgement is null, and every operational authority
remains false with zero requests and zero writes.

## Consequences

- The next user decision will be based on one exact current report rather than
  an old narrative estimate.
- A source-permission package can no longer be borrowed across provider IDs.
- The current Massive path remains blocked even if its request count is within
  engineering limits.
- A clean committed implementation is required before a real baseline can be
  produced, so the first real evidence is recorded after this decision lands.

## Alternatives Considered

### Ask for pilot authorization immediately

Rejected because the current source and lifecycle gates explicitly fail.

### Treat owner-only computation as a workaround

Rejected because guest and credential Sessions must remain equal-capability,
and the user has not authorized a product-role divergence.

### Reuse any valid source-permission package

Rejected because permission for one source says nothing about another source's
terms, entitlement, or data families.
