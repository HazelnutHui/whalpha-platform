"""Isolated China A-share source-provider boundary."""

from tip_api.providers.china_ashare.akshare_reference_adapter import (
    AKSHARE_ASHARE_REFERENCE_PROVIDER_ID,
    AkshareAshareReferenceAdapter,
    AkshareReferenceModule,
    TabularResult,
)
from tip_api.providers.china_ashare.baostock_adapter import (
    BAOSTOCK_ASHARE_PROVIDER_ID,
    BaoStockAshareSourceAdapter,
    BaoStockCursor,
    BaoStockSession,
)
from tip_api.providers.china_ashare.baostock_session import BaoStockClientSession
from tip_api.providers.china_ashare.protocol import (
    ChinaAshareDailySourceBatchV1,
    ChinaAshareIdentityBindingV1,
    ChinaAshareSourceCapability,
    ChinaAshareSourceDailyQuery,
    ChinaAshareSourceInstrumentQuery,
    ChinaAshareSourceProvider,
)

__all__ = [
    "AKSHARE_ASHARE_REFERENCE_PROVIDER_ID",
    "AkshareAshareReferenceAdapter",
    "AkshareReferenceModule",
    "BAOSTOCK_ASHARE_PROVIDER_ID",
    "BaoStockAshareSourceAdapter",
    "BaoStockClientSession",
    "BaoStockCursor",
    "BaoStockSession",
    "ChinaAshareDailySourceBatchV1",
    "ChinaAshareIdentityBindingV1",
    "ChinaAshareSourceCapability",
    "ChinaAshareSourceDailyQuery",
    "ChinaAshareSourceInstrumentQuery",
    "ChinaAshareSourceProvider",
    "TabularResult",
]
