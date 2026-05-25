# plan.md — Redesign Screener TradingView + Telegram Alert Architecture

## 0. Tujuan Redesign

Sistem ini bukan auto-trading bot. Sistem ini adalah:

```text
TradingView Screener → Actionable Alert → Telegram
```

Target redesign:

1. TradingView tetap menampilkan semua kondisi market dalam bentuk table/screener.
2. Telegram hanya menerima sinyal yang benar-benar actionable.
3. Harga `NOW`, `TRIGGER`, `ENTRY`, `TP`, dan `SL` tidak ambigu.
4. Sinyal futures tidak boleh ngawur, misalnya harga sedang naik kuat tapi `ACTION = SHORT`.
5. Sinyal tidak dibuat terlalu telat dengan menunggu validasi ekstrem, tetapi tetap harus punya price-action confirmation.
6. Saham tidak memakai konsep `SHORT`. Saham hanya `BUY`, `SELL/EXIT`, `TP`, dan `SL`.
7. Binance Futures boleh `LONG` dan `SHORT`, tetapi harus punya logic arah, risk, dan lifecycle yang jelas.
8. `main.py` tidak boleh percaya mentah-mentah payload Pine Script. Harus ada validasi server-side.
9. Precision harga futures yang sudah benar harus dipertahankan.
10. Cloudflare Tunnel tidak dibutuhkan karena sudah memakai VPS sendiri.

---

## 1. Masalah yang Harus Diselesaikan

### 1.1 Harga `NOW` dan `ENTRY` masih membingungkan

Masalah yang terlihat:

```text
NOW berbeda dari ENTRY
ENTRY sudah tampil padahal belum ada sinyal valid
TP/SL tampil padahal posisi belum aktif
```

Perbaikan:

```text
NOW     = harga sekarang / close symbol tersebut
TRIGGER = level pantau untuk breakout/breakdown/reversal
ENTRY   = harga saat sinyal actionable benar-benar muncul
```

Jika belum ada aksi:

```text
ENTRY = -
TP    = -
SL    = -
ACTION = WAIT
```

---

### 1.2 Harga sedang naik kuat tapi signal malah SHORT

Ini adalah masalah paling penting.

Sistem tidak boleh mengubah indikator bearish menjadi `ACTION = SHORT` kalau candle/harga saat ini masih bullish kuat.

Contoh salah:

```text
Harga naik kuat
Candle hijau
Close dekat high
Volume naik
ACTION = SHORT
```

Yang benar:

```text
STATUS = OVERHEAT / SHORT WATCH
ACTION = WAIT
SIGNAL = NEUTRAL / RISKY
```

SHORT baru boleh muncul jika ada tanda pelemahan/rejection, bukan hanya karena RSI tinggi atau score short besar.

---

### 1.3 Score/bias dipakai sebagai action

Ini salah.

Harus dipisah:

```text
BIAS   = kecenderungan indikator
SETUP  = potensi peluang
ACTION = aksi yang boleh dikirim Telegram
```

Contoh:

```text
BIAS   = BEARISH
SETUP  = SHORT WATCH
ACTION = WAIT
```

Bukan:

```text
ACTION = SHORT
```

---

### 1.4 TP/SL dihitung sebelum posisi valid

TP/SL hanya boleh aktif jika:

```text
ACTION = LONG
ACTION = SHORT
ACTION = BUY_ENTRY
```

Jika masih `WAIT`, table boleh menampilkan `TRIGGER`, tetapi jangan tampilkan `ENTRY`, `TP`, dan `SL` sebagai plan aktif.

---

### 1.5 TP_HIT / SL_HIT salah lifecycle

Jika posisi sebelumnya LONG, maka event TP/SL harus tetap membawa side LONG:

```text
LONG_TP_HIT
LONG_SL_HIT
```

Bukan berubah menjadi SHORT hanya karena candle terbaru bearish.

---

## 2. Arsitektur Baru

### 2.1 Layer 1 — Market Data

Semua data multi-symbol wajib berasal dari symbol target via `request.security()`.

