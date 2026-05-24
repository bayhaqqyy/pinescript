# FIX.md — Final Implementation Brief

Repo: `bayhaqqyy/pinescript`  
Scope: **TradingView screener + Telegram alert**, bukan auto-trading bot.

Dokumen ini menggantikan `fix.md` sebelumnya. Fokus revisi terbaru:

1. Binance Futures table harus kembali **readable dan actionable**.
2. Harga/price precision yang sudah benar **jangan diubah mundur**.
3. Kolom risk seperti `L-RISK`, `MAXLEV`, dan `LIQ` jangan membuat tabel jadi penuh dan membingungkan.
4. `ACTION` tidak boleh berisi `LEV-RISK`. `ACTION` hanya boleh `LONG`, `SHORT`, atau `WAIT`.
5. Risk/leverage tetap dihitung, tetapi dipisahkan sebagai **warning**, bukan mengganti sinyal utama.
6. Telegram hanya menerima event actionable: `LONG_ENTRY`, `SHORT_ENTRY`, `BUY_ENTRY`, `SELL_EXIT`, `TP_HIT`, `SL_HIT`.

---

## 0. Research Basis / Prinsip Implementasi

Gunakan prinsip dari dokumentasi resmi berikut:

| Area | Prinsip |
|---|---|
| TradingView `request.security()` | Data multi-symbol harus diambil dari konteks symbol masing-masing. Jangan memakai `close`, `volume`, atau `syminfo` chart utama untuk symbol lain. |
| TradingView alert | `alert()` harus dipanggil hanya saat kondisi valid. Gunakan `barstate.isconfirmed` dan `alert.freq_once_per_bar_close` agar alert keluar di candle close. |
| TradingView bar state | `barstate.isconfirmed` benar untuk menghindari repaint, tetapi jangan dipakai sebagai expression di dalam `request.security()`. Pakai di luar saat trigger alert. |
| Binance Futures `exchangeInfo` | Tick size tiap pair berasal dari `PRICE_FILTER.tickSize`. Price harus dibulatkan ke tick size symbol masing-masing. |
| Binance Futures volume | Untuk ranking dari API gunakan `quoteVolume`. Untuk Pine table, notional bar bisa diproksikan `close * volume`. |
| Binance liquidation | Liquidation asli Binance memakai Mark Price, maintenance margin, margin mode, balance, dan tier risk. Pine dashboard hanya boleh memberi **approx risk warning**, bukan liquidation price final. |

Catatan penting:

- Jangan menampilkan atau mengklaim liquidation price presisi di Pine table.
- `LEV-RISK` bukan sinyal trading. Itu hanya alasan kenapa setup tidak layak dikirim ke Telegram.
- Screener harus membantu user membaca peluang, bukan membuat semua baris jadi `LEV-RISK`.

---

## 1. Scope yang Tidak Perlu

Karena sistem berjalan di VPS sendiri dan hanya sebagai screener Telegram, item berikut **hapus / skip**:

| Item | Status |
|---|---|
| Cloudflare Tunnel | Tidak perlu |
| `CLOUDFLARE_TUNNEL_TOKEN` | Tidak perlu |
| `cloudflared` service | Tidak perlu |
| TryCloudflare URL | Tidak perlu |
| Broker integration | Tidak perlu |
| Auto-order / execution engine | Tidak perlu |
| Portfolio risk engine | Tidak perlu |
| Kafka/RabbitMQ/Redis queue berat | Tidak perlu |

Tetap perlu:

- `WEBHOOK_SECRET` untuk endpoint VPS.
- HTML escaping di Telegram formatter.
- Logging sederhana optional.

---

## 2. File yang Perlu Diubah

Jangan edit file generated Pine secara manual. Ubah generator lalu regenerate.

```text
main.py
tv_scripts/generate_screener.py
tv_scripts/generate_pine_scripts.py
tv_scripts/filter_scalping_stocks.py
tv_scripts/fetch_idx_prices.py
tv_scripts/us/generate_us_scripts.py
requirements.txt
.env.example
README.md
```

Generated Pine yang tidak boleh diedit manual:

```text
tv_scripts/scalping_v2_batch_*.pine
tv_scripts/bandar_ai_v2_batch_*.pine
tv_scripts/generated_screeners/*.pine
tv_scripts/us/us_swing_batch_*.pine
tv_scripts/us/us_bandar_ai_batch_*.pine
```

Regenerate setelah patch:

```bash
python tv_scripts/filter_scalping_stocks.py
python tv_scripts/generate_pine_scripts.py
python tv_scripts/generate_screener.py
python tv_scripts/us/generate_us_scripts.py
```

---

## 3. Prioritas Final

