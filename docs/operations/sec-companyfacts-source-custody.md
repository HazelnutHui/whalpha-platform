# SEC Company Facts Source Custody

## Boundary

This runbook acquires one official Company Facts bulk snapshot into the private
Dell historical-source root. It does not write `/data` or normalize facts.
Run from a clean repository revision with the existing owner-only SEC
User-Agent configuration.

The package name must equal the UTC date in the remote Last-Modified header:

```bash
PYTHONPATH=apps/api/src .venv/bin/python \
  -m tip_api.providers.sec.companyfacts_source_cli \
  --package <approved-root>/snapshot=YYYY-MM-DD \
  --custody-root <approved-root> \
  --execute
```

The CLI reports only source size, hashes, member counts, progress, revision,
and zero-authority fields. It never prints the User-Agent value.

## Stops and recovery

- Remote length, ETag, Last-Modified, range support, status, or Content-Range
  drift stops acquisition.
- A network interruption preserves the partial. A rerun truncates only bytes
  beyond the last bound checkpoint and resumes from that byte.
- If the SEC republishes the archive before resume, do not mix versions. Start
  a new correctly dated package after recording the old partial disposition.
- Unsafe ZIP members, excessive expansion, duplicate CIK files, corruption,
  or unexpected file residue remain isolated for diagnosis.
- A completed orphan is adopted without another network request only after
  every completed-tree invariant passes.

Completion proves source custody and central-directory integrity only. The next
stage must stream every member, validate CRC/JSON, select the five-year filing
range, preserve revisions, and produce a missingness census before any
canonical fundamentals decision.
