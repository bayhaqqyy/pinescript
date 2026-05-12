"""
Auto-generate Pine Script v6 scalping screener scripts from idx_below_1000.json
Each batch = 40 emiten max, using tuple request.security() for efficiency
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SCRIPT_DIR, "idx_below_1000.json"), "r") as f:
    data = json.load(f)

batch_groups = data["batch_groups"]
stocks_map = {s["ticker"]: s["price"] for s in data["stocks"]}

def generate_pine_script(batch_name, tickers, batch_label):
    """Generate a complete Pine Script v6 for a batch of tickers."""
    n = len(tickers)
    
    # Build ticker declarations
    ticker_lines = []
    for i, t in enumerate(tickers):
        price = stocks_map.get(t, 0)
        ticker_lines.append(f'tk{i+1} = "IDX:{t}"  // ~Rp{price:.0f}')
    
    # Build request.security blocks
    security_lines = []
    for i in range(n):
        security_lines.append(
            f'[c{i+1}, h{i+1}, l{i+1}, v{i+1}, o{i+1}] = request.security(tk{i+1}, tf, [close, high, low, volume, open])'
        )
    
    # Build calculation function calls
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
    
    # Build table row drawing
    row_chunks = []
    current_chunk = []
    
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        row = i + 1  # row 0 = header
        
        # Start a new chunk every 10 items
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
    
    # Build alert lines
    alert_lines = []
    for i in range(n):
        idx = i + 1
        t = tickers[i]
        alert_lines.append(f'''    if st{idx} == "FRESH BUY" and act{idx} == "HAKA"
        alert('{{"type":"SCALP","batch":"{batch_label}","ticker":"{t}","tf":"' + tf + '","signal":"FRESH_BUY","entry":' + str.tostring(entry{idx}) + ',"tp":' + str.tostring(tp{idx}) + ',"sl":' + str.tostring(sl{idx}) + ',"rsi":' + str.tostring(rsi{idx}, "#.#") + ',"rvol":' + str.tostring(rvol{idx}, "#.##") + ',"zona":"' + zona{idx} + '","bandar":"' + bd{idx} + '","action":"HAKA","time":' + str.tostring(time) + '}}', alert.freq_once_per_bar)''')
    
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// https://mozilla.org/MPL/2.0/
// Generated on {data["date"]} from real IDX prices

//@version=6
indicator("SCALPING SCREENER IDX - BATCH {batch_label} ({n} Emiten)", overlay=true, max_bars_back=500)

// ============================================================================
// INPUT
// ============================================================================
tf = input.timeframe("5", "Timeframe Screener")
pos = input.string("Top Right", "Table Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"])

// ============================================================================
// TICKER DEFINITIONS (harga per {data["date"]})
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


# Generate all batch scripts
for batch_key, tickers in batch_groups.items():
    label = batch_key.split("_")[1].upper()
    filename = f"scalping_batch_{label.lower()}.pine"
    filepath = os.path.join(SCRIPT_DIR, filename)
    
    script = generate_pine_script(batch_key, tickers, label)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(script)
    
    print(f"[OK] {filename} - {len(tickers)} emiten ({len(script)} chars)")

print(f"\n[DONE] Generated {len(batch_groups)} Pine Script files")
print("Files saved to:", SCRIPT_DIR)
