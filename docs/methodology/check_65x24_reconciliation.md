# Pemeriksaan Kelengkapan 65 × 24

> Sumber: log 72 training notebook, `golden_inference.json`
> Evidence level: **B** — angka berasal dari notebook, bukan listing file aktual.

## Target

| Parameter | Nilai |
|---|---|
| Jumlah subjek (dari notebook) | 65 |
| Jumlah section | 24 |
| Target total gambar | 65 × 24 = **1.560** |

## Status per Section

Berdasarkan 72 training notebook yang masing-masing melaporkan jumlah gambar konsisten:

| Section | Gambar (logged) | Status |
|---|---|---|
| S-1A | 65 | ✓ konsisten pada 3 notebook |
| S-1B | 65 | ✓ konsisten pada 3 notebook |
| S-1C | 65 | ✓ konsisten pada 3 notebook |
| S-1D | 65 | ✓ konsisten pada 3 notebook |
| S-1E | 65 | ✓ konsisten pada 3 notebook |
| S-1F | 65 | ✓ konsisten pada 3 notebook |
| S-2A | 65 | ✓ konsisten pada 3 notebook |
| S-2B | 65 | ✓ konsisten pada 3 notebook |
| S-2C | 65 | ✓ konsisten pada 3 notebook |
| S-2D | 65 | ✓ konsisten pada 3 notebook |
| S-2E | 65 | ✓ konsisten pada 3 notebook |
| S-2F | 65 | ✓ konsisten pada 3 notebook |
| S-3A | 65 | ✓ konsisten pada 3 notebook |
| S-3B | 65 | ✓ konsisten pada 3 notebook |
| S-3C | 65 | ✓ konsisten pada 3 notebook |
| S-3D | 65 | ✓ konsisten pada 3 notebook |
| S-3E | 65 | ✓ konsisten pada 3 notebook |
| S-3F | 65 | ✓ konsisten pada 3 notebook |
| S-4A | 65 | ✓ konsisten pada 3 notebook |
| S-4B | 65 | ✓ konsisten pada 3 notebook |
| S-4C | 65 | ✓ konsisten pada 3 notebook |
| S-4D | 65 | ✓ konsisten pada 3 notebook |
| S-4E | 65 | ✓ konsisten pada 3 notebook |
| S-4F | 65 | ✓ konsisten pada 3 notebook |
| **Total** | **1.560** | |

## Catatan penting

1. Angka 65 per section berasal dari output `ImageDataGenerator.flow_from_directory()` yang dilaporkan di 72 training notebook. Ini **bukan** hasil listing file `Preprocessed_Dataset` secara independen.

2. Terdapat indikasi bahwa audit preprocessing menemukan angka **1.536** pada konteks terpisah. Gap 1.560 − 1.536 = **24 gambar** (persis 1 section atau 1 subjek) belum direkonsiliasi. Lihat `reconciliation_1560_vs_1536.md`.

3. Matriks kelengkapan **65 subjek × 24 section** (apakah setiap subjek memiliki tepat 24 gambar) **belum dapat diverifikasi** tanpa listing folder per-student. Golden inference menunjukkan format path `{NIM}/{score}/{NIM}_{section}_{score}.png`, yang mengimplikasikan bahwa data terstruktur per-student, tapi completeness per-student belum dicek.

## Apa yang dibutuhkan untuk verifikasi level A

- Listing semua file di `Preprocessed_Dataset` → dapatkan jumlah unik `{NIM}` dan jumlah file per NIM per section.
- Jika sebuah NIM tidak memiliki file di section tertentu, tandai sebagai gap.
- Jika sebuah NIM memiliki lebih dari satu file di section yang sama, tandai sebagai duplikat.
