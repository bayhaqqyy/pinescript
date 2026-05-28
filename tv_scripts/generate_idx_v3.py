import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Fix console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# PINE SCRIPT V3 ENGINE TEMPLATE
# ============================================================================
ENGINE_TEMPLATE = """
// ============================================================================
// INPUTS
// ============================================================================
tf = input.timeframe("{tf}", "Timeframe Screener")
min_tv = input.float(500000000, "Min Transaction Value per Bar (Rp)")

srLen = input.int(20, "Support/Resistance Lookback", minval=5, maxval=200)
atrLen = input.int(14, "ATR Length", minval=5, maxval=100)
slBufferPct = input.float(0.5, "SL Buffer %", minval=0.0, step=0.1)
slAtrMult = input.float(1.5, "SL ATR Mult (Wider)", minval=0.1, step=0.1)
rr1 = input.float(2.0, "Risk Reward 1 (TP1 - Wide)", minval=0.5, step=0.1)
rr2 = input.float(3.5, "Risk Reward 2 (TP2 - Wider)", minval=0.5, step=0.1)
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
      s == "TP-HIT" ? cLime :
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
f_round_tick(x) =>
    math.round(x / syminfo.mintick) * syminfo.mintick

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
    ema200 = ta.ema(close, 200)
    
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
    validBuy = validBuySetup and not bearishCandle
    
    // Define entry price as current close if buying, else next resistance breakout
    entryPrice = close
    
    // SL: Wider Stop Loss (at least 1.5 * ATR and at least 2% distance)
    minSlDist = math.max(atrVal * slAtrMult, entryPrice * 0.02)
    slRaw = entryPrice - minSlDist
    sl = support < entryPrice and support > 0 ? math.min(support * (1 - slBufferPct / 100), slRaw) : slRaw
    
    // TP: Wider dual take profit levels
    risk = math.max(entryPrice - sl, syminfo.mintick)
    tp1 = entryPrice + risk * rr1
    tp2 = entryPrice + risk * rr2
    
    entryPrice := f_round_tick(entryPrice)
    tp1 := f_round_tick(tp1)
    tp2 := f_round_tick(tp2)
    sl := f_round_tick(sl)
    
    pctTp1 = close > 0 ? ((tp1 - close) / close) * 100 : na
    pctTp2 = close > 0 ? ((tp2 - close) / close) * 100 : na
    
    valueBar = close * volume
    
    rangeSr = math.max(resistance - support, syminfo.mintick)
    rangePos = (close - support) / rangeSr
    zona = rangePos <= 0.382 ? "MURAH" : rangePos <= 0.618 ? "MID" : "MAHAL"
    
    trendScore = (close > ema20 ? 10 : 0) + (close > ema50 ? 10 : 0) + (close > ema200 ? 10 : 0)
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
    
    tpHit = close >= tp1
    slBroken = close <= sl
    
    status = slBroken ? "SL-BROKE" : tpHit ? "TP-HIT" : validBuy ? "FLYING" : score >= 60 ? "SETUP" : close > ema20 ? "RUNNING" : "WAIT"
    
    signal = distAwal ? "DIST-AWAL" : score >= 85 and bigAccum ? "AKUMULASI" : score >= 75 and not bearishCandle and zona != "MAHAL" ? "BOW-SIAP" : score >= 65 and validBuy ? "SETUP-OK" : score >= 45 ? "NETRAL" : "WEAK"
    action = distAwal ? "WASPADA" : validBuy ? "BUY>" + str.tostring(entryPrice, format.mintick) : "WAIT"
    
    [close, support, resistance, entryPrice, tp1, tp2, sl, pctTp1, pctTp2, status, zona, rsiVal, macdLine > macdSignal ? "UP" : "DOWN", rvolPct, valueBar, bandarState, action, score, signal]
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
        security_lines.append(
            f'[now{idx}, sup{idx}, rst{idx}, entry{idx}, tp1_{idx}, tp2_{idx}, sl_{idx}, pctTp1_{idx}, pctTp2_{idx}, status{idx}, zona{idx}, rsi{idx}, macd{idx}, rvolPct{idx}, valueBar{idx}, bandar{idx}, action{idx}, score{idx}, signal{idx}] = request.security(tk{idx}, tf, f_dashboard_engine())'
        )
    
    row_chunks = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        row = i + 1
        
        row_str = f'''    // Row {row}
    f_cell(tbl, 0, {row}, "{t}", color.rgb(30, 90, 180), color.white)
    f_cell(tbl, 1, {row}, tf, cDark, color.white)
    f_cell(tbl, 2, {row}, str.tostring(sup{idx}, format.mintick), cDark, color.white)
    f_cell(tbl, 3, {row}, str.tostring(rst{idx}, format.mintick), cDark, color.white)
    f_cell(tbl, 4, {row}, str.tostring(entry{idx}, format.mintick), cDark, color.white)
    f_cell(tbl, 5, {row}, str.tostring(now{idx}, format.mintick), cDark, color.white)
    f_cell(tbl, 6, {row}, str.tostring(tp1_{idx}, format.mintick), cDark, color.lime)
    f_cell(tbl, 7, {row}, str.tostring(tp2_{idx}, format.mintick), cDark, color.green)
    f_cell(tbl, 8, {row}, str.tostring(sl_{idx}, format.mintick), cDark, color.orange)
    f_cell(tbl, 9, {row}, str.tostring(pctTp1_{idx}, "#.##") + "%", pctTp1_{idx} >= 0 ? cGreen : cRed, color.white)
    f_cell(tbl, 10, {row}, str.tostring(pctTp2_{idx}, "#.##") + "%", pctTp2_{idx} >= 0 ? cGreen : cRed, color.white)
    f_cell(tbl, 11, {row}, status{idx}, f_status_color(status{idx}), color.white)
    f_cell(tbl, 12, {row}, zona{idx}, f_zona_color(zona{idx}), color.white)
    f_cell(tbl, 13, {row}, str.tostring(rsi{idx}, "#.0"), rsi{idx} < 30 ? cRed : rsi{idx} > 70 ? cOrange : cBlue, color.white)
    f_cell(tbl, 14, {row}, macd{idx}, f_macd_color(macd{idx}), color.white)
    f_cell(tbl, 15, {row}, str.tostring(rvolPct{idx}, "#.0") + "%", rvolPct{idx} >= 150 ? cGreen : cDark, color.white)
    f_cell(tbl, 16, {row}, f_value_idr(valueBar{idx}), valueBar{idx} >= min_tv ? cGreen : cDark, color.white)
    f_cell(tbl, 17, {row}, bandar{idx}, f_signal_color(bandar{idx}), color.white)
    f_cell(tbl, 18, {row}, action{idx}, action{idx} == "WASPADA" ? cOrange : cGreen, color.white)
    f_cell(tbl, 19, {row}, str.tostring(score{idx}, "#"), f_score_color(score{idx}), color.white)
    f_cell(tbl, 20, {row}, signal{idx}, f_signal_color(signal{idx}), color.white)'''
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
    f_header(tbl, 9, "%TP1")
    f_header(tbl, 10, "%TP2")
    f_header(tbl, 11, "STATUS")
    f_header(tbl, 12, "ZONA")
    f_header(tbl, 13, "RSI")
    f_header(tbl, 14, "MACD")
    f_header(tbl, 15, "RVOL")
    f_header(tbl, 16, "VALUE")
    f_header(tbl, 17, "FLOW")
    f_header(tbl, 18, "ACTION")
    f_header(tbl, 19, "SCORE")
    f_header(tbl, 20, "SINYAL")'''

    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        tier = stocks_map.get(t, {}).get("tier", "SCALP_GORENGAN" if strategy_type == "SCALP" else "BANDAR_SWING")
        hint = "intraday (menit-jam)" if strategy_type == "SCALP" else "swing 3-7 hari"
        
        alert_lines.append(f'''    if (signal{idx} == "AKUMULASI" or signal{idx} == "BOW-SIAP" or signal{idx} == "SETUP-OK") and valueBar{idx} >= min_tv
        alert('{{"type":"{strategy_type}_V3","tier":"{tier}","ticker":"{t}","tf":"' + tf + '","signal":"' + signal{idx} + '","action":"' + action{idx} + '","entry":' + str.tostring(entry{idx}) + ',"tp1":' + str.tostring(tp1_{idx}) + ',"tp2":' + str.tostring(tp2_{idx}) + ',"sl":' + str.tostring(sl_{idx}) + ',"support":' + str.tostring(sup{idx}) + ',"resistance":' + str.tostring(rst{idx}) + ',"score":' + str.tostring(score{idx}) + ',"zona":"' + zona{idx} + '","bandar":"' + bandar{idx} + '","holding_hint":"{hint}","transaction_value":' + str.tostring(valueBar{idx}) + ',"time":' + str.tostring(time) + '}}', alert.freq_once_per_bar_close)''')

    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Generated on {date_str} | Strategy: {title} (Dashboard)
//@version=6
indicator("{title} - BATCH {batch_label} ({n} Emiten)", overlay=true, max_bars_back=500)

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
var tbl = table.new(tbl_pos, 21, {n + 1}, border_width=1, border_color=#333333)

if barstate.islast
{headers}
{chr(10).join(row_chunks)}

// ============================================================================
// ALERTS - Webhook JSON
// ============================================================================
if barstate.islast and barstate.isconfirmed
{chr(10).join(alert_lines)}

plot(close, display=display.none)
'''
    return script

def main():
    scalp_stocks_path = os.path.join(SCRIPT_DIR, "scalping_stocks.json")
    if os.path.exists(scalp_stocks_path):
        with open(scalp_stocks_path, "r") as f:
            scalp_data = json.load(f)
        scalp_map = {s["ticker"]: s for s in scalp_data["stocks"]}
        
        scalp_count = 0
        for batch_key, tickers in scalp_data["batch_groups"].items():
            label = batch_key.split("_")[1].upper()
            filename = f"scalping_v2_batch_{label.lower()}.pine" # Generating into the main tv_scripts dir
            filepath = os.path.join(SCRIPT_DIR, filename)
            script = generate_pine_script("SCALP", tickers, label, scalp_map, scalp_data["date"])
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(script)
            scalp_count += 1
            print(f"  [SCALP V3]  Batch {label} -> {len(tickers)} emiten")
            
    bandar_stocks_path = os.path.join(SCRIPT_DIR, "bandar_ai_stocks.json")
    if os.path.exists(bandar_stocks_path):
        with open(bandar_stocks_path, "r") as f:
            bandar_data = json.load(f)
        bandar_map = {s["ticker"]: s for s in bandar_data["stocks"]}
        
        bandar_count = 0
        for batch_key, tickers in bandar_data["batch_groups"].items():
            label = batch_key.split("_")[1].upper()
            filename = f"bandar_ai_v2_batch_{label.lower()}.pine" # Generating into the main tv_scripts dir
            filepath = os.path.join(SCRIPT_DIR, filename)
            script = generate_pine_script("BANDAR_AI", tickers, label, bandar_map, bandar_data["date"])
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(script)
            bandar_count += 1
            print(f"  [BANDAR V3] Batch {label} -> {len(tickers)} emiten")

if __name__ == "__main__":
    main()
