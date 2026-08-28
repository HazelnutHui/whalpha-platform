from __future__ import annotations

import base64
import crypt
import http.client
import importlib.util
import json
import sys
import threading
from pathlib import Path
from http.server import HTTPServer

import pytest


MODULE_PATH = Path(__file__).resolve().parents[4] / "deploy" / "oci" / "auth" / "whalpha_auth_service.py"
spec = importlib.util.spec_from_file_location("whalpha_auth_service", MODULE_PATH)
assert spec and spec.loader
auth = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = auth
spec.loader.exec_module(auth)


def credential(password: str = "correct-password"):
    return auth.Credential("hui", crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512)))


def test_validates_existing_sha512_crypt_password() -> None:
    cred = credential()
    assert auth.verify_password(cred, "hui", "correct-password")
    assert not auth.verify_password(cred, "hui", "wrong-password")
    assert not auth.verify_password(cred, "other", "correct-password")


def test_safe_next_rejects_open_redirects() -> None:
    assert auth.safe_next("/dashboard/") == "/dashboard/"
    assert auth.safe_next("/dashboard/deep") == "/dashboard/deep"
    assert auth.safe_next("https://example.com/dashboard/") == "/dashboard/"
    assert auth.safe_next("//example.com/dashboard/") == "/dashboard/"
    assert auth.safe_next("/private-data/v1/manifest.json") == "/dashboard/"
    assert auth.safe_next("/auth/logout") == "/dashboard/"
    assert auth.safe_next("/dashboard/\\evil") == "/dashboard/"
    assert auth.safe_next("/dashboard/\n") == "/dashboard/"


def test_session_cookie_flags_and_opacity() -> None:
    state = auth.AuthState(credential(), now=lambda: 1000.0)
    session = state.create_session()
    cookie = auth.cookie_header(session)
    assert cookie.startswith(f"{auth.COOKIE_NAME}=")
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Path=/" in cookie
    token = session.session_id
    assert len(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))) >= 32
    assert "correct-password" not in cookie


def test_expired_session_and_restart_invalidation() -> None:
    clock = {"now": 1000.0}
    state = auth.AuthState(credential(), now=lambda: clock["now"])
    session = state.create_session()
    assert state.check_session(session.session_id)
    clock["now"] += auth.SESSION_TTL_SECONDS + 1
    assert not state.check_session(session.session_id)
    restarted = auth.AuthState(credential(), now=lambda: 1000.0)
    assert not restarted.check_session(session.session_id)


def test_logout_removes_session() -> None:
    state = auth.AuthState(credential(), now=lambda: 1000.0)
    session = state.create_session()
    state.logout(session.session_id)
    assert not state.check_session(session.session_id)


def test_status_endpoint_returns_empty_auth_state() -> None:
    state = auth.AuthState(credential(), now=lambda: 1000.0)
    server, thread = run_server(state)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("GET", "/status", headers={"Host": "whalpha.com"})
        response = conn.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        conn.close()
        assert response.status == 401
        assert body == b""
        assert headers["Cache-Control"] == "private, no-store"

        session = state.create_session()
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("HEAD", "/status", headers={"Host": "whalpha.com", "Cookie": f"{auth.COOKIE_NAME}={session.session_id}"})
        response = conn.getresponse()
        body = response.read()
        conn.close()
        assert response.status == 204
        assert body == b""
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_rate_limit_records_failures() -> None:
    clock = {"now": 1000.0}
    state = auth.AuthState(credential(), now=lambda: clock["now"])
    for _ in range(auth.LOGIN_LIMIT):
        assert not state.rate_limited("client")
        state.record_failure("client")
    assert state.rate_limited("client")
    clock["now"] += auth.LOGIN_WINDOW_SECONDS + 1
    assert not state.rate_limited("client")


def test_guest_rate_limit_is_separate_from_login_failures() -> None:
    clock = {"now": 1000.0}
    state = auth.AuthState(credential(), now=lambda: clock["now"])
    for _ in range(auth.GUEST_LIMIT):
        assert not state.guest_rate_limited("client")
        state.record_guest_request("client")
    assert state.guest_rate_limited("client")
    assert not state.rate_limited("client")
    clock["now"] += auth.GUEST_WINDOW_SECONDS + 1
    assert not state.guest_rate_limited("client")


def test_active_session_count_is_bounded_and_expiry_releases_capacity() -> None:
    clock = {"now": 1000.0}
    state = auth.AuthState(credential(), now=lambda: clock["now"], max_active_sessions=1)
    first = state.create_session()
    with pytest.raises(auth.SessionCapacityError):
        state.create_session()
    clock["now"] = first.expires_at + 1
    replacement = state.create_session()
    assert replacement.session_id != first.session_id
    assert len(state.sessions) == 1


def test_load_credential_accepts_only_configured_user(tmp_path: Path) -> None:
    path = tmp_path / "auth.htpasswd"
    path.write_text(f"other:ignored\nhui:{credential().password_hash}\n", encoding="utf-8")
    loaded = auth.load_credential(path)
    assert loaded.username == "hui"
    assert loaded.password_hash.startswith("$6$")


