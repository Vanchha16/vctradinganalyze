import { apiGet } from "@/services/api-client";
import type {
  AssetListResponse,
  MarketRegimeResponse,
  SMCAnalysisResponse,
  TechnicalAnalysisResponse,
  Timeframe,
} from "@/services/types";

export function getAssets(): Promise<AssetListResponse> {
  return apiGet<AssetListResponse>("/assets", { limit: "100" });
}

export function getTechnicalAnalysis(symbol: string, timeframe: Timeframe): Promise<TechnicalAnalysisResponse> {
  return apiGet<TechnicalAnalysisResponse>(`/analysis/technical/${symbol}`, { timeframe });
}

export function getSmcAnalysis(symbol: string, timeframe: Timeframe): Promise<SMCAnalysisResponse> {
  return apiGet<SMCAnalysisResponse>(`/analysis/smc/${symbol}`, { timeframe });
}

export function getMarketRegime(symbol: string, timeframe: Timeframe): Promise<MarketRegimeResponse> {
  return apiGet<MarketRegimeResponse>(`/analysis/market-regime/${symbol}`, { timeframe });
}
