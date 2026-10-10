# Changelog — 5-Backend

## 2026-10-10 — Migrasi JSON Payload → Tabel Relasional (daccounting) ✅ SELESAI

### Model baru di `app/apps/dbacc/models.py`
- `CoaAccount` (coa_accounts) — chart of accounts per perusahaan
- `Journal` + `JournalLine` (journals, journal_lines) — double-entry
- `Customer`/`Supplier` (customers, suppliers) — master
- `SalesInvoice` + `SalesInvoiceLine` — faktur penjualan
- `PurchaseInvoice` + `PurchaseInvoiceLine` — faktur pembelian
- `CashBankTransaction` (cashbank_transactions) — kas/bank
- Kolom `companies.payload` ditandai DEPRECATED (belum dihapus fisik, untuk migrasi data)

### Router diubah
- `routers/transactions.py` — tulis ke tabel relasional, bukan append JSON
- `routers/reports.py` — agregat via SQL (SUM/GROUP BY), bukan loop Python
- `routers/companies.py` — hapus baca/tulis payload
- `router.py` — daftarkan router baru

### Router baru
- `routers/coa.py` — CRUD chart of accounts
- `routers/partners.py` — CRUD customers & suppliers

### Yang belum (tahap berikutnya)
- Update frontend dash-accounting bila perlu

### Selesai 2026-10-10
- Kolom `companies.payload` dihapus total (DB kosong, tidak perlu migrasi data)
- Tidak ada sisa referensi JSON payload di kode (kecuali komentar dokumentasi)

## 2026-10-10 — Restrukturisasi schema & hapus Haylen

### Dihapus
- **Aplikasi Haylen dihapus total** dari backend:
  - Folder `app/apps/haylen/` (models, router, routers, seed, tiers, dll)
  - Import & registrasi router di `app/main.py` (`/api/haylen`)
  - Seed `haylen_owner()` di lifespan
  - Referensi di `app/core/security.py`

### Diubah — Rename schema database
Pola baru: prefix `d` + nama repo tanpa `dash-`.

| Schema lama | Schema baru | Repo git |
|---|---|---|
| `n6` | `dn6sport` | dash-n6sport |
| `dbacc` | `daccounting` | dash-accounting |
| `dbfin` | `dfinance` | dash-finance |
| `clx` | `dclaisrox` | dash-claisrox |

Detail perubahan:
- `app/core/database.py`: `APP_SCHEMAS = ["dn6sport", "daccounting", "dfinance", "dclaisrox"]`
- Semua `__table_args__ = {"schema": ...}` di model setiap aplikasi
- Semua `app_base("...")` di setiap `models/`
- Docstring di `app/core/config.py` dan `app/core/database.py`

### Catatan
- API path (`/api/n6`, `/api/dbacc`, dll) **tidak berubah** — hanya schema DB.
- Nama folder kode (`app/apps/n6/` dll) **tidak berubah** — hanya schema DB.
- Database existing perlu migrasi manual: `ALTER SCHEMA <lama> RENAME TO <baru>;`
