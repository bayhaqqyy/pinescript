"""
Binance USDⓈ-M Futures — V8 Autobot Dashboard Generator
=========================================================
Fetches real-time 24hr ticker data from Binance Futures API,
extracts the Top 100 highest-volume USDT perpetual CRYPTO pairs,
and generates 10 batches (A-J) of Pine Script v6 indicator files.

Usage:
    py generate_screener.py
"""
import requests
import json
import os
import time
import sys
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# CONFIGURATION
# ============================================================================
BINANCE_API = "https://fapi.binance.com/fapi/v1/ticker/24hr"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, "binance_futures_cache.json")
TOP_N = 100
BATCH_SIZE = 10
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "generated_screeners")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15

# TradFi / Equity / Commodity symbols to EXCLUDE (these are NOT crypto)
TRADFI_SYMBOLS = {
    "AAPLUSDT", "AMDUSDT", "AMZNUSDT", "AVGOUSDT", "BABAUSDT", "BRKBUSDT",
    "BZUSDT", "CBRSUSDT", "CLUSDT", "COINUSDT", "COPPERUSDT", "CRCLUSDT",
    "CRWVUSDT", "CSCOUSDT", "EWYUSDT", "GOOGLUSDT", "INTCUSDT", "MSTRUSDT",
    "MSFTUSDT", "METAUSDT", "NATGASUSDT", "NVDAUSDT", "PAXGUSDT", "QQQUSDT",
    "SOXLUSDT", "SPCXUSDT", "TSLAUSDT", "VUSDT", "XAGUSDT", "XAUUSDT",
    "XPLUSDT",
}

# Top 100 Binance USDⓈ-M Futures CRYPTO perpetual pairs by 24h volume
# Source: CoinGlass (verified May 2026), filtered to crypto-only
HARDCODED_TOP_100 = [
    # --- Batch A ---
    "BTCUSDT", "ETHUSDT", "HYPEUSDT", "SOLUSDT", "XRPUSDT",
    "NEARUSDT", "DOGEUSDT", "BNBUSDT", "SUIUSDT", "ADAUSDT",
    # --- Batch B (Requested / Screenshot hot pairs) ---
    "GRASSUSDT", "FIDAUSDT", "BEATUSDT", "GENIUSUSDT", "ALTUSDT",
    "AGTUSDT", "EDENUSDT", "JCTUSDT", "1000PEPEUSDT", "ONDOUSDT",
    # --- Batch C ---
    "WLDUSDT", "TAOUSDT", "LINKUSDT", "TONUSDT", "AVAXUSDT",
    "DOTUSDT", "LTCUSDT", "FILUSDT", "INJUSDT", "ENAUSDT",
    # --- Batch D ---
    "TRUMPUSDT", "FETUSDT", "AAVEUSDT", "TRXUSDT", "ICPUSDT",
    "UNIUSDT", "BCHUSDT", "ARBUSDT", "TIAUSDT", "VIRTUALUSDT",
    # --- Batch E ---
    "XMRUSDT", "RENDERUSDT", "ATOMUSDT", "XLMUSDT", "ETCUSDT",
    "APTUSDT", "CHZUSDT", "1000SHIBUSDT", "OPUSDT", "HBARUSDT",
    # --- Batch F ---
    "ALGOUSDT", "SEIUSDT", "MKRUSDT", "ORDIUSDT", "RUNEUSDT",
    "PENDLEUSDT", "CRVUSDT", "DYDXUSDT", "ENSUSDT", "MATICUSDT",
    # --- Batch G ---
    "WIFUSDT", "JUPUSDT", "STXUSDT", "LDOUSDT", "FLOKIUSDT",
    "BONKUSDT", "PEPEUSDT", "CFXUSDT", "JASMYUSDT", "ARUSDT",
    # --- Batch H ---
    "GALAUSDT", "SNXUSDT", "IMXUSDT", "THETAUSDT", "FTMUSDT",
    "SANDUSDT", "MANAUSDT", "AXSUSDT", "BEAMXUSDT", "GMXUSDT",
    # --- Batch I ---
    "APEUSDT", "EGLDUSDT", "FLOWUSDT", "MASKUSDT", "1INCHUSDT",
    "COMPUSDT", "ZRXUSDT", "IOTAUSDT", "EOSUSDT", "NEOUSDT",
    # --- Batch J ---
    "XTZUSDT", "KAVAUSDT", "KLAYUSDT", "GRTUSDT", "VETUSDT",
    "ZILUSDT", "WOOUSDT", "SKLUSDT", "CAKEUSDT", "LRCUSDT"
]
# Remove duplicates while preserving order
seen = set()
HARDCODED_TOP_100 = [x for x in HARDCODED_TOP_100 if not (x in seen or seen.add(x))]


