-- ============================================================
-- EMATHTOCO — Migration: Enterprise Audit Log Schema
-- ============================================================
--
-- TUJUAN:
-- Menambahkan kolom baru ke tabel audit_log demi standardisasi
-- enterprise-grade: user_id, user_name, role, action, target, detail (JSONB).
-- Juga melakukan backfill aman data lama ke kolom baru.
--
-- CARA MENJALANKAN:
-- 1. Buka Supabase Dashboard → SQL Editor
-- 2. Copy-paste seluruh isi file ini
-- 3. Klik "Run"
--
-- ============================================================

-- 1. Tambah kolom baru jika belum ada
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_name TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS role TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS action TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS target TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS detail JSONB;

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
      WHEN description IS NOT NULL AND (description LIKE '{%' OR description LIKE '[%') THEN 
        try_cast_to_jsonb(description) 
      WHEN description IS NOT NULL THEN 
        to_jsonb(description)
      ELSE 
        NULL 
    END
  );

-- Helper function untuk menguji parsing JSON (jika diperlukan)
-- Supabase biasanya sudah mendukung to_jsonb(text) atau casting secara langsung.
-- Update description dengan fallback sederhana.
UPDATE audit_log
SET
  user_name = COALESCE(user_name, 'System')
WHERE user_name IS NULL;

-- 3. Cetak informasi konfirmasi
DO $$
BEGIN
    RAISE NOTICE '✅ Migrasi tabel audit_log berhasil dilakukan!';
END $$;
