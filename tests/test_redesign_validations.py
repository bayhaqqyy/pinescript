import pytest
from httpx import AsyncClient, ASGITransport
from main import app, validate_direction, validate_hit, validate_market_type
import main

# Disable futures freeze during tests to make sure they reach validations
main.FUTURES_FREEZE = False

def test_direction_validation_long():
    # Long valid: TP > Entry and SL < Entry
    assert validate_direction({"side": "LONG", "entry": 100, "tp": 105, "sl": 95}) is True
    # Long invalid: TP <= Entry
    assert validate_direction({"side": "LONG", "entry": 100, "tp": 99, "sl": 95}) is False
    # Long invalid: SL >= Entry
    assert validate_direction({"side": "LONG", "entry": 100, "tp": 105, "sl": 101}) is False

def test_direction_validation_short():
    # Short valid: TP < Entry and SL > Entry
    assert validate_direction({"side": "SHORT", "entry": 100, "tp": 95, "sl": 105}) is True
    # Short invalid: TP >= Entry
    assert validate_direction({"side": "SHORT", "entry": 100, "tp": 101, "sl": 105}) is False
    # Short invalid: SL <= Entry
    assert validate_direction({"side": "SHORT", "entry": 100, "tp": 95, "sl": 99}) is False

def test_hit_validation_long_tp():
    # LONG_TP_HIT valid: now >= tp
    assert validate_hit({"event": "LONG_TP_HIT", "now": 106, "tp": 105, "sl": 95}) is True
    # LONG_TP_HIT invalid: now < tp
    assert validate_hit({"event": "LONG_TP_HIT", "now": 104, "tp": 105, "sl": 95}) is False

def test_hit_validation_long_sl():
    # LONG_SL_HIT valid: now <= sl
    assert validate_hit({"event": "LONG_SL_HIT", "now": 94, "tp": 105, "sl": 95}) is True
    # LONG_SL_HIT invalid: now > sl
    assert validate_hit({"event": "LONG_SL_HIT", "now": 96, "tp": 105, "sl": 95}) is False

def test_hit_validation_short_tp():
    # SHORT_TP_HIT valid: now <= tp
    assert validate_hit({"event": "SHORT_TP_HIT", "now": 94, "tp": 95, "sl": 105}) is True
    # SHORT_TP_HIT invalid: now > tp
    assert validate_hit({"event": "SHORT_TP_HIT", "now": 96, "tp": 95, "sl": 105}) is False

def test_hit_validation_short_sl():
    # SHORT_SL_HIT valid: now >= sl
    assert validate_hit({"event": "SHORT_SL_HIT", "now": 106, "tp": 95, "sl": 105}) is True
    # SHORT_SL_HIT invalid: now < sl
    assert validate_hit({"event": "SHORT_SL_HIT", "now": 104, "tp": 95, "sl": 105}) is False

def test_market_type_validation():
    # Equity/IDX must NOT allow SHORT entries
    assert validate_market_type({"market": "IDX", "event": "SHORT_ENTRY", "side": "SHORT"}) is False
    assert validate_market_type({"market": "BINANCE_FUTURES", "event": "SHORT_ENTRY", "side": "SHORT"}) is True

