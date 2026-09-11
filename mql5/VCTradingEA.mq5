//+------------------------------------------------------------------+
//|                                                  VCTradingEA.mq5 |
//|  Trades VC Trading AI signals inside this MetaTrader 5 terminal. |
//|                                                                  |
//|  ADR-161. The website never places trades and never sees the     |
//|  broker login: this EA reads GET /ea/signals and does all the    |
//|  trading here. Dry run is the default.                           |
//|  ADR-162. It reports what it did to POST /ea/events, so the      |
//|  website's EA Activity page shows it without opening MT5.        |
//+------------------------------------------------------------------+
#property copyright   "VC Trading AI"
#property version     "1.10"
#property description "Reads the VC Trading AI signal feed and trades it in this terminal."
#property description "Dry run by default: every order is logged and checked, never sent."

#include <Trade\Trade.mqh>

//--- inputs -----------------------------------------------------------
input group "Connection"
input string InpApiBaseUrl     = "https://vcanalyzetrading.site/api/v1"; // API base URL
input string InpEaToken        = "";   // EA token from Settings (starts with vcea_)
input int    InpPollSeconds    = 10;   // Seconds between feed checks (minimum 5)
input bool   InpReportActivity = true; // Report what the EA does to the website

input group "Symbols"
input string InpSignalSymbol = "XAUUSD";  // Symbol on the website
input string InpBrokerSymbol = "XAUUSDc"; // Symbol in this terminal

input group "Trading"
input bool   InpDryRun          = true;     // Dry run: log and check orders, never send them
input double InpLotSize         = 0.01;     // Fixed lot size for every signal
input int    InpMaxOpenTrades   = 1;        // Max positions + pending orders from this EA
input ulong  InpMagicNumber     = 16112026; // Magic number marking this EA's orders
input int    InpDeviationPoints = 50;       // Max slippage on market entries (points)

//--- constants ---------------------------------------------------------
#define STATE_FOLDER   "VCTrading"
#define COMMENT_PREFIX "VC "
#define TOKEN_PREFIX   "vcea_"

// What this EA did with a signal. Every signal is acted on at most once.
#define KIND_DRY_RUN  0 // logged and checked only
#define KIND_PENDING  1 // limit order sent
#define KIND_MARKET   2 // market order sent (price had already reached entry)
#define KIND_SKIPPED  3 // not traded: setup invalid at current prices, or lot below minimum
#define KIND_REJECTED 4 // broker refused, or outcome unknown - never retried

// An order needs at least this long before the signal expires to be worth placing.
#define MIN_SECONDS_BEFORE_EXPIRY 300

// Activity reports waiting to be sent. Bounded so a terminal offline for
// weeks cannot grow the file without limit; the oldest go first.
#define MAX_QUEUED_EVENTS 500
#define EVENT_BATCH_SIZE  50 // the website accepts at most 50 per request

//--- types -------------------------------------------------------------
struct FeedSignal
  {
   string            id;
   string            side;      // "buy" or "sell"
   string            status;    // "active" or "triggered"
   double            entry;
   double            sl;
   double            tp;
   datetime          expiresAt; // UTC, on the website's clock
  };

struct HandledSignal
  {
   string            id;
   ulong             ticket;         // pending order still to manage; 0 when none
   int               kind;
   datetime          expiresAt;
   ulong             orderTicket;    // order sent and not yet resolved (filled/cancelled); 0 when none
   ulong             positionId;     // position the order opened; 0 until filled
   int               closedReported; // 1 once that position's close was reported
  };

