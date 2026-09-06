"""CLI boundary for append-only normalized daily Identity source repair."""

from __future__ import annotations

from tip_api.providers.massive.same_day_catchup import identity_source_main


def main(argv: list[str] | None = None) -> int:
    try:
        return identity_source_main(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2


if __name__ == "__main__":
    raise SystemExit(main())
