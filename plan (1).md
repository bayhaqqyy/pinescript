# PLAN.md — Perbaikan PineScript Binance Futures untuk Trade 1–3 Jam

## 1. Tujuan Utama

Script `Binance USD-M Autobot A` akan diarahkan menjadi indikator/screener untuk **short-term futures trade / intraday scalp 1–3 jam**, bukan scalping 1–2 menit dan bukan swing terlalu lama.

Target karakter signal:

- Entry tidak terlalu telat.
- TP/SL tidak terlalu jauh untuk leverage.
- Signal tetap cukup selektif agar tidak terlalu banyak noise.
- Cocok untuk Binance USD-M Futures.
- Alert webhook harus mengirim data entry, TP, SL, risk, RR, dan status yang benar-benar sinkron.
- State posisi harus konsisten sampai TP/SL hit.

---

## 2. Masalah Utama dari Script Saat Ini

### 2.1 TP/SL Hit Masih Menggunakan `high` dan `low` Chart Utama

Masalah:

Saat ini logic TP/SL hit seperti ini:

```pinescript
longTpHit1 = activeSide1 == "LONG" and high >= activeTp1
longSlHit1 = activeSide1 == "LONG" and low <= activeSl1
shortTpHit1 = activeSide1 == "SHORT" and low <= activeTp1
shortSlHit1 = activeSide1 == "SHORT" and high >= activeSl1
```

`high` dan `low` tersebut adalah candle dari chart utama yang sedang dibuka, bukan candle dari pair yang diambil lewat `request.security()`.

Dampaknya:

- TP/SL pair A bisa dihitung dari candle pair lain.
- Alert TP/SL bisa salah.
- PnL dan status active position bisa tidak valid.
- Sangat berbahaya kalau alert langsung masuk ke bot.

Rencana fix:

- Return `high` dan `low` dari `f_dashboard_engine()`.
- Gunakan `hi1`, `lo1`, `hi2`, `lo2`, dan seterusnya untuk pengecekan TP/SL setiap pair.

Contoh arah fix:

```pinescript
// return engine
[close, high, low, sup, rst, finalEntry, finalTP, finalSL, rsiVal, rvol * 100.0, action, score, flowFlag, statusFlag]

// request.security
[now1, hi1, lo1, sup1, rst1, entry1, tp_1, sl_1, rsi1, rvolPct1, actionRaw1, score1, flowFlag1, statusFlag1] =
    request.security(tk1, tf, f_dashboard_engine())

// alert hit check
longTpHit1  = activeSide1 == "LONG" and hi1 >= activeTp1
longSlHit1  = activeSide1 == "LONG" and lo1 <= activeSl1
shortTpHit1 = activeSide1 == "SHORT" and lo1 <= activeTp1
shortSlHit1 = activeSide1 == "SHORT" and hi1 >= activeSl1
```

Prioritas: **WAJIB / BLOCKER**.

---

### 2.2 Entry Tidak Sinkron dengan Dasar Perhitungan TP/SL

Masalah:

Script saat ini menghitung entry internal seperti ini:

```pinescript
entryLong  = longBreak ? close : longTrigger
entryShort = shortBreak ? close : shortTrigger
```

Tetapi output akhir entry memakai:

```pinescript
finalEntry = action != 0 ? close : na
```

Dampaknya:

- TP/SL bisa dihitung dari `longTrigger` atau `shortTrigger`.
- Tetapi alert entry dikirim sebagai `close`.
- Risk, RR, TP, dan SL bisa tidak sesuai dengan harga entry yang dikirim.

Contoh masalah:

```text
close sekarang = 0.1000
longTrigger    = 0.1050
alert entry    = 0.1000
TP/SL dihitung dari 0.1050
```

Rencana fix:

Tentukan mode entry dengan jelas.

Untuk bot futures live, rekomendasi default:

```text
Mode entry = MARKET_ENTRY_ON_CLOSE
```

Artinya:

- Kalau signal valid saat candle close, entry = close.
- TP dan SL harus dihitung dari close yang sama.
- Jangan pakai trigger price untuk hitung TP/SL kalau alert-nya market entry.

Arah perubahan:

```pinescript
entryLong  = close
entryShort = close
```

