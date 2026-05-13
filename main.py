from fastapi import FastAPI, Request
import httpx
import os
import uvicorn

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_to_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Token/Chat ID is missing! Cannot send message.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            print(f"Message sent to Telegram successfully: {text[:30]}...")
        except Exception as e:
            print(f"Error sending to Telegram: {e}")

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
    except:
        return {"status": "error", "message": "Invalid JSON"}

    message_text = ""

    # 1. Handle old Bandar AI (Just "message")
    if "message" in data and "type" not in data:
        message_text = data["message"]
    
    # 2. Handle new Bandar AI Batch Screener
    elif data.get("type") == "BANDAR_AI":
        ticker = data.get("ticker", "UNKNOWN")
        signal = data.get("signal", "UNKNOWN")
        price = data.get("price", "0")
        
        icon = "🚀" if "BUY" in signal or "BULL" in signal else "⚠️"
        message_text = f"{icon} *{signal}* {icon}\n"
        message_text += f"🏢 *Emiten*: `{ticker}`\n"
        message_text += f"💰 *Harga*: Rp{price}\n"
        message_text += f"#BANDAR_AI"

    # 3. Handle Scalping Batch Screener
    elif data.get("type") == "SCALP":
        ticker = data.get("ticker", "UNKNOWN")
        action = data.get("action", "UNKNOWN")
        entry = data.get("entry", "0")
        tp = data.get("tp", "0")
        sl = data.get("sl", "0")
        bandar = data.get("bandar", "-")
        zona = data.get("zona", "-")
        
        # Color coding with emojis based on Action
        icon = "🔥" if action == "HAKA" else "💡"
        message_text = f"{icon} *SCALPING {action}* {icon}\n"
        message_text += f"🏢 *Emiten*: `{ticker}`\n"
        message_text += f"🎯 *Entry*: Rp{entry}\n"
        message_text += f"✅ *TP*: Rp{tp} (3%)\n"
        message_text += f"🛑 *SL*: Rp{sl}\n"
        message_text += f"📊 *Bandar*: {bandar} | *Zona*: {zona}\n"
        message_text += f"#SCALPING"
    
    else:
        # Fallback if TradingView sends unknown JSON format
        message_text = f"🔔 *TradingView Alert*\n```json\n{data}\n```"

    if message_text:
        await send_to_telegram(message_text)

    return {"status": "success", "received": True}

@app.get("/health")
async def health_check():
    return {"status": "Webhook is running!", "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 443))
    uvicorn.run(app, host="0.0.0.0", port=port)