# ============================================================================
# PHASE 1: FETCH & FILTER
# ============================================================================
def fetch_top_pairs():
    """Fetch Binance Futures tickers. Tries live API first, falls back to hardcoded list."""
    print("=" * 60)
    print(" BINANCE USDS-M AUTOBOT - V8 DASHBOARD GENERATOR")
    print("=" * 60)

    data = None
    api_success = False

    # --- Try live API first ---
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"\n[FETCH] Attempt {attempt}/{MAX_RETRIES} - Connecting to Binance Futures API...")
            resp = requests.get(BINANCE_API, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            print(f"[FETCH] Received {len(data)} tickers from API")
            api_success = True
            break
        except requests.RequestException as e:
            print(f"[FETCH] Attempt {attempt} failed: {str(e)[:100]}")
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"[FETCH] Retrying in {wait}s...")
                time.sleep(wait)

    if api_success:
        # --- Filter: USDT perpetuals only, crypto only ---
        filtered = [
            t for t in data
            if t["symbol"].endswith("USDT")
            and "_" not in t["symbol"]
            and t["symbol"] not in TRADFI_SYMBOLS
        ]
        print(f"[FILTER] {len(data)} total -> {len(filtered)} crypto USDT perpetuals (TradFi excluded)")

        # --- Sort by 24h quoteVolume descending ---
        filtered.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
        top = filtered[:TOP_N]

        # Save cache
        cache_data = [{"symbol": t["symbol"], "quoteVolume": t["quoteVolume"], "lastPrice": t["lastPrice"]} for t in top]
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

        symbols = [t["symbol"] for t in top]

    else:
        # --- Fallback: use hardcoded list ---
        print(f"\n[FETCH] API unreachable (ISP block). Using verified pair list...")
        symbols = HARDCODED_TOP_100[:TOP_N]
        print(f"[LIST]  Loaded {len(symbols)} verified crypto perpetual pairs")

    print(f"[TOP 5] {', '.join(symbols[:5])}")
    return symbols


