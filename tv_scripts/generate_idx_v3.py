import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Fix console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# PINE SCRIPT IDX V3 ENGINE TEMPLATE
# ============================================================================
ENGINE_TEMPLATE = """
// ============================================================================
// INPUTS
// ============================================================================
tf = input.timeframe("{tf}", "Timeframe Screener")
min_tv = input.float(500000000, "Min Transaction Value per Bar (Rp)")

srLen = input.int(14, "S/R Length", minval=5, maxval=200)
atrLen = input.int(14, "ATR Length", minval=5, maxval=100)
leverage = input.int(1, "Leverage", minval=1, maxval=125)

entryScore = input.int(65, "Entry Score")
scoreGap = input.int(6, "Score Gap")

slAtrMult = input.float(1.4, "SL ATR Mult", step=0.1)
tpAtrMult = input.float(2.4, "TP ATR Mult (Unused)", step=0.1)
rr1 = input.float(2.0, "Risk Reward 1 (TP1)", minval=0.5, step=0.1)
rr2 = input.float(3.5, "Risk Reward 2 (TP2)", minval=0.5, step=0.1)

minSlRawPct = input.float(0.6, "Minimum SL Raw %", step=0.1)
minTpRawPct = input.float(1.0, "Minimum TP Raw %", step=0.1)
maxPlanRiskPct = input.float(2.0, "Max Raw Risk % For Action", step=0.5)
maxLevRiskPct = input.float(25.0, "Max Leveraged Risk % For Action", step=5.0)

breakoutBufferPct = input.float(0.04, "Breakout Buffer %", step=0.01)
srAtrBuffer = input.float(0.15, "S/R ATR Buffer", step=0.05)
useStructureSL = input.bool(true, "Use Structure SL When Reasonable")
maxStructureRiskPct = input.float(2.5, "Max Structure SL %", step=0.5)

cooldownBars = input.int(3, "Alert Cooldown Bars", minval=1)
useReversalEntry = input.bool(false, "Use Reversal As Entry")
sameBarRule = input.string("SL_FIRST", "Same Bar TP/SL Rule", options=["SL_FIRST", "TP_FIRST", "IGNORE"])
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

f_status_color(s) =>
    s == "FLYING" ? cLime :
      s == "RUNNING" ? cGreen :
      s == "SETUP" ? cBlue :
      s == "TP1-HIT" ? cLime :
      s == "TP2-HIT" ? cLime :
      s == "SL-BROKE" ? cRed :
      cGray

f_zona_color(z) =>
    z == "MURAH" ? cBlue :
      z == "MID" ? cYellow :
      cRed

f_macd_color(m) =>
    m == "UP" ? cGreen :
      m == "DOWN" ? cRed :
      cYellow

f_signal_color(sig) =>
    sig == "AKUMULASI" ? cLime :
      sig == "BOW-SIAP" ? cGreen :
      sig == "SETUP-OK" ? cBlue :
      sig == "DIST-AWAL" ? cOrange :
      sig == "WEAK" ? cRed :
      cGray

f_score_color(score) =>
    score >= 85 ? color.lime :
      score >= 70 ? color.green :
      score >= 55 ? color.yellow :
      score >= 40 ? color.orange :
      color.red

f_cell(tbl, col, row, txt, bg, txtColor) =>
    table.cell(tbl, col, row, txt, bgcolor=bg, text_color=txtColor, text_size=size.small)

f_header(tbl, col, title) =>
    table.cell(tbl, col, 0, title, bgcolor=cHeader, text_color=color.yellow, text_size=size.small)

f_value_idr(v) =>
    v >= 1000000000 ? str.tostring(v / 1000000000, "#.##") + "B" :
      v >= 1000000 ? str.tostring(v / 1000000, "#.##") + "M" :
      str.tostring(v, "#.##")

// ============================================================================
// CORE ENGINE FUNCTION (DASHBOARD)
// ============================================================================
f_round_tick(x) => math.round(x / syminfo.mintick) * syminfo.mintick

f_dashboard_engine() =>
    support = ta.lowest(low[1], srLen)
    resistance = ta.highest(high[1], srLen)
    
    atrVal = ta.atr(atrLen)
    rsiVal = ta.rsi(close, 14)
    [macdLine, macdSignal, macdHist] = ta.macd(close, 12, 26, 9)
    
    volMA = ta.sma(volume, 20)
    rvol = volMA > 0 ? volume / volMA : 0.0
    rvolPct = rvol * 100
    
    ema20 = ta.ema(close, 20)
    ema50 = ta.ema(close, 50)
    
    body = math.abs(close - open)
    candleRange = math.max(high - low, syminfo.mintick)
    upperWick = high - math.max(open, close)
    lowerWick = math.min(open, close) - low
    
    closeNearHigh = candleRange > 0 and close >= low + candleRange * 0.65
    closeNearLow  = candleRange > 0 and close <= low + candleRange * 0.35
    
    // 1. Breakout Entry: close breakouts lookback resistance
    breakoutEntry = close >= resistance * (1 - 0.002) and closeNearHigh and rvol >= 1.2
    
    // 2. Pullback Entry: healthy zone close near EMA20
    pullbackEntry = close > ema20 and close <= ema20 * 1.03 and rsiVal >= 40 and rsiVal <= 65 and macdLine > macdSignal
    
    // 3. Reversal Entry: oversold RSI with strong lower rejection wick
    reversalEntry = rsiVal < 35 and lowerWick > body * 1.2 and close > open and rvol >= 1.2
    
    validBuySetup = breakoutEntry or pullbackEntry or reversalEntry
    bearishCandle = close < open and closeNearLow and upperWick > body * 1.0
    validBuySetup := validBuySetup and not bearishCandle
    
    // Entry price (support-based)
    entryPrice = not na(support) and support > 0 ? support : close
    
    // SL: Stop Loss calculation
    baseSlDist = math.max(atrVal * slAtrMult, entryPrice * minSlRawPct / 100.0, syminfo.mintick)
    structSl = support - atrVal * srAtrBuffer
    structSlDist = entryPrice - structSl
    structRiskPct = entryPrice > 0 ? (structSlDist / entryPrice * 100.0) : na
    useStruct = useStructureSL and not na(structSlDist) and structSlDist > 0 and structRiskPct <= maxStructureRiskPct
    slDist = useStruct ? math.max(baseSlDist, structSlDist) : baseSlDist
    sl = entryPrice - slDist
    
    // TP: Dual take profit levels
    risk = math.max(entryPrice - sl, syminfo.mintick)
    tp1 = entryPrice + risk * rr1
    tp2 = entryPrice + risk * rr2
    
    entryPrice := f_round_tick(entryPrice)
    tp1 := f_round_tick(tp1)
    tp2 := f_round_tick(tp2)
    sl := f_round_tick(sl)
    
    // Risk checks
    riskOk = entryPrice > 0 and (slDist / entryPrice * 100.0) <= maxPlanRiskPct and (slDist / entryPrice * 100.0 * leverage) <= maxLevRiskPct
    validBuy = validBuySetup and riskOk
    
    valueBar = close * volume
    
    rangeSr = math.max(resistance - support, syminfo.mintick)
    rangePos = (close - support) / rangeSr
    zona = rangePos <= 0.382 ? "MURAH" : rangePos <= 0.618 ? "MID" : "MAHAL"
    
    trendScore = (close > ema20 ? 15 : 0) + (close > ema50 ? 15 : 0)
    zoneScore = zona == "MURAH" ? 20 : zona == "MID" ? 12 : 3
    macdBull = macdLine > macdSignal and macdHist > 0
    rsiHealthy = rsiVal >= 35 and rsiVal <= 65
    rsiHot = rsiVal > 65 and rsiVal <= 75
    momentumScore = (rsiHealthy ? 8 : rsiHot ? 5 : 0) + (macdBull ? 7 : 0) + (validBuy ? 10 : 0)
    volumeScore = rvol >= 2.0 ? 15 : rvol >= 1.3 ? 10 : rvol >= 0.8 ? 5 : 0
    
    bigAccum = lowerWick > body * 1.2 and rvol >= 2.0 and close >= open and close > low + candleRange * 0.5
    accum = rvol >= 1.3 and close > open and close > ema20
    distAwal = upperWick > body * 1.2 and rvol >= 1.5 and close < open
    sepi = rvol < 0.7
    
    bandarState = bigAccum ? "BIG ACCUM" : accum ? "ACCUM" : distAwal ? "DIST AWAL" : sepi ? "SEPI" : "NORMAL"
    
    flowScore = bigAccum ? 20 : accum ? 14 : distAwal ? 0 : sepi ? 2 : 8
    scoreRaw = trendScore + zoneScore + momentumScore + volumeScore + flowScore
    score = math.min(100, scoreRaw)
    
    tpHit = high >= tp1
    slBroken = low <= sl
    
    statusFlag = slBroken ? 1.0 : tpHit ? 2.0 : validBuy ? 3.0 : score >= 60 ? 4.0 : close > ema20 ? 5.0 : 0.0
    zonaFlag = zona == "MURAH" ? 1.0 : zona == "MID" ? 2.0 : 3.0
    macdFlag = macdLine > macdSignal ? 1.0 : 0.0
    bandarFlag = bigAccum ? 1.0 : accum ? 2.0 : distAwal ? 3.0 : sepi ? 4.0 : 0.0
    actionFlag = distAwal ? 1.0 : validBuy ? 2.0 : 0.0
    signalFlag = distAwal ? 1.0 : score >= 85 and bigAccum ? 2.0 : score >= 75 and not bearishCandle and zona != "MAHAL" ? 3.0 : score >= 65 and validBuy ? 4.0 : score >= 45 ? 5.0 : 0.0
    
    // Pack 5 flags into a single float (19 -> 14 variables)
    packedFlags = signalFlag + actionFlag * 10.0 + bandarFlag * 100.0 + macdFlag * 1000.0 + statusFlag * 10000.0
    
    [close, high, low, support, resistance, entryPrice, tp1, tp2, sl, rsiVal, rvolPct, valueBar, score, packedFlags]
"""

