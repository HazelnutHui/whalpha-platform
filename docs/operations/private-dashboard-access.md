# Private Dashboard Access

## Current boundary

The static Dashboard uses a branded entry page, a localhost-only Auth Service,
Nginx `auth_request`, and opaque in-memory Sessions. A visitor may either use
the owner's credential or select guest entry. Both paths create the same
role-free Session and expose the exact same data, functionality, language,
Universe, precision, and analysis. Browser-native Basic Auth is not the
user-facing login flow. The existing htpasswd file is only the server-side
credential store for the credential path.

The user provisioned the credential outside Codex. Codex may verify safe
metadata and route behavior but must never read or output the password, hash,
cookie, session token, credential file contents, or private key.

## Live verification

On 2026-08-26, a credential-free SSH check verified:

- Nginx and `whalpha-dashboard-auth.service` active and enabled;
- the Auth Service listening only on `127.0.0.1:8010`;
- public `/` returning the data-free branded login page;
- unauthenticated `/dashboard/` redirecting to `/?next=/dashboard/`;
- private data and `/auth/status` returning 401;
- external `/auth/internal-verify` returning 404; and
- a temporary guest Session reading both `/dashboard/` and the same protected
  Snapshot 1.5 payload, followed by successful logout and cookie-jar removal.

Guest server-side access is verified. Password-based browser login remains a
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

## Guest entry

- The browser sends a same-origin JSON `POST /auth/guest` containing only the
  validated Dashboard `next` path.
- The endpoint rejects cross-origin requests, unknown fields, oversized or
  malformed bodies, and requests above its bounded rate limit.
- Active Sessions have a fixed memory bound; after expired Sessions are
  removed, a full service returns temporary unavailability rather than growing
  without limit.
- Guest entry does not consume password-login failure allowance and does not
  accept or emit a role, identity, or entitlement.
- The returned cookie is produced by the same Session creation path and passes
  the same Nginx `auth_request` check as credential login.
- `/dashboard/` and `/private-data/` remain inaccessible without one of these
  valid Sessions; guest access is not a second asset route.

## Cumulative guest-entry counter

- After the protected React workspace opens, it sends one same-origin
  `POST /auth/visit` for the current Session.
- A guest Session increments the counter only on its first successful call.
  Refreshes, deployment-created Sessions that never open the workspace, and
  credential Sessions do not increment it.
- The displayed metric is a cumulative guest-entry counter, not unique people,
  page views, or audited audience analytics. Its owner-selected baseline is
  retained in ADR 0285 and is not presented as observed traffic.
- State is one versioned JSON file under the Auth Service's systemd-managed
  state directory. It is written atomically with mode `0600` and is not part of
  an immutable web release or canonical `/data`.
- No IP address, user agent, browser fingerprint, credential, or browsing path
  is retained for this counter.

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

This Session boundary is accepted for the personal prototype only. Equal-
capability guest entry is implemented; public unprotected asset access, a
multi-user role model, per-user private state, Cloudflare Access, and OIDC are
not. Provider licensing must be reassessed before broader promotion or
commercial use.
