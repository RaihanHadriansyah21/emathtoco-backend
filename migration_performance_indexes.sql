-- ============================================================
-- EMATHTOCO — Migrasi: Enterprise Audit Log Performance Indexes
-- ============================================================
--
-- TUJUAN:
-- Menambahkan indeks performa ke tabel audit_log demi mempercepat
-- pencarian, pemfilteran, dan pengurutan data audit trail.
--
-- CARA MENJALANKAN DI SUPABASE:
-- 1. Buka Supabase Dashboard → SQL Editor
-- 2. Buat query baru, copy-paste seluruh isi file ini
-- 3. Klik "Run"
--
-- ============================================================

-- 1. Indeks untuk kolom Skema Enterprise (hanya jika kolom sudah dibuat via migrasi V2)
-- Indeks pencarian action
CREATE INDEX IF NOT EXISTS idx_audit_log_action 
ON audit_log(action);

-- Indeks filter role
CREATE INDEX IF NOT EXISTS idx_audit_log_role 
ON audit_log(role);

-- Indeks pengurutan waktu (Descending)
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at 
ON audit_log(created_at DESC);

-- Indeks filter user_id
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id 
ON audit_log(user_id);

-- Indeks komposit filter action + pengurutan waktu
CREATE INDEX IF NOT EXISTS idx_audit_log_action_created 
ON audit_log(action, created_at DESC);


-- 2. Indeks untuk kolom Skema Legacy (selalu dibuat demi backward compatibility)
-- Indeks pencarian action_type
CREATE INDEX IF NOT EXISTS idx_audit_log_action_type 
ON audit_log(action_type);

-- Indeks filter actor_role
CREATE INDEX IF NOT EXISTS idx_audit_log_actor_role 
ON audit_log(actor_role);

-- Indeks pengurutan waktu legacy (Descending)
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at_legacy 
ON audit_log(created_at DESC);

-- 3. Konfirmasi penyelesaian
DO $$
BEGIN
    RAISE NOTICE '✅ Indeks performa audit_log berhasil dibuat!';
END $$;
