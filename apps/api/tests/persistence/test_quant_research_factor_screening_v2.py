from __future__ import annotations

from pathlib import Path

import pytest

from tip_api.persistence.quant_research_factor_screening_v2 import (
    QuantResearchFactorScreeningV2PersistenceError,
    read_quant_research_factor_screening_v2_report,
    write_quant_research_factor_screening_v2_report,
)


def test_v2_factor_screening_custody_rejects_untrusted_parent(tmp_path: Path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o755)

    with pytest.raises(
        QuantResearchFactorScreeningV2PersistenceError,
        match="custody differs",
    ):
        read_quant_research_factor_screening_v2_report(
            output_root=custody / "report=test",
            output_custody_root=custody,
        )


def test_v2_factor_screening_writer_rejects_target_outside_custody(
    tmp_path: Path,
) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)

    with pytest.raises(
        QuantResearchFactorScreeningV2PersistenceError,
        match="custody differs",
    ):
        write_quant_research_factor_screening_v2_report(
            output_root=tmp_path / "report=test",
            output_custody_root=custody,
            report=None,  # type: ignore[arg-type]
        )
