from fastapi import FastAPI, Request, HTTPException
import httpx
import os
import re
import uvicorn
import asyncio
import secrets
import html
from datetime import datetime, timezone

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# ============================================================================
# STATE & CACHE (P2-01)
# ============================================================================
last_alert = {}
COOLDOWN_SECONDS = 300
FUTURES_FREEZE = False

ALLOWED_FUTURES_EVENTS = {
    "LONG_ENTRY", "SHORT_ENTRY",
    "LONG_TP_HIT", "LONG_SL_HIT",
    "SHORT_TP_HIT", "SHORT_SL_HIT",
    "LONG_TP1_HIT", "LONG_TP2_HIT", "LONG_TP3_HIT",
    "SHORT_TP1_HIT", "SHORT_TP2_HIT", "SHORT_TP3_HIT",
}

ALLOWED_EQUITY_EVENTS = {
    "BUY_ENTRY", "SELL_EXIT",
    "TP_HIT", "SL_HIT",
}

# ============================================================================
# LOGGING (P2-02)
# ============================================================================
os.makedirs("logs", exist_ok=True)
def log_alert(type_val, ticker, signal, score, tv, telegram_status):
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with open("logs/alerts.log", "a", encoding="utf-8") as f:
            f.write(f"{ts} | {type_val} | {ticker} | {signal} | {score} | {tv} | {telegram_status}\n")
    except Exception as e:
        print(f"Error writing log: {e}")

def h(value) -> str:
    return html.escape(str(value), quote=True)

