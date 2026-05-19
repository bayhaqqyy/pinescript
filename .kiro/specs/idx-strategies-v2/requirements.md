# Requirements Document

## Introduction

IDX Strategies v2 adalah revisi total dari dua screener Pine Script yang sudah ada di repo (Scalping IDX dan Bandar AI IDX) supaya keluar dari kandang penny stock di bawah Rp1.000 dan masuk ke tier yang lebih likuid serta layak ditradingkan secara nyata. Versi pertama menyaring saham di bawah Rp1.000 — di sana spread terlalu lebar, banyak emiten masuk Papan Pemantauan Khusus (FCA), dan eksekusi sulit. Versi 2 memisahkan dua tier:

- **Scalping (gorengan tier)**: harga < Rp1.000, volatil tapi masih tradable, bukan FCA, bukan suspended, bukan IPO baru < 30 hari.
- **Bandar AI Swing (mid-cap tier)**: harga < Rp1.000 dengan preferensi ≥ Rp3.000, dipakai untuk swing 3–7 hari kerja dengan deteksi akumulasi/distribusi institusi.

Selain pemisahan tier, v2 juga: (a) mengganti TP/SL fixed-percent dengan level berbasis ATR supaya adaptif terhadap volatilitas masing-masing emiten, (b) menambah filter likuiditas dollar-volume per bar, (c) memperkaya payload alert (TP1/TP2/SL/holding hint/tier), (d) memperjelas tampilan Telegram per tier, dan (e) menyimpan output Pine ke file ber-suffix `_v2` supaya tidak menimpa file lama.

## Glossary

- **IDX**: Indonesia Stock Exchange (Bursa Efek Indonesia).
- **Pool_Scalping**: Daftar saham hasil filter dengan harga penutupan terakhir < Rp1.000 yang dipakai sebagai universe Scalping v2.
- **Pool_Bandar**: Daftar saham hasil filter dengan harga penutupan terakhir < Rp1.000 yang dipakai sebagai universe Bandar AI Swing v2; subset dengan harga ≥ Rp3.000 ditandai sebagai tier preferred.
- **FCA_Blacklist**: Himpunan ticker yang dikenal masuk Papan Pemantauan Khusus (Full Call Auction) atau di-suspend dan harus dikeluarkan dari kedua pool.
- **Whitelist_Seed**: Daftar ticker hasil riset awal pengguna yang di-pin masuk pool walaupun threshold harga atau likuiditasnya marginal, selama tidak ada di FCA_Blacklist.
- **Tier**: Penanda kategori sinyal pada payload alert; nilai sah `SCALP_GORENGAN` atau `BANDAR_SWING`.
- **Holding_Hint**: String pendek pada payload alert yang menjelaskan ekspektasi durasi memegang posisi (misalnya `"intraday"` untuk Scalping, `"3-7 hari"` untuk Bandar Swing).
- **Pipeline_Fetch**: Skrip `tv_scripts/fetch_idx_prices.py` yang mengambil harga dari Yahoo Finance dan memetakan setiap ticker ke pool yang sesuai.
- **Pipeline_Filter**: Skrip `tv_scripts/filter_scalping_stocks.py` yang membaca output Pipeline_Fetch dan menghasilkan dua JSON akhir (Scalping dan Bandar) setelah blacklist + threshold + likuiditas diterapkan.
- **Pine_Generator**: Skrip `tv_scripts/generate_pine_scripts.py` yang membaca dua JSON dari Pipeline_Filter dan menghasilkan file Pine v6 ber-suffix `_v2`.
- **Telegram_Formatter**: Fungsi di `main.py` (`format_idx_scalp_alert`, `format_idx_bandar_alert`) yang menerima payload alert dan menghasilkan string siap kirim ke Telegram.
- **ATR**: Average True Range periode default 14 yang dipakai untuk men-skala TP1, TP2, dan SL.
- **Dollar_Volume**: Nilai transaksi per bar dihitung sebagai `volume * close` dalam Rupiah; dipakai sebagai filter likuiditas.
- **Liquidity_Threshold**: Ambang minimum Dollar_Volume per bar agar sinyal valid; default Rp 500.000.000 dan dapat dikonfigurasi via input Pine.
- **Round_Trip_Property**: Properti yang menjamin payload alert yang di-encode lalu di-decode kembali oleh Telegram_Formatter tetap memuat semua field penting tanpa kehilangan informasi.

