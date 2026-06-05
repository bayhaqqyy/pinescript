# PLAN.md — Final Upgrade TradingView Futures Alert Engine

## 1. Tujuan Final

Upgrade script TradingView `Binance USD-M Autobot A` agar output alert dari TradingView bisa menjadi signal futures yang lebih rapi, mirip format signal profesional/Telegram, tetapi tetap aman untuk limit TradingView dan tetap cocok untuk sistem batch kecil.

Target output signal:

```text
PORTALUSDT SHORT
Leverage: 5x - 10x recommended
Entry: 0.0245 - 0.0260
TP1: 0.0230
TP2: 0.0215
TP3: 0.0200
SL: 0.0275
Mode: SUPPLY_REJECTION / BREAKDOWN_RETEST
Status: VALID_SHORT / WAIT_RETEST_SHORT
Score: 82
Risk: SAFE
```

Target alert JSON TradingView:

```json
{
  "market": "BINANCE_FUTURES",
  "type": "FUTURES_SIGNAL",
  "event": "SHORT_ENTRY",
  "symbol": "PORTALUSDT",
  "side": "SHORT",
  "tf_trigger": "15",
  "tf_zone": "60",
  "tf_bias": "240",
  "mode": "SUPPLY_REJECTION",
  "status": "VALID_SHORT",
  "now": 0.0248,
  "entry_low": 0.0245,
  "entry_high": 0.0260,
  "entry_avg": 0.02525,
  "tp1": 0.0230,
  "tp2": 0.0215,
  "tp3": 0.0200,
  "sl": 0.0275,
  "risk_pct": 8.91,
  "rr_tp1": 0.89,
  "rr_tp2": 1.48,
  "rr_tp3": 2.08,
  "input_leverage": 10,
  "recommended_leverage": 3,
  "risk_label": "RISKY_PLAN",
  "score": 82,
  "bias_4h": "BEARISH",
  "zone_1h": "SUPPLY",
  "trigger_15m": "BREAKDOWN_RETEST",
  "rsi": 42.5,
  "rvol": 145.2,
  "time": 1770000000000
}
```

---

## 2. Kondisi Script Saat Ini

Script sekarang sudah punya fondasi yang bagus:

- TradingView Pine Script v6.
- Default screener timeframe 15m.
- Multi pair screener.
- Menggunakan EMA 20/50, RSI 14, MACD 12/26/9, RVOL, ATR, support resistance, candle behavior, scoring, risk filter, dan alert JSON.
- Sudah ada `activeSide`, `activeEntry`, `activeTp`, `activeSl`, event entry, event TP hit, event SL hit, cooldown alert, dan table dashboard.

Masalah utama:

1. Entry masih berdasarkan close candle saat sinyal valid.
2. TP masih satu target.
3. Belum ada entry zone.
4. Belum ada TP1, TP2, TP3.
5. Belum ada HTF bias 4H dan 1H zone yang ringkas.
6. Sinyal bisa telat ketika candle sudah pump/dump jauh.
7. Kalau MTF ditambah secara mentah-mentah, bisa kena limit TradingView.

---

## 3. Prinsip Final Karena Pair Diproses Sedikit Per Batch

Karena pair diproses sedikit per batch, sistem boleh lebih lengkap daripada screener 20-30 pair. Namun tetap harus ada batas aman.

Rekomendasi batch:

```text
Conservative batch: 3 - 5 pair per script
Maximum batch: 6 pair per script
Tidak disarankan: lebih dari 6 pair jika memakai 4H + 1H + 15m sekaligus
```

Alasan:

- 15m trigger akan return cukup banyak data.
- 1H zone akan return entry zone.
- 4H bias akan return bias filter.
- TradingView punya limit request dan tuple element.
- Dengan batch kecil, sistem bisa tetap detail tanpa terlalu berat.

---

## 4. Arsitektur Final

Gunakan 3 engine utama:

```text
1. 4H Bias Engine
2. 1H Zone Engine
3. 15m Trigger & Plan Engine
```

Flow final:

```text
4H menentukan bias besar
1H menentukan supply/demand zone
15m mencari trigger entry
Risk engine menghitung SL, TP1, TP2, TP3
Alert engine mengirim JSON dari TradingView
Webhook/backend menerima alert dan format ulang menjadi signal final
```

