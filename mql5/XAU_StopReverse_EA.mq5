//+------------------------------------------------------------------+
//|                                           XAU_StopReverse_EA.mq5 |
//|                                                                  |
//|  Stop-and-Reverse trailing manager for XAUUSD (M1).              |
//|                                                                  |
//|  Reproduces the behaviour observed in the reference screen        |
//|  recording: exactly ONE open position at all times, protected by  |
//|  ONE opposite pending STOP order. The stop starts at a fixed      |
//|  distance from entry, trails behind price once in profit, and     |
//|  when it fills it closes the old position and reverses direction. |
//|                                                                  |
//|  This is NOT a two-sided straddle. See documentation.             |
//+------------------------------------------------------------------+
#property copyright "Vanchha"
#property link      ""
#property version   "2.00"
#property description "Stop-and-reverse trailing EA for XAUUSD M1. One position + one opposite trailing stop order. Always in the market."

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\OrderInfo.mqh>

//+------------------------------------------------------------------+
//| Enumerations                                                     |
//+------------------------------------------------------------------+
enum ENUM_SEED_DIRECTION
  {
   SEED_NONE      = 0,  // Do not open the first trade automatically
   SEED_BUY       = 1,  // Seed with a BUY
   SEED_SELL      = 2,  // Seed with a SELL
   SEED_LAST_BAR  = 3   // Follow the direction of the last closed M1 bar
  };

enum ENUM_TRAIL_ANCHOR
  {
   ANCHOR_CLOSE_PRICE = 0, // Anchor trail to the price the position closes at (Bid for buy / Ask for sell)
   ANCHOR_MID_PRICE   = 1  // Anchor trail to the mid price
  };

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input group "=== Volume ==="
input double              LotSize                  = 0.01;      // LotSize (fixed, per side)

input group "=== Stop-and-reverse geometry (POINTS) ==="
input int                 InitialStopPoints        = 70;        // Distance of the reverse stop from ENTRY when a position opens
input int                 TrailingStopPoints       = 45;        // Trail distance behind price once profitable
input int                 TrailStartPoints         = 10;        // Profit needed before trailing begins
input int                 TrailingStepPoints       = 5;         // Minimum improvement before sending a modify
input ENUM_TRAIL_ANCHOR   TrailAnchor              = ANCHOR_CLOSE_PRICE; // What the trail measures from
input bool                TrailOnBarCloseOnly      = false;     // Update the trail only once per M1 bar

input group "=== Reversal behaviour ==="
input bool                EnableReversal           = true;      // When the stop fills, open the opposite side (SAR)
input bool                CloseOppositeOnFill      = true;      // Close the old position when the reverse stop fills (hedging accounts)
input ENUM_SEED_DIRECTION SeedDirection            = SEED_NONE; // How to open the very first position
input bool                EnableBuy                = true;      // Allow long positions
input bool                EnableSell               = true;      // Allow short positions

input group "=== Optional profit target (not seen in the video) ==="
input int                 TakeProfitPoints         = 0;         // 0 = none. Video showed no TP.
input int                 HardStopLossPoints       = 0;         // 0 = none. The reverse stop is the real stop.

input group "=== Execution safety ==="
input int                 MaxSpreadPoints          = 25;        // Blocks new orders above this spread
input ulong               Slippage                 = 20;        // Deviation in points
input ulong               MagicNumber              = 20260814;  // MagicNumber
input int                 MinSecondsBetweenTrades  = 2;         // Cooldown to stop reversal storms
input int                 MaxReversalsPerDay       = 0;         // 0 = unlimited
input double              MaxDailyLossCurrency     = 0.0;      // 0 = disabled. Today's realised loss (account currency) that flattens and stops trading

input group "=== Session filter ==="
input bool                TradeOnlyDuringSpecifiedHours = false; // Restrict to a session (server time)
input int                 StartHour                = 8;         // StartHour (0-23)
input int                 EndHour                  = 20;        // EndHour (0-23, exclusive)
input bool                CloseAllAtSessionEnd     = false;      // Flatten when the session closes

input group "=== News filter (manual windows, server time) ==="
input bool                AllowNewsTrading         = true;      // Continue trading inside news windows
input string              NewsTimesCSV             = "";        // "HH:MM,HH:MM" server time
input int                 NewsMinutesBefore        = 15;        // Blackout minutes before
input int                 NewsMinutesAfter         = 15;        // Blackout minutes after
input int                 MaximumSpreadDuringNews  = 60;        // Spread cap used inside a news window

input group "=== Display ==="
input bool                ShowChartObjects         = true;      // Draw levels and info panel
input int                 PanelXOffset             = 12;
input int                 PanelYOffset             = 20;
input color               BuyColor                 = clrDodgerBlue;
input color               SellColor                = clrOrangeRed;
input color               PanelTextColor           = clrWhiteSmoke;
input string              OrderComment             = "XAU_SAR";

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
CTrade   trade;

string   g_prefix        = "";
double   g_point         = 0.0;
double   g_tickSize      = 0.0;
int      g_digits        = 0;
int      g_stopsLevel    = 0;
int      g_freezeLevel   = 0;
double   g_volMin        = 0.0;
double   g_volMax        = 0.0;
double   g_volStep       = 0.0;
double   g_contractSize  = 0.0;
double   g_tradeLot      = 0.0;
bool     g_isHedging     = false;