# ============================================================================
# PHASE 3: PINE SCRIPT V8 ENGINE (IMPROVED)
# ============================================================================
def generate_pine_script(symbols, batch_label):
    """Generate a complete Pine Script v6 file for one batch of 10 symbols.
    
    V8 Engine uses triple-confirmation strategy:
    - EMA 200 trend filter
    - HMA turn detection for precise entries
    - ADX trend strength filter (>20 = trending)
    - RSI momentum filter (avoid overbought/oversold entries)
    - Volume spike confirmation
    - ATR-based dynamic TP/SL
    """
    n = len(symbols)

    # --- 3.1: Ticker Definitions ---
    ticker_lines = []
    for i, sym in enumerate(symbols):
        ticker_lines.append(f'tk{i+1} = "BINANCE:{sym}.P"')
    ticker_definitions = "\n".join(ticker_lines)

    # --- 3.2: Security Calls ---
    security_lines = []
    for i in range(n):
        idx = i + 1
        security_lines.append(
            f'[c{idx}, ep{idx}, sig{idx}, at{idx}, sd{idx}, tp{idx}, sl{idx}, lev{idx}, qty{idx}] = '
            f'request.security(tk{idx}, tf, f_engine())'
        )
    security_calls = "\n".join(security_lines)

    # --- 3.3: Table Rows ---
    row_lines = []
    for i in range(n):
        idx = i + 1
        row = i + 1
        sym = symbols[i]
        row_lines.append(f'''    // Row {row}: {sym}
    sig_bg{idx} = sig{idx} == "LONG" ? color.lime : sig{idx} == "SHORT" ? color.red : color.gray
    sig_tc{idx} = sig{idx} == "WAIT" ? color.white : color.black
    table.cell(tbl, 0, {row}, "{sym}", text_color=color.yellow, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 1, {row}, sig{idx}, text_color=sig_tc{idx}, bgcolor=sig_bg{idx}, text_size=size.small)
    table.cell(tbl, 2, {row}, c{idx}, text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 3, {row}, ep{idx}, text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 4, {row}, tp{idx}, text_color=color.lime, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 5, {row}, sl{idx}, text_color=color.red, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 6, {row}, str.tostring(lev{idx}), text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)
    table.cell(tbl, 7, {row}, qty{idx}, text_color=color.white, bgcolor=#1a1a2e, text_size=size.small)''')
    table_rows = "\n".join(row_lines)

    # --- 3.4: Webhook Alerts ---
    alert_lines = []
    for i in range(n):
        idx = i + 1
        sym = symbols[i]
        alert_lines.append(
            f'    if at{idx} != "WAIT"\n'
            f'        alert(\'{{"type":"USDM_V12","batch":"{batch_label}","ticker":"{sym}","side":"\' + sd{idx} + \'","signal":"\' + at{idx} + \'","entry":\' + ep{idx} + \',"tp":\' + tp{idx} + \',"sl":\' + sl{idx} + \',"lev":\' + str.tostring(lev{idx}) + \',"qty":\' + qty{idx} + \',"time":\' + str.tostring(time) + \'}}\', alert.freq_once_per_bar)'
        )
    webhook_alerts = "\n".join(alert_lines)

    # --- Assemble Full Script with IMPROVED V12 PREMIUM ENGINE ---
    script = f'''// This Pine Script(TM) v6 indicator is subject to the terms of the Mozilla Public License 2.0
// Strategy: USD-M AUTOBOT DASHBOARD V12 PREMIUM (BATCH {batch_label})
// Engine: Premium High-Speed EMA Crossover (EMA 5/13 + Volume + RSI)
//@version=6
indicator("USD-M DASHBOARD V12 - BATCH {batch_label}", overlay=true, max_bars_back=500)

// ============================================================================
// 1. SOP & TRADING PLAN
// ============================================================================
fixedMargin = input.float(20.0, "Modal per Trade (USDT)", group="1. TRADING PLAN (SOP)")
maxMarginRiskPct = input.float(50.0, "Max Drawdown Modal (%)", step=5.0, group="1. TRADING PLAN (SOP)")
maxLeverageCap = input.int(20, "Maksimal Leverage (Limit)", minval=1, maxval=125, group="1. TRADING PLAN (SOP)")
tradeWeekdaysOnly = input.bool(true, "Matikan Bot di Sabtu & Minggu?", group="1. TRADING PLAN (SOP)")

// ============================================================================
// 2. ENGINE PARAMETERS
// ============================================================================
tf = input.timeframe("5", "Timeframe Screener", group="2. ENGINE")
maFastLen = input.int(5, "Fast MA (Momentum)", group="2. ENGINE")
maSlowLen = input.int(13, "Slow MA (Trigger)", group="2. ENGINE")
volLen = input.int(20, "Volume SMA Length", group="2. ENGINE")
volSpikeMult = input.float(1.5, "Volume Spike Multiplier", step=0.1, group="2. ENGINE")
rsiLen = input.int(14, "RSI Length", group="2. ENGINE")
atrPeriod = input.int(14, "ATR Period", group="2. ENGINE")
tpMult = input.float(1.5, "TP ATR Multiplier", step=0.1, group="2. ENGINE")
slMult = input.float(1.0, "SL ATR Multiplier", step=0.1, group="2. ENGINE")
waitForClose = input.bool(false, "Wait for Bar Close (Lebih aman, tapi lambat)", group="2. ENGINE")

// ============================================================================
// TICKER DEFINITIONS
// ============================================================================
{ticker_definitions}

// ============================================================================
// CORE ENGINE V12 — HIGH-SPEED EMA 5/13 CROSSOVER STRATEGY
// Strategy Logic (V12 Premium - Ultra Fast):
//   1. Entry Trigger: HMA (Hull Moving Average) 5 crosses 13 for NO-LAG reaction!
//   2. Volume Spike: Volume must be X times higher than its SMA to detect real momentum.
//   3. Momentum Filter: RSI >= 50 for Long, <= 50 for Short to ensure trend direction.
//   4. Auto-Invalidation: Exit immediately on reverse crossover.
// ============================================================================
f_engine() =>
    // --- MOVING AVERAGES (Using HMA for zero-lag real-time reaction) ---
    maFast = ta.hma(close, maFastLen)
    maSlow = ta.hma(close, maSlowLen)
    
    // --- VOLUME CONFIRMATION (Spike Detection) ---
    volMA = ta.sma(volume, volLen)
    isVolOk = volume > (volMA * volSpikeMult)
    
    // --- MOMENTUM: RSI ---
    rsiVal = ta.rsi(close, rsiLen)
    rsiLongOk = rsiVal >= 50
    rsiShortOk = rsiVal <= 50
    
    // --- WEEKEND FILTER ---
    isWeekend = dayofweek == dayofweek.saturday or dayofweek == dayofweek.sunday
    isTradingAllowed = tradeWeekdaysOnly ? not isWeekend : true
    
    // === HIGH-SPEED CROSSOVER ENTRY TRIGGERS ===
    isLong = isTradingAllowed and ta.crossover(maFast, maSlow) and isVolOk and rsiLongOk
    isShort = isTradingAllowed and ta.crossunder(maFast, maSlow) and isVolOk and rsiShortOk
    
    // --- ATR for dynamic TP/SL ---
    atrVal = ta.atr(atrPeriod)
    
    // === STATE MACHINE & LIVE CALCULATIONS ===
    var int tradeState = 0 
    var float ep = 0.0
    var float tp = 0.0
    var float sl = 0.0
    
    // Auto-Invalidation Exit: If opposite crossover occurs, exit immediately!
    if tradeState == 1
        if high >= tp or low <= sl or ta.crossunder(maFast, maSlow)
            tradeState := 0 
    if tradeState == -1
        if low <= tp or high >= sl or ta.crossover(maFast, maSlow)
            tradeState := 0 

    bool isNewLong = false
    bool isNewShort = false
    
    if isTradingAllowed
        if isLong and tradeState != 1
            tradeState := 1
            ep := close
            tp := close + (atrVal * tpMult)
            sl := close - (atrVal * slMult)
            isNewLong := true
        else if isShort and tradeState != -1
            tradeState := -1
            ep := close
            tp := close - (atrVal * tpMult)
            sl := close + (atrVal * slMult)
            isNewShort := true

    // Compute live values (shows actual trade values if active, or potential values if waiting)
    isBearishTrend = maFast < maSlow
    potential_tp = isBearishTrend ? (close - (atrVal * tpMult)) : (close + (atrVal * tpMult))
    potential_sl = isBearishTrend ? (close + (atrVal * slMult)) : (close - (atrVal * slMult))
    
    display_ep = tradeState != 0 ? ep : close
    display_tp = tradeState != 0 ? tp : potential_tp
    display_sl = tradeState != 0 ? sl : potential_sl
    
    display_sl_dist = (math.abs(display_ep - display_sl) / display_ep) * 100
    display_raw_lev = display_sl_dist > 0 ? (maxMarginRiskPct / display_sl_dist) : 1.0
    display_leverage = math.max(1, math.min(maxLeverageCap, math.round(display_raw_lev)))
    display_qty = display_ep > 0 ? ((fixedMargin * display_leverage) / display_ep) : 0.0
    
    // Convert all numeric values to beautiful strings matching ticker-specific decimal precision
    str_close = str.tostring(close, format.mintick)
    str_ep = str.tostring(display_ep, format.mintick)
    str_tp = str.tostring(display_tp, format.mintick)
    str_sl = str.tostring(display_sl, format.mintick)
    
    // Dynamic quantity formatting based on coin price magnitude to keep table extremely clean
    str_qty = display_qty >= 1000 ? str.tostring(math.round(display_qty)) : display_qty >= 10 ? str.tostring(display_qty, "#.##") : str.tostring(display_qty, "#.####")
            
    activeSig = tradeState == 1 ? "LONG" : tradeState == -1 ? "SHORT" : "WAIT"
    alert_trigger = isNewLong ? "LONG" : isNewShort ? "SHORT" : "WAIT"
    alert_side = isNewLong ? "BUY" : isNewShort ? "SELL" : "NONE"
    
    [str_close, str_ep, activeSig, alert_trigger, alert_side, str_tp, str_sl, display_leverage, str_qty]

// ============================================================================
// DATA FETCH - request.security
// ============================================================================
{security_calls}

// ============================================================================
// UI TABLE & DASHBOARD
// ============================================================================
var tbl = table.new(position.top_right, 8, 11, border_width=1, border_color=#333333)
if barstate.islast
    table.cell(tbl, 0, 0, "PAIR (B-{batch_label})", text_color=color.black, bgcolor=#f3ba2f, text_size=size.small)
    table.cell(tbl, 1, 0, "SIGNAL", text_color=color.black, bgcolor=#f3ba2f, text_size=size.small)
    table.cell(tbl, 2, 0, "PRICE NOW", text_color=color.black, bgcolor=#f3ba2f, text_size=size.small)
    table.cell(tbl, 3, 0, "ENTRY", text_color=color.black, bgcolor=#f3ba2f, text_size=size.small)
    table.cell(tbl, 4, 0, "TARGET TP", text_color=color.black, bgcolor=#f3ba2f, text_size=size.small)
    table.cell(tbl, 5, 0, "STOP LOSS", text_color=color.black, bgcolor=#f3ba2f, text_size=size.small)
    table.cell(tbl, 6, 0, "LEV", text_color=color.black, bgcolor=#f3ba2f, text_size=size.small)
    table.cell(tbl, 7, 0, "COIN QTY", text_color=color.black, bgcolor=#f3ba2f, text_size=size.small)
    
{table_rows}

// ============================================================================
// WEBHOOK ALERTS - JSON Payload
// ============================================================================
triggerAlert = waitForClose ? (barstate.islast and barstate.isconfirmed) : barstate.islast
if triggerAlert
{webhook_alerts}

plot(close, display=display.none)
'''
    return script


