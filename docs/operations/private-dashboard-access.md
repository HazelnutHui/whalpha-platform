# Private Dashboard Access

## Purpose

This document records the future credential provisioning boundary for the private Market Dashboard.

## Status

Provisioned by the user outside Codex. Codex verified metadata only.

## V1 Credential Boundary

- Suggested username: `hui`
- The password must be chosen by the user interactively.
- The password must not be sent to ChatGPT/Codex.
- The password must not be placed in shell command arguments.
- The server stores only a password hash.
- The hash must not enter Git, documentation, chat, command history, or logs.
- TLS must be verified before credential use.

## Future Provisioning Pattern

Use an interactive hidden prompt on OCI, then write the htpasswd file with restricted ownership and mode. Exact commands must be reviewed at execution time. Placeholders only:

```bash
# Placeholder pattern only; do not paste real passwords into commands.
read -rsp "Dashboard password: " DASHBOARD_PASSWORD
printf '\n'
# Generate/update htpasswd entry using an approved tool and hidden variable handling.
unset DASHBOARD_PASSWORD
```

The target file for the reviewed Nginx template is:

```text
/etc/nginx/auth/whalpha-dashboard.htpasswd
```

It should be root-owned and mode `640` or stricter, while remaining readable by the Nginx worker according to the final server group policy.

As of the first OCI deployment, the file exists at the reviewed path with owner `root:www-data` and mode `640`. Codex did not read or output the stored hash and did not receive the password.

## Rotation

1. Generate a new password hash interactively.
2. Replace the htpasswd file atomically.
3. Test Nginx config.
4. Reload Nginx only after config test passes.
5. Verify old password no longer works and new password works.
6. Record the operational event without recording the password or hash.

## Revocation

For a single-user prototype, revocation means replacing the password hash and invalidating any shared browser sessions by closing clients. If credentials are suspected exposed, rotate immediately and review access logs without exposing secrets.

## Limitations

Nginx Basic Auth is acceptable only for the personal prototype. A future public or multi-user product should evaluate Cloudflare Access, OIDC, or another formal identity provider.
