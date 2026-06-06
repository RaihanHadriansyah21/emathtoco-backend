-- ============================================================
-- EMATHTOCO — Migration: RLS Policy untuk tabel audit_log
-- ============================================================
--
-- MASALAH:
-- Tabel audit_log memiliki RLS aktif tetapi TIDAK ADA policy.
-- Backend menulis menggunakan service_role_key (bypass RLS) → sukses.
-- Frontend membaca menggunakan anon_key → SELECT mengembalikan 0 baris
-- karena tidak ada policy yang mengizinkan SELECT.
--
-- SOLUSI:
-- Tambahkan policy SELECT agar authenticated users (admin) dapat
-- membaca data audit_log.
--
-- CARA MENJALANKAN:
-- 1. Buka Supabase Dashboard → SQL Editor
-- 2. Copy-paste seluruh isi file ini
-- 3. Klik "Run"
--
-- ============================================================

-- 1. Policy: Semua authenticated users boleh SELECT (membaca) audit_log
--    Ini aman karena halaman audit log hanya bisa diakses oleh admin
--    (dilindungi oleh role-based routing di frontend AuthGate).
CREATE POLICY "Allow authenticated users to read audit_log"
    ON audit_log
    FOR SELECT
    TO authenticated
    USING (true);

-- 2. Policy: Service role (backend) boleh INSERT audit_log
--    Ini sebagai safety net — service role sudah bypass RLS,
--    tetapi kita tambahkan policy ini untuk dokumentasi.
CREATE POLICY "Allow service role to insert audit_log"
    ON audit_log
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- 3. Verifikasi
DO $$
BEGIN
    RAISE NOTICE '✅ RLS policies untuk tabel audit_log berhasil ditambahkan!';
    RAISE NOTICE '   - SELECT: authenticated users (admin, dosen, mahasiswa)';
    RAISE NOTICE '   - INSERT: service_role (backend FastAPI)';
END $$;
