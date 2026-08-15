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
- Browser-native Basic Auth is no longer the user-facing login flow.
- The htpasswd file remains the server-side credential store for the local Auth Service.
- Sessions are opaque, random, in-memory, and expire after seven days.
- Service restart invalidates all sessions.
- The session cookie is `Secure`, `HttpOnly`, `SameSite=Lax`, host-only, and path `/`.
- Logout clears the session cookie and deletes the in-memory session.

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

## Login submission contract

The branded login page must submit credentials through JavaScript using a same-origin `POST /auth/login` request with JSON fields `username`, `password`, and `next`. The password must never be placed in the URL, browser storage, logs, or documentation. Failed login attempts return a generic error and clear the password field client-side. Native browser navigation to `/auth/login` is not the intended flow.

## Rotation

Chrome or another password manager warning that a password appeared in a known data breach usually means that password is present in an external breach corpus. It does not by itself prove WH Alpha was breached, but the current Dashboard password must be replaced.

The deployed OCI helper is:

```bash
/srv/whalpha/admin/rotate-whalpha-dashboard-password.sh
```

The user must run it interactively on OCI. Codex must not receive the password.

```bash
sudo /srv/whalpha/admin/rotate-whalpha-dashboard-password.sh
sudo /srv/whalpha/admin/rotate-whalpha-dashboard-password.sh --apply
```

The dry run verifies the target host, auth file, service boundary, and fixed username. The apply flow prompts for the new password twice with hidden input, rejects empty or short passwords, writes a new htpasswd file atomically, restarts the Auth Service, and invalidates all existing in-memory sessions. It does not print the password, password length, hash, cookie, or session token.

Choose a new password that is unique and only used for WH Alpha. The rotation script enforces a hard minimum of 10 characters; longer randomly generated passwords from a trusted password manager are recommended. Do not reuse Google, email, school, IBKR, OCI, Massive, or any other account password. After rotation, update or delete the old `whalpha.com` password in Chrome Password Manager.

## 2026-08-15 Rotation Failure and Repair

The first real `--apply` run accepted hidden user input twice, then failed with:

```text
error: auth service must listen only on 127.0.0.1:8010
```

Safe metadata showed the Auth Service was active and `ss` showed the service listening only on `127.0.0.1:8010`. The failure was in the rotation script, not evidence of a public listener.

Root cause:

- the script restarted the Auth Service and immediately checked listener state once, with no bounded readiness polling;
- the failure path used a helper that exited before the restore branch could complete, so rollback status was not reported clearly.

Metadata showed a backup file from the failed run and the auth file mtime changed during the run, so an atomic replacement likely happened before failure. Because neither old nor new password can be tested or inspected without the user password, the current password version is `unknown` until the user performs one repaired rotation.

The repaired script uses structured listener extraction, bounded readiness polling, explicit rollback status output, and a rollback path that atomically restores from the run backup if post-replacement verification fails.

## Revocation

For a single-user prototype, revocation means replacing the password hash and invalidating any shared browser sessions by closing clients. If credentials are suspected exposed, rotate immediately and review access logs without exposing secrets.

## Limitations

The server-side session Auth Service is acceptable only for the personal prototype. A future public or multi-user product should evaluate Cloudflare Access, OIDC, or another formal identity provider.