---

## 5. Timeframe Final

| Timeframe | Fungsi | Output |
|---|---|---|
| 4H / 240 | Major bias | Bullish, bearish, neutral, strength |
| 1H / 60 | Supply-demand zone | Zone type, zone low, zone high |
| 15m / 15 | Trigger entry | Side, mode, entry zone, TP, SL, score |
| 5m | Optional, jangan dipakai dulu | Hanya untuk versi lanjutan |

Untuk versi final awal, jangan gunakan 5m dulu agar TradingView tetap ringan.

---

## 6. TradingView Limit Safety Plan

### 6.1 Rule utama

Jangan return semua data indikator dari setiap timeframe. Return hasil akhirnya saja.

Contoh yang harus dihindari:

```text
4H return EMA20, EMA50, EMA200, RSI, MACD, ATR, high, low, close
1H return EMA20, EMA50, RSI, MACD, ATR, support, resistance, zone
15m return semua data lengkap
```

Contoh yang disarankan:

```text
4H return: biasFlag, biasStrength
1H return: zoneFlag, zoneLow, zoneHigh, zoneScore
15m return: actionFlag, statusFlag, modeFlag, now, entryLow, entryHigh, tp1, tp2, tp3, sl, score, riskPct, rvolPct, rsi
```

### 6.2 Estimasi tuple per pair

Desain aman:

```text
4H bias engine  = 2 values
1H zone engine  = 4 values
15m plan engine = 14 values
Total per pair  = 20 values
```

Dengan batch:

```text
3 pair = 60 tuple values
4 pair = 80 tuple values
5 pair = 100 tuple values
6 pair = 120 tuple values
```

Batas aman yang disarankan:

```text
Max pair per script: 5 pair
Max pair jika sangat perlu: 6 pair
```

Jangan memakai 7 pair untuk versi MTF lengkap karena terlalu dekat dengan limit.

### 6.3 Optimasi wajib

Gunakan:

```pine
request.security(symbol, tf, expression, calc_bars_count=300)
```

Catatan:

- Jangan pakai array/map/label/line/box di dalam `request.security()`.
- Jangan return string dari security context. Pakai numeric flag.
- Decode numeric flag menjadi string di chart utama.
- Jangan membuat terlalu banyak table column jika tidak perlu.
- Jangan menggambar banyak label/box per pair.
- Alert JSON cukup dikirim saat `barstate.isconfirmed`.

---

## 7. Numeric Flag Standard

Agar ringan, semua engine return angka, bukan string.

### 7.1 Side flag

```text
1  = LONG
-1 = SHORT
0  = WAIT
```

### 7.2 Bias flag

```text
1  = BULLISH
-1 = BEARISH
0  = NEUTRAL
```

### 7.3 Zone flag

```text
1  = DEMAND
-1 = SUPPLY
0  = NONE
```

### 7.4 Status flag

```text
1 = VALID_LONG
2 = VALID_SHORT
3 = WAIT_RETEST_LONG
4 = WAIT_RETEST_SHORT
5 = OVEREXTENDED
6 = CONFLICT
7 = RISKY_PLAN
0 = NO_TRADE
```

### 7.5 Mode flag

```text
1 = TREND_CONTINUATION
2 = PULLBACK_ENTRY
3 = BREAKOUT_ENTRY
4 = BREAKDOWN_ENTRY
5 = SUPPLY_REJECTION
6 = DEMAND_REJECTION
7 = BREAKOUT_RETEST
8 = BREAKDOWN_RETEST
0 = NONE
```

---

## 8. 4H Bias Engine

### 8.1 Tujuan

Mencegah entry melawan trend besar.

### 8.2 Indicator

- EMA 20
- EMA 50
- EMA 200
- RSI 14
- MACD histogram

### 8.3 Rule bullish

```text
close > EMA50
EMA20 > EMA50
RSI > 50
MACD histogram >= 0
```

Optional stronger bullish:

```text
close > EMA200
EMA50 > EMA200
```

### 8.4 Rule bearish