// current state, refreshed each tick
ulong             g_posTicket    = 0;
ENUM_POSITION_TYPE g_posType     = POSITION_TYPE_BUY;
double            g_posEntry     = 0.0;
double            g_posVolume    = 0.0;
double            g_posProfit    = 0.0;
bool              g_hasPosition  = false;

ulong    g_stopTicket    = 0;
double   g_stopPrice     = 0.0;
ENUM_ORDER_TYPE g_stopType = ORDER_TYPE_BUY_STOP;
bool     g_hasStop       = false;

datetime g_lastTradeTime = 0;
datetime g_lastBarTime   = 0;
datetime g_lastBlockLog  = 0;
int      g_reversalsToday = 0;
int      g_todayDay      = -1;
bool     g_dailyLossHit  = false;
datetime g_lastRetryLog  = 0;
string   g_statusText    = "starting";

int      g_newsHour[];
int      g_newsMinute[];

//+------------------------------------------------------------------+
//| Small helpers                                                    |
//+------------------------------------------------------------------+
double Ask() { return SymbolInfoDouble(_Symbol, SYMBOL_ASK); }
double Bid() { return SymbolInfoDouble(_Symbol, SYMBOL_BID); }

int SpreadPoints()
  {
   if(g_point <= 0.0)
      return 0;
   return (int)MathRound((Ask() - Bid()) / g_point);
  }

double NormalizePrice(const double price)
  {
   double ts = (g_tickSize > 0.0 ? g_tickSize : g_point);
   if(ts <= 0.0)
      return NormalizeDouble(price, g_digits);
   return NormalizeDouble(MathRound(price / ts) * ts, g_digits);
  }

double NormalizeVolume(const double volume)
  {
   double v = volume;
   if(g_volStep > 0.0)
      v = MathRound(v / g_volStep) * g_volStep;
   if(v < g_volMin)
      v = g_volMin;
   if(v > g_volMax)
      v = g_volMax;

   int volDigits = 0;
   double step = (g_volStep > 0.0 ? g_volStep : 0.01);
   while(step < 1.0 && volDigits < 8)
     {
      step *= 10.0;
      volDigits++;
     }
   return NormalizeDouble(v, volDigits);
  }

int MinDistancePoints()
  {
   int d = g_stopsLevel;
   int s = SpreadPoints();
   if(d < s)
      d = s;
   if(d < 1)
      d = 1;
   return d;
  }

//+------------------------------------------------------------------+
//| Trade result checking and logging                                |
//+------------------------------------------------------------------+
bool LogTradeResult(const string context, const bool sent)
  {
   uint   rc   = trade.ResultRetcode();
   string desc = trade.ResultRetcodeDescription();

   bool good = (sent && (rc == TRADE_RETCODE_DONE ||
                         rc == TRADE_RETCODE_PLACED ||
                         rc == TRADE_RETCODE_DONE_PARTIAL));
   if(!good)
     {
      PrintFormat("[EA] Trade error: %s | retcode=%u (%s) | order=%I64u deal=%I64u",
                  context, rc, desc, trade.ResultOrder(), trade.ResultDeal());
      return false;
     }

   PrintFormat("[EA] %s | retcode=%u (%s) | order=%I64u price=%s volume=%.2f",
               context, rc, desc, trade.ResultOrder(),
               DoubleToString(trade.ResultPrice(), g_digits), trade.ResultVolume());
   return true;
  }

//+------------------------------------------------------------------+
//| News window parsing                                              |
//+------------------------------------------------------------------+
void ParseNewsTimes()
  {
   ArrayFree(g_newsHour);
   ArrayFree(g_newsMinute);

   string csv = NewsTimesCSV;
   StringTrimLeft(csv);
   StringTrimRight(csv);
   if(StringLen(csv) == 0)
      return;

   string parts[];
   int n = StringSplit(csv, ',', parts);
   for(int i = 0; i < n; i++)
     {
      string item = parts[i];
      StringTrimLeft(item);
      StringTrimRight(item);
      if(StringLen(item) == 0)
         continue;

      string hm[];
      if(StringSplit(item, ':', hm) != 2)
        {
         PrintFormat("[EA] News time ignored (bad format): %s", item);
         continue;
        }
      int hh = (int)StringToInteger(hm[0]);
      int mm = (int)StringToInteger(hm[1]);
      if(hh < 0 || hh > 23 || mm < 0 || mm > 59)
        {
         PrintFormat("[EA] News time ignored (out of range): %s", item);
         continue;
        }
      int sz = ArraySize(g_newsHour);
      ArrayResize(g_newsHour,   sz + 1);
      ArrayResize(g_newsMinute, sz + 1);
      g_newsHour[sz]   = hh;
      g_newsMinute[sz] = mm;
     }
   PrintFormat("[EA] News windows loaded: %d", ArraySize(g_newsHour));
  }

bool IsInsideNewsWindow()
  {
   int count = ArraySize(g_newsHour);
   if(count == 0)
      return false;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int nowMinutes = dt.hour * 60 + dt.min;

   for(int i = 0; i < count; i++)
     {
      int ev   = g_newsHour[i] * 60 + g_newsMinute[i];
      int from = ev - NewsMinutesBefore;
      int to   = ev + NewsMinutesAfter;

      // A window can cross midnight in EITHER direction. The old code
      // wrapped only when `from` went negative, so a 23:55 event lost its
      // minutes-after blackout. Test the window shifted a day each way.
      for(int shift = -1440; shift <= 1440; shift += 1440)
        {
         if(nowMinutes >= from + shift && nowMinutes <= to + shift)
            return true;
        }
     }
   return false;
  }