## Requirements

### Requirement 1: Universe Scalping v2 (gorengan tier)

**User Story:** Sebagai trader scalper IDX, saya ingin pool Scalping v2 hanya berisi saham dengan harga ≥ Rp1.000 yang bukan FCA dan bukan IPO baru, supaya saya tidak kena spread lebar dan suspend mendadak.

#### Acceptance Criteria

1. WHEN Pipeline_Filter membangun Pool_Scalping, THE Pipeline_Filter SHALL memasukkan hanya ticker yang harga penutupan terakhirnya lebih besar dari atau sama dengan Rp1.000.
2. WHEN Pipeline_Filter membangun Pool_Scalping, THE Pipeline_Filter SHALL mengeluarkan setiap ticker yang ada di FCA_Blacklist.
3. WHEN Pipeline_Filter membangun Pool_Scalping, THE Pipeline_Filter SHALL mengeluarkan setiap ticker yang IPO-nya kurang dari 30 hari kalender pada tanggal jalankan.
4. WHERE ticker termasuk dalam Whitelist_Seed Scalping, THE Pipeline_Filter SHALL memasukkan ticker tersebut ke Pool_Scalping hanya jika ticker tidak ada di FCA_Blacklist DAN harga penutupan terakhirnya lebih besar dari atau sama dengan Rp1.000 DAN umur listing-nya lebih besar dari atau sama dengan 30 hari kalender.
5. IF ticker tidak ada di Whitelist_Seed Scalping dan tidak memenuhi kriteria di kriteria 1, 2, atau 3, THEN THE Pipeline_Filter SHALL mengeluarkan ticker tersebut dari Pool_Scalping.
6. THE Pipeline_Filter SHALL menulis Pool_Scalping ke file `tv_scripts/scalping_stocks.json` dengan field `tier` bernilai `"SCALP_GORENGAN"` di setiap entri.

### Requirement 2: Universe Bandar AI Swing v2 (mid-cap tier)

**User Story:** Sebagai swing trader 1 mingguan, saya ingin pool Bandar AI v2 berisi saham mid-cap dengan harga ≥ Rp1.000 dan preferensi ≥ Rp3.000, supaya hasil deteksi akumulasi institusi memang relevan untuk holding 3–7 hari.

#### Acceptance Criteria

1. WHEN Pipeline_Filter membangun Pool_Bandar, THE Pipeline_Filter SHALL memasukkan hanya ticker yang harga penutupan terakhirnya lebih besar dari atau sama dengan Rp1.000.
2. WHEN Pipeline_Filter membangun Pool_Bandar, THE Pipeline_Filter SHALL mengeluarkan setiap ticker yang ada di FCA_Blacklist.
3. THE Pipeline_Filter SHALL menghitung field `price_tier` untuk setiap ticker yang punya harga penutupan terakhir, dengan nilai `"PREFERRED"` jika harga lebih besar dari atau sama dengan Rp3.000, `"BASE"` jika harga lebih besar dari atau sama dengan Rp1.000 dan kurang dari Rp3.000, atau `"BELOW"` jika harga kurang dari Rp1.000; ticker `"BELOW"` tidak masuk ke Pool_Bandar.
4. WHERE jumlah ticker dengan `price_tier` `"PREFERRED"` di Pool_Bandar lebih besar dari atau sama dengan 30, THE Pipeline_Filter SHALL menyusun Pool_Bandar hanya dari ticker `"PREFERRED"`.
5. WHERE jumlah ticker dengan `price_tier` `"PREFERRED"` di Pool_Bandar kurang dari 30, THE Pipeline_Filter SHALL melengkapi Pool_Bandar dengan ticker `"BASE"` yang Dollar_Volume rata-rata 20 bar terakhirnya lebih besar dari atau sama dengan Liquidity_Threshold sampai jumlah total mencapai 30 ticker atau pool kandidat habis.
6. THE Pipeline_Filter SHALL menulis Pool_Bandar ke file `tv_scripts/bandar_ai_stocks.json` dengan field `tier` bernilai `"BANDAR_SWING"` dan field `price_tier` di setiap entri.

