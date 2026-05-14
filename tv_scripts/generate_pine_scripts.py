"""
Auto-generate Pine Script v6 screener scripts for 2 strategies:
  1. SCALPING  — from scalping_stocks.json  (TF: 5 min, saham murah Rp50-500)
  2. BANDAR AI — from bandar_ai_stocks.json (TF: 15 min, mid-cap + blue chip)
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================================
# SCALPING GENERATOR
# ============================================================================
def generate_scalping_script(tickers, batch_label, stocks_map, date_str):
    """Generate Pine Script v6 scalping screener for a batch of tickers."""
    n = len(tickers)
    
    ticker_lines = []
    for i, t in enumerate(tickers):
        price = stocks_map.get(t, 0)
        ticker_lines.append(f'tk{i+1} = "IDX:{t}"  // ~Rp{price:.0f}')
    
    security_lines = []
    for i in range(n):
        security_lines.append(
            f'[c{i+1}, h{i+1}, l{i+1}, v{i+1}, o{i+1}] = request.security(tk{i+1}, tf, [close, high, low, volume, open])'
        )
    
    calc_lines = []
    for i in range(n):
        idx = i + 1
        calc_lines.append(f'''// --- {tickers[i]} ---
pv{idx} = (h{idx}[1] + l{idx}[1] + c{idx}[1]) / 3
atr{idx} = ta.atr(14)
entry{idx} = math.round(2 * pv{idx} - h{idx}[1])
tp{idx}    = math.round(entry{idx} * 1.03)
sl{idx}    = math.round(entry{idx} - atr{idx} * 0.5)
pft{idx}   = entry{idx} > 0 ? (c{idx} - entry{idx}) / entry{idx} * 100 : 0
rsi{idx}   = ta.rsi(c{idx}, 14)
avgv{idx}  = ta.sma(v{idx}, 20)
rvol{idx}  = avgv{idx} > 0 ? v{idx} / avgv{idx} : 0
val{idx}   = v{idx} * c{idx}
bb_b{idx}  = ta.sma(c{idx}, 20)
bb_d{idx}  = 2 * ta.stdev(c{idx}, 20)
zona{idx}  = c{idx} <= bb_b{idx} - bb_d{idx} ? "MURAH" : c{idx} >= bb_b{idx} + bb_d{idx} ? "MAHAL" : "MID"
st{idx}    = c{idx} <= entry{idx} and rsi{idx} < 35 and rvol{idx} > 1.5 ? "FRESH BUY" : c{idx} >= tp{idx} ? "PROFIT (>3%)" : c{idx} > entry{idx} ? "RUNNING" : "WAIT"
bd{idx}    = v{idx} > avgv{idx} * 3 and c{idx} >= o{idx} ? "BIG ACCUM" : v{idx} > avgv{idx} * 1.5 and c{idx} >= o{idx} ? "ACCUM" : "NORMAL"
act{idx}   = st{idx} == "FRESH BUY" and bd{idx} != "NORMAL" ? "HAKA" : (st{idx} == "RUNNING" or st{idx} == "PROFIT (>3%)") ? (rsi{idx} > 80 ? "SELL" : "HOLD") : zona{idx} == "MAHAL" ? "SKIP" : "WAIT"

st_c{idx}  = st{idx} == "FRESH BUY" ? color.lime : st{idx} == "PROFIT (>3%)" ? color.fuchsia : st{idx} == "RUNNING" ? color.yellow : color.gray
zn_c{idx}  = zona{idx} == "MURAH" ? color.lime : zona{idx} == "MAHAL" ? color.red : color.yellow
rs_c{idx}  = rsi{idx} < 30 ? color.lime : rsi{idx} > 70 ? color.red : color.white
bd_c{idx}  = bd{idx} == "BIG ACCUM" ? color.fuchsia : bd{idx} == "ACCUM" ? color.lime : color.gray
ac_c{idx}  = act{idx} == "HAKA" ? color.lime : act{idx} == "SELL" ? color.red : act{idx} == "HOLD" ? color.yellow : act{idx} == "SKIP" ? color.red : color.gray
rv_c{idx}  = rvol{idx} > 2 ? color.lime : rvol{idx} > 1 ? color.yellow : color.gray''')
    
    row_chunks = []
    current_chunk = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        row = i + 1
        if i > 0 and i % 10 == 0:
            row_chunks.append(chr(10).join(current_chunk))
            current_chunk = []
        current_chunk.append(f'''    // Row {row}: {t}
    row{idx} = {row}
    table.cell(tbl, 0, row{idx}, "{t}", text_color=color.yellow, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 1, row{idx}, tf, text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 2, row{idx}, str.tostring(entry{idx}, "#"), text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 3, row{idx}, str.tostring(c{idx}, "#"), text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 4, row{idx}, str.tostring(tp{idx}, "#"), text_color=color.lime, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 5, row{idx}, str.tostring(sl{idx}, "#"), text_color=color.red, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 6, row{idx}, str.tostring(pft{idx}, "#.##") + "%", text_color=pft{idx} > 0 ? color.lime : color.red, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 7, row{idx}, st{idx}, text_color=color.black, bgcolor=st_c{idx}, text_size=size.small)
    table.cell(tbl, 8, row{idx}, zona{idx}, text_color=color.black, bgcolor=zn_c{idx}, text_size=size.small)
    table.cell(tbl, 9, row{idx}, str.tostring(rsi{idx}, "#.#"), text_color=rs_c{idx}, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 10, row{idx}, str.tostring(rvol{idx}, "#.##"), text_color=rv_c{idx}, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 11, row{idx}, val{idx} > 1e9 ? str.tostring(val{idx}/1e9, "#.#") + "B" : str.tostring(val{idx}/1e6, "#.#") + "M", text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 12, row{idx}, bd{idx}, text_color=color.black, bgcolor=bd_c{idx}, text_size=size.small)
    table.cell(tbl, 13, row{idx}, act{idx}, text_color=color.black, bgcolor=ac_c{idx}, text_size=size.small)''')
    if current_chunk:
        row_chunks.append(chr(10).join(current_chunk))
    formatted_rows = chr(10).join([f"if barstate.islast\n{chunk}" for chunk in row_chunks])
    
    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        alert_lines.append(f'''    if st{idx} == "FRESH BUY" and act{idx} == "HAKA"
        alert('{{"type":"SCALP","batch":"{batch_label}","ticker":"{t}","tf":"' + tf + '","signal":"FRESH_BUY","entry":' + str.tostring(entry{idx}) + ',"tp":' + str.tostring(tp{idx}) + ',"sl":' + str.tostring(sl{idx}) + ',"rsi":' + str.tostring(rsi{idx}, "#.#") + ',"rvol":' + str.tostring(rvol{idx}, "#.##") + ',"zona":"' + zona{idx} + '","bandar":"' + bd{idx} + '","action":"HAKA","time":' + str.tostring(time) + '}}', alert.freq_once_per_bar)''')
    
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// https://mozilla.org/MPL/2.0/
// Generated on {date_str} | Strategy: SCALPING (Intraday)
//
// @description Scalping screener untuk saham IDX murah (Rp50-500).
//   Default Timeframe: 1 menit. Holding period: menit-jam (intraday).
//   Strategi: Pivot Entry + RSI Oversold (<35) + Volume Spike (RVOL>1.5).
//   Sinyal HAKA = Entry segera saat semua kondisi terpenuhi + ada akumulasi bandar.
//   TP: +3% dari entry | SL: 0.5x ATR di bawah entry.

//@version=6
indicator("SCALPING SCREENER IDX - BATCH {batch_label} ({n} Emiten)", overlay=true, max_bars_back=500)

// ============================================================================
// INPUT
// ============================================================================
tf = input.timeframe("1", "Timeframe Screener")
pos = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

// ============================================================================
// TICKER DEFINITIONS (harga per {date_str})
// ============================================================================
{chr(10).join(ticker_lines)}

// ============================================================================
// DATA FETCH - request.security with tuple (1 call per emiten)
// ============================================================================
{chr(10).join(security_lines)}

// ============================================================================
// CALCULATIONS
// ============================================================================
{chr(10).join(calc_lines)}

// ============================================================================
// TABLE DISPLAY
// ============================================================================
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_left : pos == "Bottom Right" ? position.bottom_right : position.bottom_left

var tbl = table.new(tbl_pos, 14, {n + 1}, border_width=1, border_color=#333333)

if barstate.islast
    // Header row
    hdr_bg = #ff8c00
    hdr_clr = color.black
    table.cell(tbl, 0, 0, "EMITEN", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 1, 0, "TF", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 2, 0, "ENTRY", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 3, 0, "NOW", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 4, 0, "TP", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 5, 0, "SL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 6, 0, "PROFIT", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 7, 0, "STATUS", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 8, 0, "ZONA", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 9, 0, "RSI", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 10, 0, "RVOL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 11, 0, "VALUE", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 12, 0, "BANDAR", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 13, 0, "ACTION", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)

{formatted_rows}

// ============================================================================
// ALERTS - Webhook JSON payload for each HAKA signal
// ============================================================================
if barstate.islast
{chr(10).join(alert_lines)}

// ============================================================================
// PLOT (hidden, for alert placeholders)
// ============================================================================
plot(close, display=display.none)
'''
    return script


# ============================================================================
# BANDAR AI GENERATOR
# ============================================================================
def generate_bandar_ai_script(tickers, batch_label, stocks_map, date_str):
    """Generate Bandar AI screener for a batch of tickers."""
    n = len(tickers)
    
    ticker_lines = []
    for i, t in enumerate(tickers):
        price = stocks_map.get(t, 0)
        ticker_lines.append(f'tk{i+1} = "IDX:{t}"  // ~Rp{price:.0f}')
        
    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(f'[c{idx}, st{idx}] = request.security(tk{idx}, tf, f_engine(emaSlowLen, volMultiplier))')
        
    row_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        row = i + 1
        row_lines.append(f'''    table.cell(tbl, 0, {row}, "{t}", text_color=color.yellow, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 1, {row}, str.tostring(c{idx}, "#"), text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 2, {row}, st{idx}, text_color=color.black, bgcolor=f_get_color(st{idx}), text_size=size.small)''')
    formatted_rows = chr(10).join(row_lines)
    
    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        alert_lines.append(f'''    if st{idx} != "WAIT"
        alert('{{"type":"BANDAR_AI","batch":"{batch_label}","ticker":"{t}","price":' + str.tostring(c{idx}) + ',"signal":"' + st{idx} + '"}}', alert.freq_once_per_bar_close)''')
        
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// https://mozilla.org/MPL/2.0/
// Generated on {date_str} | Strategy: BANDAR AI (Swing Detection)
//
// @description Bandar AI screener untuk saham IDX mid-cap dan blue chip.
//   Default Timeframe: 10 menit. Holding period: hari-minggu (swing).
//   Strategi: EMA 200 Trend + Volume Spike + Candle Absorption Pattern.
//   Sinyal: SNIPER BUY (bullish trend + vol spike), BULL ABSORB (lower wick absorption),
//           SNIPER SELL (bearish trend + vol spike), BEAR ABSORB (upper wick absorption).
//   Cocok untuk mendeteksi akumulasi/distribusi bandar dan institusi.

//@version=6
indicator("BANDAR AI SCREENER - BATCH {batch_label} ({n} Emiten)", overlay=true, max_bars_back=500)

// ============================================================================
// INPUT
// ============================================================================
tf             = input.timeframe("10", "Timeframe Screener")
emaSlowLen     = input.int(200, "EMA Trend")
volMultiplier  = input.float(1.5, "Vol Spike Multiplier")
pos            = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

// ============================================================================
// TICKER DEFINITIONS (harga per {date_str})
// ============================================================================
{chr(10).join(ticker_lines)}

// ============================================================================
// CORE ENGINE FUNCTION (Dihitung di masing-masing emiten)
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
    
    // Status Text
    status = sniperBuy ? "SNIPER BUY" : sniperSell ? "SNIPER SELL" : bullAbsorb ? "BULL ABSORB" : bearAbsorb ? "BEAR ABSORB" : "WAIT"
    [close, status]

// ============================================================================
// DATA FETCH (request.security)
// ============================================================================
{chr(10).join(security_lines)}

// ============================================================================
// TABLE DISPLAY
// ============================================================================
tbl_pos = pos == "Top Right" ? position.top_right : pos == "Top Left" ? position.top_left : pos == "Bottom Right" ? position.bottom_right : position.bottom_left
var tbl = table.new(tbl_pos, 3, {n + 1}, border_width=1, border_color=#333333)

f_get_color(st) =>
    st == "SNIPER BUY" ? color.lime : st == "SNIPER SELL" ? color.red : st == "BULL ABSORB" ? color.aqua : st == "BEAR ABSORB" ? color.orange : color.gray

if barstate.islast
    // Header
    hdr_bg = #6a0dad
    hdr_clr = color.white
    table.cell(tbl, 0, 0, "EMITEN", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 1, 0, "PRICE", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 2, 0, "SIGNAL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    
{formatted_rows}

// ============================================================================
// ALERTS UNTUK TELEGRAM (JSON PAYLOAD)
// ============================================================================
if barstate.islast and barstate.isconfirmed
{chr(10).join(alert_lines)}

plot(close, display=display.none)
'''
    return script


# ============================================================================
# MAIN — Generate all scripts
# ============================================================================
if __name__ == "__main__":
    # --- 1. SCALPING ---
    with open(os.path.join(SCRIPT_DIR, "scalping_stocks.json"), "r") as f:
        scalp_data = json.load(f)
    scalp_map = {s["ticker"]: s["price"] for s in scalp_data["stocks"]}
    
    scalp_count = 0
    for batch_key, tickers in scalp_data["batch_groups"].items():
        label = batch_key.split("_")[1].upper()
        filename = f"scalping_batch_{label.lower()}.pine"
        filepath = os.path.join(SCRIPT_DIR, filename)
        script = generate_scalping_script(tickers, label, scalp_map, scalp_data["date"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)
        scalp_count += 1
        print(f"  [SCALP]     Batch {label} -> {len(tickers)} emiten ({len(script):,} chars)")
    
    # --- 2. BANDAR AI ---
    with open(os.path.join(SCRIPT_DIR, "bandar_ai_stocks.json"), "r") as f:
        bandar_data = json.load(f)
    bandar_map = {s["ticker"]: s["price"] for s in bandar_data["stocks"]}
    
    bandar_count = 0
    for batch_key, tickers in bandar_data["batch_groups"].items():
        label = batch_key.split("_")[1].upper()
        filename = f"bandar_ai_batch_{label.lower()}.pine"
        filepath = os.path.join(SCRIPT_DIR, filename)
        script = generate_bandar_ai_script(tickers, label, bandar_map, bandar_data["date"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)
        bandar_count += 1
        print(f"  [BANDAR AI] Batch {label} -> {len(tickers)} emiten ({len(script):,} chars)")
    
    total = scalp_count + bandar_count
    print(f"\n[DONE] Generated {total} Pine Script files ({scalp_count} Scalping + {bandar_count} Bandar AI)")
    print(f"  Scalping:  {scalp_data['total']} emiten, TF=5min,  {scalp_count} batches")
    print(f"  Bandar AI: {bandar_data['total']} emiten, TF=15min, {bandar_count} batches")
    print(f"Files saved to: {SCRIPT_DIR}")