bool IsInsideTradingHours()
  {
   if(!TradeOnlyDuringSpecifiedHours)
      return true;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int h = dt.hour;

   if(StartHour == EndHour)
      return true;
   if(StartHour < EndHour)
      return (h >= StartHour && h < EndHour);
   return (h >= StartHour || h < EndHour);
  }

//+------------------------------------------------------------------+
//| Daily reversal counter                                           |
//+------------------------------------------------------------------+
void RollDailyCounter()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   // day_of_year, not day: dt.day alone makes the 16th of one month look
   // identical to the 16th of the next, so the counter never resets.
   if(dt.day_of_year != g_todayDay)
     {
      g_todayDay       = dt.day_of_year;
      g_reversalsToday = 0;
      g_dailyLossHit   = false;
     }
  }

//+------------------------------------------------------------------+
//| Realised profit/loss booked today by this EA (account currency)  |
//| Read from history rather than accumulated, so it survives a      |
//| terminal restart or a re-attach part-way through the day.        |
//+------------------------------------------------------------------+
double RealisedProfitToday()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0;
   dt.min  = 0;
   dt.sec  = 0;
   datetime dayStart = StructToTime(dt);

   if(!HistorySelect(dayStart, TimeCurrent() + 3600))
      return 0.0;

   double total = 0.0;
   int    deals = HistoryDealsTotal();
   for(int i = 0; i < deals; i++)
     {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0)
         continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL) != _Symbol)
         continue;
      if((ulong)HistoryDealGetInteger(ticket, DEAL_MAGIC) != MagicNumber)
         continue;
      // Opening deals book no result; only exits carry profit.
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY) == DEAL_ENTRY_IN)
         continue;

      total += HistoryDealGetDouble(ticket, DEAL_PROFIT)
               + HistoryDealGetDouble(ticket, DEAL_SWAP)
               + HistoryDealGetDouble(ticket, DEAL_COMMISSION);
     }
   return total;
  }

//+------------------------------------------------------------------+
//| Margin check                                                     |
//+------------------------------------------------------------------+
bool HasEnoughMargin(const ENUM_ORDER_TYPE type, const double volume, const double price)
  {
   double required = 0.0;
   if(!OrderCalcMargin(type, _Symbol, volume, price, required))
     {
      PrintFormat("[EA] Margin check failed: OrderCalcMargin error %d", GetLastError());
      return false;
     }
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(required > freeMargin)
     {
      PrintFormat("[EA] Margin check failed: required=%.2f free=%.2f", required, freeMargin);
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Global trading conditions                                        |
//+------------------------------------------------------------------+
bool ValidateTradingConditions(string &reason)
  {
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
     { reason = "terminal: algo trading disabled"; return false; }
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
     { reason = "EA: trading not allowed"; return false; }
   if(!AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
     { reason = "account: expert trading disabled"; return false; }
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
     { reason = "account: trading disabled"; return false; }

   long tradeMode = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE);
   if(tradeMode == SYMBOL_TRADE_MODE_DISABLED)
     { reason = "symbol: trading disabled"; return false; }
   if(tradeMode == SYMBOL_TRADE_MODE_CLOSEONLY)
     { reason = "symbol: close only"; return false; }

   if(Bid() <= 0.0 || Ask() <= 0.0)
     { reason = "no valid quotes yet"; return false; }

   if(!IsInsideTradingHours())
     { reason = "outside configured trading hours"; return false; }

   bool newsNow = IsInsideNewsWindow();
   int  spreadLimit = MaxSpreadPoints;
   if(newsNow)
     {
      if(!AllowNewsTrading)
        { reason = "news window: new orders blocked"; return false; }
      spreadLimit = MaximumSpreadDuringNews;
     }

   int spread = SpreadPoints();
   if(spreadLimit > 0 && spread > spreadLimit)
     {
      reason = StringFormat("spread %d > limit %d", spread, spreadLimit);
      return false;
     }

   if(MinSecondsBetweenTrades > 0 &&
      (TimeCurrent() - g_lastTradeTime) < MinSecondsBetweenTrades)
     { reason = "cooldown between trades"; return false; }

   RollDailyCounter();
   if(MaxReversalsPerDay > 0 && g_reversalsToday >= MaxReversalsPerDay)
     { reason = "daily reversal limit reached"; return false; }

   if(MaxDailyLossCurrency > 0.0)
     {
      double realised = RealisedProfitToday();
      if(realised <= -MathAbs(MaxDailyLossCurrency))
        {
         g_dailyLossHit = true;
         reason = StringFormat("daily loss limit reached (%.2f %s)",
                               realised, AccountInfoString(ACCOUNT_CURRENCY));
         return false;
        }
     }

   return true;
  }

//+------------------------------------------------------------------+
//| State refresh: this EA's position                                |
//+------------------------------------------------------------------+
void CheckExistingPositions()
  {
   g_hasPosition = false;
   g_posTicket   = 0;
   g_posEntry    = 0.0;
   g_posVolume   = 0.0;
   g_posProfit   = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;

      g_hasPosition = true;
      g_posTicket   = ticket;
      g_posType     = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      g_posEntry    = PositionGetDouble(POSITION_PRICE_OPEN);
      g_posVolume   = PositionGetDouble(POSITION_VOLUME);
      g_posProfit   = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      break;   // this EA holds at most one
     }
  }

//+------------------------------------------------------------------+
//| State refresh: this EA's pending stop order                      |
//+------------------------------------------------------------------+
void CheckExistingOrders()
  {
   g_hasStop    = false;
   g_stopTicket = 0;
   g_stopPrice  = 0.0;

   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket))
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != MagicNumber)
         continue;

      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type != ORDER_TYPE_BUY_STOP && type != ORDER_TYPE_SELL_STOP)
         continue;

      g_hasStop    = true;
      g_stopTicket = ticket;
      g_stopType   = type;
      g_stopPrice  = OrderGetDouble(ORDER_PRICE_OPEN);
      break;
     }
  }

