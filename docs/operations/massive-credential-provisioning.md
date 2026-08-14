# Massive Credential Provisioning

## Purpose

This document records the secure credential boundary for the first Massive Stocks Basic private EOD development credential. It is an operations record, not a credential store.

## Status

Completed and Smoke-Test Verified

## Credential File

The credential file is provisioned outside Git at:

`/home/hui/.config/trading-intelligence-platform/massive.env`

Required metadata:

- owner: `hui:hui`
- mode: `600`
- regular file
- not a symlink
- not readable or writable by group or other

The repository does not contain the credential value, a credential copy, a hash, a fingerprint, or credential-derived metadata.

## Supported Keys

The loader accepts only:

- `TIP_MASSIVE_API_KEY`
- `TIP_MASSIVE_BASE_URL`
- `TIP_MASSIVE_REQUEST_TIMEOUT_SECONDS`

The API key is required. Optional values are validated by `MassiveProviderConfig`.

## Loader Behavior

The loader:

- reads the credential file as plain text
- validates ownership and permissions before parsing
- rejects symlinks
- rejects duplicate keys
- rejects unknown variables
- rejects malformed lines
- rejects `export` syntax
- rejects shell command syntax
- does not use `source`, `eval`, or shell execution
- returns `SecretStr` through `MassiveProviderConfig`
- does not print or log secret values

The credential file path can be overridden by the non-sensitive `TIP_MASSIVE_ENV_FILE` environment variable.

## Smoke-Test Entry

The protected smoke-test entry is:

```bash
scripts/admin/smoke-test-massive-provider.sh
```

The script accepts no API key arguments, supports `--help`, and runs exactly one read-only request through the Python loader and transport.

Smoke-test endpoint:

- provider: Massive
- endpoint: `/v3/reference/tickers`
- parameters: `market=stocks`, `active=true`, `limit=1`
- request count: one
- authentication: Authorization bearer header

The smoke-test output is limited to a safe summary. It does not print headers, raw JSON, ticker records, account identity, request URLs containing credentials, or the API key.

## Verification Record

Last verified: 2026-08-14

Verified results:

- credential file owner and mode were correct
- credential loader parsed the file without exposing the secret
- standard-library HTTPS transport reached the official Massive API host
- one read-only Stocks reference request succeeded
- authentication succeeded
- Stocks reference entitlement was accessible
- no market-data file, database, Parquet file, or ingestion output was created

## Rotation Principle

If the key is rotated, the new value must be provisioned outside Git and outside chat. Do not pass the key through command-line arguments, logs, process titles, shell tracing, documentation, or frontend bundles.

## Non-Goals

- storing credentials in Git
- creating or rotating the API key
- implementing ingestion
- downloading Grouped Daily or Custom Bars data
- writing Parquet or database records
- scheduling requests
- deploying provider-backed data
- selecting private web access control
