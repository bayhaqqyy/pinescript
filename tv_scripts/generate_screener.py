import requests
import json
import os
import time
import sys
import math
import subprocess
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BINANCE_API = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_INFO_API = "https://fapi.binance.com/fapi/v1/exchangeInfo"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, "binance_futures_cache.json")
TOP_N = 100
BATCH_SIZE = 8
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "generated_screeners")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15

TRADFI_SYMBOLS = {
    "AAPLUSDT", "AMDUSDT", "AMZNUSDT", "AVGOUSDT", "BABAUSDT", "BRKBUSDT",
    "BZUSDT", "CBRSUSDT", "CLUSDT", "COINUSDT", "COPPERUSDT", "CRCLUSDT",
    "CRWVUSDT", "CSCOUSDT", "EWYUSDT", "GOOGLUSDT", "INTCUSDT", "MSTRUSDT",
    "MSFTUSDT", "METAUSDT", "NATGASUSDT", "NVDAUSDT", "PAXGUSDT", "QQQUSDT",
    "SOXLUSDT", "SPCXUSDT", "TSLAUSDT", "VUSDT", "XAGUSDT", "XAUUSDT",
    "XPLUSDT",
}

def resolve_doh(domain):
    try:
        # Resolve via Cloudflare DNS-over-HTTPS
        resp = requests.get(f"https://1.1.1.1/dns-query?name={domain}&type=A", headers={"accept": "application/dns-json"}, timeout=5)
        if resp.status_code == 200:
            dns_data = resp.json()
            return [ans["data"] for ans in dns_data.get("Answer", []) if ans["type"] == 1]
    except Exception as e:
        print(f"[DoH] Resolution failed for {domain}: {e}")
    return []

def fetch_api_via_curl(url, domain, resolved_ips):
    for ip in resolved_ips:
        cmd = [
            'curl',
            '-k',
            '-s',
            '--resolve',
            f'{domain}:443:{ip}',
            url
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=15)
            if res.returncode == 0:
                output = res.stdout.decode('utf-8', errors='ignore')
                return json.loads(output)
        except Exception as e:
            print(f"[CURL] Failed with IP {ip}: {e}")
    return None

