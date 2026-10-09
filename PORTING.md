# Spesifikasi Porting ke unified-backend

Tujuan: memindahkan tiap backend aplikasi ke `app/apps/<nama>/` dengan perubahan
minimal, agar kelimanya jalan dalam satu proses FastAPI.

## Pemetaan

| Aplikasi | Folder sumber | Folder target | Schema PG | Namespace mount |
|---|---|---|---|---|
| Haylen | `Haylen/backend` | `app/apps/haylen` | `haylen` | `/api/haylen` |
| N6 | `N6/backend` | `app/apps/n6` | `n6` | `/api/n6` (pertahankan `/v1` di dalam → `/api/n6/v1/...`) |
| DB Accounting | `DB Acounting/backend` | `app/apps/dbacc` | `dbacc` | `/api/dbacc` |
| DB Finance | `DB Finance/backend` | `app/apps/dbfin` | `dbfin` | `/api/dbfin` |
| claisrox | `claisrox/backend` | `app/apps/claisrox` | `clx` | `/api/claisrox` |

## Aturan wajib

1. **Struktur target** tiap aplikasi:
   ```
   app/apps/<nama>/
     __init__.py
     models.py            # atau package models/ seperti aslinya
     routers/             # salinan router asli
     router.py            # APIRouter gabungan (seperti include di main.py aslinya)
     tiers/               # salinan file JSON tier asli (nama file dipertahankan)
     seed.py              # fungsi ensure_owner(db) — buat owner dari env bila belum ada
     access.py / deps.py / dst sesuai kebutuhan (salinan yang diadaptasi)
   ```
2. **Model**: `from app.core.database import Base, JSONType`. Tiap model tambah
   `__table_args__ = {"schema": "<schema>"}` (gabung dengan yang sudah ada).
   Ganti `postgresql.JSONB`/`JSON` → `JSONType`. Jangan pakai tipe spesifik-driver lain.
3. **Import**: semua `from .config import settings` → `from app.core.config import settings`;
   `get_db` → `from app.core.database import get_db`;
   password/JWT → `from app.core import security` (hash_password, verify_password,
   create_access_token, create_refresh_token, decode_token, TokenError).
   Tidak boleh ada import ke backend asli.
4. **Prefix**: di `router.py` JANGAN pasang prefix global — mount point di main.py
   yang menangani. Path relatif router harus menghasilkan path final yang benar
   (contoh Haylen: router asli tanpa prefix → final `/api/haylen/auth/login`).
   N6: pertahankan segmen `/v1` (buat `router.py` dengan `prefix="/v1"`).
5. **Bentuk request/response JSON TIDAK BOLEH berubah** (kecuali auth, lihat 6).
   Nama field, status code, dan pesan error dipertahankan.
6. **Auth**:
   - Klaim token: `security.create_access_token(app="<namespace-tanpa-/api>", sub=str(id), tier=tier)`.
     Nilai `app`: `haylen`, `n6`, `dbacc`, `dbfin`, `claisrox`.
   - Dependency `get_current_user`: ambil Bearer token → `security.decode_token(token, app="<app>")`
     → muat user dari DB (tambah filter tier dari DB, bukan dari token) → 401 bila gagal.
   - **DB Accounting: tulis ulang total** — hapus SHA-256 + `"dev-token"` + header `X-Tier`.
     Login verifikasi bcrypt, kembalikan JWT asli. `POST /auth/register` hanya boleh bila
     tabel users masih kosong (bootstrap), selebihnya 403.
   - Hash lama (PBKDF2/scrypt/sha256) tidak didukung — catat di laporan.
7. **Tier**: salin file JSON apa adanya ke `tiers/`. Adaptasi kode pembaca tier agar path
   mengarah ke folder tersebut (path relatif terhadap file, mis. `Path(__file__).parent / "tiers"`).
   Semantik enforcement dipertahankan persis seperti aslinya.
8. **Lifespan/create_all**: JANGAN buat tabel di modul aplikasi — `init_db()` di core yang menangani.
   `seed.py` hanya berisi `ensure_owner(db)` (dipanggil dari main.py).
9. **Perbaikan bug yang diizinkan** (catat di laporan):
   - DB Finance: `TIERS_DIR` → folder `tiers/` sendiri; judul app; nama owner default.
   - Hapus referensi driver spesifik (`psycopg2`, dsb.) — pakai SQLAlchemy generik.
10. **Jangan** sertakan: Dockerfile, docker-compose, `.env`, skrip PowerShell, test lama.

## Laporan kembali (wajib)

- Daftar endpoint final (method + path lengkap dengan namespace).
- Perubahan perilaku vs aslinya (terutama auth).
- Perubahan frontend yang dibutuhkan (mis. `API_BASE` baru, header Authorization).
- Hal yang tidak bisa diporting / disederhanakan dan alasannya.