```text
close < EMA50
EMA20 < EMA50
RSI < 50
MACD histogram <= 0
```

Optional stronger bearish:

```text
close < EMA200
EMA50 < EMA200
```

### 8.5 Output

```text
biasFlag
biasStrength
```

Bias strength:

```text
0 = weak
1 = normal
2 = strong
```

### 8.6 Anti-conflict

```text
Jika 4H strong bullish, jangan kirim SHORT kecuali mode = supply rejection ekstrem dan score sangat tinggi.
Jika 4H strong bearish, jangan kirim LONG kecuali mode = demand rejection ekstrem dan score sangat tinggi.
```

Untuk versi awal, lebih aman:

```text
Strong bullish = block SHORT
Strong bearish = block LONG
```

---

## 9. 1H Zone Engine

### 9.1 Tujuan

Membuat entry zone seperti signal Telegram, bukan hanya entry close.

### 9.2 Indicator

- Highest high 20 - 50 candle
- Lowest low 20 - 50 candle
- ATR 14
- Swing high / swing low sederhana

### 9.3 Supply zone untuk SHORT

```text
resistance1h = highest(high[1], zoneLen)
zoneBuffer = ATR1H * 0.25
supplyLow = resistance1h - zoneBuffer
supplyHigh = resistance1h + zoneBuffer
```

### 9.4 Demand zone untuk LONG

```text
support1h = lowest(low[1], zoneLen)
zoneBuffer = ATR1H * 0.25
demandLow = support1h - zoneBuffer
demandHigh = support1h + zoneBuffer
```

### 9.5 Zone valid

Supply valid jika:

```text
Harga sekarang dekat resistance 1H
Atau harga baru breakdown dari area support lalu retest
Atau candle 1H sebelumnya membentuk rejection atas
```

Demand valid jika:

```text
Harga sekarang dekat support 1H
Atau harga baru breakout dari resistance lalu retest
Atau candle 1H sebelumnya membentuk rejection bawah
```

### 9.6 Output

```text
zoneFlag
zoneLow
zoneHigh
zoneScore
```

Zone score:

```text
0 - 100
>= 70 valid
50 - 69 watch
< 50 ignore
```

---

## 10. 15m Trigger & Plan Engine

### 10.1 Tujuan

Menentukan apakah signal sudah valid untuk dikirim sebagai alert.

### 10.2 Indicator

- EMA 20
- EMA 50
- RSI 14
- MACD 12/26/9
- RVOL = volume / SMA volume 20
- ATR 14
- Candle body/wick
- Close near high / close near low
- Support/resistance 15m

### 10.3 LONG valid

```text
4H bias bukan strong bearish
1H zone = DEMAND atau breakout retest valid
close 15m > EMA20
EMA20 >= EMA50 atau mulai mengarah naik
RSI > 50 dan RSI < 72
MACD histogram bullish
RVOL >= 1.2
Candle hijau
Close dekat high
Risk plan aman
Score >= 70
```

### 10.4 SHORT valid

```text
4H bias bukan strong bullish
1H zone = SUPPLY atau breakdown retest valid
close 15m < EMA20
EMA20 <= EMA50 atau mulai mengarah turun
RSI < 50 dan RSI > 28
MACD histogram bearish
RVOL >= 1.2
Candle merah
Close dekat low
Risk plan aman
Score >= 70
```

---

## 11. WAIT_RETEST Logic

### 11.1 Tujuan

Menghindari entry yang telat setelah candle sudah terlalu jauh.

### 11.2 SHORT wait retest

```text
Jika bearish trigger valid
Tapi close sudah terlalu jauh dari EMA20 15m
Atau jarak close ke breakdown level > ATR15m * 1.2
Maka jangan kirim SHORT_ENTRY
Kirim status WAIT_RETEST_SHORT atau hanya tampilkan di dashboard
```

Retest zone SHORT:

```text
entryLow = brokenSupport - ATR15m * 0.15
entryHigh = brokenSupport + ATR15m * 0.30
```

### 11.3 LONG wait retest

```text
Jika bullish trigger valid
Tapi close sudah terlalu jauh dari EMA20 15m
Atau jarak close ke breakout level > ATR15m * 1.2
Maka jangan kirim LONG_ENTRY
Kirim status WAIT_RETEST_LONG atau hanya tampilkan di dashboard
```

