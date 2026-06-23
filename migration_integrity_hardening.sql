-- Migration: Database Integrity Hardening (Fix A & Fix B)
-- Adds unique constraints to pengumpulan_tugas and lembar_jawaban tables

-- FIX A: Ensure one student has at most one active submission per course
ALTER TABLE public.pengumpulan_tugas
    ADD CONSTRAINT uq_pengumpulan_tugas_mahasiswa_mata_kuliah
    UNIQUE (mahasiswa_id, mata_kuliah_id);

-- FIX B: Ensure one submission has at most one record per section/slot
ALTER TABLE public.lembar_jawaban
    ADD CONSTRAINT uq_lembar_jawaban_submission_section
    UNIQUE (pengumpulan_tugas_id, section_code);
