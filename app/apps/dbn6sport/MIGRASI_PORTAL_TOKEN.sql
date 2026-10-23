-- Migrasi: token acak untuk link portal publik klien (2026-10-23)
-- Jalankan SEKALI di database produksi (schema dn6sport), lalu pull backend
-- + restart. Setelah migrasi, link lama #c=N6-xxxx berhenti membuka portal
-- publik (uid urut = mudah ditebak); link baru memakai portal_token acak.
ALTER TABLE dn6sport.clients ADD COLUMN IF NOT EXISTS portal_token VARCHAR(64);
CREATE UNIQUE INDEX IF NOT EXISTS ix_dn6sport_clients_portal_token
  ON dn6sport.clients (portal_token);
-- Backfill: token acak 64 heksadesimal untuk semua klien yang belum punya.
UPDATE dn6sport.clients
   SET portal_token = md5(random()::text || id || clock_timestamp()::text)
                   || md5(id || random()::text || clock_timestamp()::text)
 WHERE portal_token IS NULL;