| Priority | Area | File | Target |
|---|---|---|---|
| P0 | Simplify Binance Futures table | `generate_screener.py` | Table readable, tidak overload `L-RISK/MAXLEV/LIQ`. |
| P0 | Separate ACTION from RISK | `generate_screener.py` | `ACTION` hanya `LONG`, `SHORT`, `WAIT`. Tidak boleh `LEV-RISK`. |
| P0 | Fix NaN / missing data | `generate_screener.py` | Tidak ada `NaN`, `NaNx`, `NaN%`. Pakai `-` atau `WAIT_DATA`. |
| P0 | Preserve price precision | `generate_screener.py` | Harga yang sudah benar tetap ikut tick size per symbol. Jangan regress ke fixed 4 decimal. |
| P0 | Directional TP/SL | `generate_screener.py` | LONG: TP > ENTRY, SL < ENTRY. SHORT: TP < ENTRY, SL > ENTRY. |
| P0 | Leverage-aware warning | `generate_screener.py` | Risk dihitung, tapi jadi kolom warning, bukan sinyal utama. |
| P0 | Telegram actionable-only | generator + `main.py` | Telegram hanya kirim event valid, bukan `WAIT`, `NETRAL`, `LEV-RISK`. |
| P0 | IDX transaction value bug | `generate_pine_scripts.py` | Value dihitung di dalam `request.security()`. |
| P0 | Webhook secret + HTML escape | `main.py` | Endpoint VPS aman dan message Telegram tidak rusak. |
| P1 | Visual standardization | semua generator | Tampilan table seragam dan mudah dibaca. |
| P1 | README sync | `README.md` | Jelaskan sistem sebagai screener + Telegram alert. |

---

# P0-01 — Simplify Binance Futures Table

## Problem dari screenshot terakhir

Tabel Binance Futures terlalu penuh dan sulit dibaca karena kolom risk ditaruh sebagai kolom utama:

```text
L-RISK | MAXLEV | LIQ | STATUS | ACTION | SIGNAL
```

Masalah yang muncul:

- Mayoritas baris jadi `LEV-RISK`.
- `ACTION` berisi `LEV-RISK`, padahal action seharusnya arah trading.
- `MAXLEV` menghasilkan `1x`, `2x`, `NaNx`, sehingga tabel terlihat kacau.
- `LIQ` seperti `NEAR-LIQ` mendominasi screen, padahal liquidation tidak bisa dihitung presisi dari Pine.
- User sulit tahu mana yang benar-benar `LONG`, `SHORT`, atau `WAIT`.

## Required fix

Gunakan table utama yang lebih sederhana:

```text
PAIR | TF | ENTRY | NOW | TP | SL | TP% | RISK% | RR | LEV | RISK | STATUS | RSI | MACD | RVOL | FLOW | ACTION | SCORE | SIGNAL
```

## Kolom yang dihapus dari main table

Hapus dari main table default:

```text
L-RISK
MAXLEV
LIQ
```

Jika masih ingin dipakai untuk debugging, buat input:

```pine
showDebugRisk = input.bool(false, "Show Debug Risk Columns")
```

Saat `showDebugRisk = true`, boleh tampilkan:

```text
LEV_RISK% | MAX_SAFE_LEV | LIQ_WARN
```

Default harus `false`.

---

# P0-02 — ACTION, STATUS, SIGNAL Harus Dipisah

## Definisi final

### `STATUS`
Menjelaskan kondisi market.

Allowed values:

```text
LONG SETUP
SHORT SETUP
BREAKOUT
BREAKDOWN
WAIT
WAIT_DATA
RISKY_SETUP
```

### `ACTION`
Menjelaskan aksi yang boleh dipertimbangkan user.

Allowed values:

```text
LONG
SHORT
WAIT
```

Tidak boleh ada:

```text
LEV-RISK
NEAR-LIQ
SAFE
RISKY
HIGH
```

di kolom `ACTION`.

### `RISK`
Menjelaskan warning leverage/risk.

Allowed values:

```text
SAFE
RISKY
HIGH
NO_DATA
```

### `SIGNAL`
Ringkasan akhir untuk visual.

Allowed values:

```text
LONG
SHORT
NEUTRAL
RISKY
WEAK
WAIT_DATA
```

## Logic final