Contoh konsep:

```pine
f_engine() =>
    [
        close,
        open,
        high,
        low,
        volume,
        syminfo.mintick
    ]

[o, h, l, c, v, tick] = request.security(symbol, tf, f_engine())
```

Catatan:

- Jangan pakai `volume` chart utama untuk symbol lain.
- Jangan pakai `syminfo.mintick` chart utama untuk format symbol lain.
- Precision harga yang sekarang sudah benar jangan diubah mundur.

---

### 2.2 Layer 2 — Indicator Engine

Menghitung indikator mentah:

```text
EMA20
EMA50
EMA200
ATR14
ATR%
RSI14
MACD 12/26/9
RVOL
VALUE
Support
Resistance
Candle behavior
Flow
```

Layer ini hanya menghitung data, belum menentukan action.

---

### 2.3 Layer 3 — Bias Engine

Menghasilkan kecenderungan:

```text
BULLISH_BIAS
BEARISH_BIAS
NEUTRAL_BIAS
```

Bias tidak boleh langsung jadi action.

---

### 2.4 Layer 4 — Setup Engine

Menghasilkan potensi setup:

```text
LONG_SETUP
SHORT_SETUP
OVERHEAT
REVERSAL_WATCH
BREAKOUT_WATCH
BREAKDOWN_WATCH
RISKY
CONFLICT
WAIT
```

Setup juga belum tentu dikirim Telegram.

---

### 2.5 Layer 5 — Action Engine

Hanya menghasilkan:

#### Binance Futures

```text
LONG
SHORT
WAIT
```

#### Saham IDX / US

```text
BUY
SELL_EXIT
WAIT
```

Action hanya muncul jika ada price-action confirmation.

---

### 2.6 Layer 6 — Trade State Machine

Menyimpan posisi aktif per symbol:

```text
NONE
LONG_ACTIVE
SHORT_ACTIVE
BUY_ACTIVE
```

State dipakai untuk:

```text
TP_HIT
SL_HIT
cooldown
mencegah alert bolak-balik
mencegah SHORT saat LONG belum selesai
```

---

### 2.7 Layer 7 — Telegram Event Gate

Hanya event berikut yang boleh dikirim:

#### Futures

```text
LONG_ENTRY
SHORT_ENTRY
LONG_TP_HIT
LONG_SL_HIT
SHORT_TP_HIT
SHORT_SL_HIT
```

#### Saham

```text
BUY_ENTRY
SELL_EXIT
TP_HIT
SL_HIT
```

Event lain tidak boleh dikirim.

---

## 3. Definisi Harga

### 3.1 NOW

```text
NOW = close dari symbol target pada timeframe screener
```

Pine:

```pine
now = close
```

Untuk table, `NOW` selalu tampil.

---

### 3.2 TRIGGER

`TRIGGER` adalah level pantau.

Untuk futures:

#### Long trigger

```pine
prevResistance = ta.highest(high, srLen)[1]
longTrigger = prevResistance + tick
```

#### Short trigger

```pine
prevSupport = ta.lowest(low, srLen)[1]
shortTrigger = prevSupport - tick
```

Catatan:

- Pakai `[1]` supaya support/resistance tidak ikut berubah oleh candle berjalan.
- Trigger bukan entry aktif.
- Trigger boleh tampil di table walaupun belum action.

---

### 3.3 ENTRY

`ENTRY` adalah harga saat action benar-benar muncul.

#### Recommended default

```pine
entryLong = close
entryShort = close
```

Bukan:

```text
entry = resistance/support prediksi
```

Alasan:

- Telegram lebih sesuai dengan kondisi real candle.
- User tahu sinyal muncul pada harga berapa.
- Tidak membingungkan antara level rencana dan harga actual.

---

### 3.4 Table display rule

Jika belum action:

```text
ENTRY = -
TP    = -
SL    = -
```

Jika action muncul:

```text
ENTRY = close saat sinyal
TP    = hasil perhitungan dari entry
SL    = hasil perhitungan dari entry
```

---

## 4. Binance Futures Signal Logic