Lalu breakout trigger hanya menjadi syarat validasi, bukan dasar harga entry.

Prioritas: **WAJIB / BLOCKER**.

---

### 2.3 Risk%, TP%, dan RR Saat Alert Entry Bisa 0 atau NO_DATA

Masalah:

Perhitungan `pctTp`, `riskPct`, dan `rr` mengambil dari `activeEntry`.

Pada candle entry pertama, `activeEntry` masih `na` sebelum update state. Akibatnya alert entry bisa terkirim dengan:

```json
"tp_pct": 0,
"risk_pct": 0,
"rr": 0,
"risk_label": "NO_DATA"
```

Padahal entry, TP, dan SL sudah ada.

Rencana fix:

- Untuk alert, hitung risk dari `alertEntry`, `alertTp`, dan `alertSl`.
- Jangan pakai nilai `pctTp1`, `riskPct1`, dan `rr1` yang berbasis `activeEntry` lama.

Contoh formula:

```pinescript
alertTpPct1 = not na(alertEntry1) and alertEntry1 > 0 ? math.abs(alertTp1 - alertEntry1) / alertEntry1 * 100.0 : na
alertRiskPct1 = not na(alertEntry1) and alertEntry1 > 0 ? math.abs(alertEntry1 - alertSl1) / alertEntry1 * 100.0 : na
alertRr1 = not na(alertRiskPct1) and alertRiskPct1 > 0 ? alertTpPct1 / alertRiskPct1 : na
alertLevTp1 = alertTpPct1 * leverage
alertLevRisk1 = alertRiskPct1 * leverage
alertRiskLabel1 = f_risk_label(alertLevRisk1)
```

JSON alert harus pakai:

```pinescript
alertTpPct1
alertRiskPct1
alertRr1
alertLevTp1
alertLevRisk1
alertRiskLabel1
```

Prioritas: **WAJIB / BLOCKER**.

---

### 2.4 `liq_warn` dan `max_safe_leverage` Salah Saat Posisi Sudah Aktif

Masalah:

Saat posisi aktif, `action` bisa kembali `WAIT`, tetapi `activeSide` masih berisi `LONG` atau `SHORT`.

Logic sekarang masih banyak bergantung pada `action`, misalnya:

```pinescript
liqWarn1 = action1 == "LONG" ? liqWarnLong1 : action1 == "SHORT" ? liqWarnShort1 : "SAFE"
```

Dampaknya:

- Posisi masih aktif tapi liquidation warning bisa tampil `SAFE`.
- `max_safe_leverage` bisa balik ke default.
- Table dan alert tidak menggambarkan risiko posisi aktif.

Rencana fix:

Gunakan `activeSide` sebagai prioritas.

```pinescript
sideForRisk1 = activeSide1 != "" ? activeSide1 : action1

liqWarn1 = sideForRisk1 == "LONG" ? liqWarnLong1 :
           sideForRisk1 == "SHORT" ? liqWarnShort1 :
           "SAFE"
```

Prioritas: **TINGGI**.

---

### 2.5 TP dan SL Bisa Kena di Candle yang Sama

Masalah:

Kalau dalam satu candle `high >= TP` dan `low <= SL`, script harus menentukan event mana yang dianggap terjadi dulu.

Untuk LONG saat ini prioritas TP lebih dulu:

```pinescript
event1 = longTpHit ? "LONG_TP_HIT" : longSlHit ? "LONG_SL_HIT" : ...
```

Ini terlalu optimis.

Rencana fix:

Tambahkan input:

```pinescript
sameBarRule = input.string("SL_FIRST", "Same Bar TP/SL Rule", options=["SL_FIRST", "TP_FIRST", "IGNORE"])
```

Default rekomendasi:

```text
SL_FIRST
```

Karena untuk bot dan risk management, lebih aman konservatif.

Prioritas: **TINGGI**.

---

## 3. Penyesuaian Strategi untuk Hold 1–3 Jam

### 3.1 Karakter yang Diinginkan

Karena target hold 1–3 jam, maka signal tidak perlu secepat 1m scalping, tetapi juga jangan terlalu lebar seperti swing.

Karakter ideal:

```text
Timeframe utama: 15m
Opsional trigger cepat: 5m
Hold target: 4–12 candle pada 15m
SL raw: sekitar 0.6%–1.2%
TP raw: sekitar 1.0%–2.0%
RR: 1.5–1.8
Leverage: 5x–10x
```

---

### 3.2 Preset Default Rekomendasi

Gunakan preset ini sebagai baseline pertama.

```pinescript
tf = "15"
srLen = 14
atrLen = 14
leverage = 10

entryScore = 65
scoreGap = 6

slAtrMult = 1.4
tpAtrMult = 2.4
minRR = 1.6

minSlRawPct = 0.6
minTpRawPct = 1.0

maxPlanRiskPct = 2.0
maxLevRiskPct = 25.0

breakoutBufferPct = 0.04
srAtrBuffer = 0.15
useStructureSL = true
maxStructureRiskPct = 2.5

cooldownBars = 3
```

Alasan:

- Lebih responsif dari setting lama.
- Tidak terlalu sempit seperti scalping 1 menit.
- TP/SL masih masuk akal untuk hold 1–3 jam.
- Risk leverage lebih dijaga.

---

### 3.3 Preset Lebih Aman

Gunakan jika signal terlalu banyak atau pair terlalu noise.

```pinescript
tf = "15"
srLen = 20
atrLen = 14
leverage = 5

entryScore = 70
scoreGap = 8

slAtrMult = 1.6
tpAtrMult = 3.0
minRR = 1.8

minSlRawPct = 0.8
minTpRawPct = 1.4

maxPlanRiskPct = 2.5
maxLevRiskPct = 25.0

breakoutBufferPct = 0.05
srAtrBuffer = 0.20
maxStructureRiskPct = 3.0
cooldownBars = 4
```

Cocok untuk:

- Pair volatile.
- Kondisi market choppy.
- User ingin lebih sedikit signal tapi lebih selektif.

---

### 3.4 Preset Lebih Cepat tapi Masih 1–3 Jam

Gunakan jika full 15m terasa telat.

```pinescript
tf = "5"
srLen = 20
atrLen = 14
leverage = 10

entryScore = 65
scoreGap = 6

slAtrMult = 1.2
tpAtrMult = 2.0
minRR = 1.5

minSlRawPct = 0.5
minTpRawPct = 0.9

maxPlanRiskPct = 1.5
maxLevRiskPct = 20.0

breakoutBufferPct = 0.03
srAtrBuffer = 0.12
maxStructureRiskPct = 2.0
cooldownBars = 5
```

Catatan:

- TF 5m bukan berarti hold hanya 5 menit.
- TF 5m bisa dipakai untuk entry lebih cepat, tetapi exit tetap bisa 1–3 jam.
- Wajib pakai trend filter agar tidak terlalu noise.

---

## 4. Rekomendasi Arsitektur Signal

### 4.1 Pisahkan Mode Signal

Saat ini script mencampur:

- trend-following,
- breakout,
- reversal,
- absorption,
- flow,
- scoring.

Rencana perubahan:

Buat mode signal lebih jelas:

```text
MODE_TREND_SCALP
MODE_PULLBACK_SCALP
MODE_BREAKOUT_SCALP
MODE_REVERSAL_WARNING
```

Default untuk bot:

```text
Entry boleh dari TREND, PULLBACK, BREAKOUT.
REVERSAL hanya warning dulu, bukan entry utama.
```

---

### 4.2 Trend Scalp

LONG valid jika:

```text
close > EMA fast
EMA fast > EMA slow
RSI 50–72
MACD histogram > 0 dan naik
RVOL >= 1.0
candle hijau dan close dekat high
not overheat
risk valid
```

SHORT valid jika kebalikannya.

Fungsi:

- Cocok untuk ikut arah market.
- Lebih aman untuk leverage dibanding countertrend.

---

### 4.3 Pullback Scalp

Tambahkan mode pullback karena untuk hold 1–3 jam biasanya entry terbaik bukan saat harga sudah terlalu jauh, tetapi setelah koreksi kecil.

LONG pullback valid jika:

```text
trend 15m bullish
harga sempat dekat EMA fast / EMA slow pendek
candle reclaim hijau
RSI kembali di atas 50
histogram membaik
volume valid
```

SHORT pullback valid jika:

```text
trend 15m bearish
harga sempat naik ke area EMA
candle reject merah
RSI kembali di bawah 50
histogram melemah
volume valid
```

Rencana implementasi sederhana:

```pinescript
nearEmaLong = low <= emaFast + atrVal * 0.25 and close > emaFast
nearEmaShort = high >= emaFast - atrVal * 0.25 and close < emaFast

longPullbackAction = trendLong and nearEmaLong and greenCandle and closeNearHigh and hist > hist[1] and rsiVal > 50 and volOk
shortPullbackAction = trendShort and nearEmaShort and redCandle and closeNearLow and hist < hist[1] and rsiVal < 50 and volOk
```

---

### 4.4 Breakout Scalp

Breakout tetap boleh dipakai, tetapi jangan terlalu jauh.

Rencana:

- `srLen` default turun dari 20 ke 14 untuk 15m.
- `breakoutBufferPct` turun dari 0.05 ke 0.04.
- Entry tetap `close`, bukan trigger price.
- Breakout harus didukung volume.

LONG breakout:

```text
close > resistance + buffer
green candle
close near high
RVOL >= 1.1
not overheat parah
```

SHORT breakdown:

```text
close < support - buffer
red candle
close near low
RVOL >= 1.1
not oversold parah
```

---

### 4.5 Reversal Jangan Jadi Entry Utama

Masalah sebelumnya:

Script bisa memberi SHORT ketika harga sedang naik kuat hanya karena overheat + upper wick.

Rencana:

- `OVERHEAT` = warning.
- `OVERSOLD` = warning.
- Jangan otomatis menjadi SHORT/LONG.
- Reversal hanya valid kalau ada konfirmasi struktur.

SHORT reversal baru valid jika:

```text
overheat
upper rejection
red candle
close below EMA fast
histogram turun
RSI mulai turun dari area tinggi
```

LONG reversal baru valid jika:

```text
oversold
lower rejection
green candle
close above EMA fast
histogram naik
RSI mulai naik dari area rendah
```

Implementasi awal:

```pinescript
longReversalAction = oversold and lowerReject and greenCandle and closeNearHigh and rvol >= 1.2 and hist > hist[1] and close > emaFast
shortReversalAction = overheat and upperReject and redCandle and closeNearLow and rvol >= 1.2 and hist < hist[1] and close < emaFast
```

Untuk mode bot pertama, bisa juga matikan reversal entry:

```pinescript
useReversalEntry = input.bool(false, "Use Reversal As Entry")
```

---

## 5. Rencana TP/SL untuk 1–3 Jam

### 5.1 Default TP/SL

Gunakan kombinasi ATR dan raw percentage.

Default rekomendasi:

```text
SL = max(ATR * 1.4, entry * 0.6%)
TP = max(ATR * 2.4, entry * 1.0%, SL distance * 1.6)
```

Tujuannya:

- SL tidak terlalu kecil sehingga tidak gampang kena noise.
- TP tidak terlalu jauh sehingga masih realistis untuk 1–3 jam.
- RR tetap sehat.

---

### 5.2 Structure SL

Structure SL tetap dipakai, tapi jangan terlalu jauh.

Saat ini `maxStructureRiskPct = 6.0` terlalu besar untuk leverage dan hold 1–3 jam.

Rekomendasi:

```pinescript
maxStructureRiskPct = 2.5
srAtrBuffer = 0.15
```

Jika structure SL lebih dari 2.5% raw, jangan pakai structure SL. Pakai ATR/raw SL saja.

---

### 5.3 Optional Break Even

Tambahkan tahap lanjutan setelah bug utama selesai.

Rule sederhana:

```text
Jika harga sudah mencapai 50% jarak menuju TP, SL bisa dinaikkan ke entry.
```

Untuk LONG:

```text
BE trigger = entry + (TP - entry) * 0.5
SL baru = entry
```

Untuk SHORT:

```text
BE trigger = entry - (entry - TP) * 0.5
SL baru = entry
```

Catatan:

- Untuk alert webhook, event bisa berupa `MOVE_SL_BE`.
- Jangan implementasikan BE sebelum state TP/SL dasar sudah valid.

---

## 6. Rencana Alert JSON

### 6.1 Field yang Wajib Benar

Setiap alert entry harus mengirim:

```json
{
  "market": "BINANCE_FUTURES",
  "type": "FUTURES_SIGNAL",
  "strategy_version": "v2_intraday_1_3h",
  "event": "LONG_ENTRY",
  "side": "LONG",
  "symbol": "BTCUSDT",
  "tf": "15",
  "mode": "TREND_SCALP",
  "now": 0,
  "entry": 0,
  "tp": 0,
  "sl": 0,
  "tp_pct": 0,
  "risk_pct": 0,
  "rr": 0,
  "leverage": 10,
  "lev_tp_pct": 0,
  "lev_risk_pct": 0,
  "risk_label": "SAFE",
  "score": 0,
  "flow": "NORMAL",
  "signal": "LONG",
  "time": 0
}
```

### 6.2 Tambahkan `mode`

`mode` berguna agar bot tahu asal signal:

```text
TREND_SCALP
PULLBACK_SCALP
BREAKOUT_SCALP
REVERSAL_ENTRY
```

Untuk tahap awal, cukup encode sebagai flag angka dari `request.security()`, lalu decode di luar seperti `flowFlag`.

---

## 7. Refactor Struktur Code

### 7.1 Jangan Terlalu Banyak Copy-Paste per Pair

Script saat ini mengulang logic pair 1 sampai pair 8 secara manual.

Masalah:

- Sulit maintenance.
- Risiko bug di satu pair tidak diperbaiki di pair lain.
- Kalau pair ditambah, code makin panjang.
- Risiko limit PineScript makin besar.

Rencana refactor bertahap:

Tahap 1:

- Tetap 8 pair manual.
- Perbaiki bug core dulu.
- Pastikan behavior benar.

Tahap 2:

- Buat helper function untuk:
  - decode action,
  - decode flow,
  - decode status,
  - hitung risk,
  - build JSON.

Tahap 3:

- Pertimbangkan array symbol dan loop.
- Jangan dilakukan sebelum logic inti stabil.

---

## 8. Urutan Implementasi

### Phase 1 — Fix Bug Core

Checklist:

- [ ] Return `high` dan `low` dari `f_dashboard_engine()`.
- [ ] Ganti TP/SL hit agar memakai high/low dari masing-masing symbol.
- [ ] Samakan entry dengan TP/SL calculation.
- [ ] Pakai `MARKET_ENTRY_ON_CLOSE` sebagai default.
- [ ] Hitung alert risk dari `alertEntry`, `alertTp`, dan `alertSl`.
- [ ] Ganti `liq_warn` agar memakai `activeSide`.
- [ ] Tambahkan handling same-bar TP/SL.
- [ ] Fix mapping `Top Left` ke `position.top_left`.

Output phase 1:

```text
Alert entry valid
Alert TP/SL valid
Risk dan RR tidak 0 saat entry
TP/SL tidak dihitung dari chart lain
```

---

### Phase 2 — Preset 1–3 Jam

Checklist:

- [ ] Ubah default input ke preset balanced 1–3 jam.
- [ ] Turunkan `entryScore` dari 70 ke 65.
- [ ] Turunkan `scoreGap` dari 8 ke 6.
- [ ] Turunkan `slAtrMult` dari 2.0 ke 1.4.
- [ ] Turunkan `tpAtrMult` dari 4.0 ke 2.4.
- [ ] Turunkan `minRR` dari 2.0 ke 1.6.
- [ ] Turunkan `minSlRawPct` dari 1.0 ke 0.6.
- [ ] Turunkan `minTpRawPct` dari 2.0 ke 1.0.
- [ ] Turunkan `maxPlanRiskPct` dari 5.0 ke 2.0.
- [ ] Turunkan `maxLevRiskPct` dari 65.0 ke 25.0.
- [ ] Turunkan `maxStructureRiskPct` dari 6.0 ke 2.5.

Output phase 2:

```text
Signal lebih cocok untuk hold 1–3 jam
TP/SL tidak terlalu jauh
Risk leverage lebih sehat
```

---

### Phase 3 — Perbaikan Signal Logic

Checklist:

- [ ] Tambahkan `useReversalEntry` default `false`.
- [ ] Buat reversal hanya warning jika belum ada konfirmasi EMA.
- [ ] Tambahkan pullback action.
- [ ] Tambahkan mode flag: trend, pullback, breakout, reversal.
- [ ] Prioritaskan trend dan pullback daripada reversal.
- [ ] Jangan SHORT saat bullish impulse kuat.
- [ ] Jangan LONG saat bearish impulse kuat.

Output phase 3:

```text
Signal tidak gampang melawan trend besar
Entry lebih natural untuk 1–3 jam
Market overheat/oversold jadi warning, bukan asal entry lawan arah
```

---

### Phase 4 — Validasi Manual di TradingView

Test minimal untuk setiap pair:

- [ ] Cek 50 signal terakhir.
- [ ] Cek apakah entry di candle close yang benar.
- [ ] Cek apakah TP/SL berada di arah yang benar.
- [ ] Cek apakah TP/SL hit sesuai candle symbol tersebut.
- [ ] Cek apakah alert entry risk tidak 0.
- [ ] Cek apakah alert TP/SL tidak double.
- [ ] Cek apakah signal SHORT tidak muncul saat market jelas bullish tanpa breakdown.
- [ ] Cek apakah signal LONG tidak muncul saat market jelas bearish tanpa reclaim.

---

## 9. Acceptance Criteria

Script dianggap valid untuk lanjut ke bot jika:

```text
1. Entry, TP, dan SL selalu dihitung dari harga dasar yang sama.
2. Alert entry selalu punya risk_pct, tp_pct, rr, lev_risk_pct yang benar.
3. TP/SL hit memakai high/low dari symbol yang benar.
4. Signal tidak repaint parah pada candle close.
5. Signal cocok untuk hold 1–3 jam, bukan terlalu cepat dan bukan terlalu jauh.
6. Reversal tidak menjadi entry utama tanpa konfirmasi tambahan.
7. State active position konsisten sampai TP/SL hit.
8. JSON webhook tetap valid dan mudah diproses bot.
```

---

## 10. Default Final yang Direkomendasikan

Untuk implementasi awal, gunakan konfigurasi berikut:

```pinescript
tf = input.timeframe("15", "Timeframe Screener")
srLen = input.int(14, "S/R Length")
atrLen = input.int(14, "ATR Length")
leverage = input.int(10, "Leverage", minval=1, maxval=125)

entryScore = input.int(65, "Entry Score")
scoreGap = input.int(6, "Score Gap")

slAtrMult = input.float(1.4, "SL ATR Mult", step=0.1)
tpAtrMult = input.float(2.4, "TP ATR Mult", step=0.1)
minRR = input.float(1.6, "Minimum RR", step=0.1)

minSlRawPct = input.float(0.6, "Minimum SL Raw %", step=0.1)
minTpRawPct = input.float(1.0, "Minimum TP Raw %", step=0.1)
maxPlanRiskPct = input.float(2.0, "Max Raw Risk % For Action", step=0.5)
maxLevRiskPct = input.float(25.0, "Max Leveraged Risk % For Action", step=5.0)

breakoutBufferPct = input.float(0.04, "Breakout Buffer %", step=0.01)
srAtrBuffer = input.float(0.15, "S/R ATR Buffer", step=0.05)
useStructureSL = input.bool(true, "Use Structure SL When Reasonable")
maxStructureRiskPct = input.float(2.5, "Max Structure SL %", step=0.5)

cooldownBars = input.int(3, "Alert Cooldown Bars", minval=1)
useReversalEntry = input.bool(false, "Use Reversal As Entry")
sameBarRule = input.string("SL_FIRST", "Same Bar TP/SL Rule", options=["SL_FIRST", "TP_FIRST", "IGNORE"])
```

---

## 11. Catatan Penting untuk Agent/Coder

Jangan langsung refactor besar sebelum bug core selesai.

Urutan wajib:

```text
1. Benarkan akurasi data high/low symbol.
2. Benarkan sinkronisasi entry, TP, SL.
3. Benarkan risk alert.
4. Baru tuning preset 1–3 jam.
5. Baru tambah pullback/reversal filter.
6. Baru refactor code agar lebih rapi.
```

Alasan:

Kalau tuning dilakukan sebelum bug core selesai, hasil backtest atau visual review tetap bisa menipu karena TP/SL dan risk belum valid.