```pine
technicalSide =
     scoreLong >= entryScore and scoreLong > scoreShort + scoreGap ? "LONG" :
     scoreShort >= entryScore and scoreShort > scoreLong + scoreGap ? "SHORT" :
     "NEUTRAL"

riskOk = riskLabel != "HIGH" and not na(levRiskPct) and rr >= minRR
validData = not na(finalEntry) and not na(finalTP) and not na(finalSL) and not na(riskPct) and not na(rr)

action =
     not validData ? "WAIT" :
     technicalSide == "LONG" and riskOk and dirOkLong ? "LONG" :
     technicalSide == "SHORT" and riskOk and dirOkShort ? "SHORT" :
     "WAIT"

status =
     not validData ? "WAIT_DATA" :
     technicalSide == "LONG" and not riskOk ? "RISKY_SETUP" :
     technicalSide == "SHORT" and not riskOk ? "RISKY_SETUP" :
     technicalSide == "LONG" ? "LONG SETUP" :
     technicalSide == "SHORT" ? "SHORT SETUP" :
     "WAIT"

signal =
     not validData ? "WAIT_DATA" :
     action == "LONG" ? "LONG" :
     action == "SHORT" ? "SHORT" :
     technicalSide != "NEUTRAL" and not riskOk ? "RISKY" :
     math.max(scoreLong, scoreShort) >= 55 ? "WEAK" :
     "NEUTRAL"
```

Acceptance:

```text
STATUS = SHORT SETUP, ACTION = WAIT boleh hanya jika RISK = HIGH / data invalid.
ACTION tidak pernah berisi LEV-RISK.
SIGNAL tidak pernah berisi LEV-RISK.
RISK warning tampil hanya di kolom RISK.
```

---

# P0-03 — No NaN Display

## Problem

Screenshot masih menunjukkan:

```text
NaN
NaN%
NaNx
```

Ini harus dihilangkan total.

## Required helper

```pine
f_fmt_num(x, pattern) =>
    na(x) ? "-" : str.tostring(x, pattern)

f_fmt_pct(x) =>
    na(x) ? "-" : str.tostring(x, "#.##") + "%"

f_fmt_x(x) =>
    na(x) ? "-" : str.tostring(x, "#") + "x"
```

Untuk price tetap gunakan helper tick-size, bukan `f_fmt_num` biasa.

```pine
f_round_to_tick(x, tick) =>
    na(x) or na(tick) or tick <= 0 ? na : math.round(x / tick) * tick

f_fmt_price(x, tick) =>
    px = f_round_to_tick(x, tick)
    na(px) ? "-" :
     tick >= 1          ? str.tostring(px, "#") :
     tick >= 0.1        ? str.tostring(px, "#.0") :
     tick >= 0.01       ? str.tostring(px, "#.00") :
     tick >= 0.001      ? str.tostring(px, "#.000") :
     tick >= 0.0001     ? str.tostring(px, "#.0000") :
     tick >= 0.00001    ? str.tostring(px, "#.00000") :
     tick >= 0.000001   ? str.tostring(px, "#.000000") :
     tick >= 0.0000001  ? str.tostring(px, "#.0000000") :
     tick >= 0.00000001 ? str.tostring(px, "#.00000000") :
                          str.tostring(px, "#.0000000000")
```

Acceptance:

```bash
grep -R "NaN" -n tv_scripts/generated_screeners/*.pine
```

Tidak wajib nol karena string source bisa ada guard, tetapi di TradingView table runtime tidak boleh tampil `NaN`, `NaNx`, atau `NaN%`.

---

# P0-04 — Preserve Price Precision yang Sudah Benar

## Status

Dari feedback terbaru, price precision sekarang sudah lebih benar. Jangan regress.

## Rule wajib

- Jangan pakai fixed decimal global seperti `#.####` untuk semua futures pair.
- Jangan pakai `math.round(price, 4)`.
- Setiap pair harus punya `tickSize` dari Binance `exchangeInfo`.
- Semua field harga wajib round dan format sesuai tick size.

Field harga:

```text
SUP
RST
ENTRY
NOW
TP
SL
```

## Python generator target

Di `generate_screener.py`, ambil metadata:

```python
def price_decimals_from_tick(tick_size: str) -> int:
    s = tick_size.rstrip("0")
    if "." not in s:
        return 0
    return len(s.split(".")[1])
```

Generated Pine harus punya per symbol:

```pine
tk1 = "BINANCE:1000PEPEUSDT.P"
tick1 = 0.0000001
```

Jika format ticker repo bukan `.P`, ikuti format yang sudah compile di TradingView.

---

# P0-05 — Directional TP/SL Binance Futures

## Hard rule

```text
LONG  => TP > ENTRY dan SL < ENTRY
SHORT => TP < ENTRY dan SL > ENTRY
```

Jika rule ini gagal, signal harus `NEUTRAL` / `WAIT_DATA`, bukan tetap dipaksa.

## Inputs rekomendasi