Retest zone LONG:

```text
entryLow = brokenResistance - ATR15m * 0.30
entryHigh = brokenResistance + ATR15m * 0.15
```

### 11.4 Alert behavior

Untuk versi awal:

```text
VALID_LONG / VALID_SHORT = kirim alert entry
WAIT_RETEST_LONG / WAIT_RETEST_SHORT = tampilkan dashboard, optional alert watchlist
OVEREXTENDED = jangan kirim alert entry
CONFLICT = jangan kirim alert entry
RISKY_PLAN = jangan kirim alert entry, atau kirim alert dengan risk warning jika dibutuhkan
```

---

## 12. Entry Zone Rules

### 12.1 Entry average

```text
entryAvg = (entryLow + entryHigh) / 2
```

### 12.2 LONG entry zone prioritas

```text
1. Demand zone 1H
2. Breakout retest 15m
3. EMA20/EMA50 pullback 15m
4. ATR buffer dari candle confirmation
```

### 12.3 SHORT entry zone prioritas

```text
1. Supply zone 1H
2. Breakdown retest 15m
3. EMA20/EMA50 pullback 15m
4. ATR buffer dari candle confirmation
```

### 12.4 Jika harga sedang berada di dalam entry zone

```text
status = VALID_LONG atau VALID_SHORT
entryLow/entryHigh tetap dikirim
now dikirim sebagai harga saat ini
entryAvg untuk perhitungan risk
```

### 12.5 Jika harga sudah keluar terlalu jauh dari entry zone

```text
status = WAIT_RETEST atau OVEREXTENDED
jangan entry market
```

---

## 13. Stop Loss Final

### 13.1 SL LONG

Prioritas:

```text
1. Di bawah demand zone low
2. Di bawah swing low 15m
3. Support 1H - ATR buffer
4. Minimum ATR-based SL
```

Formula awal:

```text
slLongCandidate1 = zoneLow - ATR15m * 0.30
slLongCandidate2 = swingLow15m - ATR15m * 0.20
slLongBase = entryAvg - max(ATR15m * slAtrMult, entryAvg * minSlRawPct / 100)
slLong = min(slLongCandidate1, slLongCandidate2, slLongBase)
```

### 13.2 SL SHORT

Prioritas:

```text
1. Di atas supply zone high
2. Di atas swing high 15m
3. Resistance 1H + ATR buffer
4. Minimum ATR-based SL
```

Formula awal:

```text
slShortCandidate1 = zoneHigh + ATR15m * 0.30
slShortCandidate2 = swingHigh15m + ATR15m * 0.20
slShortBase = entryAvg + max(ATR15m * slAtrMult, entryAvg * minSlRawPct / 100)
slShort = max(slShortCandidate1, slShortCandidate2, slShortBase)
```

---

## 14. Multi TP Final

### 14.1 Risk value

LONG:

```text
risk = entryAvg - slLong
```

SHORT:

```text
risk = slShort - entryAvg
```

### 14.2 TP LONG

Prioritas structure:

```text
TP1 = resistance terdekat 15m atau 1R
TP2 = resistance 1H berikutnya atau 1.8R
TP3 = major resistance / extension atau 2.6R
```

Fallback:

```text
tp1Long = entryAvg + risk * 1.0
tp2Long = entryAvg + risk * 1.8
tp3Long = entryAvg + risk * 2.6
```

### 14.3 TP SHORT

Prioritas structure:

```text
TP1 = support terdekat 15m atau 1R
TP2 = support 1H berikutnya atau 1.8R
TP3 = major support / extension atau 2.6R
```

Fallback:

```text
tp1Short = entryAvg - risk * 1.0
tp2Short = entryAvg - risk * 1.8
tp3Short = entryAvg - risk * 2.6
```

### 14.4 TP validation

LONG valid:

```text
tp1 > entryAvg
tp2 > tp1
tp3 > tp2
sl < entryLow
```

SHORT valid:

```text
tp1 < entryAvg
tp2 < tp1
tp3 < tp2
sl > entryHigh
```

---