### Requirement 3: Pipeline Fetch dua-pool

**User Story:** Sebagai pemilik repo, saya ingin `fetch_idx_prices.py` mendukung dua pool sekaligus, supaya satu kali fetch cukup untuk men-feed Scalping v2 dan Bandar AI v2.

#### Acceptance Criteria

1. WHEN Pipeline_Fetch dijalankan, THE Pipeline_Fetch SHALL mengambil harga penutupan terakhir untuk setiap ticker IDX yang terdaftar di kode skrip menggunakan Yahoo Finance.
2. WHEN Pipeline_Fetch menyimpan hasil, THE Pipeline_Fetch SHALL menulis file output `tv_scripts/idx_prices_v2.json` yang memuat untuk setiap ticker: simbol, harga penutupan terakhir, rata-rata Dollar_Volume 20 bar terakhir, dan flag `tier_eligible` berisi daftar tier yang memenuhi syarat (`"SCALP_GORENGAN"`, `"BANDAR_SWING"`, atau keduanya).
3. IF pengambilan harga untuk ticker gagal lebih dari tiga kali percobaan, THEN THE Pipeline_Fetch SHALL mencatat ticker tersebut ke daftar `errors` di file output dan melanjutkan pemrosesan ticker berikutnya.
4. THE Pipeline_Fetch SHALL menyertakan tanggal jalannya skrip dalam format `YYYY-MM-DD` di field `date` pada file output.

### Requirement 4: Filter likuiditas Dollar_Volume

**User Story:** Sebagai trader, saya ingin alert hanya muncul untuk emiten yang transaksinya cukup tebal, supaya saya tidak nyangkut karena order tidak terisi.

#### Acceptance Criteria

1. WHEN sebuah sinyal dievaluasi pada bar terakhir, THE Pine_Generator SHALL menghitung Dollar_Volume bar tersebut sebagai `volume * close`.
2. IF Dollar_Volume bar terakhir kurang dari Liquidity_Threshold, THEN THE Pine_Generator SHALL menahan alert dan mengubah status emiten menjadi `"WAIT_LIQ"` di tabel screener.
3. THE Pine_Generator SHALL mengekspos Liquidity_Threshold sebagai input Pine bertipe float dengan nilai default `500000000` dan label `"Min Dollar Volume per Bar (Rp)"`.

### Requirement 5: TP/SL berbasis ATR

**User Story:** Sebagai trader, saya ingin TP dan SL adaptif terhadap volatilitas masing-masing emiten, supaya saham tenang tidak dikasih target lebar dan saham liar tidak dikasih SL terlalu rapat.

#### Acceptance Criteria

1. WHEN sinyal BUY dihasilkan, THE Pine_Generator SHALL menghitung TP1 sebagai `entry + ATR * tp1_mult`, TP2 sebagai `entry + ATR * tp2_mult`, dan SL sebagai `entry - ATR * sl_mult`.
2. WHEN sinyal SELL dihasilkan, THE Pine_Generator SHALL menghitung TP1 sebagai `entry - ATR * tp1_mult`, TP2 sebagai `entry - ATR * tp2_mult`, dan SL sebagai `entry + ATR * sl_mult`.
3. THE Pine_Generator SHALL mengekspos `tp1_mult`, `tp2_mult`, dan `sl_mult` sebagai input Pine bertipe float dengan default Scalping `1.0`, `2.0`, `1.0` dan default Bandar Swing `1.5`, `3.0`, `1.5`.
4. THE Pine_Generator SHALL memastikan untuk sinyal BUY berlaku hubungan `TP2 > TP1 > entry > SL`, dan untuk sinyal SELL berlaku hubungan `TP2 < TP1 < entry < SL`.
5. IF nilai ATR pada bar evaluasi adalah nol atau `na`, THEN THE Pine_Generator SHALL menahan alert dan menandai status emiten sebagai `"WAIT_ATR"` di tabel screener.

