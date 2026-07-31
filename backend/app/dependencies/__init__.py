from app.dependencies.auth import get_authentication_service, get_current_user, get_user_service
from app.dependencies.database import get_db
from app.dependencies.market_data import (
    get_asset_repository,
    get_indicator_result_repository,
    get_market_data_providers,
    get_market_data_service,
    get_price_candle_repository,
)
from app.dependencies.market_regime import get_market_regime_engine
from app.dependencies.smc import get_smc_engine
from app.dependencies.technical_analysis import get_technical_analysis_engine

__all__ = [
    "get_asset_repository",
    "get_authentication_service",
    "get_current_user",
    "get_db",
    "get_indicator_result_repository",
    "get_market_data_providers",
    "get_market_data_service",
    "get_market_regime_engine",
    "get_price_candle_repository",
    "get_smc_engine",
    "get_technical_analysis_engine",
    "get_user_service",
]
