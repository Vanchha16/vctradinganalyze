//+------------------------------------------------------------------+
//|                                                  VCTradingEA.mq5 |
//|  Trades VC Trading AI signals inside this MetaTrader 5 terminal. |
//|                                                                  |
//|  ADR-161. The website never places trades and never sees the     |
//|  broker login: this EA reads GET /ea/signals and does all the    |
//|  trading here. Dry run is the default.                           |
//+------------------------------------------------------------------+
#property copyright   "VC Trading AI"
#property version     "1.00"
#property description "Reads the VC Trading AI signal feed and trades it in this terminal."
#property description "Dry run by default: every order is logged and checked, never sent."

#include <Trade\Trade.mqh>

//--- inputs -----------------------------------------------------------
input group "Connection"
input string InpApiBaseUrl  = "https://vcanalyzetrading.site/api/v1"; // API base URL
input string InpEaToken     = "";      // EA token from Settings (starts with vcea_)
input int    InpPollSeconds = 10;      // Seconds between feed checks (minimum 5)

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
#define KIND_PENDING  1 // limit order sent; ticket recorded
#define KIND_MARKET   2 // market order sent (price had already reached entry)
#define KIND_SKIPPED  3 // not traded: setup invalid at current prices, or lot below minimum
#define KIND_REJECTED 4 // broker refused, or outcome unknown - never retried

// An order needs at least this long before the signal expires to be worth placing.
#define MIN_SECONDS_BEFORE_EXPIRY 300

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
   ulong             ticket;    // pending order ticket, 0 when there is none to manage
   int               kind;
   datetime          expiresAt;
  };

//--- state -------------------------------------------------------------
CTrade        g_trade;
HandledSignal g_handled[];
string        g_stateFile        = "";
long          g_clockDrift       = 0;   // website clock minus this PC's GMT clock, seconds
string        g_status           = "waiting for first check";
string        g_lastLogged       = "";
int           g_openSignalCount  = 0;

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
   g_stateFile = StringFormat("%s\\handled_%I64d_%I64d_%s.txt", STATE_FOLDER,
                              AccountInfoInteger(ACCOUNT_LOGIN), (long)InpMagicNumber,
                              InpDryRun ? "dry" : "live");
   LoadState();

   if(!EventSetTimer(MathMax(InpPollSeconds, 5)))
      return(INIT_FAILED);

   PrintFormat("VC Trading EA started - %s | %s -> %s | lot %.2f | max trades %d | state %s",
               InpDryRun ? "DRY RUN (no orders are sent)" : "LIVE", InpSignalSymbol,
               InpBrokerSymbol, InpLotSize, InpMaxOpenTrades, g_stateFile);
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

// Expiry uses only the local clock, so it runs even when the website
// cannot be reached - an unfilled order must not outlive its signal.
   CancelExpiredOrders();

// Everything below trusts the feed, so it runs only on a response that
// arrived and parsed in full. A failed request never means "no signals".
   if(fetched)
     {
      g_openSignalCount = ArraySize(signals);
      CancelOrdersForClosedSignals(signals);
      for(int i = 0; i < ArraySize(signals); i++)
         HandleSignal(signals[i]);
      PruneState();
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

   datetime websiteNow = (datetime)((long)TimeGMT() + g_clockDrift);
   if((long)s.expiresAt - (long)websiteNow < MIN_SECONDS_BEFORE_EXPIRY)
      return;

   string comment = COMMENT_PREFIX + StringSubstr(s.id, 0, 8);
   if(HasTradeWithComment(comment))
     {
      // The state file was lost but the order exists - adopt it, do not duplicate it.
      Remember(s.id, FindPendingTicket(comment), KIND_PENDING, s.expiresAt);
      return;
     }
   if(CountOwnTrades() >= InpMaxOpenTrades)
     {
      LogOnce(StringFormat("signal %s waiting: %d of %d trades already open",
                           StringSubstr(s.id, 0, 8), CountOwnTrades(), InpMaxOpenTrades));
      return; // not remembered - reconsidered once a trade closes, while still active
     }

   double volume = NormalizeVolume(InpLotSize);
   if(volume <= 0.0)
     {
      Remember(s.id, 0, KIND_SKIPPED, s.expiresAt);
      PrintFormat("signal %s skipped: LotSize %.2f is below %s's minimum lot", StringSubstr(s.id, 0, 8),
                  InpLotSize, InpBrokerSymbol);
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
      Remember(s.id, 0, KIND_SKIPPED, s.expiresAt);
      PrintFormat("signal %s skipped: price (bid %s / ask %s) is already past its stop or target",
                  StringSubstr(s.id, 0, 8), PriceText(tick.bid), PriceText(tick.ask));
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
   double price = market ? (isBuy ? tick.ask : tick.bid) : entry;
   string what  = StringFormat("%s %s %.2f lots @ %s  SL %s  TP %s  expires %s UTC  [%s]",
                               EnumToString(type), InpBrokerSymbol, volume, PriceText(price),
                               PriceText(sl), PriceText(tp), TimeToString(s.expiresAt),
                               StringSubstr(s.id, 0, 8));

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

      bool passed = OrderCheck(request, check);
      PrintFormat("[DRY RUN] %s | broker check: %s (retcode %u %s, margin %.2f, free margin after %.2f)",
                  what, passed ? "would be accepted" : "WOULD BE REFUSED", check.retcode,
                  check.comment, check.margin, check.margin_free);
      Remember(s.id, 0, KIND_DRY_RUN, s.expiresAt);
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
      Remember(s.id, market ? 0 : g_trade.ResultOrder(), market ? KIND_MARKET : KIND_PENDING, s.expiresAt);
      PrintFormat("[LIVE] placed %s | ticket %I64u", what, g_trade.ResultOrder());
      return;
     }

   if(IsRetryable(retcode))
     {
      LogOnce(StringFormat("[LIVE] %s not placed yet (%u %s) - will retry", StringSubstr(s.id, 0, 8),
                           retcode, g_trade.ResultRetcodeDescription()));
      return;
     }

   Remember(s.id, 0, KIND_REJECTED, s.expiresAt);
   PrintFormat("[LIVE] NOT placed, not retrying: %s | %u %s", what, retcode,
               g_trade.ResultRetcodeDescription());
   if(retcode == TRADE_RETCODE_TIMEOUT)
      Print("[LIVE] the broker timed out - the order may exist anyway. Check the Trade tab.");
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
   datetime websiteNow = (datetime)((long)TimeGMT() + g_clockDrift);
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
      g_handled[index].ticket = 0;
      SaveState();
     }
   else
      LogOnce(StringFormat("[LIVE] could not cancel order %I64u (%u %s) - will retry", ticket,
                           g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription()));
  }

