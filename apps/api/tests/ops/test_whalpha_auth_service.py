from __future__ import annotations

import base64
import crypt
import importlib.util
import sys
from pathlib import Path


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


def test_rate_limit_records_failures() -> None:
    clock = {"now": 1000.0}
    state = auth.AuthState(credential(), now=lambda: clock["now"])
    for _ in range(auth.LOGIN_LIMIT):
        assert not state.rate_limited("client")
        state.record_failure("client")
    assert state.rate_limited("client")
    clock["now"] += auth.LOGIN_WINDOW_SECONDS + 1
    assert not state.rate_limited("client")


def test_load_credential_accepts_only_configured_user(tmp_path: Path) -> None:
    path = tmp_path / "auth.htpasswd"
    path.write_text(f"other:ignored\nhui:{credential().password_hash}\n", encoding="utf-8")
    loaded = auth.load_credential(path)
    assert loaded.username == "hui"
    assert loaded.password_hash.startswith("$6$")
