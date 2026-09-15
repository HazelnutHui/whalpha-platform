from __future__ import annotations

import hashlib
from datetime import date

import pytest

from tip_api.persistence.quant_research_factor_diagnostics import (
    QuantResearchFactorDiagnosticsPersistenceError,
    factor_diagnostics_bytes,
    read_quant_research_factor_diagnostics,
    write_quant_research_factor_diagnostics,
)
from tip_api.services.quant_research_factor_diagnostics import (
    QuantResearchFactorDiagnosticsAccumulator,
)


def _report():
    accumulator = QuantResearchFactorDiagnosticsAccumulator(
        chronological_plan_fingerprint="1" * 64,
        source_population_fingerprint="2" * 64,
        source_eod_fingerprint="3" * 64,
        source_membership_fingerprint="4" * 64,
        source_action_fingerprint="5" * 64,
        source_adjustment_fingerprint="6" * 64,
        calculation_code_sha256="7" * 64,
        diagnostic_code_sha256="8" * 64,
        limitation_codes=("reconstructed_membership_not_as_operated",),
    )
    accumulator.add_session(as_of_session=date(2026, 1, 2), observations=())
    return accumulator.build()


def test_write_is_owner_only_idempotent_and_formally_reread(tmp_path) -> None:
    custody = tmp_path / "factor-diagnostics"
    custody.mkdir(mode=0o700)
    output = custody / "report=fixture-v1"
    report = _report()

    first = write_quant_research_factor_diagnostics(
        output_root=output,
        output_custody_root=custody,
        report=report,
    )
    repeated = write_quant_research_factor_diagnostics(
        output_root=output,
        output_custody_root=custody,
        report=report,
    )

    assert first == repeated
    assert first.stat().st_mode & 0o777 == 0o400
    assert output.stat().st_mode & 0o777 == 0o700
    assert read_quant_research_factor_diagnostics(
        output_root=output,
        output_custody_root=custody,
    ) == report
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(
        factor_diagnostics_bytes(report)
    ).hexdigest()


def test_existing_different_report_is_rejected(tmp_path) -> None:
    custody = tmp_path / "factor-diagnostics"
    custody.mkdir(mode=0o700)
    output = custody / "report=fixture-v1"
    report = _report()
    write_quant_research_factor_diagnostics(
        output_root=output,
        output_custody_root=custody,
        report=report,
    )
    changed = report.model_copy(
        update={"logical_fingerprint": "9" * 64},
    )

    with pytest.raises(
        QuantResearchFactorDiagnosticsPersistenceError,
        match="existing factor diagnostics differ",
    ):
        write_quant_research_factor_diagnostics(
            output_root=output,
            output_custody_root=custody,
            report=changed,
        )
