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
        # Invalid long direction TP <= Entry
        payload = {
            "type": "FUTURES_SIGNAL",
            "market": "BINANCE_FUTURES",
            "event": "LONG_ENTRY",
            "side": "LONG",
            "symbol": "GRASSUSDT",
            "entry": 0.5,
            "tp": 0.45,
            "sl": 0.48
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
        # Invalid hit: LONG_TP_HIT but now < tp
        payload = {
            "type": "FUTURES_SIGNAL",
            "market": "BINANCE_FUTURES",
            "event": "LONG_TP_HIT",
            "side": "LONG",
            "symbol": "GRASSUSDT",
            "now": 0.52,
            "entry": 0.5,
            "tp": 0.55,
            "sl": 0.48
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
