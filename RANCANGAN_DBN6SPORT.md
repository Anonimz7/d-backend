# Struktur Tree Backend — dbn6sport

**Tanggal:** 2026-10-15
**Sumber analisis:**
- Frontend: `~/workspace/dash-n6sport/js/` (31 modul ES, fase-4 selesai)
- Kontrak API: `~/workspace/dash-n6sport-api/API_CONTRACT.md`
- Mock: `~/workspace/dash-n6sport-api/mock_server.py` (434 baris, 30+ endpoint)
- Titik masuk API frontend: `js/core/api.js` (satu-satunya modul yang `fetch()`)

Prinsip: **backend mengikuti bentuk data yang sudah dipakai frontend**,
bukan sebaliknya. Mock sudah membuktikan bentuk ini bekerja (32/32 test lulus).

---

## 1. Keputusan Desain Kunci

### 1.1. String ID sebagai primary key
Frontend memakai string ID: `u1` (member), `cl1` (client), `p1` (program),
`rp1` (report), `t1` (transaction), `N6-1001` (uid publik). Mock sama.

**Keputusan:** pakai `String` sebagai PK, bukan integer auto-increment.
- Nol translasi ID di `api.js`.
- `uid` (N6-xxxx) tetap sebagai kunci publik portal.
- Format: prefix + counter (`cl`+n, `rp`+n, dst).

### 1.2. Field fase-4 masuk database (tidak lagi local-only)

| Field frontend | Kolom DB | Tabel |
|---|---|---|
| `client.note` | `note TEXT` | `clients` |
| `client.grp` | `grp VARCHAR(16) NULL` | `clients` |
| `client.end` | `end DATE NULL` | `clients` |
| link latihan | `link_url TEXT NULL` | `reports` |
| status baca pesan | `read_at TIMESTAMPTZ NULL` | `messages` |

### 1.3. Relasi grup semi-privat
`clients.grp` = string grup bebas (bukan FK). Dua klien dengan `grp`
sama = pasangan.

### 1.4. Satu transaksi gabungan
Application layer: program `peserta:2` → satu baris `transactions`
dengan `desc = "Nama1 & Nama2"`.

---

## 2. Skema Database (`dn6sport`)

```sql
CREATE TABLE members (
  id VARCHAR(16) PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  role VARCHAR(16) NOT NULL,           -- owner|admin|head|coach
  login VARCHAR(64) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  email VARCHAR(255), wa VARCHAR(32), loc VARCHAR(128),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE programs (
  id VARCHAR(16) PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  price INTEGER NOT NULL,
  unit VARCHAR(32), wk INTEGER NOT NULL,
  lvl NUMERIC(4,2) NOT NULL,
  peserta INTEGER NOT NULL DEFAULT 1,
  fee INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE clients (
  id VARCHAR(16) PRIMARY KEY,
  uid VARCHAR(16) UNIQUE NOT NULL,
  name VARCHAR(160) NOT NULL,
  program_id VARCHAR(16) REFERENCES programs(id),
  start DATE NOT NULL, "end" DATE,
  coach_id VARCHAR(16) REFERENCES members(id),
  cond VARCHAR(64), renew BOOLEAN DEFAULT FALSE,
  hrmax INTEGER, mp INTEGER,
  arch DATE, note TEXT, grp VARCHAR(16),
  share_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON clients (coach_id);
CREATE INDEX ON clients (grp);

CREATE TABLE reports (
  id VARCHAR(16) PRIMARY KEY,
  client_id VARCHAR(16) REFERENCES clients(id) ON DELETE CASCADE,
  date DATE NOT NULL, type VARCHAR(32),
  plan_km NUMERIC(5,1), km NUMERIC(5,1),
  pace INTEGER, hr INTEGER, rasa INTEGER,
  note TEXT, missed BOOLEAN DEFAULT FALSE,
  link_url TEXT,
  correction_by VARCHAR(16) REFERENCES members(id),
  correction_text TEXT, correction_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON reports (client_id, date);

CREATE TABLE transactions (
  id VARCHAR(16) PRIMARY KEY,
  date DATE NOT NULL, type VARCHAR(8) NOT NULL, -- 'in'|'out'
  category VARCHAR(128), amount INTEGER NOT NULL,
  description TEXT,
  program_id VARCHAR(16) REFERENCES programs(id),
  coach_id VARCHAR(16) REFERENCES members(id),
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON transactions (date, type);

CREATE TABLE requests (
  id VARCHAR(16) PRIMARY KEY,
  type VARCHAR(32) NOT NULL, who VARCHAR(16) NOT NULL,
  date DATE, date2 DATE, detail TEXT,
  status VARCHAR(16) DEFAULT 'Menunggu',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE messages (
  id VARCHAR(16) PRIMARY KEY,
  kind VARCHAR(16) NOT NULL,           -- 'team'|'dm'|'broadcast'
  thread_id VARCHAR(16),
  sender VARCHAR(16) NOT NULL,
  to_text VARCHAR(160), text TEXT NOT NULL,
  t TIMESTAMPTZ NOT NULL DEFAULT now(),
  read_at TIMESTAMPTZ
);
CREATE INDEX ON messages (kind, thread_id, t);

CREATE TABLE schedule_patterns (
  coach_id VARCHAR(16) REFERENCES members(id),
  day INTEGER, slots TEXT[],
  PRIMARY KEY (coach_id, day)
);
CREATE TABLE bookings (
  id VARCHAR(16) PRIMARY KEY,
  coach_id VARCHAR(16) REFERENCES members(id),
  client_id VARCHAR(16) REFERENCES clients(id) ON DELETE CASCADE,
  day INTEGER, time VARCHAR(8)
);

CREATE TABLE correction_templates (
  id VARCHAR(16) PRIMARY KEY,
  title VARCHAR(160), text TEXT NOT NULL
);

CREATE TABLE settings (
  key VARCHAR(64) PRIMARY KEY, value JSONB NOT NULL
);
CREATE TABLE activity_log (
  id SERIAL PRIMARY KEY,
  t TIMESTAMPTZ NOT NULL DEFAULT now(),
  who VARCHAR(160), text TEXT NOT NULL
);
```

