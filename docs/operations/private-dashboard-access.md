# Private Dashboard Access

## Current boundary

The private static Dashboard uses a branded login page, a localhost-only Auth
Service, Nginx `auth_request`, and opaque in-memory Sessions. Browser-native
Basic Auth is not the user-facing login flow. The existing htpasswd file is
only the server-side credential store for the Auth Service.

The user provisioned the credential outside Codex. Codex may verify safe
metadata and route behavior but must never read or output the password, hash,
cookie, session token, credential file contents, or private key.

## Live verification

On 2026-08-26, a credential-free SSH check verified:

- Nginx and `whalpha-dashboard-auth.service` active and enabled;
- the Auth Service listening only on `127.0.0.1:8010`;
- public `/` returning the data-free branded login page;
- unauthenticated `/dashboard/` redirecting to `/?next=/dashboard/`;
- private data and `/auth/status` returning 401; and
- external `/auth/internal-verify` returning 404.

This does not prove successful authenticated browser login. That remains a
manual user check because Codex does not know or use the password.

## Credential and Session rules

- The password is chosen and entered by the user through a hidden interactive
  prompt; it never enters chat, Git, command arguments, browser storage, logs,
  or repository documentation.
- The server stores only a password hash in the protected credential file.
- The login page sends a same-origin JSON `POST /auth/login` with `username`,
  `password`, and validated `next`; failures are generic and clear the password
  field client-side.
- Sessions are random, opaque, in memory, and expire after seven days.
- The cookie is Secure, HttpOnly, SameSite=Lax, host-only, and scoped to `/`.
- Logout deletes the in-memory Session and clears the cookie.
- Restarting the Auth Service invalidates all Sessions.

## Password rotation

The deployed helper is:

```bash
sudo /srv/whalpha/admin/rotate-whalpha-dashboard-password.sh
sudo /srv/whalpha/admin/rotate-whalpha-dashboard-password.sh --apply
```

The first command is a credential-free dry run. `--apply` requires an
interactive TTY, prompts twice with hidden input, enforces the minimum length,
writes atomically, restarts the Auth Service, and verifies the localhost-only
listener. Never pipe or paste a password through Codex.

Use a unique password from a trusted password manager. If exposure is
suspected, rotate it immediately, invalidate existing Sessions, and review logs
without exposing secret content.

## Scope limit

This Session boundary is accepted for the personal prototype only. Guest access
is not implemented, and this document does not authorize public provider-backed
data, a multi-user role model, Cloudflare Access, or OIDC.