def run_server(state):
    server = HTTPServer(("127.0.0.1", 0), auth.make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def json_login(server, payload: dict[str, str]):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    body = json.dumps(payload)
    conn.request(
        "POST",
        "/login",
        body=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Host": "whalpha.com",
            "Origin": "https://whalpha.com",
        },
    )
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    headers = dict(response.getheaders())
    conn.close()
    return response.status, headers, json.loads(data)


def json_guest(server, payload: dict[str, str], *, origin: str = "https://whalpha.com"):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    body = json.dumps(payload)
    conn.request(
        "POST",
        "/guest",
        body=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Host": "whalpha.com",
            "Origin": origin,
        },
    )
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    headers = dict(response.getheaders())
    conn.close()
    return response.status, headers, json.loads(data)


def test_json_login_success_sets_cookie_and_returns_safe_next() -> None:
    server, thread = run_server(auth.AuthState(credential(), now=lambda: 1000.0))
    try:
        status, headers, payload = json_login(
            server,
            {"username": "hui", "password": "correct-password", "next": "/dashboard/"},
        )
        assert status == 200
        assert payload == {"authenticated": True, "next": "/dashboard/"}
        cookie = headers["Set-Cookie"]
        assert cookie.startswith(f"{auth.COOKIE_NAME}=")
        assert "HttpOnly" in cookie and "Secure" in cookie
        assert "correct-password" not in cookie
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_json_login_rejects_bad_credentials_without_cookie() -> None:
    server, thread = run_server(auth.AuthState(credential(), now=lambda: 1000.0))
    try:
        status, headers, payload = json_login(
            server,
            {"username": "invalid-test-user", "password": "invalid-test-password", "next": "/dashboard/"},
        )
        assert status == 401
        assert payload == {"error": "invalid_credentials"}
        assert "Set-Cookie" not in headers
        assert "invalid-test-password" not in json.dumps(payload)
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_json_login_rejects_malformed_request_safely() -> None:
    server, thread = run_server(auth.AuthState(credential(), now=lambda: 1000.0))
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request(
            "POST",
            "/login",
            body=json.dumps({"username": "hui", "password": "correct-password", "extra": "nope"}),
            headers={"Content-Type": "application/json", "Host": "whalpha.com"},
        )
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        headers = dict(response.getheaders())
        conn.close()
        assert response.status == 400
        assert payload == {"error": "invalid_request"}
        assert "Set-Cookie" not in headers
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_guest_session_uses_same_opaque_cookie_and_safe_next() -> None:
    state = auth.AuthState(credential(), now=lambda: 1000.0)
    server, thread = run_server(state)
    try:
        status, headers, payload = json_guest(server, {"next": "/dashboard/?view=regime&lang=zh"})
        assert status == 200
        assert payload == {"authenticated": True, "next": "/dashboard/?view=regime&lang=zh"}
        cookie = headers["Set-Cookie"]
        assert cookie.startswith(f"{auth.COOKIE_NAME}=")
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
        token = cookie.split("=", 1)[1].split(";", 1)[0]
        assert state.check_session(token)
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_guest_and_credential_sessions_have_identical_role_free_capability() -> None:
    state = auth.AuthState(credential(), now=lambda: 1000.0)
    server, thread = run_server(state)
    try:
        login_status, login_headers, _ = json_login(
            server,
            {"username": "hui", "password": "correct-password", "next": "/dashboard/"},
        )
        guest_status, guest_headers, _ = json_guest(server, {"next": "/dashboard/"})
        assert login_status == guest_status == 200
        login_token = login_headers["Set-Cookie"].split("=", 1)[1].split(";", 1)[0]
        guest_token = guest_headers["Set-Cookie"].split("=", 1)[1].split(";", 1)[0]
        assert set(vars(state.sessions[login_token])) == set(vars(state.sessions[guest_token])) == {
            "session_id", "expires_at",
        }
        assert state.check_session(login_token) and state.check_session(guest_token)
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_guest_rejects_cross_origin_and_unknown_fields() -> None:
    server, thread = run_server(auth.AuthState(credential(), now=lambda: 1000.0))
    try:
        status, headers, payload = json_guest(server, {"next": "/dashboard/"}, origin="https://evil.example")
        assert status == 403
        assert payload == {"error": "invalid_request"}
        assert "Set-Cookie" not in headers

        status, headers, payload = json_guest(server, {"next": "/dashboard/", "role": "admin"})
        assert status == 400
        assert payload == {"error": "invalid_request"}
        assert "Set-Cookie" not in headers
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_guest_requires_json_content_type() -> None:
    server, thread = run_server(auth.AuthState(credential(), now=lambda: 1000.0))
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request(
            "POST",
            "/guest",
            body='{"next":"/dashboard/"}',
            headers={
                "Content-Type": "text/plain",
                "Host": "whalpha.com",
                "Origin": "https://whalpha.com",
            },
        )
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        headers = dict(response.getheaders())
        conn.close()
        assert response.status == 415
        assert payload == {"error": "invalid_request"}
        assert "Set-Cookie" not in headers
    finally:
        server.shutdown()
        thread.join(timeout=5)