# ============================================================================
# TELEGRAM SENDER
# ============================================================================
async def send_to_telegram(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Token/Chat ID is missing! Cannot send message.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    print(f"Telegram API Error: {response.text}")
                response.raise_for_status()
                print(f"Message sent to Telegram successfully: {text[:50]}...")
                return True
        except Exception as e:
            print(f"Telegram send failed attempt {attempt + 1}/3: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
    return False


# ============================================================================
# US SWING HUNTER v2 — Text Alert Parser
# ============================================================================
def format_us_swing_alert(raw: str) -> str:
    lines = raw.strip().split("\n")
    data = {}
    for line in lines:
        line = line.strip()
        if line.startswith("Ticker:"):
            data["ticker"] = line.split(":", 1)[1].strip()
        elif line.startswith("Price:"):
            data["price"] = line.split(":", 1)[1].strip()
        elif line.startswith("Signal:"):
            data["signal"] = line.split(":", 1)[1].strip()
        elif line.startswith("RSI:"):
            data["momentum"] = line.split(":", 1)[1].strip()

    ticker = h(data.get("ticker", "???"))
    price = h(data.get("price", "$0"))
    signal = h(data.get("signal", "UNKNOWN"))
    momentum = h(data.get("momentum", "-"))

    rsi_match = re.search(r"([\d.]+)", momentum)
    rsi_val = float(rsi_match.group(1)) if rsi_match else 50.0

    if "BREAKOUT" in signal:
        icon = "🚀"
        sentiment = "Momentum breakout detected"
    elif "BULL ABSORB" in signal:
        icon = "🟢"
        sentiment = "Buyers absorbing selling pressure"
    elif "BEAR ABSORB" in signal:
        icon = "🔴"
        sentiment = "Sellers absorbing buying pressure"
    elif "DISTRIBUTION" in signal:
        icon = "⚠️"
        sentiment = "Smart money distributing shares"
    else:
        icon = "📊"
        sentiment = "Monitoring"

    if rsi_val < 30:
        rsi_tag = "🟢 Oversold"
    elif rsi_val > 70:
        rsi_tag = "🔴 Overbought"
    else:
        rsi_tag = "⚪ Neutral"

    msg = f"{icon} <b>US SWING HUNTER</b> {icon}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🏷 <b>Ticker</b>: <code>{ticker}</code>\n"
    msg += f"💵 <b>Price</b>: {price}\n"
    msg += f"⚡ <b>Signal</b>: <b>{signal}</b>\n"
    msg += f"📈 <b>Momentum</b>: RSI {momentum}\n"
    msg += f"🌡 <b>RSI Zone</b>: {rsi_tag}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💡 <i>{sentiment}</i>\n"
    msg += f"⏰ TF 15m · Swing 2-10 hari\n"
    msg += f"#US_SWING #{ticker}"

    return msg


# ============================================================================
# US BANDAR AI v2 — Text Alert Parser
# ============================================================================
def format_us_bandar_alert(raw: str) -> str:
    lines = raw.strip().split("\n")
    data = {}
    for line in lines:
        line = line.strip()
        if line.startswith("Ticker:"):
            data["ticker"] = line.split(":", 1)[1].strip()
        elif line.startswith("Price:"):
            data["price"] = line.split(":", 1)[1].strip()
        elif line.startswith("Signal:"):
            data["signal"] = line.split(":", 1)[1].strip()
        elif line.startswith("Flow:"):
            data["flow"] = line.split(":", 1)[1].strip()
        elif line.startswith("Strength:"):
            data["strength"] = line.split(":", 1)[1].strip()

    ticker = h(data.get("ticker", "???"))
    price = h(data.get("price", "$0"))
    signal = h(data.get("signal", "UNKNOWN"))
    flow = h(data.get("flow", "NORMAL"))
    strength = h(data.get("strength", "0%"))

    str_match = re.search(r"([\d.]+)", strength)
    str_val = float(str_match.group(1)) if str_match else 0.0

    if "SNIPER BUY" in signal:
        icon = "🎯"
        sentiment = "Institutional buying detected — HIGH CONVICTION entry"
    elif "BULL ABSORB" in signal:
        icon = "🟢"
        sentiment = "Smart money absorbing dip — accumulation in progress"
    elif "SNIPER SELL" in signal:
        icon = "🔻"
        sentiment = "Institutional selling detected — distribution warning"
    elif "BEAR ABSORB" in signal:
        icon = "🔴"
        sentiment = "Selling pressure absorbed by weak hands — caution"
    else:
        icon = "📊"
        sentiment = "Monitoring institutional flow"

    flow_icons = {
        "BIG ACCUM": "🐋 Big Accumulation",
        "ACCUM": "🟢 Accumulation",
        "BIG DISTRIB": "🚨 Big Distribution",
        "DISTRIB": "🟠 Distribution",
        "NORMAL": "⚪ Normal"
    }
    flow_display = flow_icons.get(flow, f"⚪ {flow}")

    filled = int(str_val / 20)
    bar = "█" * filled + "░" * (5 - filled)

    msg = f"{icon} <b>US BANDAR AI</b> {icon}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🏷 <b>Ticker</b>: <code>{ticker}</code>\n"
    msg += f"💵 <b>Price</b>: {price}\n"
    msg += f"⚡ <b>Signal</b>: <b>{signal}</b>\n"
    msg += f"💰 <b>Flow</b>: {flow_display}\n"
    msg += f"💪 <b>Strength</b>: {strength} [{bar}]\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💡 <i>{sentiment}</i>\n"
    msg += f"⏰ TF 10m · Bandar Detection\n"
    msg += f"#US_BANDAR #{ticker}"

    return msg


# ============================================================================
# QUANTUM SIGNAL — Universal Parser (Gold & Bitcoin)
# ============================================================================
def format_quantum_alert(raw: str, market_type: str) -> str:
    lines = raw.strip().split("\n")
    data = {}
    for line in lines:
        line = line.strip()
        if line.startswith("Ticker:"):
            data["ticker"] = line.split(":", 1)[1].strip()[:20]
        elif line.startswith("Action:"):
            data["action"] = line.split(":", 1)[1].strip()
        elif line.startswith("Entry:"):
            data["entry"] = line.split(":", 1)[1].strip()
        elif line.startswith("TP1:"):
            data["tp1"] = line.split(":", 1)[1].strip()
        elif line.startswith("TP2:"):
            data["tp2"] = line.split(":", 1)[1].strip()
        elif line.startswith("SL:"):
            data["sl"] = line.split(":", 1)[1].strip()
        elif line.startswith("Context:"):
            data["context"] = line.split(":", 1)[1].strip()[:200]

    ticker = h(data.get("ticker") or "???")
    context = h(data.get("context") or "???")

    action_raw = h(data.get("action", ""))
    action = action_raw if action_raw in ("BUY", "SELL") else "???"

    # Helper function untuk membersihkan format harga
    def _parse_price(raw_value):
        try:
            # Menghapus spasi atau karakter tak terduga sebelum diubah ke float
            clean_value = raw_value.replace(",", "")
            value = float(clean_value)
            
            # Dinamis: Jika desimalnya 0, format utuh. Jika ada desimal, tampilkan persis.
            if value.is_integer():
                return value, f"{int(value)}"
            else:
                return value, f"{value}"
        except (TypeError, ValueError, AttributeError):
            return None, "0.00"

    entry_val, entry_str = _parse_price(data.get("entry"))
    tp1_val, tp1_str = _parse_price(data.get("tp1"))
    tp2_val, tp2_str = _parse_price(data.get("tp2"))
    sl_val, sl_str = _parse_price(data.get("sl"))

    # R:R Calculation (Risk to Reward untuk TP1)
    rr_str = "N/A"
    if entry_val is not None and tp1_val is not None and sl_val is not None:
        if action == "BUY":
            denominator = entry_val - sl_val
            if denominator != 0:
                rr_str = f"{(tp1_val - entry_val) / denominator:.1f}"
        elif action == "SELL":
            denominator = sl_val - entry_val
            if denominator != 0:
                rr_str = f"{(entry_val - tp1_val) / denominator:.1f}"

    # Visual Adjustments based on Market Type (XAU vs BTC)
    if market_type == "GOLD":
        title_str = "XAU QUANTUM SIGNAL"
        asset_icon = "🥇"
        hashtags = f"#GOLD #{ticker.replace('/', '')}"
    elif market_type == "BTC":
        title_str = "BTC QUANTUM SIGNAL"
        asset_icon = "₿"
        hashtags = f"#BITCOIN #{ticker.replace('/', '')}"
    else:
        title_str = "QUANTUM SIGNAL"
        asset_icon = "📈"
        hashtags = f"#{ticker.replace('/', '')}"

    # Header warna berdasarkan jenis posisi
    if action == "BUY":
        header_emoji = "🟢"
    elif action == "SELL":
        header_emoji = "🔴"
    else:
        header_emoji = "⚪"

    separator = "━━━━━━━━━━━━━━━━━━"

    msg = f"{header_emoji} <b>{title_str}</b> {header_emoji}\n"
    msg += f"{separator}\n"
    msg += f"{asset_icon} <b>Pair</b>: <code>{ticker}</code>\n"
    msg += f"⚡ <b>Action</b>: <b>{action}</b>\n"
    msg += f"🎯 <b>Entry</b>: {entry_str}\n"
    msg += f"✅ <b>TP1</b>: {tp1_str}\n"
    msg += f"🚀 <b>TP2</b>: {tp2_str}\n"
    msg += f"🛑 <b>SL</b>: {sl_str}\n"
    msg += f"{separator}\n"
    msg += f"📊 <b>Context</b>: <i>{context}</i>\n"
    msg += f"⚖️ <b>Risk:Reward (TP1)</b>: {rr_str}\n"
    msg += f"{separator}\n"
    msg += f"{hashtags}"

    return msg


# ============================================================================
# IDX BANDAR AI (Legacy) — JSON Alert Parser
# ============================================================================
def format_idx_bandar_alert(data: dict) -> str:
    ticker = h(data.get("ticker", "UNKNOWN"))
    signal = h(data.get("signal", "UNKNOWN"))
    price = h(data.get("price", "0"))

    signal_upper = signal.upper()
    if any(k in signal_upper for k in ["BUY", "BULL", "AKUM", "HAKA"]):
        icon = "🟢"
        sentiment = "Deteksi akumulasi Bandar — Peluang Entry"
    elif any(k in signal_upper for k in ["SELL", "BEAR", "DIST", "HAKI"]):
        icon = "🔴"
        sentiment = "Deteksi distribusi Bandar — Waspada Guyuran"
    else:
        icon = "⚡"
        sentiment = "Pergerakan Smart Money terdeteksi"

    msg = f"{icon} <b>IDX BANDAR AI</b> {icon}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🏢 <b>Emiten</b>: <code>{ticker}</code>\n"
    msg += f"💰 <b>Harga</b>: Rp{price}\n"
    msg += f"📊 <b>Signal</b>: <b>{signal}</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💡 <i>{sentiment}</i>\n"
    msg += f"🇮🇩 Saham Indonesia (BEI)\n"
    msg += f"#IDX_BANDAR #{ticker}"
    return msg


# ============================================================================
# IDX SCALPING (Legacy) — JSON Alert Parser
# ============================================================================
def format_idx_scalp_alert(data: dict) -> str:
    ticker = h(data.get("ticker", "UNKNOWN"))
    action_raw = str(data.get("action") or data.get("signal") or data.get("event") or "UNKNOWN")
    entry = h(data.get("entry", "0"))
    tp = h(data.get("tp") or data.get("tp1") or data.get("tp2") or "0")
    sl = h(data.get("sl", "0"))
    bandar = h(data.get("bandar", "-"))
    zona = h(data.get("zona", "-"))

    action_upper = action_raw.upper()
    if "BUY" in action_upper or "HAKA" in action_upper:
        action = "BUY"
        icon = "🔥"
        sentiment = "Momentum HAKA super cepat terdeteksi! Siap pantau bid-offer."
    elif "SELL" in action_upper or "HAKI" in action_upper or "EXIT" in action_upper:
        action = "SELL"
        icon = "⚠️"
        sentiment = "Tekanan jual HAKI tinggi, amankan profit / ketat SL."
    else:
        action = action_raw
        icon = "⚡"
        sentiment = "Sinyal Scalping aktif."

    bandar_upper = bandar.upper()
    bandar_display = f"🐋 {bandar}" if "AKUM" in bandar_upper else f"🚨 {bandar}" if "DIST" in bandar_upper else f"⚪ {bandar}"
    
    zona_upper = zona.upper()
    zona_display = f"🟢 {zona}" if any(k in zona_upper for k in ["AMAN", "BULL"]) else f"🔴 {zona}" if "RAWAN" in zona_upper else f"⚪ {zona}"

    msg = f"{icon} <b>IDX SCALPING HUNTER</b> {icon}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🏢 <b>Emiten</b>: <code>{ticker}</code>\n"
    msg += f"⚡ <b>Action</b>: <b>{action}</b>\n"
    msg += f"🎯 <b>Entry</b>: Rp{entry}\n"
    msg += f"✅ <b>TP</b>: Rp{tp} (Target ~3%)\n"
    msg += f"🛑 <b>SL</b>: Rp{sl}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 <b>Bandar Flow</b>: {bandar_display}\n"
    msg += f"🌡 <b>Zona Risk</b>: {zona_display}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💡 <i>{sentiment}</i>\n"
    msg += f"⚡ Disiplin TP/SL · Scalp &lt; 15 Menit\n"
    msg += f"#IDX_SCALP #{ticker}"
    return msg


# ============================================================================
# HELPER: Format Transaction Value (Nilai Transaksi)
# ============================================================================
def _format_tv(tv: float) -> str:
    try:
        tv = float(tv)
        if tv >= 1e9:
            return f"Rp{tv/1e9:.1f}B"
        return f"Rp{tv/1e6:.1f}M"
    except:
        return "N/A"

# ============================================================================
# IDX BANDAR AI V2 — JSON Alert Parser
# ============================================================================
def format_idx_bandar_v2_alert(data: dict) -> str:
    tier = data.get("tier")
    if not tier:
        raise ValueError("Missing 'tier' in payload")
        
    ticker = h(data.get("ticker", "UNKNOWN"))
    signal = h(data.get("signal", "UNKNOWN"))
    entry = data.get("entry", 0)
    tp1 = data.get("tp1", 0)
    tp2 = data.get("tp2", 0)
    sl = data.get("sl", 0)
    tv = data.get("transaction_value", 0)
    hint = data.get("holding_hint", "swing 3-7 hari")

    try:
        sl_warn = " ⚠️(SL > Entry)" if float(sl) >= float(entry) else ""
    except:
        sl_warn = ""

    signal_upper = signal.upper()
    if any(k in signal_upper for k in ["BUY", "BULL", "AKUM", "HAKA"]):
        icon = "🟢"
        sentiment = "Deteksi akumulasi Bandar — Peluang Entry"
    elif any(k in signal_upper for k in ["SELL", "BEAR", "DIST", "HAKI"]):
        icon = "🔴"
        sentiment = "Deteksi distribusi Bandar — Waspada Guyuran"
    else:
        icon = "⚡"
        sentiment = "Pergerakan Smart Money terdeteksi"

    msg = f"{icon} <b>IDX BANDAR AI V2</b> {icon}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🏢 <b>Emiten</b>: <code>{ticker}</code> (BANDAR · SWING 1W)\n"
    
    # Optional Trade Plan Fields
    score = data.get("score")
    sup = data.get("support")
    rst = data.get("resistance")
    action = data.get("action")
    
    if score is not None and action is not None:
        msg += f"📊 <b>Score</b>: {score} | {signal}\n"
        msg += f"⚡ <b>Action</b>: <b>{action}</b>\n"
        msg += f"💵 <b>Val/Bar</b>: {_format_tv(tv)}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        msg += f"🎯 <b>Entry</b>: Rp{entry}\n"
        msg += f"✅ <b>TP1</b>: Rp{tp1}\n"
        msg += f"🚀 <b>TP2</b>: Rp{tp2}\n"
        msg += f"🛑 <b>SL</b>: Rp{sl}{sl_warn}\n"
        msg += f"📍 <b>SUP/RST</b>: {sup} / {rst}\n"
    else:
        msg += f"📊 <b>Signal</b>: <b>{signal}</b>\n"
        msg += f"💵 <b>Val/Bar</b>: {_format_tv(tv)}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        msg += f"🎯 <b>Entry</b>: Rp{entry}\n"
        msg += f"✅ <b>TP1</b>: Rp{tp1}\n"
        msg += f"🚀 <b>TP2</b>: Rp{tp2}\n"
        msg += f"🛑 <b>SL</b>: Rp{sl}{sl_warn}\n"

    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💡 <i>{sentiment}</i>\n"
    msg += f"⏳ {hint}\n"
    msg += f"#IDX_BANDAR_V2 #{ticker}"
    return msg


# ============================================================================
# IDX SCALPING V2 — JSON Alert Parser
# ============================================================================
def format_idx_scalp_v2_alert(data: dict) -> str:
    tier = data.get("tier")
    if not tier:
        raise ValueError("Missing 'tier' in payload")
        
    ticker = h(data.get("ticker", "UNKNOWN"))
    signal = h(data.get("signal", "UNKNOWN"))
    entry = data.get("entry", 0)
    tp1 = data.get("tp1", 0)
    tp2 = data.get("tp2", 0)
    sl = data.get("sl", 0)
    tv = data.get("transaction_value", 0)
    hint = data.get("holding_hint", "intraday (menit-jam)")
    
    try:
        sl_warn = " ⚠️(SL > Entry)" if float(sl) >= float(entry) else ""
    except:
        sl_warn = ""

    signal_upper = signal.upper()
    if any(k in signal_upper for k in ["BUY", "HAKA"]):
        icon = "🔥"
        sentiment = "Momentum HAKA super cepat terdeteksi! Siap pantau bid-offer."
    elif any(k in signal_upper for k in ["SELL", "HAKI"]):
        icon = "⚠️"
        sentiment = "Tekanan jual HAKI tinggi, amankan profit / ketat SL."
    else:
        icon = "⚡"
        sentiment = "Sinyal Scalping aktif."

    msg = f"{icon} <b>IDX SCALPING V2</b> {icon}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🏢 <b>Emiten</b>: <code>{ticker}</code> (SCALP · GORENGAN)\n"

    # Optional Trade Plan Fields
    score = data.get("score")
    sup = data.get("support")
    rst = data.get("resistance")
    action = data.get("action")
    
    if score is not None and action is not None:
        msg += f"📊 <b>Score</b>: {score} | {signal}\n"
        msg += f"⚡ <b>Action</b>: <b>{action}</b>\n"
        msg += f"💵 <b>Val/Bar</b>: {_format_tv(tv)}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        msg += f"🎯 <b>Entry</b>: Rp{entry}\n"
        msg += f"✅ <b>TP1</b>: Rp{tp1}\n"
        msg += f"🚀 <b>TP2</b>: Rp{tp2}\n"
        msg += f"🛑 <b>SL</b>: Rp{sl}{sl_warn}\n"
        msg += f"📍 <b>SUP/RST</b>: {sup} / {rst}\n"
    else:
        msg += f"⚡ <b>Signal</b>: <b>{signal}</b>\n"
        msg += f"💵 <b>Val/Bar</b>: {_format_tv(tv)}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        msg += f"🎯 <b>Entry</b>: Rp{entry}\n"
        msg += f"✅ <b>TP1</b>: Rp{tp1}\n"
        msg += f"🚀 <b>TP2</b>: Rp{tp2}\n"
        msg += f"🛑 <b>SL</b>: Rp{sl}{sl_warn}\n"

    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💡 <i>{sentiment}</i>\n"
    msg += f"⏳ {hint}\n"
    msg += f"#IDX_SCALP_V2 #{ticker}"
    return msg


# ============================================================================
# US SWING & BANDAR V3 — JSON Alert Parser
# ============================================================================
def format_us_v3_alert(data: dict) -> str:
    type_val = data.get("type", "US_SWING_V3")
    ticker = h(data.get("ticker") or data.get("symbol") or "UNKNOWN")
    signal = h(data.get("signal") or data.get("event") or "UNKNOWN")
    entry = data.get("entry", 0)
    tp1 = data.get("tp1", 0)
    tp2 = data.get("tp2", 0)
    sl = data.get("sl", 0)
    tv = data.get("transaction_value", 0)
    hint = data.get("holding_hint", "swing 2-10 days")
    score = data.get("score", 0)
    sup = data.get("support", 0)
    rst = data.get("resistance", 0)
    action = data.get("action", "BUY")
    flow = h(data.get("bandar") or data.get("flow") or "-")
    zona = h(data.get("zona", "-"))
    
    strategy_name = "US SWING HUNTER V3" if "SWING" in type_val else "US BANDAR AI V3"
    
    signal_upper = signal.upper()
    if "BUY_ENTRY" in signal_upper or "LONG_ENTRY" in signal_upper:
        icon = "🟢"
        title = f"{strategy_name} - ENTRY"
        sentiment = "Premium institutional entry signal terdeteksi"
    elif any(k in signal_upper for k in ["TP1_HIT", "TP2_HIT", "TP_HIT"]):
        icon = "🎯"
        title = f"{strategy_name} - TP HIT"
        sentiment = "Target profit tercapai! Amankan keuntungan"
    elif any(k in signal_upper for k in ["SL_HIT", "SL-BROKE"]):
        icon = "🛑"
        title = f"{strategy_name} - SL HIT"
        sentiment = "Stop loss terpicu. Batasi risiko"
    else:
        icon = "🚀" if "SWING" in type_val else "🎯"
        title = strategy_name
        sentiment = "Premium institutional stock alert"

    try:
        sl_warn = " ⚠️(SL > Entry)" if float(sl) >= float(entry) and float(entry) > 0 else ""
    except:
        sl_warn = ""

    msg = f"{icon} <b>{title}</b> {icon}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🇺🇸 <b>Ticker</b>: <code>{ticker}</code> (US PENNY STOCK)\n"
    msg += f"📊 <b>Score</b>: {score} | <b>{signal}</b>\n"
    msg += f"⚡ <b>Action</b>: <b>{action}</b>\n"
    msg += f"💵 <b>Vol/Bar</b>: ${tv:,.0f}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🎯 <b>Entry</b>: ${entry:.2f}\n"
    msg += f"✅ <b>TP1</b>: ${tp1:.2f}\n"
    msg += f"🚀 <b>TP2</b>: ${tp2:.2f}\n"
    msg += f"🛑 <b>SL</b>: ${sl:.2f}{sl_warn}\n"
    msg += f"📍 <b>SUP/RST</b>: ${sup:.2f} / ${rst:.2f}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💰 <b>Flow</b>: {flow}\n"
    msg += f"🌡 <b>Zone</b>: {zona}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💡 <i>{sentiment}</i>\n"
    msg += f"⏳ {hint}\n"
    msg += f"#US_V3 #{ticker}"
    return msg


# ============================================================================
# WEBHOOK VALIDATION HELPERS (Phase 5)
# ============================================================================
def validate_direction(data: dict) -> bool:
    side = data.get("side", "")
    version = data.get("version", "1.0")
    try:
        if version == "2.0":
            entry = float(data.get("entry_avg", 0))
            tp = float(data.get("tp1", 0))
            sl = float(data.get("sl", 0))
        else:
            entry = float(data.get("entry", 0))
            tp = float(data.get("tp", 0))
            sl = float(data.get("sl", 0))
    except (ValueError, TypeError):
        return False
        
    if entry <= 0:
        return True  # skip check if entry not specified
        
    if side == "LONG":
        return tp > entry and sl < entry
    if side == "SHORT":
        return tp < entry and sl > entry
    return False

def validate_hit(data: dict) -> bool:
    event = data.get("event", "")
    version = data.get("version", "1.0")
    try:
        now = float(data.get("now", 0))
        sl = float(data.get("sl", 0))
        if version == "2.0":
            tp1 = float(data.get("tp1", 0))
            tp2 = float(data.get("tp2", 0))
            tp3 = float(data.get("tp3", 0))
        else:
            tp = float(data.get("tp", 0))
    except (ValueError, TypeError):
        return False
        
    if event == "LONG_TP_HIT":   return now >= tp
    if event == "LONG_SL_HIT":   return now <= sl
    if event == "SHORT_TP_HIT":  return now <= tp
    if event == "SHORT_SL_HIT":  return now >= sl
    
    # Version 2.0 TP hits
    if event == "LONG_TP1_HIT":  return now >= tp1
    if event == "LONG_TP2_HIT":  return now >= tp2
    if event == "LONG_TP3_HIT":  return now >= tp3
    if event == "SHORT_TP1_HIT": return now <= tp1
    if event == "SHORT_TP2_HIT": return now <= tp2
    if event == "SHORT_TP3_HIT": return now <= tp3
    return True

def validate_market_type(data: dict) -> bool:
    market = data.get("market", "")
    event = data.get("event", "")
    
    if market in ("IDX", "US"):
        if event in ("SHORT_ENTRY", "SHORT_TP_HIT", "SHORT_SL_HIT") or data.get("side") == "SHORT":
            return False
    return True


# ============================================================================
# BINANCE FUTURES — JSON Alert Parser
# ============================================================================
def format_futures_message(data: dict) -> str:
    symbol = h(data.get("symbol", "UNKNOWN"))
    event = h(data.get("event", "UNKNOWN"))
    tf_trigger = h(data.get("tf_trigger", data.get("tf", "15")))
    tf_zone = h(data.get("tf_zone", "60"))
    tf_bias = h(data.get("tf_bias", "240"))
    side = h(data.get("side", "NONE"))
    version = data.get("version", "1.0")
    
    price_decimals = data.get("price_decimals", 4)
    def fmt_price(key):
        val = data.get(key)
        if f"{key}_text" in data and data[f"{key}_text"] != "-":
            return h(data[f"{key}_text"])
        if val is None or val == "-":
            return "-"
        try:
            return f"{float(val):.{price_decimals}f}"
        except:
            return str(val)

    price_text = data.get("price_text", {})
    def get_price(key):
        if key in price_text and price_text[key] != "-":
            return h(price_text[key])
        return fmt_price(key)

    # Decode titles
    if version == "2.0":
        if event == "LONG_ENTRY":
            icon, title = "🟢", "BINANCE FUTURES LONG - ENTRY"
        elif event == "SHORT_ENTRY":
            icon, title = "🔴", "BINANCE FUTURES SHORT - ENTRY"
        elif event == "LONG_TP1_HIT":
            icon, title = "🎯", "TP1 HIT - LONG PARTIAL"
        elif event == "SHORT_TP1_HIT":
            icon, title = "🎯", "TP1 HIT - SHORT PARTIAL"
        elif event == "LONG_TP2_HIT":
            icon, title = "🎯", "TP2 HIT - LONG PARTIAL"
        elif event == "SHORT_TP2_HIT":
            icon, title = "🎯", "TP2 HIT - SHORT PARTIAL"
        elif event == "LONG_TP3_HIT":
            icon, title = "🏆", "ALL TP HIT - LONG CLOSED"
        elif event == "SHORT_TP3_HIT":
            icon, title = "🏆", "ALL TP HIT - SHORT CLOSED"
        elif event == "LONG_SL_HIT":
            icon, title = "🛑", "SL HIT - LONG CLOSED"
        elif event == "SHORT_SL_HIT":
            icon, title = "🛑", "SL HIT - SHORT CLOSED"
        else:
            icon = "🟢" if "LONG" in side.upper() else "🔴"
            title = f"BINANCE FUTURES {side.upper()}"
    else:
        # Legacy version 1.0 support
        if event == "LONG_ENTRY":
            icon, title = "🟢", "BINANCE FUTURES LONG - ENTRY"
        elif event == "SHORT_ENTRY":
            icon, title = "🔴", "BINANCE FUTURES SHORT - ENTRY"
        elif event == "LONG_TP_HIT":
            icon, title = "🎯", "TP HIT - LONG CLOSED"
        elif event == "SHORT_TP_HIT":
            icon, title = "🎯", "TP HIT - SHORT CLOSED"
        elif event == "LONG_SL_HIT":
            icon, title = "🛑", "SL HIT - LONG CLOSED"
        elif event == "SHORT_SL_HIT":
            icon, title = "🛑", "SL HIT - SHORT CLOSED"
        else:
            icon = "🟢" if "LONG" in side.upper() else "🔴"
            title = f"BINANCE FUTURES {side.upper()}"

    if version == "2.0":
        now = get_price("now")
        entry_low = get_price("entry_low")
        entry_high = get_price("entry_high")
        entry_avg = get_price("entry_avg")
        tp1 = get_price("tp1")
        tp2 = get_price("tp2")
        tp3 = get_price("tp3")
        sl = get_price("sl")
        
        mode = h(data.get("mode", "-"))
        status = h(data.get("status", "-"))
        risk_label = h(data.get("risk_label", "-"))
        rec_lev = data.get("recommended_leverage", 1)
        input_leverage = data.get("input_leverage", 10)
        
        score = data.get("score", 0)
        bias_4h = h(data.get("bias_4h", "-"))
        bias_strength_4h = h(data.get("bias_strength_4h", "-"))
        zone_1h = h(data.get("zone_1h", "-"))
        zone_score_1h = data.get("zone_score_1h", "-")
        rsi = data.get("rsi", "-")
        rvol = data.get("rvol", "-")
        
        # Format percentages
        try:
            rvol_pct = f"{float(rvol) * 100:.1f}%" if rvol != "-" else "-"
        except:
            rvol_pct = str(rvol)
            
        try:
            risk_pct = float(data.get("risk_pct", 0.0))
            risk_pct_str = f"{risk_pct:.2f}%"
        except:
            risk_pct_str = "-"
            
        rr_tp1 = data.get("rr_tp1", "-")
        rr_tp2 = data.get("rr_tp2", "-")
        rr_tp3 = data.get("rr_tp3", "-")
        
        msg = f"{icon} <b>{title}</b> {icon}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        msg += f"🏷 <b>Symbol</b> : <code>{symbol}</code>\n"
        msg += f"⏰ <b>TF</b>     : {tf_trigger}m / {tf_zone}m / {tf_bias}m\n"
        msg += f"⚡ <b>Event</b>  : <b>{event}</b>\n"
        msg += f"🎯 <b>Mode</b>   : {mode}\n\n"
        
        msg += f"💵 <b>NOW</b>    : {now}\n"
        msg += f"📥 <b>ENTRY</b>  : {entry_low} - {entry_high} (Avg: {entry_avg})\n"
        msg += f"🎯 <b>TP1</b>    : {tp1} (RR: {rr_tp1})\n"
        msg += f"🎯 <b>TP2</b>    : {tp2} (RR: {rr_tp2})\n"
        msg += f"🎯 <b>TP3</b>    : {tp3} (RR: {rr_tp3})\n"
        msg += f"🛑 <b>SL</b>     : {sl} ({risk_pct_str})\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        
        msg += f"📈 <b>LEV</b>    : {input_leverage}x (Rec: {rec_lev}x)\n"
        msg += f"🛡️ <b>RISK</b>   : <b>{risk_label}</b>\n"
        msg += f"📊 <b>Score</b>  : {score}\n\n"
        
        msg += f"🧭 <b>Bias 4H</b>: {bias_4h} ({bias_strength_4h})\n"
        msg += f"🌡 <b>Zone 1H</b>: {zone_1h} (Score: {zone_score_1h})\n"
        msg += f"📉 <b>RSI</b>    : {rsi}\n"
        msg += f"🔊 <b>RVOL</b>   : {rvol_pct}\n"
        
        if risk_label == "RISKY_PLAN":
            msg += f"━━━━━━━━━━━━━━━━━━\n"
            msg += f"⚠️ <b>WARNING</b>: Gunakan leverage lebih kecil dari input, recommended leverage: <b>{rec_lev}x</b>\n"
            
        return msg
    else:
        # Legacy v1 logic
        now = h(price_text.get("now", fmt_price("now")))
        entry = h(price_text.get("entry", fmt_price("entry")))
        tp = h(price_text.get("tp", fmt_price("tp")))
        sl = h(price_text.get("sl", fmt_price("sl")))
        
        if "LONG" in side.upper() or "LONG" in event:
            tp_sign = "+"
            sl_sign = "-"
            l_tp_sign = "+"
            l_risk_sign = "-"
        else:
            tp_sign = "-"
            sl_sign = "+"
            l_tp_sign = "+"
            l_risk_sign = "-"
        
        rr = float(data.get("rr", 0.0))
        tp_pct = float(data.get("tp_pct", 0.0))
        risk_pct = float(data.get("risk_pct", 0.0))
        
        lev = data.get("leverage", 1)
        l_tp = float(data.get("lev_tp_pct", 0.0))
        l_risk = float(data.get("lev_risk_pct", 0.0))
        max_lev = data.get("max_safe_leverage", "-")
        liq = h(data.get("liq_warn", "SAFE"))
        
        score = data.get("score", 0)
        flow = h(data.get("flow", "-"))
        signal = h(data.get("signal", "-"))
        
        msg = f"{icon} <b>{title}</b> {icon}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        msg += f"🏷 <b>Symbol</b> : <code>{symbol}</code>\n"
        msg += f"⏰ <b>TF</b>     : {tf_trigger}m\n"
        msg += f"⚡ <b>Event</b>  : <b>{event}</b>\n\n"
        
        msg += f"💵 <b>NOW</b>    : {now}\n"
        msg += f"🎯 <b>ENTRY</b>  : {entry}\n"
        msg += f"✅ <b>TP</b>     : {tp} ({tp_sign}{tp_pct:.2f}%)\n"
        msg += f"🛑 <b>SL</b>     : {sl} ({sl_sign}{risk_pct:.2f}%)\n"
        msg += f"⚖️ <b>RR</b>     : {rr:.2f}\n━━━━━━━━━━━━━━━━━━\n"
        
        msg += f"📈 <b>LEV</b>    : {lev}x\n"
        msg += f"🚀 <b>L-TP</b>   : {l_tp_sign}{l_tp:.2f}%\n"
        msg += f"📉 <b>L-RISK</b> : {l_risk_sign}{l_risk:.2f}%\n"
        msg += f"🛡️ <b>MAX LEV</b>: {max_lev}x\n"
        msg += f"🔥 <b>LIQ</b>    : {liq}\n━━━━━━━━━━━━━━━━━━\n"
        
        msg += f"📊 <b>Score</b>  : {score}\n"
        msg += f"💰 <b>Flow</b>   : {flow}\n"
        msg += f"🌡 <b>Signal</b> : {signal}\n"
        
        return msg


# ============================================================================
# WEBHOOK HANDLER
# ============================================================================
@app.post("/webhook")
async def handle_webhook(request: Request):
    if WEBHOOK_SECRET:
        provided_secret = request.headers.get("x-webhook-secret") or request.query_params.get("secret")
        if not provided_secret or not secrets.compare_digest(provided_secret, WEBHOOK_SECRET):
            raise HTTPException(status_code=403, detail="Forbidden")

    content_type = request.headers.get("content-type", "")
    user_agent = request.headers.get("user-agent", "unknown")
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8", errors="replace").strip()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] 📨 WEBHOOK HIT | Content-Type: {content_type} | UA: {user_agent} | Body ({len(body_str)} chars): {body_str[:200]}")

    message_text = ""

    # 1. Cek JSON
    try:
        data = await request.json()
        if isinstance(data, dict):
            # Key normalization for compatibility
            if "symbol" in data and "ticker" not in data:
                data["ticker"] = data["symbol"]
            if "event" in data and "signal" not in data:
                data["signal"] = data["event"]

            # Reject any SHORT signals for IDX/US equity/stocks
            if data.get("type") in ("BANDAR_AI", "SCALP", "BANDAR_AI_V3", "SCALP_V3", "US_SWING_V3", "US_BANDAR_V3", "US_STOCKS_SIGNAL") or data.get("market") in ("IDX", "US"):
                if data.get("side") == "SHORT" or "SHORT" in str(data.get("signal", "")) or "SHORT" in str(data.get("action", "")) or "SHORT" in str(data.get("event", "")):
                    print(f"[{ts}] ❌ Equity alert rejected: SHORT is not supported for stocks.")
                    return {"status": "ignored", "reason": "invalid_equity_event"}
                
                # Reject UNKNOWN / WAIT / NONE signals
                action_str = str(data.get("action", "")).upper()
                signal_str = str(data.get("signal", "")).upper()
                event_str = str(data.get("event", "")).upper()
                if any(x in action_str for x in ("UNKNOWN", "WAIT", "NONE")) or \
                   any(x in signal_str for x in ("UNKNOWN", "WAIT", "NONE")) or \
                   any(x in event_str for x in ("UNKNOWN", "WAIT", "NONE")):
                    print(f"[{ts}] ❌ Equity alert rejected: Action/Signal/Event contains UNKNOWN, WAIT, or NONE.")
                    return {"status": "ignored", "reason": "non_actionable_equity_event"}
                
                # Reject 0/invalid entry price
                try:
                    entry_val = float(data.get("entry") or data.get("price") or 0)
                    if entry_val <= 0:
                        print(f"[{ts}] ❌ Equity alert rejected: Entry price is 0 or negative.")
                        return {"status": "ignored", "reason": "invalid_entry_price"}
                except (ValueError, TypeError):
                    print(f"[{ts}] ❌ Equity alert rejected: Entry price is invalid.")
                    return {"status": "ignored", "reason": "invalid_entry_price"}
                    
            if data.get("type") in ("BANDAR_AI", "BANDAR_AI_V3"):
                if "tier" in data:
                    message_text = format_idx_bandar_v2_alert(data)
                else:
                    message_text = format_idx_bandar_alert(data)
            elif data.get("type") in ("SCALP", "SCALP_V3"):
                if "tier" in data:
                    message_text = format_idx_scalp_v2_alert(data)
                else:
                    message_text = format_idx_scalp_alert(data)
            elif data.get("type") in ("US_SWING_V3", "US_BANDAR_V3", "US_STOCKS_SIGNAL"):
                message_text = format_us_v3_alert(data)
            elif data.get("type") == "FUTURES_SIGNAL":
                if FUTURES_FREEZE:
                    print(f"[{ts}] ❄️ Webhook ignored: FUTURES_SIGNAL is currently FROZEN.")
                    return {"status": "frozen"}
                if data.get("market") == "BINANCE_FUTURES":
                    event = data.get("event")
                    if event not in ALLOWED_FUTURES_EVENTS:
                        return {"status": "ignored", "reason": "non_actionable_event"}
                    if not validate_market_type(data):
                        return {"status": "ignored", "reason": "invalid_market_type"}
                    if not validate_direction(data):
                        return {"status": "ignored", "reason": "invalid_direction"}
                    if not validate_hit(data):
                        return {"status": "ignored", "reason": "invalid_hit"}
                    message_text = format_futures_message(data)
            elif "message" in data and "type" not in data:
                message_text = h(data["message"])
            else:
                message_text = f"🔔 <b>TradingView Alert</b>\n<pre>{h(data)}</pre>"
    except Exception as e:
        if isinstance(e, ValueError) and "Missing 'tier'" in str(e):
            print(f"[{ts}] ❌ Validation Error: {e}")
            return {"status": "error", "message": str(e)}

    # 2. Cek Plain Text (Algoritma Quantum, US v2, dll)
    if not message_text and body_str:
        if "XAU QUANTUM SIGNAL" in body_str:
            message_text = format_quantum_alert(body_str, "GOLD")
        elif "BTC QUANTUM SIGNAL" in body_str:
            message_text = format_quantum_alert(body_str, "BTC")
        elif "HEARTBEAT TEST" in body_str:
            message_text = f"💚 <b>HEARTBEAT OK</b>\n<pre>{body_str}</pre>\n\n✅ Pipeline: TradingView → Cloudflare → Webhook → Telegram"
        elif "US SWING HUNTER" in body_str:
            message_text = format_us_swing_alert(body_str)
        elif "US BANDAR AI" in body_str:
            message_text = format_us_bandar_alert(body_str)
        else:
            message_text = f"🔔 <b>Alert</b>\n<pre>{h(body_str[:500])}</pre>"

    # Cooldown & Data Extraction for Logging
    signal_val = ""
    ticker_val = ""
    score_val = ""
    tv_val = ""
    type_val = "UNKNOWN"
    
    if isinstance(data, dict):
        ticker_val = data.get("ticker", "UNKNOWN")
        signal_val = data.get("signal", "UNKNOWN")
        score_val = data.get("score", "-")
        tv_val = data.get("transaction_value", "-")
        type_val = data.get("type", "UNKNOWN")
        
        # P2-01: Cooldown
        key = f"{ticker_val}:{signal_val}"
        now = datetime.now().timestamp()
        if now - last_alert.get(key, 0) < COOLDOWN_SECONDS:
            print(f"[{ts}] ⏳ Skipping alert for {key} due to cooldown.")
            return {"status": "skipped", "reason": "cooldown"}
        last_alert[key] = now

    # 3. Kirim ke Telegram
    if message_text:
        sent = await send_to_telegram(message_text)
        if sent:
            print(f"[{ts}] ✅ Message forwarded to Telegram")
        else:
            print(f"[{ts}] ❌ Message failed to forward to Telegram")
            
        # P2-02: Logging
        telegram_status = "SUCCESS" if sent else "FAILED"
        log_alert(type_val, ticker_val, signal_val, score_val, tv_val, telegram_status)
        
        return {"status": "success" if sent else "telegram_failed", "received": True}
    else:
        print(f"[{ts}] ⚠️ No message generated from body")
        return {"status": "success", "received": True}


@app.get("/health")
async def health_check():
    return {
        "status": "Webhook is running smoothly!",
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
        "supported_alerts": [
            "XAU Quantum Signal (plain text)",
            "BTC Quantum Signal (plain text)",
            "US Swing Hunter V3 (JSON)",
            "US Bandar AI V3 (JSON)",
            "IDX Bandar AI V3 (JSON)",
            "IDX Scalping V3 (JSON)",
            "USD-M Autobot V3 (JSON)"
        ]
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)