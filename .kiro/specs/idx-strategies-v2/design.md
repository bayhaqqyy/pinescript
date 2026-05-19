# Design Document — IDX Strategies v2

## Architecture Overview

IDX Strategies v2 adalah revisi dari dua screener Pine Script (Scalping IDX dan Bandar AI IDX) yang **tetap fokus ke saham harga < Rp1.000** (penny stock / gorengan tier) tetapi dengan peningkatan kualitas sinyal. Versi 2 memisahkan dua tier:

- **Scalping (gorengan tier)**: harga **< Rp1.000**, volatil, bukan FCA, bukan suspended, bukan IPO baru < 30 hari.
- **Bandar AI Swing (mid-cap tier)**: harga **< Rp1.000** dengan preferensi ≥ Rp300 (tier atas penny stock), untuk swing 3–7 hari dengan deteksi akumulasi/distribusi institusi.

Pipeline: **Fetch → Filter → Generate → TradingView → Webhook → Telegram**

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Pipeline_Fetch│────▶│Pipeline_Filter│────▶│Pine_Generator │
│ fetch_idx_    │     │ filter_      │     │ generate_pine_│
│ prices.py     │     │ scalping_    │     │ scripts.py    │
│               │     │ stocks.py    │     │               │
│ Output:       │     │ Output:      │     │ Output:       │
│ idx_prices_   │     │ scalping_    │     │ *_v2_batch_   │
│ v2.json       │     │ stocks.json  │     │ {label}.pine  │
│               │     │ bandar_ai_   │     │               │
│               │     │ stocks.json  │     │               │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │  TradingView  │
                                          │  (Pine v6)    │
                                          │  Alerts ──────┤
                                          └──────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │  main.py      │
                                          │  Telegram     │
                                          │  Formatter    │
                                          └──────────────┘
