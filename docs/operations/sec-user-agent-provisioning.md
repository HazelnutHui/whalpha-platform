# SEC User-Agent Provisioning

## Boundary

SEC automated access requires a private, descriptive User-Agent containing the project identifier and a contact email. The value is personal configuration and must not be placed in Git, documentation, chat, command arguments, shell history, logs, test output, or deployment bundles.

Expected workstation file:

`/home/hui/.config/trading-intelligence-platform/sec.env`

The only allowed key is `TIP_SEC_USER_AGENT`. The loader does not source or evaluate the file. It requires a regular non-symlink file owned by `hui` with no group/other permissions; mode `600` is recommended and created by the helper.

## Provisioning

Run first in dry-run mode:

```bash
ssh dell5820
cd /home/hui/projects/trading-intelligence-platform
scripts/admin/configure-sec-user-agent.sh
```

Then run the interactive operation only when ready:

```bash
scripts/admin/configure-sec-user-agent.sh --apply
```

Enter a value containing the literal project identifier `trading-intelligence-platform` and a private contact email. The helper requires an interactive TTY, does not echo the value, writes a same-directory mode-600 temporary file, atomically replaces the target, and reports only path, owner, mode, and `configured=true`.

Do not send the value or file contents to Codex. Report only the non-sensitive success or failure summary.

## Phase B2A State

The helper and loader are implemented and fixture-tested. No real value was configured, no SEC request was made, and no live ingestion CLI exists. A separate authorization is required before any bounded Phase B2B network operation.
