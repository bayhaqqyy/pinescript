import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def _exchange_prefix(exchange: str) -> str:
    return {"NASDAQ": "NASDAQ", "NYSE": "NYSE", "AMEX": "AMEX"}.get(exchange, "NASDAQ")

ENGINE_TEMPLATE = """
// ============================================================================
// INPUTS
// ============================================================================
tf = input.timeframe("{tf}", "Timeframe Screener")
min_tv = input.float(1000000, "Min Volume ($)")

srLen = input.int(20, "Support/Resistance Lookback", minval=5, maxval=200)
atrLen = input.int(14, "ATR Length", minval=5, maxval=100)
entryBufferPct = input.float(0.5, "Entry Buffer %", minval=0.0, step=0.1)
slBufferPct = input.float(0.5, "SL Buffer %", minval=0.0, step=0.1)
slAtrMult = input.float(1.0, "SL ATR Mult", minval=0.1, step=0.1)
rr = input.float(2.0, "Risk Reward", minval=0.5, step=0.1)
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
    sig == "BREAKOUT BUY" ? cLime :
      sig == "BULL ABSORB" ? cGreen :
      sig == "SNIPER BUY" ? cLime :
      sig == "SNIPER SELL" ? cRed :
      sig == "AKUMULASI" ? cLime :
      sig == "BOW-SIAP" ? cGreen :
      sig == "SETUP-OK" ? cBlue :
      sig == "DIST-AWAL" ? cOrange :
      sig == "WEAK" ? cRed :
      sig == "DISTRIBUTION" ? cRed :
      sig == "BEAR ABSORB" ? cOrange :
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
    v >= 1000000000 ? "$" + str.tostring(v / 1000000000, "#.##") + "B" :
      v >= 1000000 ? "$" + str.tostring(v / 1000000, "#.##") + "M" :
      "$" + str.tostring(v, "#.##")

// ============================================================================
// CORE ENGINE FUNCTION (DASHBOARD)
// ============================================================================
f_round_tick(x) => math.round(x / syminfo.mintick) * syminfo.mintick

f_dashboard_engine(strategy_mode) =>
    support = ta.lowest(low[1], srLen)
    resistance = ta.highest(high[1], srLen)
    entry = resistance * (1 + entryBufferPct / 100)
    atrVal = ta.atr(atrLen)
    slBySupport = support * (1 - slBufferPct / 100)
    slByAtr = entry - atrVal * slAtrMult
    slRaw = math.max(slBySupport, slByAtr)
    sl = math.min(slRaw, entry - syminfo.mintick)
    
    risk = math.max(entry - sl, syminfo.mintick)
    tp = entry + risk * rr
    
    entry := f_round_tick(entry)
    tp := f_round_tick(tp)
    sl := f_round_tick(sl)
    
    pctTp = close > 0 ? ((tp - close) / close) * 100 : na
    profitPct = entry > 0 ? ((tp - entry) / entry) * 100 : na
    
    rsiVal = ta.rsi(close, 14)
    rsiBase = rsiVal
    stochRsiRaw = ta.stoch(rsiBase, rsiBase, rsiBase, 14)
    stochK = ta.sma(stochRsiRaw, 3)
    stochD = ta.sma(stochK, 3)
    srsiState = stochK > stochD and stochK > stochK[1] ? "UP+" : stochK > stochD ? "UP" : stochK < stochD and stochK < stochK[1] ? "D-" : "D"
    
    [macdLine, macdSignal, macdHist] = ta.macd(close, 12, 26, 9)
    macdState = macdLine > macdSignal and macdHist > macdHist[1] ? "UP" : macdLine < macdSignal and macdHist < macdHist[1] ? "DOWN" : "MID"
    
    volMA = ta.sma(volume, 20)
    rvol = volMA > 0 ? volume / volMA : 0.0
    rvolPct = rvol * 100
    
    valueBar = close * volume
    
    rangeSr = math.max(resistance - support, syminfo.mintick)
    rangePos = (close - support) / rangeSr
    zona = rangePos <= 0.382 ? "MURAH" : rangePos <= 0.618 ? "MID" : "MAHAL"
    
    ema20 = ta.ema(close, 20)
    ema50 = ta.ema(close, 50)
    ema200 = ta.ema(close, 200)
    
    trendScore = (close > ema20 ? 10 : 0) + (close > ema50 ? 10 : 0) + (close > ema200 ? 10 : 0)
    zoneScore = zona == "MURAH" ? 20 : zona == "MID" ? 12 : 3
    macdBull = macdLine > macdSignal and macdHist > 0
    rsiHealthy = rsiVal >= 35 and rsiVal <= 65
    rsiHot = rsiVal > 65 and rsiVal <= 75
    momentumScore = (rsiHealthy ? 8 : rsiHot ? 5 : 0) + (macdBull ? 7 : 0) + (close >= entry ? 5 : 0)
    volumeScore = rvol >= 2.0 ? 15 : rvol >= 1.3 ? 10 : rvol >= 0.8 ? 5 : 0
    
    body = math.abs(close - open)
    candleRange = math.max(high - low, syminfo.mintick)
    upperWick = high - math.max(open, close)
    lowerWick = math.min(open, close) - low
    
    bigAccum = lowerWick > body * 1.2 and rvol >= 2.0 and close >= open and close > low + candleRange * 0.5
    accum = rvol >= 1.3 and close > open and close > ema20
    distAwal = upperWick > body * 1.2 and rvol >= 1.5 and close < open
    sepi = rvol < 0.7
    
    bandarState = bigAccum ? "BIG ACCUM" : accum ? "ACCUM" : distAwal ? "DIST AWAL" : sepi ? "SEPI" : "NORMAL"
    
    flowScore = bigAccum ? 20 : accum ? 14 : distAwal ? 0 : sepi ? 2 : 8
    scoreRaw = trendScore + zoneScore + momentumScore + volumeScore + flowScore
    score = math.min(100, scoreRaw)
    
    breakout = close >= entry
    nearSetup = close < entry and close >= support and score >= 60
    aboveTrend = close > ema20
    tpHit = close >= tp
    slBroken = close <= sl
    
    status = slBroken ? "SL-BROKE" : tpHit ? "TP-HIT" : breakout ? "FLYING" : nearSetup ? "SETUP" : aboveTrend ? "RUNNING" : "WAIT"
    
    // US SWING LOGIC
    bullTrend = close > ema200 and ema20 > ema50
    bearTrend = close < ema200 and ema20 < ema50
    volSpike = rvol > 1.5
    highest20 = ta.highest(high, 20)
    swingBreakout = close > highest20[1] and volSpike
    bullAbsorb = lowerWick > body * 1.5 and volSpike and close > open
    bearAbsorb = upperWick > body * 1.5 and volSpike and close < open
    
    swingSignal = swingBreakout and bullTrend ? "BREAKOUT BUY" : bullAbsorb and bullTrend ? "BULL ABSORB" : bearAbsorb and bearTrend ? "BEAR ABSORB" : bearTrend and volSpike and close < open ? "DISTRIBUTION" : "WAIT"
    
    // US BANDAR LOGIC
    sniperBuy = (close > ema200) and volSpike and (close > open)
    sniperSell = (close < ema200) and volSpike and (close < open)
    bBullAbsorb = lowerWick > body * 1.1 and rvol > 1.3 and close > low + (candleRange * 0.4)
    bBearAbsorb = upperWick > body * 1.1 and rvol > 1.3 and close < high - (candleRange * 0.4)
    bandarSignal = sniperBuy ? "SNIPER BUY" : sniperSell ? "SNIPER SELL" : bBullAbsorb ? "BULL ABSORB" : bBearAbsorb ? "BEAR ABSORB" : "WAIT"
    
    signal = strategy_mode == "SWING" ? swingSignal : strategy_mode == "BANDAR" ? bandarSignal : distAwal ? "DIST-AWAL" : score >= 85 and bigAccum ? "AKUMULASI" : score >= 75 and close < entry and zona != "MAHAL" ? "BOW-SIAP" : score >= 65 ? "SETUP-OK" : score >= 45 ? "NETRAL" : "WEAK"
    
    action = distAwal ? "WASPADA" : close >= entry ? "SL>" + str.tostring(sl, format.mintick) : score >= 75 ? "BUY>" + str.tostring(entry, format.mintick) : "WAIT"
    
    [close, support, resistance, entry, tp, sl, pctTp, profitPct, status, zona, rsiVal, srsiState, macdState, rvolPct, valueBar, bandarState, action, score, signal]
"""