---

## 3. Struktur Tree Folder

```
app/apps/dbn6sport/
├── __init__.py
├── models.py          # 12 tabel (SQLAlchemy)
├── schemas.py         # Pydantic
├── deps.py            # get_db, get_current_user, require_role
├── seed.py            # p1-p6, 7 members, 16 clients
├── router.py          # gabung sub-router, prefix /api/v1
├── routers/
│   ├── auth.py        # POST /auth/login, GET /auth/me
│   ├── members.py     # GET/POST /members, PATCH /members/{id}
│   ├── programs.py    # GET/POST /programs, PATCH /programs/{id}
│   ├── clients.py     # CRUD + archive + nested reports
│   ├── corrections.py # POST /reports/{id}/correction, GET /corrections/pending
│   ├── schedule.py    # GET /schedule, POST/DELETE /bookings
│   ├── requests.py    # GET/POST /requests, PATCH /requests/{id}
│   ├── finance.py     # transactions, /finance/summary, /commissions
│   ├── messages.py    # team, dm, broadcasts, POST /messages/{id}/read (baru)
│   ├── dashboard.py   # GET /dashboard/summary
│   ├── settings.py    # GET/PATCH /settings, GET /correction-templates
│   ├── activity.py    # GET/POST /activity
│   └── portal.py      # GET /portal/{uid}, POST /portal/{uid}/messages (publik)
└── tiers/
```

Total: **14 router**, ~32 endpoint (semua terbukti di mock).

---

## 4. Perubahan di Frontend (`api.js`)

Backend pakai string ID + nama field sama → fungsi translasi
(`tClient`, `tTx`) bisa dihapus. Tersisa konversi tanggal → `Date`.

---

## 5. Urutan Implementasi

1. `models.py` — 12 tabel
2. `schemas.py` — Pydantic
3. `seed.py` — data dari mock
4. `routers/` — 14 file
5. `router.py` + registrasi ke `main.py`
6. Contract test vs backend asli
7. Migrasi data localStorage (jika ada)

## 6. Pertanyaan Terbuka

1. Auth: JWT + password hash, atau sederhana?
2. Soft delete (`arch`) vs hard delete — dukung keduanya?
3. Rate limit portal publik?
4. Komisi 20% — kolom atau hitung on-the-fly?
