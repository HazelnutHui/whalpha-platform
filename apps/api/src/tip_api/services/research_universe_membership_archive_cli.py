"""CLI for inspecting or archiving research-only Membership candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tip_api.services.research_universe_membership_archive import (
    archive_research_universe_membership_candidates,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Archive reconstructed Membership into research-only custody."
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--created-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    result = archive_research_universe_membership_candidates(
        data_root=args.data_root,
        candidate_root=args.candidate_root,
        workspace_root=args.workspace_root,
        created_at=args.created_at,
        execute=args.execute,
    )
    print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
    return 1 if result.failed_session_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