## 4.1 Indicator dasar

```pine
emaFast = ta.ema(close, 20)
emaSlow = ta.ema(close, 50)
emaTrend = ta.ema(close, 200)

atr = ta.atr(14)
atrPct = atr / close * 100

rsi = ta.rsi(close, 14)

[macdLine, macdSignal, macdHist] = ta.macd(close, 12, 26, 9)

volMA = ta.sma(volume, 20)
rvol = volMA > 0 ? volume / volMA : na

value = close * volume
```

---

## 4.2 Candle behavior

Candle behavior harus menjadi filter utama agar tidak short saat harga sedang naik kuat.

```pine
body = math.abs(close - open)
range = high - low

greenCandle = close > open
redCandle = close < open

closeNearHigh = range > 0 ? close >= low + range * 0.65 : false
closeNearLow  = range > 0 ? close <= low + range * 0.35 : false

barUp = close > open and close >= close[1]
barDown = close < open and close <= close[1]

upperWick = high - math.max(open, close)
lowerWick = math.min(open, close) - low

upperReject = body > 0 ? upperWick >= body * 0.8 : false
lowerReject = body > 0 ? lowerWick >= body * 0.8 : false
```

---

## 4.3 Trend bias

### Long bias

```pine
trendLong =
    close > emaFast and
    emaFast > emaSlow
```

Lebih kuat:

```pine
trendLongStrong =
    close > emaFast and
    emaFast > emaSlow and
    emaSlow > emaTrend
```

### Short bias

```pine
trendShort =
    close < emaFast and
    emaFast < emaSlow
```

Lebih kuat:

```pine
trendShortStrong =
    close < emaFast and
    emaFast < emaSlow and
    emaSlow < emaTrend
```

---

## 4.4 Momentum bias

### Long momentum

```pine
momentumLong =
    rsi >= 50 and
    rsi <= 72 and
    macdHist > 0 and
    macdHist >= macdHist[1]
```

### Short momentum

```pine
momentumShort =
    rsi <= 50 and
    rsi >= 28 and
    macdHist < 0 and
    macdHist <= macdHist[1]
```

Catatan:

- RSI terlalu tinggi bukan otomatis short.
- RSI terlalu rendah bukan otomatis long.
- RSI ekstrem hanya membuat status `OVERHEAT` / `OVERSOLD WATCH`.

---

## 4.5 Volume filter

```pine
minRvol = input.float(1.2, "Min RVOL")
volOk = rvol >= minRvol
```

---

## 4.6 Overheat / Oversold watch

### Overheat

Harga naik kuat tetapi rawan reversal.

```pine
overheat =
    rsi > 72 or
    close > emaFast + atr * 1.8
```

Jika overheat tetapi candle masih bullish:

```text
STATUS = OVERHEAT
ACTION = WAIT
SIGNAL = RISKY
```

Tidak boleh langsung `SHORT`.

### Oversold

Harga turun kuat tetapi rawan pantulan.

```pine
oversold =
    rsi < 28 or
    close < emaFast - atr * 1.8
```

Jika oversold tetapi candle masih bearish:

```text
STATUS = OVERSOLD
ACTION = WAIT
SIGNAL = RISKY
```

Tidak boleh langsung `LONG`.

---

## 4.7 Long Action — cepat tapi tidak ngawur

Long tidak harus menunggu breakout besar, tetapi harus ada candle behavior bullish.

### Trend-following long

```pine
longTrendAction =
    trendLong and
    momentumLong and
    volOk and
    greenCandle and
    closeNearHigh and
    not overheat
```

### Breakout long

```pine
longBreakoutAction =
    close > longTrigger and
    greenCandle and
    closeNearHigh and
    volOk
```

### Reversal long

Boleh lebih cepat saat harga turun lalu muncul rejection.

```pine
longReversalAction =
    oversold and
    lowerReject and
    greenCandle and
    closeNearHigh and
    rvol >= 1.2 and
    macdHist > macdHist[1]
```

### Final long action

