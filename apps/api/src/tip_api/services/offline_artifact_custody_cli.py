"""Narrow administrator preflight for the persistent serving-bundle root."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tip_api.services.offline_artifact_custody import (
    validate_offline_artifact_location,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serving-bundle-root", required=True, type=Path)
    args = parser.parse_args(argv)
    path = validate_offline_artifact_location(
        args.serving_bundle_root,
        persistent_names={"serving-bundle"},
    )
    print(json.dumps({"path": str(path), "status": "validated"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