### Requirement 6: Default timeframe per tier

**User Story:** Sebagai trader, saya ingin TF default v2 cocok dengan karakter tier-nya, supaya scalping tidak kebanyakan noise dan swing tidak kebanyakan delay.

#### Acceptance Criteria

1. THE Pine_Generator SHALL mengeset default input timeframe untuk skrip Scalping v2 ke `"5"` (5 menit).
2. THE Pine_Generator SHALL mengeset default input timeframe untuk skrip Bandar AI v2 ke `"60"` (1 jam).
3. THE Pine_Generator SHALL menyertakan Holding_Hint dengan nilai `"intraday (menit-jam)"` pada payload alert Scalping v2.
4. THE Pine_Generator SHALL menyertakan Holding_Hint dengan nilai `"swing 3-7 hari"` pada payload alert Bandar AI v2.

### Requirement 7: Payload alert kaya field

**User Story:** Sebagai pengelola webhook, saya ingin payload alert Scalping v2 dan Bandar AI v2 selalu membawa Tier, Entry, TP1, TP2, SL, dan Holding_Hint, supaya formatter Telegram bisa menampilkan informasi lengkap.

#### Acceptance Criteria

1. WHEN sinyal Scalping v2 di-fire, THE Pine_Generator SHALL menyertakan field berikut di JSON alert: `type` bernilai `"SCALP"`, `tier` bernilai `"SCALP_GORENGAN"`, `ticker`, `tf`, `signal`, `entry`, `tp1`, `tp2`, `sl`, `holding_hint`, `dollar_volume`, dan `time`.
2. WHEN sinyal Bandar AI v2 di-fire, THE Pine_Generator SHALL menyertakan field berikut di JSON alert: `type` bernilai `"BANDAR_AI"`, `tier` bernilai `"BANDAR_SWING"`, `ticker`, `tf`, `signal`, `entry`, `tp1`, `tp2`, `sl`, `holding_hint`, `dollar_volume`, dan `time`.
3. THE Pine_Generator SHALL memformat semua field harga (`entry`, `tp1`, `tp2`, `sl`) sebagai bilangan numerik tanpa simbol mata uang dan tanpa tanda kutip.
4. IF salah satu field harga atau ATR tidak tersedia pada saat alert dievaluasi, THEN THE Pine_Generator SHALL membatalkan pengiriman alert untuk bar tersebut.

### Requirement 8: Telegram formatter v2

**User Story:** Sebagai penerima notifikasi Telegram, saya ingin pesan v2 jelas membedakan tier scalping vs swing dan menampilkan TP1, TP2, SL, plus durasi hold, supaya saya bisa langsung eksekusi tanpa buka chart.

#### Acceptance Criteria

1. WHEN Telegram_Formatter menerima payload dengan `type` bernilai `"SCALP"` dan `tier` bernilai `"SCALP_GORENGAN"`, THE Telegram_Formatter SHALL menghasilkan string yang memuat secara berurutan: badge tier `"SCALP · GORENGAN"`, ticker, harga entry, TP1, TP2, SL, dan Holding_Hint.
2. WHEN Telegram_Formatter menerima payload dengan `type` bernilai `"BANDAR_AI"` dan `tier` bernilai `"BANDAR_SWING"`, THE Telegram_Formatter SHALL menghasilkan string yang memuat secara berurutan: badge tier `"BANDAR · SWING 1W"`, ticker, harga entry, TP1, TP2, SL, dan Holding_Hint.
3. IF payload tidak menyertakan field `tier`, THEN THE Telegram_Formatter SHALL mengembalikan string error yang menjelaskan field `tier` hilang dan tidak boleh memanggil Telegram API.
4. THE Telegram_Formatter SHALL menyertakan hashtag `#IDX_SCALP_V2` pada output Scalping v2 dan `#IDX_BANDAR_V2` pada output Bandar AI v2.

