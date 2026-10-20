-- Migrasi Fase 1 — Komisi Per Klien (dash-n6sport / dbn6sport)
-- Jalankan SATU KALI di database produksi (PostgreSQL, schema dn6sport)
-- sebelum / bersamaan dengan deploy backend Fase 1.
--
-- Sifat: ADITIF dan aman diulang (IF NOT EXISTS). Tidak mengubah data lama.
-- Record lama otomatis ber-client_id NULL = pembayaran legacy era per-coach;
-- frontend Fase 1 TIDAK menandai klien mana pun dari record legacy tsb.
-- (Record legacy akan ditangani migrasi alokasi di Fase 2.)

ALTER TABLE dn6sport.commission_payments
    ADD COLUMN IF NOT EXISTS client_id VARCHAR(16)
    REFERENCES dn6sport.clients(id);

CREATE INDEX IF NOT EXISTS ix_commission_payments_client_id
    ON dn6sport.commission_payments (client_id);

-- Verifikasi setelah jalan:
--   SELECT column_name FROM information_schema.columns
--   WHERE table_schema='dn6sport' AND table_name='commission_payments'
--     AND column_name='client_id';
-- harus mengembalikan 1 baris.
