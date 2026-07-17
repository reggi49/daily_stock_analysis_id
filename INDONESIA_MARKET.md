# Dukungan Pasar Indonesia (IDX) — Native

Dokumen ini merangkum perubahan yang menjadikan **Bursa Efek Indonesia (IDX)** sebagai pasar kelas satu di sistem, di-route ke **Yahoo Finance** memakai suffix `.JK` (mis. `BBCA.JK`, `TLKM.JK`, `ASII.JK`). Kode ticker Indonesia bersifat **huruf** (bukan angka), jadi lapisan deteksi pasar diperluas agar mendukung basis alfabet — bukan sekadar mengganti watchlist.

> Watchlist **tidak di-hardcode** di kode. Semua daftar saham tetap digerakkan oleh konfigurasi (`STOCK_LIST` / `STOCK_GROUP_N`), sehingga mudah dikembangkan & dikategorikan.

## Kode market baru: `id`
Pasar Indonesia memakai tag `id`, sejajar dengan `cn/hk/us/jp/kr/tw`.

## Perubahan inti

### 1. Deteksi simbol suffix (basis huruf)
`src/services/market_symbol_utils.py`
- `SuffixMarketSpec` kini punya `alpha_lengths` (selain `digit_lengths`), sehingga bisa menerima basis ticker huruf.
- Ditambah spec Indonesia: `SuffixMarketSpec("id", ("JK",), alpha_lengths=(2, 3, 4, 5))`.
- `get_suffix_market("BBCA.JK") -> "id"`. Deteksi hanya lewat suffix `.JK` (tanpa suffix, `BBCA` tetap dianggap ticker AS — konsisten dengan pola JP/KR/TW).
- Ditambah helper `is_id_suffix_symbol`.

### 2. Normalisasi & validasi kode
`src/services/stock_code_utils.py`
- `is_code_like` & `normalize_code` mengenali `.JK`; `.JK` ditambahkan ke `_PRESERVE_SUFFIXES`.

### 3. Routing data provider
`data_provider/base.py`
- Ditambah `_is_id_market`; `_market_tag` mengembalikan `id`.
- `normalize_stock_code` mempertahankan bentuk `BBCA.JK` (huruf di-uppercase).
- `get_daily_data` & `get_realtime_quote` mengarahkan pasar `id` ke Yahoo Finance.
- `YfinanceFetcher` didaftarkan mendukung `id` (`_DAILY_MARKET_FETCHER_SUPPORT`).
- `get_fundamental_context` memakai jalur fundamental offshore untuk `id`.

`data_provider/yfinance_fetcher.py`
- Ditambah `_is_id_suffix_stock`; `_convert_stock_code` meneruskan simbol `.JK` apa adanya ke Yahoo.
- Ditambah `_get_id_main_indices` (indeks JKSE/IHSG `^JKSE`, LQ45 `^JKLQ45`) + dispatch `region == "id"`.
- Kutipan realtime menerima simbol `.JK`.

### 4. Profil market review
`src/core/market_profile.py`
- Ditambah `ID_PROFILE` (index sentimen `JKSE`, kata kunci berita Indonesia) + cabang `get_profile("id")`.

### 5. Kalender bursa
`src/core/trading_calendar.py`
- `MARKET_EXCHANGE["id"] = "XIDX"` (kalender `exchange-calendars`), `MARKET_TIMEZONE["id"] = "Asia/Jakarta"`.
- `id` ditambahkan ke daftar market efektif market-review.

### 6. Konfigurasi
`src/config.py`
- `MARKET_REVIEW_REGION` menerima `id` (dan `both` mencakup `id`).

### 7. Permukaan layanan (agar `id` first-class)
- `intelligence_service`, `market_light_service`, `portfolio_service` (VALID_MARKETS & PARTIAL_VALUATION_MARKETS), `decision_signal_service`, `pipeline`, `market_phase_summary`, `market_analyzer`, `daily_market_context` — semua diperluas untuk mengenali `id` (label “Saham Indonesia” / “Indonesia”).

## Konfigurasi (.env)
```
MARKET_REVIEW_REGION=id
# Contoh watchlist (silakan ganti / kategorikan lewat STOCK_GROUP_N):
STOCK_LIST=BBCA.JK,BBRI.JK,BMRI.JK,TLKM.JK,ASII.JK,UNVR.JK
```

## Catatan / batasan
- `REPORT_LANGUAGE` bawaan hanya mendukung `zh/en/ko`; belum ada opsi Bahasa Indonesia. Berita/prompt profil Indonesia sudah disiapkan, namun bahasa laporan akhir mengikuti opsi yang ada (disarankan `en`). Menambah `id` sebagai bahasa laporan adalah pekerjaan lanjutan tersendiri.
- Data IDX diambil dari Yahoo Finance (sumber fallback), sehingga kedalaman fundamental sekelas pasar offshore lain (jp/kr/tw), bukan sedetail data A-share domestik.
- Deteksi hanya aktif untuk kode ber-suffix `.JK`. Kode huruf tanpa suffix akan diperlakukan sebagai ticker AS.

## Verifikasi
Semua modul lolos pemeriksaan sintaks. Uji fungsional (lolos):
- `get_suffix_market('BBCA.JK') == 'id'`, `normalize_stock_code('tlkm.jk') == 'TLKM.JK'`
- `_market_tag('ASII.JK') == 'id'`, `'id' in YfinanceFetcher support`
- `YfinanceFetcher()._convert_stock_code('bbca.jk') == 'BBCA.JK'`
- `Config._parse_market_review_region('id') == 'id'`, `get_profile('id').region == 'id'`