```pine
srLen = input.int(20, "S/R Length")
atrLen = input.int(14, "ATR Length")
leverage = input.int(10, "Leverage", minval=1, maxval=125)

entryScore = input.int(70, "Entry Score")
scoreGap = input.int(8, "Score Gap")

slAtrMult = input.float(1.5, "SL ATR Mult", step=0.1)
tpAtrMult = input.float(3.0, "TP ATR Mult", step=0.1)
minRR = input.float(1.8, "Minimum RR", step=0.1)

minSlRawPct = input.float(0.6, "Minimum SL Raw %", step=0.1)
minTpRawPct = input.float(1.2, "Minimum TP Raw %", step=0.1)
maxPlanRiskPct = input.float(5.0, "Max Raw Risk % For Action", step=0.5)
maxLevRiskPct = input.float(65.0, "Max Leveraged Risk % For Action", step=5.0)

breakoutBufferPct = input.float(0.05, "Breakout Buffer %", step=0.01)
srAtrBuffer = input.float(0.20, "S/R ATR Buffer", step=0.05)
useStructureSL = input.bool(true, "Use Structure SL When Reasonable")
maxStructureRiskPct = input.float(6.0, "Max Structure SL %", step=0.5)
```

## Support / resistance non-repaint

```pine
sup = ta.lowest(low[1], srLen)
rst = ta.highest(high[1], srLen)
```

Alasan pakai `[1]`: breakout tidak dibandingkan dengan high/low candle yang sama.

## Entry trigger

Gunakan tick symbol, bukan `syminfo.mintick` chart utama.

```pine
buf = breakoutBufferPct / 100.0
longTriggerRaw  = rst * (1 + buf)
shortTriggerRaw = sup * (1 - buf)

longTrigger  = f_round_to_tick(longTriggerRaw, tick)
shortTrigger = f_round_to_tick(shortTriggerRaw, tick)

longBreak  = close >= longTrigger
shortBreak = close <= shortTrigger

entryLong  = longBreak ? close : longTrigger
entryShort = shortBreak ? close : shortTrigger
```

## SL distance v3: ATR + min percent + structure only if reasonable

Jangan selalu pakai structure SL jika support/resistance terlalu jauh, karena itu membuat `riskPct` sangat besar dan semua pair jadi `LEV-RISK`.

### LONG

```pine
baseSlLongDist = math.max(atrVal * slAtrMult, entryLong * minSlRawPct / 100.0, tick)
structSlLong = sup - atrVal * srAtrBuffer
structSlLongDist = entryLong - structSlLong
structRiskLongPct = entryLong > 0 ? structSlLongDist / entryLong * 100.0 : na
useStructLong = useStructureSL and not na(structSlLongDist) and structSlLongDist > 0 and structRiskLongPct <= maxStructureRiskPct

slLongDist = useStructLong ? math.max(baseSlLongDist, structSlLongDist) : baseSlLongDist
slLong = f_round_to_tick(entryLong - slLongDist, tick)
```

### SHORT

```pine
baseSlShortDist = math.max(atrVal * slAtrMult, entryShort * minSlRawPct / 100.0, tick)
structSlShort = rst + atrVal * srAtrBuffer
structSlShortDist = structSlShort - entryShort
structRiskShortPct = entryShort > 0 ? structSlShortDist / entryShort * 100.0 : na
useStructShort = useStructureSL and not na(structSlShortDist) and structSlShortDist > 0 and structRiskShortPct <= maxStructureRiskPct

slShortDist = useStructShort ? math.max(baseSlShortDist, structSlShortDist) : baseSlShortDist
slShort = f_round_to_tick(entryShort + slShortDist, tick)
```

## TP distance v3: ATR + min percent + RR

Jangan lagi memaksa TP dari `target leveraged profit`, karena itu bisa membuat TP terlalu jauh dan tabel tidak realistis. Leverage profit cukup dihitung sebagai output display.

### LONG

```pine
tpLongByAtrDist = atrVal * tpAtrMult
tpLongByMinPctDist = entryLong * minTpRawPct / 100.0
tpLongByRRDist = slLongDist * minRR

tpLongDist = math.max(tpLongByAtrDist, tpLongByMinPctDist, tpLongByRRDist, tick)
tpLong = f_round_to_tick(entryLong + tpLongDist, tick)
```

### SHORT

```pine
tpShortByAtrDist = atrVal * tpAtrMult
tpShortByMinPctDist = entryShort * minTpRawPct / 100.0
tpShortByRRDist = slShortDist * minRR

tpShortDist = math.max(tpShortByAtrDist, tpShortByMinPctDist, tpShortByRRDist, tick)
tpShort = f_round_to_tick(math.max(entryShort - tpShortDist, tick), tick)
```

## Direction validation

