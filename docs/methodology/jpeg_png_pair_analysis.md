# Pasangan JPEG–PNG

> Evidence level: **D** — template, data source tidak tersedia di mesin lokal.

## Pipeline Preprocessing

Berdasarkan `manifest.json` field `training_dataset_preprocessing`:

```
JPEG (scan/foto lembar jawab)
  → Crop per section (manual atau frontend)
  → Convert to grayscale
  → Otsu binary threshold (non-inverted: tinta hitam, latar putih)
  → Simpan sebagai PNG single-channel binary
  → Gambar PNG inilah yang masuk ke Preprocessed_Dataset
```

## Format Path Dataset

Dari `golden_inference.json`, path file preprocessed mengikuti pola:

```
Preprocessed_Dataset/{NIM}/{score}/{NIM}_{section}_{score}.png
```

Contoh (dari golden_inference, dengan NIM asli):
```
Preprocessed_Dataset/08780030/1/08780030_1a_4.png
```

Artinya: subjek `08780030`, folder skor `1` (kelas index), file `08780030_1a_4.png` (section 1a, skor 4).

## Status Pasangan JPEG–PNG

**BELUM TERSEDIA.** Untuk membuat tabel pasangan JPEG–PNG yang lengkap, diperlukan:

1. Listing file di folder `Steganografi TT-46-G1` (dataset asli JPEG) — lokasi: Google Drive.
2. Listing file di folder `Preprocessed_Dataset` (PNG hasil preprocessing) — lokasi: Google Drive.
3. Matching berdasarkan nama file atau student ID.

Kedua folder hanya tersedia di Google Drive dan belum didownload ke mesin lokal.

## Template Tabel (untuk diisi setelah data tersedia)

| No | Anon ID | Section | JPEG Source | JPEG SHA-256 | PNG Preprocessed | PNG SHA-256 | Pair Verified |
|---|---|---|---|---|---|---|---|
| 1 | — | — | — | — | — | — | — |

## Rekomendasi

Untuk menyelesaikan deliverable ini:
1. Download folder `Steganografi TT-46-G1` dan `Preprocessed_Dataset` ke lokal.
2. Jalankan script listing untuk mengekstrak semua filename dan SHA-256.
3. Pasangkan berdasarkan pattern `{NIM}_{section}_{score}`.