```

## Component Design

### 1. Pipeline_Fetch (`tv_scripts/fetch_idx_prices.py`)

**Perubahan dari v1:**
- Output file: `idx_below_1000.json` → `idx_prices_v2.json`
- Tetap filter harga **< Rp1.000** — ini adalah inti dari strategi penny stock
- Menambah perhitungan `avg_dollar_volume_20` (rata-rata `volume × close` 20 bar terakhir)
- Retry logic (max 3x per ticker, exponential backoff)
- Field `date` format `YYYY-MM-DD` (dinamis)

**Output Schema — `idx_prices_v2.json`:**
```json
{
  "date": "2026-05-19",
  "total": 180,
  "stocks": [
    {
      "ticker": "BRMS",
      "price": 720,
      "avg_dollar_volume_20": 45000000000,
      "tier_eligible": ["SCALP_GORENGAN", "BANDAR_SWING"]
    }
  ],
  "errors": ["XYZZ: timeout after 3 retries"]
}
```

**Logika `tier_eligible`:**
- `SCALP_GORENGAN`: `price < 1000` AND `price >= 50`
- `BANDAR_SWING`: `price < 1000` AND `price >= 50`
- Ticker dengan `price >= 1000` atau `price < 50` → `tier_eligible: []`

### 2. Pipeline_Filter (`tv_scripts/filter_scalping_stocks.py`)

**Perubahan dari v1:**
- Input: `idx_prices_v2.json`
- Output 2 file: `scalping_stocks.json` dan `bandar_ai_stocks.json`
- Field `tier` dan `price_tier` per entri
- Filter IPO < 30 hari (Scalping)
- Whitelist seed per tier — **DIPERBARUI dengan emiten populer minggu 19 Mei 2026**

**FCA Blacklist** (tetap dari v1, ditambah update):
```python
CONFIRMED_FCA = {
    "TAXI", "BTEK", "KREN", "HADE", "WSBP", "PPRO", "BAPI",
    "IKAI", "BEKS", "MARI", "PURA", "PBRX", "PCAR", "DIGI",
    "WSKT",  # suspended sejak Mei 2023
}
```

**Whitelist Seed — HANYA emiten yang benar-benar populer & aktif minggu 12-19 Mei 2026:**

Sumber data: Top gainers BEI harian, trending Stockbit, broker recommendation, foreign flow CNBC/Kontan.

```python
# =========================================================================
# WHITELIST SCALPING — HANYA penny stock < Rp1000 yang TERBUKTI AKTIF
# Kriteria: top gainer minggu ini, trending Stockbit, top frekuensi BEI,
#           atau ada katalis nyata (aksi korporasi, masuk indeks, UMA, dsb)
# Sumber: Liputan6 top frekuensi, Katadata top gainers, Stockbit trending,
#         CNBC foreign flow, IDX UMA announcements — 12-19 Mei 2026
# =========================================================================
WHITELIST_SCALPING = {
    # === GRUP BAKRIE — volume konsisten besar, paling ramai dibicarakan ===
    "BUMI",   # ~Rp210, volume transaksi selalu top, frekuensi ritel gila
    "BRMS",   # ~Rp720, net buy asing CNBC confirmed, range 685-755 aktif
    "DEWA",   # ~Rp440-484, masuk LQ45 & IDX80 Mei 2026, trending Stockbit
    "BNBR",   # ~Rp159-167, naik 2.45% tgl 19 Mei, rights issue rumor 2026

    # === TOP GAINERS MINGGU INI (12-19 Mei 2026) — kenaikan terbukti ===
    "DYAN",   # ~Rp109, TOP GAINER +31.33% tgl 18 Mei
    "DPUM",   # ~Rp192, TOP GAINER +28.00% (11-13 Mei)
    "KOPI",   # ~Rp284, TOP GAINER +24.56% tgl 13 Mei
    "KJEN",   # ~Rp168, TOP GAINER +24.44% (11-13 Mei)
    "NEST",   # ~Rp590, TOP GAINER +20.90% (11-13 Mei)
    "DFAM",   # ~Rp125, TOP GAINER +20.19% (11-13 Mei), UMA 11 Mei
    "BLUE",   # ~Rp590, TOP GAINER +18.28% tgl 18 Mei (Blue Bird)
    "BPTR",   # ~Rp97, TOP GAINER +16.87% tgl 18 Mei
    "CCSI",   # ~Rp278, TOP GAINER +16.81% (11-13 Mei)
    "ESTI",   # TOP GAINER +16.08% tgl 19 Mei (hari ini!)
    "ZATA",   # ~Rp85, TOP GAINER +14.67% tgl 19 Mei (hari ini!)
    "GRIA",   # ~Rp116, TOP GAINER +13.73% (11-13 Mei)
    "IRSX",   # ~Rp464, TOP GAINER +13.17% (11-13 Mei)
    "FILM",   # TOP GAINER +11.06% tgl 19 Mei (hari ini!)
    "BELL",   # TOP GAINER +11.38% tgl 19 Mei (hari ini!)

    # === TOP FREKUENSI 18 Mei — paling banyak transaksi di BEI ===
    "BIPI",   # ~Rp226, #2 frekuensi 29.419 kali (18 Mei), infra energy
    "MEDS",   # TOP frekuensi 16.919 kali (18 Mei), healthcare IPO baru

    # === TRENDING STOCKBIT & BROKER RECS ===
    "PACK",   # trending Stockbit, aksi korporasi Haji Isam, swing breakout
    "MBMA",   # ~Rp605, nikel, net buy asing (CNBC list), volatile
    "BULL",   # ~Rp490-505, shipping, sering masuk top frekuensi
    "HUMI",   # ~Rp180, trending Stockbit 19 Mei, bullish breakout status

    # === KOMODITAS AKTIF — volume besar, rekomendasi broker ===
    "TOBA",   # ~Rp570, coal, rights issue rumor, volatile
    "ESSA",   # ~Rp805, energy, volume stabil
    "ELSA",   # ~Rp710, energy

    # === LAIN-LAIN AKTIF ===
    "EMTK",   # ~Rp710-730, top gainer LQ45 +1.43% tgl 19 Mei
    "SHIP",   # UMA list 12 Mei, volatilitas tinggi
    "KOTA",   # ~Rp143, naik +5.15% tgl 19 Mei
}