//+------------------------------------------------------------------+
//| Volume the reverse stop must carry                               |
//| Hedging  : 1x lot, old position closed explicitly                |
//| Netting  : 2x lot flips the position in a single fill            |
//+------------------------------------------------------------------+
double ReverseVolume()
  {
   if(!EnableReversal)
      return g_tradeLot;                  // stop only, no flip
   if(g_isHedging)
      return g_tradeLot;
   return NormalizeVolume(g_tradeLot * 2.0);
  }

//+------------------------------------------------------------------+
//| Where the reverse stop should sit right now                      |
//+------------------------------------------------------------------+
double DesiredStopPrice()
  {
   if(!g_hasPosition)
      return 0.0;

   bool   isBuyPos = (g_posType == POSITION_TYPE_BUY);
   double anchor;

   if(TrailAnchor == ANCHOR_MID_PRICE)
      anchor = (Bid() + Ask()) * 0.5;
   else
      anchor = (isBuyPos ? Bid() : Ask());   // the price the position would close at

   double profitPoints = (isBuyPos ? (Bid() - g_posEntry) : (g_posEntry - Ask())) / g_point;

   double target;
   if(profitPoints >= TrailStartPoints && TrailingStopPoints > 0)
     {
      // trailing phase
      target = (isBuyPos ? anchor - TrailingStopPoints * g_point
                : anchor + TrailingStopPoints * g_point);
     }
   else
     {
      // initial phase: fixed distance from entry
      target = (isBuyPos ? g_posEntry - InitialStopPoints * g_point
                : g_posEntry + InitialStopPoints * g_point);
     }

   // never place a stop inside the broker's minimum distance
   int minD = MinDistancePoints();
   if(isBuyPos && (Bid() - target) < minD * g_point)
      target = Bid() - minD * g_point;
   if(!isBuyPos && (target - Ask()) < minD * g_point)
      target = Ask() + minD * g_point;

   return NormalizePrice(target);
  }

//+------------------------------------------------------------------+
//| Ratchet guard: the stop may only ever move toward profit         |
//+------------------------------------------------------------------+
bool StopMayMoveTo(const double newPrice)
  {
   if(!g_hasStop || g_stopPrice <= 0.0)
      return true;

   double step = TrailingStepPoints * g_point;
   bool   isBuyPos = (g_posType == POSITION_TYPE_BUY);

   if(isBuyPos)                       // sell stop below: may only rise
      return (newPrice > g_stopPrice + step);
   return (newPrice < g_stopPrice - step);   // buy stop above: may only fall
  }

bool IsFrozen(const double orderPrice)
  {
   if(g_freezeLevel <= 0)
      return false;
   double ref = (orderPrice > Bid() ? Ask() : Bid());
   return (MathAbs(orderPrice - ref) < g_freezeLevel * g_point);
  }

//+------------------------------------------------------------------+
//| Place the reverse stop order for the current position            |
//+------------------------------------------------------------------+
bool PlaceReverseStop()
  {
   if(!g_hasPosition)
      return false;

   double price = DesiredStopPrice();
   if(price <= 0.0)
      return false;

   bool   isBuyPos = (g_posType == POSITION_TYPE_BUY);
   double volume   = ReverseVolume();

   // direction filters apply to the side the stop would open
   if(isBuyPos && !EnableSell && EnableReversal)
      return false;
   if(!isBuyPos && !EnableBuy && EnableReversal)
      return false;

   ENUM_ORDER_TYPE type = (isBuyPos ? ORDER_TYPE_SELL_STOP : ORDER_TYPE_BUY_STOP);
   if(!HasEnoughMargin(type, volume, price))
      return false;

   double tp = 0.0;
   if(TakeProfitPoints > 0)
      tp = NormalizePrice(isBuyPos ? price - TakeProfitPoints * g_point
                          : price + TakeProfitPoints * g_point);

   bool sent;
   if(isBuyPos)
      sent = trade.SellStop(volume, price, _Symbol, 0.0, tp, ORDER_TIME_GTC, 0, OrderComment);
   else
      sent = trade.BuyStop(volume, price, _Symbol, 0.0, tp, ORDER_TIME_GTC, 0, OrderComment);

   return LogTradeResult(StringFormat("%s created: %.2f lots @ %s (position entry %s)",
                                      (isBuyPos ? "SELL STOP" : "BUY STOP"),
                                      volume,
                                      DoubleToString(price, g_digits),
                                      DoubleToString(g_posEntry, g_digits)), sent);
  }

