"""One-request Massive provider smoke test CLI."""

from __future__ import annotations

import sys
from typing import Mapping

from tip_api.providers.massive.credential import MassiveCredentialFileError, load_massive_provider_config_from_file
from tip_api.providers.massive.transport import (
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
    MassiveUrllibTransport,
)

_ENDPOINT = "/v3/reference/tickers"
_PARAMS = {"market": "stocks", "active": True, "limit": 1}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--help"]:
        print("usage: smoke-test-massive-provider.sh")
        print("Runs one read-only Massive Stocks reference request using the protected credential file.")
        return 0
    if args:
        print("error=unsupported-argument", file=sys.stderr)
        return 2
    try:
        config = load_massive_provider_config_from_file()
        response = MassiveUrllibTransport().get_json(
            _ENDPOINT,
            params=_PARAMS,
            api_key=config.api_key,
            timeout_seconds=config.request_timeout_seconds,
            base_url=config.base_url,
        )
        result_count = _result_count(response)
    except MassiveCredentialFileError:
        print("provider=massive")
        print(f"endpoint={_ENDPOINT}")
        print("authenticated=false")
        print("entitlement=not-verified")
        print("request_count=0")
        print("status=credential-boundary-error")
        return 1
    except MassiveTransportResponseError as exc:
        print("provider=massive")
        print(f"endpoint={_ENDPOINT}")
        print(f"authenticated={str(exc.status_code not in {401, 403}).lower()}")
        print("entitlement=not-verified")
        print("request_count=1")
        if exc.status_code == 429:
            print("status=rate-limited")
        elif exc.status_code in {401, 403}:
            print("status=authentication-or-entitlement-failed")
        else:
            print("status=http-error")
        return 1
    except MassiveTransportTimeoutError:
        _print_unavailable("timeout")
        return 1
    except MassiveTransportUnavailableError:
        _print_unavailable("unavailable")
        return 1
    except MassiveTransportDataError:
        print("provider=massive")
        print(f"endpoint={_ENDPOINT}")
        print("authenticated=true")
        print("entitlement=stocks-reference-accessible")
        print("request_count=1")
        print("status=malformed-response")
        return 1

    print("provider=massive")
    print(f"endpoint={_ENDPOINT}")
    print("authenticated=true")
    print("entitlement=stocks-reference-accessible")
    print(f"result_count={result_count}")
    print("request_count=1")
    print("status=ok")
    return 0


def _result_count(response: Mapping[str, object]) -> int:
    results = response.get("results")
    if isinstance(results, list):
        return len(results)
    return 0


def _print_unavailable(status: str) -> None:
    print("provider=massive")
    print(f"endpoint={_ENDPOINT}")
    print("authenticated=false")
    print("entitlement=not-verified")
    print("request_count=1")
    print(f"status={status}")


if __name__ == "__main__":
    raise SystemExit(main())
