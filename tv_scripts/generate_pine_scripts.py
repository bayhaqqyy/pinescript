"""
Auto-generate Pine Script v6 screener scripts for 2 strategies (V2):
  1. SCALPING_V2  — from scalping_stocks.json  (TF: 5 min)
  2. BANDAR_AI_V2 — from bandar_ai_stocks.json (TF: 60 min)
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# SCALPING GENERATOR (UPDATED: ANTI-ARB ENGINE)
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
        idx = i + 1
        # Memanggil f_scalp_engine untuk efisiensi komputasi
        security_lines.append(
            f'[c{idx}, st_{idx}, rsi_{idx}, rvol_{idx}, atr_{idx}] = request.security(tk{idx}, tf, f_scalp_engine())'
        )
    
    calc_lines = []
    for i in range(n):
        idx = i + 1
        calc_lines.append(f'''// --- Calculation Ticker {idx} ---
tp1_{idx} = math.round(c{idx} + (atr_{idx} * tp1_mult))
tp2_{idx} = math.round(c{idx} + (atr_{idx} * tp2_mult))
sl_{idx}  = math.round(c{idx} - (atr_{idx} * sl_mult))
tv_{idx}  = volume * c{idx}

st_c{idx} = st_{idx} == "HAKA" ? color.lime : color.gray
rs_c{idx} = rsi_{idx} < 30 ? color.lime : rsi_{idx} > 70 ? color.red : color.white
rv_c{idx} = rvol_{idx} > 2 ? color.lime : rvol_{idx} > 1.5 ? color.yellow : color.gray''')
    
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
    table.cell(tbl, 0, {row}, "{t}", text_color=color.yellow, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 1, {row}, tf, text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 2, {row}, str.tostring(c{idx}, "#"), text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 3, {row}, str.tostring(tp1_{idx}, "#"), text_color=color.lime, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 4, {row}, str.tostring(sl_{idx}, "#"), text_color=color.red, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 5, {row}, st_{idx}, text_color=color.black, bgcolor=st_c{idx}, text_size=size.small)
    table.cell(tbl, 6, {row}, str.tostring(rsi_{idx}, "#.#"), text_color=rs_c{idx}, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 7, {row}, str.tostring(rvol_{idx}, "#.##"), text_color=rv_c{idx}, bgcolor=#1a1a2e, text_size=size.small)''')
    
    if current_chunk:
        row_chunks.append(chr(10).join(current_chunk))
    formatted_rows = chr(10).join([f"if barstate.islast\n{chunk}" for chunk in row_chunks])
    
    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        tier = stocks_map.get(t, {}).get("tier", "SCALP_GORENGAN")
        alert_lines.append(f'''    if st_{idx} == "HAKA" and tv_{idx} >= min_tv
        alert('{{"type":"SCALP","tier":"{tier}","ticker":"{t}","tf":"' + tf + '","signal":"HAKA","entry":' + str.tostring(c{idx}) + ',"tp1":' + str.tostring(tp1_{idx}) + ',"tp2":' + str.tostring(tp2_{idx}) + ',"sl":' + str.tostring(sl_{idx}) + ',"holding_hint":"intraday","time":' + str.tostring(time) + '}}', alert.freq_once_per_bar)''')
    
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Generated on {date_str} | Strategy: SCALPING_V2 (Anti-ARB Engine)
//@version=6
indicator("SCALPING V2 - BATCH {batch_label} ({n} Emiten)", overlay=true, max_bars_back=500)

// ============================================================================
// INPUT
// ============================================================================
tf = input.timeframe("5", "Timeframe Screener")
min_tv = input.float(500000000, "Min Transaction Value per Bar (Rp)")
tp1_mult = input.float(1.0, "TP1 ATR Multiplier")
tp2_mult = input.float(2.0, "TP2 ATR Multiplier")
sl_mult  = input.float(1.5, "SL ATR Multiplier") // SL dilebarkan sedikit untuk volatilitas
pos = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

// ============================================================================
// TICKER DEFINITIONS
// ============================================================================
{chr(10).join(ticker_lines)}

// ============================================================================
// CORE ENGINE FUNCTION (ANTI FALLING KNIFE)
// ============================================================================
f_scalp_engine() =>
    emaFast = ta.ema(close, 5)
    
    // Filter Price Action Ketat
    isGreenCandle = close > open
    isNotARB = close > low
    
    // Analisis Volume & Momentum
    volMA = ta.sma(volume, 20)
    rvol = volMA > 0 ? volume / volMA : 0
    rsiVal = ta.rsi(close, 14)
    
    // Syarat HAKA: Harus hijau, tidak ARB, volume meledak, di atas EMA 5
    validHaka = isGreenCandle and isNotARB and (rvol > 1.5) and (close > emaFast)
    
    status = validHaka ? "HAKA" : "WAIT"
    atr_val = ta.atr(14)
    
    [close, status, rsiVal, rvol, atr_val]

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
var tbl = table.new(tbl_pos, 8, {n + 1}, border_width=1, border_color=#333333)

if barstate.islast
    hdr_bg = #ff8c00
    hdr_clr = color.black
    table.cell(tbl, 0, 0, "EMITEN", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 1, 0, "TF", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 2, 0, "ENTRY", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 3, 0, "TP1", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 4, 0, "SL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 5, 0, "STATUS", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 6, 0, "RSI", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)
    table.cell(tbl, 7, 0, "RVOL", text_color=hdr_clr, bgcolor=hdr_bg, text_size=size.small)

{formatted_rows}

// ============================================================================
// ALERTS - Webhook JSON
// ============================================================================
if barstate.islast and barstate.isconfirmed
{chr(10).join(alert_lines)}

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
        security_lines.append(f'[c{idx}, st_{idx}, atr_{idx}, tv_{idx}] = request.security(tk{idx}, tf, f_engine(emaSlowLen, volMultiplier))')
        
    calc_lines = []
    for i in range(n):
        idx = i + 1
        calc_lines.append(f'''// --- {tickers[i]} ---
tp1_{idx} = math.round(c{idx} + (atr_{idx} * tp1_mult))
tp2_{idx} = math.round(c{idx} + (atr_{idx} * tp2_mult))
sl_{idx}  = math.round(c{idx} - (atr_{idx} * sl_mult))
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
        alert_lines.append(f'''    if (st_{idx} == "SNIPER BUY" or st_{idx} == "BULL ABSORB") and tv_{idx} >= min_tv
        alert('{{"type":"BANDAR_AI","tier":"{tier}","ticker":"{t}","tf":"' + tf + '","signal":"' + st_{idx} + '","entry":' + str.tostring(c{idx}) + ',"tp1":' + str.tostring(tp1_{idx}) + ',"tp2":' + str.tostring(tp2_{idx}) + ',"sl":' + str.tostring(sl_{idx}) + ',"holding_hint":"swing 3-7 hari","time":' + str.tostring(time) + '}}', alert.freq_once_per_bar_close)''')
        
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Generated on {date_str} | Strategy: BANDAR_AI_V2 (Swing Detection)
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
// TICKER DEFINITIONS
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
    atr_val = ta.atr(14)
    tv_val = volume * close
    [close, status, atr_val, tv_val]

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
        print(f"  [SCALP V2]  Batch {label} -> {len(tickers)} emiten")
    
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
        print(f"  [BANDAR V2] Batch {label} -> {len(tickers)} emiten")
    
    total = scalp_count + bandar_count
    print(f"\n[DONE] Generated {total} Pine Script V2 files")