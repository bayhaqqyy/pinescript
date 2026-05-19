"""
Auto-generate Pine Script v6 screener scripts for 2 strategies (V2):
  1. SCALPING_V2  — from scalping_stocks.json  (TF: 5 min)
  2. BANDAR_AI_V2 — from bandar_ai_stocks.json (TF: 60 min)
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================================
# SCALPING GENERATOR
# ============================================================================
def generate_scalping_script(tickers, batch_label, stocks_map, date_str):
    """Generate Pine Script v6 scalping screener v2 for a batch of tickers."""
    n = len(tickers)
    
    ticker_lines = []
    for i, t in enumerate(tickers):
        tier = stocks_map.get(t, {}).get("tier", "SCALP_GORENGAN")
        ticker_lines.append(f'tk{i+1} = "IDX:{t}"  // {tier}')
    
    security_lines = []
    for i in range(n):
        security_lines.append(
            f'[c{i+1}, h{i+1}, l{i+1}, v{i+1}, o{i+1}, atr_{i+1}] = request.security(tk{i+1}, tf, [close, high, low, volume, open, ta.atr(14)])'
        )
    
    calc_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        tier = stocks_map.get(t, {}).get("tier", "SCALP_GORENGAN")
        
        calc_lines.append(f'''// --- {t} ---
pv{idx} = (h{idx}[1] + l{idx}[1] + c{idx}[1]) / 3
entry{idx} = math.round(2 * pv{idx} - h{idx}[1])
tv_{idx} = v{idx} * c{idx}

tp1_{idx} = math.round(entry{idx} + (atr_{idx} * tp1_mult))
tp2_{idx} = math.round(entry{idx} + (atr_{idx} * tp2_mult))
sl_{idx}  = math.round(entry{idx} - (atr_{idx} * sl_mult))

rsi{idx}   = ta.rsi(c{idx}, 14)
avgv{idx}  = ta.sma(v{idx}, 20)
rvol{idx}  = avgv{idx} > 0 ? v{idx} / avgv{idx} : 0

// Base signal
sig_base{idx} = (c{idx} <= entry{idx} and rsi{idx} < 35 and rvol{idx} > 1.5) ? "FRESH BUY" : "WAIT"

// Validation Checks
is_atr_valid{idx} = not na(atr_{idx}) and atr_{idx} > 0
is_liq_valid{idx} = tv_{idx} >= min_tv
is_mono_valid{idx} = (tp2_{idx} > tp1_{idx}) and (tp1_{idx} > entry{idx}) and (entry{idx} > sl_{idx})

st{idx} = not is_atr_valid{idx} ? "WAIT_ATR" : not is_liq_valid{idx} ? "WAIT_LIQ" : not is_mono_valid{idx} ? "WAIT_TICK" : sig_base{idx}

st_c{idx}  = st{idx} == "FRESH BUY" ? color.lime : st{idx} == "WAIT_ATR" or st{idx} == "WAIT_LIQ" or st{idx} == "WAIT_TICK" ? color.gray : color.gray
rs_c{idx}  = rsi{idx} < 30 ? color.lime : rsi{idx} > 70 ? color.red : color.white
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
    table.cell(tbl, 4, row{idx}, str.tostring(tp1_{idx}, "#"), text_color=color.lime, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 5, row{idx}, str.tostring(tp2_{idx}, "#"), text_color=color.lime, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 6, row{idx}, str.tostring(sl_{idx}, "#"), text_color=color.red, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 7, row{idx}, st{idx}, text_color=color.black, bgcolor=st_c{idx}, text_size=size.small)
    table.cell(tbl, 8, row{idx}, str.tostring(rsi{idx}, "#.#"), text_color=rs_c{idx}, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 9, row{idx}, str.tostring(rvol{idx}, "#.##"), text_color=rv_c{idx}, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 10, row{idx}, tv_{idx} > 1e9 ? str.tostring(tv_{idx}/1e9, "#.#") + "B" : str.tostring(tv_{idx}/1e6, "#.#") + "M", text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)''')
    if current_chunk:
        row_chunks.append(chr(10).join(current_chunk))
    formatted_rows = chr(10).join([f"if barstate.islast\n{chunk}" for chunk in row_chunks])
    
    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        tier = stocks_map.get(t, {}).get("tier", "SCALP_GORENGAN")
        alert_lines.append(f'''    if st{idx} == "FRESH BUY"
        alert('{{"type":"SCALP","tier":"{tier}","ticker":"{t}","tf":"' + tf + '","signal":"FRESH_BUY","entry":' + str.tostring(entry{idx}) + ',"tp1":' + str.tostring(tp1_{idx}) + ',"tp2":' + str.tostring(tp2_{idx}) + ',"sl":' + str.tostring(sl_{idx}) + ',"holding_hint":"intraday (menit-jam)","transaction_value":' + str.tostring(tv_{idx}) + ',"time":' + str.tostring(time) + '}}', alert.freq_once_per_bar)''')
    
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// https://mozilla.org/MPL/2.0/
// Generated on {date_str} | Strategy: SCALPING_V2 (Intraday)
//
// @description Scalping screener v2 untuk penny stocks.
//   Default Timeframe: 5 menit. Holding period: intraday.

//@version=6
indicator("SCALPING V2 - BATCH {batch_label} ({n} Emiten)", overlay=true, max_bars_back=500)

// ============================================================================
// INPUT
// ============================================================================
tf = input.timeframe("5", "Timeframe Screener")
min_tv = input.float(500000000, "Min Transaction Value per Bar (Rp)")
tp1_mult = input.float(1.0, "TP1 ATR Multiplier")
tp2_mult = input.float(2.0, "TP2 ATR Multiplier")
sl_mult  = input.float(1.0, "SL ATR Multiplier")
pos = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

// ============================================================================
// TICKER DEFINITIONS (harga per {date_str})
// ============================================================================
{chr(10).join(ticker_lines)}

// ============================================================================
// DATA FETCH - request.security
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

var tbl = table.new(tbl_pos, 11, {n + 1}, border_width=1, border_color=#333333)

if barstate.islast
    // Header row
    hdr_bg = #ff8c00
    hdr_clr = color.black
    table.cell(tbl, 0, 0, "EMITEN", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 1, 0, "TF", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 2, 0, "ENTRY", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 3, 0, "NOW", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 4, 0, "TP1", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 5, 0, "TP2", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 6, 0, "SL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 7, 0, "STATUS", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 8, 0, "RSI", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 9, 0, "RVOL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 10, 0, "VALUE", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)

{formatted_rows}

// ============================================================================
// ALERTS - Webhook JSON payload v2
// ============================================================================
if barstate.islast
{chr(10).join(alert_lines)}

// ============================================================================
// PLOT (hidden)
// ============================================================================
plot(close, display=display.none)
'''
    return script


# ============================================================================
# BANDAR AI GENERATOR
# ============================================================================
def generate_bandar_ai_script(tickers, batch_label, stocks_map, date_str):
    """Generate Bandar AI screener v2 for a batch of tickers."""
    n = len(tickers)
    
    ticker_lines = []
    for i, t in enumerate(tickers):
        tier = stocks_map.get(t, {}).get("tier", "BANDAR_SWING")
        ticker_lines.append(f'tk{i+1} = "IDX:{t}"  // {tier}')
        
    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(f'[c{idx}, st_base_{idx}, entry_{idx}, atr_{idx}, tv_{idx}] = request.security(tk{idx}, tf, f_engine(emaSlowLen, volMultiplier))')
        
    calc_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        calc_lines.append(f'''// --- {t} ---
tp1_{idx} = math.round(entry_{idx} + (atr_{idx} * tp1_mult))
tp2_{idx} = math.round(entry_{idx} + (atr_{idx} * tp2_mult))
sl_{idx}  = math.round(entry_{idx} - (atr_{idx} * sl_mult))

is_atr_valid_{idx} = not na(atr_{idx}) and atr_{idx} > 0
is_liq_valid_{idx} = tv_{idx} >= min_tv
is_mono_valid_{idx} = (st_base_{idx} == "SNIPER BUY" or st_base_{idx} == "BULL ABSORB") ? (tp2_{idx} > tp1_{idx} and tp1_{idx} > entry_{idx} and entry_{idx} > sl_{idx}) : true

st_{idx} = not is_atr_valid_{idx} ? "WAIT_ATR" : not is_liq_valid_{idx} ? "WAIT_LIQ" : not is_mono_valid_{idx} ? "WAIT_TICK" : st_base_{idx}
''')

    row_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        row = i + 1
        row_lines.append(f'''    table.cell(tbl, 0, {row}, "{t}", text_color=color.yellow, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 1, {row}, str.tostring(c{idx}, "#"), text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 2, {row}, str.tostring(tv_{idx}/1e6, "#.#") + "M", text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 3, {row}, st_{idx}, text_color=color.black, bgcolor=f_get_color(st_{idx}), text_size=size.small)''')
    formatted_rows = chr(10).join(row_lines)
    
    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        tier = stocks_map.get(t, {}).get("tier", "BANDAR_SWING")
        alert_lines.append(f'''    if st_{idx} == "SNIPER BUY" or st_{idx} == "BULL ABSORB"
        alert('{{"type":"BANDAR_AI","tier":"{tier}","ticker":"{t}","tf":"' + tf + '","signal":"' + st_{idx} + '","entry":' + str.tostring(entry_{idx}) + ',"tp1":' + str.tostring(tp1_{idx}) + ',"tp2":' + str.tostring(tp2_{idx}) + ',"sl":' + str.tostring(sl_{idx}) + ',"holding_hint":"swing 3-7 hari","transaction_value":' + str.tostring(tv_{idx}) + ',"time":' + str.tostring(time) + '}}', alert.freq_once_per_bar_close)''')
        
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// https://mozilla.org/MPL/2.0/
// Generated on {date_str} | Strategy: BANDAR_AI_V2 (Swing Detection)
//
// @description Bandar AI screener v2. Default Timeframe: 60 menit.

//@version=6
indicator("BANDAR AI V2 - BATCH {batch_label} ({n} Emiten)", overlay=true, max_bars_back=500)

// ============================================================================
// INPUT
// ============================================================================
tf             = input.timeframe("60", "Timeframe Screener")
min_tv         = input.float(500000000, "Min Transaction Value per Bar (Rp)")
tp1_mult       = input.float(1.5, "TP1 ATR Multiplier")
tp2_mult       = input.float(3.0, "TP2 ATR Multiplier")
sl_mult        = input.float(1.5, "SL ATR Multiplier")
emaSlowLen     = input.int(200, "EMA Trend")
volMultiplier  = input.float(1.5, "Vol Spike Multiplier")
pos            = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

// ============================================================================
// TICKER DEFINITIONS (harga per {date_str})
// ============================================================================
{chr(10).join(ticker_lines)}

// ============================================================================
// CORE ENGINE FUNCTION
// ============================================================================
f_engine(ema_len, vol_mult) =>
    emaSlow = ta.ema(close, ema_len)
    bullTrend = close > emaSlow
    
    volMA = ta.sma(volume, 20)
    volSpike = volume > volMA * vol_mult
    
    body = math.abs(close - open)
    candleRange = high - low
    lowerWick = math.min(open, close) - low
    
    bullAbsorb = lowerWick > body * 1.1 and volume > volMA * 1.3 and close > low + (candleRange * 0.4)
    sniperBuy = bullTrend and volSpike and (close > open)
    
    status = sniperBuy ? "SNIPER BUY" : bullAbsorb ? "BULL ABSORB" : "WAIT"
    entry_val = close
    atr_val = ta.atr(14)
    tv_val = volume * close
    [close, status, entry_val, atr_val, tv_val]

// ============================================================================
// DATA FETCH (request.security)
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
var tbl = table.new(tbl_pos, 4, {n + 1}, border_width=1, border_color=#333333)

f_get_color(st) =>
    st == "SNIPER BUY" ? color.lime : st == "BULL ABSORB" ? color.aqua : color.gray

if barstate.islast
    // Header
    hdr_bg = #6a0dad
    hdr_clr = color.white
    table.cell(tbl, 0, 0, "EMITEN", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 1, 0, "PRICE", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 2, 0, "DOLVOL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 3, 0, "SIGNAL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    
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
    scalp_map = {s["ticker"]: s for s in scalp_data["stocks"]}
    
    scalp_count = 0
    for batch_key, tickers in scalp_data["batch_groups"].items():
        label = batch_key.split("_")[1].upper()
        filename = f"scalping_v2_batch_{label.lower()}.pine"
        filepath = os.path.join(SCRIPT_DIR, filename)
        script = generate_scalping_script(tickers, label, scalp_map, scalp_data["date"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)
        scalp_count += 1
        print(f"  [SCALP V2]  Batch {label} -> {len(tickers)} emiten ({len(script):,} chars)")
    
    # --- 2. BANDAR AI ---
    with open(os.path.join(SCRIPT_DIR, "bandar_ai_stocks.json"), "r") as f:
        bandar_data = json.load(f)
    bandar_map = {s["ticker"]: s for s in bandar_data["stocks"]}
    
    bandar_count = 0
    for batch_key, tickers in bandar_data["batch_groups"].items():
        label = batch_key.split("_")[1].upper()
        filename = f"bandar_ai_v2_batch_{label.lower()}.pine"
        filepath = os.path.join(SCRIPT_DIR, filename)
        script = generate_bandar_ai_script(tickers, label, bandar_map, bandar_data["date"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)
        bandar_count += 1
        print(f"  [BANDAR V2] Batch {label} -> {len(tickers)} emiten ({len(script):,} chars)")
    
    total = scalp_count + bandar_count
    print(f"\n[DONE] Generated {total} Pine Script V2 files")
    print(f"Files saved to: {SCRIPT_DIR}")
