import requests
import json
import os
import time
import sys
import math
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BINANCE_API = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_INFO_API = "https://fapi.binance.com/fapi/v1/exchangeInfo"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, "binance_futures_cache.json")
TOP_N = 100
BATCH_SIZE = 10
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

def fetch_top_pairs():
    print("=" * 60)
    print(" BINANCE USDS-M DASHBOARD GENERATOR")
    print("=" * 60)

    data = None
    info_data = None
    api_success = False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"\n[FETCH] Attempt {attempt}/{MAX_RETRIES} - Connecting to Binance Futures API...")
            resp = requests.get(BINANCE_API, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            
            resp_info = requests.get(BINANCE_INFO_API, timeout=REQUEST_TIMEOUT)
            resp_info.raise_for_status()
            info_data = resp_info.json()
            
            print(f"[FETCH] Received {len(data)} tickers and exchange info")
            api_success = True
            break
        except requests.RequestException as e:
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
        ]
        filtered.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
        top = filtered[:TOP_N]

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
    else:
        # fallback
        HARDCODED = [
            "BTCUSDT", "ETHUSDT", "HYPEUSDT", "SOLUSDT", "XRPUSDT",
            "NEARUSDT", "DOGEUSDT", "BNBUSDT", "SUIUSDT", "ADAUSDT",
            "GRASSUSDT", "FIDAUSDT", "BEATUSDT", "GENIUSUSDT", "ALTUSDT",
            "AGTUSDT", "EDENUSDT", "JCTUSDT", "1000PEPEUSDT", "ONDOUSDT",
            "WLDUSDT", "TAOUSDT", "LINKUSDT", "TONUSDT", "AVAXUSDT",
            "DOTUSDT", "LTCUSDT", "FILUSDT", "INJUSDT", "ENAUSDT",
            "TRUMPUSDT", "FETUSDT", "AAVEUSDT", "TRXUSDT", "ICPUSDT",
            "UNIUSDT", "BCHUSDT", "ARBUSDT", "TIAUSDT", "VIRTUALUSDT",
            "XMRUSDT", "RENDERUSDT", "ATOMUSDT", "XLMUSDT", "ETCUSDT",
            "APTUSDT", "CHZUSDT", "1000SHIBUSDT", "OPUSDT", "HBARUSDT"
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

srLen = input.int(20, "S/R Length")
atrLen = input.int(14, "ATR Length")
leverage = input.int(10, "Leverage", minval=1, maxval=125)

entryScore = input.int(70, "Entry Score")
scoreGap = input.int(8, "Score Gap")

slAtrMult = input.float(1.5, "SL ATR Mult", step=0.1)
tpAtrMult = input.float(3.0, "TP ATR Mult", step=0.1)
minRR = input.float(1.8, "Minimum RR", step=0.1)

minSlRawPct = input.float(0.6, "Minimum SL Raw %", step=0.1)
minTpRawPct = input.float(1.2, "Minimum TP Raw %", step=0.1)
maxPlanRiskPct = input.float(5.0, "Max Raw Risk % For Action", step=0.5)
maxLevRiskPct = input.float(65.0, "Max Leveraged Risk % For Action", step=5.0)

breakoutBufferPct = input.float(0.05, "Breakout Buffer %", step=0.01)
srAtrBuffer = input.float(0.20, "S/R ATR Buffer", step=0.05)
useStructureSL = input.bool(true, "Use Structure SL When Reasonable")
maxStructureRiskPct = input.float(6.0, "Max Structure SL %", step=0.5)

cooldownBars = input.int(5, "Alert Cooldown Bars", minval=1)

pos = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

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
    longTriggerRaw  = rst * (1 + buf)
    shortTriggerRaw = sup * (1 - buf)
    
    longTrigger  = longTriggerRaw
    shortTrigger = shortTriggerRaw
    
    longBreak  = close >= longTrigger
    shortBreak = close <= shortTrigger
    
    entryLong  = longBreak ? close : longTrigger
    entryShort = shortBreak ? close : shortTrigger
    
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
    tpLongByAtrDist = atrVal * tpAtrMult
    tpLongByMinPctDist = entryLong * minTpRawPct / 100.0
    tpLongByRRDist = slLongDist * minRR
    tpLongDist = math.max(tpLongByAtrDist, tpLongByMinPctDist, tpLongByRRDist)
    tpLong = entryLong + tpLongDist
    
    // TP SHORT
    tpShortByAtrDist = atrVal * tpAtrMult
    tpShortByMinPctDist = entryShort * minTpRawPct / 100.0
    tpShortByRRDist = slShortDist * minRR
    tpShortDist = math.max(tpShortByAtrDist, tpShortByMinPctDist, tpShortByRRDist)
    tpShort = math.max(entryShort - tpShortDist, 0.00000001)
    
    dirOkLong  = not na(entryLong) and not na(tpLong) and not na(slLong) and tpLong > entryLong and slLong < entryLong
    dirOkShort = not na(entryShort) and not na(tpShort) and not na(slShort) and tpShort < entryShort and slShort > entryShort
    
    riskPctLong = entryLong > 0 ? math.abs(entryLong - slLong) / entryLong * 100.0 : na
    tpPctLong   = entryLong > 0 ? math.abs(tpLong - entryLong) / entryLong * 100.0 : na
    rrLong      = riskPctLong > 0 ? tpPctLong / riskPctLong : na
    
    riskPctShort = entryShort > 0 ? math.abs(slShort - entryShort) / entryShort * 100.0 : na
    tpPctShort   = entryShort > 0 ? math.abs(entryShort - tpShort) / entryShort * 100.0 : na
    rrShort      = riskPctShort > 0 ? tpPctShort / riskPctShort : na
    
    levRiskPctLong = riskPctLong * leverage
    levTpPctLong   = tpPctLong * leverage
    levRiskPctShort = riskPctShort * leverage
    levTpPctShort   = tpPctShort * leverage
    
    riskOkLong = not na(riskPctLong) and riskPctLong <= maxPlanRiskPct and levRiskPctLong <= maxLevRiskPct and rrLong >= minRR
    riskOkShort = not na(riskPctShort) and riskPctShort <= maxPlanRiskPct and levRiskPctShort <= maxLevRiskPct and rrShort >= minRR
    
    // Layer 2 — Indicator Engine
    emaFast = ta.ema(close, 20)
    emaSlow = ta.ema(close, 50)
    emaTrend = ta.ema(close, 200)
    rsiVal = ta.rsi(close, 14)
    [macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)
    volMA = ta.sma(volume, 20)
    rvol = volMA > 0 ? volume / volMA : na
    volOk = not na(rvol) and rvol >= 1.0
    
    // Layer 3 — Candle Behavior
    body = math.abs(close - open)
    barRange = math.max(high - low, syminfo.mintick)
    greenCandle = close > open
    redCandle = close < open
    closeNearHigh = barRange > 0 ? close >= low + barRange * 0.65 : false
    closeNearLow  = barRange > 0 ? close <= low + barRange * 0.35 : false
    
    upperReject = body > 0 ? (high - math.max(open, close)) >= body * 0.8 : false
    lowerReject = body > 0 ? (math.min(open, close) - low) >= body * 0.8 : false
    
    // Layer 4 — Bias Engine
    trendLong = close > emaFast and emaFast > emaSlow
    trendShort = close < emaFast and emaFast < emaSlow
    momentumLong = rsiVal >= 50 and rsiVal <= 72 and hist > 0 and hist >= hist[1]
    momentumShort = rsiVal <= 50 and rsiVal >= 28 and hist < 0 and hist <= hist[1]
    
    // Layer 5 — Setup & Overheat/Oversold Engine
    overheat = rsiVal > 72 or close > emaFast + atrVal * 1.8
    oversold = rsiVal < 28 or close < emaFast - atrVal * 1.8
    
    // Impulse guards
    bullishImpulse = greenCandle and closeNearHigh and close > close[1]
    bearishImpulse = redCandle and closeNearLow and close < close[1]
    
    // Layer 6 — Action Engine
    longTrendAction = trendLong and momentumLong and volOk and greenCandle and closeNearHigh and not overheat
    shortTrendAction = trendShort and momentumShort and volOk and redCandle and closeNearLow and not oversold
    
    longBreakoutAction = close > longTrigger and greenCandle and closeNearHigh and volOk
    shortBreakdownAction = close < shortTrigger and redCandle and closeNearLow and volOk
    
    longReversalAction = oversold and lowerReject and greenCandle and closeNearHigh and rvol >= 1.2 and hist > hist[1]
    shortReversalAction = overheat and upperReject and redCandle and closeNearLow and rvol >= 1.2 and hist < hist[1]
    
    validLongAction = validData and (longTrendAction or longBreakoutAction or longReversalAction) and riskOkLong and dirOkLong
    validShortAction = validData and (shortTrendAction or shortBreakdownAction or shortReversalAction) and riskOkShort and dirOkShort
    
    if bullishImpulse
        validShortAction := false
    if bearishImpulse
        validLongAction := false
        
    // Layer 7 — Flow & Score
    lowerWick = math.min(open, close) - low
    upperWick = high - math.max(open, close)
    longAbsorb  = lowerWick > body * 1.2 and closeNearHigh and rvol >= 1.3
    shortAbsorb = upperWick > body * 1.2 and closeNearLow and rvol >= 1.3
    smallBodyHighVol = body <= atrVal * 0.30 and rvol >= 1.8
    
    bullImpulse = greenCandle and closeNearHigh and rvol >= 1.2
    bearImpulse = redCandle and closeNearLow and rvol >= 1.2
    
    flow = bullImpulse and trendLong ? "LONG FLOW" : bearImpulse and trendShort ? "SHORT FLOW" : longAbsorb ? "BUY ABSORB" : shortAbsorb ? "SELL ABSORB" : smallBodyHighVol ? "SQUEEZE" : rvol < 0.5 ? "SEPI" : "NORMAL"
    
    longFlow = flow == "LONG FLOW" or flow == "BUY ABSORB"
    shortFlow = flow == "SHORT FLOW" or flow == "SELL ABSORB"
    
    // Flow conflict rule
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
    
    // Final action with score gate
    longScoreOk = scoreLong >= entryScore and scoreLong > scoreShort + scoreGap
    shortScoreOk = scoreShort >= entryScore and scoreShort > scoreLong + scoreGap
    
    action = validLongAction and longScoreOk ? "LONG" : validShortAction and shortScoreOk ? "SHORT" : "WAIT"
    
    finalEntry = action == "LONG" ? close : action == "SHORT" ? close : na
    finalTP = action == "LONG" ? tpLong : action == "SHORT" ? tpShort : na
    finalSL = action == "LONG" ? slLong : action == "SHORT" ? slShort : na
    tpPct = action == "LONG" ? tpPctLong : action == "SHORT" ? tpPctShort : na
    riskPct = action == "LONG" ? riskPctLong : action == "SHORT" ? riskPctShort : na
    rr = action == "LONG" ? rrLong : action == "SHORT" ? rrShort : na
    levTpPct = action == "LONG" ? levTpPctLong : action == "SHORT" ? levTpPctShort : na
    levRiskPct = action == "LONG" ? levRiskPctLong : action == "SHORT" ? levRiskPctShort : na
    
    score = action == "LONG" ? scoreLong : action == "SHORT" ? scoreShort : math.max(scoreLong, scoreShort)
    riskLabel = f_risk_label(levRiskPct)
    
    status = overheat ? "OVERHEAT" : oversold ? "OVERSOLD" : flowConflict ? "CONFLICT" : riskLabel == "HIGH" ? "RISKY" : action != "WAIT" ? action + " SETUP" : "WATCH"
    signal = action == "LONG" ? "LONG" : action == "SHORT" ? "SHORT" : riskLabel == "HIGH" or riskLabel == "RISKY" ? "RISKY" : "NEUTRAL"
    
    [close, longTrigger, shortTrigger, finalEntry, finalTP, finalSL, tpPct, riskPct, rr, levTpPct, levRiskPct, riskLabel, rsiVal, rvol * 100.0, flow, status, action, score, signal, syminfo.mintick]
"""

def generate_pine_script(symbols, batch_label):
    n = len(symbols)
    
    ticker_lines = []
    tick_lines = []
    decimals_lines = []
    for i, sym in enumerate(symbols):
        ticker_lines.append(f'tk{i+1} = "BINANCE:{sym["symbol"]}.P"')
        decimals_lines.append(f'dec{i+1} = {sym["price_decimals"]}')
        
    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(
            f'[now{idx}, longTrig{idx}, shortTrig{idx}, entry{idx}, tp_{idx}, sl_{idx}, pctTp{idx}, riskPct{idx}, rr{idx}, levTpPct{idx}, levRiskPct{idx}, risk{idx}, rsi{idx}, rvolPct{idx}, flow{idx}, status{idx}, action{idx}, score{idx}, signal{idx}, tick{idx}] = request.security(tk{idx}, tf, f_dashboard_engine())'
        )

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
    entryDisp{idx} = na(entry{idx}) ? "-" : f_fmt_price(entry{idx}, tick{idx})
    tpDisp{idx} = na(tp_{idx}) ? "-" : f_fmt_price(tp_{idx}, tick{idx})
    slDisp{idx} = na(sl_{idx}) ? "-" : f_fmt_price(sl_{idx}, tick{idx})
    pctTpDisp{idx} = na(pctTp{idx}) ? "-" : str.tostring(pctTp{idx}, "#.##") + "%"
    riskPctDisp{idx} = na(riskPct{idx}) ? "-" : str.tostring(riskPct{idx}, "#.##") + "%"
    rrDisp{idx} = na(rr{idx}) ? "-" : str.tostring(rr{idx}, "#.##")
    
    f_cell(tbl, 4, {row}, entryDisp{idx}, cDark, color.white)
    f_cell(tbl, 5, {row}, tpDisp{idx}, cDark, color.lime)
    f_cell(tbl, 6, {row}, slDisp{idx}, cDark, color.orange)
    f_cell(tbl, 7, {row}, pctTpDisp{idx}, cDark, color.white)
    f_cell(tbl, 8, {row}, riskPctDisp{idx}, cDark, color.white)
    f_cell(tbl, 9, {row}, rrDisp{idx}, cDark, color.white)
    
    f_cell(tbl, 10, {row}, str.tostring(leverage) + "x", cDark, color.white)
    f_cell(tbl, 11, {row}, risk{idx}, f_risk_color(risk{idx}), color.white)
    f_cell(tbl, 12, {row}, str.tostring(rsi{idx}, "#.0"), rsi{idx} < 30 ? cRed : rsi{idx} > 70 ? cOrange : cBlue, color.white)
    f_cell(tbl, 13, {row}, str.tostring(rvolPct{idx}, "#.0") + "%", rvolPct{idx} >= 120 ? cGreen : cDark, color.white)
    f_cell(tbl, 14, {row}, flow{idx}, cDark, color.white)
    f_cell(tbl, 15, {row}, status{idx}, cDark, color.yellow)
    f_cell(tbl, 16, {row}, action{idx}, f_action_color(action{idx}), color.white)
    f_cell(tbl, 17, {row}, str.tostring(score{idx}, "#"), f_score_color(score{idx}), color.white)
    f_cell(tbl, 18, {row}, signal{idx}, f_signal_color(signal{idx}), color.white)"""
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
    f_header(tbl, 10, "LEV")
    f_header(tbl, 11, "RISK")
    f_header(tbl, 12, "RSI")
    f_header(tbl, 13, "RVOL")
    f_header(tbl, 14, "FLOW")
    f_header(tbl, 15, "STATUS")
    f_header(tbl, 16, "ACTION")
    f_header(tbl, 17, "SCORE")
    f_header(tbl, 18, "SIGNAL")"""

    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = symbols[i]["symbol"]
        alert_lines.append(f'''var string activeSide{idx} = ""
var float activeEntry{idx} = na
var float activeTp{idx} = na
var float activeSl{idx} = na
var string lastEvent{idx} = ""
var int lastBar{idx} = na

longTpHit{idx} = activeSide{idx} == "LONG" and high >= activeTp{idx}
longSlHit{idx} = activeSide{idx} == "LONG" and low <= activeSl{idx}
shortTpHit{idx} = activeSide{idx} == "SHORT" and low <= activeTp{idx}
shortSlHit{idx} = activeSide{idx} == "SHORT" and high >= activeSl{idx}

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
else if event{idx} == "LONG_ENTRY"
    activeSide{idx} := "LONG"
    activeEntry{idx} := entry{idx}
    activeTp{idx} := tp_{idx}
    activeSl{idx} := sl_{idx}
else if event{idx} == "SHORT_ENTRY"
    activeSide{idx} := "SHORT"
    activeEntry{idx} := entry{idx}
    activeTp{idx} := tp_{idx}
    activeSl{idx} := sl_{idx}
    
sendAlert{idx} = event{idx} == "LONG_ENTRY" or event{idx} == "SHORT_ENTRY" or event{idx} == "LONG_TP_HIT" or event{idx} == "LONG_SL_HIT" or event{idx} == "SHORT_TP_HIT" or event{idx} == "SHORT_SL_HIT"
canAlert{idx} = sendAlert{idx} and (event{idx} != lastEvent{idx} or na(lastBar{idx}) or bar_index - lastBar{idx} >= cooldownBars)

alertTpPct{idx} = na(pctTp{idx}) ? 0.0 : pctTp{idx}
alertRiskPct{idx} = na(riskPct{idx}) ? 0.0 : riskPct{idx}
alertRr{idx} = na(rr{idx}) ? 0.0 : rr{idx}
alertLevTp{idx} = na(levTpPct{idx}) ? 0.0 : levTpPct{idx}
alertLevRisk{idx} = na(levRiskPct{idx}) ? 0.0 : levRiskPct{idx}

if barstate.isconfirmed and canAlert{idx}
    msg_{idx} = '{{"market": "BINANCE_FUTURES", "type": "FUTURES_SIGNAL", "event": "' + event{idx} + '", "side": "' + str.tostring(alertSide{idx}) + '", "symbol": "{t}", "tf": "' + tf + '", "now": ' + str.tostring(now{idx}) + ', "entry": ' + str.tostring(alertEntry{idx}) + ', "tp": ' + str.tostring(alertTp{idx}) + ', "sl": ' + str.tostring(alertSl{idx}) + ', "tp_pct": ' + str.tostring(alertTpPct{idx}) + ', "risk_pct": ' + str.tostring(alertRiskPct{idx}) + ', "rr": ' + str.tostring(alertRr{idx}) + ', "leverage": ' + str.tostring(leverage) + ', "lev_tp_pct": ' + str.tostring(alertLevTp{idx}) + ', "lev_risk_pct": ' + str.tostring(alertLevRisk{idx}) + ', "risk_label": "' + risk{idx} + '", "score": ' + str.tostring(score{idx}) + ', "flow": "' + flow{idx} + '", "signal": "' + signal{idx} + '", "price_text": {{"now": "' + f_fmt_price(now{idx}, tick{idx}) + '", "entry": "' + f_fmt_price(alertEntry{idx}, tick{idx}) + '", "tp": "' + f_fmt_price(alertTp{idx}, tick{idx}) + '", "sl": "' + f_fmt_price(alertSl{idx}, tick{idx}) + '"}}, "tick_size": ' + str.tostring(tick{idx}) + ', "price_decimals": ' + str.tostring(dec{idx}) + ', "time": ' + str.tostring(time) + '}}'
    alert(msg_{idx}, alert.freq_once_per_bar_close)
    lastEvent{idx} := event{idx}
    lastBar{idx} := bar_index
''')

    pine_code = f"""// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Strategy: Binance USD-M Autobot {batch_label}
//@version=6
indicator("Binance USD-M Autobot {batch_label}", overlay=true, max_bars_back=500)

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
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_right : pos == "Bottom Right" ? position.bottom_right : position.bottom_left
var tbl = table.new(tbl_pos, 19, {n+1}, border_width=1, border_color=#333333)

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
        print(f"  [BINANCE V2] Batch {batch_label} -> {len(batch_syms)} tickers")
        
    print(f"\\n[DONE] Generated Binance USD-M files")

if __name__ == "__main__":
    main()
