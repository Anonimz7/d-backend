# Unified Backend — 1 Backend untuk 5 Aplikasi Apk-Final

Satu proses FastAPI yang melayani endpoint kelima aplikasi:

| Namespace | Aplikasi | Endpoint |
|---|---|---|
| `/api/haylen/*` | Haylen (sekolah renang) | 20 path: auth, access/me, tiers, dashboard, reports, members, programs, coaches, schedules, transactions, facilities, settings |
| `/api/n6/v1/*` | N6 (dashboard kepelatihan) | 60 path: auth (+refresh, access/me), accounts, clients, schedules, pricing, programs, commissions, finance, tickets, messages, attendance, monitoring, corrections, athletes, reports, portal |
| `/api/dbacc/*` | DB Accounting | 12 path: auth, companies, journal, sales/purchases/cashbank/journal append, reports (labarugi, neraca, pajak) |
| `/api/dbfin/*` | DB Finance | 10 path: auth, access/me, state, profile, accounts, transactions, budgets, bills, goals, investments |
| `/api/claisrox/*` | Claisrox (produksi) | 23 path: auth, snapshot, keuangan, CRUD 9 koleksi (produk, bahan-baku, supplier, customer, penjualan, pembelian, resep, produksi, online) |

Plus `GET /health`.

## Arsitektur

- **Satu database PostgreSQL, 5 schema**: `haylen`, `n6`, `dbacc`, `dbfin`, `clx`.
  Tiap aplikasi punya registry model sendiri (`app.core.database.app_base()`),
  sehingga nama tabel/class yang sama antar aplikasi tidak bertabrakan.
- **Satu JWT** (HS256): klaim `{sub, app, tier, typ, iat, exp, jti}`. Klaim `app`
  mengisolasi token antar aplikasi (token Haylen ditolak di N6, dst.).
- **Satu hashing**: bcrypt (cost 12) untuk semua aplikasi.
- **Tier**: tiap aplikasi memakai file JSON tier-nya sendiri
  (`app/apps/<nama>/tiers/`), semantik enforcement dipertahankan dari aslinya.
  File tier adalah SATU-SATUNYA sumber konfigurasi tier — frontend tidak lagi
  menyimpan salinannya. Tiap aplikasi menyediakan SATU endpoint akses per-user
  yang dihitung server dari tier di DB (bukan dari input client):
  Haylen `GET /access/me` → `{tier, name, menus, features}`,
  N6 `GET /v1/access/me` → profil + `{menus, actions}`,
  DB Accounting `GET /auth/me` → `{tier, name, roleLabel, menus, permissions}`,
  DB Finance `GET /access/me` → `{tier, name, access}`,
  claisrox `GET /auth/me` → `{username, name, tier, tierName, menus}`.
  Frontend hanya menyimpan vocabulary key→UI dan menyembunyikan menu (UX);
  server tetap penegak utama (403).

## Perubahan penting vs backend asli

1. **DB Accounting auth ditulis ulang total** — backend asli memakai SHA-256 +
   token dummy `"dev-token"` + tier dari header `X-Tier` (tidak aman).
   Kini bcrypt + JWT asli; `POST /auth/register` hanya untuk bootstrap
   (403 bila user sudah ada).
2. **Hash & token lama tidak berlaku** — semua user harus dibuat ulang
   (owner tiap aplikasi dibuat otomatis dari `.env` saat startup).
   Pengecualian: N6 aslinya sudah bcrypt, tapi token lamanya tetap invalid
   karena klaim `app` baru.
3. **Bug DB Finance diperbaiki**: `TIERS_DIR` yang menunjuk folder tidak ada,
   judul "Claisrox API", dan default owner "Denis".
4. **Bug N6 diperbaiki**: `schemas/account.py` memakai `TIER_ADMIN` yang tidak
   diimpor (NameError saat import; tidak pernah ketahuan karena backend belum dipakai).
5. **Frontend**: tiap aplikasi cukup ubah `API_BASE`/`BASE_URL` di `js/config.js`:
   `https://<host>/api/haylen`, `https://<host>/api/n6` (path `/v1/...` tetap),
   `https://<host>/api/dbacc`, `https://<host>/api/dbfin`, `https://<host>/api/claisrox`.
   DB Accounting: kirim `Authorization: Bearer <token>` di setiap request
   (ganti konsep `X-Tier`).

## Menjalankan

```bash
cd unified-backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # isi JWT_SECRET (min 32 karakter) & password owner
# buat database PostgreSQL: createdb apkfinal
uvicorn app.main:app --reload
# dokumen: http://localhost:8000/docs
```

Tabel + schema dibuat otomatis saat startup; owner tiap aplikasi dibuat dari `.env`.

## Mode uji (tanpa PostgreSQL)

```bash
DATABASE_URL="sqlite:////tmp/uji.db" JWT_SECRET="test-secret-min-32-karakter-1234567890" \
  .venv/bin/python -c "from fastapi.testclient import TestClient; ..."
```

Mode SQLite me-ATTACH tiap schema sebagai database `:memory:` terpisah —
hanya untuk pengujian lokal, bukan produksi.

## Struktur

```
unified-backend/
  app/
    main.py              # FastAPI + lifespan + mount 5 namespace
    core/
      config.py          # 1 .env untuk semua aplikasi
      database.py        # engine, Base per-app, JSONType, init_db, get_db
      security.py        # bcrypt + JWT terpadu
    apps/
      haylen/            # routers, models (schema haylen), tiers, access, seed
      n6/                # + metrics.py, period.py, deps.py, schemas/
      dbacc/             # + reports (labarugi/neraca/pajak dihitung server)
      dbfin/             # + services/ (access, sections, state upsert+prune)
      claisrox/          # + models/, schemas/, resources (pabrik CRUD)
  requirements.txt
  .env.example
  PORTING.md             # spesifikasi yang dipakai saat porting
```

## Status uji

23/23 skenario lolos via TestClient (mode SQLite): login 5 aplikasi, CRUD,
snapshot/state sync, laporan, refresh token N6, penolakan token lintas aplikasi
(401), enforcement tier (403), register bootstrap-only DB Accounting.
Uji PostgreSQL asli belum dilakukan — butuh server PostgreSQL.
