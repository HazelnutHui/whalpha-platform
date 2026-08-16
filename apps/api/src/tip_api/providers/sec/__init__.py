"""SEC evidence boundaries. This package performs no import-time I/O."""

from tip_api.providers.sec.config import SEC_USER_AGENT_ENV, SecProviderConfig
from tip_api.providers.sec.credential import load_sec_provider_config_from_file
from tip_api.providers.sec.transport import SecRateLimiter, SecRetryPolicy, SecTransport

__all__ = [
    "SEC_USER_AGENT_ENV",
    "SecProviderConfig",
    "SecRateLimiter",
    "SecRetryPolicy",
    "SecTransport",
    "load_sec_provider_config_from_file",
]
