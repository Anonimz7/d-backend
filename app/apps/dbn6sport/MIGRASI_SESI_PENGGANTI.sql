-- Migrasi Sesi Pengganti (2026-10-21)
-- Tabel makeup: sesi pengganti hasil pengunduran izin coach, ditempatkan pada
-- tanggal + jam pilihan (boleh di luar pola mingguan klien), dilatih coach sama.
-- Aman diulang (IF NOT EXISTS).
CREATE TABLE IF NOT EXISTS dn6sport.makeup (
    id          VARCHAR(16) PRIMARY KEY,
    client_id   VARCHAR(16) REFERENCES dn6sport.clients(id),
    coach_id    VARCHAR(16) NOT NULL,
    date        DATE NOT NULL,
    time        VARCHAR(5)  NOT NULL,
    request_id  VARCHAR(16),
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_makeup_client ON dn6sport.makeup (client_id);
CREATE INDEX IF NOT EXISTS ix_makeup_date ON dn6sport.makeup (date);
CREATE INDEX IF NOT EXISTS ix_makeup_coach ON dn6sport.makeup (coach_id);