@pytest.mark.asyncio
async def test_webhook_reject_invalid_direction():
    # Mock webhook secret
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid long direction tp1 <= entry_avg
        payload = {
            "type": "FUTURES_SIGNAL",
            "market": "BINANCE_FUTURES",
            "version": "4.0",
            "event": "LONG_ENTRY",
            "side": "LONG",
            "symbol": "GRASSUSDT",
            "tf_trigger": "5",
            "tf_setup": "15",
            "tf_zone": "60",
            "tf_bias": "240",
            "entry_low": 0.49,
            "entry_high": 0.51,
            "entry_avg": 0.50,
            "tp1": 0.45,
            "tp2": 0.55,
            "tp3": 0.60,
            "sl": 0.48,
            "mode": "DEMAND_REJECTION",
            "status": "VALID_LONG",
            "score": 85,
            "risk_pct": 1.13,
            "recommended_leverage": 17,
            "risk_label": "SAFE",
            "bias_4h": "BULLISH",
            "zone_1h": "DEMAND",
            "rsi": 55.4,
            "rvol": 1.45,
            "bar_high": 0.52,
            "bar_low": 0.49
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "ignored"
        assert res_data["reason"] == "invalid_direction"

@pytest.mark.asyncio
async def test_webhook_reject_invalid_hit():
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid hit: LONG_TP1_HIT but now < tp1
        payload = {
            "type": "FUTURES_SIGNAL",
            "market": "BINANCE_FUTURES",
            "version": "4.0",
            "event": "LONG_TP1_HIT",
            "side": "LONG",
            "symbol": "GRASSUSDT",
            "tf_trigger": "5",
            "tf_setup": "15",
            "tf_zone": "60",
            "tf_bias": "240",
            "now": 0.52,
            "entry_low": 0.49,
            "entry_high": 0.51,
            "entry_avg": 0.50,
            "tp1": 0.55,
            "tp2": 0.60,
            "tp3": 0.65,
            "sl": 0.48,
            "mode": "DEMAND_REJECTION",
            "status": "VALID_LONG",
            "score": 85,
            "risk_pct": 1.13,
            "recommended_leverage": 17,
            "risk_label": "SAFE",
            "bias_4h": "BULLISH",
            "zone_1h": "DEMAND",
            "rsi": 55.4,
            "rvol": 1.45,
            "bar_high": 0.53,
            "bar_low": 0.51
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "ignored"
        assert res_data["reason"] == "invalid_hit"

@pytest.mark.asyncio
async def test_webhook_reject_equity_short():
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reject IDX short signal
        payload = {
            "type": "BANDAR_AI",
            "market": "IDX",
            "ticker": "BBRI",
            "side": "SHORT",
            "action": "SHORT",
            "signal": "SHORT"
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "ignored"
        assert res_data["reason"] == "invalid_equity_event"

@pytest.mark.asyncio
async def test_webhook_reject_equity_unknown_wait():
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reject unknown/wait action/signal
        payload = {
            "type": "SCALP",
            "market": "IDX",
            "ticker": "GPRA",
            "action": "UNKNOWN",
            "entry": 99,
            "tp": 0,
            "sl": 98
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "ignored"
        assert res_data["reason"] == "non_actionable_equity_event"

@pytest.mark.asyncio
async def test_webhook_reject_equity_invalid_price():
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reject zero/invalid entry price
        payload = {
            "type": "SCALP",
            "market": "IDX",
            "ticker": "RICY",
            "action": "BUY",
            "entry": 0,
            "tp": 78,
            "sl": 75
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["reason"] == "invalid_entry_price"

def test_direction_validation_v2():
    # Long valid: TP1 > Entry Avg and SL < Entry Avg
    assert validate_direction({"version": "2.0", "side": "LONG", "entry_avg": 100, "tp1": 105, "sl": 95}) is True
    # Long invalid: TP1 <= Entry Avg
    assert validate_direction({"version": "2.0", "side": "LONG", "entry_avg": 100, "tp1": 99, "sl": 95}) is False
    # Short valid: TP1 < Entry Avg and SL > Entry Avg
    assert validate_direction({"version": "2.0", "side": "SHORT", "entry_avg": 100, "tp1": 95, "sl": 105}) is True

def test_hit_validation_v2():
    # LONG_TP1_HIT valid: now >= tp1
    assert validate_hit({"version": "2.0", "event": "LONG_TP1_HIT", "now": 105, "tp1": 105, "sl": 95}) is True
    assert validate_hit({"version": "2.0", "event": "LONG_TP1_HIT", "now": 104, "tp1": 105, "sl": 95}) is False
    
    # SHORT_TP2_HIT valid: now <= tp2
    assert validate_hit({"version": "2.0", "event": "SHORT_TP2_HIT", "now": 90, "tp1": 95, "tp2": 90, "tp3": 85, "sl": 105}) is True
    assert validate_hit({"version": "2.0", "event": "SHORT_TP2_HIT", "now": 91, "tp1": 95, "tp2": 90, "tp3": 85, "sl": 105}) is False

def test_format_futures_message_v2():
    from main import format_futures_message
    
    data = {
        "market": "BINANCE_FUTURES",
        "type": "FUTURES_SIGNAL",
        "version": "2.0",
        "event": "SHORT_ENTRY",
        "symbol": "PORTALUSDT",
        "side": "SHORT",
        "tf_trigger": "15",
        "tf_zone": "60",
        "tf_bias": "240",
        "mode": "BREAKDOWN_RETEST",
        "status": "VALID_SHORT",
        "now": 0.0248,
        "entry_low": 0.0245,
        "entry_high": 0.0260,
        "entry_avg": 0.02525,
        "tp1": 0.0230,
        "tp2": 0.0215,
        "tp3": 0.0200,
        "sl": 0.0275,
        "risk_pct": 8.91,
        "rr_tp1": 0.89,
        "rr_tp2": 1.48,
        "rr_tp3": 2.08,
        "input_leverage": 10,
        "recommended_leverage": 3,
        "lev_risk_pct": 89.1,
        "risk_label": "RISKY_PLAN",
        "score": 82,
        "bias_4h": "BEARISH",
        "bias_strength_4h": "NORMAL",
        "zone_1h": "SUPPLY",
        "zone_score_1h": 78,
        "trigger_15m": "BEARISH_CONFIRMATION",
        "rsi": 42.5,
        "rvol": 1.452
    }
    
    msg = format_futures_message(data)
    assert "PORTALUSDT" in msg
    assert "SHORT" in msg
    assert "BREAKDOWN_RETEST" in msg
    assert "0.0245 - 0.0260" in msg
    assert "0.0230" in msg
    assert "0.0215" in msg
    assert "0.0200" in msg
    assert "0.0275" in msg
    assert "RISKY_PLAN" in msg
    assert "Rec: 3x" in msg
    assert "Score" in msg
    assert "82" in msg
    assert "BEARISH" in msg
    assert "SUPPLY" in msg
    assert "WARNING" in msg

def test_format_futures_message_legacy():
    from main import format_futures_message
    
    data = {
        "market": "BINANCE_FUTURES",
        "type": "FUTURES_SIGNAL",
        "event": "SHORT_SL_HIT",
        "symbol": "MRVLUSDT",
        "side": "SHORT",
        "tf": "15",
        "now": 303.76,
        "entry": 298.8,
        "tp": 291.7250969659,
        "sl": 302.92702
    }
    
    msg = format_futures_message(data)
    assert "MRVLUSDT" in msg
    # The formatted entry_low/entry_high/entry_avg should fallback to entry (298.8000)
    assert "298.8000 - 298.8000" in msg
    assert "Avg: 298.8000" in msg
    # The tp1 should fallback to tp (291.7251)
    assert "291.7251" in msg
    # Risk calculation fallback
    # abs(298.8 - 302.92702) / 298.8 * 100 = 1.38%
    assert "1.38%" in msg
    # R:R calculation fallback
    # abs(298.8 - 291.7250969659) / abs(302.92702 - 298.8) = 7.074903 / 4.12702 = 1.714
    # Wait, 1.714 or 1.71
    assert "1.71" in msg


def test_validate_futures_payload_valid_v4():
    from main import validate_futures_payload
    payload = {
        "market": "BINANCE_FUTURES",
        "type": "FUTURES_SIGNAL",
        "version": "4.0",
        "event": "LONG_ENTRY",
        "symbol": "BEUSDT",
        "side": "LONG",
        "entry_low": 247.40,
        "entry_high": 248.20,
        "entry_avg": 247.80,
        "tp1": 250.0,
        "tp2": 252.0,
        "tp3": 255.0,
        "sl": 245.0,
        "mode": "DEMAND_REJECTION",
        "status": "VALID_LONG",
        "score": 85,
        "risk_pct": 1.13,
        "recommended_leverage": 17,
        "risk_label": "SAFE",
        "bias_4h": "BULLISH",
        "zone_1h": "DEMAND",
        "rsi": 55.4,
        "rvol": 1.45,
        "bar_high": 248.50,
        "bar_low": 247.10
    }
    assert validate_futures_payload(payload) is True

def test_validate_futures_payload_missing_field():
    from main import validate_futures_payload
    payload = {
        "market": "BINANCE_FUTURES",
        "type": "FUTURES_SIGNAL",
        "version": "4.0",
        "event": "LONG_ENTRY",
        "symbol": "BEUSDT",
        "side": "LONG",
        # entry_low missing
        "entry_high": 248.20,
        "entry_avg": 247.80,
        "tp1": 250.0,
        "tp2": 252.0,
        "tp3": 255.0,
        "sl": 245.0,
        "mode": "DEMAND_REJECTION",
        "status": "VALID_LONG",
        "score": 85,
        "risk_pct": 1.13,
        "recommended_leverage": 17,
        "risk_label": "SAFE",
        "bias_4h": "BULLISH",
        "zone_1h": "DEMAND",
        "rsi": 55.4,
        "rvol": 1.45,
        "bar_high": 248.50,
        "bar_low": 247.10
    }
    assert validate_futures_payload(payload) is False

def test_validate_futures_payload_mode_none():
    from main import validate_futures_payload
    payload = {
        "market": "BINANCE_FUTURES",
        "type": "FUTURES_SIGNAL",
        "version": "4.0",
        "event": "LONG_ENTRY",
        "symbol": "BEUSDT",
        "side": "LONG",
        "entry_low": 247.4,
        "entry_high": 248.20,
        "entry_avg": 247.80,
        "tp1": 250.0,
        "tp2": 252.0,
        "tp3": 255.0,
        "sl": 245.0,
        "mode": "NONE",
        "status": "VALID_LONG",
        "score": 85,
        "risk_pct": 1.13,
        "recommended_leverage": 17,
        "risk_label": "SAFE",
        "bias_4h": "BULLISH",
        "zone_1h": "DEMAND",
        "rsi": 55.4,
        "rvol": 1.45,
        "bar_high": 248.50,
        "bar_low": 247.10
    }
    assert validate_futures_payload(payload) is False

def test_validate_futures_payload_low_score():
    from main import validate_futures_payload
    payload = {
        "market": "BINANCE_FUTURES",
        "type": "FUTURES_SIGNAL",
        "version": "4.0",
        "event": "LONG_ENTRY",
        "symbol": "BEUSDT",
        "side": "LONG",
        "entry_low": 247.4,
        "entry_high": 248.20,
        "entry_avg": 247.80,
        "tp1": 250.0,
        "tp2": 252.0,
        "tp3": 255.0,
        "sl": 245.0,
        "mode": "DEMAND_REJECTION",
        "status": "VALID_LONG",
        "score": 79, # below 80
        "risk_pct": 1.13,
        "recommended_leverage": 17,
        "risk_label": "SAFE",
        "bias_4h": "BULLISH",
        "zone_1h": "DEMAND",
        "rsi": 55.4,
        "rvol": 1.45,
        "bar_high": 248.50,
        "bar_low": 247.10
    }
    assert validate_futures_payload(payload) is False

def test_validate_futures_payload_risky():
    from main import validate_futures_payload
    payload = {
        "market": "BINANCE_FUTURES",
        "type": "FUTURES_SIGNAL",
        "version": "4.0",
        "event": "LONG_ENTRY",
        "symbol": "BEUSDT",
        "side": "LONG",
        "entry_low": 247.4,
        "entry_high": 248.20,
        "entry_avg": 247.80,
        "tp1": 250.0,
        "tp2": 252.0,
        "tp3": 255.0,
        "sl": 245.0,
        "mode": "DEMAND_REJECTION",
        "status": "VALID_LONG",
        "score": 85,
        "risk_pct": 1.13,
        "recommended_leverage": 17,
        "risk_label": "RISKY_PLAN", # rejected
        "bias_4h": "BULLISH",
        "zone_1h": "DEMAND",
        "rsi": 55.4,
        "rvol": 1.45,
        "bar_high": 248.50,
        "bar_low": 247.10
    }
    assert validate_futures_payload(payload) is False

def test_format_futures_message_v4_full():
    from main import format_futures_message
    payload = {
        "market": "BINANCE_FUTURES",
        "type": "FUTURES_SIGNAL",
        "version": "4.0",
        "event": "LONG_ENTRY",
        "symbol": "BEUSDT",
        "side": "LONG",
        "tf_trigger": "5",
        "tf_setup": "15",
        "tf_zone": "60",
        "tf_bias": "240",
        "entry_low": 247.40,
        "entry_high": 248.20,
        "entry_avg": 247.80,
        "tp1": 250.0,
        "tp2": 252.0,
        "tp3": 255.0,
        "sl": 245.0,
        "mode": "DEMAND_REJECTION",
        "status": "VALID_LONG",
        "score": 85,
        "risk_pct": 1.13,
        "recommended_leverage": 17,
        "risk_label": "SAFE",
        "bias_4h": "BULLISH",
        "bias_strength_4h": "NORMAL",
        "zone_1h": "DEMAND",
        "zone_score_1h": 80,
        "trigger_5m": "BULLISH_REJECTION",
        "setup_15m": "RETEST_STRUCTURE",
        "rsi": 55.4,
        "rvol": 1.45,
        "bar_high": 248.50,
        "bar_low": 247.10
    }
    msg = format_futures_message(payload)
    assert "BEUSDT" in msg
    assert "5m / 15m / 60m / 240m" in msg
    assert "VALID_LONG" in msg
    assert "DEMAND_REJECTION" in msg
    assert "Rec: 17x" in msg
    assert "Trigger 5m" in msg
    assert "BULLISH_REJECTION" in msg
    assert "Setup 15m" in msg
    assert "RETEST_STRUCTURE" in msg
    assert "145.0%" in msg
    assert "📊 <b>BAR</b>" in msg
    assert "H 248.50 / L 247.10" in msg or "H 248.5000 / L 247.1000" in msg

@pytest.mark.asyncio
async def test_wait_retest_filter_webhook():
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Status WAIT_RETEST_LONG should be ignored from Telegram forwarding (for non-entry events)
        payload = {
            "market": "BINANCE_FUTURES",
            "type": "FUTURES_SIGNAL",
            "version": "4.0",
            "event": "LONG_TP1_HIT",
            "symbol": "BEUSDT",
            "side": "LONG",
            "tf_trigger": "5",
            "tf_setup": "15",
            "tf_zone": "60",
            "tf_bias": "240",
            "entry_low": 247.40,
            "entry_high": 248.20,
            "entry_avg": 247.80,
            "tp1": 250.0,
            "tp2": 252.0,
            "tp3": 255.0,
            "sl": 245.0,
            "mode": "DEMAND_REJECTION",
            "status": "WAIT_RETEST_LONG",
            "score": 85,
            "risk_pct": 1.13,
            "recommended_leverage": 17,
            "risk_label": "SAFE",
            "bias_4h": "BULLISH",
            "bias_strength_4h": "NORMAL",
            "zone_1h": "DEMAND",
            "zone_score_1h": 80,
            "rsi": 55.4,
            "rvol": 1.45,
            "bar_high": 251.00,
            "bar_low": 246.00
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res = response.json()
        assert res["status"] == "ignored"
        assert res["reason"] == "wait_retest_ignored"

@pytest.mark.asyncio
async def test_entry_wait_retest_guard_webhook():
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Guard should reject entry events with WAIT_RETEST status
        payload = {
            "market": "BINANCE_FUTURES",
            "type": "FUTURES_SIGNAL",
            "version": "4.0",
            "event": "LONG_ENTRY",
            "symbol": "BEUSDT",
            "side": "LONG",
            "tf_trigger": "5",
            "tf_setup": "15",
            "tf_zone": "60",
            "tf_bias": "240",
            "entry_low": 247.40,
            "entry_high": 248.20,
            "entry_avg": 247.80,
            "tp1": 250.0,
            "tp2": 252.0,
            "tp3": 255.0,
            "sl": 245.0,
            "mode": "DEMAND_REJECTION",
            "status": "WAIT_RETEST_LONG",
            "score": 85,
            "risk_pct": 1.13,
            "recommended_leverage": 17,
            "risk_label": "SAFE",
            "bias_4h": "BULLISH",
            "bias_strength_4h": "NORMAL",
            "zone_1h": "DEMAND",
            "zone_score_1h": 80,
            "rsi": 55.4,
            "rvol": 1.45,
            "bar_high": 248.50,
            "bar_low": 247.10
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res = response.json()
        assert res["status"] == "ignored"
        assert res["reason"] == "entry_status_wait_retest_invalid"

@pytest.mark.asyncio
async def test_webhook_reject_legacy_payload():
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Legacy version 3.0
        payload = {
            "market": "BINANCE_FUTURES",
            "type": "FUTURES_SIGNAL",
            "version": "3.0",
            "event": "LONG_ENTRY",
            "symbol": "BEUSDT",
            "side": "LONG",
            "tf_trigger": "15",
            "entry_low": 247.40,
            "entry_high": 248.20,
            "entry_avg": 247.80,
            "tp1": 250.0,
            "tp2": 252.0,
            "tp3": 255.0,
            "sl": 245.0,
            "mode": "DEMAND_REJECTION",
            "status": "VALID_LONG",
            "score": 85,
            "risk_pct": 1.13,
            "recommended_leverage": 17,
            "risk_label": "SAFE",
            "bias_4h": "BULLISH",
            "zone_1h": "DEMAND",
            "rsi": 55.4,
            "rvol": 1.45
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res = response.json()
        assert res["status"] == "ignored"
        assert res["reason"] == "legacy_futures_payload"


@pytest.mark.asyncio
async def test_webhook_reject_missing_risk_label():
    main.WEBHOOK_SECRET = ""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing risk_label
        payload = {
            "market": "BINANCE_FUTURES",
            "type": "FUTURES_SIGNAL",
            "version": "4.0",
            "event": "LONG_ENTRY",
            "symbol": "GRASSUSDT",
            "side": "LONG",
            "tf_trigger": "5",
            "tf_setup": "15",
            "tf_zone": "60",
            "tf_bias": "240",
            "entry_low": 0.49,
            "entry_high": 0.51,
            "entry_avg": 0.50,
            "tp1": 0.55,
            "tp2": 0.60,
            "tp3": 0.65,
            "sl": 0.48,
            "mode": "DEMAND_REJECTION",
            "status": "VALID_LONG",
            "score": 85,
            "risk_pct": 1.13,
            "recommended_leverage": 17,
            "bias_4h": "BULLISH",
            "zone_1h": "DEMAND",
            "rsi": 55.4,
            "rvol": 1.45,
            "bar_high": 0.53,
            "bar_low": 0.49
        }
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        res = response.json()
        assert res["status"] == "ignored"
        assert res["reason"] == "invalid_futures_payload"





