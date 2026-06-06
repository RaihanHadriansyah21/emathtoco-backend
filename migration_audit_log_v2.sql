-- ============================================================
-- EMATHTOCO — Migrasi: Enterprise Audit Log Schema (V2)
-- ============================================================
--
-- TUJUAN:
-- Menambahkan kolom baru ke tabel audit_log demi standardisasi
-- enterprise-grade: user_id, user_name, role, action, target, detail (JSONB).
-- Melakukan backfill aman data lama ke kolom baru tanpa menghapus data/kolom lama.
--
-- CARA MENJALANKAN DI SUPABASE:
-- 1. Buka Supabase Dashboard → SQL Editor
-- 2. Buat query baru, copy-paste seluruh isi file ini
-- 3. Klik "Run"
--
-- ============================================================

-- 1. Tambah kolom baru jika belum ada
ALTER TABLE audit_log 
ADD COLUMN IF NOT EXISTS user_id UUID,
ADD COLUMN IF NOT EXISTS user_name TEXT,
ADD COLUMN IF NOT EXISTS role TEXT,
ADD COLUMN IF NOT EXISTS action TEXT,
ADD COLUMN IF NOT EXISTS target TEXT,
ADD COLUMN IF NOT EXISTS detail JSONB;

-- 2. Lakukan backfill data existing secara aman
UPDATE audit_log
SET
  user_id = COALESCE(user_id, actor_id),
  role = COALESCE(role, actor_role),
  action = COALESCE(action, action_type),
  target = COALESCE(target, target_type),
  detail = COALESCE(
    detail, 
    CASE 
      WHEN description IS NOT NULL OR target_id IS NOT NULL THEN 
        jsonb_build_object(
          'legacy_description', description,
          'target_id', target_id
        )
      ELSE 
        NULL 
    END
  )
WHERE user_id IS NULL 
   OR role IS NULL 
   OR action IS NULL 
   OR target IS NULL 
   OR detail IS NULL;

-- 3. Isi user_name dari profil_pengguna jika ada kecocokan user_id, fallback ke 'System'
UPDATE audit_log
SET user_name = p.nama_lengkap
FROM profil_pengguna p
WHERE audit_log.user_id = p.id AND audit_log.user_name IS NULL;

UPDATE audit_log
SET user_name = 'System'
WHERE user_name IS NULL;

-- 4. Cetak informasi konfirmasi
DO $$
BEGIN
    RAISE NOTICE '✅ Migrasi skema baru dan backfill data audit_log berhasil dilakukan!';
END $$;