## 15. Risk & Leverage Final

### 15.1 Raw risk

```text
riskPct = abs(entryAvg - sl) / entryAvg * 100
```

### 15.2 Leveraged risk

```text
leveragedRiskPct = riskPct * inputLeverage
```

### 15.3 Recommended leverage

```text
recommendedLeverage = floor(maxAllowedLeveragedRisk / riskPct)
```

Default:

```text
maxAllowedLeveragedRisk = 20
```

### 15.4 Risk label

```text
SAFE       = leveragedRiskPct <= 25
RISKY      = leveragedRiskPct > 25 and <= 50
HIGH       = leveragedRiskPct > 50
RISKY_PLAN = recommendedLeverage < inputLeverage
```

### 15.5 Entry rule berdasarkan risk

```text
Jika riskPct > maxPlanRiskPct, jangan kirim VALID_ENTRY.
Jika recommendedLeverage < 1, jangan kirim VALID_ENTRY.
Jika recommendedLeverage < inputLeverage, tetap boleh kirim signal tetapi field risk_label harus RISKY_PLAN dan recommended_leverage wajib ada.
```

Untuk mode aman:

```text
Hanya kirim entry jika risk_label = SAFE.
```

---

## 16. Score Final

Gunakan scoring 100 poin.

| Komponen | Bobot |
|---|---:|
| 4H bias searah | 20 |
| 1H zone valid | 20 |
| 15m trigger valid | 20 |
| RVOL valid | 15 |
| RSI/MACD valid | 15 |
| Risk/Reward valid | 10 |

Kategori:

```text
85 - 100 = A+ setup
75 - 84  = A setup
70 - 74  = Valid setup
60 - 69  = Watch only
< 60     = No trade
```

Alert entry hanya dikirim jika:

```text
score >= 70
status = VALID_LONG atau VALID_SHORT
risk_label bukan HIGH
barstate.isconfirmed
cooldown sudah lewat
```

---

## 17. Alert Event Final

Event yang dikirim dari TradingView:

```text
LONG_ENTRY
SHORT_ENTRY
LONG_TP1_HIT
LONG_TP2_HIT
LONG_TP3_HIT
LONG_SL_HIT
SHORT_TP1_HIT
SHORT_TP2_HIT
SHORT_TP3_HIT
SHORT_SL_HIT
WAIT_RETEST_LONG
WAIT_RETEST_SHORT
CANCELLED
```

Untuk versi awal:

```text
Wajib: LONG_ENTRY, SHORT_ENTRY, TP1_HIT, TP2_HIT, TP3_HIT, SL_HIT
Optional: WAIT_RETEST alert
```

Rekomendasi:

```text
WAIT_RETEST tidak perlu dikirim ke channel utama.
WAIT_RETEST cukup untuk dashboard atau channel internal.
```

---

## 18. Alert JSON Final Flat Format

Gunakan flat JSON agar mudah diparse backend.

```json
{
  "market": "BINANCE_FUTURES",
  "type": "FUTURES_SIGNAL",
  "version": "2.0",
  "event": "SHORT_ENTRY",
  "symbol": "PORTALUSDT",
  "side": "SHORT",
  "tf_trigger": "15",
  "tf_zone": "60",
  "tf_bias": "240",
  "mode": "BREAKDOWN_RETEST",
  "status": "VALID_SHORT",
  "now": 0.0248,
  "entry_low": 0.0245,
  "entry_high": 0.0260,
  "entry_avg": 0.02525,
  "tp1": 0.0230,
  "tp2": 0.0215,
  "tp3": 0.0200,
  "sl": 0.0275,
  "risk_pct": 8.91,
  "rr_tp1": 0.89,
  "rr_tp2": 1.48,
  "rr_tp3": 2.08,
  "input_leverage": 10,
  "recommended_leverage": 3,
  "lev_risk_pct": 89.1,
  "risk_label": "RISKY_PLAN",
  "score": 82,
  "bias_4h": "BEARISH",
  "bias_strength_4h": "NORMAL",
  "zone_1h": "SUPPLY",
  "zone_score_1h": 78,
  "trigger_15m": "BEARISH_CONFIRMATION",
  "rsi": 42.5,
  "rvol": 145.2,
  "time": 1770000000000
}
```

