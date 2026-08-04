// ---- Auth (docs/04 §Authentication, docs/37_AUTHENTICATION_FLOW.md) ----

export type UserRole =
  | "guest"
  | "registered"
  | "premium"
  | "moderator"
  | "support"
  | "admin"
  | "super_admin";

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  last_login: string | null;
  created_at: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string | null;
  expires_in: number;
}

export type MarketType = "forex" | "metal" | "crypto" | "index";

export type Timeframe = "m1" | "m5" | "m15" | "m30" | "h1" | "h4" | "d1" | "w1" | "mn";

export interface Asset {
  id: string;
  symbol: string;
  name: string;
  market_type: MarketType;
  exchange: string | null;
  base_currency: string | null;
  quote_currency: string | null;
  is_active: boolean;
}

export interface AssetListResponse {
  items: Asset[];
  page: number;
  limit: number;
  total: number;
}

// ---- Technical Analysis ----

export type TrendDirection = "bullish" | "bearish" | "sideways";
export type TrendStrengthLevel = "weak" | "moderate" | "strong" | "very_strong";

export interface ScoreBreakdown {
  trend: number;
  momentum: number;
  oscillator: number;
  volume: number;
  volatility: number;
  support_resistance: number;
  penalties: number;
  total: number;
}

export interface SupportResistanceLevel {
  price: string;
  source: string;
  strength: string;
}

export interface TechnicalAnalysisResponse {
  symbol: string;
  timeframe: Timeframe;
  trend: TrendDirection;
  strength: TrendStrengthLevel;
  technical_score: number;
  score_breakdown: ScoreBreakdown;
  support: SupportResistanceLevel | null;
  resistance: SupportResistanceLevel | null;
  support_levels: SupportResistanceLevel[];
  resistance_levels: SupportResistanceLevel[];
  indicators: Record<string, number>;
  warnings: string[];
  calculated_at: string;
}

// ---- Smart Money Concepts ----

export type MarketStructureState = "bullish" | "bearish" | "range" | "transition";
export type Direction = "bullish" | "bearish";
export type LiquiditySide = "buy_side" | "sell_side";
export type PremiumDiscountPosition = "premium" | "discount" | "equilibrium";
export type SMCEventStatus = string;

export interface SwingClassification {
  kind: string;
  price: string;
  timestamp: string;
  index: number;
}

export interface MarketStructure {
  state: MarketStructureState;
  classifications: SwingClassification[];
}

export interface BOS {
  direction: Direction;
  break_price: string;
  break_time: string;
  strength: number;
  confirmed: boolean;
}

export interface CHOCH {
  previous_trend: MarketStructureState;
  new_trend: MarketStructureState;
  confidence: number;
  confirmation_time: string;
}

export interface OrderBlock {
  direction: Direction;
  zone_high: string;
  zone_low: string;
  created_at: string;
  status: SMCEventStatus;
  touched: boolean;
  mitigated: boolean;
  broken: boolean;
  strength_score: number;
  freshness_score: number;
  volume_confirmed: boolean;
  is_breaker: boolean;
  breaker_confirmed: boolean;
  retest_count: number;
}

export interface FairValueGap {
  direction: Direction;
  gap_high: string;
  gap_low: string;
  created_at: string;
  status: SMCEventStatus;
  gap_size: string;
  priority: string;
}

export interface LiquidityZone {
  side: LiquiditySide;
  level: string;
  touch_count: number;
  status: SMCEventStatus;
  created_at: string;
}

export interface LiquiditySweep {
  side: LiquiditySide;
  level: string;
  sweep_time: string;
  false_breakout: boolean;
}

export interface PremiumDiscount {
  position: PremiumDiscountPosition;
  distance: number;
  range_high: string;
  range_low: string;
  equilibrium: string;
}

export interface Confluence {
  factors: string[];
  confluence_score: number;
}

export interface SMCScoreBreakdown {
  market_structure: number;
  order_blocks: number;
  fair_value_gaps: number;
  liquidity: number;
  premium_discount: number;
  confluence: number;
  penalties: number;
  total: number;
}

export interface SMCAnalysisResponse {
  symbol: string;
  timeframe: Timeframe;
  market_structure: MarketStructure;
  bos: BOS[];
  choch: CHOCH[];
  order_blocks: OrderBlock[];
  fair_value_gaps: FairValueGap[];
  liquidity_zones: LiquidityZone[];
  liquidity_sweeps: LiquiditySweep[];
  premium_discount: PremiumDiscount;
  confluence: Confluence;
  smc_score: number;
  score_breakdown: SMCScoreBreakdown;
  warnings: string[];
  calculated_at: string;
}

