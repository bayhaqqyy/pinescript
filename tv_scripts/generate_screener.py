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
BATCH_SIZE = 1
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
    onboard_map = {}
    if info_data:
        for sym in info_data.get("symbols", []):
            symbol_name = sym["symbol"]
            onboard_map[symbol_name] = sym.get("onboardDate", 0)
            for f in sym.get("filters", []):
                if f["filterType"] == "PRICE_FILTER":
                    tick_size_str = f["tickSize"]
                    tick_map[symbol_name] = float(tick_size_str)
                    break

    symbols_with_meta = []
    if api_success:
        # Exclude symbols listed in the last 48 hours to prevent TradingView 'Invalid symbol' errors
        now_ms = int(time.time() * 1000)
        min_age_ms = 48 * 60 * 60 * 1000
        
        filtered = [
            t for t in data
            if t["symbol"].endswith("USDT")
            and "_" not in t["symbol"]
            and t["symbol"] not in TRADFI_SYMBOLS
            and t["symbol"].isascii()
            and (now_ms - onboard_map.get(t["symbol"], 0)) >= min_age_ms
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
// USER-DEFINED TYPES (UDT)
// ============================================================================
type BiasResult
    float biasFlag
    float biasStrength

type ZoneResult
    float zoneFlag
    float zoneLow
    float zoneHigh
    float zoneScore

type TriggerResult
    float triggerFlag
    string triggerType
    float rsi5m
    float rvol5m

type PlanResult
    float now
    float high
    float low
    float sup
    float rst
    float action
    float score
    float flowFlag
    float statusFlag
    float modeFlag
    float rsi
    float rvolPct
    float entryLow
    float entryHigh
    float entryAvg
    float tp1
    float tp2
    float tp3
    float sl
    float riskPct
    float rrTp1
    float rrTp2
    float rrTp3
    float recommendedLev
    float riskLabel

// ============================================================================
// INPUTS
// ============================================================================
tfTrigger = input.timeframe("5", "Trigger TF")
tfSetup   = input.timeframe("15", "Setup TF")
tfZone    = input.timeframe("60", "Zone TF")
tfBias    = input.timeframe("240", "Bias TF")

enableStrictEntry = input.bool(true, "Enable Strict Entry")
allowTrendContinuation = input.bool(false, "Allow Trend Continuation Entry")
allowDirectBreakout = input.bool(false, "Allow Direct Breakout/Breakdown Entry")
minRvolEntry = input.float(1.2, "Minimum RVOL Entry", step=0.1)
minTriggerRvol = input.float(1.1, "Minimum Trigger RVOL", step=0.1)
entryScore = input.int(80, "Entry Score")

tf = tfSetup // Compatibility fallback

srLen = input.int(14, "S/R Length")
atrLen = input.int(14, "ATR Length")
leverage = input.int(10, "Leverage", minval=1, maxval=125)
scoreGap = input.int(6, "Score Gap")

slAtrMult = input.float(1.4, "SL ATR Mult (Wider)", step=0.1)
tpAtrMult = input.float(2.4, "TP ATR Mult (Wider)", step=0.1)
minRR = input.float(1.6, "Minimum RR (Wider)", step=0.1)

minSlRawPct = input.float(0.6, "Minimum SL Raw % (Wider)", step=0.1)
minTpRawPct = input.float(1.0, "Minimum TP Raw % (Wider)", step=0.1)
maxPlanRiskPct = input.float(2.0, "Max Raw Risk % For Action", step=0.5)
maxLevRiskPct = input.float(50.0, "Max Leveraged Risk % For Action", step=5.0)

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

f_risk_label(levRiskPct, isRiskyPlan) =>
    na(levRiskPct) ? "NO_DATA" :
      isRiskyPlan ? "RISKY_PLAN" :
      levRiskPct <= 35.0 ? "SAFE" :
      levRiskPct <= 65.0 ? "RISKY" :
      "HIGH"

f_risk_label_float(float levRiskPct, bool isRiskyPlan) =>
    na(levRiskPct) ? 4.0 :
      isRiskyPlan ? 3.0 :
      levRiskPct <= 35.0 ? 0.0 :
      levRiskPct <= 65.0 ? 1.0 : 2.0

f_risk_color(risk) =>
    risk == "SAFE" ? cLime :
      risk == "RISKY" ? cOrange :
      risk == "RISKY_PLAN" ? cOrange :
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
    score >= 80.0 ? cLime :
      score >= 60.0 ? cGreen :
      score >= 40.0 ? cOrange :
      cRed

f_cell(tbl, col, row, txt, bg, txtColor) =>
    table.cell(tbl, col, row, txt, bgcolor=bg, text_color=txtColor, text_size=size.small)

f_header(tbl, col, title) =>
    table.cell(tbl, col, 0, title, bgcolor=cHeader, text_color=color.yellow, text_size=size.small)

f_fmt_price(val, tickSize) =>
    str.tostring(val, tickSize == 0.1 ? "0.0" : tickSize == 0.01 ? "0.00" : tickSize == 0.001 ? "0.000" : tickSize == 0.0001 ? "0.0000" : tickSize == 0.00001 ? "0.00000" : tickSize == 0.000001 ? "0.000000" : tickSize == 0.0000001 ? "0.0000000" : tickSize == 0.00000001 ? "0.00000000" : "0.00")

// ============================================================================
// 4H BIAS ENGINE
// ============================================================================
f_bias_engine() =>
    ema20 = ta.ema(close, 20)
    ema50 = ta.ema(close, 50)
    ema200 = ta.ema(close, 200)
    rsiVal = ta.rsi(close, 14)
    [macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)
    
    isBullish = close > ema50 and ema20 > ema50 and rsiVal > 50.0 and hist >= 0.0
    isBearish = close < ema50 and ema20 < ema50 and rsiVal < 50.0 and hist <= 0.0
    
    biasFlag = 0.0
    biasStrength = 0.0
    
    if isBullish
        biasFlag := 1.0
        isStrongBull = close > ema200 and ema50 > ema200
        biasStrength := isStrongBull ? 2.0 : 1.0
    else if isBearish
        biasFlag := -1.0
        isStrongBear = close < ema200 and ema50 < ema200
        biasStrength := isStrongBear ? 2.0 : 1.0
        
    BiasResult.new(biasFlag, biasStrength)

// ============================================================================
// 1H ZONE ENGINE
// ============================================================================
f_zone_engine() =>
    zoneLen = 20
    support1h = ta.lowest(low[1], zoneLen)
    resistance1h = ta.highest(high[1], zoneLen)
    atr1h = ta.atr(14)
    
    demandLow = support1h - atr1h * 0.25
    demandHigh = support1h + atr1h * 0.25
    
    supplyLow = resistance1h - atr1h * 0.25
    supplyHigh = resistance1h + atr1h * 0.25
    
    isNearDemand = close >= (demandLow - atr1h * 0.5) and close <= (demandHigh + atr1h * 0.5)
    isNearSupply = close >= (supplyLow - atr1h * 0.5) and close <= (supplyHigh + atr1h * 0.5)
    
    body1 = math.abs(close[1] - open[1])
    prevLowerReject = body1 > 0 ? (math.min(open[1], close[1]) - low[1]) >= body1 * 0.8 : false
    prevUpperReject = body1 > 0 ? (high[1] - math.max(open[1], close[1])) >= body1 * 0.8 : false
    
    ema50_1h = ta.ema(close, 50)
    trendBullish = close > ema50_1h
    trendBearish = close < ema50_1h
    
    zoneFlag = 0.0
    float zoneLow = na
    float zoneHigh = na
    zoneScore = 0.0
    
    if isNearDemand or prevLowerReject
        zoneFlag := 1.0
        zoneLow := demandLow
        zoneHigh := demandHigh
        score = 50.0
        if isNearDemand
            score := score + 20.0
        if prevLowerReject
            score := score + 20.0
        if trendBullish
            score := score + 10.0
        zoneScore := score
    else if isNearSupply or prevUpperReject
        zoneFlag := -1.0
        zoneLow := supplyLow
        zoneHigh := supplyHigh
        score = 50.0
        if isNearSupply
            score := score + 20.0
        if prevUpperReject
            score := score + 20.0
        if trendBearish
            score := score + 10.0
        zoneScore := score
        
    ZoneResult.new(zoneFlag, zoneLow, zoneHigh, zoneScore)

// ============================================================================
// 5m TRIGGER ENGINE
// ============================================================================
f_trigger_engine() =>
    body = math.abs(close - open)
    barRange = math.max(high - low, syminfo.mintick)
    greenCandle = close > open
    redCandle = close < open
    
    closeNearHigh = barRange > 0 ? close >= low + barRange * 0.65 : false
    closeNearLow  = barRange > 0 ? close <= low + barRange * 0.35 : false
    
    lowerReject = body > 0 ? (math.min(open, close) - low) >= body * 0.8 : false
    upperReject = body > 0 ? (high - math.max(open, close)) >= body * 0.8 : false
    
    rsiVal = ta.rsi(close, 14)
    rsiUp = ta.change(rsiVal) > 0 or rsiVal > 50.0
    rsiDown = ta.change(rsiVal) < 0 or rsiVal < 50.0
    
    [macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)
    histUp = ta.change(hist) > 0
    histDown = ta.change(hist) < 0
    
    volMA = ta.sma(volume, 20)
    rvol5m = volMA > 0 ? volume / volMA : 1.0
    
    bullishTrigger = closeNearHigh and (greenCandle or lowerReject) and (rsiUp or histUp) and rvol5m >= minTriggerRvol
    bearishTrigger = closeNearLow and (redCandle or upperReject) and (rsiDown or histDown) and rvol5m >= minTriggerRvol
    
    triggerFlag = 0.0
    triggerType = "NEUTRAL"
    if bullishTrigger
        triggerFlag := 1.0
        triggerType := "BULLISH_REJECTION"
    else if bearishTrigger
        triggerFlag := -1.0
        triggerType := "BEARISH_REJECTION"
        
    TriggerResult.new(triggerFlag, triggerType, rsiVal, rvol5m)

// ============================================================================
// 15m PLAN ENGINE
// ============================================================================
f_plan_engine(float biasFlag, float biasStrength, float zoneFlag, float zoneLow, float zoneHigh, float zoneScore) =>
    sup = ta.lowest(low[1], srLen)
    rst = ta.highest(high[1], srLen)
    atrVal = ta.atr(atrLen)
    
    validData = not na(close) and close > 0 and not na(atrVal) and atrVal > 0 and not na(sup) and not na(rst)
    
    emaFast = ta.ema(close, 20)
    emaSlow = ta.ema(close, 50)
    rsiVal = ta.rsi(close, 14)
    [macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)
    volMA = ta.sma(volume, 20)
    rvol = volMA > 0 ? volume / volMA : na
    volOk = not na(rvol) and rvol >= 1.0
    
    body = math.abs(close - open)
    barRange = math.max(high - low, syminfo.mintick)
    greenCandle = close > open
    redCandle = close < open
    closeNearHigh = barRange > 0 ? close >= low + barRange * 0.65 : false
    closeNearLow  = barRange > 0 ? close <= low + barRange * 0.35 : false
    upperReject = body > 0 ? (high - math.max(open, close)) >= body * 0.8 : false
    lowerReject = body > 0 ? (math.min(open, close) - low) >= body * 0.8 : false
    
    trendLong = close > emaFast and emaFast > emaSlow
    trendShort = close < emaFast and emaFast < emaSlow
    momentumLong = rsiVal >= 50.0 and rsiVal <= 72.0 and hist > 0.0 and hist >= hist[1]
    momentumShort = rsiVal <= 50.0 and rsiVal >= 28.0 and hist < 0.0 and hist <= hist[1]
    
    overheat = rsiVal > 72.0 or close > emaFast + atrVal * 1.8
    oversold = rsiVal < 28.0 or close < emaFast - atrVal * 1.8
    
    buf = breakoutBufferPct / 100.0
    longTrigger  = rst * (1 + buf)
    shortTrigger = sup * (1 - buf)
    
    nearEmaLong = low <= emaFast + atrVal * 0.25 and close > emaFast
    nearEmaShort = high >= emaFast - atrVal * 0.25 and close < emaFast
    
    longTrendAction = trendLong and momentumLong and volOk and greenCandle and closeNearHigh and not overheat
    shortTrendAction = trendShort and momentumShort and volOk and redCandle and closeNearLow and not oversold
    
    longPullbackAction = trendLong and nearEmaLong and greenCandle and closeNearHigh and hist > hist[1] and rsiVal > 50.0 and volOk
    shortPullbackAction = trendShort and nearEmaShort and redCandle and closeNearLow and hist < hist[1] and rsiVal < 50.0 and volOk
    
    longBreakoutAction = close > longTrigger and greenCandle and closeNearHigh and volOk
    shortBreakdownAction = close < shortTrigger and redCandle and closeNearLow and volOk
    
    longDemandRejection = (zoneFlag == 1.0 and zoneScore >= 70.0) and lowerReject and greenCandle and closeNearHigh and rvol >= 1.2 and hist > hist[1]
    shortSupplyRejection = (zoneFlag == -1.0 and zoneScore >= 70.0) and upperReject and redCandle and closeNearLow and rvol >= 1.2 and hist < hist[1]
    
    longRetestAction = close >= rst - atrVal * 0.5 and close <= rst + atrVal * 0.5 and greenCandle and hist > hist[1] and close > emaFast
    shortRetestAction = close <= sup + atrVal * 0.5 and close >= sup - atrVal * 0.5 and redCandle and hist < hist[1] and close < emaFast
    
    // Anti-conflict
    blockShort = (biasFlag == 1.0 and biasStrength == 2.0)
    blockLong = (biasFlag == -1.0 and biasStrength == 2.0)
    
    // Strict entry toggles
    longTrendAllowed = allowTrendContinuation ? longTrendAction : false
    shortTrendAllowed = allowTrendContinuation ? shortTrendAction : false
    longBreakoutAllowed = allowDirectBreakout ? longBreakoutAction : false
    shortBreakdownAllowed = allowDirectBreakout ? shortBreakdownAction : false
    
    longSetupValid = validData and (longTrendAllowed or longPullbackAction or longBreakoutAllowed or longDemandRejection or longRetestAction) and not blockLong
    shortSetupValid = validData and (shortTrendAllowed or shortPullbackAction or shortBreakdownAllowed or shortSupplyRejection or shortRetestAction) and not blockShort
    
    // Anti-telat filter (Section 6)
    tooLateLong = longSetupValid and (close > emaFast + atrVal * 1.0 or close > rst + atrVal * 0.6)
    tooLateShort = shortSetupValid and (close < emaFast - atrVal * 1.0 or close < sup - atrVal * 0.6)
    
    isWaitRetestLong = longSetupValid and tooLateLong
    isWaitRetestShort = shortSetupValid and tooLateShort
    
    // If anti-telat triggered, entry is not valid yet
    if tooLateLong
        longSetupValid := false
    if tooLateShort
        shortSetupValid := false
        
    // Entry Zone boundaries
    entryLow = close - atrVal * 0.25
    entryHigh = close + atrVal * 0.10
    if isWaitRetestLong
        entryLow := rst - atrVal * 0.30
        entryHigh := rst + atrVal * 0.15
    else if zoneFlag == 1.0 and not na(zoneLow) and not na(zoneHigh)
        entryLow := zoneLow
        entryHigh := zoneHigh
    else if longRetestAction
        entryLow := rst - atrVal * 0.30
        entryHigh := rst + atrVal * 0.15
    else if longPullbackAction
        entryLow := emaFast - atrVal * 0.15
        entryHigh := emaFast + atrVal * 0.15
        
    if isWaitRetestShort
        entryLow := sup - atrVal * 0.15
        entryHigh := sup + atrVal * 0.30
    else if zoneFlag == -1.0 and not na(zoneLow) and not na(zoneHigh)
        entryLow := zoneLow
        entryHigh := zoneHigh
    else if shortRetestAction
        entryLow := sup - atrVal * 0.15
        entryHigh := sup + atrVal * 0.30
    else if shortPullbackAction
        entryLow := emaFast - atrVal * 0.15
        entryHigh := emaFast + atrVal * 0.15
        
    entryAvg = (entryLow + entryHigh) / 2.0
    
    // Stop Loss structure-based calculation (Section 9)
    zoneLowVal = (zoneFlag == 1.0 and not na(zoneLow)) ? zoneLow : 99999999.0
    slLong = math.min(
         zoneLowVal - atrVal * 0.20,
         sup - atrVal * 0.20
     )
    slLong := math.min(slLong, entryLow - math.max(atrVal * 1.8, entryAvg * 0.8 / 100.0))
    
    zoneHighVal = (zoneFlag == -1.0 and not na(zoneHigh)) ? zoneHigh : 0.0
    slShort = math.max(
         zoneHighVal + atrVal * 0.20,
         rst + atrVal * 0.20
     )
    slShort := math.max(slShort, entryHigh + math.max(atrVal * 1.8, entryAvg * 0.8 / 100.0))
    
    // TP calculation (Section 10)
    riskLong = entryAvg - slLong
    tp1Long = entryAvg + riskLong * 1.0
    tp2Long = entryAvg + riskLong * 1.8
    tp3Long = entryAvg + riskLong * 2.6
    
    riskShort = slShort - entryAvg
    tp1Short = entryAvg - riskShort * 1.0
    tp2Short = entryAvg - riskShort * 1.8
    tp3Short = entryAvg - riskShort * 2.6
    
    // Risk validation
    riskPct = 0.0
    float sl = na
    float tp1 = na
    float tp2 = na
    float tp3 = na
    
    if longSetupValid
        sl := slLong
        tp1 := tp1Long
        tp2 := tp2Long
        tp3 := tp3Long
        riskPct := entryAvg > 0.0 ? (riskLong / entryAvg * 100.0) : 0.0
    else if shortSetupValid
        sl := slShort
        tp1 := tp1Short
        tp2 := tp2Short
        tp3 := tp3Short
        riskPct := entryAvg > 0.0 ? (riskShort / entryAvg * 100.0) : 0.0
        
    recommendedLeverage = riskPct > 0.0 ? math.max(1.0, math.floor(20.0 / riskPct)) : 20.0
    isRiskyPlan = recommendedLeverage < leverage
    
    riskOk = riskPct <= maxPlanRiskPct and (riskPct * leverage) <= maxLevRiskPct
    
    // Enforce min RR and TP sequence rules
    tpSeqOk = false
    if longSetupValid
        tpSeqOk := tp1 > entryAvg and tp2 > tp1 and tp3 > tp2 and sl < entryLow and riskLong > 0.0
    else if shortSetupValid
        tpSeqOk := tp1 < entryAvg and tp2 < tp1 and tp3 < tp2 and sl > entryHigh and riskShort > 0.0
        
    longSetupValid := longSetupValid and riskOk and tpSeqOk
    shortSetupValid := shortSetupValid and riskOk and tpSeqOk
    
    // Scoring system (Section 12) - Base score out of 80 (excluding 5m trigger)
    scoreBiasLong = 0.0
    if biasFlag == 1.0
        scoreBiasLong := biasStrength == 2.0 ? 15.0 : 10.0
    else if biasFlag == 0.0
        scoreBiasLong := 5.0
        
    scoreBiasShort = 0.0
    if biasFlag == -1.0
        scoreBiasShort := biasStrength == 2.0 ? 15.0 : 10.0
    else if biasFlag == 0.0
        scoreBiasShort := 5.0
        
    scoreZoneLong = (zoneFlag == 1.0 and zoneScore >= 70.0) ? 20.0 : (zoneFlag == 1.0 ? 10.0 : 0.0)
    scoreZoneShort = (zoneFlag == -1.0 and zoneScore >= 70.0) ? 20.0 : (zoneFlag == -1.0 ? 10.0 : 0.0)
    
    scoreSetupLong = longSetupValid ? 20.0 : 0.0
    scoreSetupShort = shortSetupValid ? 20.0 : 0.0
    
    scoreRvol = (not na(rvol) and rvol >= minRvolEntry) ? 10.0 : (not na(rvol) and rvol >= 1.0 ? 5.0 : 0.0)
    
    scoreTechLong = (rsiVal > 50.0 and hist > 0.0) ? 10.0 : (rsiVal > 50.0 or hist > 0.0 ? 5.0 : 0.0)
    scoreTechShort = (rsiVal < 50.0 and hist < 0.0) ? 10.0 : (rsiVal < 50.0 or hist < 0.0 ? 5.0 : 0.0)
    
    scoreRisk = (recommendedLeverage >= leverage) ? 5.0 : 0.0
    
    baseScoreLong = scoreBiasLong + scoreZoneLong + scoreSetupLong + scoreRvol + scoreTechLong + scoreRisk
    baseScoreShort = scoreBiasShort + scoreZoneShort + scoreSetupShort + scoreRvol + scoreTechShort + scoreRisk
    
    // Final action logic for 15m (will be combined with 5m trigger)
    action = 0.0
    statusFlag = 0.0
    
    // Set status flag based on setup conditions
    if longSetupValid
        if isRiskyPlan
            statusFlag := 7.0
        else
            statusFlag := 1.0
            action := 1.0
    else if shortSetupValid
        if isRiskyPlan
            statusFlag := 7.0
        else
            statusFlag := 2.0
            action := -1.0
    else if isWaitRetestLong
        statusFlag := 3.0
    else if isWaitRetestShort
        statusFlag := 4.0
    else if overheat or oversold
        statusFlag := 5.0
    else if (longTrendAction or longPullbackAction or longBreakoutAction or longDemandRejection or longRetestAction) and (shortTrendAction or shortPullbackAction or shortBreakdownAction or shortSupplyRejection or shortRetestAction)
        statusFlag := 6.0
        
    scoreVal = 0.0
    if action == 1.0 or longSetupValid or isWaitRetestLong
        scoreVal := baseScoreLong
    else if action == -1.0 or shortSetupValid or isWaitRetestShort
        scoreVal := baseScoreShort
    else
        scoreVal := math.max(baseScoreLong, baseScoreShort)
        
    modeFlag = 0.0
    if action == 1.0 or longSetupValid or isWaitRetestLong
        if longTrendAction
            modeFlag := 1.0
        else if longPullbackAction
            modeFlag := 2.0
        else if longBreakoutAction
            modeFlag := 3.0
        else if longDemandRejection
            modeFlag := 6.0
        else if longRetestAction
            modeFlag := 7.0
    else if action == -1.0 or shortSetupValid or isWaitRetestShort
        if shortTrendAction
            modeFlag := 1.0
        else if shortPullbackAction
            modeFlag := 2.0
        else if shortBreakdownAction
            modeFlag := 4.0
        else if shortSupplyRejection
            modeFlag := 5.0
        else if shortRetestAction
            modeFlag := 8.0
            
    body15m = math.abs(close - open)
    smallBodyHighVol15m = body15m <= atrVal * 0.30 and rvol >= 1.8
    bullImpulse15m = greenCandle and closeNearHigh and rvol >= 1.2
    bearImpulse15m = redCandle and closeNearLow and rvol >= 1.2
    longAbsorb15m  = (math.min(open, close) - low) > body15m * 1.2 and closeNearHigh and rvol >= 1.3
    shortAbsorb15m = (high - math.max(open, close)) > body15m * 1.2 and closeNearLow and rvol >= 1.3
    
    flowFlag = bullImpulse15m and trendLong ? 1.0 : bearImpulse15m and trendShort ? 2.0 : longAbsorb15m ? 3.0 : shortAbsorb15m ? 4.0 : smallBodyHighVol15m ? 5.0 : (not na(rvol) and rvol < 0.5) ? 6.0 : 0.0
    
    rrTp1 = riskPct > 0.0 ? (tp1Long - entryAvg) / (entryAvg - slLong) : na
    rrTp2 = riskPct > 0.0 ? (tp2Long - entryAvg) / (entryAvg - slLong) : na
    rrTp3 = riskPct > 0.0 ? (tp3Long - entryAvg) / (entryAvg - slLong) : na
    
    if action == -1.0 or shortSetupValid or isWaitRetestShort
        rrTp1 := riskPct > 0.0 ? (entryAvg - tp1Short) / (slShort - entryAvg) : na
        rrTp2 := riskPct > 0.0 ? (entryAvg - tp2Short) / (slShort - entryAvg) : na
        rrTp3 := riskPct > 0.0 ? (entryAvg - tp3Short) / (slShort - entryAvg) : na
        
    riskLabel = f_risk_label_float(riskPct * leverage, isRiskyPlan)
        
    PlanResult.new(
        close, high, low, sup, rst, action, scoreVal, flowFlag, statusFlag, modeFlag,
        rsiVal, rvol * 100.0, entryLow, entryHigh, entryAvg, tp1, tp2, tp3, sl, riskPct, rrTp1,
        rrTp2, rrTp3, recommendedLeverage, riskLabel
    )

f_setup_desc(float mode) =>
    mode == 1.0 ? "TREND_CONTINUATION" :
      mode == 2.0 ? "PULLBACK_EMA" :
      mode == 5.0 ? "ZONE_REJECTION" :
      mode == 6.0 ? "ZONE_REJECTION" :
      mode == 7.0 ? "RETEST_STRUCTURE" :
      mode == 8.0 ? "RETEST_STRUCTURE" :
      mode == 3.0 ? "DIRECT_BREAKOUT" :
      mode == 4.0 ? "DIRECT_BREAKOUT" : "NONE"
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
var float activeEntryLow{idx} = na
var float activeEntryHigh{idx} = na
var float activeEntryAvg{idx} = na
var float activeTp1{idx} = na
var float activeTp2{idx} = na
var float activeTp3{idx} = na
var float activeSl{idx} = na
var bool activeTp1Hit{idx} = false
var bool activeTp2Hit{idx} = false
var bool activeTp3Hit{idx} = false
var float activeMode{idx} = na
var float activeScore{idx} = na
var string activeBias4h{idx} = ""
var string activeBiasStrength4h{idx} = ""
var string activeZone1h{idx} = ""
var float activeZoneScore1h{idx} = na
var float activeRsi{idx} = na
var float activeRvol{idx} = na
var string activeRiskLabel{idx} = ""
var float activeRecommendedLev{idx} = na
var string activeTrigger5m{idx} = ""
var string activeSetup15m{idx} = ""
var string lastEvent{idx} = ""
var int lastBar{idx} = na

biasRaw{idx} = request.security(tk{idx}, tfBias, f_bias_engine())
zoneRaw{idx} = request.security(tk{idx}, tfZone, f_zone_engine())
planRaw{idx} = request.security(tk{idx}, tfSetup, f_plan_engine(not na(biasRaw{idx}) ? biasRaw{idx}.biasFlag : 0.0, not na(biasRaw{idx}) ? biasRaw{idx}.biasStrength : 0.0, not na(zoneRaw{idx}) ? zoneRaw{idx}.zoneFlag : 0.0, not na(zoneRaw{idx}) ? zoneRaw{idx}.zoneLow : na, not na(zoneRaw{idx}) ? zoneRaw{idx}.zoneHigh : na, not na(zoneRaw{idx}) ? zoneRaw{idx}.zoneScore : 0.0))
trigRaw{idx} = request.security(tk{idx}, tfTrigger, f_trigger_engine())

bias{idx} = not na(biasRaw{idx}) ? biasRaw{idx} : defaultBias
zone{idx} = not na(zoneRaw{idx}) ? zoneRaw{idx} : defaultZone
plan{idx} = not na(planRaw{idx}) ? planRaw{idx} : defaultPlan
trig{idx} = not na(trigRaw{idx}) ? trigRaw{idx} : defaultTrigger

now{idx} = plan{idx}.now
hi{idx} = plan{idx}.high
lo{idx} = plan{idx}.low
sup{idx} = plan{idx}.sup
rst{idx} = plan{idx}.rst

biasStr{idx} = bias{idx}.biasFlag == 1.0 ? "BULLISH" : bias{idx}.biasFlag == -1.0 ? "BEARISH" : "NEUTRAL"
biasStrengthStr{idx} = bias{idx}.biasStrength == 2.0 ? "STRONG" : bias{idx}.biasStrength == 1.0 ? "NORMAL" : "WEAK"
zoneStr{idx} = zone{idx}.zoneFlag == 1.0 ? "DEMAND" : zone{idx}.zoneFlag == -1.0 ? "SUPPLY" : "NONE"

alertStatus{idx} = plan{idx}.statusFlag == 1.0 ? "VALID_LONG" : plan{idx}.statusFlag == 2.0 ? "VALID_SHORT" : plan{idx}.statusFlag == 3.0 ? "WAIT_RETEST_LONG" : plan{idx}.statusFlag == 4.0 ? "WAIT_RETEST_SHORT" : plan{idx}.statusFlag == 5.0 ? "OVEREXTENDED" : plan{idx}.statusFlag == 6.0 ? "CONFLICT" : plan{idx}.statusFlag == 7.0 ? "RISKY_PLAN" : "NO_TRADE"

pctTp1{idx} = na(activeEntryAvg{idx}) ? na : (activeEntryAvg{idx} > 0 ? math.abs(activeTp1{idx} - activeEntryAvg{idx}) / activeEntryAvg{idx} * 100.0 : na)
riskPct{idx} = na(activeEntryAvg{idx}) ? na : (activeEntryAvg{idx} > 0 ? math.abs(activeEntryAvg{idx} - activeSl{idx}) / activeEntryAvg{idx} * 100.0 : na)
rrTp1{idx} = na(riskPct{idx}) or riskPct{idx} == 0.0 ? na : pctTp1{idx} / riskPct{idx}

pctTp2{idx} = na(activeEntryAvg{idx}) ? na : (activeEntryAvg{idx} > 0 ? math.abs(activeTp2{idx} - activeEntryAvg{idx}) / activeEntryAvg{idx} * 100.0 : na)
rrTp2{idx} = na(riskPct{idx}) or riskPct{idx} == 0.0 ? na : pctTp2{idx} / riskPct{idx}

pctTp3{idx} = na(activeEntryAvg{idx}) ? na : (activeEntryAvg{idx} > 0 ? math.abs(activeTp3{idx} - activeEntryAvg{idx}) / activeEntryAvg{idx} * 100.0 : na)
rrTp3{idx} = na(riskPct{idx}) or riskPct{idx} == 0.0 ? na : pctTp3{idx} / riskPct{idx}

// Linear active/display calculations to prevent circular references
activeRecLev{idx} = riskPct{idx} > 0.0 ? math.max(1.0, math.floor(20.0 / riskPct{idx})) : 20.0
activeLevRiskPct{idx} = riskPct{idx} * leverage
activeIsRiskyPlan{idx} = activeRecLev{idx} < leverage
activeRiskLabelStr{idx} = f_risk_label(activeLevRiskPct{idx}, activeIsRiskyPlan{idx})

displayRiskPct{idx} = activeSide{idx} != "" ? riskPct{idx} : plan{idx}.riskPct
displayRecLev{idx} = activeSide{idx} != "" ? activeRecLev{idx} : plan{idx}.recommendedLev
displayRisk{idx} = activeSide{idx} != "" ? activeRiskLabelStr{idx} : (plan{idx}.riskLabel == 0.0 ? "SAFE" : plan{idx}.riskLabel == 1.0 ? "RISKY" : plan{idx}.riskLabel == 2.0 ? "HIGH" : plan{idx}.riskLabel == 3.0 ? "RISKY_PLAN" : "NO_DATA")

levRiskPct{idx} = displayRiskPct{idx} * leverage
recommendedLeverage{idx} = displayRecLev{idx}
isRiskyPlan{idx} = displayRecLev{idx} < leverage
risk{idx} = displayRisk{idx}

liqPriceLong{idx} = activeEntryAvg{idx} * (1 - 0.90 / leverage)
liqPriceShort{idx} = activeEntryAvg{idx} * (1 + 0.90 / leverage)
liqWarnLong{idx} = activeSl{idx} <= liqPriceLong{idx} ? "HIGH RISK" : activeSl{idx} <= liqPriceLong{idx} * 1.02 ? "WARNING" : "SAFE"
liqWarnShort{idx} = activeSl{idx} >= liqPriceShort{idx} ? "HIGH RISK" : activeSl{idx} >= liqPriceShort{idx} * 0.98 ? "WARNING" : "SAFE"
sideForRisk{idx} = activeSide{idx} != "" ? activeSide{idx} : (plan{idx}.action == 1.0 ? "LONG" : plan{idx}.action == -1.0 ? "SHORT" : "NONE")
liqWarn{idx} = sideForRisk{idx} == "LONG" ? liqWarnLong{idx} : sideForRisk{idx} == "SHORT" ? liqWarnShort{idx} : "SAFE"

pnlPct{idx} = activeSide{idx} == "LONG" ? ((now{idx} - activeEntryAvg{idx}) / activeEntryAvg{idx}) * 100.0 * leverage : activeSide{idx} == "SHORT" ? ((activeEntryAvg{idx} - now{idx}) / activeEntryAvg{idx}) * 100.0 * leverage : na

// V4 Final Action Evaluated on 5m chart TF
finalAction{idx} = 0.0
finalScore{idx} = plan{idx}.score

if activeSide{idx} == ""
    // Check LONG entry conditions
    isLongSetup = plan{idx}.statusFlag == 1.0 or plan{idx}.statusFlag == 3.0
    priceInsideLong = now{idx} >= plan{idx}.entryLow and now{idx} <= plan{idx}.entryHigh
    triggerLong = trig{idx}.triggerFlag == 1.0
    scoreLong = plan{idx}.score + (triggerLong ? 20.0 : 0.0)
    
    if isLongSetup and priceInsideLong and triggerLong and scoreLong >= entryScore
        finalAction{idx} := 1.0
        finalScore{idx} := scoreLong
        
    // Check SHORT entry conditions
    isShortSetup = plan{idx}.statusFlag == 2.0 or plan{idx}.statusFlag == 4.0
    priceInsideShort = now{idx} >= plan{idx}.entryLow and now{idx} <= plan{idx}.entryHigh
    triggerShort = trig{idx}.triggerFlag == -1.0
    scoreShort = plan{idx}.score + (triggerShort ? 20.0 : 0.0)
    
    if isShortSetup and priceInsideShort and triggerShort and scoreShort >= entryScore
        finalAction{idx} := -1.0
        finalScore{idx} := scoreShort
''')

    row_chunks = []
    for i in range(n):
        idx = i + 1
        t = symbols[i]["symbol"]
        row = i + 1
        
        row_str = f"""    // Row {row}
    biasDisp{idx} = biasStr{idx} + " (" + biasStrengthStr{idx} + ")"
    biasBg{idx} = bias{idx}.biasFlag == 1.0 ? cLime : bias{idx}.biasFlag == -1.0 ? cRed : cGray
    zoneDisp{idx} = zoneStr{idx} == "NONE" ? "-" : zoneStr{idx} + " (" + str.tostring(zone{idx}.zoneScore, "#") + ")"
    zoneBg{idx} = zone{idx}.zoneFlag == 1.0 ? color.rgb(0, 100, 200) : zone{idx}.zoneFlag == -1.0 ? color.rgb(150, 50, 50) : cDark
    entryRangeDisp{idx} = na(activeEntryLow{idx}) ? "-" : f_fmt_price(activeEntryLow{idx}, tick{idx}) + "-" + f_fmt_price(activeEntryHigh{idx}, tick{idx})
    
    tp1Disp{idx} = na(activeTp1{idx}) ? "-" : f_fmt_price(activeTp1{idx}, tick{idx}) + (activeTp1Hit{idx} ? " ✓" : "")
    tp2Disp{idx} = na(activeTp2{idx}) ? "-" : f_fmt_price(activeTp2{idx}, tick{idx}) + (activeTp2Hit{idx} ? " ✓" : "")
    tp3Disp{idx} = na(activeTp3{idx}) ? "-" : f_fmt_price(activeTp3{idx}, tick{idx}) + (activeTp3Hit{idx} ? " ✓" : "")
    slDisp{idx} = na(activeSl{idx}) ? "-" : f_fmt_price(activeSl{idx}, tick{idx})
    
    riskPctDisp{idx} = na(displayRiskPct{idx}) ? "-" : str.tostring(displayRiskPct{idx}, "#.##") + "%"
    recLevDisp{idx} = na(displayRecLev{idx}) ? "-" : str.tostring(displayRecLev{idx}) + "x"
    rvolDisp{idx} = na(plan{idx}.rvolPct) ? "-" : str.tostring(plan{idx}.rvolPct, "#") + "%"
    modeDisp{idx} = alertMode{idx}
    statusDisp{idx} = alertStatus{idx}
    scoreDisp{idx} = str.tostring(finalScore{idx}, "#")
    signalDisp{idx} = finalAction{idx} == 1.0 ? "LONG" : finalAction{idx} == -1.0 ? "SHORT" : "NEUTRAL"
    
    f_cell(tbl, 0, {row}, "{t}", color.rgb(30, 90, 180), color.white)
    f_cell(tbl, 1, {row}, biasDisp{idx}, biasBg{idx}, color.white)
    f_cell(tbl, 2, {row}, zoneDisp{idx}, zoneBg{idx}, color.white)
    f_cell(tbl, 3, {row}, f_fmt_price(now{idx}, tick{idx}), cDark, color.white)
    f_cell(tbl, 4, {row}, entryRangeDisp{idx}, cDark, color.white)
    f_cell(tbl, 5, {row}, tp1Disp{idx}, cDark, activeTp1Hit{idx} ? cLime : color.white)
    f_cell(tbl, 6, {row}, tp2Disp{idx}, cDark, activeTp2Hit{idx} ? cLime : color.white)
    f_cell(tbl, 7, {row}, tp3Disp{idx}, cDark, activeTp3Hit{idx} ? cLime : color.white)
    f_cell(tbl, 8, {row}, slDisp{idx}, cDark, color.orange)
    f_cell(tbl, 9, {row}, riskPctDisp{idx}, cDark, color.white)
    f_cell(tbl, 10, {row}, str.tostring(leverage) + "x", cDark, color.white)
    f_cell(tbl, 11, {row}, recLevDisp{idx}, isRiskyPlan{idx} ? cOrange : cLime, color.white)
    f_cell(tbl, 12, {row}, str.tostring(plan{idx}.rsi, "#.0"), plan{idx}.rsi < 30.0 ? cRed : plan{idx}.rsi > 70.0 ? cOrange : cBlue, color.white)
    f_cell(tbl, 13, {row}, rvolDisp{idx}, plan{idx}.rvolPct >= 120.0 ? cGreen : cDark, color.white)
    f_cell(tbl, 14, {row}, modeDisp{idx}, cDark, color.white)
    f_cell(tbl, 15, {row}, statusDisp{idx}, cDark, color.yellow)
    f_cell(tbl, 16, {row}, scoreDisp{idx}, f_score_color(finalScore{idx}), color.white)
    f_cell(tbl, 17, {row}, signalDisp{idx}, f_signal_color(signalDisp{idx}), color.white)"""
        row_chunks.append(row_str)

    headers = """    f_header(tbl, 0, "PAIR")
    f_header(tbl, 1, "BIAS")
    f_header(tbl, 2, "ZONE")
    f_header(tbl, 3, "NOW")
    f_header(tbl, 4, "ENTRY")
    f_header(tbl, 5, "TP1")
    f_header(tbl, 6, "TP2")
    f_header(tbl, 7, "TP3")
    f_header(tbl, 8, "SL")
    f_header(tbl, 9, "RISK%")
    f_header(tbl, 10, "LEV")
    f_header(tbl, 11, "REC.LEV")
    f_header(tbl, 12, "RSI")
    f_header(tbl, 13, "RVOL")
    f_header(tbl, 14, "MODE")
    f_header(tbl, 15, "STATUS")
    f_header(tbl, 16, "SCORE")
    f_header(tbl, 17, "SIGNAL")"""

    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = symbols[i]["symbol"]
        alert_lines.append(f'''anyTpHitLong{idx} = (not activeTp1Hit{idx} and hi{idx} >= activeTp1{idx}) or (activeTp1Hit{idx} and not activeTp2Hit{idx} and hi{idx} >= activeTp2{idx}) or (activeTp2Hit{idx} and not activeTp3Hit{idx} and hi{idx} >= activeTp3{idx})
anyTpHitShort{idx} = (not activeTp1Hit{idx} and lo{idx} <= activeTp1{idx}) or (activeTp1Hit{idx} and not activeTp2Hit{idx} and lo{idx} <= activeTp2{idx}) or (activeTp2Hit{idx} and not activeTp3Hit{idx} and lo{idx} <= activeTp3{idx})

longSlHit{idx} = activeSide{idx} == "LONG" and lo{idx} <= activeSl{idx}
shortSlHit{idx} = activeSide{idx} == "SHORT" and hi{idx} >= activeSl{idx}

bothHitLong{idx} = activeSide{idx} == "LONG" and anyTpHitLong{idx} and longSlHit{idx}
bothHitShort{idx} = activeSide{idx} == "SHORT" and anyTpHitShort{idx} and shortSlHit{idx}

tpHitValidLong{idx} = activeSide{idx} == "LONG" and anyTpHitLong{idx}
slHitValidLong{idx} = longSlHit{idx}

tpHitValidShort{idx} = activeSide{idx} == "SHORT" and anyTpHitShort{idx}
slHitValidShort{idx} = shortSlHit{idx}

if bothHitLong{idx}
    if sameBarRule == "SL_FIRST"
        tpHitValidLong{idx} := false
    else if sameBarRule == "TP_FIRST"
        slHitValidLong{idx} := false
    else if sameBarRule == "IGNORE"
        tpHitValidLong{idx} := false
        slHitValidLong{idx} := false

if bothHitShort{idx}
    if sameBarRule == "SL_FIRST"
        tpHitValidShort{idx} := false
    else if sameBarRule == "TP_FIRST"
        slHitValidShort{idx} := false
    else if sameBarRule == "IGNORE"
        tpHitValidShort{idx} := false
        slHitValidShort{idx} := false

entryEvent{idx} = activeSide{idx} == "" and finalAction{idx} == 1.0 ? "LONG_ENTRY" : activeSide{idx} == "" and finalAction{idx} == -1.0 ? "SHORT_ENTRY" : "NONE"

event{idx} = "NONE"
if activeSide{idx} == "LONG"
    if slHitValidLong{idx}
        event{idx} := "LONG_SL_HIT"
    else if tpHitValidLong{idx}
        if hi{idx} >= activeTp3{idx} and activeTp2Hit{idx}
            event{idx} := "LONG_TP3_HIT"
        else if hi{idx} >= activeTp2{idx} and activeTp1Hit{idx}
            event{idx} := "LONG_TP2_HIT"
        else if hi{idx} >= activeTp1{idx}
            event{idx} := "LONG_TP1_HIT"
else if activeSide{idx} == "SHORT"
    if slHitValidShort{idx}
        event{idx} := "SHORT_SL_HIT"
    else if tpHitValidShort{idx}
        if lo{idx} <= activeTp3{idx} and activeTp2Hit{idx}
            event{idx} := "SHORT_TP3_HIT"
        else if lo{idx} <= activeTp2{idx} and activeTp1Hit{idx}
            event{idx} := "SHORT_TP2_HIT"
        else if lo{idx} <= activeTp1{idx}
            event{idx} := "SHORT_TP1_HIT"
else
    event{idx} := entryEvent{idx}

isEntryEvent{idx} = event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY"
alertSide{idx} = isEntryEvent{idx} ? (event{idx} == "LONG_ENTRY" ? "LONG" : "SHORT") : activeSide{idx}
alertEntryLow{idx} = isEntryEvent{idx} ? plan{idx}.entryLow : activeEntryLow{idx}
alertEntryHigh{idx} = isEntryEvent{idx} ? plan{idx}.entryHigh : activeEntryHigh{idx}
alertEntryAvg{idx} = isEntryEvent{idx} ? plan{idx}.entryAvg : activeEntryAvg{idx}
alertTp1{idx} = isEntryEvent{idx} ? plan{idx}.tp1 : activeTp1{idx}
alertTp2{idx} = isEntryEvent{idx} ? plan{idx}.tp2 : activeTp2{idx}
alertTp3{idx} = isEntryEvent{idx} ? plan{idx}.tp3 : activeTp3{idx}
alertSl{idx} = isEntryEvent{idx} ? plan{idx}.sl : activeSl{idx}
alertModeRaw{idx} = isEntryEvent{idx} ? plan{idx}.modeFlag : activeMode{idx}

if event{idx} == "LONG_SL_HIT" or event{idx} == "LONG_TP3_HIT" or event{idx} == "SHORT_SL_HIT" or event{idx} == "SHORT_TP3_HIT"
    activeSide{idx} := ""
    activeEntryLow{idx} := na
    activeEntryHigh{idx} := na
    activeEntryAvg{idx} := na
    activeTp1{idx} := na
    activeTp2{idx} := na
    activeTp3{idx} := na
    activeSl{idx} := na
    activeTp1Hit{idx} := false
    activeTp2Hit{idx} := false
    activeTp3Hit{idx} := false
    activeMode{idx} := na
    activeScore{idx} := na
    activeBias4h{idx} := ""
    activeBiasStrength4h{idx} := ""
    activeZone1h{idx} := ""
    activeZoneScore1h{idx} := na
    activeRsi{idx} := na
    activeRvol{idx} := na
    activeRiskLabel{idx} := ""
    activeRecommendedLev{idx} := na
    activeTrigger5m{idx} := ""
    activeSetup15m{idx} := ""
else if event{idx} == "LONG_TP1_HIT" or event{idx} == "SHORT_TP1_HIT"
    activeTp1Hit{idx} := true
else if event{idx} == "LONG_TP2_HIT" or event{idx} == "SHORT_TP2_HIT"
    activeTp1Hit{idx} := true
    activeTp2Hit{idx} := true
else if event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY"
    activeSide{idx} := event{idx} == "LONG_ENTRY" ? "LONG" : "SHORT"
    activeEntryLow{idx} := plan{idx}.entryLow
    activeEntryHigh{idx} := plan{idx}.entryHigh
    activeEntryAvg{idx} := plan{idx}.entryAvg
    activeTp1{idx} := plan{idx}.tp1
    activeTp2{idx} := plan{idx}.tp2
    activeTp3{idx} := plan{idx}.tp3
    activeSl{idx} := plan{idx}.sl
    activeTp1Hit{idx} := false
    activeTp2Hit{idx} := false
    activeTp3Hit{idx} := false
    activeMode{idx} := plan{idx}.modeFlag
    activeScore{idx} := finalScore{idx}
    activeBias4h{idx} := biasStr{idx}
    activeBiasStrength4h{idx} := biasStrengthStr{idx}
    activeZone1h{idx} := zoneStr{idx}
    activeZoneScore1h{idx} := zone{idx}.zoneScore
    activeRsi{idx} := plan{idx}.rsi
    activeRvol{idx} := plan{idx}.rvolPct
    activeRiskLabel{idx} := risk{idx}
    activeRecommendedLev{idx} := recommendedLeverage{idx}
    activeTrigger5m{idx} := trig{idx}.triggerType
    activeSetup15m{idx} := f_setup_desc(plan{idx}.modeFlag)

sendAlert{idx} = event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY" or event{idx} == "LONG_TP1_HIT" or event{idx} == "LONG_TP2_HIT" or event{idx} == "LONG_TP3_HIT" or event{idx} == "LONG_SL_HIT" or event{idx} == "SHORT_TP1_HIT" or event{idx} == "SHORT_TP2_HIT" or event{idx} == "SHORT_TP3_HIT" or event{idx} == "SHORT_SL_HIT"
canAlert{idx} = sendAlert{idx} and (event{idx} != lastEvent{idx} or na(lastBar{idx}) or bar_index - lastBar{idx} >= cooldownBars)

alertMode{idx} = alertModeRaw{idx} == 1.0 ? "TREND_CONTINUATION" : alertModeRaw{idx} == 2.0 ? "PULLBACK_ENTRY" : alertModeRaw{idx} == 3.0 ? "BREAKOUT_ENTRY" : alertModeRaw{idx} == 4.0 ? "BREAKDOWN_ENTRY" : alertModeRaw{idx} == 5.0 ? "SUPPLY_REJECTION" : alertModeRaw{idx} == 6.0 ? "DEMAND_REJECTION" : alertModeRaw{idx} == 7.0 ? "BREAKOUT_RETEST" : alertModeRaw{idx} == 8.0 ? "BREAKDOWN_RETEST" : "NONE"

alertScore{idx} = isEntryEvent{idx} ? finalScore{idx} : activeScore{idx}
alertBias4h{idx} = isEntryEvent{idx} ? biasStr{idx} : activeBias4h{idx}
alertBiasStrength4h{idx} = isEntryEvent{idx} ? biasStrengthStr{idx} : activeBiasStrength4h{idx}
alertZone1h{idx} = isEntryEvent{idx} ? zoneStr{idx} : activeZone1h{idx}
alertZoneScore1h{idx} = isEntryEvent{idx} ? zone{idx}.zoneScore : activeZoneScore1h{idx}
alertRsi{idx} = isEntryEvent{idx} ? plan{idx}.rsi : activeRsi{idx}
alertRvol{idx} = isEntryEvent{idx} ? plan{idx}.rvolPct : activeRvol{idx}
alertRiskLabel{idx} = isEntryEvent{idx} ? risk{idx} : activeRiskLabel{idx}
alertRecLev{idx} = isEntryEvent{idx} ? recommendedLeverage{idx} : activeRecommendedLev{idx}
alertTrigger5m{idx} = isEntryEvent{idx} ? trig{idx}.triggerType : activeTrigger5m{idx}
alertSetup15m{idx} = isEntryEvent{idx} ? f_setup_desc(plan{idx}.modeFlag) : f_setup_desc(activeMode{idx})

alertRiskPct{idx} = isEntryEvent{idx} ? plan{idx}.riskPct : riskPct{idx}
alertRrTp1{idx} = isEntryEvent{idx} ? plan{idx}.rrTp1 : rrTp1{idx}
alertRrTp2{idx} = isEntryEvent{idx} ? plan{idx}.rrTp2 : rrTp2{idx}
alertRrTp3{idx} = isEntryEvent{idx} ? plan{idx}.rrTp3 : rrTp3{idx}
alertLevRiskPct{idx} = isEntryEvent{idx} ? (plan{idx}.riskPct * leverage) : levRiskPct{idx}

if barstate.isconfirmed and canAlert{idx}
    msg_{idx} = '{{"market": "BINANCE_FUTURES", "type": "FUTURES_SIGNAL", "version": "4.0", "event": "' + event{idx} + '", "symbol": "{t}", "side": "' + alertSide{idx} + '", "tf_trigger": "5", "tf_setup": "15", "tf_zone": "60", "tf_bias": "240", "mode": "' + alertMode{idx} + '", "status": "' + alertStatus{idx} + '", "now": ' + str.tostring(now{idx}) + ', "entry_low": ' + (na(alertEntryLow{idx}) ? 'null' : str.tostring(alertEntryLow{idx})) + ', "entry_high": ' + (na(alertEntryHigh{idx}) ? 'null' : str.tostring(alertEntryHigh{idx})) + ', "entry_avg": ' + (na(alertEntryAvg{idx}) ? 'null' : str.tostring(alertEntryAvg{idx})) + ', "tp1": ' + (na(alertTp1{idx}) ? 'null' : str.tostring(alertTp1{idx})) + ', "tp2": ' + (na(alertTp2{idx}) ? 'null' : str.tostring(alertTp2{idx})) + ', "tp3": ' + (na(alertTp3{idx}) ? 'null' : str.tostring(alertTp3{idx})) + ', "sl": ' + (na(alertSl{idx}) ? 'null' : str.tostring(alertSl{idx})) + ', "risk_pct": ' + (na(alertRiskPct{idx}) ? 'null' : str.tostring(alertRiskPct{idx}, "#.##")) + ', "rr_tp1": ' + (na(alertRrTp1{idx}) ? 'null' : str.tostring(alertRrTp1{idx}, "#.##")) + ', "rr_tp2": ' + (na(alertRrTp2{idx}) ? 'null' : str.tostring(alertRrTp2{idx}, "#.##")) + ', "rr_tp3": ' + (na(alertRrTp3{idx}) ? 'null' : str.tostring(alertRrTp3{idx}, "#.##")) + ', "input_leverage": ' + str.tostring(leverage) + ', "recommended_leverage": ' + (na(alertRecLev{idx}) ? 'null' : str.tostring(alertRecLev{idx})) + ', "lev_risk_pct": ' + (na(alertLevRiskPct{idx}) ? 'null' : str.tostring(alertLevRiskPct{idx}, "#.##")) + ', "risk_label": "' + alertRiskLabel{idx} + '", "score": ' + str.tostring(alertScore{idx}, "#") + ', "bias_4h": "' + alertBias4h{idx} + '", "bias_strength_4h": "' + alertBiasStrength4h{idx} + '", "zone_1h": "' + alertZone1h{idx} + '", "zone_score_1h": ' + str.tostring(alertZoneScore1h{idx}, "#") + ', "trigger_5m": "' + alertTrigger5m{idx} + '", "setup_15m": "' + alertSetup15m{idx} + '", "rsi": ' + str.tostring(alertRsi{idx}, "#.##") + ', "rvol": ' + str.tostring(alertRvol{idx} / 100.0, "#.##") + ', "price_text": {{"now": "' + f_fmt_price(now{idx}, tick{idx}) + '", "entry_low": "' + (na(alertEntryLow{idx}) ? '-' : f_fmt_price(alertEntryLow{idx}, tick{idx})) + '", "entry_high": "' + (na(alertEntryHigh{idx}) ? '-' : f_fmt_price(alertEntryHigh{idx}, tick{idx})) + '", "tp1": "' + (na(alertTp1{idx}) ? '-' : f_fmt_price(alertTp1{idx}, tick{idx})) + '", "tp2": "' + (na(alertTp2{idx}) ? '-' : f_fmt_price(alertTp2{idx}, tick{idx})) + '", "tp3": "' + (na(alertTp3{idx}) ? '-' : f_fmt_price(alertTp3{idx}, tick{idx})) + '", "sl": "' + (na(alertSl{idx}) ? '-' : f_fmt_price(alertSl{idx}, tick{idx})) + '"}}, "time": ' + str.tostring(time) + '}}'
    alert(msg_{idx}, alert.freq_once_per_bar_close)
    lastEvent{idx} := event{idx}
    lastBar{idx} := bar_index
''')

    pine_code = f"""// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Strategy: Binance USD-M Autobot V4 {batch_label}
//@version=6
indicator("Binance USD-M Autobot V4 {batch_label}", overlay=true, max_bars_back=200)

{ENGINE_TEMPLATE}

// ============================================================================
// DATA FETCH
// ============================================================================
{chr(10).join(ticker_lines)}
{chr(10).join(tick_lines)}
{chr(10).join(decimals_lines)}

var defaultBias = BiasResult.new(0.0, 0.0)
var defaultZone = ZoneResult.new(0.0, na, na, 0.0)
var defaultTrigger = TriggerResult.new(0.0, "NEUTRAL", na, na)
var defaultPlan = PlanResult.new(na, na, na, na, na, 0.0, 0.0, 0.0, 0.0, 0.0, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na)

{chr(10).join(security_lines)}

// ============================================================================
// ALERT LOGIC
// ============================================================================
{chr(10).join(alert_lines)}

// ============================================================================
// UI TABLE
// ============================================================================
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_left : pos == "Bottom Right" ? position.bottom_right : position.bottom_left
var tbl = table.new(tbl_pos, 18, {n+1}, border_width=1, border_color=#333333)

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
        
    # Clean up old batch files
    if os.path.exists(OUTPUT_DIR):
        import glob
        old_files = glob.glob(os.path.join(OUTPUT_DIR, "binance_usdm_autobot_batch_*.pine"))
        for f_path in old_files:
            try:
                os.remove(f_path)
            except Exception as e:
                print(f"[CLEANUP] Failed to remove {os.path.basename(f_path)}: {e}")
        print(f"[CLEANUP] Cleaned up {len(old_files)} old batch files")

    num_batches = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE
    num_batches = min(num_batches, 5) # Limit to first 5 batches (A, B, C, D, E) as requested
    for i in range(num_batches):
        batch_syms = symbols[i*BATCH_SIZE : (i+1)*BATCH_SIZE]
        
        # Excel-style column label generator (e.g. A-Z, AA-AZ, etc.)
        batch_label = ""
        temp = i
        while temp >= 0:
            batch_label = chr(65 + (temp % 26)) + batch_label
            temp = (temp // 26) - 1
            
        generate_pine_script(batch_syms, batch_label)
        print(f"  [BINANCE V4] Batch {batch_label} -> {len(batch_syms)} tickers")
        
    print(f"\n[DONE] Generated Binance USD-M V4 files")

if __name__ == "__main__":
    main()