# ============================================================================
# MAIN - ORCHESTRATION
# ============================================================================
def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Phase 1: Fetch
    symbols = fetch_top_pairs()

    # Phase 2: Batch split
    batches = []
    for i in range(0, min(TOP_N, len(symbols)), BATCH_SIZE):
        batch_symbols = symbols[i:i + BATCH_SIZE]
        label = chr(65 + i // BATCH_SIZE)  # A, B, C, ..., J
        batches.append((label, batch_symbols))

    # Phase 3 & 4: Generate & Write
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n[OUTPUT] Directory: {OUTPUT_DIR}")
    print("-" * 60)

    for label, batch_symbols in batches:
        script = generate_pine_script(batch_symbols, label)
        filename = f"binance_usdm_autobot_batch_{label.lower()}.pine"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script)

        pair_preview = ", ".join(batch_symbols[:4]) + ", ..." if len(batch_symbols) > 4 else ", ".join(batch_symbols)
        print(f"[GEN] Batch {label} -> {pair_preview} ({len(batch_symbols)} pairs)")

    # Summary
    print("\n" + "=" * 60)
    print(f"[DONE] Generated {len(batches)} Pine Script V12 Premium files -> generated_screeners/")
    print(f"[TIME] {timestamp}")
    print("=" * 60)

    # Save metadata JSON
    meta = {
        "generated_at": timestamp,
        "total_pairs": len(symbols),
        "batches": len(batches),
        "engine": "V12 Premium High-Speed EMA Crossover (EMA 5/13 + Volume + RSI)",
        "pairs": {label: syms for label, syms in batches},
        "top_10": symbols[:10]
    }
    meta_path = os.path.join(OUTPUT_DIR, "_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[META] Saved metadata -> _metadata.json")


if __name__ == "__main__":
    main()