```pine
dirOkLong  = not na(entryLong) and not na(tpLong) and not na(slLong) and tpLong > entryLong and slLong < entryLong
dirOkShort = not na(entryShort) and not na(tpShort) and not na(slShort) and tpShort < entryShort and slShort > entryShort
```

Acceptance:

```text
Jika ACTION = LONG:
TP harus lebih besar dari ENTRY
SL harus lebih kecil dari ENTRY

Jika ACTION = SHORT:
TP harus lebih kecil dari ENTRY
SL harus lebih besar dari ENTRY
```

---

# P0-06 — Leverage-Aware Risk Model yang Tidak Merusak Table

## Formula raw risk dan reward

### LONG

```pine
riskPctLong = entryLong > 0 ? math.abs(entryLong - slLong) / entryLong * 100.0 : na
tpPctLong   = entryLong > 0 ? math.abs(tpLong - entryLong) / entryLong * 100.0 : na
rrLong      = riskPctLong > 0 ? tpPctLong / riskPctLong : na
```

### SHORT

```pine
riskPctShort = entryShort > 0 ? math.abs(slShort - entryShort) / entryShort * 100.0 : na
tpPctShort   = entryShort > 0 ? math.abs(entryShort - tpShort) / entryShort * 100.0 : na
rrShort      = riskPctShort > 0 ? tpPctShort / riskPctShort : na
```

## Leveraged risk/profit display

```pine
levRiskPctLong = riskPctLong * leverage
levTpPctLong   = tpPctLong * leverage

levRiskPctShort = riskPctShort * leverage
levTpPctShort   = tpPctShort * leverage
```

Interpretasi:

- `riskPct` = pergerakan harga dari entry ke SL.
- `levRiskPct` = estimasi loss terhadap margin sebelum fee/funding/slippage.
- Ini bukan liquidation price.

## Risk label

Gunakan label sederhana:

```pine
f_risk_label(levRiskPct) =>
    na(levRiskPct) ? "NO_DATA" :
    levRiskPct <= 35 ? "SAFE" :
    levRiskPct <= 65 ? "RISKY" :
    "HIGH"
```

## Action risk gate

```pine
riskOkLong = not na(riskPctLong) and riskPctLong <= maxPlanRiskPct and levRiskPctLong <= maxLevRiskPct and rrLong >= minRR
riskOkShort = not na(riskPctShort) and riskPctShort <= maxPlanRiskPct and levRiskPctShort <= maxLevRiskPct and rrShort >= minRR
```

## Jangan tampilkan `LEV-RISK` sebagai action

Salah:

```text
ACTION = LEV-RISK
SIGNAL = LEV-RISK
```

Benar:

```text
RISK   = HIGH
ACTION = WAIT
SIGNAL = RISKY
```

Jika risiko masih sedang:

```text
RISK   = RISKY
ACTION = LONG / SHORT jika score dan RR valid
SIGNAL = LONG / SHORT
```

---

# P0-07 — Score Formula Binance Futures

Score adalah ranking kualitas setup, bukan prediksi profit.

## Trend

```pine
ema20 = ta.ema(close, 20)
ema50 = ta.ema(close, 50)
ema200 = ta.ema(close, 200)

trendUp = close > ema20 and ema20 > ema50
trendDown = close < ema20 and ema20 < ema50
macroBull = close > ema200
macroBear = close < ema200
```

## RSI

```pine
rsiVal = ta.rsi(close, 14)
rsiLongOk = rsiVal >= 50 and rsiVal <= 72
rsiShortOk = rsiVal <= 50 and rsiVal >= 28
```

## MACD

```pine
[macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)
macdUp = macdLine > signalLine and hist > 0
macdDown = macdLine < signalLine and hist < 0
```

## RVOL

```pine
volMA = ta.sma(volume, 20)
rvol = volMA > 0 ? volume / volMA : na
```

## DMI / ADX optional

```pine
[plusDI, minusDI, adxVal] = ta.dmi(14, 14)
adxOk = adxVal >= 18
longDmiOk = plusDI > minusDI
shortDmiOk = minusDI > plusDI
```

## Score LONG

```pine
scoreLong = 0
scoreLong += trendUp ? 18 : 0
scoreLong += macroBull ? 7 : 0
scoreLong += rsiVal >= 50 and rsiVal <= 68 ? 15 : rsiVal > 68 and rsiVal <= 75 ? 8 : 0
scoreLong += macdUp ? 15 : 0
scoreLong += rvol >= 2.0 ? 15 : rvol >= 1.2 ? 10 : rvol >= 0.8 ? 5 : 0
scoreLong += adxOk and longDmiOk ? 10 : adxOk ? 5 : 0
scoreLong += longBreak ? 10 : close > ema20 ? 5 : 0
scoreLong += rrLong >= 1.8 ? 10 : rrLong >= 1.3 ? 5 : 0
```

