"""
Filter stock lists for Scalping and Bandar AI strategies.
- Scalping: ALL volatile stocks, only remove CONFIRMED FCA
- Bandar AI: Mid-cap swing trading candidates
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# FCA BLACKLIST — HANYA saham yang BENAR-BENAR MASIH di Papan Pemantauan Khusus
# Per Mei 2026. Yang sudah keluar FCA (seperti BNBR) TIDAK dimasukkan.
# ============================================================================
CONFIRMED_FCA = {
    # Confirmed masih FCA / harga < Rp51 (kriteria otomatis PPK)
    "TAXI",   # Rp16 — Confirmed FCA
    "BTEK",   # Rp13 — Confirmed FCA
    "KREN",   # Rp16
    "HADE",   # Rp18
    "WSBP",   # Rp18
    "PPRO",   # Rp20
    "BAPI",   # Rp23
    "IKAI",   # Rp24
    "BEKS",   # Rp26
    "MARI",   # Rp30
    "PURA",   # Rp31
    "PBRX",   # Rp35
    "PCAR",   # Rp36
    "DIGI",   # Rp38
}

# ============================================================================
# LOAD DATA
# ============================================================================
with open(os.path.join(SCRIPT_DIR, "idx_below_1000.json"), "r") as f:
    raw_data = json.load(f)

all_stocks = raw_data["stocks"]
date_str = raw_data["date"]

# ============================================================================
# SCALPING — Semua saham volatile, hanya buang confirmed FCA
# Range: Rp50-1000 (semua yang ada di list)
# ============================================================================
scalping_picks = [
    s for s in all_stocks
    if s["ticker"] not in CONFIRMED_FCA
    and s["price"] >= 50  # Minimal Rp50 (di bawah ini spread terlalu lebar)
]
scalping_picks.sort(key=lambda x: x["price"], reverse=True)

# Create batches of 10
scalp_batches = {}
labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
for i in range(0, len(scalping_picks), 10):
    idx = i // 10
    if idx >= len(labels):
        break
    scalp_batches[f"batch_{labels[idx].lower()}"] = [s["ticker"] for s in scalping_picks[i:i+10]]

scalp_result = {
    "date": date_str,
    "strategy": "SCALPING",
    "description": "Saham IDX volatile untuk scalping intraday. TF: 1 menit. Termasuk saham gorengan yang liquid.",
    "total": len(scalping_picks),
    "batches": len(scalp_batches),
    "stocks": scalping_picks,
    "batch_groups": scalp_batches
}

scalp_path = os.path.join(SCRIPT_DIR, "scalping_stocks.json")
with open(scalp_path, "w", encoding="utf-8") as f:
    json.dump(scalp_result, f, indent=2, ensure_ascii=False)

print(f"\n=== SCALPING ===")
print(f"  Total: {len(scalping_picks)} emiten (removed {len(all_stocks) - len(scalping_picks)} FCA)")
print(f"  Batches: {len(scalp_batches)}")
print(f"  Range: Rp{scalping_picks[-1]['price']:.0f} - Rp{scalping_picks[0]['price']:.0f}")

# ============================================================================
# BANDAR AI — Mid-cap untuk SWING TRADING
# Bukan LQ45 blue chip, tapi saham yang punya potensi swing
# ============================================================================
bandar_stocks = [
    # Mid-cap property — sering swing
    {"ticker": "SMRA", "price": 322, "sector": "Property"},
    {"ticker": "PWON", "price": 310, "sector": "Property"},
    {"ticker": "CTRA", "price": 680, "sector": "Property"},
    {"ticker": "BSDE", "price": 755, "sector": "Property"},
    {"ticker": "APLN", "price": 180, "sector": "Property"},
    {"ticker": "KIJA", "price": 175, "sector": "Property"},
    {"ticker": "LPKR", "price": 80, "sector": "Property"},
    {"ticker": "ASRI", "price": 128, "sector": "Property"},
    {"ticker": "BKSL", "price": 102, "sector": "Property"},
    {"ticker": "DILD", "price": 125, "sector": "Property"},

    # Mining / komoditas — volatile, swing bagus
    {"ticker": "BUMI", "price": 214, "sector": "Mining"},
    {"ticker": "BRMS", "price": 755, "sector": "Mining"},
    {"ticker": "DEWA", "price": 466, "sector": "Mining"},
    {"ticker": "ANTM", "price": 1400, "sector": "Mining"},
    {"ticker": "HRUM", "price": 910, "sector": "Mining"},
    {"ticker": "MBMA", "price": 605, "sector": "Mining"},
    {"ticker": "TOBA", "price": 570, "sector": "Mining"},
    {"ticker": "ESSA", "price": 805, "sector": "Energy"},
    {"ticker": "ELSA", "price": 710, "sector": "Energy"},
    {"ticker": "MEDC", "price": 1200, "sector": "Energy"},

    # Konstruksi / infra — BUMN, sering ada momentum
    {"ticker": "PTPP", "price": 244, "sector": "Construction"},
    {"ticker": "ADHI", "price": 200, "sector": "Construction"},
    {"ticker": "WIKA", "price": 300, "sector": "Construction"},
    {"ticker": "WSKT", "price": 200, "sector": "Construction"},
    {"ticker": "WTON", "price": 88, "sector": "Construction"},

    # Consumer / retail — swing dengan volume
    {"ticker": "ERAA", "price": 402, "sector": "Retail"},
    {"ticker": "ACES", "price": 380, "sector": "Retail"},
    {"ticker": "ROTI", "price": 610, "sector": "Consumer"},
    {"ticker": "CLEO", "price": 402, "sector": "Consumer"},
    {"ticker": "SIDO", "price": 472, "sector": "Healthcare"},

    # Banking mid-cap — swing saat ada sentimen
    {"ticker": "BJBR", "price": 795, "sector": "Banking"},
    {"ticker": "BJTM", "price": 595, "sector": "Banking"},
    {"ticker": "BBTN", "price": 1200, "sector": "Banking"},
    {"ticker": "BFIN", "price": 765, "sector": "Finance"},
    {"ticker": "ASSA", "price": 770, "sector": "Transport"},

    # Media / tech — volatil, swing cepat
    {"ticker": "EMTK", "price": 730, "sector": "Media"},
    {"ticker": "SCMA", "price": 246, "sector": "Media"},
    {"ticker": "MNCN", "price": 222, "sector": "Media"},
    {"ticker": "KAEF", "price": 630, "sector": "Healthcare"},
    {"ticker": "KLBF", "price": 870, "sector": "Healthcare"},

    # Saham volatile yang sering swing
    {"ticker": "HMSP", "price": 740, "sector": "Tobacco"},
    {"ticker": "TBLA", "price": 690, "sector": "Plantation"},
    {"ticker": "DRMA", "price": 980, "sector": "Industry"},
    {"ticker": "ARNA", "price": 488, "sector": "Industry"},
    {"ticker": "TOWR", "price": 470, "sector": "Telco"},
    {"ticker": "MAPI", "price": 1300, "sector": "Retail"},
    {"ticker": "SMGR", "price": 3800, "sector": "Industry"},
    {"ticker": "INDF", "price": 6800, "sector": "Consumer"},
    {"ticker": "CPIN", "price": 4800, "sector": "Consumer"},
    {"ticker": "PGAS", "price": 1500, "sector": "Energy"},
]

bandar_batches = {}
for i in range(0, len(bandar_stocks), 10):
    idx = i // 10
    if idx >= len(labels):
        break
    bandar_batches[f"batch_{labels[idx].lower()}"] = [s["ticker"] for s in bandar_stocks[i:i+10]]

bandar_result = {
    "date": date_str,
    "strategy": "BANDAR_AI",
    "description": "Saham IDX mid-cap untuk swing trading. TF: 10 menit. Deteksi akumulasi bandar/institusi.",
    "total": len(bandar_stocks),
    "batches": len(bandar_batches),
    "stocks": bandar_stocks,
    "batch_groups": bandar_batches
}

bandar_path = os.path.join(SCRIPT_DIR, "bandar_ai_stocks.json")
with open(bandar_path, "w", encoding="utf-8") as f:
    json.dump(bandar_result, f, indent=2, ensure_ascii=False)

print(f"\n=== BANDAR AI ===")
print(f"  Total: {len(bandar_stocks)} emiten (swing mid-cap)")
print(f"  Batches: {len(bandar_batches)}")

print(f"\n=== DONE ===")
print(f"  Scalping: {len(scalping_picks)} emiten (TF=1min)")
print(f"  Bandar AI: {len(bandar_stocks)} emiten (TF=10min)")
