# Massive Day Aggregates Flat File Ingestion

## Current state

The fetch-only adapter, raw-source custody, strict CSV normalization, exact
authorization, and offline compatibility with the existing EOD package reader
are implemented and fixture-tested. A live object has not been fetched.

Massive Flat Files use credentials distinct from the REST API key. Obtain the
S3 Access Key ID and Secret Key from the Massive dashboard and place them in an
owner-only file outside Git:

```text
TIP_MASSIVE_FLAT_FILES_ACCESS_KEY_ID=<value>
TIP_MASSIVE_FLAT_FILES_SECRET_ACCESS_KEY=<value>
```

Default path:
`~/.config/trading-intelligence-platform/massive-flat-files.env`.
The file must be owned by the current user, be a regular non-symlink file, and
have mode `0600`. Never paste either value into a task, terminal argument,
repository file, log, or audit.

Install the Dell-only optional dependency through the project environment:

```bash
python -m pip install -e 'apps/api[dev,flat-files]'
```

## One-session pilot

Use 2021-09-09 because Grouped Daily REST denied that required session and the
official Starter Flat File history is expected to cover it. Select an unused
owner-only acquisition-package path in the governed daily workspace or one
direct `/tmp` child.

First run `--review`; copy its exact revision-bound acknowledgement into a
second invocation. The execution may make exactly one S3 request and writes
only the declared acquisition package. It does not write `/data`.

```bash
scripts/admin/fetch-massive-day-aggregate-flat-file.sh \
  --session-date 2021-09-09 \
  --package-path /tmp/whalpha-2021-09-09-acquisition-package \
  --review
```

After successful fetch, formally reread the package and compare its normalized
bars with a date where Grouped Daily REST is also accessible. Validate exact
header, row count, ticker set, OHLCV, transaction count, time semantics, and
unadjusted split behavior before enabling multi-session acquisition.

## Stop rules

Stop the affected Flat File stage on authentication/entitlement denial,
missing object, schema drift, decompression limit, session mismatch, duplicate
ticker, source hash mismatch, normalized-row mismatch, or EOD quality-gate
failure. Record the exact non-sensitive failure class. Do not delete accepted
source evidence or block independent Identity/lifecycle/fundamental work.

The transport reports stable local classes for access denial, missing object,
and unclassified transport failure. Classification consumes only the standard
S3 error code and HTTP status; provider messages, request identifiers, response
bodies, and credentials never enter CLI output or retained evidence.
