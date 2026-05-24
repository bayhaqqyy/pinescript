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
