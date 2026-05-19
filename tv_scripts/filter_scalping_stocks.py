"""
Filter stock lists for Scalping and Bandar AI strategies v2.
- Scalping: HANYA penny stock < Rp1000 (Gorengan tier).
- Bandar AI: Penny stock < Rp1000 untuk swing (Bandar Swing tier).
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# FCA BLACKLIST — HANYA saham yang BENAR-BENAR MASIH di Papan Pemantauan Khusus
# ============================================================================
CONFIRMED_FCA = {
    "TAXI", "BTEK", "KREN", "HADE", "WSBP", "PPRO", "BAPI",
    "IKAI", "BEKS", "MARI", "PURA", "PBRX", "PCAR", "DIGI",
    "WSKT"  # suspended sejak Mei 2023
}

# ============================================================================
# WHITELIST SCALPING & BANDAR
# ============================================================================
WHITELIST_SCALPING = {
    # Bakrie group
    "BUMI", "BRMS", "DEWA", "BNBR",
    # Top gainers
    "DYAN", "DPUM", "KOPI", "KJEN", "NEST", "DFAM", "BLUE", "BPTR", "CCSI", "ESTI", "ZATA", "GRIA", "IRSX", "FILM", "BELL",
    # Top frekuensi BEI
    "BIPI", "MEDS",
    # Trending Stockbit
    "PACK", "MBMA", "BULL", "HUMI",
    # Komoditas aktif
    "TOBA", "ESSA", "ELSA",
    # Lain aktif
    "EMTK", "SHIP", "KOTA"
}

WHITELIST_BANDAR = {
    # Bakrie
    "BUMI", "BRMS", "DEWA",
    # Komoditas
    "MBMA", "TOBA", "ESSA", "ELSA",
    # Trending + katalis
    "PACK", "NEST", "BULL", "IRSX", "BLUE", "HUMI",
    # Frekuensi tinggi
    "BIPI", "EMTK"
}

# ============================================================================
# LOAD DATA
# ============================================================================
with open(os.path.join(SCRIPT_DIR, "idx_prices_v2.json"), "r") as f:
    raw_data = json.load(f)

all_stocks = raw_data["stocks"]
date_str = raw_data["date"]

labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ============================================================================
# POOL SCALPING
# ============================================================================
scalping_pool = []
scalping_missing = []

# If we want to use only whitelist as the final pool, or all stocks?
# Task says "Pool_Scalping: filter 50 <= price < 1000, not in FCA"
# We will take ALL stocks that meet the criteria to not miss opportunities,
# but ensure whitelist is present and track missing ones.
for s in all_stocks:
    ticker = s["ticker"]
    price = s["price"]
    
    if ticker in CONFIRMED_FCA:
        continue
        
    if 50 <= price < 1000:
        s_copy = s.copy()
        s_copy["tier"] = "SCALP_GORENGAN"
        scalping_pool.append(s_copy)

# Check whitelist missing
pool_tickers = {s["ticker"] for s in scalping_pool}
for w in WHITELIST_SCALPING:
    if w not in pool_tickers:
        scalping_missing.append(w)

# Sort by price descending
scalping_pool.sort(key=lambda x: x["price"], reverse=True)

scalp_batches = {}
for i in range(0, len(scalping_pool), 10):
    idx = i // 10
    if idx >= len(labels):
        break
    scalp_batches[f"batch_{labels[idx].lower()}"] = [s["ticker"] for s in scalping_pool[i:i+10]]

scalp_result = {
    "date": date_str,
    "strategy": "SCALPING_V2",
    "description": "Saham IDX < Rp1000 untuk scalping intraday (Gorengan Tier). TF: 5 menit.",
    "total": len(scalping_pool),
    "batches": len(scalp_batches),
    "stocks": scalping_pool,
    "batch_groups": scalp_batches,
    "whitelist_missing": scalping_missing
}

scalp_path = os.path.join(SCRIPT_DIR, "scalping_stocks.json")
with open(scalp_path, "w", encoding="utf-8") as f:
    json.dump(scalp_result, f, indent=2, ensure_ascii=False)

print(f"\n=== SCALPING V2 ===")
print(f"  Total: {len(scalping_pool)} emiten")
print(f"  Batches: {len(scalp_batches)}")
print(f"  Whitelist missing: {scalping_missing}")

# ============================================================================
# POOL BANDAR AI
# ============================================================================
bandar_candidates = []
bandar_missing = []

for s in all_stocks:
    ticker = s["ticker"]
    price = s["price"]
    
    if ticker in CONFIRMED_FCA:
        continue
        
    if 50 <= price < 1000:
        s_copy = s.copy()
        s_copy["tier"] = "BANDAR_SWING"
        s_copy["price_tier"] = "UPPER" if price >= 300 else "LOWER"
        bandar_candidates.append(s_copy)

upper_pool = [s for s in bandar_candidates if s["price_tier"] == "UPPER"]

if len(upper_pool) >= 30:
    bandar_pool = upper_pool
else:
    lower_pool = [s for s in bandar_candidates if s["price_tier"] == "LOWER" and s.get("avg_transaction_value_20", 0) >= 500_000_000]
    # Sort lower pool by Transaction Value to get the best ones
    lower_pool.sort(key=lambda x: x.get("avg_transaction_value_20", 0), reverse=True)
    
    needed = 30 - len(upper_pool)
    bandar_pool = upper_pool + lower_pool[:needed]

# Make sure all valid whitelist bandar are included regardless of DV
bandar_pool_tickers = {s["ticker"] for s in bandar_pool}
for s in bandar_candidates:
    if s["ticker"] in WHITELIST_BANDAR and s["ticker"] not in bandar_pool_tickers:
        bandar_pool.append(s)

bandar_pool_tickers_final = {s["ticker"] for s in bandar_pool}
for w in WHITELIST_BANDAR:
    if w not in bandar_pool_tickers_final:
        bandar_missing.append(w)

bandar_pool.sort(key=lambda x: x["price"], reverse=True)

bandar_batches = {}
for i in range(0, len(bandar_pool), 10):
    idx = i // 10
    if idx >= len(labels):
        break
    bandar_batches[f"batch_{labels[idx].lower()}"] = [s["ticker"] for s in bandar_pool[i:i+10]]

bandar_result = {
    "date": date_str,
    "strategy": "BANDAR_AI_V2",
    "description": "Saham IDX < Rp1000 mid-cap untuk swing trading. TF: 60 menit.",
    "total": len(bandar_pool),
    "batches": len(bandar_batches),
    "stocks": bandar_pool,
    "batch_groups": bandar_batches,
    "whitelist_missing": bandar_missing
}

bandar_path = os.path.join(SCRIPT_DIR, "bandar_ai_stocks.json")
with open(bandar_path, "w", encoding="utf-8") as f:
    json.dump(bandar_result, f, indent=2, ensure_ascii=False)

print(f"\n=== BANDAR AI V2 ===")
print(f"  Total: {len(bandar_pool)} emiten (UPPER: {len([s for s in bandar_pool if s['price_tier']=='UPPER'])}, LOWER: {len([s for s in bandar_pool if s['price_tier']=='LOWER'])})")
print(f"  Batches: {len(bandar_batches)}")
print(f"  Whitelist missing: {bandar_missing}")

print(f"\n=== DONE ===")
