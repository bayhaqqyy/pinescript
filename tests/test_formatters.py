def test_idx_scalp_v2_transaction_value():
    from main import format_idx_scalp_v2_alert

    msg = format_idx_scalp_v2_alert({
        "type": "SCALP",
        "tier": "SCALP_GORENGAN",
        "ticker": "TEST",
        "signal": "HAKA",
        "entry": 100,
        "tp1": 105,
        "tp2": 110,
        "sl": 95,
        "transaction_value": 1_250_000_000,
        "holding_hint": "intraday"
    })

    assert "Rp1.2B" in msg or "Rp1.3B" in msg
    assert "TEST" in msg

def test_html_escape_in_alert():
    from main import format_idx_scalp_v2_alert

    msg = format_idx_scalp_v2_alert({
        "type": "SCALP",
        "tier": "SCALP_GORENGAN",
        "ticker": "<script>",
        "signal": "HAKA<b>",
        "entry": 100,
        "tp1": 105,
        "tp2": 110,
        "sl": 95,
        "transaction_value": 500_000_000,
    })

    assert "<script>" not in msg
    assert "&lt;script&gt;" in msg


def test_us_v3_alert_formatting():
    from main import format_us_v3_alert

    data = {
        "type": "US_SWING_V3",
        "ticker": "AAPL",
        "tf": "15",
        "signal": "BREAKOUT BUY",
        "action": "BUY>180.50",
        "entry": 180.50,
        "tp1": 195.00,
        "tp2": 210.00,
        "sl": 172.00,
        "transaction_value": 5000000,
        "score": 85,
        "support": 170.00,
        "resistance": 185.00,
        "bandar": "BULL ABSORB",
        "zona": "MID",
        "holding_hint": "swing 2-10 days"
    }

    msg = format_us_v3_alert(data)

    assert "US SWING HUNTER V3" in msg
    assert "AAPL" in msg
    assert "180.50" in msg
    assert "195.00" in msg
    assert "210.00" in msg
    assert "172.00" in msg
    assert "$5,000,000" in msg or "5000000" in msg
    assert "BULL ABSORB" in msg

