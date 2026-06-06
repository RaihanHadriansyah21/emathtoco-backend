-- ============================================================
-- EMATHTOCO — Migration: Unique Constraint pada hasil_prediksi
-- ============================================================
--
-- TUJUAN:
-- Menambahkan UNIQUE CONSTRAINT pada (pengumpulan_tugas_id, section_code)
-- agar database menolak duplikasi walaupun ada bug di backend.
--
-- EVALUASI KEAMANAN:
-- ✅ Semua jalur INSERT/UPSERT di backend sudah menggunakan
--    on_conflict="pengumpulan_tugas_id,section_code"
-- ✅ Batch AI route (frontend) menulis ke lembar_jawaban,
--    BUKAN ke hasil_prediksi — tidak terpengaruh
-- ✅ save_prediction() sudah diubah ke UPSERT
-- ✅ upsert_prediction() sudah diubah ke UPSERT
-- ✅ delete_predictions_by_submission() menghapus SEMUA prediksi
--    per submission sebelum re-run
--
-- CARA MENJALANKAN:
-- 1. Buka Supabase Dashboard → SQL Editor
-- 2. Copy-paste seluruh isi file ini
-- 3. Klik "Run"
-- 4. Verifikasi hasilnya di output
--
-- AMAN DIJALANKAN BERULANG (idempotent)
-- ============================================================

-- ┌─────────────────────────────────────────────────────────┐
-- │  STEP 1: Cek apakah ada duplikat di data existing       │
-- └─────────────────────────────────────────────────────────┘
-- Jalankan ini terlebih dahulu untuk melihat apakah ada duplikat:
-- (Tidak mengubah data, hanya menampilkan informasi)

DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO duplicate_count
    FROM (
        SELECT pengumpulan_tugas_id, section_code
        FROM hasil_prediksi
        GROUP BY pengumpulan_tugas_id, section_code
        HAVING COUNT(*) > 1
    ) AS dupes;

    IF duplicate_count > 0 THEN
        RAISE NOTICE '⚠ Ditemukan % kombinasi (submission, section) yang memiliki duplikat.', duplicate_count;
        RAISE NOTICE 'Duplikat akan dihapus — hanya menyisakan record terbaru.';
    ELSE
        RAISE NOTICE '✅ Tidak ada duplikat ditemukan. Constraint bisa langsung ditambahkan.';
    END IF;
END $$;


-- ┌─────────────────────────────────────────────────────────┐
-- │  STEP 2: Hapus duplikat (sisakan yang terbaru)           │
-- └─────────────────────────────────────────────────────────┘
-- Untuk setiap (pengumpulan_tugas_id, section_code) yang memiliki
-- lebih dari 1 row, hanya menyisakan row dengan created_at terbaru.

DELETE FROM hasil_prediksi
WHERE id NOT IN (
    SELECT DISTINCT ON (pengumpulan_tugas_id, section_code) id
    FROM hasil_prediksi
    ORDER BY pengumpulan_tugas_id, section_code, created_at DESC
);


-- ┌─────────────────────────────────────────────────────────┐
-- │  STEP 3: Drop index/constraint lama (jika ada)           │
-- └─────────────────────────────────────────────────────────┘

-- Drop unique INDEX lama (3-kolom: termasuk model_ai)
DROP INDEX IF EXISTS idx_hasil_prediksi_unique;

-- Drop constraint lama jika sudah pernah ditambahkan sebelumnya
ALTER TABLE hasil_prediksi
    DROP CONSTRAINT IF EXISTS uq_hasil_prediksi_submission_section;


-- ┌─────────────────────────────────────────────────────────┐
-- │  STEP 4: Tambahkan UNIQUE CONSTRAINT baru (2-kolom)      │
-- └─────────────────────────────────────────────────────────┘
-- Constraint ini memastikan:
--   1 submission + 1 section = maksimal 1 row
--
-- Jika dosen mengganti model AI (MobileNetV2 → DenseNet121),
-- backend akan UPDATE row yang sama, bukan INSERT baru.

ALTER TABLE hasil_prediksi
    ADD CONSTRAINT uq_hasil_prediksi_submission_section
    UNIQUE (pengumpulan_tugas_id, section_code);


-- ┌─────────────────────────────────────────────────────────┐
-- │  STEP 5: Verifikasi                                      │
-- └─────────────────────────────────────────────────────────┘

DO $$
DECLARE
    constraint_exists BOOLEAN;
    row_count INTEGER;
BEGIN
    -- Cek constraint sudah ada
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'hasil_prediksi'
        AND constraint_name = 'uq_hasil_prediksi_submission_section'
        AND constraint_type = 'UNIQUE'
    ) INTO constraint_exists;

    -- Cek total rows
    SELECT COUNT(*) INTO row_count FROM hasil_prediksi;

    IF constraint_exists THEN
        RAISE NOTICE '✅ UNIQUE CONSTRAINT berhasil ditambahkan!';
        RAISE NOTICE '   Constraint: uq_hasil_prediksi_submission_section';
        RAISE NOTICE '   Kolom: (pengumpulan_tugas_id, section_code)';
        RAISE NOTICE '   Total rows saat ini: %', row_count;
    ELSE
        RAISE NOTICE '❌ GAGAL: Constraint tidak ditemukan. Periksa error di atas.';
    END IF;
END $$;