// ---- Market Regime ----

export type MarketRegimeState =
  | "trending_bullish"
  | "trending_bearish"
  | "ranging"
  | "accumulation"
  | "distribution"
  | "breakout"
  | "pullback"
  | "reversal"
  | "high_volatility"
  | "low_volatility"
  | "uncertain";

export type VolatilityRegimeState = "very_low" | "low" | "normal" | "high" | "extreme";
export type ExpansionState = "expansion" | "contraction" | "stable";
export type BreakoutDirection = "bullish" | "bearish" | "false_breakout";
export type PullbackDepth = "healthy" | "deep" | "potential_reversal";
export type ReversalDirection = "bullish" | "bearish";

export interface RegimeConfidenceBreakdown {
  trend_clarity: number;
  volatility_clarity: number;
  structural_confirmation: number;
  stability_penalty: number;
  conflict_penalty: number;
  total: number;
}

export interface TrendRegime {
  direction: TrendDirection;
  strength: TrendStrengthLevel;
  structure_state: MarketStructureState;
  aligned: boolean;
}

export interface VolatilityRegime {
  state: VolatilityRegimeState;
  recent_atr_average: number | null;
  baseline_atr_average: number | null;
}

export interface RangeInfo {
  is_ranging: boolean;
  range_width: string | null;
  range_strength: string | null;
}

export interface ExpansionInfo {
  state: ExpansionState;
  ratio: number | null;
}

export interface TransitionInfo {
  shifting: boolean;
  from_hint: MarketRegimeState | null;
  to_hint: MarketRegimeState | null;
  confidence: number;
}

export interface AccumulationDistribution {
  accumulation_score: number;
  distribution_score: number;
}

export interface BreakoutInfo {
  detected: boolean;
  direction: BreakoutDirection | null;
  volume_confirmed: boolean;
}

export interface PullbackReversal {
  pullback_depth: PullbackDepth | null;
  retracement_ratio: number | null;
  reversal_direction: ReversalDirection | null;
  reversal_confidence: number | null;
  exhaustion_warning: string | null;
}

export interface RegimeCandidate {
  regime: MarketRegimeState;
  confidence: number;
  precedence: number;
}

export interface MarketRegimeResponse {
  symbol: string;
  timeframe: Timeframe;
  regime: MarketRegimeState;
  confidence: number;
  confidence_breakdown: RegimeConfidenceBreakdown;
  trend_regime: TrendRegime;
  volatility: VolatilityRegime;
  range: RangeInfo;
  expansion: ExpansionInfo;
  transition: TransitionInfo;
  accumulation_distribution: AccumulationDistribution;
  breakout: BreakoutInfo;
  pullback_reversal: PullbackReversal;
  candidates: RegimeCandidate[];
  warnings: string[];
  calculated_at: string;
}

// ---- Market Data extras (docs/04 §Market Data) ----