//--- state -------------------------------------------------------------
CTrade        g_trade;
HandledSignal g_handled[];
string        g_events[];              // JSON objects waiting to be reported
string        g_stateFile       = "";
string        g_eventsFile      = "";
long          g_clockDrift      = 0;   // website clock minus this PC's GMT clock, seconds
string        g_status          = "waiting for first check";
string        g_lastLogged      = "";
int           g_openSignalCount = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(StringFind(InpEaToken, TOKEN_PREFIX) != 0 || StringLen(InpEaToken) < 20)
     {
      Alert("VC Trading EA: paste the EA token from Settings into EaToken (it starts with vcea_).");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!SymbolSelect(InpBrokerSymbol, true))
     {
      Alert("VC Trading EA: symbol '", InpBrokerSymbol, "' is not available in this terminal.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpLotSize <= 0.0 || InpMaxOpenTrades < 1)
     {
      Alert("VC Trading EA: LotSize must be above 0 and MaxOpenTrades at least 1.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints((ulong)MathMax(InpDeviationPoints, 0));
   g_trade.SetTypeFillingBySymbol(InpBrokerSymbol);
   g_trade.LogLevel(LOG_LEVEL_ERRORS);

// Separate files for dry run and live, so switching to live does not
// inherit "already handled" from signals that were only logged.
   FolderCreate(STATE_FOLDER);
   string suffix = StringFormat("%I64d_%I64d_%s.txt", AccountInfoInteger(ACCOUNT_LOGIN),
                                (long)InpMagicNumber, InpDryRun ? "dry" : "live");
   g_stateFile  = STATE_FOLDER + "\\handled_" + suffix;
   g_eventsFile = STATE_FOLDER + "\\reports_" + suffix;
   LoadState();
   LoadEvents();

   if(!EventSetTimer(MathMax(InpPollSeconds, 5)))
      return(INIT_FAILED);

   PrintFormat("VC Trading EA 1.10 started - %s | %s -> %s | lot %.2f | max trades %d | reporting %s",
               InpDryRun ? "DRY RUN (no orders are sent)" : "LIVE", InpSignalSymbol, InpBrokerSymbol,
               InpLotSize, InpMaxOpenTrades, InpReportActivity ? "on" : "off");
   UpdatePanel();
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
// Work happens on the timer: signals arrive from the website, not from ticks.
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   FeedSignal signals[];
   bool fetched = FetchFeed(signals);

// Both use only this terminal's own clock and trade history, so they run
// even when the website cannot be reached: an unfilled order must not
// outlive its signal, and a fill is recorded (and queued) when it happens.
   CancelExpiredOrders();
   ReconcileTrades();

// Everything below trusts the feed, so it runs only on a response that
// arrived and parsed in full. A failed request never means "no signals".
   if(fetched)
     {
      g_openSignalCount = ArraySize(signals);
      CancelOrdersForClosedSignals(signals);
      for(int i = 0; i < ArraySize(signals); i++)
         HandleSignal(signals[i]);
      PruneState();
      FlushEvents();
     }
   UpdatePanel();
  }

//+------------------------------------------------------------------+
//| Feed                                                             |
//+------------------------------------------------------------------+
bool FetchFeed(FeedSignal &signals[])
  {
   ArrayResize(signals, 0);
   string url     = InpApiBaseUrl + "/ea/signals?symbol=" + InpSignalSymbol;
   string headers = "X-EA-Token: " + InpEaToken + "\r\nAccept: application/json\r\n";
   char   body[];
   char   result[];
   string resultHeaders;

   ResetLastError();
   int code = WebRequest("GET", url, headers, 10000, body, result, resultHeaders);
   if(code == -1)
     {
      int err = GetLastError();
      if(err == 4014)
         SetStatus("URL not allowed - add " + BaseHost(InpApiBaseUrl) +
                   " in Tools > Options > Expert Advisors > Allow WebRequest");
      else
         SetStatus(StringFormat("cannot reach the website (error %d)", err));
      return(false);
     }

   string text = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   if(code == 401)
     {
      SetStatus("token rejected (revoked or wrong) - create a new one in Settings");
      return(false);
     }
   if(code == 429)
     {
      SetStatus("rate limited by the website - raise PollSeconds");
      return(false);
     }
   if(code != 200)
     {
      SetStatus(StringFormat("website returned HTTP %d", code));
      return(false);
     }

   string serverTime;
   if(!JsonValue(text, "server_time", serverTime))
     {
      SetStatus("unreadable response from the website");
      return(false);
     }
   g_clockDrift = StringToInteger(serverTime) - (long)TimeGMT();

   if(!ParseSignals(text, signals))
     {
      ArrayResize(signals, 0);
      SetStatus("unreadable signal list - nothing changed");
      return(false);
     }

   SetStatus("ok");
   return(true);
  }

//+------------------------------------------------------------------+
//| All-or-nothing: one malformed signal fails the whole response, so a
//| partial parse can never look like "those other signals are gone".
bool ParseSignals(const string json, FeedSignal &signals[])
  {
   string marker = "\"signals\":[";
   int    pos    = StringFind(json, marker);
   if(pos < 0)
      return(false);
   pos += StringLen(marker);

   while(true)
     {
      int open    = StringFind(json, "{", pos);
      int listEnd = StringFind(json, "]", pos);
      if(listEnd < 0)
         return(false);
      if(open < 0 || open > listEnd)
         break;
      int close = StringFind(json, "}", open);
      if(close < 0)
         return(false);

      FeedSignal item;
      if(!ParseSignal(StringSubstr(json, open, close - open + 1), item))
         return(false);
      int n = ArraySize(signals);
      ArrayResize(signals, n + 1);
      signals[n] = item;
      pos = close + 1;
     }
   return(true);
  }

//+------------------------------------------------------------------+
bool ParseSignal(const string obj, FeedSignal &item)
  {
   string entry, sl, tp, expires;
   if(!JsonValue(obj, "id", item.id) || !JsonValue(obj, "signal_type", item.side) ||
      !JsonValue(obj, "status", item.status) || !JsonValue(obj, "entry_price", entry) ||
      !JsonValue(obj, "stop_loss", sl) || !JsonValue(obj, "take_profit", tp) ||
      !JsonValue(obj, "expires_at", expires))
      return(false);

   item.entry     = StringToDouble(entry);
   item.sl        = StringToDouble(sl);
   item.tp        = StringToDouble(tp);
   item.expiresAt = (datetime)StringToInteger(expires);

   if(StringLen(item.id) != 36 || item.entry <= 0.0 || item.sl <= 0.0 || item.tp <= 0.0 ||
      item.expiresAt <= 0)
      return(false);
   if(item.side != "buy" && item.side != "sell")
      return(false);
// A buy's stop must sit below entry and its target above; the reverse for a sell.
   if(item.side == "buy" && !(item.sl < item.entry && item.entry < item.tp))
      return(false);
   if(item.side == "sell" && !(item.tp < item.entry && item.entry < item.sl))
      return(false);
   return(true);
  }

//+------------------------------------------------------------------+
//| Value of "key" in a flat JSON object, without quotes. The feed has
//| no nested objects inside a signal and no brackets in any value, so a
//| full JSON parser is not needed.
bool JsonValue(const string json, const string key, string &value)
  {
   string needle = "\"" + key + "\":";
   int    start  = StringFind(json, needle);
   if(start < 0)
      return(false);
   start += StringLen(needle);
   int len = StringLen(json);
   while(start < len && StringGetCharacter(json, start) == ' ')
      start++;
   if(start >= len)
      return(false);

   if(StringGetCharacter(json, start) == '"')
     {
      int close = StringFind(json, "\"", start + 1);
      if(close < 0)
         return(false);
      value = StringSubstr(json, start + 1, close - start - 1);
      return(true);
     }

   int end = start;
   while(end < len)
     {
      ushort ch = StringGetCharacter(json, end);
      if(ch == ',' || ch == '}' || ch == ']')
         break;
      end++;
     }
   value = StringSubstr(json, start, end - start);
   StringTrimRight(value);
   return(StringLen(value) > 0 && value != "null");
  }

//+------------------------------------------------------------------+
//| Trading                                                          |
//+------------------------------------------------------------------+
void HandleSignal(const FeedSignal &s)
  {
   if(FindHandled(s.id) >= 0)
      return; // acted on already - never twice
   if(s.status != "active")
      return; // triggered: keep any order we have, open nothing new
   if((long)s.expiresAt - (long)WebsiteNow() < MIN_SECONDS_BEFORE_EXPIRY)
      return;

   string shortId = StringSubstr(s.id, 0, 8);
   string comment = COMMENT_PREFIX + shortId;
   if(HasTradeWithComment(comment))
     {
      // The state file was lost but the order exists - adopt it, do not duplicate it.
      ulong pending = FindPendingTicket(comment);
      Remember(s.id, pending, KIND_PENDING, s.expiresAt, pending, FindPositionId(comment));
      return;
     }
   if(CountOwnTrades() >= InpMaxOpenTrades)
     {
      LogOnce(StringFormat("signal %s waiting: %d of %d trades already open", shortId, CountOwnTrades(),
                           InpMaxOpenTrades));
      return; // not remembered - reconsidered once a trade closes, while still active
     }

   double volume = NormalizeVolume(InpLotSize);
   if(volume <= 0.0)
     {
      string why = StringFormat("LotSize %.2f is below %s's minimum lot", InpLotSize, InpBrokerSymbol);
      Remember(s.id, 0, KIND_SKIPPED, s.expiresAt);
      QueueEvent("skipped:" + s.id, "order_skipped", s.id, JS("message", why));
      PrintFormat("signal %s skipped: %s", shortId, why);
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(InpBrokerSymbol, tick) || tick.bid <= 0.0 || tick.ask <= 0.0)
      return; // no price yet - try again next check

   bool   isBuy = (s.side == "buy");
   double entry = NormalizePrice(s.entry);
   double sl    = NormalizePrice(s.sl);
   double tp    = NormalizePrice(s.tp);

   if((isBuy && (tick.bid <= sl || tick.bid >= tp)) || (!isBuy && (tick.ask >= sl || tick.ask <= tp)))
     {
      string why = StringFormat("price (bid %s / ask %s) was already past the stop or target",
                                PriceText(tick.bid), PriceText(tick.ask));
      Remember(s.id, 0, KIND_SKIPPED, s.expiresAt);
      QueueEvent("skipped:" + s.id, "order_skipped", s.id,
                 JP("stop_loss", sl) + "," + JP("take_profit", tp) + "," + JS("message", why));
      PrintFormat("signal %s skipped: %s", shortId, why);
      return;
     }

// A limit at the signal's entry while price has not reached it. Once it
// has, a limit would sit on the wrong side of the market and be refused,
// so enter at market instead - at or better than the signal's entry.
   bool market = isBuy ? (tick.ask <= entry) : (tick.bid >= entry);

   ENUM_ORDER_TYPE_TIME timeType   = ORDER_TIME_GTC;
   datetime             expiration = 0;
   if(!market && SupportsSpecifiedExpiry())
     {
      // expires_at is on the website's clock; the broker wants its own server time.
      long brokerOffset = (long)TimeTradeServer() - (long)TimeGMT();
      expiration        = (datetime)((long)s.expiresAt - g_clockDrift + brokerOffset);
      timeType          = ORDER_TIME_SPECIFIED;
     }

   ENUM_ORDER_TYPE type = market ? (isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL)
                          : (isBuy ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT);
   double price  = market ? (isBuy ? tick.ask : tick.bid) : entry;
   string fields = JS("order_type", OrderTypeText(type)) + "," + JV("volume", volume) + "," +
                   JP("price", price) + "," + JP("stop_loss", sl) + "," + JP("take_profit", tp);
   string what   = StringFormat("%s %s %.2f lots @ %s  SL %s  TP %s  expires %s UTC  [%s]",
                                EnumToString(type), InpBrokerSymbol, volume, PriceText(price),
                                PriceText(sl), PriceText(tp), TimeToString(s.expiresAt), shortId);

   if(InpDryRun)
     {
      MqlTradeRequest     request;
      MqlTradeCheckResult check;
      ZeroMemory(request);
      ZeroMemory(check);
      request.action       = market ? TRADE_ACTION_DEAL : TRADE_ACTION_PENDING;
      request.symbol       = InpBrokerSymbol;
      request.volume       = volume;
      request.type         = type;
      request.price        = price;
      request.sl           = sl;
      request.tp           = tp;
      request.deviation    = (ulong)MathMax(InpDeviationPoints, 0);
      request.magic        = InpMagicNumber;
      request.comment      = comment;
      request.type_filling = FillingFor(InpBrokerSymbol);
      request.type_time    = timeType;
      request.expiration   = expiration;

      bool   passed  = OrderCheck(request, check);
      string verdict = StringFormat("%s (%s, margin %.2f, free margin after %.2f)",
                                    passed ? "would be accepted" : "WOULD BE REFUSED", check.comment,
                                    check.margin, check.margin_free);
      PrintFormat("[DRY RUN] %s | broker check: %s", what, verdict);
      Remember(s.id, 0, KIND_DRY_RUN, s.expiresAt);
      QueueEvent("dry_run_checked:" + s.id, "dry_run_checked", s.id,
                 fields + "," + JI("retcode", (long)check.retcode) + "," + JS("message", verdict));
      return;
     }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
     {
      LogOnce("LIVE but trading is not allowed - turn on Algo Trading and allow it in the EA settings");
      return; // not remembered - placed once trading is allowed, while still active
     }

   bool sent;
   if(market)
      sent = isBuy ? g_trade.Buy(volume, InpBrokerSymbol, 0.0, sl, tp, comment)
             : g_trade.Sell(volume, InpBrokerSymbol, 0.0, sl, tp, comment);
   else
      sent = isBuy ? g_trade.BuyLimit(volume, entry, InpBrokerSymbol, sl, tp, timeType, expiration, comment)
             : g_trade.SellLimit(volume, entry, InpBrokerSymbol, sl, tp, timeType, expiration, comment);

   uint retcode = g_trade.ResultRetcode();
   if(sent && (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_PLACED ||
               retcode == TRADE_RETCODE_DONE_PARTIAL))
     {
      ulong orderTicket = g_trade.ResultOrder();
      Remember(s.id, market ? 0 : orderTicket, market ? KIND_MARKET : KIND_PENDING, s.expiresAt, orderTicket);
      QueueEvent("placed:" + s.id, "order_placed", s.id, fields + "," + JI("order_ticket", (long)orderTicket));
      PrintFormat("[LIVE] placed %s | ticket %I64u", what, orderTicket);
      return;
     }

   if(IsRetryable(retcode))
     {
      LogOnce(StringFormat("[LIVE] %s not placed yet (%u %s) - will retry", shortId, retcode,
                           g_trade.ResultRetcodeDescription()));
      return;
     }

   string why = (retcode == TRADE_RETCODE_TIMEOUT)
                ? "the broker timed out - the order may exist anyway, check the Trade tab"
                : g_trade.ResultRetcodeDescription();
   Remember(s.id, 0, KIND_REJECTED, s.expiresAt);
   QueueEvent("rejected:" + s.id, "order_rejected", s.id,
              fields + "," + JI("retcode", (long)retcode) + "," + JS("message", why));
   PrintFormat("[LIVE] NOT placed, not retrying: %s | %u %s", what, retcode, why);
  }

//+------------------------------------------------------------------+
//| Temporary refusals worth retrying on the next check. A timeout is
//| deliberately not here: the order may have been placed, and retrying
//| could open it twice.
bool IsRetryable(const uint retcode)
  {
   return(retcode == TRADE_RETCODE_REQUOTE || retcode == TRADE_RETCODE_PRICE_CHANGED ||
          retcode == TRADE_RETCODE_PRICE_OFF || retcode == TRADE_RETCODE_CONNECTION ||
          retcode == TRADE_RETCODE_TOO_MANY_REQUESTS || retcode == TRADE_RETCODE_MARKET_CLOSED ||
          retcode == TRADE_RETCODE_CLIENT_DISABLES_AT || retcode == TRADE_RETCODE_SERVER_DISABLES_AT);
  }

//+------------------------------------------------------------------+
void CancelOrdersForClosedSignals(const FeedSignal &signals[])
  {
   for(int i = 0; i < ArraySize(g_handled); i++)
     {
      if(g_handled[i].ticket == 0 || !IsOwnPendingOrder(g_handled[i].ticket))
         continue;
      bool listed = false;
      for(int j = 0; j < ArraySize(signals) && !listed; j++)
         listed = (signals[j].id == g_handled[i].id);
      if(!listed)
         CancelOrder(i, "its signal is no longer open on the website");
     }
  }

//+------------------------------------------------------------------+
void CancelExpiredOrders()
  {
   datetime websiteNow = WebsiteNow();
   for(int i = 0; i < ArraySize(g_handled); i++)
     {
      if(g_handled[i].ticket == 0 || g_handled[i].expiresAt > websiteNow)
         continue;
      if(IsOwnPendingOrder(g_handled[i].ticket))
         CancelOrder(i, "its signal expired");
     }
  }

//+------------------------------------------------------------------+
void CancelOrder(const int index, const string reason)
  {
   ulong ticket = g_handled[index].ticket;
   if(g_trade.OrderDelete(ticket))
     {
      PrintFormat("[LIVE] cancelled pending order %I64u because %s [%s]", ticket, reason,
                  StringSubstr(g_handled[index].id, 0, 8));
      QueueEvent("cancelled:" + IntegerToString((long)ticket), "order_cancelled", g_handled[index].id,
                 JI("order_ticket", (long)ticket) + "," + JS("message", reason));
      g_handled[index].ticket      = 0;
      g_handled[index].orderTicket = 0; // resolved - reconciliation must not report it again
      SaveState();
     }
   else
      LogOnce(StringFormat("[LIVE] could not cancel order %I64u (%u %s) - will retry", ticket,
                           g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription()));
  }

//+------------------------------------------------------------------+
//| Fills and closes, read from this terminal's own trade history rather
//| than from trade events, so one that happened while the EA was not
//| running is still found - and reported - the next time it is.
void ReconcileTrades()
  {
   bool changed = false;
   for(int i = 0; i < ArraySize(g_handled); i++)
     {
      ulong order = g_handled[i].orderTicket;
      if(order > 0 && g_handled[i].positionId == 0 && !IsOwnPendingOrder(order) && HistoryOrderSelect(order))
        {
         ENUM_ORDER_STATE state      = (ENUM_ORDER_STATE)HistoryOrderGetInteger(order, ORDER_STATE);
         ulong            positionId = (ulong)HistoryOrderGetInteger(order, ORDER_POSITION_ID);
         if((state == ORDER_STATE_FILLED || state == ORDER_STATE_PARTIAL) && positionId > 0)
           {
            if(ReportOpened(i, positionId))
              {
               g_handled[i].positionId = positionId;
               g_handled[i].ticket     = 0;
               changed                 = true;
              }
           }
         else
            if(state == ORDER_STATE_CANCELED || state == ORDER_STATE_EXPIRED || state == ORDER_STATE_REJECTED)
              {
               string why = (state == ORDER_STATE_EXPIRED) ? "expired at the broker"
                            : (state == ORDER_STATE_REJECTED) ? "rejected by the broker after it was placed"
                            : "cancelled outside the EA";
               QueueEvent("cancelled:" + IntegerToString((long)order), "order_cancelled", g_handled[i].id,
                          JI("order_ticket", (long)order) + "," + JS("message", why));
               PrintFormat("[LIVE] order %I64u %s [%s]", order, why, StringSubstr(g_handled[i].id, 0, 8));
               g_handled[i].ticket      = 0;
               g_handled[i].orderTicket = 0;
               changed                  = true;
              }
        }

      if(g_handled[i].positionId > 0 && g_handled[i].closedReported == 0 && !PositionOpen(g_handled[i].positionId))
        {
         if(ReportClosed(i))
           {
            g_handled[i].closedReported = 1;
            changed                     = true;
           }
        }
     }
   if(changed)
      SaveState();
  }

//+------------------------------------------------------------------+
bool ReportOpened(const int index, const ulong positionId)
  {
   if(!HistorySelectByPosition(positionId))
      return(false);
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0 || (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;
      string side  = ((ENUM_DEAL_TYPE)HistoryDealGetInteger(deal, DEAL_TYPE) == DEAL_TYPE_BUY) ? "buy" : "sell";
      double price = HistoryDealGetDouble(deal, DEAL_PRICE);
      double lots  = HistoryDealGetDouble(deal, DEAL_VOLUME);
      QueueEvent("opened:" + IntegerToString((long)positionId), "position_opened", g_handled[index].id,
                 JS("order_type", side) + "," + JI("order_ticket", (long)g_handled[index].orderTicket) + "," +
                 JI("position_id", (long)positionId) + "," + JV("volume", lots) + "," + JP("price", price),
                 ServerToWebsite((datetime)HistoryDealGetInteger(deal, DEAL_TIME)));
      PrintFormat("[LIVE] filled %s %.2f lots @ %s | position %I64u [%s]", side, lots, PriceText(price),
                  positionId, StringSubstr(g_handled[index].id, 0, 8));
      return(true);
     }
   return(false); // history not loaded yet - try again next check
  }

//+------------------------------------------------------------------+
//| Profit is net of commission, swap and fees across every deal of the
//| position, including partial closes.
bool ReportClosed(const int index)
  {
   ulong positionId = g_handled[index].positionId;
   if(!HistorySelectByPosition(positionId))
      return(false);

   double   net       = 0.0;
   double   lots      = 0.0;
   double   lastPrice = 0.0;
   datetime lastTime  = 0;
   string   reason    = "other";
   bool     closed    = false;
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0)
         continue;
      net += HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_COMMISSION) +
             HistoryDealGetDouble(deal, DEAL_SWAP) + HistoryDealGetDouble(deal, DEAL_FEE);
      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY)
         continue;
      closed = true;
      lots  += HistoryDealGetDouble(deal, DEAL_VOLUME);
      datetime when = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);
      if(when >= lastTime)
        {
         lastTime  = when;
         lastPrice = HistoryDealGetDouble(deal, DEAL_PRICE);
         reason    = CloseReason((ENUM_DEAL_REASON)HistoryDealGetInteger(deal, DEAL_REASON));
        }
     }
   if(!closed)
      return(false);

   string currency = AccountInfoString(ACCOUNT_CURRENCY);
   QueueEvent("closed:" + IntegerToString((long)positionId), "position_closed", g_handled[index].id,
              JI("position_id", (long)positionId) + "," + JV("volume", lots) + "," + JP("price", lastPrice) + "," +
              JM("profit", net) + "," + JS("currency", currency) + "," + JS("close_reason", reason),
              ServerToWebsite(lastTime));
   PrintFormat("[LIVE] closed position %I64u by %s | net %.2f %s [%s]", positionId, reason, net, currency,
               StringSubstr(g_handled[index].id, 0, 8));
   return(true);
  }