```pine
validLongAction =
    longTrendAction or
    longBreakoutAction or
    longReversalAction
```

---

## 4.8 Short Action — cepat tapi tidak melawan candle hijau kuat

Short tidak harus menunggu breakdown jauh, tetapi wajib ada tanda pelemahan harga.

### Trend-following short

```pine
shortTrendAction =
    trendShort and
    momentumShort and
    volOk and
    redCandle and
    closeNearLow and
    not oversold
```

### Breakdown short

```pine
shortBreakdownAction =
    close < shortTrigger and
    redCandle and
    closeNearLow and
    volOk
```

### Reversal short

Untuk kasus harga naik terlalu kuat lalu mulai ditolak:

```pine
shortReversalAction =
    overheat and
    upperReject and
    redCandle and
    closeNearLow and
    rvol >= 1.2 and
    macdHist < macdHist[1]
```

### Final short action

```pine
validShortAction =
    shortTrendAction or
    shortBreakdownAction or
    shortReversalAction
```

### Hard rule

Jika candle masih bullish kuat:

```pine
bullishImpulse =
    greenCandle and
    closeNearHigh and
    close > close[1]
```

Maka:

```pine
if bullishImpulse
    validShortAction := false
```

Jika candle masih bearish kuat:

```pine
bearishImpulse =
    redCandle and
    closeNearLow and
    close < close[1]
```

Maka:

```pine
if bearishImpulse
    validLongAction := false
```

---

## 5. FLOW Rule

FLOW harus mendukung action, bukan bertentangan.

### Long flow

```pine
longFlow =
    greenCandle and
    closeNearHigh and
    rvol >= 1.2
```

Label:

```text
LONG FLOW
BUY ABSORB
NORMAL
```

### Short flow

```pine
shortFlow =
    redCandle and
    closeNearLow and
    rvol >= 1.2
```

Label:

```text
SHORT FLOW
SELL PRESSURE
NORMAL
```

### Conflict rule

Jika:

```text
validShortAction = true
flow = BUY ABSORB / LONG FLOW
```

Maka:

```text
ACTION = WAIT
STATUS = CONFLICT
SIGNAL = NEUTRAL
```

Jika:

```text
validLongAction = true
flow = SELL PRESSURE / SHORT FLOW
```

Maka:

```text
ACTION = WAIT
STATUS = CONFLICT
SIGNAL = NEUTRAL
```

---

## 6. Score Engine

Score tidak boleh sendirian menentukan action.

Score hanya memperkuat keputusan action.

### Long score

```pine
scoreLong = 0
scoreLong += trendLong ? 20 : 0
scoreLong += momentumLong ? 20 : 0
scoreLong += volOk ? 15 : 0
scoreLong += greenCandle ? 15 : 0
scoreLong += closeNearHigh ? 10 : 0
scoreLong += longFlow ? 10 : 0
scoreLong += not overheat ? 10 : 0
```

### Short score

```pine
scoreShort = 0
scoreShort += trendShort ? 20 : 0
scoreShort += momentumShort ? 20 : 0
scoreShort += volOk ? 15 : 0
scoreShort += redCandle ? 15 : 0
scoreShort += closeNearLow ? 10 : 0
scoreShort += shortFlow ? 10 : 0
scoreShort += not oversold ? 10 : 0
```

### Final score gate

```pine
minScore = input.int(70, "Min Action Score")
scoreGap = input.int(8, "Min Score Gap")

longScoreOk = scoreLong >= minScore and scoreLong > scoreShort + scoreGap
shortScoreOk = scoreShort >= minScore and scoreShort > scoreLong + scoreGap
```

### Final action

```pine
if validLongAction and longScoreOk
    action := "LONG"
else if validShortAction and shortScoreOk
    action := "SHORT"
else
    action := "WAIT"
```

---

## 7. TP/SL Futures

TP/SL dihitung hanya setelah action valid.

### 7.1 Inputs