export interface LatestCandleResponse {
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface CandleListResponse {
  symbol: string;
  timeframe: Timeframe;
  items: LatestCandleResponse[];
}

export interface IndicatorResultResponse {
  indicator: string;
  value: string;
  metadata: Record<string, unknown> | null;
  calculated_at: string;
}

export interface IndicatorListResponse {
  symbol: string;
  timeframe: Timeframe;
  items: IndicatorResultResponse[];
}

// ---- AI Analysis (docs/04 §AI Analysis, docs/50) ----

export type Recommendation = "buy" | "sell" | "wait";

export interface ReasoningResponse {
  summary: string;
  technical: string;
  smc: string;
  economic: string;
  news: string;
  risk: string;
  conclusion: string;
}

export interface AIAnalysisResponse {
  id: string;
  symbol: string;
  timeframe: Timeframe;
  recommendation: Recommendation;
  confidence_score: number;
  confidence_level: string;
  risk_level: string | null;
  entry_price: string | null;
  stop_loss: string | null;
  take_profit: string | null;
  execution_guidance: string | null;
  reasoning: ReasoningResponse;
  supporting_evidence: string[];
  conflicting_evidence: string[];
  risks: string[];
  invalidation_conditions: string[];
  model_name: string;
  prompt_version: string;
  ai_available: boolean;
  warnings: string[];
  calculated_at: string;
}

export interface AIAnalysisListResponse {
  items: AIAnalysisResponse[];
  page: number;
  limit: number;
  total: number;
}

// ---- Signals (docs/04 §Signals, docs/51) ----

export type SignalType = "buy" | "sell";

export type SignalStatus =
  | "draft"
  | "active"
  | "triggered"
  | "expired"
  | "cancelled"
  | "closed"
  | "successful"
  | "stopped_out";

export interface SignalResponse {
  id: string;
  analysis_id: string;
  symbol: string;
  timeframe: Timeframe;
  signal_type: SignalType;
  entry_price: string;
  stop_loss: string;
  take_profit: string;
  risk_reward: number;
  confidence: number;
  status: SignalStatus;
  triggered_at: string | null;
  closed_at: string | null;
  profit_loss: string | null;
  created_at: string;
}

export interface SignalListResponse {
  items: SignalResponse[];
  page: number;
  limit: number;
  total: number;
}

export interface SignalGenerationResponse {
  analysis_id: string;
  symbol: string;
  timeframe: Timeframe;
  recommendation: Recommendation;
  signal: SignalResponse | null;
}

export interface BookmarkResponse {
  id: string;
  signal_id: string;
  created_at: string;
}

// ---- News (docs/04 §News) ----

export type NewsCategory =
  | "central_bank"
  | "inflation"
  | "employment"
  | "gdp"
  | "interest_rates"
  | "politics"
  | "war"
  | "energy"
  | "commodities"
  | "crypto"
  | "regulation"
  | "corporate_earnings"
  | "breaking_news";

export type NewsImportance = "critical" | "high" | "medium" | "low" | "ignore";

export type NewsSentimentLabel = "very_bullish" | "bullish" | "neutral" | "bearish" | "very_bearish";

export interface NewsArticleListItemResponse {
  id: string;
  source: string;
  title: string;
  summary: string | null;
  category: NewsCategory;
  importance: NewsImportance;
  published_at: string;
  sentiment: NewsSentimentLabel | null;
  confidence: number | null;
}

export interface NewsArticleListResponse {
  items: NewsArticleListItemResponse[];
  page: number;
  limit: number;
  total: number;
}

export interface NewsSentimentDetailResponse {
  sentiment: NewsSentimentLabel;
  confidence: number;
  reason: string;
  affected_assets: string[];
  ai_summary: string | null;
}

export interface NewsArticleDetailResponse {
  id: string;
  source: string;
  title: string;
  summary: string | null;
  content: string | null;
  url: string;
  category: NewsCategory;
  importance: NewsImportance;
  published_at: string;
  sentiment: NewsSentimentDetailResponse | null;
}

// ---- Economic Calendar (docs/04 §Economic Calendar) ----

export type EconomicEventCategory =
  | "inflation"
  | "employment"
  | "growth"
  | "central_bank"
  | "consumer"
  | "housing"
  | "other";

export type EconomicEventImportance = "critical" | "high" | "medium" | "low";

export type EconomicEventStatus = "scheduled" | "released" | "revised" | "cancelled";

export type MarketBias = "potentially_bullish" | "potentially_bearish" | "neutral";

export interface EconomicEventResponse {
  id: string;
  country: string;
  currency: string;
  event_name: string;
  category: EconomicEventCategory;
  importance: EconomicEventImportance;
  forecast: string | null;
  previous: string | null;
  actual: string | null;
  surprise: string | null;
  unit: string | null;
  status: EconomicEventStatus;
  source: string;
  release_time: string;
  risk_window: boolean;
  market_bias: Record<string, MarketBias> | null;
}

export interface EconomicEventListResponse {
  items: EconomicEventResponse[];
  page: number;
  limit: number;
  total: number;
}

export interface EconomicEventUpcomingResponse {
  items: EconomicEventResponse[];
}

// ---- AI Chat (docs/04 §AI Chat, docs/52) ----

export type ConversationStatus = "active" | "archived";

export type MessageRole = "user" | "assistant";

export interface ConversationResponse {
  id: string;
  title: string | null;
  current_symbol: string | null;
  current_timeframe: Timeframe | null;
  status: ConversationStatus;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  symbol: string | null;
  timeframe: Timeframe | null;
  ai_analysis_id: string | null;
  signal_id: string | null;
  model_name: string | null;
  created_at: string;
}

export interface ConversationDetailResponse extends ConversationResponse {
  messages: MessageResponse[];
}

export interface ConversationListResponse {
  items: ConversationResponse[];
  page: number;
  limit: number;
  total: number;
}

export interface CreateConversationRequest {
  symbol?: string;
  timeframe?: Timeframe;
}

export interface SendMessageRequest {
  content: string;
  symbol?: string;
  timeframe?: Timeframe;
}

export interface SendMessageResponse {
  conversation: ConversationResponse;
  user_message: MessageResponse;
  assistant_message: MessageResponse;
  warnings: string[];
}