## Score SHORT

```pine
scoreShort = 0
scoreShort += trendDown ? 18 : 0
scoreShort += macroBear ? 7 : 0
scoreShort += rsiVal <= 50 and rsiVal >= 32 ? 15 : rsiVal < 32 and rsiVal >= 25 ? 8 : 0
scoreShort += macdDown ? 15 : 0
scoreShort += rvol >= 2.0 ? 15 : rvol >= 1.2 ? 10 : rvol >= 0.8 ? 5 : 0
scoreShort += adxOk and shortDmiOk ? 10 : adxOk ? 5 : 0
scoreShort += shortBreak ? 10 : close < ema20 ? 5 : 0
scoreShort += rrShort >= 1.8 ? 10 : rrShort >= 1.3 ? 5 : 0
```

## Technical side

```pine
technicalSide =
     scoreLong >= entryScore and scoreLong > scoreShort + scoreGap ? "LONG" :
     scoreShort >= entryScore and scoreShort > scoreLong + scoreGap ? "SHORT" :
     "NEUTRAL"
```

Jangan paksa sinyal jika score LONG dan SHORT terlalu dekat.

---

# P0-08 — Candidate Signal Tidak Boleh Salah Arah

## LONG candidate

```pine
longCandidate = trendUp and rsiLongOk and macdUp and rvol >= 1.0
```

## SHORT candidate

```pine
shortCandidate = trendDown and rsiShortOk and macdDown and rvol >= 1.0
```

## Valid action

```pine
validLongAction = validData and longCandidate and technicalSide == "LONG" and riskOkLong and dirOkLong
validShortAction = validData and shortCandidate and technicalSide == "SHORT" and riskOkShort and dirOkShort

action = validLongAction ? "LONG" : validShortAction ? "SHORT" : "WAIT"
```

Jangan membuat `SHORT` hanya karena `SL` long kebobolan. `SHORT` harus punya bearish confirmation sendiri.

---

# P0-09 — Telegram Alert Gating

## Futures event taxonomy

Pine payload wajib punya field `event`.

Allowed actionable events:

```text
LONG_ENTRY
SHORT_ENTRY
TP_HIT
SL_HIT
```

Non-actionable events yang tidak boleh dikirim Telegram:

```text
NONE
WAIT
NEUTRAL
WEAK
RISKY
WAIT_DATA
LEV_RISK
```

## Pine alert condition

```pine
event =
     action == "LONG" ? "LONG_ENTRY" :
     action == "SHORT" ? "SHORT_ENTRY" :
     "NONE"

sendAlert = event == "LONG_ENTRY" or event == "SHORT_ENTRY" or event == "TP_HIT" or event == "SL_HIT"

if barstate.isconfirmed and sendAlert
    alert(payload, alert.freq_once_per_bar_close)
```

## Payload futures minimal

Kirim numeric dan text price agar `main.py` tidak salah format ulang.

```json
{
  "market": "BINANCE_FUTURES",
  "event": "LONG_ENTRY",
  "symbol": "1000PEPEUSDT",
  "side": "LONG",
  "tf": "15",
  "entry": 0.0035263,
  "entry_text": "0.0035263",
  "now": 0.0035704,
  "now_text": "0.0035704",
  "tp": 0.0039291,
  "tp_text": "0.0039291",
  "sl": 0.0036537,
  "sl_text": "0.0036537",
  "tp_pct": 6.6,
  "risk_pct": 3.66,
  "rr": 1.8,
  "leverage": 10,
  "lev_tp_pct": 66.0,
  "lev_risk_pct": 36.6,
  "risk_label": "RISKY",
  "score": 65,
  "signal": "LONG",
  "flow": "NORMAL",
  "time": 1710000000000
}
```

## `main.py` server-side allowlist

`main.py` juga harus ignore payload non-actionable, walaupun Pine salah kirim.

```python
ACTIONABLE_EVENTS = {
    "LONG_ENTRY",
    "SHORT_ENTRY",
    "BUY_ENTRY",
    "SELL_EXIT",
    "TP_HIT",
    "SL_HIT",
}

event = str(data.get("event", "")).upper()
if event not in ACTIONABLE_EVENTS:
    return {"status": "ignored", "reason": "non_actionable", "event": event}
```

---

# P0-10 — Telegram Message Format Futures

Gunakan text price dari payload.

## LONG message

```text
🟢 BINANCE FUTURES LONG
PAIR  : 1000PEPEUSDT
TF    : 15m

ENTRY : 0.0035263
NOW   : 0.0035704
TP    : 0.0039291 (+6.60%)
SL    : 0.0036537 (-3.66%)

RR    : 1.80
LEV   : 10x
L-TP  : +66.0%
L-RISK: -36.6% | RISKY

FLOW  : NORMAL
SCORE : 65
```