# =========================================================================
# WHITELIST BANDAR AI — Penny stock < Rp1000 untuk SWING 3-7 hari
# Kriteria: volume & likuiditas cukup untuk hold, ada pola akumulasi,
#           foreign flow aktif, atau katalis yang bikin hold-able
# =========================================================================
WHITELIST_BANDAR = {
    # === BAKRIE GROUP — akumulasi/distribusi institusi terdeteksi ===
    "BUMI",   # ~Rp210, big volume, pola distribusi/akumulasi jelas
    "BRMS",   # ~Rp720, net buy asing aktif, swing range 685-755
    "DEWA",   # ~Rp440-484, masuk LQ45 Mei 2026, buy zone 400-445

    # === KOMODITAS — swing play klasik, foreign flow ===
    "MBMA",   # ~Rp605, nikel, net buy asing
    "TOBA",   # ~Rp570, coal, rights issue catalyst
    "ESSA",   # ~Rp805, energy
    "ELSA",   # ~Rp710, energy

    # === TRENDING + KATALIS — hold-able 3-7 hari ===
    "PACK",   # trending, aksi korporasi Haji Isam, transformasi bisnis nikel
    "NEST",   # ~Rp590, momentum kuat +20.9%
    "BULL",   # ~Rp490-505, shipping, volume stabil
    "IRSX",   # ~Rp464, momentum +13.17%
    "BLUE",   # ~Rp590, Blue Bird, momentum +18.28%
    "HUMI",   # ~Rp180, bullish breakout, trending Stockbit

    # === FREKUENSI TINGGI — likuid untuk swing ===
    "BIPI",   # ~Rp226, #2 frekuensi BEI, likuid
    "EMTK",   # ~Rp710, LQ45 gainer
}
```

**Pool_Scalping build logic:**
```
1. Baca idx_prices_v2.json
2. Filter: price < 1000 AND price >= 50 AND NOT IN FCA_Blacklist AND listing_age >= 30 hari
3. Whitelist seed: masukkan jika memenuhi semua kriteria di atas
4. Tambah field tier: "SCALP_GORENGAN"
5. Sort by price descending
6. Batch per 10 ticker
7. Tulis ke scalping_stocks.json
```

**Pool_Bandar build logic:**
```
1. Baca idx_prices_v2.json
2. Filter: price < 1000 AND price >= 50 AND NOT IN FCA_Blacklist
3. Hitung price_tier: UPPER (>= 300 & < 1000), LOWER (>= 50 & < 300)
4. Jika UPPER >= 30: pool = hanya UPPER
5. Jika UPPER < 30: backfill dengan LOWER yang avg_dollar_volume_20 >= Liquidity_Threshold sampai 30 atau habis
6. Tambah field tier: "BANDAR_SWING", price_tier: "UPPER"/"LOWER"
7. Sort by price descending → batch per 10 → tulis ke bandar_ai_stocks.json
```

**Output Schema — `scalping_stocks.json`:**
```json
{
  "date": "2026-05-19",
  "strategy": "SCALPING_V2",
  "total": 50,
  "batches": 5,
  "stocks": [
    { "ticker": "BRMS", "price": 720, "tier": "SCALP_GORENGAN" }
  ],
  "batch_groups": { "batch_a": ["BRMS", "EMTK", ...] },
  "whitelist_missing": []
}
```

**Output Schema — `bandar_ai_stocks.json`:**
```json
{
  "date": "2026-05-19",
  "strategy": "BANDAR_AI_V2",
  "total": 33,
  "batches": 4,
  "stocks": [
    { "ticker": "DRMA", "price": 980, "tier": "BANDAR_SWING", "price_tier": "UPPER" }
  ],
  "batch_groups": { "batch_a": ["DRMA", "HRUM", ...] },
  "whitelist_missing": []
}
```

### 3. Pine_Generator (`tv_scripts/generate_pine_scripts.py`)

**Perubahan dari v1:**
- Output filename: `scalping_v2_batch_{label}.pine`, `bandar_ai_v2_batch_{label}.pine`
- File v1 TIDAK dihapus/ditimpa
- Default TF: Scalping `"5"` (5m), Bandar AI `"60"` (1h)
- TP/SL sekarang berbasis ATR (bukan fixed %)
- Menambah filter Dollar_Volume per bar
- Payload alert diperkaya (TP1, TP2, SL, tier, holding_hint, dollar_volume)

**ATR-based TP/SL (Pine v6):**
```pine
// Input multipliers — Scalping default
tp1_mult = input.float(1.0, "TP1 ATR Multiplier")
tp2_mult = input.float(2.0, "TP2 ATR Multiplier")
sl_mult  = input.float(1.0, "SL ATR Multiplier")

// Bandar AI default: tp1=1.5, tp2=3.0, sl=1.5

// BUY signal
atr_val = ta.atr(14)
tp1 = entry + atr_val * tp1_mult
tp2 = entry + atr_val * tp2_mult
sl  = entry - atr_val * sl_mult

