# 2026-08-27 EOD Canonical Apply — 2026-08-28

## Authorization and scope

The user explicitly authorized
`AUTHORIZE_2026_08_27_EOD_CANONICAL_APPLY`. Scope was limited to one exact
canonical EOD Apply from the already reviewed plan. It excluded provider
access, analytics calculation, publication, Snapshot, bundle, deployment,
notification, and scheduler work.

## Fail-closed integration correction

The first invocation was rejected before reservation with
`DailyEodReadinessError`. Formal journal reread proved that no
`canonical_apply_started` event, canonical target, provider request, or
`/data` inventory change occurred. The cause was an integration gap: the
coordinator projected ADR 0047 operator-review events into readiness, while
canonical Apply custody's independent recheck projected only attempts.

The minimal correction makes Apply custody project the same immutable reviews.
A regression now covers permanent failure, exact terminal review, bounded
successful retry, and Apply reservation. The focused
readiness/coordinator/capability/custody suite passed 59 tests. The fix was
committed as `6256bf3c92f5babea9c016e2a5b1d3f5d64d6d2b`; it changed neither
readiness policy nor Apply scope.

After canonical postflight, the complete backend suite passed 1,569 tests with
two pre-existing dependency deprecation warnings.

## Exact successful transition

Fresh owner-only controls were bound to `6256bf3` and allowed only
`apply_eod`. The coordinator executed one canonical transition with:

- target session: 2026-08-27
- approved plan SHA-256:
  `76ac1c50a016b82772ce8ac391f8d67e107c8433caae0e1f6364b311deb23bc5`
- expected pre-Apply inventory fingerprint:
  `7d66bc02fe88410a4ed6f000f74875aa135e11d10318ff010a148d03ba08a0de`
- status/reason: `transition_executed` /
  `canonical_stage_completed_and_replanned`
- transition fingerprint:
  `14a9ef9a03f57c64e892994e6f0204544ccdd80ee9a5cd77ed09d83720df11ee`
- external request count: 0
- Production transition count: 1
- publication/deployment/scheduler authorization: false / false / false

## Canonical postflight

The completed 2026-08-27 partition formally contains 9,945 rows and 9,945
unique `instrument_id`/`session_date` business keys. Its manifest reports the
same row count and EOD content fingerprint as the approved plan:

- EOD content fingerprint:
  `5e2338a6fc0e4ccc84b746a324ceed6b7e5e60d06d1561c3490c07855ba2ca87`
- Parquet SHA-256:
  `57cb590c6a8b49970c91fe3b48eadbffc922e08352c3ac339af67f05efa64e72`
- manifest SHA-256:
  `155dfcf5ae34e254cb9ad8f1bca979c7ce4e0ea8e1440e345fe65b3e0063c747`

The session journal now contains 11 events, ends with
`canonical_apply_succeeded`, fingerprint
`aa23faac06e8e49ad505ab0963c4e613581c62dd7187f14c975032756e7756e9`,
and has no unresolved start event.

The canonical root now contains 392 files / 203,931,663 bytes with inventory
fingerprint
`ddbe1ab03d5b945e9c3e2be975218c830f10e1ca615571e9616e131c847c7749`.
There are zero symlinks and zero staging/partial residues. Latest EOD and
Identity are both 2026-08-27 and formally aligned.

The exact next automation action is the offline `calculate_phase1a`. Active
Market Intelligence, Snapshot, Dashboard, and OCI remain on the separately
authorized 2026-08-26 stale-review release. This Apply does not authorize or
imply downstream calculation or serving changes.