def fetch_top_pairs():
    print("=" * 60)
    print(" BINANCE USDS-M DASHBOARD GENERATOR")
    print("=" * 60)

    data = None
    info_data = None
    api_success = False

    # Attempt 1: Try direct connection first (since user says they fixed it)
    print("\n[FETCH] Attempting direct connection to Binance Futures API...")
    try:
        # Disable warning for verify=False in case of Windows cert store issues
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        resp = requests.get(BINANCE_API, verify=False, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # If it returned HTML instead of a JSON list/dict, raise error
            if not isinstance(data, (list, dict)):
                raise Exception("Response is not JSON")
                
            resp_info = requests.get(BINANCE_INFO_API, verify=False, timeout=10)
            info_data = resp_info.json()
            if not isinstance(info_data, dict):
                raise Exception("Exchange info response is not JSON")
                
            print(f"[FETCH] Direct connection successful! Received {len(data)} tickers")
            api_success = True
    except Exception as e:
        print(f"[FETCH] Direct connection failed: {e}")

    # Attempt 2: Fallback to DoH + Curl bypass if direct connection failed
    if not api_success:
        print("\n[FETCH] Falling back to secure DNS-over-HTTPS (DoH) + Curl bypass...")
        ips = resolve_doh("fapi.binance.com")
        if not ips:
            print("[DoH] DNS resolution failed, using hardcoded AWS/CloudFront edge IPs...")
            ips = ["13.249.231.24", "13.249.231.26", "13.249.231.94", "13.249.231.124"]

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[FETCH] Attempt {attempt}/{MAX_RETRIES} via Curl resolve...")
                data = fetch_api_via_curl(BINANCE_API, "fapi.binance.com", ips)
                if not data:
                    raise Exception("Failed to fetch tickers")
                    
                info_data = fetch_api_via_curl(BINANCE_INFO_API, "fapi.binance.com", ips)
                if not info_data:
                    raise Exception("Failed to fetch exchange info")
                
                print(f"[FETCH] Secure bypass successful! Received {len(data)} tickers")
                api_success = True
                break
            except Exception as e:
                print(f"[FETCH] Attempt {attempt} failed: {str(e)[:100]}")
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    time.sleep(wait)

    tick_map = {}
    if info_data:
        for sym in info_data.get("symbols", []):
            symbol_name = sym["symbol"]
            for f in sym.get("filters", []):
                if f["filterType"] == "PRICE_FILTER":
                    tick_size_str = f["tickSize"]
                    tick_map[symbol_name] = float(tick_size_str)
                    break

    symbols_with_meta = []
    if api_success:
        filtered = [
            t for t in data
            if t["symbol"].endswith("USDT")
            and "_" not in t["symbol"]
            and t["symbol"] not in TRADFI_SYMBOLS
            and t["symbol"].isascii()
        ]
        # Sort by 24h Change % descending (Top Gainers - matching user's photo!)
        filtered.sort(key=lambda t: float(t.get("priceChangePercent", 0)), reverse=True)
        top = filtered[:TOP_N]

        print(f"\n[INFO] Selected Top {len(top)} pairs by 24h Change descending:")
        for idx, t in enumerate(top[:15]):
            print(f"  {idx+1:2d}. {t['symbol']:15s} Change: {float(t.get('priceChangePercent', 0)):>7.2f}%")

        for t in top:
            sym = t["symbol"]
            tick_size = tick_map.get(sym, 0.001)
            # calculate decimals based on tick size
            price_decimals = 0
            tick_str = str(float(tick_size))
            if "e" in tick_str:
                price_decimals = abs(int(tick_str.split('e')[-1]))
            elif "." in tick_str:
                frac = tick_str.split('.')[1].rstrip('0')
                if frac:
                    price_decimals = len(frac)
            
            symbols_with_meta.append({
                "symbol": sym,
                "tick_size": tick_size,
                "price_decimals": price_decimals
            })
            
        # Update Cache file so we have a fresh 100% correct local copy
        try:
            cache_to_save = {
                "source": "live_api_bypass",
                "count": len(symbols_with_meta),
                "symbols": symbols_with_meta
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as cf:
                json.dump(cache_to_save, cf, indent=2)
            print(f"[CACHE] Saved {len(symbols_with_meta)} fresh pairs to {CACHE_FILE} for future fallback")
        except Exception as ce:
            print(f"[CACHE] Failed to save fresh cache: {ce}")
    else:
        # Fallback: try loading from cache file (populated by CoinGecko or previous runs)
        if os.path.exists(CACHE_FILE):
            print(f"\n[CACHE] Loading from {CACHE_FILE}")
            with open(CACHE_FILE, "r", encoding="utf-8") as cf:
                cache_data = json.load(cf)
            cached_symbols = cache_data.get("symbols", [])
            for s in cached_symbols:
                sym = s["symbol"]
                # Skip non-ASCII symbols and TradFi
                if not sym.isascii() or sym in TRADFI_SYMBOLS:
                    continue
                symbols_with_meta.append({
                    "symbol": sym,
                    "tick_size": s.get("tick_size", 0.001),
                    "price_decimals": s.get("price_decimals", 3),
                })
            # Limit to TOP_N
            symbols_with_meta = symbols_with_meta[:TOP_N]
            print(f"[CACHE] Loaded {len(symbols_with_meta)} pairs from cache")
        else:
            print("\n[WARN] No cache file found, using hardcoded fallback")
            HARDCODED = [
                "BTCUSDT", "ETHUSDT", "HYPEUSDT", "SOLUSDT", "XRPUSDT",
                "NEARUSDT", "DOGEUSDT", "BNBUSDT", "SUIUSDT", "ADAUSDT",
                "1000PEPEUSDT", "ONDOUSDT", "WLDUSDT", "TAOUSDT", "LINKUSDT",
                "TONUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT", "FILUSDT",
                "INJUSDT", "ENAUSDT", "TRUMPUSDT", "FETUSDT", "AAVEUSDT",
                "TRXUSDT", "ICPUSDT", "UNIUSDT", "BCHUSDT", "ARBUSDT",
                "TIAUSDT", "VIRTUALUSDT", "XMRUSDT", "RENDERUSDT", "XLMUSDT",
                "ETCUSDT", "APTUSDT", "CHZUSDT", "1000SHIBUSDT", "OPUSDT",
                "HBARUSDT", "GENIUSUSDT", "ALTUSDT", "AGTUSDT",
            ]
            for sym in HARDCODED:
                tick_size = 0.001
                if sym.startswith("1000"):
                    tick_size = 0.0000001
                elif sym == "BTCUSDT":
                    tick_size = 0.1
                elif sym == "ETHUSDT":
                    tick_size = 0.01
                    
                price_decimals = 0
                tick_str = str(float(tick_size))
                if "e" in tick_str:
                    price_decimals = abs(int(tick_str.split('e')[-1]))
                elif "." in tick_str:
                    frac = tick_str.split('.')[1].rstrip('0')
                    if frac:
                        price_decimals = len(frac)
                    
                symbols_with_meta.append({
                    "symbol": sym,
                    "tick_size": tick_size,
                    "price_decimals": price_decimals
                })
    return symbols_with_meta

ENGINE_TEMPLATE = """
// ============================================================================
// INPUTS
// ============================================================================
tf = input.timeframe("15", "Timeframe Screener")

srLen = input.int(14, "S/R Length")
atrLen = input.int(14, "ATR Length")
leverage = input.int(10, "Leverage", minval=1, maxval=125)

entryScore = input.int(65, "Entry Score")
scoreGap = input.int(6, "Score Gap")

slAtrMult = input.float(1.4, "SL ATR Mult (Wider)", step=0.1)
tpAtrMult = input.float(2.4, "TP ATR Mult (Wider)", step=0.1)
minRR = input.float(1.6, "Minimum RR (Wider)", step=0.1)

minSlRawPct = input.float(0.6, "Minimum SL Raw % (Wider)", step=0.1)
minTpRawPct = input.float(1.0, "Minimum TP Raw % (Wider)", step=0.1)
maxPlanRiskPct = input.float(2.0, "Max Raw Risk % For Action", step=0.5)
maxLevRiskPct = input.float(25.0, "Max Leveraged Risk % For Action", step=5.0)

breakoutBufferPct = input.float(0.05, "Breakout Buffer %", step=0.01)
srAtrBuffer = input.float(0.20, "S/R ATR Buffer", step=0.05)
useStructureSL = input.bool(true, "Use Structure SL When Reasonable")
maxStructureRiskPct = input.float(2.5, "Max Structure SL %", step=0.5)

cooldownBars = input.int(3, "Alert Cooldown Bars", minval=1)

pos = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

sameBarRule = input.string("SL_FIRST", "Same Bar TP/SL Rule", options=["SL_FIRST", "TP_FIRST", "IGNORE"])
useReversalEntry = input.bool(false, "Use Reversal As Entry")

// ============================================================================
// COLORS & HELPERS
// ============================================================================
cHeader = color.rgb(55, 62, 70)
cDark = color.rgb(28, 33, 40)
cText = color.white
cGreen = color.rgb(0, 180, 90)
cLime = color.rgb(70, 220, 90)
cBlue = color.rgb(40, 130, 220)
cYellow = color.rgb(220, 190, 40)
cOrange = color.rgb(230, 120, 40)
cRed = color.rgb(220, 60, 60)
cGray = color.rgb(110, 110, 110)

f_risk_label(levRiskPct) =>
    na(levRiskPct) ? "NO_DATA" :
      levRiskPct <= 35 ? "SAFE" :
      levRiskPct <= 65 ? "RISKY" :
      "HIGH"

f_risk_color(risk) =>
    risk == "SAFE" ? cLime :
      risk == "RISKY" ? cOrange :
      cRed

f_action_color(act) =>
    act == "LONG" ? cLime :
      act == "SHORT" ? cRed :
      cGray

f_signal_color(sig) =>
    sig == "LONG" ? cLime :
      sig == "SHORT" ? cRed :
      sig == "RISKY" ? cOrange :
      cGray

f_score_color(score) =>
    score >= 80 ? cLime :
      score >= 60 ? cGreen :
      score >= 40 ? cOrange :
      cRed

f_cell(tbl, col, row, txt, bg, txtColor) =>
    table.cell(tbl, col, row, txt, bgcolor=bg, text_color=txtColor, text_size=size.small)

f_header(tbl, col, title) =>
    table.cell(tbl, col, 0, title, bgcolor=cHeader, text_color=color.yellow, text_size=size.small)

f_fmt_price(val, tickSize) =>
    str.tostring(val, tickSize == 0.1 ? "0.0" : tickSize == 0.01 ? "0.00" : tickSize == 0.001 ? "0.000" : tickSize == 0.0001 ? "0.0000" : tickSize == 0.00001 ? "0.00000" : tickSize == 0.000001 ? "0.000000" : tickSize == 0.0000001 ? "0.0000000" : tickSize == 0.00000001 ? "0.00000000" : "0.00")

// ============================================================================
// DASHBOARD ENGINE
// ============================================================================
f_dashboard_engine() =>
    sup = ta.lowest(low[1], srLen)
    rst = ta.highest(high[1], srLen)
    atrVal = ta.atr(atrLen)
    
    validData = not na(close) and close > 0 and not na(atrVal) and atrVal > 0 and not na(sup) and not na(rst)
    
    buf = breakoutBufferPct / 100.0
    longTrigger  = rst * (1 + buf)
    shortTrigger = sup * (1 - buf)
    
    longBreak  = close >= longTrigger
    shortBreak = close <= shortTrigger
    
    entryLong  = close
    entryShort = close
    
    // SL LONG
    baseSlLongDist = math.max(atrVal * slAtrMult, entryLong * minSlRawPct / 100.0, syminfo.mintick)
    structSlLong = sup - atrVal * srAtrBuffer
    structSlLongDist = entryLong - structSlLong
    structRiskLongPct = entryLong > 0 ? structSlLongDist / entryLong * 100.0 : na
    useStructLong = useStructureSL and not na(structSlLongDist) and structSlLongDist > 0 and structRiskLongPct <= maxStructureRiskPct
    slLongDist = useStructLong ? math.max(baseSlLongDist, structSlLongDist) : baseSlLongDist
    slLong = entryLong - slLongDist
    
    // SL SHORT
    baseSlShortDist = math.max(atrVal * slAtrMult, entryShort * minSlRawPct / 100.0, syminfo.mintick)
    structSlShort = rst + atrVal * srAtrBuffer
    structSlShortDist = structSlShort - entryShort
    structRiskShortPct = entryShort > 0 ? structSlShortDist / entryShort * 100.0 : na
    useStructShort = useStructureSL and not na(structSlShortDist) and structSlShortDist > 0 and structRiskShortPct <= maxStructureRiskPct
    slShortDist = useStructShort ? math.max(baseSlShortDist, structSlShortDist) : baseSlShortDist
    slShort = entryShort + slShortDist
    
    // TP LONG
    tpLongDist = math.max(atrVal * tpAtrMult, entryLong * minTpRawPct / 100.0, slLongDist * minRR)
    tpLong = entryLong + tpLongDist
    
    // TP SHORT
    tpShortDist = math.max(atrVal * tpAtrMult, entryShort * minTpRawPct / 100.0, slShortDist * minRR)
    tpShort = math.max(entryShort - tpShortDist, 0.00000001)
    
    dirOkLong  = tpLong > entryLong and slLong < entryLong
    dirOkShort = tpShort < entryShort and slShort > entryShort
    
    riskOkLong = entryLong > 0 and (slLongDist / entryLong * 100.0) <= maxPlanRiskPct and (slLongDist / entryLong * 100.0 * leverage) <= maxLevRiskPct and (slLongDist > 0 ? tpLongDist / slLongDist : 0) >= minRR
    riskOkShort = entryShort > 0 and (slShortDist / entryShort * 100.0) <= maxPlanRiskPct and (slShortDist / entryShort * 100.0 * leverage) <= maxLevRiskPct and (slShortDist > 0 ? tpShortDist / slShortDist : 0) >= minRR
    
    // Indicators
    emaFast = ta.ema(close, 20)
    emaSlow = ta.ema(close, 50)
    rsiVal = ta.rsi(close, 14)
    [macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)
    volMA = ta.sma(volume, 20)
    rvol = volMA > 0 ? volume / volMA : na
    volOk = not na(rvol) and rvol >= 1.0
    
    // Candle Behavior
    body = math.abs(close - open)
    barRange = math.max(high - low, syminfo.mintick)
    greenCandle = close > open
    redCandle = close < open
    closeNearHigh = barRange > 0 ? close >= low + barRange * 0.65 : false
    closeNearLow  = barRange > 0 ? close <= low + barRange * 0.35 : false
    
    upperReject = body > 0 ? (high - math.max(open, close)) >= body * 0.8 : false
    lowerReject = body > 0 ? (math.min(open, close) - low) >= body * 0.8 : false
    
    // Bias
    trendLong = close > emaFast and emaFast > emaSlow
    trendShort = close < emaFast and emaFast < emaSlow
    momentumLong = rsiVal >= 50 and rsiVal <= 72 and hist > 0 and hist >= hist[1]
    momentumShort = rsiVal <= 50 and rsiVal >= 28 and hist < 0 and hist <= hist[1]
    
    overheat = rsiVal > 72 or close > emaFast + atrVal * 1.8
    oversold = rsiVal < 28 or close < emaFast - atrVal * 1.8
    
    bullishImpulse = greenCandle and closeNearHigh and close > close[1]
    bearishImpulse = redCandle and closeNearLow and close < close[1]
    
    // Pullback Entry
    nearEmaLong = low <= emaFast + atrVal * 0.25 and close > emaFast
    nearEmaShort = high >= emaFast - atrVal * 0.25 and close < emaFast
    
    longPullbackAction = trendLong and nearEmaLong and greenCandle and closeNearHigh and hist > hist[1] and rsiVal > 50 and volOk
    shortPullbackAction = trendShort and nearEmaShort and redCandle and closeNearLow and hist < hist[1] and rsiVal < 50 and volOk
    
    // Actions
    longTrendAction = trendLong and momentumLong and volOk and greenCandle and closeNearHigh and not overheat
    shortTrendAction = trendShort and momentumShort and volOk and redCandle and closeNearLow and not oversold
    
    longBreakoutAction = close > longTrigger and greenCandle and closeNearHigh and volOk
    shortBreakdownAction = close < shortTrigger and redCandle and closeNearLow and volOk
    
    longReversalAction = useReversalEntry and oversold and lowerReject and greenCandle and closeNearHigh and rvol >= 1.2 and hist > hist[1] and close > emaFast
    shortReversalAction = useReversalEntry and overheat and upperReject and redCandle and closeNearLow and rvol >= 1.2 and hist < hist[1] and close < emaFast
    
    validLongAction = validData and (longTrendAction or longPullbackAction or longBreakoutAction or longReversalAction) and riskOkLong and dirOkLong
    validShortAction = validData and (shortTrendAction or shortPullbackAction or shortBreakdownAction or shortReversalAction) and riskOkShort and dirOkShort
    
    if bullishImpulse
        validShortAction := false
    if bearishImpulse
        validLongAction := false
        
    // Flow
    lowerWick = math.min(open, close) - low
    upperWick = high - math.max(open, close)
    longAbsorb  = lowerWick > body * 1.2 and closeNearHigh and rvol >= 1.3
    shortAbsorb = upperWick > body * 1.2 and closeNearLow and rvol >= 1.3
    smallBodyHighVol = body <= atrVal * 0.30 and rvol >= 1.8
    
    bullImpulse = greenCandle and closeNearHigh and rvol >= 1.2
    bearImpulse = redCandle and closeNearLow and rvol >= 1.2
    
    longFlow = (bullImpulse and trendLong) or longAbsorb
    shortFlow = (bearImpulse and trendShort) or shortAbsorb
    
    flowConflict = (validShortAction and longFlow) or (validLongAction and shortFlow)
    if flowConflict
        validLongAction := false
        validShortAction := false
        
    // Scoring
    scoreLong = 0.0
    scoreLong += trendLong ? 20.0 : 0.0
    scoreLong += momentumLong ? 20.0 : 0.0
    scoreLong += volOk ? 15.0 : 0.0
    scoreLong += greenCandle ? 15.0 : 0.0
    scoreLong += closeNearHigh ? 10.0 : 0.0
    scoreLong += longFlow ? 10.0 : 0.0
    scoreLong += not overheat ? 10.0 : 0.0
    
    scoreShort = 0.0
    scoreShort += trendShort ? 20.0 : 0.0
    scoreShort += momentumShort ? 20.0 : 0.0
    scoreShort += volOk ? 15.0 : 0.0
    scoreShort += redCandle ? 15.0 : 0.0
    scoreShort += closeNearLow ? 10.0 : 0.0
    scoreShort += shortFlow ? 10.0 : 0.0
    scoreShort += not oversold ? 10.0 : 0.0
    
    longScoreOk = scoreLong >= entryScore and scoreLong > scoreShort + scoreGap
    shortScoreOk = scoreShort >= entryScore and scoreShort > scoreLong + scoreGap
    
    action = validLongAction and longScoreOk ? 1.0 : validShortAction and shortScoreOk ? -1.0 : 0.0
    
    finalEntry = action != 0 ? close : na
    finalTP = action == 1.0 ? tpLong : action == -1.0 ? tpShort : na
    finalSL = action == 1.0 ? slLong : action == -1.0 ? slShort : na
    
    score = action == 1.0 ? scoreLong : action == -1.0 ? scoreShort : math.max(scoreLong, scoreShort)
    
    // Encode flow+status as numeric flags to avoid string series in security context
    // flowFlag: 1=LONG FLOW, 2=SHORT FLOW, 3=BUY ABSORB, 4=SELL ABSORB, 5=SQUEEZE, 6=SEPI, 0=NORMAL
    flowFlag = bullImpulse and trendLong ? 1.0 : bearImpulse and trendShort ? 2.0 : longAbsorb ? 3.0 : shortAbsorb ? 4.0 : smallBodyHighVol ? 5.0 : (not na(rvol) and rvol < 0.5) ? 6.0 : 0.0
    // statusFlag: 1=OVERHEAT, 2=OVERSOLD, 3=CONFLICT, 4=LONG SETUP, 5=SHORT SETUP, 0=WATCH
    statusFlag = overheat ? 1.0 : oversold ? 2.0 : flowConflict ? 3.0 : action == 1.0 ? 4.0 : action == -1.0 ? 5.0 : 0.0
    
    // Mode flag: 1=TREND, 2=PULLBACK, 3=BREAKOUT, 4=REVERSAL, 0=NONE
    modeFlag = (longTrendAction or shortTrendAction) ? 1.0 : (longPullbackAction or shortPullbackAction) ? 2.0 : (longBreakoutAction or shortBreakdownAction) ? 3.0 : (longReversalAction or shortReversalAction) ? 4.0 : 0.0
    
    [close, high, low, sup, rst, finalEntry, finalTP, finalSL, rsiVal, rvol * 100.0, action, score, flowFlag, statusFlag, modeFlag]
"""

def generate_pine_script(symbols, batch_label):
    n = len(symbols)
    
    ticker_lines = []
    tick_lines = []
    decimals_lines = []
    for i, sym in enumerate(symbols):
        ticker_lines.append(f'tk{i+1} = "BINANCE:{sym["symbol"]}.P"')
        tick_lines.append(f'tick{i+1} = {sym["tick_size"]}')
        decimals_lines.append(f'dec{i+1} = {sym["price_decimals"]}')
        
    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(f'''var string activeSide{idx} = ""
var float activeEntry{idx} = na
var float activeTp{idx} = na
var float activeSl{idx} = na
var string lastEvent{idx} = ""
var int lastBar{idx} = na
var float activeMode{idx} = na

[now{idx}, hi{idx}, lo{idx}, sup{idx}, rst{idx}, entry{idx}, tp_{idx}, sl_{idx}, rsi{idx}, rvolPct{idx}, actionRaw{idx}, score{idx}, flowFlag{idx}, statusFlag{idx}, modeFlag{idx}] = request.security(tk{idx}, tf, f_dashboard_engine())

// Decode numeric flags to strings locally on chart
action{idx} = actionRaw{idx} == 1.0 ? "LONG" : actionRaw{idx} == -1.0 ? "SHORT" : "WAIT"
flow{idx} = flowFlag{idx} == 1.0 ? "LONG FLOW" : flowFlag{idx} == 2.0 ? "SHORT FLOW" : flowFlag{idx} == 3.0 ? "BUY ABSORB" : flowFlag{idx} == 4.0 ? "SELL ABSORB" : flowFlag{idx} == 5.0 ? "SQUEEZE" : flowFlag{idx} == 6.0 ? "SEPI" : "NORMAL"

buf{idx} = breakoutBufferPct / 100.0
longTrig{idx} = rst{idx} * (1 + buf{idx})
shortTrig{idx} = sup{idx} * (1 - buf{idx})

pctTp{idx} = na(activeEntry{idx}) ? na : (activeEntry{idx} > 0 ? math.abs(activeTp{idx} - activeEntry{idx}) / activeEntry{idx} * 100.0 : na)
riskPct{idx} = na(activeEntry{idx}) ? na : (activeEntry{idx} > 0 ? math.abs(activeEntry{idx} - activeSl{idx}) / activeEntry{idx} * 100.0 : na)
rr{idx} = na(riskPct{idx}) or riskPct{idx} == 0 ? na : pctTp{idx} / riskPct{idx}

levTpPct{idx} = pctTp{idx} * leverage
levRiskPct{idx} = riskPct{idx} * leverage
risk{idx} = f_risk_label(levRiskPct{idx})

// Decode status locally using statusFlag and risk label
status{idx} = statusFlag{idx} == 1.0 ? "OVERHEAT" : statusFlag{idx} == 2.0 ? "OVERSOLD" : statusFlag{idx} == 3.0 ? "CONFLICT" : risk{idx} == "HIGH" ? "RISKY" : statusFlag{idx} == 4.0 ? "LONG SETUP" : statusFlag{idx} == 5.0 ? "SHORT SETUP" : "WATCH"
signal{idx} = action{idx} == "LONG" ? "LONG" : action{idx} == "SHORT" ? "SHORT" : risk{idx} == "HIGH" or risk{idx} == "RISKY" ? "RISKY" : "NEUTRAL"

liqPriceLong{idx} = activeEntry{idx} * (1 - 0.90 / leverage)
liqPriceShort{idx} = activeEntry{idx} * (1 + 0.90 / leverage)
liqWarnLong{idx} = activeSl{idx} <= liqPriceLong{idx} ? "HIGH RISK" : activeSl{idx} <= liqPriceLong{idx} * 1.02 ? "WARNING" : "SAFE"
liqWarnShort{idx} = activeSl{idx} >= liqPriceShort{idx} ? "HIGH RISK" : activeSl{idx} >= liqPriceShort{idx} * 0.98 ? "WARNING" : "SAFE"
sideForRisk{idx} = activeSide{idx} != "" ? activeSide{idx} : action{idx}
liqWarn{idx} = sideForRisk{idx} == "LONG" ? liqWarnLong{idx} : sideForRisk{idx} == "SHORT" ? liqWarnShort{idx} : "SAFE"

maxSafeLev{idx} = action{idx} == "LONG" or action{idx} == "SHORT" ? (riskPct{idx} > 0 ? math.floor(20.0 / riskPct{idx}) : 20) : 20
bbSqz{idx} = "NORMAL"

pnlPct{idx} = activeSide{idx} == "LONG" ? ((now{idx} - activeEntry{idx}) / activeEntry{idx}) * 100.0 * leverage : activeSide{idx} == "SHORT" ? ((activeEntry{idx} - now{idx}) / activeEntry{idx}) * 100.0 * leverage : na''')

    row_chunks = []
    for i in range(n):
        idx = i + 1
        t = symbols[i]["symbol"]
        row = i + 1
        
        row_str = f"""    // Row {row}
    f_cell(tbl, 0, {row}, "{t}", color.rgb(30, 90, 180), color.white)
    f_cell(tbl, 1, {row}, tf, cDark, color.white)
    f_cell(tbl, 2, {row}, f_fmt_price(now{idx}, tick{idx}), cDark, color.white)
    
    // TRIG
    trigDisp{idx} = f_fmt_price(longTrig{idx}, tick{idx}) + " / " + f_fmt_price(shortTrig{idx}, tick{idx})
    f_cell(tbl, 3, {row}, trigDisp{idx}, cDark, color.white)
    
    // ENTRY, TP, SL, TP%, RISK%, RR display rules
    entryDisp{idx} = na(activeEntry{idx}) ? "-" : f_fmt_price(activeEntry{idx}, tick{idx})
    tpDisp{idx} = na(activeTp{idx}) ? "-" : f_fmt_price(activeTp{idx}, tick{idx})
    slDisp{idx} = na(activeSl{idx}) ? "-" : f_fmt_price(activeSl{idx}, tick{idx})
    pctTpDisp{idx} = na(pctTp{idx}) ? "-" : str.tostring(pctTp{idx}, "#.##") + "%"
    riskPctDisp{idx} = na(riskPct{idx}) ? "-" : str.tostring(riskPct{idx}, "#.##") + "%"
    rrDisp{idx} = na(rr{idx}) ? "-" : str.tostring(rr{idx}, "#.##")
    pnlDisp{idx} = na(pnlPct{idx}) ? "-" : (pnlPct{idx} >= 0 ? "+" : "") + str.tostring(pnlPct{idx}, "#.##") + "%"
    pnlBg{idx} = na(pnlPct{idx}) ? cDark : (pnlPct{idx} >= 0 ? cGreen : cRed)
    
    f_cell(tbl, 4, {row}, entryDisp{idx}, cDark, color.white)
    f_cell(tbl, 5, {row}, tpDisp{idx}, cDark, color.lime)
    f_cell(tbl, 6, {row}, slDisp{idx}, cDark, color.orange)
    f_cell(tbl, 7, {row}, pctTpDisp{idx}, cDark, color.white)
    f_cell(tbl, 8, {row}, riskPctDisp{idx}, cDark, color.white)
    f_cell(tbl, 9, {row}, rrDisp{idx}, cDark, color.white)
    f_cell(tbl, 10, {row}, pnlDisp{idx}, pnlBg{idx}, color.white)
    
    f_cell(tbl, 11, {row}, str.tostring(leverage) + "x", cDark, color.white)
    f_cell(tbl, 12, {row}, risk{idx}, f_risk_color(risk{idx}), color.white)
    f_cell(tbl, 13, {row}, str.tostring(rsi{idx}, "#.0"), rsi{idx} < 30 ? cRed : rsi{idx} > 70 ? cOrange : cBlue, color.white)
    f_cell(tbl, 14, {row}, str.tostring(rvolPct{idx}, "#.0") + "%", rvolPct{idx} >= 120 ? cGreen : cDark, color.white)
    f_cell(tbl, 15, {row}, flow{idx}, cDark, color.white)
    f_cell(tbl, 16, {row}, status{idx}, cDark, color.yellow)
    f_cell(tbl, 17, {row}, action{idx}, f_action_color(action{idx}), color.white)
    f_cell(tbl, 18, {row}, str.tostring(score{idx}, "#"), f_score_color(score{idx}), color.white)
    f_cell(tbl, 19, {row}, signal{idx}, f_signal_color(signal{idx}), color.white)"""
        row_chunks.append(row_str)

    headers = """    f_header(tbl, 0, "PAIR")
    f_header(tbl, 1, "TF")
    f_header(tbl, 2, "NOW")
    f_header(tbl, 3, "TRIG")
    f_header(tbl, 4, "ENTRY")
    f_header(tbl, 5, "TP")
    f_header(tbl, 6, "SL")
    f_header(tbl, 7, "TP%")
    f_header(tbl, 8, "RISK%")
    f_header(tbl, 9, "RR")
    f_header(tbl, 10, "PnL%")
    f_header(tbl, 11, "LEV")
    f_header(tbl, 12, "RISK")
    f_header(tbl, 13, "RSI")
    f_header(tbl, 14, "RVOL")
    f_header(tbl, 15, "FLOW")
    f_header(tbl, 16, "STATUS")
    f_header(tbl, 17, "ACTION")
    f_header(tbl, 18, "SCORE")
    f_header(tbl, 19, "SIGNAL")"""

    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = symbols[i]["symbol"]
        alert_lines.append(f'''longTpHit{idx} = activeSide{idx} == "LONG" and hi{idx} >= activeTp{idx}
longSlHit{idx} = activeSide{idx} == "LONG" and lo{idx} <= activeSl{idx}
shortTpHit{idx} = activeSide{idx} == "SHORT" and lo{idx} <= activeTp{idx}
shortSlHit{idx} = activeSide{idx} == "SHORT" and hi{idx} >= activeSl{idx}

bothHitLong{idx} = longTpHit{idx} and longSlHit{idx}
bothHitShort{idx} = shortTpHit{idx} and shortSlHit{idx}

if bothHitLong{idx}
    if sameBarRule == "SL_FIRST"
        longTpHit{idx} := false
    else if sameBarRule == "TP_FIRST"
        longSlHit{idx} := false
    else if sameBarRule == "IGNORE"
        longTpHit{idx} := false
        longSlHit{idx} := false

if bothHitShort{idx}
    if sameBarRule == "SL_FIRST"
        shortTpHit{idx} := false
    else if sameBarRule == "TP_FIRST"
        shortSlHit{idx} := false
    else if sameBarRule == "IGNORE"
        shortTpHit{idx} := false
        shortSlHit{idx} := false

entryEvent{idx} = activeSide{idx} == "" and action{idx} == "LONG" ? "LONG_ENTRY" : activeSide{idx} == "" and action{idx} == "SHORT" ? "SHORT_ENTRY" : "NONE"
event{idx} = (activeSide{idx} == "LONG" and longTpHit{idx}) ? "LONG_TP_HIT" : (activeSide{idx} == "LONG" and longSlHit{idx}) ? "LONG_SL_HIT" : (activeSide{idx} == "SHORT" and shortTpHit{idx}) ? "SHORT_TP_HIT" : (activeSide{idx} == "SHORT" and shortSlHit{idx}) ? "SHORT_SL_HIT" : entryEvent{idx}

alertSide{idx} = event{idx} == "LONG_ENTRY" ? "LONG" : event{idx} == "SHORT_ENTRY" ? "SHORT" : activeSide{idx}
alertEntry{idx} = event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY" ? entry{idx} : activeEntry{idx}
alertTp{idx} = event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY" ? tp_{idx} : activeTp{idx}
alertSl{idx} = event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY" ? sl_{idx} : activeSl{idx}

if event{idx} == "LONG_SL_HIT" or event{idx} == "LONG_TP_HIT" or event{idx} == "SHORT_SL_HIT" or event{idx} == "SHORT_TP_HIT"
    activeSide{idx} := ""
    activeEntry{idx} := na
    activeTp{idx} := na
    activeSl{idx} := na
    activeMode{idx} := na
else if event{idx} == "LONG_ENTRY"
    activeSide{idx} := "LONG"
    activeEntry{idx} := entry{idx}
    activeTp{idx} := tp_{idx}
    activeSl{idx} := sl_{idx}
    activeMode{idx} := modeFlag{idx}
else if event{idx} == "SHORT_ENTRY"
    activeSide{idx} := "SHORT"
    activeEntry{idx} := entry{idx}
    activeTp{idx} := tp_{idx}
    activeSl{idx} := sl_{idx}
    activeMode{idx} := modeFlag{idx}
    
sendAlert{idx} = event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY" or event{idx} == "LONG_TP_HIT" or event{idx} == "LONG_SL_HIT" or event{idx} == "SHORT_TP_HIT" or event{idx} == "SHORT_SL_HIT"
canAlert{idx} = sendAlert{idx} and (event{idx} != lastEvent{idx} or na(lastBar{idx}) or bar_index - lastBar{idx} >= cooldownBars)

alertModeRaw{idx} = event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY" ? modeFlag{idx} : activeMode{idx}
alertMode{idx} = alertModeRaw{idx} == 1.0 ? "TREND_SCALP" : alertModeRaw{idx} == 2.0 ? "PULLBACK_SCALP" : alertModeRaw{idx} == 3.0 ? "BREAKOUT_SCALP" : alertModeRaw{idx} == 4.0 ? "REVERSAL_ENTRY" : "NONE"

alertTpPct{idx} = not na(alertEntry{idx}) and alertEntry{idx} > 0 ? math.abs(alertTp{idx} - alertEntry{idx}) / alertEntry{idx} * 100.0 : 0.0
alertRiskPct{idx} = not na(alertEntry{idx}) and alertEntry{idx} > 0 ? math.abs(alertEntry{idx} - alertSl{idx}) / alertEntry{idx} * 100.0 : 0.0
alertRr{idx} = alertRiskPct{idx} == 0 ? 0.0 : alertTpPct{idx} / alertRiskPct{idx}
alertLevTp{idx} = alertTpPct{idx} * leverage
alertLevRisk{idx} = alertRiskPct{idx} * leverage

if barstate.isconfirmed and canAlert{idx}
    msg_{idx} = '{{"market": "BINANCE_FUTURES", "type": "FUTURES_SIGNAL", "event": "' + event{idx} + '", "side": "' + str.tostring(alertSide{idx}) + '", "symbol": "{t}", "tf": "' + tf + '", "now": ' + str.tostring(now{idx}) + ', "entry": ' + str.tostring(alertEntry{idx}) + ', "tp": ' + str.tostring(alertTp{idx}) + ', "sl": ' + str.tostring(alertSl{idx}) + ', "tp_pct": ' + str.tostring(alertTpPct{idx}) + ', "risk_pct": ' + str.tostring(alertRiskPct{idx}) + ', "rr": ' + str.tostring(alertRr{idx}) + ', "leverage": ' + str.tostring(leverage) + ', "lev_tp_pct": ' + str.tostring(alertLevTp{idx}) + ', "lev_risk_pct": ' + str.tostring(alertLevRisk{idx}) + ', "risk_label": "' + risk{idx} + '", "liq_warn": "' + liqWarn{idx} + '", "bb_squeeze": "' + bbSqz{idx} + '", "max_safe_leverage": ' + str.tostring(maxSafeLev{idx}) + ', "score": ' + str.tostring(score{idx}) + ', "flow": "' + flow{idx} + '", "signal": "' + signal{idx} + '", "mode": "' + alertMode{idx} + '", "price_text": {{"now": "' + f_fmt_price(now{idx}, tick{idx}) + '", "entry": "' + f_fmt_price(alertEntry{idx}, tick{idx}) + '", "tp": "' + f_fmt_price(alertTp{idx}, tick{idx}) + '", "sl": "' + f_fmt_price(alertSl{idx}, tick{idx}) + '"}}, "tick_size": ' + str.tostring(tick{idx}) + ', "price_decimals": ' + str.tostring(dec{idx}) + ', "time": ' + str.tostring(time) + '}}'
    alert(msg_{idx}, alert.freq_once_per_bar_close)
    lastEvent{idx} := event{idx}
    lastBar{idx} := bar_index
''')

    pine_code = f"""// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Strategy: Binance USD-M Autobot {batch_label}
//@version=6
indicator("Binance USD-M Autobot {batch_label}", overlay=true, max_bars_back=200)

{ENGINE_TEMPLATE}

// ============================================================================
// DATA FETCH
// ============================================================================
{chr(10).join(ticker_lines)}
{chr(10).join(tick_lines)}
{chr(10).join(decimals_lines)}

{chr(10).join(security_lines)}

// ============================================================================
// ALERT LOGIC
// ============================================================================
{chr(10).join(alert_lines)}

// ============================================================================
// UI TABLE
// ============================================================================
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_left : pos == "Bottom Right" ? position.bottom_right : position.bottom_left
var tbl = table.new(tbl_pos, 20, {n+1}, border_width=1, border_color=#333333)

if barstate.islast
{headers}

{chr(10).join(row_chunks)}

plot(close, display=display.none)
"""
    
    filename = os.path.join(OUTPUT_DIR, f"binance_usdm_autobot_batch_{batch_label.lower()}.pine")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(pine_code)

def main():
    symbols = fetch_top_pairs()
    if not symbols:
        print("No symbols found.")
        return
        
    num_batches = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(num_batches):
        batch_syms = symbols[i*BATCH_SIZE : (i+1)*BATCH_SIZE]
        batch_label = chr(65 + i)
        generate_pine_script(batch_syms, batch_label)
        print(f"  [BINANCE V3] Batch {batch_label} -> {len(batch_syms)} tickers")
        
    print(f"\n[DONE] Generated Binance USD-M V3 files")

if __name__ == "__main__":
    main()
