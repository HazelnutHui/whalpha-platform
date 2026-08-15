#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import crypt
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs, urlencode

COOKIE_NAME: Final = "__Host-whalpha_session"
SESSION_TTL_SECONDS: Final = 7 * 24 * 60 * 60
MAX_BODY_BYTES: Final = 4096
LOGIN_LIMIT: Final = 5
LOGIN_WINDOW_SECONDS: Final = 60
ALLOWED_USERNAME: Final = "hui"


@dataclass(frozen=True)
class Credential:
    username: str
    password_hash: str


@dataclass
class Session:
    session_id: str
    expires_at: float


class AuthState:
    def __init__(self, credential: Credential, *, now=time.time) -> None:
        self.credential = credential
        self.now = now
        self.sessions: dict[str, Session] = {}
        self.failures: dict[str, list[float]] = {}

    def create_session(self) -> Session:
        self.cleanup_expired()
        token = secrets.token_urlsafe(48)
        session = Session(session_id=token, expires_at=self.now() + SESSION_TTL_SECONDS)
        self.sessions[token] = session
        return session

    def check_session(self, token: str | None) -> bool:
        if not token:
            return False
        session = self.sessions.get(token)
        if session is None:
            return False
        if session.expires_at <= self.now():
            self.sessions.pop(token, None)
            return False
        return True

    def logout(self, token: str | None) -> None:
        if token:
            self.sessions.pop(token, None)

    def cleanup_expired(self) -> None:
        now = self.now()
        for token, session in list(self.sessions.items()):
            if session.expires_at <= now:
                self.sessions.pop(token, None)

    def rate_limited(self, client_id: str) -> bool:
        now = self.now()
        attempts = [item for item in self.failures.get(client_id, []) if item > now - LOGIN_WINDOW_SECONDS]
        self.failures[client_id] = attempts
        return len(attempts) >= LOGIN_LIMIT

    def record_failure(self, client_id: str) -> None:
        attempts = [item for item in self.failures.get(client_id, []) if item > self.now() - LOGIN_WINDOW_SECONDS]
        attempts.append(self.now())
        self.failures[client_id] = attempts


def load_credential(path: Path) -> Credential:
    text = path.read_text(encoding="utf-8")
    records = [line for line in text.splitlines() if line.strip()]
    for line in records:
        if ":" not in line:
            continue
        username, password_hash = line.split(":", 1)
        if username == ALLOWED_USERNAME and password_hash:
            return Credential(username=username, password_hash=password_hash)
    raise RuntimeError("Configured dashboard user was not found")


def verify_password(credential: Credential, username: str, password: str) -> bool:
    if username != credential.username:
        crypt.crypt(password, credential.password_hash)
        return False
    candidate = crypt.crypt(password, credential.password_hash)
    return hmac.compare_digest(candidate, credential.password_hash)


def safe_next(value: str | None) -> str:
    if (
        value
        and value.startswith("/dashboard/")
        and not value.startswith("//")
        and "\\" not in value
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        return value
    return "/dashboard/"


def cookie_header(session: Session) -> str:
    return (
        f"{COOKIE_NAME}={session.session_id}; "
        f"Max-Age={SESSION_TTL_SECONDS}; Path=/; Secure; HttpOnly; SameSite=Lax"
    )


def clear_cookie_header() -> str:
    return f"{COOKIE_NAME}=; Max-Age=0; Path=/; Secure; HttpOnly; SameSite=Lax"


def parse_cookie(header: str | None) -> str | None:
    if not header:
        return None
    for item in header.split(";"):
        if "=" not in item:
            continue
        name, value = item.strip().split("=", 1)
        if name == COOKIE_NAME:
            return value
    return None


def make_handler(state: AuthState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "WhalphaDashboardAuth/1"

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _send_json(self, status: HTTPStatus, payload: dict[str, object], *, cookie: str | None = None) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _redirect(self, location: str, *, cookie: str | None = None) -> None:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()

        def _client_id(self) -> str:
            forwarded = self.headers.get("X-Real-IP") or self.headers.get("X-Forwarded-For")
            return (forwarded or self.client_address[0]).split(",", 1)[0].strip()

        def _same_origin_ok(self) -> bool:
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if origin is None:
                return True
            return origin in {f"https://{host}", f"http://{host}"}

        def _read_form(self) -> dict[str, str]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("invalid body")
            raw = self.rfile.read(length).decode("utf-8", errors="strict")
            parsed = parse_qs(raw, keep_blank_values=True)
            return {key: values[0] for key, values in parsed.items()}

        def _read_json(self) -> dict[str, str]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("invalid body")
            raw = self.rfile.read(length).decode("utf-8", errors="strict")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("invalid body")
            allowed = {"username", "password", "next"}
            if set(payload) - allowed:
                raise ValueError("invalid body")
            result = {}
            for key in allowed:
                value = payload.get(key, "")
                if value is None:
                    value = ""
                if not isinstance(value, str):
                    raise ValueError("invalid body")
                result[key] = value
            return result

        def _is_json_login(self) -> bool:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            return content_type == "application/json"

        def do_GET(self) -> None:
            if self.path == "/check":
                ok = state.check_session(parse_cookie(self.headers.get("Cookie")))
                self._send_json(HTTPStatus.OK if ok else HTTPStatus.UNAUTHORIZED, {"authenticated": ok})
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path.startswith("/login"):
                self._handle_login()
                return
            if self.path == "/logout":
                state.logout(parse_cookie(self.headers.get("Cookie")))
                self._redirect("/login/", cookie=clear_cookie_header())
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def _handle_login(self) -> None:
            wants_json = self._is_json_login()
            if not self._same_origin_ok():
                self._send_json(HTTPStatus.FORBIDDEN, {"error": "invalid_request"})
                return
            client_id = self._client_id()
            if state.rate_limited(client_id):
                if wants_json:
                    self._send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "invalid_credentials"})
                    return
                self._redirect("/login/?error=1")
                return
            try:
                form = self._read_json() if wants_json else self._read_form()
            except Exception:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request"})
                return
            username = form.get("username", "")
            password = form.get("password", "")
            next_url = safe_next(form.get("next"))
            if not verify_password(state.credential, username, password):
                state.record_failure(client_id)
                if wants_json:
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "invalid_credentials"})
                    return
                self._redirect(f"/login/?{urlencode({'error': '1', 'next': next_url})}")
                return
            session = state.create_session()
            if wants_json:
                self._send_json(HTTPStatus.OK, {"authenticated": True, "next": next_url}, cookie=cookie_header(session))
                return
            self._redirect(next_url, cookie=cookie_header(session))

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="WH Alpha private Dashboard session auth service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--htpasswd", type=Path, default=Path("/etc/nginx/auth/whalpha-dashboard.htpasswd"))
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        raise SystemExit("auth service must bind 127.0.0.1")
    state = AuthState(load_credential(args.htpasswd))
    server = HTTPServer((args.host, args.port), make_handler(state))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
