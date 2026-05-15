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
# Format from Pine Script:
#   🚨 US SWING HUNTER
#   Ticker: TSLA
#   Price: $347.50 (+2.5%)
#   Signal: BREAKOUT BUY
#   RSI: 65.3 | R.Vol: 2.1x
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

    # Parse RSI value for sentiment context
    rsi_match = re.search(r"([\d.]+)", momentum)
    rsi_val = float(rsi_match.group(1)) if rsi_match else 50.0

    # Signal-based icon & sentiment
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

    # RSI context
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
# Format from Pine Script:
#   🔥 US BANDAR AI
#   Ticker: TSLA
#   Price: $347.50
#   Signal: SNIPER BUY
#   Flow: BIG ACCUM
#   Strength: 85.0%
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

    # Parse strength value
    str_match = re.search(r"([\d.]+)", strength)
    str_val = float(str_match.group(1)) if str_match else 0.0

    # Signal-based icon & sentiment
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

    # Flow icon
    flow_icons = {
        "BIG ACCUM": "🐋 Big Accumulation",
        "ACCUM": "🟢 Accumulation",
        "BIG DISTRIB": "🚨 Big Distribution",
        "DISTRIB": "🟠 Distribution",
        "NORMAL": "⚪ Normal"
    }
    flow_display = flow_icons.get(flow, f"⚪ {flow}")

    # Strength bar visual (5 blocks)
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

    # Visual indicators
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
    msg += f"⚡ Disiplin TP/SL · Scalp < 15 Menit\n"
    msg += f"#IDX_SCALP #{ticker}"
    return msg


# ============================================================================
# WEBHOOK HANDLER — Supports both JSON (legacy IDX) and plain text (US v2)
# ============================================================================
@app.post("/webhook")
async def handle_webhook(request: Request):
    content_type = request.headers.get("content-type", "")
    user_agent = request.headers.get("user-agent", "unknown")
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8", errors="replace").strip()

    # ── REQUEST LOGGING — see every incoming hit ─────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] 📨 WEBHOOK HIT | Content-Type: {content_type} | UA: {user_agent} | Body ({len(body_str)} chars): {body_str[:200]}")

    message_text = ""

    # ── Try JSON first (legacy IDX alerts) ──────────────────────────
    try:
        data = await request.json()

        if isinstance(data, dict):
            # IDX Bandar AI (JSON)
            if data.get("type") == "BANDAR_AI":
                message_text = format_idx_bandar_alert(data)

            # IDX Scalping (JSON)
            elif data.get("type") == "SCALP":
                message_text = format_idx_scalp_alert(data)

            # Legacy: just a "message" key
            elif "message" in data and "type" not in data:
                message_text = data["message"]

            else:
                message_text = f"🔔 <b>TradingView Alert</b>\n<pre>{data}</pre>"

    except Exception:
        # ── Not JSON → plain text alert (US v2) ─────────────────────
        pass

    # ── Parse plain text alerts from US v2 scripts ──────────────────
    if not message_text and body_str:
        if "HEARTBEAT TEST" in body_str:
            # Heartbeat — forward as confirmation
            message_text = f"💚 <b>HEARTBEAT OK</b>\n<pre>{body_str}</pre>\n\n✅ Pipeline: TradingView → Cloudflare → Webhook → Telegram"
        elif "US SWING HUNTER" in body_str:
            message_text = format_us_swing_alert(body_str)
        elif "US BANDAR AI" in body_str:
            message_text = format_us_bandar_alert(body_str)
        else:
            # Unknown plain text — forward as-is
            message_text = f"🔔 <b>Alert</b>\n<pre>{body_str[:500]}</pre>"

    if message_text:
        await send_to_telegram(message_text)
        print(f"[{ts}] ✅ Message forwarded to Telegram")
    else:
        print(f"[{ts}] ⚠️ No message generated from body")

    return {"status": "success", "received": True}


@app.get("/health")
async def health_check():
    return {
        "status": "Webhook is running!",
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
        "supported_alerts": [
            "US Swing Hunter v2 (plain text)",
            "US Bandar AI v2 (plain text)",
            "IDX Bandar AI (JSON legacy)",
            "IDX Scalping (JSON legacy)"
        ]
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
