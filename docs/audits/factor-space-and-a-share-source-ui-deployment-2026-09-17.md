# Factor-Space and A-Share Source UI Deployment — 2026-09-17

## Result

OCI release `2026-09-17T202230Z-566c335817f8` was built from clean source
revision `566c335817f86e60b18548bc6420b85e8caf92e2` and deployed after a clean
dry run. It projects the exactly replayed U.S. factor-space result and the
completed 109/109 A-share source and normalization checkpoint in English,
Chinese, and Spanish.

## Verification

- 3,159 backend tests passed;
- 135 frontend tests passed;
- the Production frontend build passed;
- bundle review reported 64 files, no credential, Parquet, raw-provider, or
  synthetic-demo content;
- remote preflight and Nginx configuration checks passed;
- postflight matched release, source, manifest, bundle, and checksum state;
- Nginx and the localhost-only authentication service are active and enabled;
- protected routes and a bounded guest Session passed;
- guest and credential route policy remains identical;
- no unexpected listener, failed release, staging release, or failed system
  unit remained; and
- credential login and final visual appearance remain manual checks.

## Authority boundary

The deployment changes presentation only. The factor-space result is not
Alpha, the A-share source completion is not Historical Coverage admission, and
no model, Candidate ranking, Validation, Holdout, broker, or trading authority
was opened.