//+------------------------------------------------------------------+
//| Move the reverse stop as price advances                          |
//+------------------------------------------------------------------+
void ManageReverseStop()
  {
   if(!g_hasPosition || !g_hasStop)
      return;

   if(TrailOnBarCloseOnly)
     {
      datetime barTime = iTime(_Symbol, PERIOD_M1, 0);
      if(barTime == g_lastBarTime)
         return;
      g_lastBarTime = barTime;
     }

   double target = DesiredStopPrice();
   if(target <= 0.0)
      return;
   if(!StopMayMoveTo(target))
      return;
   if(IsFrozen(g_stopPrice))
     {
      Print("[EA] Trail skipped: pending order inside freeze level");
      return;
     }

   double tp = 0.0;
   if(TakeProfitPoints > 0)
     {
      bool isBuyPos = (g_posType == POSITION_TYPE_BUY);
      tp = NormalizePrice(isBuyPos ? target - TakeProfitPoints * g_point
                          : target + TakeProfitPoints * g_point);
     }

   bool sent = trade.OrderModify(g_stopTicket, target, 0.0, tp, ORDER_TIME_GTC, 0, 0.0);
   LogTradeResult(StringFormat("Reverse stop trailed: #%I64u %s -> %s",
                               g_stopTicket,
                               DoubleToString(g_stopPrice, g_digits),
                               DoubleToString(target, g_digits)), sent);
  }

//+------------------------------------------------------------------+
//| Optional hard stop loss / take profit on the position itself     |
//+------------------------------------------------------------------+
void ApplyPositionLevels()
  {
   if(!g_hasPosition)
      return;
   if(HardStopLossPoints <= 0 && TakeProfitPoints <= 0)
      return;
   if(!PositionSelectByTicket(g_posTicket))
      return;

   double curSL = PositionGetDouble(POSITION_SL);
   double curTP = PositionGetDouble(POSITION_TP);
   bool   isBuy = (g_posType == POSITION_TYPE_BUY);

   double sl = curSL;
   double tp = curTP;
   int    minD = MinDistancePoints();

   if(HardStopLossPoints > 0 && curSL == 0.0)
     {
      int d = (HardStopLossPoints < minD ? minD : HardStopLossPoints);
      sl = NormalizePrice(isBuy ? g_posEntry - d * g_point : g_posEntry + d * g_point);
     }
   if(TakeProfitPoints > 0 && curTP == 0.0)
     {
      int d = (TakeProfitPoints < minD ? minD : TakeProfitPoints);
      tp = NormalizePrice(isBuy ? g_posEntry + d * g_point : g_posEntry - d * g_point);
     }

   if(sl == curSL && tp == curTP)
      return;

   bool sent = trade.PositionModify(g_posTicket, sl, tp);
   LogTradeResult(StringFormat("Position levels applied to #%I64u (SL %s / TP %s)",
                               g_posTicket,
                               DoubleToString(sl, g_digits),
                               DoubleToString(tp, g_digits)), sent);
  }

//+------------------------------------------------------------------+
//| Open the very first position                                     |
//+------------------------------------------------------------------+
bool SeedPosition()
  {
   if(SeedDirection == SEED_NONE)
      return false;

   bool goLong;
   if(SeedDirection == SEED_BUY)
      goLong = true;
   else
      if(SeedDirection == SEED_SELL)
         goLong = false;
      else
        {
         double o = iOpen(_Symbol, PERIOD_M1, 1);
         double c = iClose(_Symbol, PERIOD_M1, 1);
         if(o == 0.0 || c == 0.0)
            return false;
         if(MathAbs(c - o) < g_point)
            return false;
         goLong = (c > o);
        }

   if(goLong && !EnableBuy)
      return false;
   if(!goLong && !EnableSell)
      return false;

   ENUM_ORDER_TYPE type = (goLong ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double price = (goLong ? Ask() : Bid());
   if(!HasEnoughMargin(type, g_tradeLot, price))
      return false;

   bool sent;
   if(goLong)
      sent = trade.Buy(g_tradeLot, _Symbol, 0.0, 0.0, 0.0, OrderComment);
   else
      sent = trade.Sell(g_tradeLot, _Symbol, 0.0, 0.0, 0.0, OrderComment);

   bool ok = LogTradeResult(StringFormat("Seed %s opened", (goLong ? "BUY" : "SELL")), sent);
   if(ok)
      g_lastTradeTime = TimeCurrent();
   return ok;
  }

//+------------------------------------------------------------------+
//| Close every position owned by this EA                            |
//+------------------------------------------------------------------+
void CloseAllOwnPositions(const string why)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;

      bool sent = trade.PositionClose(ticket, Slippage);
      LogTradeResult(StringFormat("Position closed #%I64u (%s)", ticket, why), sent);
     }
  }

void DeleteOwnPendings(const string why)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket))
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != MagicNumber)
         continue;

      bool sent = trade.OrderDelete(ticket);
      LogTradeResult(StringFormat("Pending deleted #%I64u (%s)", ticket, why), sent);
     }
  }

