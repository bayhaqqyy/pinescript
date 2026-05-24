# SahamScreen — IDX Strategies v2

Pipeline end-to-end untuk screener TradingView saham Indonesia (IDX) berbasis algoritma kuantitatif dan volume. Versi 2 berfokus eksklusif pada **Penny Stocks (< Rp1.000)** dengan volatilitas tinggi, memisahkan strategi menjadi dua tier: **SCALP_GORENGAN** (intraday) dan **BANDAR_SWING** (swing trading).

## Arsitektur Pipeline v2

```text
[Yahoo Finance] 
       |
(1) fetch_idx_prices.py
       |  idx_prices_v2.json (All < Rp1000)
       v
(2) filter_scalping_stocks.py  ---> scalping_stocks.json (35 emiten aktif)
       |                            bandar_ai_stocks.json (30 emiten mid-cap)
       v
(3) generate_pine_scripts.py
       |
       +---> scalping_v2_batch_a.pine, bandar_ai_v2_batch_a.pine, dsb.
```

## Tier Strategi

### 1. SCALP GORENGAN (`scalping_v2_*.pine`)
- **Fokus:** Saham dengan volatilitas harian ekstrem (Gorengan/Aktif).
- **Timeframe:** 5 Menit (Intraday).
- **Target:** Holding period dari hitungan menit hingga maksimal penutupan sesi.
- **Kriteria:** Seeded dari 35 ticker terbukti aktif minggu ini (BUMI, DYAN, PACK, dsb).
- **Logika Alert:** Candle hijau, close > low, relative volume > 1.5, close > EMA5, transaction value >= min_tv, dan close-bar confirmed. TP/SL menggunakan standar ATR.

### 2. BANDAR SWING (`bandar_ai_v2_*.pine`)
- **Fokus:** Saham penny liquid dengan indikasi akumulasi institusi/bandar.
- **Timeframe:** 60 Menit (Swing).
- **Target:** Holding period 3-7 hari.
- **Kriteria:** Seeded dari 15 ticker potensial, di-backfill dengan saham < Rp1.000 yang memiliki likuiditas (Transaction Value rata-rata > Rp500 Juta/hari).
- **Logika Alert:** EMA 200 Trend + Candle Absorption + Volume Spike (Sniper Buy & Bull Absorb).

## Webhook & Payload Format

Sistem menggunakan JSON terstruktur yang ditangkap oleh `main.py` (FastAPI) dan diformat secara otomatis untuk dikirim ke Telegram.

**Contoh Payload V2:**
```json
{
  "type": "SCALP",
  "tier": "SCALP_GORENGAN",
  "ticker": "BUMI",
  "tf": "5",
  "signal": "FRESH_BUY",
  "entry": 120,
  "tp1": 124,
  "tp2": 128,
  "sl": 116,
  "holding_hint": "intraday (menit-jam)",
  "transaction_value": 45000000000,
  "time": "1747036800"
}
```

## Cara Menjalankan Pipeline

1. **Update Data Harga:**
   Tarik data terbaru selama 1 bulan dari YFinance untuk menghitung Transaction Value:
   ```bash
   python tv_scripts/fetch_idx_prices.py
   ```

2. **Filter & Kategorisasi Tiers:**
   Buat `scalping_stocks.json` dan `bandar_ai_stocks.json` berdasarkan whitelist dan likuiditas:
   ```bash
   python tv_scripts/filter_scalping_stocks.py
   ```

3. **Generate Script Pine:**
   Generate `.pine` scripts V2 dengan logika ATR dan dynamic wait thresholds:
   ```bash
   python tv_scripts/generate_pine_scripts.py
   ```
   *File output akan berada di folder `tv_scripts/` dengan prefix `_v2_`.*

4. **Jalankan Webhook (Lokal/Server):**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Catatan Penting
* **FCA Blacklist**: Saham yang berstatus Full Call Auction (FCA) dan/atau Suspended (contoh: `WSKT`, `TAXI`) difilter secara keras di tahap (2) agar Pine Script tidak error/nyangkut.
* **Smart Filtering**: Pine script V2 secara dinamis membatalkan alert (`WAIT_LIQ`) jika transaction value per bar mendadak anjlok, melindungi trader dari ilusi breakout tanpa likuiditas.