//+------------------------------------------------------------------+
//| Filled positions are never looked at here: the broker's own stop
//| loss and take profit, set from the signal, close them.
bool IsOwnPendingOrder(const ulong ticket)
  {
   return(OrderSelect(ticket) && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagicNumber);
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
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagicNumber &&
         StringFind(PositionGetString(POSITION_COMMENT), comment) == 0)
         return(true);
   return(FindPendingTicket(comment) > 0);
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
//| Symbol helpers                                                   |
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
string BaseHost(const string url)
  {
   int scheme = StringFind(url, "://");
   if(scheme < 0)
      return(url);
   int path = StringFind(url, "/", scheme + 3);
   return(path < 0 ? url : StringSubstr(url, 0, path));
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
void Remember(const string id, const ulong ticket, const int kind, const datetime expiresAt)
  {
   int n = ArraySize(g_handled);
   ArrayResize(g_handled, n + 1);
   g_handled[n].id        = id;
   g_handled[n].ticket    = ticket;
   g_handled[n].kind      = kind;
   g_handled[n].expiresAt = expiresAt;
   SaveState();
  }

//+------------------------------------------------------------------+
//| Keeps a week of history past expiry, then forgets - long after the
//| website stops listing the signal, so it can never be re-traded.
void PruneState()
  {
   datetime cutoff = (datetime)((long)TimeGMT() + g_clockDrift - 7 * 24 * 3600);
   int      kept   = 0;
   for(int i = 0; i < ArraySize(g_handled); i++)
     {
      if(g_handled[i].expiresAt < cutoff && !IsOwnPendingOrder(g_handled[i].ticket))
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
      if(StringSplit(FileReadString(handle), ';', parts) != 4)
         continue;
      int n = ArraySize(g_handled);
      ArrayResize(g_handled, n + 1);
      g_handled[n].id        = parts[0];
      g_handled[n].ticket    = (ulong)StringToInteger(parts[1]);
      g_handled[n].kind      = (int)StringToInteger(parts[2]);
      g_handled[n].expiresAt = (datetime)StringToInteger(parts[3]);
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
      PrintFormat("could not write %s (error %d)", g_stateFile, GetLastError());
      return;
     }
   for(int i = 0; i < ArraySize(g_handled); i++)
      FileWriteString(handle, StringFormat("%s;%I64u;%d;%I64d\r\n", g_handled[i].id, g_handled[i].ticket,
                                           g_handled[i].kind, (long)g_handled[i].expiresAt));
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
   Comment(StringFormat("VC Trading EA  -  %s\nFeed: %s  (checked %s)\nOpen signals: %d   EA trades: %d / %d\n%s -> %s   lot %.2f",
                        InpDryRun ? "DRY RUN (no orders sent)" : "LIVE", g_status,
                        TimeToString(TimeLocal(), TIME_SECONDS), g_openSignalCount, CountOwnTrades(),
                        InpMaxOpenTrades, InpSignalSymbol, InpBrokerSymbol, InpLotSize));
  }
//+------------------------------------------------------------------+