def generate_pine_script(strategy_type, tickers, batch_label, stocks_map, date_str):
    n = len(tickers)
    tf = "5" if strategy_type == "SCALP" else "60"
    title = f"SCALPING V3" if strategy_type == "SCALP" else f"BANDAR AI V3"
    
    ticker_lines = []
    for i, t in enumerate(tickers):
        tier = stocks_map.get(t, {}).get("tier", "SCALP_GORENGAN" if strategy_type == "SCALP" else "BANDAR_SWING")
        ticker_lines.append(f'tk{i+1} = "IDX:{t}"  // {tier}')
    
    security_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[idx - 1]
        security_lines.append(f'''// --- Ticker {idx} State Machine and Fetch ---
var string activeSide{idx} = ""
var float activeEntry{idx} = na
var float activeTp1_{idx} = na
var float activeTp2_{idx} = na
var float activeSl{idx} = na
var string lastEvent{idx} = ""
var int lastBar{idx} = na
var float activeMode{idx} = na

[now{idx}, hi{idx}, lo{idx}, sup{idx}, rst{idx}, entry{idx}, tp1_{idx}, tp2_{idx}, sl_{idx}, rsi{idx}, rvolPct{idx}, valueBar{idx}, score{idx}, packedFlags{idx}] = request.security(tk{idx}, tf, f_dashboard_engine())

// Unpack flags
signalFlag{idx} = math.floor(packedFlags{idx} % 10)
actionFlag{idx} = math.floor((packedFlags{idx} / 10) % 10)
bandarFlag{idx} = math.floor((packedFlags{idx} / 100) % 10)
macdFlag{idx}   = math.floor((packedFlags{idx} / 1000) % 10)
statusFlag{idx} = math.floor((packedFlags{idx} / 10000) % 10)

// Decode flags locally
statusRaw{idx} = statusFlag{idx} == 1.0 ? "SL-BROKE" : statusFlag{idx} == 2.0 ? "TP-HIT" : statusFlag{idx} == 3.0 ? "FLYING" : statusFlag{idx} == 4.0 ? "SETUP" : statusFlag{idx} == 5.0 ? "RUNNING" : "WAIT"
macd{idx} = macdFlag{idx} == 1.0 ? "UP" : "DOWN"
bandar{idx} = bandarFlag{idx} == 1.0 ? "BIG ACCUM" : bandarFlag{idx} == 2.0 ? "ACCUM" : bandarFlag{idx} == 3.0 ? "DIST AWAL" : bandarFlag{idx} == 4.0 ? "SEPI" : "NORMAL"
action{idx} = actionFlag{idx} == 1.0 ? "WASPADA" : actionFlag{idx} == 2.0 ? "BUY" : "WAIT"
signal{idx} = signalFlag{idx} == 1.0 ? "DIST-AWAL" : signalFlag{idx} == 2.0 ? "AKUMULASI" : signalFlag{idx} == 3.0 ? "BOW-SIAP" : signalFlag{idx} == 4.0 ? "SETUP-OK" : signalFlag{idx} == 5.0 ? "NETRAL" : "WEAK"

// Calculate zona locally on-chart to save memory
rangeSr{idx} = math.max(rst{idx} - sup{idx}, syminfo.mintick)
rangePos{idx} = (now{idx} - sup{idx}) / rangeSr{idx}
zona{idx} = rangePos{idx} <= 0.382 ? "MURAH" : rangePos{idx} <= 0.618 ? "MID" : "MAHAL"

// State Machine logic
longTpHit{idx} = activeSide{idx} == "BUY" and hi{idx} >= activeTp1_{idx}
longTp2Hit{idx} = activeSide{idx} == "BUY" and hi{idx} >= activeTp2_{idx}
longSlHit{idx} = activeSide{idx} == "BUY" and lo{idx} <= activeSl{idx}

bothHitLong{idx} = longTpHit{idx} and longSlHit{idx}
if bothHitLong{idx}
    if sameBarRule == "SL_FIRST"
        longTpHit{idx} := false
        longTp2Hit{idx} := false
    else if sameBarRule == "TP_FIRST"
        longSlHit{idx} := false
    else if sameBarRule == "IGNORE"
        longTpHit{idx} := false
        longTp2Hit{idx} := false
        longSlHit{idx} := false

// Only trigger entry on qualified signals
entryAllowed{idx} = action{idx} == "BUY" and (signal{idx} == "AKUMULASI" or signal{idx} == "BOW-SIAP" or signal{idx} == "SETUP-OK")
entryEvent{idx} = activeSide{idx} == "" and entryAllowed{idx} ? "BUY_ENTRY" : "NONE"
event{idx} = (activeSide{idx} == "BUY" and longSlHit{idx}) ? "SL_HIT" : (activeSide{idx} == "BUY" and longTp2Hit{idx}) ? "TP2_HIT" : (activeSide{idx} == "BUY" and longTpHit{idx}) ? "TP1_HIT" : entryEvent{idx}

alertSide{idx} = event{idx} == "BUY_ENTRY" ? "BUY" : activeSide{idx}
alertEntry{idx} = event{idx} == "BUY_ENTRY" ? entry{idx} : activeEntry{idx}
alertTp1_{idx} = event{idx} == "BUY_ENTRY" ? tp1_{idx} : activeTp1_{idx}
alertTp2_{idx} = event{idx} == "BUY_ENTRY" ? tp2_{idx} : activeTp2_{idx}
alertSl{idx} = event{idx} == "BUY_ENTRY" ? sl_{idx} : activeSl{idx}

if event{idx} == "SL_HIT" or event{idx} == "TP1_HIT" or event{idx} == "TP2_HIT"
    activeSide{idx} := ""
    activeEntry{idx} := na
    activeTp1_{idx} := na
    activeTp2_{idx} := na
    activeSl{idx} := na
    activeMode{idx} := na
else if event{idx} == "BUY_ENTRY"
    activeSide{idx} := "BUY"
    activeEntry{idx} := entry{idx}
    activeTp1_{idx} := tp1_{idx}
    activeTp2_{idx} := tp2_{idx}
    activeSl{idx} := sl_{idx}
    activeMode{idx} := signalFlag{idx}

sendAlert{idx} = event{idx} == "BUY_ENTRY" or event{idx} == "TP1_HIT" or event{idx} == "TP2_HIT" or event{idx} == "SL_HIT"
canAlert{idx} = sendAlert{idx} and (event{idx} != lastEvent{idx} or na(lastBar{idx}) or bar_index - lastBar{idx} >= cooldownBars)

alertModeRaw{idx} = event{idx} == "BUY_ENTRY" ? signalFlag{idx} : activeMode{idx}
alertMode{idx} = alertModeRaw{idx} == 1.0 ? "DIST-AWAL" : alertModeRaw{idx} == 2.0 ? "AKUMULASI" : alertModeRaw{idx} == 3.0 ? "BOW-SIAP" : alertModeRaw{idx} == 4.0 ? "SETUP-OK" : "NONE"

// Display values - locked if position is active, else dynamic
entryDisp{idx} = na(activeEntry{idx}) ? entry{idx} : activeEntry{idx}
tp1Disp{idx} = na(activeTp1_{idx}) ? tp1_{idx} : activeTp1_{idx}
tp2Disp{idx} = na(activeTp2_{idx}) ? tp2_{idx} : activeTp2_{idx}
slDisp{idx} = na(activeSl{idx}) ? sl_{idx} : activeSl{idx}

pctTp1_{idx} = entryDisp{idx} > 0 ? ((tp1Disp{idx} - entryDisp{idx}) / entryDisp{idx}) * 100.0 : na
pctTp2_{idx} = entryDisp{idx} > 0 ? ((tp2Disp{idx} - entryDisp{idx}) / entryDisp{idx}) * 100.0 : na
pnlPct{idx} = activeSide{idx} == "BUY" ? ((now{idx} - activeEntry{idx}) / activeEntry{idx}) * 100.0 : na

// Override status for active trades
status{idx} = activeSide{idx} == "BUY" ? "RUNNING" : (event{idx} == "TP1_HIT" or event{idx} == "TP2_HIT") ? "TP-HIT" : event{idx} == "SL_HIT" ? "SL-BROKE" : statusRaw{idx}
''')
    
    row_chunks = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        row = i + 1
        
        row_str = f'''    // Row {row}
    pnlDisp{idx} = na(pnlPct{idx}) ? "-" : (pnlPct{idx} >= 0.0 ? "+" : "") + str.tostring(pnlPct{idx}, "#.##") + "%"
    pnlBg{idx} = na(pnlPct{idx}) ? cDark : (pnlPct{idx} >= 0.0 ? cGreen : cRed)
    entryValDisp{idx} = na(entryDisp{idx}) ? "-" : str.tostring(entryDisp{idx}, "#")
    tp1ValDisp{idx} = na(tp1Disp{idx}) ? "-" : str.tostring(tp1Disp{idx}, "#")
    tp2ValDisp{idx} = na(tp2Disp{idx}) ? "-" : str.tostring(tp2Disp{idx}, "#")
    slValDisp{idx} = na(slDisp{idx}) ? "-" : str.tostring(slDisp{idx}, "#")
    
    f_cell(tbl, 0, {row}, "{t}", color.rgb(30, 90, 180), color.white)
    f_cell(tbl, 1, {row}, tf, cDark, color.white)
    f_cell(tbl, 2, {row}, str.tostring(sup{idx}, "#"), cDark, color.white)
    f_cell(tbl, 3, {row}, str.tostring(rst{idx}, "#"), cDark, color.white)
    f_cell(tbl, 4, {row}, entryValDisp{idx}, cDark, color.white)
    f_cell(tbl, 5, {row}, str.tostring(now{idx}, "#"), cDark, color.white)
    f_cell(tbl, 6, {row}, tp1ValDisp{idx}, cDark, color.lime)
    f_cell(tbl, 7, {row}, tp2ValDisp{idx}, cDark, color.green)
    f_cell(tbl, 8, {row}, slValDisp{idx}, cDark, color.orange)
    f_cell(tbl, 9, {row}, pnlDisp{idx}, pnlBg{idx}, color.white)
    f_cell(tbl, 10, {row}, str.tostring(pctTp1_{idx}, "#.##") + "%", pctTp1_{idx} >= 0 ? cGreen : cRed, color.white)
    f_cell(tbl, 11, {row}, str.tostring(pctTp2_{idx}, "#.##") + "%", pctTp2_{idx} >= 0 ? cGreen : cRed, color.white)
    f_cell(tbl, 12, {row}, status{idx}, f_status_color(status{idx}), color.white)
    f_cell(tbl, 13, {row}, zona{idx}, f_zona_color(zona{idx}), color.white)
    f_cell(tbl, 14, {row}, str.tostring(rsi{idx}, "#.0"), rsi{idx} < 30 ? cRed : rsi{idx} > 70 ? cOrange : cBlue, color.white)
    f_cell(tbl, 15, {row}, macd{idx}, f_macd_color(macd{idx}), color.white)
    f_cell(tbl, 16, {row}, str.tostring(rvolPct{idx}, "#.0") + "%", rvolPct{idx} >= 150 ? cGreen : cDark, color.white)
    f_cell(tbl, 17, {row}, f_value_idr(valueBar{idx}), valueBar{idx} >= min_tv ? cGreen : cDark, color.white)
    f_cell(tbl, 18, {row}, bandar{idx}, f_signal_color(bandar{idx}), color.white)
    f_cell(tbl, 19, {row}, action{idx}, action{idx} == "WASPADA" ? cOrange : cGreen, color.white)
    f_cell(tbl, 20, {row}, str.tostring(score{idx}, "#"), f_score_color(score{idx}), color.white)
    f_cell(tbl, 21, {row}, signal{idx}, f_signal_color(signal{idx}), color.white)'''
        row_chunks.append(row_str)
 
    headers = '''    f_header(tbl, 0, "EMITEN")
    f_header(tbl, 1, "TF")
    f_header(tbl, 2, "SUP")
    f_header(tbl, 3, "RST")
    f_header(tbl, 4, "ENTRY")
    f_header(tbl, 5, "NOW")
    f_header(tbl, 6, "TP1")
    f_header(tbl, 7, "TP2")
    f_header(tbl, 8, "SL")
    f_header(tbl, 9, "PnL%")
    f_header(tbl, 10, "%TP1")
    f_header(tbl, 11, "%TP2")
    f_header(tbl, 12, "STATUS")
    f_header(tbl, 13, "ZONA")
    f_header(tbl, 14, "RSI")
    f_header(tbl, 15, "MACD")
    f_header(tbl, 16, "RVOL")
    f_header(tbl, 17, "VALUE")
    f_header(tbl, 18, "FLOW")
    f_header(tbl, 19, "ACTION")
    f_header(tbl, 20, "SCORE")
    f_header(tbl, 21, "SINYAL")'''
 
    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        tier = stocks_map.get(t, {}).get("tier", "SCALP_GORENGAN" if strategy_type == "SCALP" else "BANDAR_SWING")
        hint = "intraday (menit-jam)" if strategy_type == "SCALP" else "swing 3-7 hari"
        
        alert_lines.append(f'''    if barstate.isconfirmed and canAlert{idx}
        msg_{idx} = '{{"market": "IDX", "type": "{strategy_type}", "tier": "{tier}", "event": "' + event{idx} + '", "side": "' + str.tostring(alertSide{idx}) + '", "ticker": "{t}", "tf": "' + tf + '", "now": ' + str.tostring(now{idx}) + ', "entry": ' + str.tostring(alertEntry{idx}) + ', "tp1": ' + str.tostring(alertTp1_{idx}) + ', "tp2": ' + str.tostring(alertTp2_{idx}) + ', "sl": ' + str.tostring(alertSl{idx}) + ', "tp_pct": ' + str.tostring(pctTp1_{idx}) + ', "tp2_pct": ' + str.tostring(pctTp2_{idx}) + ', "risk_pct": ' + str.tostring(not na(alertEntry{idx}) and alertEntry{idx} > 0 ? math.abs(alertEntry{idx} - alertSl{idx}) / alertEntry{idx} * 100.0 : 0.0) + ', "score": ' + str.tostring(score{idx}) + ', "zona": "' + zona{idx} + '", "bandar": "' + bandar{idx} + '", "holding_hint": "{hint}", "transaction_value": ' + str.tostring(valueBar{idx}) + ', "action": "' + action{idx} + '", "signal": "' + event{idx} + '", "support": ' + str.tostring(sup{idx}) + ', "resistance": ' + str.tostring(rst{idx}) + ', "time": ' + str.tostring(time) + '}}'
        alert(msg_{idx}, alert.freq_once_per_bar_close)
        lastEvent{idx} := event{idx}
        lastBar{idx} := bar_index''')
 
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Generated on {date_str} | Strategy: {title}
//@version=6
indicator("{title} - BATCH {batch_label} ({n} Emiten)", overlay=true, max_bars_back=200)
 
