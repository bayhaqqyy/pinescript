from pathlib import Path
import os

def test_generated_scalp_has_transaction_value():
    script_dir = Path(os.path.join(os.path.dirname(__file__), "..", "tv_scripts"))
    files = list(script_dir.glob("scalping_v2_batch_*.pine"))
    assert files, "No generated scalping scripts found"
    
    for file in files:
        text = file.read_text(encoding="utf-8")
        assert "transaction_value" in text, f"{file.name} is missing transaction_value in alert JSON"
        assert "volume * c1" not in text, f"{file.name} should not have volume * c calculation outside request.security"

def test_generated_bandar_has_transaction_value():
    script_dir = Path(os.path.join(os.path.dirname(__file__), "..", "tv_scripts"))
    files = list(script_dir.glob("bandar_ai_v2_batch_*.pine"))
    assert files, "No generated bandar scripts found"
    
    for file in files:
        text = file.read_text(encoding="utf-8")
        assert "transaction_value" in text, f"{file.name} is missing transaction_value in alert JSON"