## SHORT message

```text
🔴 BINANCE FUTURES SHORT
PAIR  : ALTUSDT
TF    : 15m

ENTRY : 0.0080
NOW   : 0.0078
TP    : 0.0070 (-12.50%)
SL    : 0.0086 (+7.50%)

RR    : 1.80
LEV   : 10x
L-TP  : +125.0%
L-RISK: -75.0% | HIGH

FLOW  : SHORT FLOW
SCORE : 78
```

Note:

- Untuk SHORT, TP lebih rendah dari entry tapi tetap target profit.
- `main.py` tidak perlu menghitung ulang decimal. Pakai `entry_text`, `now_text`, `tp_text`, `sl_text`.
- Semua field dari payload harus di-escape dengan `html.escape()` sebelum masuk Telegram HTML.

---

# P0-11 — IDX Transaction Value Fix

## Masalah

Jika ada pola seperti:

```pine
tv_1 = volume * c1
```

itu salah untuk screener multi-symbol, karena `volume` berasal dari chart utama.

## Fix

Hitung value di dalam function yang dipanggil `request.security()`.

```pine
f_scalp_engine() =>
    emaFast = ta.ema(close, 5)
    volMA = ta.sma(volume, 20)
    rvol = volMA > 0 ? volume / volMA : 0.0
    rsiVal = ta.rsi(close, 14)
    atrVal = ta.atr(14)
    tvVal = close * volume

    isGreenCandle = close > open
    validAtr = not na(atrVal) and atrVal > 0
    validTv = tvVal >= min_tv
    validHaka = isGreenCandle and rvol > 1.5 and close > emaFast

    status = not validAtr ? "WAIT_ATR" : validHaka and not validTv ? "WAIT_LIQ" : validHaka ? "HAKA" : "WAIT"

    [close, status, rsiVal, rvol, atrVal, tvVal]
```

Security call:

```pine
[c1, st_1, rsi_1, rvol_1, atr_1, tv_1] = request.security(tk1, tf, f_scalp_engine())
```

Payload IDX harus include:

```json
"transaction_value": 1234567890
```

---

# P0-12 — Webhook Secret + HTML Escape

## Webhook secret

VPS tetap public. Tambahkan secret sederhana.

```python
import os
from fastapi import HTTPException

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

@app.post("/webhook")
async def handle_webhook(request: Request):
    if WEBHOOK_SECRET:
        incoming_secret = request.headers.get("x-webhook-secret") or request.query_params.get("secret")
        if incoming_secret != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Forbidden")
```

Jika TradingView tidak bisa set header, pakai query param:

```text
https://domain-vps.com/webhook?secret=ISI_SECRET
```

## HTML escape

```python
import html

def esc(value):
    return html.escape(str(value), quote=False)
```

Semua field payload yang masuk message Telegram harus lewat `esc()`.

---

# P1-01 — Visual Color Rules Binance Futures

| Kolom | Kondisi | Warna |
|---|---|---|
| ACTION | LONG | Hijau |
| ACTION | SHORT | Merah |
| ACTION | WAIT | Abu-abu |
| RISK | SAFE | Hijau |
| RISK | RISKY | Kuning/Orange |
| RISK | HIGH | Merah |
| SIGNAL | LONG | Hijau |
| SIGNAL | SHORT | Merah |
| SIGNAL | RISKY | Orange |
| SIGNAL | NEUTRAL/WEAK | Abu-abu/Kuning |
| TP | LONG/SHORT target profit | Hijau |
| SL | LONG/SHORT invalidation | Orange/Merah |
| SCORE | >=80 | Hijau |
| SCORE | 60-79 | Kuning/Hijau muda |
| SCORE | 40-59 | Orange |
| SCORE | <40 | Merah |

Catatan: Untuk SHORT, TP tetap hijau walaupun harga TP lebih rendah karena itu target profit.

---

# P1-02 — FLOW Binance Futures

Ganti konsep `BANDAR` menjadi `FLOW` untuk futures.

