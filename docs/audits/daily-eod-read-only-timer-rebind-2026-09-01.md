# Daily EOD Read-Only Timer Rebind — 2026-09-01

## Authorized change

The exact candidate review fingerprint
`c0748d8bf5d0e3eaac6093404996a53e91e881967717e1c8ed67c5bc78c8d7c6`
was explicitly authorized. The installed user service was rebound from stale
revision `fb96b49f404e4f7abbd11f1822b281acafce7888` to clean Dell `main`
revision `23ae1430c53b4b24d669729c7e104fd3adbe3a89`. The timer bytes were already
identical to the reviewed candidate.

Installed evidence:

- service SHA-256:
  `1e67228cd50c8eea2fcaaffaf269783dc41e54ce1f24f696356fec174073e6f7`;
- timer SHA-256:
  `19347d553ad3300c01a03f56337bd31ee9bd9e0b7e16b05b95b58b983512da0b`;
- both files remained `hui:hui`, mode `0600`, and non-symlinks;
- user manager returned `running`; timer returned `enabled` and active/waiting.

## Controlled verification

After daemon reload and failed-state reset, one manual read-only service start
completed with exit status zero. Plan fingerprint was
`ca336db3db716dd9ae3a27ac91a0568105f1ed30844f0050021e44e9041de189`.
It selected 2026-08-31 as the sole oldest missing session and stopped at
`review_one_transition_wake` with `runtime_verified=true`.

Coordinator calls, credential accesses, external requests, filesystem writes
and Production writes were all zero. No data transition was authorized or run.
