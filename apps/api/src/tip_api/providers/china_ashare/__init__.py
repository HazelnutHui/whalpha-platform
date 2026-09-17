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
from tip_api.providers.china_ashare.official_calendar_adapter import (
    CapturedOfficialCalendarNoticeV1,
    OfficialCalendarHttpFetcher,
    OfficialCalendarHttpResponseV1,
    UrllibOfficialCalendarHttpFetcher,
    capture_official_calendar_notice,
)
from tip_api.providers.china_ashare.official_market_mechanics_adapter import (
    CapturedOfficialMarketMechanicsSourceV1,
    OfficialMarketMechanicsHttpFetcher,
    OfficialMarketMechanicsHttpResponseV1,
    UrllibOfficialMarketMechanicsHttpFetcher,
    capture_official_market_mechanics_source,
)
from tip_api.providers.china_ashare.protocol import (
    ChinaAshareDailySourceBatchV1,
    ChinaAshareIdentityBindingV1,
    ChinaAshareInstrumentSourceBatchV1,
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
    "ChinaAshareInstrumentSourceBatchV1",
    "ChinaAshareSourceCapability",
    "ChinaAshareSourceDailyQuery",
    "ChinaAshareSourceInstrumentQuery",
    "ChinaAshareSourceProvider",
    "CapturedOfficialCalendarNoticeV1",
    "CapturedOfficialMarketMechanicsSourceV1",
    "OfficialCalendarHttpFetcher",
    "OfficialCalendarHttpResponseV1",
    "OfficialMarketMechanicsHttpFetcher",
    "OfficialMarketMechanicsHttpResponseV1",
    "TabularResult",
    "UrllibOfficialCalendarHttpFetcher",
    "UrllibOfficialMarketMechanicsHttpFetcher",
    "capture_official_calendar_notice",
    "capture_official_market_mechanics_source",
]