### Requirement 9: Penamaan file Pine v2

**User Story:** Sebagai pemilik repo, saya ingin file Pine v2 hidup berdampingan dengan v1, supaya saya bisa membandingkan hasil tanpa kehilangan referensi lama.

#### Acceptance Criteria

1. WHEN Pine_Generator menulis file Scalping v2 untuk batch tertentu, THE Pine_Generator SHALL menyimpan file dengan nama berpola `scalping_v2_batch_{label}.pine` di direktori `tv_scripts/`.
2. WHEN Pine_Generator menulis file Bandar AI v2 untuk batch tertentu, THE Pine_Generator SHALL menyimpan file dengan nama berpola `bandar_ai_v2_batch_{label}.pine` di direktori `tv_scripts/`.
3. THE Pine_Generator SHALL tidak menimpa atau menghapus file Pine v1 yang sudah ada di direktori `tv_scripts/`.

### Requirement 10: Whitelist seed kandidat

**User Story:** Sebagai pengguna, saya ingin daftar kandidat hasil riset saya dipakai sebagai seed pool, supaya hasil v2 tidak miss saham-saham yang sudah saya kurasi.

#### Acceptance Criteria

1. THE Pipeline_Filter SHALL membaca Whitelist_Seed Scalping yang berisi minimal ticker berikut: `BUMI`, `BRMS`, `MDKA`, `ANTM`, `MEDC`, `ADMR`, `ITMG`, `PTBA`, `PTRO`, `RAJA`, `ELSA`, `ESSA`, `HRUM`, `INDY`, `BYAN`, `NCKL`, `MBMA`, `AADI`, `CUAN`, `BREN`, `AMMN`, `PANI`, `CDIA`, `DCII`, `EDGE`, `BUKA`, `EMTK`, `MSIN`, `FILM`, `MNCN`, `BMHS`, `RATU`, `PALI`, `BBYB`, `ARTO`, `AMAR`, `BTPS`, `BJBR`, `BJTM`, `BBTN`, `BNGA`, `BRIS`, `MAPI`, `ERAA`, `ACES`, `RALS`, `LPPF`, `SIDO`, `ROTI`, `ULTJ`, `KLBF`, `KAEF`, `PWON`, `BSDE`, `CTRA`, `SMRA`, `JRPT`, `JKON`, `ARNA`, `SCCO`, `ASII`.
2. THE Pipeline_Filter SHALL membaca Whitelist_Seed Bandar yang berisi minimal ticker berikut: `ANTM`, `MDKA`, `MEDC`, `INCO`, `NCKL`, `AADI`, `ITMG`, `PTBA`, `ADRO`, `HRUM`, `BBTN`, `BJBR`, `BJTM`, `BRIS`, `BTPS`, `ASII`, `INTP`, `SMGR`, `INDF`, `ICBP`, `UNVR`, `CPIN`, `JPFA`, `MAPI`, `CTRA`, `PWON`, `BSDE`, `JSMR`, `TOWR`, `TBIG`, `KLBF`, `KAEF`, `SIDO`, `SILO`, `HEAL`, `ULTJ`, `MYOR`, `ROTI`, `AMMN`, `BREN`, `PANI`, `CDIA`, `EDGE`, `RAAM`.
3. WHERE sebuah ticker tidak ada di hasil Pipeline_Fetch tapi ada di Whitelist_Seed, THE Pipeline_Filter SHALL mencatat ticker tersebut ke daftar `whitelist_missing` di file output dan tidak menyertakannya dalam pool akhir.

### Requirement 11: Pembaruan README

