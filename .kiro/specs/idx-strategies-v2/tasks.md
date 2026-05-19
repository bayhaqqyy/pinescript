# Tasks — IDX Strategies v2

> **Catatan**: Semua threshold harga adalah **< Rp1.000** (penny stock).
> Emiten whitelist sudah diperbarui berdasarkan riset trending minggu 12-19 Mei 2026.

---

## Task 1: Upgrade Pipeline_Fetch untuk dual-pool output
**File:** `tv_scripts/fetch_idx_prices.py`  |  **Req:** R3

- [x] 1.1 Ubah `yf.download()` dari `period="1d"` ke `period="5d"` untuk data `avg_dollar_volume_20` (diganti ke 1mo)
- [x] 1.2 Hitung `avg_dollar_volume_20`: rata-rata `volume × close` 20 bar terakhir
- [x] 1.3 Tambahkan `tier_eligible`: `["SCALP_GORENGAN", "BANDAR_SWING"]` jika `50 <= price < 1000`
- [x] 1.4 Tetap filter `price < 1000` — simpan hanya penny stock, buang yang >= 1000
- [x] 1.5 Retry logic: max 3x per ticker, exponential backoff (1s, 2s, 4s)
- [x] 1.6 Catat ticker gagal ke `errors[]` di output JSON
- [x] 1.7 Output filename: `idx_prices_v2.json` (bukan `idx_below_1000.json`)
- [x] 1.8 Field `date` format `YYYY-MM-DD` dinamis
- [x] 1.9 Verifikasi output JSON sesuai design doc

---

## Task 2: Upgrade Pipeline_Filter — dual-pool + tier + whitelist populer
**File:** `tv_scripts/filter_scalping_stocks.py`  |  **Req:** R1, R2, R4, R10, R12

- [x] 2.1 Input file: `idx_prices_v2.json`
- [x] 2.2 Definisikan `WHITELIST_SCALPING` — **35 ticker yang TERBUKTI AKTIF minggu ini** (lihat design.md):
  - Bakrie group: BUMI, BRMS, DEWA, BNBR
  - Top gainers: DYAN (+31%), DPUM (+28%), KOPI (+24%), KJEN (+24%), NEST (+20%), DFAM (+20%), BLUE (+18%), BPTR (+16%), CCSI (+16%), ESTI (+16%), ZATA (+14%), GRIA (+13%), IRSX (+13%), FILM (+11%), BELL (+11%)
  - Top frekuensi BEI: BIPI (29K tx), MEDS (17K tx)
  - Trending Stockbit: PACK, MBMA, BULL, HUMI
  - Komoditas aktif: TOBA, ESSA, ELSA
  - Lain aktif: EMTK, SHIP (UMA), KOTA
- [x] 2.3 Definisikan `WHITELIST_BANDAR` — **15 ticker** untuk swing (lihat design.md):
  - Bakrie: BUMI, BRMS, DEWA
  - Komoditas: MBMA, TOBA, ESSA, ELSA
  - Trending + katalis: PACK, NEST, BULL, IRSX, BLUE, HUMI
  - Frekuensi tinggi: BIPI, EMTK
- [x] 2.4 Tambah `WSKT` ke `CONFIRMED_FCA` (suspended sejak Mei 2023)
- [x] 2.5 **Pool_Scalping**: filter `50 <= price < 1000`, `not in FCA`, `listing_age >= 30 hari`
- [x] 2.6 Whitelist seed hanya masuk jika memenuhi SEMUA kriteria
- [x] 2.7 Field `tier: "SCALP_GORENGAN"` di setiap entri
- [x] 2.8 **Pool_Bandar**: filter `50 <= price < 1000`, `not in FCA`
- [x] 2.9 Hitung `price_tier`: `UPPER` (>= Rp300), `LOWER` (>= Rp50 & < Rp300)
- [x] 2.10 Jika UPPER >= 30 → pool = UPPER saja; jika < 30 → backfill LOWER yang `avg_dollar_volume_20 >= 500M` sampai 30
- [x] 2.11 Field `tier: "BANDAR_SWING"` dan `price_tier` di setiap entri
- [x] 2.12 Catat whitelist missing ke `whitelist_missing[]`
- [x] 2.13 Tulis kedua JSON output
- [x] 2.14 Pastikan idempotency

---

## Task 3: Upgrade Pine_Generator (`tv_scripts/generate_pine_scripts.py`)
**File:** `tv_scripts/generate_pine_scripts.py`  |  **Req:** R5, R6, R7, R8, R10

