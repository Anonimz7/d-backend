# Persiapan Migrasi: JSON Payload → Tabel Relasional (daccounting)

## Status Sekarang
- Tabel `companies.payload` (JSON) menampung: `coa`, `journal`, `sales`, `purchases`, `cashbank`
- Masalah: race condition, laporan lambat, tidak ada integritas data

## Desain Tabel Baru

### 1. `coa_accounts` — Chart of Accounts
```python
class CoaAccount(Base):
    __tablename__ = "coa_accounts"
    __table_args__ = {"schema": "daccounting"}

    id          = Column(String, primary_key=True, default=_uuid)
    company_id  = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    code        = Column(String(20), nullable=False)          # mis: "1100"
    name        = Column(String(100), nullable=False)         # mis: "Kas"
    type        = Column(String(20), nullable=False)          # Aset|Kewajiban|Modal|Pendapatan|Beban
    normal      = Column(String(6), nullable=False)           # debit|credit
    is_active   = Column(Boolean, default=True)
```
Pengganti: `payload["coa"]`

### 2. `journals` + `journal_lines` — Double-entry
```python
class Journal(Base):
    __tablename__ = "journals"
    __table_args__ = {"schema": "daccounting"}

    id          = Column(String, primary_key=True, default=_uuid)
    company_id  = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    date        = Column(Date, nullable=False, index=True)
    description = Column(String(255), default="")
    ref_no      = Column(String(50), default="")              # no bukti
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

class JournalLine(Base):
    __tablename__ = "journal_lines"
    __table_args__ = {"schema": "daccounting"}

    id          = Column(String, primary_key=True, default=_uuid)
    journal_id  = Column(String, ForeignKey("daccounting.journals.id"), nullable=False, index=True)
    account_id  = Column(String, ForeignKey("daccounting.coa_accounts.id"), nullable=False, index=True)
    debit       = Column(Numeric(18,2), default=0)
    credit      = Column(Numeric(18,2), default=0)
```
Pengganti: `payload["journal"]` (yang berisi `{date, lines: [{account, debit, credit}]}`)

### 3. `customers` / `suppliers` — Master
```python
class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "daccounting"}
    id, company_id (FK, index), name, email, phone, address

class Supplier(Base):  # struktur sama
    __tablename__ = "suppliers"
```

### 4. `sales_invoices` + `sales_invoice_lines`
```python
class SalesInvoice(Base):
    __tablename__ = "sales_invoices"
    __table_args__ = {"schema": "daccounting"}
    id, company_id (FK, index), invoice_no (unique per company),
    customer_id (FK nullable), date (index), total, status, created_at

class SalesInvoiceLine(Base):
    __tablename__ = "sales_invoice_lines"
    __table_args__ = {"schema": "daccounting"}
    id, invoice_id (FK, index), description, qty, price, subtotal
```
Pengganti: `payload["sales"]`

### 5. `purchase_invoices` + `purchase_invoice_lines`
Struktur mirip sales, dengan `supplier_id` sebagai pengganti `customer_id`.
Pengganti: `payload["purchases"]`

### 6. `cashbank_transactions`
```python
class CashBankTransaction(Base):
    __tablename__ = "cashbank_transactions"
    __table_args__ = {"schema": "daccounting"}
    id, company_id (FK, index), date (index),
    direction (masuk|keluar), account_id (FK coa_accounts),
    amount, description, ref_no
```
Pengganti: `payload["cashbank"]`

### 7. `companies` — Hapus kolom payload
```python
# HAPUS: payload = Column(JSONType, ...)
# Kolom lain tetap: id, owner_id, name, industry, color, initial, updated_at
```

## Perubahan Router yang Diperlukan

| File | Perubahan |
|---|---|
| `routers/transactions.py` | `append_trx` → INSERT ke tabel spesifik; `list_journal` → query JOIN |
| `routers/reports.py` | `_sums`, `labarugi`, `neraca`, `pajak` → query SQL agregat |
| `routers/companies.py` | Hapus baca/tulis `payload` |
| Baru: `routers/coa.py` | CRUD chart of accounts |
| Baru: `routers/customers.py`, `routers/suppliers.py` | CRUD master |

## Urutan Migrasi
1. Buat model baru di `models.py` (tambah, jangan hapus dulu)
2. Buat tabel via `init_db()` / Alembic
3. Tulis skrip migrasi data: baca `payload` → INSERT ke tabel baru
4. Update routers ke tabel baru
5. Verifikasi laporan sama hasilnya
6. Hapus kolom `payload`
7. Hapus kode baca `payload`

## Estimasi File Baru/Diubah
- `models.py`: +8 model baru, -1 kolom
- `routers/`: 3 diubah, 3 baru
- Skrip migrasi: 1 file