{ENGINE_TEMPLATE.replace("{tf}", tf)}

// ============================================================================
// TICKER DEFINITIONS
// ============================================================================
{chr(10).join(ticker_lines)}

// ============================================================================
// DATA FETCH - request.security
// ============================================================================
{chr(10).join(security_lines)}

// ============================================================================
// TABLE DISPLAY
// ============================================================================
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_left : pos == "Bottom Right" ? position.bottom_right : position.bottom_left
var tbl = table.new(tbl_pos, 22, {n + 1}, border_width=1, border_color=#333333)

if barstate.islast
{headers}
{chr(10).join(row_chunks)}

// ============================================================================
// ALERTS
// ============================================================================
{chr(10).join(alert_lines)}

plot(close, display=display.none)
'''
    return script

def get_batch_label(idx):
    label = ""
    temp = idx
    while temp >= 0:
        label = chr(65 + (temp % 26)) + label
        temp = (temp // 26) - 1
    return label

def main():
    scalp_stocks_path = os.path.join(SCRIPT_DIR, "scalping_stocks.json")
    if os.path.exists(scalp_stocks_path):
        with open(scalp_stocks_path, "r") as f:
            scalp_data = json.load(f)
        scalp_map = {s["ticker"]: s for s in scalp_data["stocks"]}
        
        # Flatten all scalp tickers in order from batch_groups
        all_scalp_tickers = []
        for tickers in scalp_data["batch_groups"].values():
            all_scalp_tickers.extend(tickers)

        # Chunk into groups of at most 8
        scalp_batches = [all_scalp_tickers[i:i + 8] for i in range(0, len(all_scalp_tickers), 8)]

        scalp_count = 0
        for idx, batch_tickers in enumerate(scalp_batches):
            label = get_batch_label(idx)
            filename = f"scalping_v2_batch_{label.lower()}.pine" # Generating into the main tv_scripts dir
            filepath = os.path.join(SCRIPT_DIR, filename)
            script = generate_pine_script("SCALP", batch_tickers, label, scalp_map, scalp_data["date"])
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(script)
            scalp_count += 1
            print(f"  [SCALP V3]  Batch {label} -> {len(batch_tickers)} emiten")
            
    bandar_stocks_path = os.path.join(SCRIPT_DIR, "bandar_ai_stocks.json")
    if os.path.exists(bandar_stocks_path):
        with open(bandar_stocks_path, "r") as f:
            bandar_data = json.load(f)
        bandar_map = {s["ticker"]: s for s in bandar_data["stocks"]}
        
        # Flatten all bandar tickers in order from batch_groups
        all_bandar_tickers = []
        for tickers in bandar_data["batch_groups"].values():
            all_bandar_tickers.extend(tickers)

        # Chunk into groups of at most 8
        bandar_batches = [all_bandar_tickers[i:i + 8] for i in range(0, len(all_bandar_tickers), 8)]

        bandar_count = 0
        for idx, batch_tickers in enumerate(bandar_batches):
            label = get_batch_label(idx)
            filename = f"bandar_ai_v2_batch_{label.lower()}.pine" # Generating into the main tv_scripts dir
            filepath = os.path.join(SCRIPT_DIR, filename)
            script = generate_pine_script("BANDAR_AI", batch_tickers, label, bandar_map, bandar_data["date"])
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(script)
            bandar_count += 1
            print(f"  [BANDAR V3] Batch {label} -> {len(batch_tickers)} emiten")

if __name__ == "__main__":
    main()
