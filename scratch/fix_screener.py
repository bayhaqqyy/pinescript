import re

with open("tv_scripts/generate_screener.py", "r", encoding="utf-8") as f:
    content = f.read()

# I will replace ENGINE_TEMPLATE and everything after it.
new_code = r'''ENGINE_TEMPLATE = """
// ============================================================================
// INPUTS
// ============================================================================
tf = input.timeframe("15", "Timeframe Screener")
min_tv = input.float(1000000, "Min Volume (USDT)")

riskMode = input.string("INTRADAY", "Futures Risk Mode", options=["SCALP", "INTRADAY", "SWING", "CUSTOM"])
leverage = input.int(10, "Leverage", minval=1, maxval=125)
useLevGuard = input.bool(true, "Use Leverage Safety Guard")

customTpAtrMult = input.float(5.0, "CUSTOM TP ATR Mult", step=0.1)
customSlAtrMult = input.float(2.2, "CUSTOM SL ATR Mult", step=0.1)
customMinTpRawPct = input.float(2.0, "CUSTOM Min TP Raw %", step=0.1)
customMinSlRawPct = input.float(0.7, "CUSTOM Min SL Raw %", step=0.1)
customTargetLevProfitPct = input.float(45.0, "CUSTOM Target Lev Profit %", step=1.0)
customMaxLevRiskPct = input.float(18.0, "CUSTOM Max Lev Risk %", step=1.0)
customMinRR = input.float(1.8, "CUSTOM Min RR", step=0.1)

breakoutBufferPct = input.float(0.05, "Breakout Buffer %", step=0.01)
srAtrBuf = input.float(0.20, "SR ATR Buffer", step=0.05)

srLen = input.int(20, "Support/Resistance Lookback", minval=5, maxval=200)
atrLen = input.int(14, "ATR Length", minval=5, maxval=100)

pos = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

tpAtrMult = riskMode == "SCALP" ? 4.0 : riskMode == "INTRADAY" ? 5.0 : riskMode == "SWING" ? 8.0 : customTpAtrMult
slAtrMult = riskMode == "SCALP" ? 1.8 : riskMode == "INTRADAY" ? 2.2 : riskMode == "SWING" ? 3.0 : customSlAtrMult
minTpRawPct = riskMode == "SCALP" ? 1.2 : riskMode == "INTRADAY" ? 2.0 : riskMode == "SWING" ? 4.0 : customMinTpRawPct
minSlRawPct = riskMode == "SCALP" ? 0.45 : riskMode == "INTRADAY" ? 0.70 : riskMode == "SWING" ? 1.20 : customMinSlRawPct
targetLevProfitPct = riskMode == "SCALP" ? 30.0 : riskMode == "INTRADAY" ? 45.0 : riskMode == "SWING" ? 70.0 : customTargetLevProfitPct
maxLevRiskPct = riskMode == "SCALP" ? 12.0 : riskMode == "INTRADAY" ? 18.0 : riskMode == "SWING" ? 25.0 : customMaxLevRiskPct
minRR = riskMode == "SCALP" ? 1.6 : riskMode == "INTRADAY" ? 1.8 : riskMode == "SWING" ? 2.0 : customMinRR

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
      s == "BREAKOUT" or s == "BREAKDOWN" ? cLime :
      s == "LONG SETUP" or s == "SHORT SETUP" ? cBlue :
      s == "TP-HIT" ? cLime :
      s == "SL-BROKE" ? cRed :
      s == "BEARISH" ? cRed :
      s == "BULLISH" ? cGreen :
      cGray

f_zona_color(z) =>
    z == "LOW" ? cBlue :
      z == "MID" ? cYellow :
      z == "HIGH" ? cOrange :
      cRed

f_macd_color(m) =>
    m == "UP" ? cGreen :
      m == "DOWN" ? cRed :
      cYellow

f_signal_color(sig) =>
    sig == "LONG" ? cLime :
      sig == "SHORT" ? cRed :
      sig == "LONG SETUP" ? cBlue :
      sig == "SHORT SETUP" ? cOrange :
      sig == "LEV-RISK" ? cYellow :
      cGray

f_action_color(act) =>
    act == "BUY" or act == "LONG" ? cLime :
      act == "SELL" or act == "SHORT" ? cRed :
      str.contains(act, "BUY >") ? cBlue :
      str.contains(act, "SELL <") ? cOrange :
      act == "LEV RISK" ? cYellow :
      cGray

f_score_color(score) =>
    score >= 80 ? cLime :
      score >= 60 ? cGreen :
      score >= 40 ? cOrange :
      cRed

f_liq_color(liq) =>
    liq == "SAFE" ? cLime :
      liq == "RISKY" ? cOrange :
      cRed

f_cell(tbl, col, row, txt, bg, txtColor) =>
    table.cell(tbl, col, row, txt, bgcolor=bg, text_color=txtColor, text_size=size.small)

f_header(tbl, col, title) =>
    table.cell(tbl, col, 0, title, bgcolor=cHeader, text_color=color.yellow, text_size=size.small)

// ============================================================================
// DASHBOARD ENGINE
// ============================================================================
f_round_tick(x) => math.round(x / syminfo.mintick) * syminfo.mintick

f_dashboard_engine() =>
    sup = ta.lowest(low[1], srLen)
    rst = ta.highest(high[1], srLen)
    atrVal = ta.atr(atrLen)
    
    buf = breakoutBufferPct / 100.0
    longTrigger = math.max(rst * (1 + buf), rst + syminfo.mintick)
    shortTrigger = math.min(sup * (1 - buf), sup - syminfo.mintick)
    
    longBreak = close > longTrigger
    shortBreak = close < shortTrigger
    
    volMA = ta.sma(volume, 20)
    rvol = volMA > 0 ? volume / volMA : 0.0
    
    ema20 = ta.ema(close, 20)
    ema50 = ta.ema(close, 50)
    ema200 = ta.ema(close, 200)
    trendUp = close > ema20 and ema20 > ema50
    trendDown = close < ema20 and ema20 < ema50
    macroBull = close > ema200
    macroBear = close < ema200
    
    rsiVal = ta.rsi(close, 14)
    sRsi = ta.sma(rsiVal, 5)
    rsiLongOk = rsiVal >= 50 and rsiVal <= 72
    rsiShortOk = rsiVal <= 50 and rsiVal >= 28
    
    [macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)
    macdUp = macdLine > signalLine and hist > 0
    macdDown = macdLine < signalLine and hist < 0
    macdStatus = macdUp ? "UP" : macdDown ? "DOWN" : "MID"
    
    longCandidate = trendUp and rsiLongOk and macdUp and rvol >= 1.0
    shortCandidate = trendDown and rsiShortOk and macdDown and rvol >= 1.0
    
    entryLong = longBreak ? close : longTrigger
    entryShort = shortBreak ? close : shortTrigger
    
    slLongByAtrDist = atrVal * slAtrMult
    slLongByStructureDist = entryLong - (sup - atrVal * srAtrBuf)
    slLongByMinPctDist = entryLong * (minSlRawPct / 100.0)
    slLongDist = math.max(slLongByAtrDist, slLongByStructureDist, slLongByMinPctDist, syminfo.mintick)
    slLong = entryLong - slLongDist
    
    slShortByAtrDist = atrVal * slAtrMult
    slShortByStructureDist = (rst + atrVal * srAtrBuf) - entryShort
    slShortByMinPctDist = entryShort * (minSlRawPct / 100.0)
    slShortDist = math.max(slShortByAtrDist, slShortByStructureDist, slShortByMinPctDist, syminfo.mintick)
    slShort = entryShort + slShortDist
    
    tpLongByAtrDist = atrVal * tpAtrMult
    tpLongByMinPctDist = entryLong * (minTpRawPct / 100.0)
    tpLongByLevTargetDist = entryLong * ((targetLevProfitPct / leverage) / 100.0)
    tpLongByRRDist = slLongDist * minRR
    tpLongDist = math.max(tpLongByAtrDist, tpLongByMinPctDist, tpLongByLevTargetDist, tpLongByRRDist, syminfo.mintick)
    tpLong = entryLong + tpLongDist
    
    tpShortByAtrDist = atrVal * tpAtrMult
    tpShortByMinPctDist = entryShort * (minTpRawPct / 100.0)
    tpShortByLevTargetDist = entryShort * ((targetLevProfitPct / leverage) / 100.0)
    tpShortByRRDist = slShortDist * minRR
    tpShortDist = math.max(tpShortByAtrDist, tpShortByMinPctDist, tpShortByLevTargetDist, tpShortByRRDist, syminfo.mintick)
    tpShort = math.max(entryShort - tpShortDist, syminfo.mintick)
    
    rrLong = slLongDist > 0 ? tpLongDist / slLongDist : 0.0
    rrShort = slShortDist > 0 ? tpShortDist / slShortDist : 0.0
    
    rangeDenom = math.max(rst - sup, syminfo.mintick)
    rangePos = (close - sup) / rangeDenom
    rangePos := math.max(0.0, math.min(1.0, rangePos))
    
    riskPctLong = entryLong > 0 ? slLongDist / entryLong * 100.0 : na
    riskPctShort = entryShort > 0 ? slShortDist / entryShort * 100.0 : na
    
    maxSafeLevLong = not na(riskPctLong) and riskPctLong > 0 ? maxLevRiskPct / riskPctLong : na
    levRiskOkLong = not na(maxSafeLevLong) and leverage <= maxSafeLevLong
    
    maxSafeLevShort = not na(riskPctShort) and riskPctShort > 0 ? maxLevRiskPct / riskPctShort : na
    levRiskOkShort = not na(maxSafeLevShort) and leverage <= maxSafeLevShort
    
    scoreLong = 0.0
    scoreLong += trendUp ? 18 : 0
    scoreLong += macroBull ? 7 : 0
    scoreLong += rsiVal >= 50 and rsiVal <= 68 ? 15 : rsiVal > 68 and rsiVal <= 75 ? 8 : 0
    scoreLong += macdUp ? 15 : 0
    scoreLong += rvol >= 2.0 ? 15 : rvol >= 1.2 ? 10 : rvol >= 0.8 ? 5 : 0
    scoreLong += close >= longTrigger ? 10 : rangePos >= 0.55 and rangePos <= 0.90 ? 6 : 0
    scoreLong += rrLong >= minRR ? 10 : rrLong >= 1.2 ? 5 : 0
    scoreLong += levRiskOkLong ? 5 : 0
    scoreLong := math.min(scoreLong, 100)
    
    scoreShort = 0.0
    scoreShort += trendDown ? 18 : 0
    scoreShort += macroBear ? 7 : 0
    scoreShort += rsiVal <= 50 and rsiVal >= 32 ? 15 : rsiVal < 32 and rsiVal >= 25 ? 8 : 0
    scoreShort += macdDown ? 15 : 0
    scoreShort += rvol >= 2.0 ? 15 : rvol >= 1.2 ? 10 : rvol >= 0.8 ? 5 : 0
    scoreShort += close <= shortTrigger ? 10 : rangePos <= 0.45 and rangePos >= 0.10 ? 6 : 0
    scoreShort += rrShort >= minRR ? 10 : rrShort >= 1.2 ? 5 : 0
    scoreShort += levRiskOkShort ? 5 : 0
    scoreShort := math.min(scoreShort, 100)
    
    bias = scoreLong >= scoreShort + 8 ? "LONG" : scoreShort >= scoreLong + 8 ? "SHORT" : "NEUTRAL"
    
    finalEntry = bias == "LONG" ? entryLong : bias == "SHORT" ? entryShort : na
    finalTP = bias == "LONG" ? tpLong : bias == "SHORT" ? tpShort : na
    finalSL = bias == "LONG" ? slLong : bias == "SHORT" ? slShort : na
    finalEntry := f_round_tick(finalEntry)
    finalTP := f_round_tick(finalTP)
    finalSL := f_round_tick(finalSL)
    
    dirOkLong = bias == "LONG" and finalTP > finalEntry and finalSL < finalEntry
    dirOkShort = bias == "SHORT" and finalTP < finalEntry and finalSL > finalEntry
    dirOk = dirOkLong or dirOkShort
    
    riskPct = bias == "LONG" ? riskPctLong : bias == "SHORT" ? riskPctShort : na
    tpPct = bias == "LONG" ? (entryLong > 0 ? tpLongDist / entryLong * 100.0 : na) : bias == "SHORT" ? (entryShort > 0 ? tpShortDist / entryShort * 100.0 : na) : na
    rr = bias == "LONG" ? rrLong : bias == "SHORT" ? rrShort : na
    
    levTpPct = not na(tpPct) ? tpPct * leverage : na
    levRiskPct = not na(riskPct) ? riskPct * leverage : na
    
    approxLiqDistPct = 100.0 / leverage
    liqUtilization = not na(riskPct) and approxLiqDistPct > 0 ? riskPct / approxLiqDistPct : na
    liqWarn = na(liqUtilization) ? "N/A" : liqUtilization >= 0.80 ? "NEAR-LIQ" : liqUtilization >= 0.60 ? "RISKY" : "SAFE"
    
    liqOk = na(liqUtilization) ? false : liqUtilization < 0.70
    levRiskOk = bias == "LONG" ? levRiskOkLong : bias == "SHORT" ? levRiskOkShort : false
    levOk = not useLevGuard or (levRiskOk and liqOk)
    
    status = longBreak and longCandidate ? "BREAKOUT" : shortBreak and shortCandidate ? "BREAKDOWN" : longCandidate ? "LONG SETUP" : shortCandidate ? "SHORT SETUP" : close < slLong and trendDown ? "BEARISH" : close > slShort and trendUp ? "BULLISH" : "WAIT"
    
    signalRaw = scoreLong >= 75 and scoreLong > scoreShort + 8 and dirOkLong ? "LONG" : scoreShort >= 75 and scoreShort > scoreLong + 8 and dirOkShort ? "SHORT" : scoreLong >= 60 and scoreLong > scoreShort + 5 and dirOkLong ? "LONG SETUP" : scoreShort >= 60 and scoreShort > scoreLong + 5 and dirOkShort ? "SHORT SETUP" : "NEUTRAL"
    signal = not dirOk ? "NEUTRAL" : not levOk ? "LEV-RISK" : signalRaw
    
    actionRaw = signalRaw == "LONG" ? "BUY" : signalRaw == "SHORT" ? "SELL" : status == "LONG SETUP" ? "BUY > " + str.tostring(longTrigger, format.mintick) : status == "SHORT SETUP" ? "SELL < " + str.tostring(shortTrigger, format.mintick) : "WAIT"
    action = not levOk ? "LEV RISK" : actionRaw
    
    score = bias == "LONG" ? scoreLong : bias == "SHORT" ? scoreShort : math.max(scoreLong, scoreShort)
    
    body = math.abs(close - open)
    barRange = math.max(high - low, syminfo.mintick)
    lowerWick = math.min(open, close) - low
    upperWick = high - math.max(open, close)
    closeNearHigh = close >= low + barRange * 0.70
    closeNearLow = close <= low + barRange * 0.30
    
    bullImpulse = close > open and closeNearHigh and rvol >= 1.2
    bearImpulse = close < open and closeNearLow and rvol >= 1.2
    longAbsorb = lowerWick > body * 1.2 and closeNearHigh and rvol >= 1.3
    shortAbsorb = upperWick > body * 1.2 and closeNearLow and rvol >= 1.3
    smallBodyHighVol = body <= atrVal * 0.30 and rvol >= 1.8
    
    flow = bullImpulse and trendUp ? "LONG FLOW" : bearImpulse and trendDown ? "SHORT FLOW" : longAbsorb ? "BUY ABSORB" : shortAbsorb ? "SELL ABSORB" : smallBodyHighVol ? "SQUEEZE" : rvol < 0.5 ? "SEPI" : "NORMAL"
    
    zona = rangePos < 0.25 ? "LOW" : rangePos < 0.60 ? "MID" : rangePos < 0.85 ? "HIGH" : "EXTREME"
    
    [close, finalEntry, finalTP, finalSL, tpPct, riskPct, rr, levRiskPct, liqWarn, status, rsiVal, macdStatus, rvol * 100, flow, action, score, signal]
"""

def generate_pine_script(symbols, batch_label):
    n = len(symbols)
    
    ticker_lines = []
    for i, sym in enumerate(symbols):
        ticker_lines.append(f'tk{i+1} = "BINANCE:{sym}.P"')
        
    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(
            f'[now{idx}, entry{idx}, tp_{idx}, sl_{idx}, pctTp{idx}, riskPct{idx}, rr{idx}, levRisk{idx}, liq{idx}, status{idx}, rsi{idx}, macd{idx}, rvolPct{idx}, flow{idx}, action{idx}, score{idx}, signal{idx}] = request.security(tk{idx}, tf, f_dashboard_engine())'
        )

    row_chunks = []
    for i in range(n):
        idx = i + 1
        t = symbols[i]
        row = i + 1
        
        row_str = f"""    // Row {row}
    f_cell(tbl, 0, {row}, "{t}", color.rgb(30, 90, 180), color.white)
    f_cell(tbl, 1, {row}, tf, cDark, color.white)
    f_cell(tbl, 2, {row}, str.tostring(entry{idx}, format.mintick), cDark, color.white)
    f_cell(tbl, 3, {row}, str.tostring(now{idx}, format.mintick), cDark, color.white)
    f_cell(tbl, 4, {row}, str.tostring(tp_{idx}, format.mintick), cDark, color.lime)
    f_cell(tbl, 5, {row}, str.tostring(sl_{idx}, format.mintick), cDark, color.orange)
    f_cell(tbl, 6, {row}, str.tostring(pctTp{idx}, "#.##") + "%", cDark, color.white)
    f_cell(tbl, 7, {row}, str.tostring(riskPct{idx}, "#.##") + "%", cDark, color.white)
    f_cell(tbl, 8, {row}, str.tostring(rr{idx}, "#.##"), cDark, color.white)
    f_cell(tbl, 9, {row}, str.tostring(leverage) + "x", cDark, color.white)
    f_cell(tbl, 10, {row}, str.tostring(levRisk{idx}, "#.##") + "%", levRisk{idx} > maxLevRiskPct ? cRed : cDark, color.white)
    f_cell(tbl, 11, {row}, liq{idx}, f_liq_color(liq{idx}), color.white)
    f_cell(tbl, 12, {row}, status{idx}, f_status_color(status{idx}), color.white)
    f_cell(tbl, 13, {row}, str.tostring(rsi{idx}, "#.0"), rsi{idx} < 30 ? cRed : rsi{idx} > 70 ? cOrange : cBlue, color.white)
    f_cell(tbl, 14, {row}, macd{idx}, f_macd_color(macd{idx}), color.white)
    f_cell(tbl, 15, {row}, str.tostring(rvolPct{idx}, "#.0") + "%", rvolPct{idx} >= 150 ? cGreen : cDark, color.white)
    f_cell(tbl, 16, {row}, flow{idx}, cDark, color.white)
    f_cell(tbl, 17, {row}, action{idx}, f_action_color(action{idx}), color.white)
    f_cell(tbl, 18, {row}, str.tostring(score{idx}, "#"), f_score_color(score{idx}), color.white)
    f_cell(tbl, 19, {row}, signal{idx}, f_signal_color(signal{idx}), color.white)"""
        row_chunks.append(row_str)

    headers = """    f_header(tbl, 0, "PAIR")
    f_header(tbl, 1, "TF")
    f_header(tbl, 2, "ENTRY")
    f_header(tbl, 3, "NOW")
    f_header(tbl, 4, "TP")
    f_header(tbl, 5, "SL")
    f_header(tbl, 6, "TP%")
    f_header(tbl, 7, "RISK%")
    f_header(tbl, 8, "RR")
    f_header(tbl, 9, "LEV")
    f_header(tbl, 10, "L-RISK")
    f_header(tbl, 11, "LIQ")
    f_header(tbl, 12, "STATUS")
    f_header(tbl, 13, "RSI")
    f_header(tbl, 14, "MACD")
    f_header(tbl, 15, "RVOL")
    f_header(tbl, 16, "FLOW")
    f_header(tbl, 17, "ACTION")
    f_header(tbl, 18, "SCORE")
    f_header(tbl, 19, "SIGNAL")"""

    pine_code = f"""// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Strategy: Binance USD-M Autobot {batch_label}
//@version=6
indicator("Binance USD-M Autobot {batch_label}", overlay=true, max_bars_back=500)

{ENGINE_TEMPLATE}

// ============================================================================
// DATA FETCH
// ============================================================================
{chr(10).join(ticker_lines)}

{chr(10).join(security_lines)}

// ============================================================================
// UI TABLE
// ============================================================================
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_right : pos == "Bottom Right" ? position.bottom_right : position.bottom_left
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
        print(f"  [BINANCE V2] Batch {batch_label} -> {len(batch_syms)} tickers")
        
    print(f"\\n[DONE] Generated Binance USD-M files")

if __name__ == "__main__":
    main()
'''

idx = content.find('ENGINE_TEMPLATE = """')
if idx != -1:
    new_content = content[:idx] + new_code
    with open("tv_scripts/generate_screener.py", "w", encoding="utf-8") as f:
        f.write(new_content)