Kenapa flat JSON:

- Lebih mudah diparse webhook.
- Lebih aman untuk formatting TradingView alert.
- Tidak terlalu panjang dibanding nested JSON.
- Mudah diubah menjadi pesan Telegram/Discord/backend.

---

## 19. Output Pesan Setelah Diterima Backend

Backend/webhook bisa mengubah JSON menjadi format ini:

```text
🚨 BINANCE FUTURES SIGNAL

PAIR: PORTALUSDT
SIDE: SHORT
MODE: BREAKDOWN RETEST
TIMEFRAME: 15m / 1H / 4H

Entry Zone: 0.0245 - 0.0260
TP1: 0.0230
TP2: 0.0215
TP3: 0.0200
SL: 0.0275

Risk: RISKY_PLAN
Recommended Leverage: 3x
Input Leverage: 10x
Score: 82

Bias 4H: BEARISH
Zone 1H: SUPPLY
RVOL: 145.2%
RSI: 42.5
```

Catatan:

```text
Jika risk_label = RISKY_PLAN, backend harus menampilkan warning:
"Gunakan leverage lebih kecil dari input, recommended leverage: 3x."
```

---

## 20. Dashboard Table Final

Kolom final yang disarankan:

```text
PAIR
BIAS
ZONE
NOW
ENTRY
TP1
TP2
TP3
SL
RISK
LEV
RSI
RVOL
MODE
STATUS
SCORE
SIGNAL
```

Jangan terlalu banyak kolom agar table tidak berat dan tetap terbaca.

Jika layar terlalu penuh, buat mode compact:

```text
PAIR
SIDE
NOW
ENTRY
TP1/TP2/TP3
SL
RISK
SCORE
STATUS
```

---

## 21. Active Trade State Final

Untuk setiap pair, simpan:

```pine
activeSide
activeEntryLow
activeEntryHigh
activeEntryAvg
activeTp1
activeTp2
activeTp3
activeSl
activeTp1Hit
activeTp2Hit
activeTp3Hit
activeMode
lastEvent
lastBar
```

Saat LONG:

```text
TP1 hit jika high >= TP1
TP2 hit jika high >= TP2
TP3 hit jika high >= TP3
SL hit jika low <= SL
```

Saat SHORT:

```text
TP1 hit jika low <= TP1
TP2 hit jika low <= TP2
TP3 hit jika low <= TP3
SL hit jika high >= SL
```

Same bar rule:

```text
Jika TP dan SL kena di candle yang sama, gunakan input sameBarRule.
Default: SL_FIRST agar konservatif.
```

---

## 22. Phase Implementasi Final

### Phase 1 — Refactor ringan dari script sekarang

```text
[ ] Pisahkan engine lama menjadi function kecil
[ ] Pertahankan alert JSON lama dulu
[ ] Pastikan output lama masih jalan
[ ] Kurangi return value yang tidak perlu
[ ] Pastikan semua string di security context diganti numeric flag
```

### Phase 2 — Tambah 4H Bias Engine

```text
[ ] Buat f_bias_engine()
[ ] Return biasFlag dan biasStrength
[ ] Request security 4H per pair
[ ] Decode flag di chart utama
[ ] Tambahkan bias ke dashboard
[ ] Tambahkan bias ke alert JSON
```

### Phase 3 — Tambah 1H Zone Engine

```text
[ ] Buat f_zone_engine()
[ ] Return zoneFlag, zoneLow, zoneHigh, zoneScore
[ ] Request security 1H per pair
[ ] Decode zone di chart utama
[ ] Tambahkan entry zone ke dashboard
[ ] Tambahkan entry_low dan entry_high ke alert JSON
```

### Phase 4 — Upgrade 15m Plan Engine

```text
[ ] Buat f_plan_engine()
[ ] Input dari 4H bias dan 1H zone dipakai di chart utama atau digabung secara ringkas
[ ] Hitung actionFlag
[ ] Hitung statusFlag
[ ] Hitung modeFlag
[ ] Hitung entryLow, entryHigh, entryAvg
[ ] Hitung TP1, TP2, TP3
[ ] Hitung SL
[ ] Hitung riskPct, RR, recommendedLeverage
[ ] Return hasil final saja
```