- [x] 3.1 Output filename: `scalping_v2_batch_{label}.pine`, `bandar_ai_v2_batch_{label}.pine`
- [x] 3.2 File v1 TIDAK dihapus/ditimpa
- [x] 3.3 Default TF Scalping: `"5"` (5 menit)
- [x] 3.4 Default TF Bandar AI: `"60"` (1 jam)
- [x] 3.5 Input `min_tv` float, default `500000000`, label `"Min Transaction Value per Bar (Rp)"`
- [x] 3.6 `tv = volume * close`; jika `tv < min_tv` → `"WAIT_LIQ"`, tahan alert
- [x] 3.7 Input `tp1_mult, tp2_mult, sl_mult`. Default Scalp: `1.0, 2.0, 1.0`. Bandar: `1.5, 3.0, 1.5`
- [x] 3.8 ATR-based: BUY → `tp1=entry+ATR*tp1_mult`, `tp2=entry+ATR*tp2_mult`, `sl=entry-ATR*sl_mult`
- [x] 3.9 Monotonicity check: BUY `TP2>TP1>entry>SL`; SELL sebaliknya. Gagal → `"WAIT_TICK"`
- [x] 3.10 ATR == 0 atau na → `"WAIT_ATR"`, tahan alert
- [x] 3.11 Hapus TP fixed 3% dan SL 0.5x ATR lama
- [x] 3.12 Payload Scalping v2: `type, tier, ticker, tf, signal, entry, tp1, tp2, sl, holding_hint:"intraday (menit-jam)", transaction_value, time`
- [x] 3.13 Payload Bandar v2: `type, tier, ticker, tf, signal, entry, tp1, tp2, sl, holding_hint:"swing 3-7 hari", transaction_value, time`
- [x] 3.14 Field harga numerik (tanpa Rp, tanpa quotes)
- [x] 3.15 Field harga/ATR na → batalkan alert

---

## Task 4: Telegram Formatter v2
**File:** `main.py`  |  **Req:** R8, R13

- [x] 4.1 `format_idx_scalp_v2_alert(data)` — badge `"SCALP · GORENGAN"`, Entry/TP1/TP2/SL/Holding_Hint
- [x] 4.2 `format_idx_bandar_v2_alert(data)` — badge `"BANDAR · SWING 1W"`, Entry/TP1/TP2/SL/Holding_Hint
- [x] 4.3 Hashtag `#IDX_SCALP_V2` dan `#IDX_BANDAR_V2`
- [x] 4.4 Error: `tier` hilang → return error, jangan kirim ke Telegram
- [x] 4.5 HTML escape `<`, `>`, `&` di `ticker` dan `signal`
- [x] 4.6 Round-trip: output mengandung `ticker, entry, tp1, tp2, sl, holding_hint`
- [x] 4.7 Determinism: payload identik → string identik

---

## Task 5: Update Webhook Handler
**File:** `main.py`  |  **Req:** R8

- [x] 5.1 Routing: `type=="SCALP" AND tier=="SCALP_GORENGAN"` → `format_idx_scalp_v2_alert()`
- [x] 5.2 Routing: `type=="BANDAR_AI" AND tier=="BANDAR_SWING"` → `format_idx_bandar_v2_alert()`
- [x] 5.3 Legacy routing tetap (payload tanpa `tier` → formatter lama)
- [x] 5.4 `/health` endpoint: tambah v2 ke `supported_alerts`

---

## Task 6: Update README
**File:** `README.md`  |  **Req:** R11

- [x] 6.1 Section "IDX Strategies v2" — overview penny stock < Rp1.000
- [x] 6.2 Screenshot dummy / ASCII diagram
- [x] 6.3 Penjelasan perbedaan SCALPING_GORENGAN vs BANDAR_SWING
- [x] 6.4 Cara run pipeline: 1) fetch 2) filter 3) generate
- [x] 6.5 Payload JSON terbaru (TP1/TP2/SL/transaction_value/tier)

---

## Task 7: Property-based tests
**Req:** R12, R13, R14

- [ ] 7.1 Pool_Scalping: semua `50 <= price < 1000` dan `not in FCA`
- [ ] 7.2 Pool_Bandar: semua `50 <= price < 1000` dan `not in FCA`
- [ ] 7.3 Pool_Bandar UPPER: semua `price >= 300`
- [ ] 7.4 Filter idempotency (2x run = identik)
- [ ] 7.5 Telegram round-trip (semua field ada di output)
- [ ] 7.6 Telegram determinism (identik → identik)
- [ ] 7.7 HTML escape benar
- [ ] 7.8 ATR monotonicity BUY dan SELL
