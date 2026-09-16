from __future__ import annotations

import os
from pathlib import Path

import pytest

from tip_api.persistence.quant_research_market_state_qualification import (
    QuantResearchMarketStateQualificationPersistenceError,
    read_quant_research_market_state_qualification_v1,
    write_quant_research_market_state_qualification_v1,
)
from tip_api.contracts.analytics.v1.quant_research_market_state_qualification import (
    market_state_population_fingerprint,
)
from tip_api.services.quant_research_market_state_qualification import (
    build_quant_research_market_state_qualification_v1,
)
from tests.services.test_quant_research_market_state_qualification import (
    _sessions,
)


def test_market_state_qualification_round_trip(tmp_path: Path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    os.chmod(custody, 0o700)
    sessions = _sessions()
    report = build_quant_research_market_state_qualification_v1(
        source_revision="a" * 40,
        source_eod_fingerprint="1" * 64,
        source_membership_fingerprint="2" * 64,
        source_action_fingerprint="3" * 64,
        source_adjustment_fingerprint="4" * 64,
        source_census_fingerprint="5" * 64,
        source_population_fingerprint=market_state_population_fingerprint(sessions),
        calculation_code_sha256="8" * 64,
        sessions=sessions,
        limitation_codes=(
            "close_only_price_state_not_total_return",
            "daily_bars_do_not_observe_intraday_state",
            "historical_classification_unavailable",
            "reconstructed_membership_not_as_operated",
        ),
    )
    output = custody / "report=test"

    path = write_quant_research_market_state_qualification_v1(
        output_root=output,
        output_custody_root=custody,
        report=report,
    )

    assert path.is_file()
    assert read_quant_research_market_state_qualification_v1(
        output_root=output,
        output_custody_root=custody,
    ) == report


def test_market_state_qualification_rejects_non_private_custody(
    tmp_path: Path,
) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o755)
    os.chmod(custody, 0o755)

    with pytest.raises(
        QuantResearchMarketStateQualificationPersistenceError,
        match="custody differs",
    ):
        read_quant_research_market_state_qualification_v1(
            output_root=custody / "report=test",
            output_custody_root=custody,
        )


def test_market_state_qualification_rejects_symlinked_custody(
    tmp_path: Path,
) -> None:
    real_custody = tmp_path / "real-custody"
    real_custody.mkdir(mode=0o700)
    os.chmod(real_custody, 0o700)
    linked_custody = tmp_path / "linked-custody"
    linked_custody.symlink_to(real_custody, target_is_directory=True)

    with pytest.raises(
        QuantResearchMarketStateQualificationPersistenceError,
        match="custody differs",
    ):
        read_quant_research_market_state_qualification_v1(
            output_root=linked_custody / "report=test",
            output_custody_root=linked_custody,
        )