### Phase 5 — Tambah WAIT_RETEST

```text
[ ] Deteksi overextended dari EMA20 dan ATR
[ ] Jika overextended, status WAIT_RETEST
[ ] Jangan kirim entry market
[ ] Entry zone diarahkan ke retest area
```

### Phase 6 — Alert JSON v2

```text
[ ] Buat JSON flat format
[ ] Tambahkan version = 2.0
[ ] Tambahkan entry_low, entry_high, entry_avg
[ ] Tambahkan tp1, tp2, tp3
[ ] Tambahkan recommended_leverage
[ ] Tambahkan status dan mode
[ ] Tambahkan bias_4h dan zone_1h
[ ] Pastikan JSON valid tanpa trailing comma
```

### Phase 7 — Multi TP active state

```text
[ ] Tambahkan activeTp1, activeTp2, activeTp3
[ ] Tambahkan activeTp1Hit, activeTp2Hit, activeTp3Hit
[ ] Kirim event TP1/TP2/TP3 hit
[ ] Jangan reset posisi setelah TP1 jika TP2/TP3 belum hit
[ ] Reset posisi setelah TP3 atau SL
```

### Phase 8 — Batch testing

```text
[ ] Test 3 pair
[ ] Test 5 pair
[ ] Test 6 pair
[ ] Cek apakah ada error limit
[ ] Cek alert JSON valid
[ ] Cek webhook bisa parse
[ ] Cek sinyal tidak repaint berbahaya
[ ] Cek barstate.isconfirmed aktif
```

---

## 23. Acceptance Criteria Final

Sistem dianggap selesai jika:

```text
[ ] TradingView tidak kena memory/tuple/request limit untuk 3-5 pair
[ ] Alert keluar hanya saat candle confirmed
[ ] Alert JSON valid dan bisa diparse backend
[ ] Entry sudah berupa zone, bukan hanya close
[ ] TP sudah TP1, TP2, TP3
[ ] SL berdasarkan struktur + ATR
[ ] Ada recommended leverage
[ ] Ada status VALID, WAIT_RETEST, RISKY_PLAN, CONFLICT
[ ] Ada 4H bias filter
[ ] Ada 1H zone filter
[ ] Dashboard tetap ringan
[ ] Signal tidak entry saat harga terlalu overextended
[ ] Active trade bisa tracking TP1, TP2, TP3, dan SL
```

---

## 24. Prioritas Pengerjaan

Urutan paling aman:

```text
1. Ubah TP single menjadi TP1/TP2/TP3
2. Ubah entry single menjadi entry zone
3. Tambahkan recommended leverage
4. Tambahkan WAIT_RETEST
5. Tambahkan 1H zone engine
6. Tambahkan 4H bias engine
7. Update alert JSON v2
8. Update dashboard compact
9. Test batch 3-5 pair
10. Baru naik ke 6 pair jika masih aman
```

Kenapa 1H/4H tidak di awal?

```text
Karena perubahan TP/entry/alert bisa dilakukan dari engine 15m dulu.
Setelah format signal sudah benar, baru ditambah MTF agar tidak terlalu banyak perubahan sekaligus.
```

---

## 25. Kesimpulan Final

Karena alert berasal dari TradingView, desain final harus menjaga dua hal:

```text
1. Signal harus lebih bagus secara trading plan.
2. Script harus tetap ringan untuk limit TradingView.
```

Dengan batch kecil, sistem bisa dibuat cukup lengkap:

```text
4H bias + 1H zone + 15m trigger + entry zone + TP1/TP2/TP3 + SL struktur + recommended leverage + JSON alert v2
```

Namun tetap gunakan batas aman:

```text
Ideal: 3-5 pair per script
Maksimal: 6 pair per script
Jangan return string dari request.security
Jangan return data indikator mentah terlalu banyak
Return numeric flag dan hasil final saja
```

Target akhir bukan mengganti semua logic lama, tapi meng-upgrade logic lama agar tidak telat entry dan output alert-nya lebih siap dikirim ke Telegram/backend.
