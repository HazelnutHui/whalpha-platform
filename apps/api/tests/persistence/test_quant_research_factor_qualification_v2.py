from __future__ import annotations

import os
from pathlib import Path

import pytest

from tip_api.persistence.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationV2PersistenceError,
    _validated_target,
)


def test_v2_qualification_custody_accepts_exact_owner_only_child(tmp_path: Path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    target = custody / "report=test-v2"

    assert _validated_target(target, custody) == (target.absolute(), custody.absolute())


def test_v2_qualification_custody_rejects_group_access(tmp_path: Path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    os.chmod(custody, 0o750)

    with pytest.raises(
        QuantResearchFactorQualificationV2PersistenceError,
        match="custody differs",
    ):
        _validated_target(custody / "report=test-v2", custody)