```pine
rrTarget = input.float(1.8, "RR Target")
slAtrMult = input.float(1.2, "SL ATR Mult")
bufferAtr = input.float(0.15, "Structure Buffer ATR")
maxRawRiskPct = input.float(4.0, "Max Raw Risk %")
leverage = input.int(10, "Leverage")
maxLevRiskPct = input.float(45.0, "Max Leveraged Risk %")
```

---

### 7.2 LONG plan

```pine
entryLong = close

structureSlLong = prevSupport - atr * bufferAtr
atrSlLong = entryLong - atr * slAtrMult

slLong = math.min(structureSlLong, atrSlLong)

riskLong = entryLong - slLong
riskPctLong = riskLong / entryLong * 100

tpLong = entryLong + riskLong * rrTarget
tpPctLong = (tpLong - entryLong) / entryLong * 100

rrLong = (tpLong - entryLong) / math.max(entryLong - slLong, tick)
```

Validation:

```pine
validLongPlan =
    tpLong > entryLong and
    slLong < entryLong and
    riskPctLong > 0 and
    riskPctLong <= maxRawRiskPct and
    riskPctLong * leverage <= maxLevRiskPct
```

---

### 7.3 SHORT plan

```pine
entryShort = close

structureSlShort = prevResistance + atr * bufferAtr
atrSlShort = entryShort + atr * slAtrMult

slShort = math.max(structureSlShort, atrSlShort)

riskShort = slShort - entryShort
riskPctShort = riskShort / entryShort * 100

tpShort = entryShort - riskShort * rrTarget
tpPctShort = (entryShort - tpShort) / entryShort * 100

rrShort = (entryShort - tpShort) / math.max(slShort - entryShort, tick)
```

Validation:

```pine
validShortPlan =
    tpShort < entryShort and
    slShort > entryShort and
    riskPctShort > 0 and
    riskPctShort <= maxRawRiskPct and
    riskPctShort * leverage <= maxLevRiskPct
```

---

### 7.4 Jika risk tidak lolos

Jika action bagus tapi risk terlalu besar:

```text
ACTION = WAIT
STATUS = RISKY
SIGNAL = RISKY
```

Telegram tidak boleh dikirim.

---

## 8. State Machine Futures

Wajib ada state per symbol.

```pine
var string activeSide = "NONE"
var float activeEntry = na
var float activeTp = na
var float activeSl = na
var int activeBar = na
```

Untuk batch multi-symbol, generator harus membuat state per ticker:

```pine
var string activeSide_1 = "NONE"
var float activeEntry_1 = na
var float activeTp_1 = na
var float activeSl_1 = na
var int activeBar_1 = na
```

---

### 8.1 Entry event

```pine
if action == "LONG" and validLongPlan and activeSide == "NONE" and barstate.isconfirmed
    activeSide := "LONG"
    activeEntry := entryLong
    activeTp := tpLong
    activeSl := slLong
    activeBar := bar_index
    alert(LONG_ENTRY)
```

```pine
if action == "SHORT" and validShortPlan and activeSide == "NONE" and barstate.isconfirmed
    activeSide := "SHORT"
    activeEntry := entryShort
    activeTp := tpShort
    activeSl := slShort
    activeBar := bar_index
    alert(SHORT_ENTRY)
```

---

### 8.2 TP/SL event

Default hit mode harus close-confirmed:

```pine
hitMode = input.string("CLOSE", "TP/SL Hit Mode", options=["CLOSE", "WICK"])
```

#### LONG active

```pine
longTpHit = hitMode == "CLOSE" ? close >= activeTp : high >= activeTp
longSlHit = hitMode == "CLOSE" ? close <= activeSl : low <= activeSl
```

#### SHORT active

```pine
shortTpHit = hitMode == "CLOSE" ? close <= activeTp : low <= activeTp
shortSlHit = hitMode == "CLOSE" ? close >= activeSl : high >= activeSl
```

#### Event

```pine
if activeSide == "LONG" and barstate.isconfirmed
    if longTpHit
        alert(LONG_TP_HIT)
        activeSide := "NONE"
    else if longSlHit
        alert(LONG_SL_HIT)
        activeSide := "NONE"
```