def generate_us_script(strategy_type, tickers, batch_label, stocks_map, exchange_map, date_str):
    n = len(tickers)
    tf = "15" if strategy_type == "SWING" else "10"
    title = f"US SWING v2" if strategy_type == "SWING" else f"US BANDAR v2"
    
    ticker_lines = []
    for i, t in enumerate(tickers):
        price = stocks_map.get(t, 0)
        exch = exchange_map.get(t, "NASDAQ")
        ticker_lines.append(f'tk{i+1} = "{exch}:{t}"  // ~${price:.2f}')
    
    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(
            f'[now{idx}, sup{idx}, rst{idx}, entry{idx}, tp_{idx}, sl_{idx}, pctTp{idx}, profit{idx}, status{idx}, zona{idx}, rsi{idx}, srsi{idx}, macd{idx}, rvolPct{idx}, valueBar{idx}, bandar{idx}, action{idx}, score{idx}, signal{idx}] = request.security(tk{idx}, tf, f_dashboard_engine("{strategy_type}"))'
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
    f_cell(tbl, 6, {row}, str.tostring(tp_{idx}, format.mintick), cDark, color.lime)
    f_cell(tbl, 7, {row}, str.tostring(sl_{idx}, format.mintick), cDark, color.orange)
    f_cell(tbl, 8, {row}, str.tostring(pctTp{idx}, "#.##") + "%", pctTp{idx} >= 0 ? cGreen : cRed, color.white)
    f_cell(tbl, 9, {row}, str.tostring(profit{idx}, "#.##") + "%", profit{idx} >= 0 ? cGreen : cRed, color.white)
    f_cell(tbl, 10, {row}, status{idx}, f_status_color(status{idx}), color.white)
    f_cell(tbl, 11, {row}, zona{idx}, f_zona_color(zona{idx}), color.white)
    f_cell(tbl, 12, {row}, str.tostring(rsi{idx}, "#.0"), rsi{idx} < 30 ? cRed : rsi{idx} > 70 ? cOrange : cBlue, color.white)
    f_cell(tbl, 13, {row}, srsi{idx}, srsi{idx} == "UP+" or srsi{idx} == "UP" ? cGreen : cRed, color.white)
    f_cell(tbl, 14, {row}, macd{idx}, f_macd_color(macd{idx}), color.white)
    f_cell(tbl, 15, {row}, str.tostring(rvolPct{idx}, "#.0") + "%", rvolPct{idx} >= 150 ? cGreen : cDark, color.white)
    f_cell(tbl, 16, {row}, f_value_idr(valueBar{idx}), valueBar{idx} >= min_tv ? cGreen : cDark, color.white)
    f_cell(tbl, 17, {row}, bandar{idx}, f_signal_color(bandar{idx}), color.white)
    f_cell(tbl, 18, {row}, action{idx}, action{idx} == "WASPADA" ? cOrange : cGreen, color.white)
    f_cell(tbl, 19, {row}, str.tostring(score{idx}, "#"), f_score_color(score{idx}), color.white)
    f_cell(tbl, 20, {row}, signal{idx}, f_signal_color(signal{idx}), color.white)'''
        row_chunks.append(row_str)

    headers = '''    f_header(tbl, 0, "TICKER")
    f_header(tbl, 1, "TF")
    f_header(tbl, 2, "SUP")
    f_header(tbl, 3, "RST")
    f_header(tbl, 4, "ENTRY")
    f_header(tbl, 5, "NOW")
    f_header(tbl, 6, "TP")
    f_header(tbl, 7, "SL")
    f_header(tbl, 8, "%TP")
    f_header(tbl, 9, "PROFIT")
    f_header(tbl, 10, "STATUS")
    f_header(tbl, 11, "ZONA")
    f_header(tbl, 12, "RSI")
    f_header(tbl, 13, "sRSI")
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
        
        if strategy_type == "SWING":
            alert_lines.append(f'''    if signal{idx} != "WAIT" and valueBar{idx} >= min_tv
        msg_{idx} = "🚨 US SWING HUNTER\\nTicker: {t}\\nPrice: $" + str.tostring(now{idx}, "#.##") + "\\nSignal: " + signal{idx} + "\\nRSI: " + str.tostring(rsi{idx}, "#.#")
        alert(msg_{idx}, alert.freq_once_per_bar_close)''')
        else:
            alert_lines.append(f'''    if signal{idx} != "WAIT" and valueBar{idx} >= min_tv
        msg_{idx} = "🔥 US BANDAR AI\\nTicker: {t}\\nPrice: $" + str.tostring(now{idx}, "#.##") + "\\nSignal: " + signal{idx} + "\\nFlow: " + bandar{idx} + "\\nStrength: " + str.tostring(score{idx}, "#.#") + "%"
        alert(msg_{idx}, alert.freq_once_per_bar_close)''')

    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Generated on {date_str} | Strategy: {title}
//@version=6
indicator("{title} - BATCH {batch_label} ({n} Tickers)", overlay=true, max_bars_back=500)

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
// ALERTS
// ============================================================================
if barstate.islast and barstate.isconfirmed
{chr(10).join(alert_lines)}

plot(close, display=display.none)
'''
    return script

if __name__ == "__main__":
    with open(os.path.join(SCRIPT_DIR, "us_penny_stocks.json"), "r") as f:
        data = json.load(f)

    stocks_map = {s["ticker"]: s["price"] for s in data["stocks"]}
    exchange_map = {s["ticker"]: _exchange_prefix(s["exchange"]) for s in data["stocks"]}
    date_str = data["date"]

    print(f"=== US GOTRADE SCREENER GENERATOR v2 ===")

    swing_count = 0
    for batch_key, tickers in data["batch_groups"].items():
        label = batch_key.split("_")[1].upper()
        filename = f"us_swing_batch_{label.lower()}.pine"
        filepath = os.path.join(SCRIPT_DIR, filename)
        script = generate_us_script("SWING", tickers, label, stocks_map, exchange_map, date_str)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)
        swing_count += 1
        print(f"  [US SWING v2]  Batch {label} -> {len(tickers)} tickers")

    bandar_count = 0
    for batch_key, tickers in data["batch_groups"].items():
        label = batch_key.split("_")[1].upper()
        filename = f"us_bandar_ai_batch_{label.lower()}.pine"
        filepath = os.path.join(SCRIPT_DIR, filename)
        script = generate_us_script("BANDAR", tickers, label, stocks_map, exchange_map, date_str)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)
        bandar_count += 1
        print(f"  [US BANDAR v2] Batch {label} -> {len(tickers)} tickers")

    total = swing_count + bandar_count
    print(f"\n[DONE] Generated {total} Pine Script files ({swing_count} Swing + {bandar_count} Bandar AI)")