//+------------------------------------------------------------------+
string CloseReason(const ENUM_DEAL_REASON reason)
  {
   if(reason == DEAL_REASON_TP)
      return("tp");
   if(reason == DEAL_REASON_SL)
      return("sl");
   if(reason == DEAL_REASON_SO)
      return("stop_out");
   if(reason == DEAL_REASON_EXPERT)
      return("expert");
   if(reason == DEAL_REASON_CLIENT || reason == DEAL_REASON_MOBILE || reason == DEAL_REASON_WEB)
      return("manual");
   return("other");
  }

//+------------------------------------------------------------------+
//| Filled positions are never modified here: the broker's own stop
//| loss and take profit, set from the signal, close them.
bool IsOwnPendingOrder(const ulong ticket)
  {
   return(ticket > 0 && OrderSelect(ticket) && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagicNumber);
  }

//+------------------------------------------------------------------+
//| By identifier, not ticket: on a netting account they differ.
bool PositionOpen(const ulong positionId)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER) == positionId)
         return(true);
   return(false);
  }

//+------------------------------------------------------------------+
int CountOwnTrades()
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagicNumber &&
         PositionGetString(POSITION_SYMBOL) == InpBrokerSymbol)
         count++;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
      if(OrderGetTicket(i) > 0 && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagicNumber &&
         OrderGetString(ORDER_SYMBOL) == InpBrokerSymbol)
         count++;
   return(count);
  }