//+------------------------------------------------------------------+
//| Hedging cleanup: if the reverse stop filled and both sides are   |
//| open, close the older one so only the new direction survives.    |
//+------------------------------------------------------------------+
void ResolveHedgedPair()
  {
   // Also gated on EnableReversal: closing the old side in favour of the
   // new one IS the flip. Running this with reversal disabled performed
   // the very reversal the operator turned off.
   if(!g_isHedging || !CloseOppositeOnFill || !EnableReversal)
      return;

   ulong tickets[];
   long  times[];
   int   count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;

      ArrayResize(tickets, count + 1);
      ArrayResize(times,   count + 1);
      tickets[count] = ticket;
      // _MSC, not POSITION_TIME: two positions opened in the same second
      // tie at second resolution, and the tie-break could keep the OLD
      // side and close the new one, silently undoing the reversal.
      times[count]   = (long)PositionGetInteger(POSITION_TIME_MSC);
      count++;
     }

   if(count < 2)
      return;

   // find the newest, close everything else
   int newest = 0;
   for(int i = 1; i < count; i++)
      if(times[i] > times[newest])
         newest = i;

   for(int i = 0; i < count; i++)
     {
      if(i == newest)
         continue;
      bool sent = trade.PositionClose(tickets[i], Slippage);
      LogTradeResult(StringFormat("Position closed #%I64u (reversed)", tickets[i]), sent);
     }
   g_reversalsToday++;
   g_lastTradeTime = TimeCurrent();
  }

//+------------------------------------------------------------------+
//| Main state machine                                               |
//+------------------------------------------------------------------+
void ManageStopAndReverse()
  {
   string reason = "";
   bool canTrade = ValidateTradingConditions(reason);

   if(TradeOnlyDuringSpecifiedHours && CloseAllAtSessionEnd && !IsInsideTradingHours())
     {
      if(g_hasPosition || g_hasStop)
        {
         DeleteOwnPendings("session end");
         CloseAllOwnPositions("session end");
        }
      g_statusText = "session closed";
      return;
     }

   if(!canTrade)
     {
      g_statusText = "blocked: " + reason;
      if(g_dailyLossHit)
        {
         // Blocking new orders is not enough: a live reverse stop would
         // keep flipping into fresh positions all day. Flatten instead.
         if(g_hasStop || g_hasPosition)
           {
            DeleteOwnPendings("daily loss limit");
            CloseAllOwnPositions("daily loss limit");
           }
         if(TimeCurrent() - g_lastBlockLog > 60)
           {
            PrintFormat("[EA] %s - flat for the rest of the day.", reason);
            g_lastBlockLog = TimeCurrent();
           }
         return;
        }
      if(TimeCurrent() - g_lastBlockLog > 60)
        {
         PrintFormat("[EA] New orders blocked: %s", reason);
         g_lastBlockLog = TimeCurrent();
        }
      // a live position still needs its trail maintained
      if(g_hasPosition && g_hasStop)
         ManageReverseStop();
      return;
     }

   g_statusText = "active";

   //--- 1. flat and no stop: seed if configured
   if(!g_hasPosition && !g_hasStop)
     {
      if(SeedPosition())
        {
         CheckExistingPositions();
         if(g_hasPosition)
            PlaceReverseStop();
        }
      else
         g_statusText = "flat (no seed configured)";
      return;
     }

   //--- 2. flat but a stop is still live: the position was closed elsewhere
   if(!g_hasPosition && g_hasStop)
     {
      if(!EnableReversal)
        {
         DeleteOwnPendings("position gone, reversal disabled");
         return;
        }
      // The netting reverse stop carries 2x volume because it is sized to
      // flip a position. With no position left it would OPEN at double
      // size, so resize it to the plain trading lot first.
      if(!g_isHedging)
        {
         double want = g_tradeLot;
         if(OrderSelect(g_stopTicket) &&
            MathAbs(OrderGetDouble(ORDER_VOLUME_CURRENT) - want) > 1e-8)
           {
            bool resized = trade.OrderDelete(g_stopTicket);
            LogTradeResult("Oversized reverse stop removed (position closed elsewhere)", resized);
            return;   // rebuilt next tick once a position exists again
           }
        }
      // leave the stop alone; it will open the next position when hit
      g_statusText = "waiting for stop entry";
      return;
     }

   //--- 3. position but no stop: (re)create the protective reverse order
   if(g_hasPosition && !g_hasStop)
     {
      ApplyPositionLevels();
      if(PlaceReverseStop())
         g_lastTradeTime = TimeCurrent();
      else
        {
         // A persistent failure (margin, invalid stops) retries every tick.
         // Throttle the log so it cannot flood the journal.
         if(TimeCurrent() - g_lastRetryLog > 60)
           {
            Print("[EA] Reverse stop could not be placed; retrying each tick.");
            g_lastRetryLog = TimeCurrent();
           }
        }
      return;
     }

   //--- 4. normal running state: trail
   ApplyPositionLevels();
   ManageReverseStop();
  }

//+------------------------------------------------------------------+
//| Chart display                                                    |
//+------------------------------------------------------------------+
void DrawLevel(const string name, const double price, const color clr,
               const ENUM_LINE_STYLE style, const string text)
  {
   if(price <= 0.0)
     {
      ObjectDelete(0, name);
      return;
     }
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
  }

void DrawPanelLine(const int index, const string text, const color clr)
  {
   string name = g_prefix + "panel_" + IntegerToString(index);
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, PanelXOffset);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, PanelYOffset + index * 15);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
  }

