from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.services import reconciled_eod_source_reacquisition_cli as module
from tip_api.services.reconciled_eod_source_reacquisition import (
    CONTRACT_VERSION,
    ReconciledEodSourceReacquisitionStoppedError,
)


def _arguments(tmp_path) -> list[str]:
    return [
        "--data-root",
        str(tmp_path / "data"),
        "--package-root",
        str(tmp_path / "packages"),
        "--coverage-path",
        str(tmp_path / "coverage.json"),
        "--coverage-file-sha256",
        "a" * 64,
        "--session-date",
        "2026-07-17",
        "--execute",
    ]


def test_cli_binds_coverage_hash_and_emits_safe_completion(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.setattr(module, "_clean_revision", lambda: "c" * 40)
    monkeypatch.setattr(
        module,
        "read_reconciled_eod_source_coverage",
        lambda **kwargs: SimpleNamespace(
            coverage="sealed",
            observed_hash=kwargs["expected_file_sha256"],
        ),
    )
    monkeypatch.setattr(
        module,
        "load_massive_provider_config_from_file",
        lambda: MassiveProviderConfig(api_key=SecretStr("fixture-secret")),
    )
    observed: dict[str, object] = {}

    def run(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            as_dict=lambda: {
                "contract_version": CONTRACT_VERSION,
                "status": "complete",
                "canonical_data_write_count": 0,
                "production_authority": False,
            }
        )

    monkeypatch.setattr(module, "run_reconciled_eod_source_reacquisition", run)

    assert module.main(_arguments(tmp_path)) == 0

    payload = json.loads(capsys.readouterr().out)
    assert observed["coverage"] == "sealed"
    assert observed["session_dates"] == (date(2026, 7, 17),)
    assert payload["status"] == "complete"
    assert payload["implementation_revision"] == "c" * 40
    assert payload["canonical_data_write_count"] == 0


def test_cli_never_emits_credential_or_provider_response(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.setattr(module, "_clean_revision", lambda: "c" * 40)
    monkeypatch.setattr(
        module,
        "read_reconciled_eod_source_coverage",
        lambda **_kwargs: SimpleNamespace(coverage="sealed"),
    )
    monkeypatch.setattr(
        module,
        "load_massive_provider_config_from_file",
        lambda: MassiveProviderConfig(api_key=SecretStr("fixture-secret")),
    )

    def stopped(**_kwargs) -> object:
        error = ReconciledEodSourceReacquisitionStoppedError(
            failed_session=date(2026, 7, 17),
            failure_code="transport_timeout",
            completed_items=(),
            provider_request_attempt_count=3,
            transient_retry_count=2,
            transient_failure_count=3,
        )
        error.__cause__ = RuntimeError("fixture-secret provider response")
        raise error

    monkeypatch.setattr(
        module,
        "run_reconciled_eod_source_reacquisition",
        stopped,
    )

    assert module.main(_arguments(tmp_path)) == 1

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert captured.out == ""
    assert payload["status"] == "stopped_transient_retries_exhausted"
    assert payload["safe_resume_from_package_custody"] is True
    assert "fixture-secret" not in captured.err
    assert "provider response" not in captured.err
