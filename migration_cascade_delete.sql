-- ============================================================
-- EMATHTOCO — Migration: ON DELETE CASCADE untuk hasil_prediksi
-- ============================================================
--
-- TUJUAN:
-- Mengubah Foreign Key constraint hasil_prediksi_lembar_jawaban_id_fkey
-- menjadi ON DELETE CASCADE agar saat baris lembar_jawaban dihapus,
-- data hasil_prediksi yang merujuk padanya otomatis terhapus secara cascade.
--
-- CARA MENJALANKAN:
-- 1. Buka Supabase Dashboard → SQL Editor
-- 2. Copy-paste seluruh isi file ini
-- 3. Klik "Run"
--
-- ============================================================

-- 1. Hapus constraint lama
ALTER TABLE hasil_prediksi
    DROP CONSTRAINT IF EXISTS hasil_prediksi_lembar_jawaban_id_fkey;

-- 2. Buat kembali constraint baru dengan klausa ON DELETE CASCADE
ALTER TABLE hasil_prediksi
    ADD CONSTRAINT hasil_prediksi_lembar_jawaban_id_fkey
    FOREIGN KEY (lembar_jawaban_id)
    REFERENCES lembar_jawaban(id)
    ON DELETE CASCADE;

-- 3. Cetak informasi konfirmasi
DO $$
BEGIN
    RAISE NOTICE '✅ CONSTRAINT hasil_prediksi_lembar_jawaban_id_fkey berhasil diubah menjadi ON DELETE CASCADE!';
END $$;