void UpdateChartObjects()
  {
   if(!ShowChartObjects)
      return;

   //--- position entry line (solid, like the video)
   if(g_hasPosition)
     {
      color c = (g_posType == POSITION_TYPE_BUY ? BuyColor : SellColor);
      string side = (g_posType == POSITION_TYPE_BUY ? "BUY" : "SELL");
      DrawLevel(g_prefix + "entry", g_posEntry, c, STYLE_DASH,
                StringFormat("%s %.2f, %+.2f %s", side, g_posVolume, g_posProfit,
                             AccountInfoString(ACCOUNT_CURRENCY)));
     }
   else
      ObjectDelete(0, g_prefix + "entry");

   //--- reverse stop line (dash-dot, like the video)
   if(g_hasStop)
     {
      bool stopIsBuy = (g_stopType == ORDER_TYPE_BUY_STOP);
      color c = (stopIsBuy ? BuyColor : SellColor);
      DrawLevel(g_prefix + "stop", g_stopPrice, c, STYLE_DASHDOT,
                StringFormat("%s STOP", (stopIsBuy ? "BUY" : "SELL")));
     }
   else
      ObjectDelete(0, g_prefix + "stop");

   //--- info panel
   int line = 0;
   DrawPanelLine(line++, StringFormat("%s  |  magic %I64u  |  %s",
                                      _Symbol, MagicNumber,
                                      (g_isHedging ? "hedging" : "netting")), PanelTextColor);
   DrawPanelLine(line++, StringFormat("Bid %s   Ask %s   Spread %d pts",
                                      DoubleToString(Bid(), g_digits),
                                      DoubleToString(Ask(), g_digits),
                                      SpreadPoints()), PanelTextColor);

   if(g_hasPosition)
     {
      bool isBuy = (g_posType == POSITION_TYPE_BUY);
      double profitPoints = (isBuy ? (Bid() - g_posEntry) : (g_posEntry - Ask())) / g_point;
      DrawPanelLine(line++, StringFormat("POS  %s %.2f @ %s   %+.0f pts   %+.2f %s",
                                         (isBuy ? "BUY " : "SELL"),
                                         g_posVolume,
                                         DoubleToString(g_posEntry, g_digits),
                                         profitPoints, g_posProfit,
                                         AccountInfoString(ACCOUNT_CURRENCY)),
                    (g_posProfit >= 0.0 ? clrLime : clrTomato));
     }
   else
      DrawPanelLine(line++, "POS  -- flat --", PanelTextColor);

   if(g_hasStop)
     {
      bool stopIsBuy = (g_stopType == ORDER_TYPE_BUY_STOP);
      double away = (stopIsBuy ? (g_stopPrice - Ask()) : (Bid() - g_stopPrice)) / g_point;
      DrawPanelLine(line++, StringFormat("STOP %s @ %s   %.0f pts away",
                                         (stopIsBuy ? "BUY " : "SELL"),
                                         DoubleToString(g_stopPrice, g_digits), away),
                    (stopIsBuy ? BuyColor : SellColor));
     }
   else
      DrawPanelLine(line++, "STOP -- none --", PanelTextColor);

   if(g_hasPosition)
     {
      bool isBuy = (g_posType == POSITION_TYPE_BUY);
      double profitPoints = (isBuy ? (Bid() - g_posEntry) : (g_posEntry - Ask())) / g_point;
      string phase = (profitPoints >= TrailStartPoints ? "trailing" : "initial stop");
      DrawPanelLine(line++, StringFormat("Phase: %s  |  reversals today %d", phase, g_reversalsToday),
                    PanelTextColor);
     }
   else
      DrawPanelLine(line++, StringFormat("Reversals today %d", g_reversalsToday), PanelTextColor);

   DrawPanelLine(line++, "Status: " + g_statusText, PanelTextColor);

   for(int k = line; k < line + 4; k++)
      ObjectDelete(0, g_prefix + "panel_" + IntegerToString(k));

   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
  {
   g_prefix = StringFormat("SAR_%I64u_", MagicNumber);

   g_digits       = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   g_point        = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   g_tickSize     = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   g_stopsLevel   = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   g_freezeLevel  = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   g_volMin       = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   g_volMax       = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   g_volStep      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   g_contractSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);

   g_isHedging = ((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE)
                  == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);

   if(g_point <= 0.0)
     {
      Print("[EA] Init failed: symbol point size is zero. Is the symbol in Market Watch?");
      return INIT_FAILED;
     }

   g_tradeLot = NormalizeVolume(LotSize);
   if(g_tradeLot <= 0.0)
     {
      Print("[EA] Init failed: LotSize could not be normalised.");
      return INIT_FAILED;
     }
   if(MathAbs(g_tradeLot - LotSize) > 1e-8)
      PrintFormat("[EA] LotSize %.4f adjusted to broker-valid %.4f (min %.2f / max %.2f / step %.2f)",
                  LotSize, g_tradeLot, g_volMin, g_volMax, g_volStep);

   if(InitialStopPoints <= 0)
     {
      Print("[EA] Init failed: InitialStopPoints must be greater than zero.");
      return INIT_FAILED;
     }
   if(!EnableBuy && !EnableSell)
      Print("[EA] Warning: both directions disabled.");
   if(!g_isHedging && EnableReversal)
      Print("[EA] Netting account detected: the reverse stop will use double volume to flip the position.");

   // --- configuration sanity ------------------------------------------
   // These fail SILENTLY otherwise: the EA simply never trades, or trades
   // at distances the operator did not choose.
   if(g_isHedging && EnableReversal && !CloseOppositeOnFill)
      Print("[EA] WARNING: hedging account with CloseOppositeOnFill=false. "
            "The old position is never closed, so this EA will ACCUMULATE "
            "positions instead of holding one. Set CloseOppositeOnFill=true.");

   int minD = MinDistancePoints();
   if(InitialStopPoints < minD || (TrailingStopPoints > 0 && TrailingStopPoints < minD))
      PrintFormat("[EA] WARNING: stop distances are below the broker minimum of %d points "
                  "(stops level %d, spread %d). InitialStopPoints=%d and TrailingStopPoints=%d "
                  "will be CLAMPED to %d, so the configured geometry is ignored. "
                  "On this %d-digit symbol 1 point = %s - check the inputs use the same scale.",
                  minD, g_stopsLevel, SpreadPoints(), InitialStopPoints, TrailingStopPoints,
                  minD, g_digits, DoubleToString(g_point, 8));

   if(MaxSpreadPoints > 0 && SpreadPoints() > MaxSpreadPoints)
      PrintFormat("[EA] WARNING: spread is %d points but MaxSpreadPoints=%d. "
                  "EVERY new order will be blocked until the spread narrows below the limit.",
                  SpreadPoints(), MaxSpreadPoints);

   if(MaxDailyLossCurrency <= 0.0)
      Print("[EA] WARNING: MaxDailyLossCurrency=0 - there is NO daily loss limit. "
            "A stop-and-reverse system loses on every flip in a ranging market.");
   else
      PrintFormat("[EA] Daily loss limit: %.2f %s (flattens and stops trading for the day)",
                  MaxDailyLossCurrency, AccountInfoString(ACCOUNT_CURRENCY));

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(Slippage);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);
   trade.LogLevel(LOG_LEVEL_ERRORS);

   ParseNewsTimes();
   RollDailyCounter();

   Print("[EA] Initialized");
   PrintFormat("[EA] Symbol %s | digits=%d point=%s tickSize=%s contract=%.2f",
               _Symbol, g_digits, DoubleToString(g_point, 8),
               DoubleToString(g_tickSize, 8), g_contractSize);
   PrintFormat("[EA] Volume: min=%.2f max=%.2f step=%.2f | trading lot=%.2f",
               g_volMin, g_volMax, g_volStep, g_tradeLot);
   PrintFormat("[EA] Stops level=%d pts | Freeze level=%d pts", g_stopsLevel, g_freezeLevel);
   PrintFormat("[EA] Current Bid: %s", DoubleToString(Bid(), g_digits));
   PrintFormat("[EA] Current Ask: %s", DoubleToString(Ask(), g_digits));
   PrintFormat("[EA] Spread: %d points", SpreadPoints());
   PrintFormat("[EA] Initial stop %d pts from entry | trail %d pts after %d pts profit",
               InitialStopPoints, TrailingStopPoints, TrailStartPoints);

   CheckExistingPositions();
   CheckExistingOrders();
   PrintFormat("[EA] Existing state adopted: position=%s stop=%s",
               (g_hasPosition ? "yes" : "no"), (g_hasStop ? "yes" : "no"));

   UpdateChartObjects();
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, g_prefix);
   ChartRedraw(0);
   PrintFormat("[EA] Deinitialized (reason %d). Orders and positions left untouched.", reason);
  }

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+
void OnTick()
  {
   CheckExistingPositions();
   ResolveHedgedPair();

   CheckExistingPositions();
   CheckExistingOrders();

   ManageStopAndReverse();

   CheckExistingPositions();
   CheckExistingOrders();
   UpdateChartObjects();
  }

