import os
import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

futures_format_str = """# ============================================================================
# BINANCE FUTURES — JSON Alert Parser
# ============================================================================
def format_futures_message(data: dict) -> str:
    symbol = h(data.get("symbol", "UNKNOWN"))
    event = h(data.get("event", "UNKNOWN"))
    tf = h(data.get("tf", "15"))
    side = h(data.get("side", "NONE"))
    
    price_decimals = data.get("price_decimals", 4)
    def fmt_price(key):
        val = data.get(key)
        if f"{key}_text" in data and data[f"{key}_text"] != "-":
            return h(data[f"{key}_text"])
        if val is None or val == "-":
            return "-"
        return f"{float(val):.{price_decimals}f}"

    now = fmt_price("now")
    entry = fmt_price("entry")
    tp = fmt_price("tp")
    sl = fmt_price("sl")
    
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
    
    if "LONG" in side.upper() or "LONG" in event:
        icon = "??"
        title = "BINANCE FUTURES LONG"
        tp_sign = "+"
        sl_sign = "-"
        l_tp_sign = "+"
        l_risk_sign = "-"
    else:
        icon = "??"
        title = "BINANCE FUTURES SHORT"
        tp_sign = "-"
        sl_sign = "+"
        l_tp_sign = "+"
        l_risk_sign = "-"

    msg = f"{icon} <b>{title}</b>\\n\\n"
    msg += f"<b>Symbol</b> : {symbol}\\n"
    msg += f"<b>TF</b>     : {tf}m\\n"
    msg += f"<b>Event</b>  : {event}\\n\\n"
    
    msg += f"<b>NOW</b>    : {now}\\n"
    msg += f"<b>ENTRY</b>  : {entry}\\n"
    msg += f"<b>TP</b>     : {tp} ({tp_sign}{tp_pct:.2f}%)\\n"
    msg += f"<b>SL</b>     : {sl} ({sl_sign}{risk_pct:.2f}%)\\n"
    msg += f"<b>RR</b>     : {rr:.2f}\\n\\n"
    
    msg += f"<b>LEV</b>    : {lev}x\\n"
    msg += f"<b>L-TP</b>   : {l_tp_sign}{l_tp:.2f}%\\n"
    msg += f"<b>L-RISK</b> : {l_risk_sign}{l_risk:.2f}%\\n"
    msg += f"<b>MAX LEV</b>: {max_lev}x\\n"
    msg += f"<b>LIQ</b>    : {liq}\\n\\n"
    
    msg += f"<b>Score</b>  : {score}\\n"
    msg += f"<b>Flow</b>   : {flow}\\n"
    msg += f"<b>Signal</b> : {signal}\\n"
    
    return msg"""

# Replace format_usdm_v12_alert with format_futures_message
content = re.sub(
    r"# ============================================================================\n# USD-M AUTOBOT V12 — JSON Alert Parser(.*?)return msg",
    futures_format_str,
    content,
    flags=re.DOTALL
)

# Replace webhook handling for USDM_V12 with FUTURES_SIGNAL
webhook_handling_str = """            elif data.get("type") == "FUTURES_SIGNAL":
                if data.get("market") == "BINANCE_FUTURES":
                    event = data.get("event")
                    if event not in {"LONG_ENTRY", "SHORT_ENTRY", "TP_HIT", "SL_HIT"}:
                        return {"status": "ignored", "reason": "non_actionable_event"}
                    message_text = format_futures_message(data)"""

content = re.sub(
    r'            elif data.get\("type"\) == "USDM_V12":\s+message_text = format_usdm_v12_alert\(data\)',
    webhook_handling_str,
    content
)

content = content.replace('"USD-M Autobot V12 (JSON)"', '"Binance Futures V2 (JSON)"')

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated main.py")
