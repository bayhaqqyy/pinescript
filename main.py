from fastapi import FastAPI, Request
import httpx
import os
import re
import uvicorn
from datetime import datetime, timezone

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ============================================================================
# TELEGRAM SENDER
# ============================================================================
async def send_to_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Token/Chat ID is missing! Cannot send message.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                print(f"Telegram API Error: {response.text}")
            response.raise_for_status()
            print(f"Message sent to Telegram successfully: {text[:50]}...")
        except Exception as e:
            print(f"Error sending to Telegram: {e}")


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

    ticker = data.get("ticker", "???")
    price = data.get("price", "$0")
    signal = data.get("signal", "UNKNOWN")
    momentum = data.get("momentum", "-")

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

    ticker = data.get("ticker", "???")
    price = data.get("price", "$0")
    signal = data.get("signal", "UNKNOWN")
    flow = data.get("flow", "NORMAL")
    strength = data.get("strength", "0%")

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

    ticker = data.get("ticker") or "???"
    context = data.get("context") or "???"

    action_raw = data.get("action", "")
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
    ticker = data.get("ticker", "UNKNOWN")
    signal = data.get("signal", "UNKNOWN")
    price = data.get("price", "0")

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
    ticker = data.get("ticker", "UNKNOWN")
    action = data.get("action", "UNKNOWN")
    entry = data.get("entry", "0")
    tp = data.get("tp", "0")
    sl = data.get("sl", "0")
    bandar = data.get("bandar", "-")
    zona = data.get("zona", "-")

    action_upper = action.upper()
    if action_upper == "HAKA":
        icon = "🔥"
        sentiment = "Momentum HAKA super cepat terdeteksi! Siap pantau bid-offer."
    elif action_upper == "HAKI":
        icon = "⚠️"
        sentiment = "Tekanan jual HAKI tinggi, amankan profit / ketat SL."
    else:
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
        
    ticker = str(data.get("ticker", "UNKNOWN")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    signal = str(data.get("signal", "UNKNOWN")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
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
        
    ticker = str(data.get("ticker", "UNKNOWN")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    signal = str(data.get("signal", "UNKNOWN")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
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
# USD-M AUTOBOT V12 — JSON Alert Parser
# ============================================================================
def format_usdm_v12_alert(data: dict) -> str:
    ticker = str(data.get("ticker", "UNKNOWN")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    signal = str(data.get("signal", "UNKNOWN")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    side = str(data.get("side", "NONE")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    batch = str(data.get("batch", "?"))
    entry = data.get("entry", 0)
    tp = data.get("tp", 0)
    sl = data.get("sl", 0)
    lev = data.get("lev", 1)
    qty = data.get("qty", 0)

    signal_upper = signal.upper()
    if signal_upper == "LONG":
        icon = "🟢"
        sentiment = "High-Speed EMA Crossover: LONG 🚀"
    elif signal_upper == "SHORT":
        icon = "🔴"
        sentiment = "High-Speed EMA Crossover: SHORT 🔻"
    else:
        icon = "⚡"
        sentiment = "Autobot V12 Signal"

    msg = f"{icon} <b>USD-M AUTOBOT V12</b> {icon}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🪙 <b>Pair</b>: <code>{ticker}</code> (Batch {batch})\n"
    msg += f"⚡ <b>Signal</b>: <b>{signal}</b> / {side}\n"
    msg += f"⚙️ <b>Leverage</b>: {lev}x\n"
    msg += f"📦 <b>Qty</b>: {qty}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🎯 <b>Entry</b>: {entry}\n"
    msg += f"✅ <b>TP</b>: {tp}\n"
    msg += f"🛑 <b>SL</b>: {sl}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💡 <i>{sentiment}</i>\n"
    msg += f"⏰ TF 5m · Binance Futures\n"
    msg += f"#USDM_V12 #{ticker.replace('.P', '')}"
    return msg


# ============================================================================
# WEBHOOK HANDLER
# ============================================================================
@app.post("/webhook")
async def handle_webhook(request: Request):
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
            if data.get("type") == "BANDAR_AI":
                if "tier" in data:
                    message_text = format_idx_bandar_v2_alert(data)
                else:
                    message_text = format_idx_bandar_alert(data) # Legacy not found, maybe handle or fallback
            elif data.get("type") == "SCALP":
                if "tier" in data:
                    message_text = format_idx_scalp_v2_alert(data)
                else:
                    message_text = format_idx_scalp_alert(data) # Legacy not found
            elif data.get("type") == "USDM_V12":
                message_text = format_usdm_v12_alert(data)
            elif "message" in data and "type" not in data:
                message_text = data["message"]
            else:
                message_text = f"🔔 <b>TradingView Alert</b>\n<pre>{data}</pre>"
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
            message_text = f"🔔 <b>Alert</b>\n<pre>{body_str[:500]}</pre>"

    # 3. Kirim ke Telegram
    if message_text:
        await send_to_telegram(message_text)
        print(f"[{ts}] ✅ Message forwarded to Telegram")
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
            "US Swing Hunter v2 (plain text)",
            "US Bandar AI v2 (plain text)",
            "IDX Bandar AI V2 (JSON)",
            "IDX Scalping V2 (JSON)",
            "USD-M Autobot V12 (JSON)"
        ]
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)