//+------------------------------------------------------------------+
bool HasTradeWithComment(const string comment)
  {
   return(FindPositionId(comment) > 0 || FindPendingTicket(comment) > 0);
  }

//+------------------------------------------------------------------+
ulong FindPositionId(const string comment)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagicNumber &&
         StringFind(PositionGetString(POSITION_COMMENT), comment) == 0)
         return((ulong)PositionGetInteger(POSITION_IDENTIFIER));
   return(0);
  }

//+------------------------------------------------------------------+
ulong FindPendingTicket(const string comment)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0 && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagicNumber &&
         StringFind(OrderGetString(ORDER_COMMENT), comment) == 0)
         return(ticket);
     }
   return(0);
  }

//+------------------------------------------------------------------+
//| Symbol and time helpers                                          |
//+------------------------------------------------------------------+
double NormalizeVolume(const double lots)
  {
   double minVolume = SymbolInfoDouble(InpBrokerSymbol, SYMBOL_VOLUME_MIN);
   double maxVolume = SymbolInfoDouble(InpBrokerSymbol, SYMBOL_VOLUME_MAX);
   double step      = SymbolInfoDouble(InpBrokerSymbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      return(0.0);
// Round down to the lot step - never trade more than was configured.
   double volume = MathFloor(lots / step + 1e-9) * step;
   if(volume < minVolume - 1e-9)
      return(0.0);
   volume = MathMin(volume, maxVolume);

   int    digits = 0;
   double scaled = step;
   while(digits < 8 && MathAbs(scaled - MathRound(scaled)) > 1e-9)
     {
      scaled *= 10.0;
      digits++;
     }
   return(NormalizeDouble(volume, digits));
  }

//+------------------------------------------------------------------+
double NormalizePrice(const double price)
  {
   double tickSize = SymbolInfoDouble(InpBrokerSymbol, SYMBOL_TRADE_TICK_SIZE);
   int    digits   = (int)SymbolInfoInteger(InpBrokerSymbol, SYMBOL_DIGITS);
   double value    = (tickSize > 0.0) ? MathRound(price / tickSize) * tickSize : price;
   return(NormalizeDouble(value, digits));
  }

//+------------------------------------------------------------------+
string PriceText(const double price)
  {
   return(DoubleToString(price, (int)SymbolInfoInteger(InpBrokerSymbol, SYMBOL_DIGITS)));
  }

//+------------------------------------------------------------------+
string OrderTypeText(const ENUM_ORDER_TYPE type)
  {
   if(type == ORDER_TYPE_BUY)
      return("buy");
   if(type == ORDER_TYPE_SELL)
      return("sell");
   if(type == ORDER_TYPE_BUY_LIMIT)
      return("buy_limit");
   if(type == ORDER_TYPE_SELL_LIMIT)
      return("sell_limit");
   return("other");
  }

//+------------------------------------------------------------------+
bool SupportsSpecifiedExpiry()
  {
   return((SymbolInfoInteger(InpBrokerSymbol, SYMBOL_EXPIRATION_MODE) & SYMBOL_EXPIRATION_SPECIFIED) != 0);
  }

//+------------------------------------------------------------------+
//| Same choice CTrade::SetTypeFillingBySymbol makes, so a dry-run check
//| matches what a live order would send.
ENUM_ORDER_TYPE_FILLING FillingFor(const string symbol)
  {
   long mode = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((mode & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      return(ORDER_FILLING_FOK);
   if((mode & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      return(ORDER_FILLING_IOC);
   return(ORDER_FILLING_RETURN);
  }

//+------------------------------------------------------------------+
datetime WebsiteNow()
  {
   return((datetime)((long)TimeGMT() + g_clockDrift));
  }

//+------------------------------------------------------------------+
//| Deal times are broker server time; reports are on the website clock.
datetime ServerToWebsite(const datetime serverTime)
  {
   long brokerOffset = (long)TimeTradeServer() - (long)TimeGMT();
   return((datetime)((long)serverTime - brokerOffset + g_clockDrift));
  }

//+------------------------------------------------------------------+
string BaseHost(const string url)
  {
   int scheme = StringFind(url, "://");
   if(scheme < 0)
      return(url);
   int path = StringFind(url, "/", scheme + 3);
   return(path < 0 ? url : StringSubstr(url, 0, path));
  }

//+------------------------------------------------------------------+
//| Activity reports (ADR-162)                                       |
//+------------------------------------------------------------------+
//| Queues one report. The key names what happened, so the website stores
//| it once however many times a lost response makes the EA re-send it.
//| Prefixed with the account and mode so a dry-run "skipped" and a live
//| "skipped" for the same signal are different events.
void QueueEvent(const string key, const string type, const string signalId, const string fields,
                const datetime occurredAt = 0)
  {
   if(!InpReportActivity)
      return;
   long     login   = AccountInfoInteger(ACCOUNT_LOGIN);
   string   fullKey = StringFormat("%I64d:%s:%s", login, InpDryRun ? "dry" : "live", key);
   datetime when    = (occurredAt > 0) ? occurredAt : WebsiteNow();
   string   json    = "{" + JS("event_key", fullKey) + "," + JS("event_type", type) + "," +
                      JS("signal_id", signalId) + ",\"dry_run\":" + (InpDryRun ? "true" : "false") + "," +
                      JI("occurred_at", (long)when) + "," + JS("account_login", IntegerToString(login)) + "," +
                      JS("broker_symbol", InpBrokerSymbol) + (StringLen(fields) > 0 ? "," + fields : "") + "}";

   int n = ArraySize(g_events);
   if(n >= MAX_QUEUED_EVENTS)
     {
      for(int i = 1; i < n; i++)
         g_events[i - 1] = g_events[i];
      n--;
      ArrayResize(g_events, n);
      LogOnce(StringFormat("report queue full (%d) - dropped the oldest report", MAX_QUEUED_EVENTS));
     }
   ArrayResize(g_events, n + 1);
   g_events[n] = json;
   SaveEvents();
  }

//+------------------------------------------------------------------+
//| Sends up to one batch. Kept on any failure except 422: a batch the
//| website calls malformed will never be accepted, and keeping it would
//| block every report behind it.
void FlushEvents()
  {
   int count = MathMin(ArraySize(g_events), EVENT_BATCH_SIZE);
   if(count == 0)
      return;

   string body = "{\"events\":[";
   for(int i = 0; i < count; i++)
      body += (i > 0 ? "," : "") + g_events[i];
   body += "]}";

   char   data[];
   char   result[];
   string resultHeaders;
   int    length = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(length > 0)
      ArrayResize(data, length - 1); // drop the terminating zero - it is not part of the JSON

   string headers = "Content-Type: application/json\r\nX-EA-Token: " + InpEaToken + "\r\n";
   ResetLastError();
   int code = WebRequest("POST", InpApiBaseUrl + "/ea/events", headers, 10000, data, result, resultHeaders);

   if(code == 200 || code == 422)
     {
      if(code == 422)
         PrintFormat("the website refused %d activity reports as malformed - dropped so later ones can send", count);
      int remaining = ArraySize(g_events) - count;
      for(int i = 0; i < remaining; i++)
         g_events[i] = g_events[i + count];
      ArrayResize(g_events, remaining);
      SaveEvents();
      return;
     }

   LogOnce(StringFormat("%d activity reports waiting to send (%s)", ArraySize(g_events),
                        code == -1 ? StringFormat("error %d", GetLastError()) : StringFormat("HTTP %d", code)));
  }

//+------------------------------------------------------------------+
string JS(const string key, const string value)
  {
   return("\"" + key + "\":\"" + JsonEscape(StringSubstr(value, 0, 200)) + "\"");
  }

string JI(const string key, const long value)
  {
   return("\"" + key + "\":" + IntegerToString(value));
  }

string JP(const string key, const double value)
  {
   return("\"" + key + "\":" + DoubleToString(value, (int)SymbolInfoInteger(InpBrokerSymbol, SYMBOL_DIGITS)));
  }

string JV(const string key, const double value)
  {
   return("\"" + key + "\":" + DoubleToString(value, 8));
  }

string JM(const string key, const double value)
  {
   return("\"" + key + "\":" + DoubleToString(value, 2));
  }

//+------------------------------------------------------------------+
string JsonEscape(string text)
  {
   StringReplace(text, "\\", "\\\\");
   StringReplace(text, "\"", "\\\"");
   StringReplace(text, "\r", " ");
   StringReplace(text, "\n", " ");
   StringReplace(text, "\t", " ");
   return(text);
  }

//+------------------------------------------------------------------+
void LoadEvents()
  {
   ArrayResize(g_events, 0);
   if(!FileIsExist(g_eventsFile))
      return;
   int handle = FileOpen(g_eventsFile, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;
   while(!FileIsEnding(handle))
     {
      string line = FileReadString(handle);
      if(StringLen(line) < 2)
         continue;
      int n = ArraySize(g_events);
      ArrayResize(g_events, n + 1);
      g_events[n] = line;
     }
   FileClose(handle);
   if(ArraySize(g_events) > 0)
      PrintFormat("%d activity reports from last session are waiting to send", ArraySize(g_events));
  }

//+------------------------------------------------------------------+
void SaveEvents()
  {
   int handle = FileOpen(g_eventsFile, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
     {
      LogOnce(StringFormat("could not write %s (error %d)", g_eventsFile, GetLastError()));
      return;
     }
   for(int i = 0; i < ArraySize(g_events); i++)
      FileWriteString(handle, g_events[i] + "\r\n");
   FileClose(handle);
  }

//+------------------------------------------------------------------+
//| State: which signals this EA has already acted on                |
//+------------------------------------------------------------------+
int FindHandled(const string id)
  {
   for(int i = 0; i < ArraySize(g_handled); i++)
      if(g_handled[i].id == id)
         return(i);
   return(-1);
  }

//+------------------------------------------------------------------+
void Remember(const string id, const ulong ticket, const int kind, const datetime expiresAt,
              const ulong orderTicket = 0, const ulong positionId = 0)
  {
   int n = ArraySize(g_handled);
   ArrayResize(g_handled, n + 1);
   g_handled[n].id             = id;
   g_handled[n].ticket         = ticket;
   g_handled[n].kind           = kind;
   g_handled[n].expiresAt      = expiresAt;
   g_handled[n].orderTicket    = orderTicket;
   g_handled[n].positionId     = positionId;
   g_handled[n].closedReported = 0;
   SaveState();
  }

//+------------------------------------------------------------------+
//| Keeps a week of history past expiry, then forgets - long after the
//| website stops listing the signal, so it can never be re-traded. A
//| position still open, or closed but not yet reported, is always kept.
void PruneState()
  {
   datetime cutoff = (datetime)((long)WebsiteNow() - 7 * 24 * 3600);
   int      kept   = 0;
   for(int i = 0; i < ArraySize(g_handled); i++)
     {
      bool unresolved = IsOwnPendingOrder(g_handled[i].ticket) || g_handled[i].orderTicket > 0 ||
                        (g_handled[i].positionId > 0 && g_handled[i].closedReported == 0);
      if(g_handled[i].expiresAt < cutoff && !unresolved)
         continue;
      g_handled[kept++] = g_handled[i];
     }
   if(kept != ArraySize(g_handled))
     {
      ArrayResize(g_handled, kept);
      SaveState();
     }
  }

//+------------------------------------------------------------------+
//| Reads both the 1.00 format (4 fields) and 1.10 (7 fields).
void LoadState()
  {
   ArrayResize(g_handled, 0);
   if(!FileIsExist(g_stateFile))
      return;
   int handle = FileOpen(g_stateFile, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
     {
      PrintFormat("could not read %s (error %d) - starting with no history", g_stateFile, GetLastError());
      return;
     }
   while(!FileIsEnding(handle))
     {
      string parts[];
      int    fields = StringSplit(FileReadString(handle), ';', parts);
      if(fields != 4 && fields != 7)
         continue;
      int n = ArraySize(g_handled);
      ArrayResize(g_handled, n + 1);
      g_handled[n].id             = parts[0];
      g_handled[n].ticket         = (ulong)StringToInteger(parts[1]);
      g_handled[n].kind           = (int)StringToInteger(parts[2]);
      g_handled[n].expiresAt      = (datetime)StringToInteger(parts[3]);
      g_handled[n].orderTicket    = (fields == 7) ? (ulong)StringToInteger(parts[4]) : g_handled[n].ticket;
      g_handled[n].positionId     = (fields == 7) ? (ulong)StringToInteger(parts[5]) : 0;
      g_handled[n].closedReported = (fields == 7) ? (int)StringToInteger(parts[6]) : 0;
     }
   FileClose(handle);
   PrintFormat("loaded %d handled signals from %s", ArraySize(g_handled), g_stateFile);
  }

//+------------------------------------------------------------------+
void SaveState()
  {
   int handle = FileOpen(g_stateFile, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
     {
      LogOnce(StringFormat("could not write %s (error %d)", g_stateFile, GetLastError()));
      return;
     }
   for(int i = 0; i < ArraySize(g_handled); i++)
      FileWriteString(handle, StringFormat("%s;%I64u;%d;%I64d;%I64u;%I64u;%d\r\n", g_handled[i].id,
                                           g_handled[i].ticket, g_handled[i].kind,
                                           (long)g_handled[i].expiresAt, g_handled[i].orderTicket,
                                           g_handled[i].positionId, g_handled[i].closedReported));
   FileClose(handle);
  }

//+------------------------------------------------------------------+
//| Display                                                          |
//+------------------------------------------------------------------+
//| Logs the feed status only when it changes, and keeps it apart from
//| LogOnce - otherwise every successful check would reset LogOnce and a
//| lasting trade message ("waiting: 1 of 1 trades open") would repeat on
//| every poll.
void SetStatus(const string status)
  {
   if(status == g_status)
      return;
   g_status = status;
   Print("feed: ", status == "ok" ? "connected, reading signals" : status);
  }

//+------------------------------------------------------------------+
//| Prints a message only when it differs from the last one, so a
//| condition lasting hours logs once instead of every few seconds.
void LogOnce(const string message)
  {
   if(message == g_lastLogged)
      return;
   g_lastLogged = message;
   Print(message);
  }

//+------------------------------------------------------------------+
void UpdatePanel()
  {
   Comment(StringFormat("VC Trading EA 1.10  -  %s\nFeed: %s  (checked %s)\nOpen signals: %d   EA trades: %d / %d\n%s -> %s   lot %.2f\nReports waiting: %d",
                        InpDryRun ? "DRY RUN (no orders sent)" : "LIVE", g_status,
                        TimeToString(TimeLocal(), TIME_SECONDS), g_openSignalCount, CountOwnTrades(),
                        InpMaxOpenTrades, InpSignalSymbol, InpBrokerSymbol, InpLotSize, ArraySize(g_events)));
  }
//+------------------------------------------------------------------+