//+------------------------------------------------------------------+
//| OnTradeTransaction                                               |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(StringLen(trans.symbol) > 0 && trans.symbol != _Symbol)
      return;

   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
     {
      if(!HistoryDealSelect(trans.deal))
         return;
      if((ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != MagicNumber)
         return;

      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
      double price  = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
      double volume = HistoryDealGetDouble(trans.deal, DEAL_VOLUME);
      double profit = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
      long   type   = HistoryDealGetInteger(trans.deal, DEAL_TYPE);
      string side   = (type == DEAL_TYPE_BUY ? "BUY" : "SELL");

      if(entry == DEAL_ENTRY_IN)
        {
         PrintFormat("[EA] Order triggered: reverse stop filled, deal #%I64u", trans.deal);
         PrintFormat("[EA] Position opened: %s %.2f @ %s",
                     side, volume, DoubleToString(price, g_digits));
         g_lastTradeTime = TimeCurrent();
        }
      else
         if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
           {
            PrintFormat("[EA] Position closed: %s %.2f @ %s | profit %.2f %s",
                        side, volume, DoubleToString(price, g_digits),
                        profit, AccountInfoString(ACCOUNT_CURRENCY));
           }
         else
            if(entry == DEAL_ENTRY_INOUT)
              {
               PrintFormat("[EA] Position reversed (netting): now %s %.2f @ %s | booked %.2f %s",
                           side, volume, DoubleToString(price, g_digits),
                           profit, AccountInfoString(ACCOUNT_CURRENCY));
               g_reversalsToday++;
               g_lastTradeTime = TimeCurrent();
              }
      return;
     }

   if(trans.type == TRADE_TRANSACTION_REQUEST)
     {
      if(result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_PLACED)
         PrintFormat("[EA] Trade error: request rejected (action %d), retcode=%u, comment=%s",
                     (int)request.action, result.retcode, result.comment);
     }
  }
//+------------------------------------------------------------------+