**User Story:** Sebagai pengguna baru repo, saya ingin README menjelaskan strategi v2 dan tier baru, supaya saya tidak salah memilih file Pine.

#### Acceptance Criteria

1. THE README SHALL memuat satu bagian yang menjelaskan tier `SCALP_GORENGAN` lengkap dengan threshold harga ≥ Rp1.000, default timeframe 5 menit, dan ekspektasi holding intraday.
2. THE README SHALL memuat satu bagian yang menjelaskan tier `BANDAR_SWING` lengkap dengan threshold harga ≥ Rp1.000 (preferensi ≥ Rp3.000), default timeframe 1 jam, dan ekspektasi holding 3–7 hari.
3. THE README SHALL menyertakan instruksi langkah demi langkah untuk menjalankan Pipeline_Fetch, Pipeline_Filter, dan Pine_Generator dalam urutan yang benar.
4. THE README SHALL mendokumentasikan format JSON payload alert v2 untuk kedua tier.

### Requirement 12: Properti pengujian filter pool

**User Story:** Sebagai pengembang, saya ingin Pool_Scalping dan Pool_Bandar bisa diuji secara properti, supaya regresi pada filter cepat ketahuan.

#### Acceptance Criteria

1. THE Pipeline_Filter SHALL menjamin bahwa untuk setiap ticker `t` di Pool_Scalping berlaku properti: `t.price >= 1000` dan `t.symbol` tidak ada di FCA_Blacklist.
2. THE Pipeline_Filter SHALL menjamin bahwa untuk setiap ticker `t` di Pool_Bandar berlaku properti: `t.price >= 1000` dan `t.symbol` tidak ada di FCA_Blacklist.
3. THE Pipeline_Filter SHALL menjamin bahwa untuk setiap ticker `t` di Pool_Bandar dengan `price_tier` `"PREFERRED"` berlaku properti: `t.price >= 3000`.
4. THE Pipeline_Filter SHALL menjamin idempotency: menjalankan Pipeline_Filter dua kali berturut-turut atas input yang sama menghasilkan file output yang isinya identik.

### Requirement 13: Properti round-trip Telegram_Formatter

**User Story:** Sebagai pengembang webhook, saya ingin payload alert v2 yang masuk Telegram_Formatter selalu memunculkan semua field penting di output, supaya tidak ada informasi yang hilang di chat.

#### Acceptance Criteria

1. THE Telegram_Formatter SHALL menjamin Round_Trip_Property: untuk setiap payload v2 valid, output string mengandung representasi tekstual dari `ticker`, `entry`, `tp1`, `tp2`, `sl`, dan `holding_hint`.
2. THE Telegram_Formatter SHALL menjamin bahwa output untuk dua payload identik selalu menghasilkan string yang sama.
3. IF payload menyertakan karakter HTML khusus (`<`, `>`, `&`) di field `ticker` atau `signal`, THEN THE Telegram_Formatter SHALL meng-escape karakter tersebut sebelum dimasukkan ke string output.

### Requirement 14: Properti monotonisitas level ATR

**User Story:** Sebagai trader, saya ingin level TP dan SL selalu konsisten arahnya, supaya tidak pernah ada kasus TP berada di sisi yang salah dari Entry.

#### Acceptance Criteria

1. WHEN sinyal BUY dihasilkan, THE Pine_Generator SHALL memastikan `TP2 > TP1 > entry > SL` untuk seluruh kombinasi nilai input multiplier yang lebih besar dari nol.
2. WHEN sinyal SELL dihasilkan, THE Pine_Generator SHALL memastikan `TP2 < TP1 < entry < SL` untuk seluruh kombinasi nilai input multiplier yang lebih besar dari nol.
3. IF kondisi monotonisitas pada kriteria 1 atau 2 tidak terpenuhi karena ATR sangat kecil sehingga pembulatan ke tick price merusak urutan, THEN THE Pine_Generator SHALL menahan alert dan menandai status emiten sebagai `"WAIT_TICK"` di tabel screener.
