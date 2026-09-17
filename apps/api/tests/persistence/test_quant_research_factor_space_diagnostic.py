from __future__ import annotations

import hashlib

import numpy as np
import pytest

from tip_api.contracts.analytics.v1.quant_research_factor_space_diagnostic import (
    FactorSpacePanelKind,
    FactorSpaceSourceBindingV1,
)
from tip_api.persistence.quant_research_factor_space_diagnostic import (
    FactorSpaceDiagnosticPersistenceError,
    factor_space_diagnostic_bytes,
    read_factor_space_diagnostic,
    write_factor_space_diagnostic,
)
from tip_api.services.quant_research_factor_space_diagnostic import (
    build_factor_space_diagnostic_report,
    build_factor_space_panel,
)


def _report():
    x = np.arange(1.0, 41.0)
    security = build_factor_space_panel(
        panel=FactorSpacePanelKind.SECURITY_CROSS_SECTION,
        input_ids=("a", "b"),
        economic_families=("x", "y"),
        values=np.column_stack((x, np.sin(x))),
        group_keys=tuple(f"s{index // 10}" for index in range(40)),
    )
    state = build_factor_space_panel(
        panel=FactorSpacePanelKind.MARKET_STATE_TIME_SERIES,
        input_ids=("c", "d"),
        economic_families=("m", "n"),
        values=np.column_stack((x, np.cos(x))),
    )
    return build_factor_space_diagnostic_report(
        source_bindings=(
            FactorSpaceSourceBindingV1(
                source_name="fixture",
                logical_fingerprint="1" * 64,
            ),
        ),
        security_panel=security,
        market_state_panel=state,
    )


def test_private_report_is_canonical_idempotent_and_rereadable(tmp_path) -> None:
    custody = tmp_path / "factor-space"
    custody.mkdir(mode=0o700)
    target = custody / "report=fixture"
    report = _report()
    first = write_factor_space_diagnostic(
        output_root=target,
        output_custody_root=custody,
        report=report,
    )
    second = write_factor_space_diagnostic(
        output_root=target,
        output_custody_root=custody,
        report=report,
    )
    assert first == second
    assert read_factor_space_diagnostic(
        output_root=target,
        output_custody_root=custody,
    ) == report
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(
        factor_space_diagnostic_bytes(report)
    ).hexdigest()


def test_existing_different_report_is_rejected(tmp_path) -> None:
    custody = tmp_path / "factor-space"
    custody.mkdir(mode=0o700)
    target = custody / "report=fixture"
    report = _report()
    write_factor_space_diagnostic(
        output_root=target,
        output_custody_root=custody,
        report=report,
    )
    changed = report.model_copy(update={"logical_fingerprint": "2" * 64})
    with pytest.raises(FactorSpaceDiagnosticPersistenceError):
        write_factor_space_diagnostic(
            output_root=target,
            output_custody_root=custody,
            report=changed,
        )