// Validation:
// BUY:  TP2 > TP1 > entry > SL
// SELL: TP2 < TP1 < entry < SL
// ATR == 0 or na → "WAIT_ATR", no alert
// Monotonicity broken → "WAIT_TICK", no alert
```

**Dollar Volume Liquidity Filter:**
```pine
min_dv = input.float(500000000, "Min Dollar Volume per Bar (Rp)")
dv = volume * close
liq_ok = dv >= min_dv
// If not liq_ok → "WAIT_LIQ", no alert
```

**Alert Payload — Scalping v2:**
```json
{
  "type": "SCALP",
  "tier": "SCALP_GORENGAN",
  "ticker": "BRMS",
  "tf": "5",
  "signal": "FRESH_BUY",
  "entry": 720,
  "tp1": 734,
  "tp2": 748,
  "sl": 706,
  "holding_hint": "intraday (menit-jam)",
  "dollar_volume": 45000000000,
  "time": 1716105600000
}
```

**Alert Payload — Bandar AI v2:**
```json
{
  "type": "BANDAR_AI",
  "tier": "BANDAR_SWING",
  "ticker": "CTRA",
  "tf": "60",
  "signal": "SNIPER_BUY",
  "entry": 680,
  "tp1": 701,
  "tp2": 722,
  "sl": 659,
  "holding_hint": "swing 3-7 hari",
  "dollar_volume": 25000000000,
  "time": 1716105600000
}
```

**Status Priority dalam screener table:**
```
WAIT_ATR  → ATR not available, alert ditahan
WAIT_LIQ  → Dollar volume < threshold, alert ditahan
WAIT_TICK → Monotonicity broken by rounding, alert ditahan
FRESH BUY → Semua kondisi terpenuhi, alert fired
RUNNING   → Sudah entry, belum TP
PROFIT    → Sudah di atas TP1
WAIT      → Belum ada sinyal
```

### 4. Telegram_Formatter (`main.py`)

**Fungsi baru:**

#### `format_idx_scalp_v2_alert(data: dict) -> str`
```
🔥 SCALP · GORENGAN 🔥
━━━━━━━━━━━━━━━━━━
🏢 Emiten: BRMS
⚡ Signal: FRESH_BUY
🎯 Entry: Rp720
✅ TP1: Rp734
🚀 TP2: Rp748
🛑 SL: Rp706
━━━━━━━━━━━━━━━━━━
⏰ intraday (menit-jam) · TF 5m
💰 DolVol: Rp45.0B
#IDX_SCALP_V2 #BRMS
```

#### `format_idx_bandar_v2_alert(data: dict) -> str`
```
🎯 BANDAR · SWING 1W 🎯
━━━━━━━━━━━━━━━━━━
🏢 Emiten: CTRA
⚡ Signal: SNIPER_BUY
🎯 Entry: Rp680
✅ TP1: Rp701
🚀 TP2: Rp722
🛑 SL: Rp659
━━━━━━━━━━━━━━━━━━
⏰ swing 3-7 hari · TF 60m
💰 DolVol: Rp25.0B
#IDX_BANDAR_V2 #CTRA
```

**Error handling:**
- `tier` field hilang → return error string, TIDAK kirim ke Telegram API
- HTML special chars di-escape

**Webhook routing update (`main.py`):**
```python
if data.get("type") == "SCALP" and data.get("tier") == "SCALP_GORENGAN":
    message_text = format_idx_scalp_v2_alert(data)
elif data.get("type") == "BANDAR_AI" and data.get("tier") == "BANDAR_SWING":
    message_text = format_idx_bandar_v2_alert(data)
# Legacy (tanpa tier) tetap pakai formatter lama
```

### 5. File Naming Convention

| Komponen | v1 (existing) | v2 (new) |
|----------|---------------|----------|
| Fetch output | `idx_below_1000.json` | `idx_prices_v2.json` |
| Scalping pool | `scalping_stocks.json` | `scalping_stocks.json` (overwrite OK) |
| Bandar pool | `bandar_ai_stocks.json` | `bandar_ai_stocks.json` (overwrite OK) |
| Pine Scalping | `scalping_batch_{x}.pine` | `scalping_v2_batch_{x}.pine` |
| Pine Bandar | `bandar_ai_batch_{x}.pine` | `bandar_ai_v2_batch_{x}.pine` |

### 6. README Update

Tambah section:
- **IDX Strategies v2** — overview dua tier (tetap < Rp1.000)
- **Tier: SCALP_GORENGAN** — threshold < Rp1.000, TF 5m, holding intraday
- **Tier: BANDAR_SWING** — threshold < Rp1.000 (preferensi ≥ Rp300), TF 1h, holding 3-7 hari
- **Pipeline Usage** — step-by-step: fetch → filter → generate
- **Alert Payload v2** — JSON schema kedua tier

## Testing Strategy

- **Filter idempotency**: 2x run → output identik
- **Pool property Scalping**: `price < 1000` AND `price >= 50` AND `not in FCA`
- **Pool property Bandar**: `price < 1000` AND `price >= 50` AND `not in FCA`, UPPER `>= 300`
- **ATR monotonicity**: BUY → `TP2 > TP1 > entry > SL`, SELL sebaliknya
- **Telegram round-trip**: output mengandung semua field penting
- **HTML escape**: `<`, `>`, `&` benar
- **Determinism**: payload identik → output identik