```pine
if activeSide == "SHORT" and barstate.isconfirmed
    if shortTpHit
        alert(SHORT_TP_HIT)
        activeSide := "NONE"
    else if shortSlHit
        alert(SHORT_SL_HIT)
        activeSide := "NONE"
```

---

## 9. Table TradingView

### 9.1 Recommended columns

```text
PAIR
TF
NOW
TRIG
ENTRY
TP
SL
TP%
RISK%
RR
LEV
RISK
RSI
RVOL
FLOW
STATUS
ACTION
SCORE
SIGNAL
```

### 9.2 Column meaning

| Column | Meaning |
|---|---|
| `PAIR` | symbol |
| `TF` | timeframe |
| `NOW` | current close |
| `TRIG` | trigger level |
| `ENTRY` | active entry only |
| `TP` | active target only |
| `SL` | active stop only |
| `TP%` | target percent |
| `RISK%` | stop distance percent |
| `RR` | reward/risk |
| `LEV` | leverage input |
| `RISK` | SAFE / RISKY / HIGH |
| `RSI` | RSI14 |
| `RVOL` | relative volume |
| `FLOW` | LONG FLOW / SHORT FLOW / NORMAL / SEPI |
| `STATUS` | setup/status |
| `ACTION` | LONG / SHORT / WAIT |
| `SCORE` | selected action score |
| `SIGNAL` | LONG / SHORT / NEUTRAL / RISKY |

### 9.3 Display rules

If `ACTION = WAIT`:

```text
ENTRY = -
TP = -
SL = -
TP% = -
RISK% = -
RR = -
```

If `ACTION = LONG` or `SHORT`:

```text
ENTRY = actual entry
TP = active TP
SL = active SL
```

Never show:

```text
NaN
NaNx
NaN%
```

Use:

```text
-
```

---

## 10. Telegram Alert Rules

### 10.1 Futures events allowed

```text
LONG_ENTRY
SHORT_ENTRY
LONG_TP_HIT
LONG_SL_HIT
SHORT_TP_HIT
SHORT_SL_HIT
```

### 10.2 Futures events blocked

```text
WAIT
NEUTRAL
RISKY
SETUP
LONG_SETUP
SHORT_SETUP
OVERHEAT
OVERSOLD
CONFLICT
LEV_RISK
```

### 10.3 Payload

```json
{
  "market": "BINANCE_FUTURES",
  "symbol": "GRASSUSDT",
  "tf": "15",
  "event": "SHORT_ENTRY",
  "side": "SHORT",
  "now": 0.5161,
  "entry": 0.5161,
  "tp": 0.4870,
  "sl": 0.5322,
  "tp_pct": 5.64,
  "risk_pct": 3.12,
  "rr": 1.8,
  "leverage": 10,
  "lev_tp_pct": 56.4,
  "lev_risk_pct": 31.2,
  "risk_label": "SAFE",
  "score": 82,
  "flow": "SHORT FLOW",
  "signal": "SHORT",
  "price_text": {
    "now": "0.5161",
    "entry": "0.5161",
    "tp": "0.4870",
    "sl": "0.5322"
  },
  "time": 1710000000000
}
```

---

## 11. main.py Validation

`main.py` harus validasi ulang sebelum kirim Telegram.

### 11.1 Allowed event

```python
ALLOWED_FUTURES_EVENTS = {
    "LONG_ENTRY",
    "SHORT_ENTRY",
    "LONG_TP_HIT",
    "LONG_SL_HIT",
    "SHORT_TP_HIT",
    "SHORT_SL_HIT",
}
```

Jika bukan event di atas:

```python
return {"status": "ignored", "reason": "non_actionable"}
```

---

### 11.2 Direction validation

```python
def validate_direction(data):
    side = data.get("side")
    entry = float(data.get("entry"))
    tp = float(data.get("tp"))
    sl = float(data.get("sl"))

    if side == "LONG":
        return tp > entry and sl < entry

    if side == "SHORT":
        return tp < entry and sl > entry

    return False
```

---

### 11.3 Hit validation