```pine
body = math.abs(close - open)
barRange = math.max(high - low, tick)
lowerWick = math.min(open, close) - low
upperWick = high - math.max(open, close)
closeNearHigh = close >= low + barRange * 0.70
closeNearLow  = close <= low + barRange * 0.30

bullImpulse = close > open and closeNearHigh and rvol >= 1.2
bearImpulse = close < open and closeNearLow and rvol >= 1.2
longAbsorb  = lowerWick > body * 1.2 and closeNearHigh and rvol >= 1.3
shortAbsorb = upperWick > body * 1.2 and closeNearLow and rvol >= 1.3
smallBodyHighVol = body <= atrVal * 0.30 and rvol >= 1.8

flow =
     bullImpulse and trendUp ? "LONG FLOW" :
     bearImpulse and trendDown ? "SHORT FLOW" :
     longAbsorb ? "BUY ABSORB" :
     shortAbsorb ? "SELL ABSORB" :
     smallBodyHighVol ? "SQUEEZE" :
     rvol < 0.5 ? "SEPI" :
     "NORMAL"
```

---

# P1-03 — BTCUSDT Exception

BTCUSDT tidak perlu dipaksa ke table multi-symbol besar. Buat single dashboard:

```text
BTCUSDT DASHBOARD
TF
NOW
TREND
SUP
RST
LONG TRIGGER
SHORT TRIGGER
ENTRY
TP
SL
TP%
RISK%
RR
LEV
RISK
RSI
MACD
RVOL
FLOW
SCORE LONG
SCORE SHORT
ACTION
SIGNAL
```

Formula tetap sama seperti Binance Futures, hanya layout yang berbeda.

---

# P1-04 — Requirements

`requirements.txt` perlu support pipeline:

```text
fastapi
uvicorn
httpx
python-multipart
requests
yfinance
```

Jika ingin lebih rapi, pisahkan:

```text
requirements-webhook.txt
requirements-pipeline.txt
```

---

# P1-05 — README Sync

README harus menjelaskan project sebagai:

```text
TradingView Screener + Telegram Alert System
```

Bukan:

```text
Auto-trading bot
Execution engine
Broker bot
```

README juga harus menyebut:

- VPS setup tanpa Cloudflare Tunnel.
- Webhook secret.
- Alert hanya actionable.
- Binance Futures menggunakan direction-aware TP/SL.
- Price precision futures mengikuti tick size symbol.

---

# Verification Checklist

## Python compile

```bash
python -m py_compile main.py
python -m py_compile tv_scripts/fetch_idx_prices.py
python -m py_compile tv_scripts/filter_scalping_stocks.py
python -m py_compile tv_scripts/generate_pine_scripts.py
python -m py_compile tv_scripts/generate_screener.py
python -m py_compile tv_scripts/us/generate_us_scripts.py
```

## Regenerate

```bash
python tv_scripts/filter_scalping_stocks.py
python tv_scripts/generate_pine_scripts.py
python tv_scripts/generate_screener.py
python tv_scripts/us/generate_us_scripts.py
```

## Check Binance table

Manual visual acceptance di TradingView:

```text
Tidak ada NaN / NaNx / NaN%.
ACTION hanya LONG / SHORT / WAIT.
RISK hanya SAFE / RISKY / HIGH / NO_DATA.
Tidak ada LEV-RISK sebagai ACTION atau SIGNAL.
MAXLEV dan LIQ tidak tampil di table utama default.
Harga micro-pair tetap full sesuai tick size.
SHORT memiliki TP lebih rendah dari ENTRY dan SL lebih tinggi dari ENTRY.
LONG memiliki TP lebih tinggi dari ENTRY dan SL lebih rendah dari ENTRY.
```

## Check alert gating

Telegram tidak boleh menerima:

```text
WAIT
NEUTRAL
WEAK
RISKY
WAIT_DATA
LEV-RISK
```

Telegram hanya boleh menerima:

```text
LONG_ENTRY
SHORT_ENTRY
BUY_ENTRY
SELL_EXIT
TP_HIT
SL_HIT
```

## Check IDX transaction value bug

```bash
grep -R "volume \* c" -n tv_scripts/scalping_v2_batch_*.pine
```

Expected: tidak ada hasil.

---

# Definition of Done

Implementasi selesai jika:

1. Binance Futures table readable dan tidak overload risk/debug columns.
2. Harga futures tetap full precision sesuai tick size.
3. Tidak ada `NaN`, `NaNx`, atau `NaN%` di table.
4. `ACTION` hanya `LONG`, `SHORT`, atau `WAIT`.
5. Risk warning tampil terpisah sebagai `SAFE`, `RISKY`, `HIGH`, atau `NO_DATA`.
6. `LEV-RISK` tidak muncul sebagai action/signal utama.
7. TP/SL benar untuk LONG dan SHORT.
8. Telegram hanya menerima actionable event.
9. `main.py` ignore event non-actionable walaupun payload salah kirim.
10. IDX transaction value dihitung dari symbol target, bukan chart utama.
11. Webhook VPS punya secret.
12. Telegram formatter memakai HTML escape.
13. README sesuai scope screener, bukan auto-trading bot.
