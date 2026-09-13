# SEC Submissions Source Custody

## Boundary

Acquire the official nightly Submissions archive into the private Dell
historical-source root from a clean revision. The operation uses the existing
owner-only SEC User-Agent, never prints or retains it, and writes no `/data`,
analytics, Product, Production, or scheduler state.

The target package date must equal the remote Last-Modified UTC date:

```bash
PYTHONPATH=apps/api/src .venv/bin/python \
  -m tip_api.providers.sec.submissions_source_cli \
  --package <approved-root>/snapshot=YYYY-MM-DD \
  --custody-root <approved-root> \
  --execute
```

Progress output contains only chunk ordinal, committed/total bytes, clean
revision, and zero-authority fields. The formal completion record adds only
source size, hashes, member counts, and fingerprints.

## Stops and recovery

- Object length, ETag, Last-Modified, content type, range support, response
  range, or hash drift stops acquisition.
- Resume rereads and hashes all committed chunks, truncates an unbound tail,
  and obtains a fresh HEAD. A changed nightly object is never appended.
- Unsafe/duplicate CIK members, unsupported compression, excessive member or
  expansion size, unexpected file residue, mode drift, or hash mismatch stop
  publication.
- A completed orphan is adopted only after the same full package reader used
  for ordinary completed custody passes.

Completion proves immutable source and central-directory custody only. The
next stage must fully read every member and measure acceptance-time coverage
  against the Company Facts five-year accession population across both root
  and older per-filer shard members.