```python
def validate_hit(data):
    event = data.get("event")
    now = float(data.get("now"))
    tp = float(data.get("tp"))
    sl = float(data.get("sl"))

    if event == "LONG_TP_HIT":
        return now >= tp

    if event == "LONG_SL_HIT":
        return now <= sl

    if event == "SHORT_TP_HIT":
        return now <= tp

    if event == "SHORT_SL_HIT":
        return now >= sl

    return True
```

---

### 11.4 Format Telegram

Header harus mengikuti `side` dan `event`, bukan candle terbaru.

#### LONG

```text
🟢 BINANCE FUTURES LONG

Symbol : GRASSUSDT
TF     : 15m
Event  : LONG_ENTRY

NOW    : 0.5161
ENTRY  : 0.5161
TP     : 0.5450 (+5.60%)
SL     : 0.5000 (-3.10%)
RR     : 1.80

LEV    : 10x
L-TP   : +56.0%
L-RISK : -31.0%
RISK   : SAFE

Score  : 82
Flow   : LONG FLOW
Signal : LONG
```

#### SHORT

```text
🔴 BINANCE FUTURES SHORT

Symbol : GRASSUSDT
TF     : 15m
Event  : SHORT_ENTRY

NOW    : 0.5161
ENTRY  : 0.5161
TP     : 0.4870 (-5.60%)
SL     : 0.5322 (+3.10%)
RR     : 1.80

LEV    : 10x
L-TP   : +56.0%
L-RISK : -31.0%
RISK   : SAFE

Score  : 82
Flow   : SHORT FLOW
Signal : SHORT
```

---

## 12. Saham IDX / US

Saham tidak memakai LONG/SHORT.

### 12.1 Allowed action

```text
BUY
SELL_EXIT
WAIT
```

### 12.2 Telegram event

```text
BUY_ENTRY
SELL_EXIT
TP_HIT
SL_HIT
```

### 12.3 Saham naik tapi indikator bearish

Jangan SHORT.

Gunakan:

```text
STATUS = TAKE PROFIT WATCH / DISTRIBUTION WATCH
ACTION = WAIT / SELL_EXIT
```

Jika belum ada posisi aktif:

```text
ACTION = WAIT
```

Jika ada posisi aktif dan muncul distribusi:

```text
ACTION = SELL_EXIT
```

---

## 13. Regression Test

### Test 1 — Harga naik kuat tidak boleh SHORT

Kondisi:

```text
green candle
close near high
close > close[1]
rvol tinggi
scoreShort tinggi
```

Expected:

```text
ACTION = WAIT
STATUS = OVERHEAT / SHORT WATCH
Telegram = tidak kirim
```

---

### Test 2 — SHORT boleh muncul saat rejection

Kondisi:

```text
overheat
upper wick besar
red candle
close near low
macdHist turun
rvol >= 1.2
```

Expected:

```text
ACTION = SHORT
Telegram = SHORT_ENTRY
```

---

### Test 3 — LONG boleh muncul saat reversal

Kondisi:

```text
oversold
lower wick besar
green candle
close near high
macdHist naik
rvol >= 1.2
```

Expected:

```text
ACTION = LONG
Telegram = LONG_ENTRY
```

---

### Test 4 — ENTRY kosong saat WAIT

Kondisi:

```text
ACTION = WAIT
```

Expected table:

```text
ENTRY = -
TP = -
SL = -
```

---

### Test 5 — LONG TP/SL direction

Kondisi:

```text
side = LONG
```

Expected:

```text
TP > ENTRY
SL < ENTRY
```

---

### Test 6 — SHORT TP/SL direction

Kondisi:

```text
side = SHORT
```

Expected:

```text
TP < ENTRY
SL > ENTRY
```

---

### Test 7 — main.py reject invalid SHORT

Payload:

```text
side = SHORT
TP > ENTRY
SL < ENTRY
```

Expected:

```text
ignored: invalid_direction
```

---

### Test 8 — main.py reject invalid TP_HIT

Payload:

```text
event = LONG_TP_HIT
now < tp
```

Expected:

```text
ignored: invalid_hit
```

---

### Test 9 — Saham tidak boleh SHORT

Payload:

```text
market = IDX
event = SHORT_ENTRY
```

Expected:

```text
ignored: invalid_equity_event
```

---

## 14. Implementation Order

### Phase 1 — Freeze alert

1. Matikan Telegram alert futures sementara.
2. Simpan screenshot dan payload kasus bermasalah.
3. Pastikan precision harga yang sudah benar tidak diubah mundur.

### Phase 2 — Refactor Pine futures engine

1. Pisahkan `NOW`, `TRIGGER`, `ENTRY`.
2. Tambahkan candle behavior filter.
3. Tambahkan overheat/oversold watch.
4. Tambahkan long/short action yang tidak melawan candle kuat.
5. Tambahkan scoreLong/scoreShort terpisah.
6. Tambahkan flow conflict rule.
7. Tambahkan TP/SL hanya setelah action valid.
8. Tambahkan state machine per symbol.

### Phase 3 — Refactor table

1. Tampilkan `TRIG`.
2. Kosongkan `ENTRY/TP/SL` jika `WAIT`.
3. ACTION hanya `LONG`, `SHORT`, `WAIT`.
4. SIGNAL hanya `LONG`, `SHORT`, `NEUTRAL`, `RISKY`.

### Phase 4 — Refactor alert payload

1. Event explicit:
   - `LONG_ENTRY`
   - `SHORT_ENTRY`
   - `LONG_TP_HIT`
   - `LONG_SL_HIT`
   - `SHORT_TP_HIT`
   - `SHORT_SL_HIT`
2. Tambahkan `side`.
3. Tambahkan `price_text`.
4. Jangan kirim setup/watch.

### Phase 5 — Refactor main.py

1. Validate allowed event.
2. Validate direction.
3. Validate TP/SL hit.
4. Format Telegram dari `side` dan `event`.
5. Escape HTML.
6. Ignore payload invalid.

### Phase 6 — IDX / US cleanup

1. Hapus konsep SHORT untuk saham.
2. Gunakan BUY/SELL_EXIT/TP_HIT/SL_HIT.
3. BUY harus berdasarkan trigger + volume + transaction value.
4. SELL_EXIT untuk distribusi/exit, bukan short.

---

## 15. Acceptance Criteria

Implementasi selesai jika:

1. Saat harga naik kuat, table tidak lagi memberi `ACTION = SHORT`.
2. Saat harga turun kuat, table tidak lagi memberi `ACTION = LONG`.
3. `SHORT WATCH` / `OVERHEAT` boleh muncul sebagai status, tetapi action tetap `WAIT`.
4. Countertrend signal hanya muncul setelah rejection candle.
5. `ENTRY` hanya muncul saat action valid.
6. `TP/SL` hanya muncul saat action valid atau active trade.
7. `TP_HIT` / `SL_HIT` selalu membawa side yang benar.
8. `main.py` menolak payload yang TP/SL-nya salah arah.
9. Telegram hanya menerima actionable event.
10. Saham tidak pernah mengirim `SHORT`.
11. Tidak ada `NaN`, `NaNx`, atau `NaN%`.
12. Price precision yang sudah benar tetap dipertahankan.
13. Table tetap readable dan tidak overload.
14. Signal tidak terlalu telat karena ada early reversal mode, tetapi tidak melawan impulse candle.

---

## 16. Catatan untuk Agent Implementer

Jangan hanya mengganti label.

Yang harus dibangun ulang adalah:

```text
Data → Indicator → Bias → Setup → Action → State → Alert
```

Kesalahan utama saat ini:

```text
indicator bias langsung dijadikan action
```

Seharusnya:

```text
indicator bias + price behavior + flow + risk + state = action
```

Prinsip final:

```text
Harga naik kuat = jangan SHORT, kecuali sudah ada rejection.
Harga turun kuat = jangan LONG, kecuali sudah ada rejection.
Setup boleh cepat.
Action harus masuk akal.
Telegram hanya untuk action.
```
