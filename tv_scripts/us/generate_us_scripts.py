"""
Auto-generate Pine Script v6 screener scripts for US Stocks (GoTrade).
Two strategies:
  1. US SWING  — EMA Trend + Breakout + RSI swing hunting (TF: 15 min)
  2. US BANDAR AI — Institutional accumulation/distribution detection (TF: 10 min)

Adapted from IDX bandar_ai and swing pipelines for US market.
v2: Daily CHG% fix, 5-col compact table, trend-aware signals, STR% gradient.
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _exchange_prefix(exchange: str) -> str:
    return {"NASDAQ": "NASDAQ", "NYSE": "NYSE", "AMEX": "AMEX"}.get(exchange, "NASDAQ")


# ============================================================================
# US SWING HUNTER GENERATOR v2 — Daily CHG%, Compact 5-Col Table
# ============================================================================
def generate_us_swing_script(tickers, batch_label, stocks_map, exchange_map, date_str):
    n = len(tickers)

    ticker_lines = []
    for i, t in enumerate(tickers):
        price = stocks_map.get(t, 0)
        exch = exchange_map.get(t, "NASDAQ")
        ticker_lines.append(f'tk{i+1} = "{exch}:{t}"  // ~${price:.2f}')

    # Engine security calls (8 return values including chgPct)
    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(
            f'[c{idx}, sig{idx}, rsi{idx}, ema20_{idx}, ema50_{idx}, rvol{idx}, dvol{idx}, chg{idx}] = request.security(tk{idx}, tf, f_swing_engine(emaLen, volMult))'
        )

    # Compact 5-column table rows
    row_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        row = i + 1
        row_lines.append(f'''    table.cell(tbl, 0, {row}, "{t}", text_color=color.yellow, bgcolor=#0d1117, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 1, {row}, "$" + str.tostring(c{idx}, "#.##") + " (" + str.tostring(chg{idx}, "#.##") + "%)", text_color=chg{idx} > 0 ? color.lime : color.red, bgcolor=#0d1117, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 2, {row}, dvol{idx} > 1e6 ? "$" + str.tostring(dvol{idx}/1e6, "#.#") + "M" : "$" + str.tostring(dvol{idx}/1e3, "#.#") + "K", text_color=dvol{idx} > 5e6 ? color.lime : color.white, bgcolor=#0d1117, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 3, {row}, "R:" + str.tostring(rsi{idx}, "#.#") + " V:" + str.tostring(rvol{idx}, "#.#") + "x", text_color=rsi{idx} < 30 ? color.lime : rsi{idx} > 70 ? color.red : color.white, bgcolor=#0d1117, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 4, {row}, sig{idx}, text_color=color.black, bgcolor=f_sig_bg(sig{idx}, c{idx} > ema20_{idx} and ema20_{idx} > ema50_{idx}, c{idx} < ema20_{idx} and ema20_{idx} < ema50_{idx}), text_size=size.small, text_halign=text.align_center)''')

    # Alert lines (human-readable text)
    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        alert_lines.append(f'''    if sig{idx} != "WAIT"
        msg_{idx} = "🚨 US SWING HUNTER\\nTicker: {t}\\nPrice: $" + str.tostring(c{idx}, "#.##") + " (" + str.tostring(chg{idx}, "#.##") + "%)\\nSignal: " + sig{idx} + "\\nRSI: " + str.tostring(rsi{idx}, "#.#") + " | R.Vol: " + str.tostring(rvol{idx}, "#.#") + "x"
        alert(msg_{idx}, alert.freq_once_per_bar_close)''')

    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// https://mozilla.org/MPL/2.0/
// Generated on {date_str} | Strategy: US SWING HUNTER v2
//
// @description US Stock swing trading screener for GoTrade users.
//   Default Timeframe: 15 menit. Holding period: 2-10 hari (swing).
//   Strategi: EMA 20/50 Trend + 20-bar Breakout + Volume Spike + RSI.
//   CHG% dihitung dari Daily Close secara organik (ta.change) agar sinkron dengan GoTrade.
//   Sinyal: BREAKOUT BUY, BULL ABSORB, DISTRIBUTION, BEAR ABSORB.
//   ⚠️ PDT Rule: Max 3 day trades per 5 hari jika account < $25K.

//@version=6
indicator("US SWING HUNTER v2 - BATCH {batch_label} ({n} Tickers)", overlay=true, max_bars_back=500)

// ============================================================================
// INPUT
// ============================================================================
tf         = input.timeframe("15", "Timeframe Screener")
emaLen     = input.int(200, "EMA Trend Length")
volMult    = input.float(1.5, "Vol Spike Multiplier")
pos        = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

// ============================================================================
// TICKER DEFINITIONS (prices as of {date_str})
// ============================================================================
{chr(10).join(ticker_lines)}

// ============================================================================
// CORE SWING ENGINE FUNCTION (8 return values)
// ============================================================================
f_swing_engine(ema_len, vol_mult) =>
    // Tangkap Harga Penutupan Harian (Daily Close) secara organik
    var float prevDailyClose = na
    if ta.change(time("D")) != 0
        prevDailyClose := close[1]

    baseClose = na(prevDailyClose) ? close[1] : prevDailyClose
    chgPct = baseClose > 0 ? (close - baseClose) / baseClose * 100 : 0.0

    ema20  = ta.ema(close, 20)
    ema50  = ta.ema(close, 50)
    emaSlow = ta.ema(close, ema_len)

    bullTrend = close > emaSlow and ema20 > ema50
    bearTrend = close < emaSlow and ema20 < ema50

    volMA = ta.sma(volume, 20)
    volSpike = volume > volMA * vol_mult
    rvol = volMA > 0 ? volume / volMA : 0.0
    dollarVol = volume * close

    rsi = ta.rsi(close, 14)

    highest20 = ta.highest(high, 20)
    breakout = close > highest20[1] and volSpike

    body = math.abs(close - open)
    lowerWick = math.min(open, close) - low
    upperWick = high - math.max(open, close)

    bullAbsorb = lowerWick > body * 1.5 and volSpike and close > open
    bearAbsorb = upperWick > body * 1.5 and volSpike and close < open

    status = breakout and bullTrend ? "BREAKOUT BUY" :
             bullAbsorb and bullTrend ? "BULL ABSORB" :
             bearAbsorb and bearTrend ? "BEAR ABSORB" :
             bearTrend and volSpike and close < open ? "DISTRIBUTION" : "WAIT"

    [close, status, rsi, ema20, ema50, rvol, dollarVol, chgPct]

// ============================================================================
// DATA FETCH — Engine (10 calls total, limit: 40) ✓
// ============================================================================
{chr(10).join(security_lines)}

// ============================================================================
// TABLE DISPLAY (Compact 5-Column Layout)
// ============================================================================
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_left : pos == "Bottom Right" ? position.bottom_right : position.bottom_left
var tbl = table.new(tbl_pos, 5, {n + 1}, border_width=1, border_color=#30363d)

// Trend-aware signal background color
f_sig_bg(sig, isBull, isBear) =>
    sig == "BREAKOUT BUY" ? color.lime : sig == "BULL ABSORB" ? color.aqua : sig == "BEAR ABSORB" ? color.orange : sig == "DISTRIBUTION" ? color.red : isBull ? #1a3a1a : isBear ? #3a1a1a : color.gray

if barstate.islast
    hdr_bg = #8b5cf6
    hdr_clr = color.white
    table.cell(tbl, 0, 0, "TICKER", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 1, 0, "PRICE", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 2, 0, "$VOL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 3, 0, "MOMENTUM", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 4, 0, "SIGNAL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)

if barstate.islast
{chr(10).join(row_lines)}

// ============================================================================
// ALERTS — Human-readable text
// ============================================================================
if barstate.islast and barstate.isconfirmed
{chr(10).join(alert_lines)}

plot(close, display=display.none)
'''
    return script


# ============================================================================
# US BANDAR AI GENERATOR v2 — STR% Gradient Coloring
# ============================================================================
def generate_us_bandar_ai_script(tickers, batch_label, stocks_map, exchange_map, date_str):
    n = len(tickers)

    ticker_lines = []
    for i, t in enumerate(tickers):
        price = stocks_map.get(t, 0)
        exch = exchange_map.get(t, "NASDAQ")
        ticker_lines.append(f'tk{i+1} = "{exch}:{t}"  // ~${price:.2f}')

    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(
            f'[c{idx}, st{idx}, fl{idx}, str{idx}] = request.security(tk{idx}, tf, f_engine(emaSlowLen, volMultiplier))'
        )

    # Table rows with gradient STR%
    row_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        row = i + 1
        row_lines.append(f'''    table.cell(tbl, 0, {row}, "{t}", text_color=color.yellow, bgcolor=#1a1a2e, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 1, {row}, str.tostring(c{idx}, "#.##"), text_color=color.white, bgcolor=#1a1a2e, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 2, {row}, fl{idx}, text_color=color.black, bgcolor=fl{idx} == "BIG ACCUM" ? color.fuchsia : fl{idx} == "ACCUM" ? color.lime : fl{idx} == "DISTRIB" ? color.orange : fl{idx} == "BIG DISTRIB" ? color.red : color.gray, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 3, {row}, str.tostring(str{idx}, "#.#") + "%", text_color=color.black, bgcolor=f_str_gradient(str{idx}), text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 4, {row}, st{idx}, text_color=color.black, bgcolor=f_get_color(st{idx}), text_size=size.small, text_halign=text.align_center)''')

    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        alert_lines.append(f'''    if st{idx} != "WAIT"
        msg_{idx} = "🔥 US BANDAR AI\\nTicker: {t}\\nPrice: $" + str.tostring(c{idx}, "#.##") + "\\nSignal: " + st{idx} + "\\nFlow: " + fl{idx} + "\\nStrength: " + str.tostring(str{idx}, "#.#") + "%"
        alert(msg_{idx}, alert.freq_once_per_bar_close)''')

    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// https://mozilla.org/MPL/2.0/
// Generated on {date_str} | Strategy: US BANDAR AI v2 (Smart Money Flow)
//
// @description US Stock Bandar AI screener for GoTrade users.
//   Default Timeframe: 10 menit. Holding period: hari-minggu (swing).
//   Strategi: EMA 200 Trend + Volume Spike + Candle Absorption Pattern.
//   Sinyal: SNIPER BUY (bullish trend + vol spike), BULL ABSORB (lower wick absorption),
//           SNIPER SELL (bearish trend + vol spike), BEAR ABSORB (upper wick absorption).
//   Deteksi akumulasi/distribusi institusi (smart money flow).
//   Signal Strength: 0-100% dengan gradient visual 5-level.
//   ⚠️ PDT Rule: Max 3 day trades per 5 hari jika account < $25K.

//@version=6
indicator("US BANDAR AI v2 - BATCH {batch_label} ({n} Tickers)", overlay=true, max_bars_back=500)

// ============================================================================
// INPUT
// ============================================================================
tf             = input.timeframe("10", "Timeframe Screener")
emaSlowLen     = input.int(200, "EMA Trend")
volMultiplier  = input.float(1.5, "Vol Spike Multiplier")
pos            = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

// ============================================================================
// TICKER DEFINITIONS (prices as of {date_str})
// ============================================================================
{chr(10).join(ticker_lines)}

// ============================================================================
// CORE ENGINE FUNCTION (Bandar AI Detection)
// ============================================================================
f_engine(ema_len, vol_mult) =>
    emaSlow = ta.ema(close, ema_len)
    bullTrend = close > emaSlow
    bearTrend = close < emaSlow

    volMA = ta.sma(volume, 20)
    volSpike = volume > volMA * vol_mult

    body = math.abs(close - open)
    candleRange = high - low
    lowerWick = math.min(open, close) - low
    upperWick = high - math.max(open, close)

    bullAbsorb = lowerWick > body * 1.1 and volume > volMA * 1.3 and close > low + (candleRange * 0.4)
    bearAbsorb = upperWick > body * 1.1 and volume > volMA * 1.3 and close < high - (candleRange * 0.4)

    sniperBuy = bullTrend and volSpike and (close > open)
    sniperSell = bearTrend and volSpike and (close < open)

    // Money Flow Detection
    flow = volume > volMA * 3 and close >= open ? "BIG ACCUM" :
           volume > volMA * 1.5 and close >= open ? "ACCUM" :
           volume > volMA * 3 and close < open ? "BIG DISTRIB" :
           volume > volMA * 1.5 and close < open ? "DISTRIB" : "NORMAL"

    // Perbaikan Signal Strength (0-100)
    rsi = ta.rsi(close, 14)

    // Base scores
    trendStr = bullTrend ? 25.0 : bearTrend ? -25.0 : 0.0
    rsiStr = rsi < 30 ? 15.0 : rsi > 70 ? -15.0 : 0.0

    // Volume multiplier (0 to 20 max) berdasarkan arah flow
    volStr = volMA > 0 ? math.min(volume / volMA * 10, 20) : 0
    volImpact = (flow == "BIG ACCUM" or flow == "ACCUM") ? volStr : (flow == "BIG DISTRIB" or flow == "DISTRIB") ? -volStr : 0

    // Kalkulasi final: Base 50 + Trend(±25) + RSI(±15) + Vol(±20) = Max 110 (di-cap 100)
    strength = math.max(0, math.min(100, 50 + trendStr + rsiStr + volImpact))

    status = sniperBuy ? "SNIPER BUY" : sniperSell ? "SNIPER SELL" : bullAbsorb ? "BULL ABSORB" : bearAbsorb ? "BEAR ABSORB" : "WAIT"
    [close, status, flow, strength]

// ============================================================================
// DATA FETCH (request.security) — 10 calls (limit: 40) ✓
// ============================================================================
{chr(10).join(security_lines)}

// ============================================================================
// TABLE DISPLAY
// ============================================================================
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_left : pos == "Bottom Right" ? position.bottom_right : position.bottom_left
var tbl = table.new(tbl_pos, 5, {n + 1}, border_width=1, border_color=#333333)

f_get_color(st) =>
    st == "SNIPER BUY" ? color.lime : st == "SNIPER SELL" ? color.red : st == "BULL ABSORB" ? color.aqua : st == "BEAR ABSORB" ? color.orange : color.gray

// 5-level gradient for Signal Strength
f_str_gradient(val) =>
    val > 80 ? #00ff00 : val > 60 ? #66ff66 : val > 40 ? #ffff00 : val > 20 ? #ff6666 : #ff0000

if barstate.islast
    hdr_bg = #6a0dad
    hdr_clr = color.white
    table.cell(tbl, 0, 0, "TICKER", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 1, 0, "PRICE", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 2, 0, "FLOW", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 3, 0, "STR%", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)
    table.cell(tbl, 4, 0, "SIGNAL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small, text_halign=text.align_center)

if barstate.islast
{chr(10).join(row_lines)}

// ============================================================================
// ALERTS — Human-readable text
// ============================================================================
if barstate.islast and barstate.isconfirmed
{chr(10).join(alert_lines)}

plot(close, display=display.none)
'''
    return script


# ============================================================================
# MAIN — Generate all US scripts (SWING + BANDAR AI only, no scalping)
# ============================================================================
if __name__ == "__main__":
    with open(os.path.join(SCRIPT_DIR, "us_penny_stocks.json"), "r") as f:
        data = json.load(f)

    stocks_map = {s["ticker"]: s["price"] for s in data["stocks"]}
    exchange_map = {s["ticker"]: _exchange_prefix(s["exchange"]) for s in data["stocks"]}
    date_str = data["date"]

    print(f"=== US GOTRADE SCREENER GENERATOR v2 ===")
    print(f"Date: {date_str} | Total: {data['total']} tickers")
    print(f"Strategies: SWING v2 (TF 15m) + BANDAR AI v2 (TF 10m)\n")

    # --- Clean old scalp files ---
    import glob
    old_scalp = glob.glob(os.path.join(SCRIPT_DIR, "us_scalp_*.pine"))
    for f_path in old_scalp:
        os.remove(f_path)
        print(f"  [DELETED] {os.path.basename(f_path)}")
    if old_scalp:
        print()

    # --- 1. US SWING HUNTER v2 ---
    swing_count = 0
    for batch_key, tickers in data["batch_groups"].items():
        label = batch_key.split("_")[1].upper()
        filename = f"us_swing_batch_{label.lower()}.pine"
        filepath = os.path.join(SCRIPT_DIR, filename)
        script = generate_us_swing_script(tickers, label, stocks_map, exchange_map, date_str)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)
        swing_count += 1
        print(f"  [US SWING v2]  Batch {label} -> {len(tickers)} tickers ({len(script):,} chars) | 10 security calls")

    # --- 2. US BANDAR AI v2 ---
    bandar_count = 0
    for batch_key, tickers in data["batch_groups"].items():
        label = batch_key.split("_")[1].upper()
        filename = f"us_bandar_ai_batch_{label.lower()}.pine"
        filepath = os.path.join(SCRIPT_DIR, filename)
        script = generate_us_bandar_ai_script(tickers, label, stocks_map, exchange_map, date_str)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)
        bandar_count += 1
        print(f"  [US BANDAR v2] Batch {label} -> {len(tickers)} tickers ({len(script):,} chars) | 10 security calls")

    total = swing_count + bandar_count
    print(f"\n[DONE] Generated {total} Pine Script files ({swing_count} Swing + {bandar_count} Bandar AI)")
    print(f"  US Swing v2:   {data['total']} tickers, TF=15min,  {swing_count} batches, 10 req/batch")
    print(f"  US Bandar v2:  {data['total']} tickers, TF=10min,  {bandar_count} batches, 10 req/batch")
    print(f"  Upgrades:      Daily CHG%, 5-col compact table, STR% gradient")
    print(f"Files saved to: {SCRIPT_DIR}")
