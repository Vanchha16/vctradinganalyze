import { apiGet } from "@/services/api-client";
import type {
  Asset,
  AssetListResponse,
  CandleListResponse,
  IndicatorListResponse,
  LatestCandleResponse,
  MarketType,
  Timeframe,
} from "@/services/types";

/**
 * The Markets page's paginated/filtered asset list - distinct from
 * `services/analysis.ts`'s `getAssets()` (a fixed limit:100 fetch used
 * only by the existing dev pages' asset picker), left untouched.
 */
export function listAssets(params: {
  page?: number;
  limit?: number;
  market_type?: MarketType;
  is_active?: boolean;
}): Promise<AssetListResponse> {
  return apiGet<AssetListResponse>("/assets", {
    page: params.page?.toString(),
    limit: (params.limit ?? 20).toString(),
    market_type: params.market_type,
    is_active: params.is_active === undefined ? undefined : String(params.is_active),
  });
}

export function getAssetBySymbol(symbol: string): Promise<Asset> {
  return apiGet<Asset>(`/assets/${symbol}`);
}

export function getLatestCandle(symbol: string, timeframe: Timeframe): Promise<LatestCandleResponse> {
  return apiGet<LatestCandleResponse>(`/market/${symbol}/latest`, { timeframe });
}

export function getCandles(
  symbol: string,
  timeframe: Timeframe,
  params?: { limit?: number },
): Promise<CandleListResponse> {
  return apiGet<CandleListResponse>(`/market/${symbol}/candles`, {
    timeframe,
    limit: (params?.limit ?? 300).toString(),
  });
}

export function getIndicators(
  symbol: string,
  timeframe: Timeframe,
  params?: { indicator?: string; limit?: number },
): Promise<IndicatorListResponse> {
  return apiGet<IndicatorListResponse>(`/market/${symbol}/indicators`, {
    timeframe,
    indicator: params?.indicator,
    limit: (params?.limit ?? 20).toString(),
  });
}
