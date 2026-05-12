# Scalping Screener IDX - TradingView Pine Script v6

Screener otomatis untuk emiten IDX harga < 1000 IDR.
Data harga diambil dari **Yahoo Finance** tanggal **12 Mei 2026**.

## Daftar Script

| File | Emiten | Range Harga |
|------|--------|-------------|
| `scalping_batch_a.pine` | 40 emiten | Rp505 - Rp995 |
| `scalping_batch_b.pine` | 40 emiten | Rp248 - Rp505 |
| `scalping_batch_c.pine` | 40 emiten | Rp117 - Rp246 |
| `scalping_batch_d.pine` | 28 emiten | Rp50 - Rp115 |

**Total: 148 emiten**

## Fitur Screener

Setiap script menampilkan tabel dengan kolom:

| Kolom | Deskripsi |
|-------|-----------|
| EMITEN | Kode saham |
| TF | Timeframe (default 5m) |
| ENTRY | Level entry (Pivot Support) |
| NOW | Harga sekarang |
| TP | Take Profit (Pivot Resistance) |
| SL | Stop Loss (Support - 0.5x ATR) |
| PROFIT | Potensi profit % |
| STATUS | FRESH BUY / RUNNING / WAIT |
| ZONA | MURAH / MID / MAHAL (Bollinger Band) |
| RSI | RSI(14) |
| RVOL | Relative Volume (vs SMA 20) |
| VALUE | Nilai transaksi (M/B) |
| BANDAR | BIG ACCUM / ACCUM / NORMAL |
| ACTION | HAKA / HOLD / SKIP / WAIT |

## Cara Pakai

### 1. Pasang Script di TradingView
1. Buka TradingView > Pine Editor
2. Copy-paste isi file `.pine`
3. Klik "Add to chart"
4. Ulangi untuk setiap batch (bisa pasang semua sekaligus di Premium)

### 2. Setup Alert + Webhook
1. Klik "Alert" di TradingView
2. Condition: pilih indicator > "Any alert() function call"
3. Centang "Webhook URL"
4. Masukkan URL webhook aplikasi Anda
5. Alert akan trigger JSON payload setiap ada sinyal HAKA

### Webhook Payload Format
```json
{
  "type": "SCALP",
  "batch": "A",
  "ticker": "KLBF",
  "tf": "5",
  "signal": "FRESH_BUY",
  "entry": 880,
  "tp": 900,
  "sl": 875,
  "rsi": 28.5,
  "rvol": 2.13,
  "zona": "MURAH",
  "bandar": "BIG_ACCUM",
  "action": "HAKA",
  "time": "1747036800"
}
```

## Rumus

- **Entry/TP/SL**: Classic Pivot Point + ATR(14) buffer
- **Zona**: Bollinger Band (SMA20, 2 StdDev)
- **Bandar**: Volume spike detection (volume > 3x avg = BIG ACCUM, > 1.5x = ACCUM)
- **Status**: Kombinasi posisi harga vs entry, RSI < 35, RVOL > 1.5
- **Action**: HAKA jika FRESH BUY + ada akumulasi bandar

## Regenerate

Untuk update daftar emiten terbaru:
```bash
python fetch_idx_prices.py    # Fetch harga terbaru dari Yahoo Finance
python generate_pine_scripts.py  # Generate ulang semua Pine Script
```
