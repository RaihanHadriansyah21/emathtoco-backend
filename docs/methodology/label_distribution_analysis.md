# Distribusi Label per Section — Dataset E-MATHTOCO

> Sumber: `services/class_mapping.py` dan `Models_New/manifest.json`
> Evidence level: **B** — berasal dari label yang dikenali oleh model, bukan dari listing file dataset asli.

## Ringkasan Jumlah Kelas per Section

| Section | Jumlah Kelas | Label yang Ada | Skor Maks | Anomali |
|---|---|---|---|---|
| S-1A | 4 | 1, 2, 3, 4 | 4 | **Tidak ada skor 0** |
| S-1B | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-1C | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-1D | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-1E | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-1F | 6 | 0, 1, 2, 3, 4, 5 | 5 | — |
| S-2A | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-2B | 4 | 0, 1, 2, 4 | 4 | **Skor 3 tidak ada** |
| S-2C | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-2D | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-2E | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-2F | 6 | 0, 1, 2, 3, 4, 5 | 5 | — |
| S-3A | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-3B | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-3C | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-3D | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-3E | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-3F | 5 | 0, 1, 2, 3, 5 | 5 | **Skor 4 tidak ada** |
| S-4A | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-4B | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-4C | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-4D | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-4E | 5 | 0, 1, 2, 3, 4 | 4 | — |
| S-4F | 6 | 0, 1, 2, 3, 4, 5 | 5 | — |

## Statistik Agregat

| Metrik | Nilai |
|---|---|
| Total section | 24 |
| Section dengan 4 kelas | 2 (S-1A, S-2B) |
| Section dengan 5 kelas | 19 |
| Section dengan 6 kelas | 3 (S-1F, S-2F, S-4F) |
| Total output classes unik | 6 (skor 0–5) |
| Total output neurons (semua section) | 118 |

## Analisis Anomali Label

### S-1A — Tidak memiliki skor 0
Section S-1A hanya memiliki label [1, 2, 3, 4]. Ini berarti **tidak ada sampel mahasiswa yang mendapat skor 0** pada section ini dalam dataset training. Model output hanya 4 neuron. Implikasi: jika mahasiswa benar-benar mendapat skor 0, model tidak dapat memprediksinya.

### S-2B — Skor 3 tidak ada (label encoding artifact)
Section S-2B memiliki label [0, 1, 2, 4] — skor 3 hilang. Kemungkinan besar tidak ada sampel berskor 3 dalam dataset training untuk section ini. Model output 4 neuron, dan `CLASS_SCORE_MAP` memetakan index 3 → skor 4 (bukan skor 3).

### S-3F — Skor 4 tidak ada (label encoding artifact)
Section S-3F memiliki label [0, 1, 2, 3, 5] — skor 4 hilang. Sama seperti S-2B, ini adalah artifact dari label encoding karena tidak ada sampel berskor 4 dalam dataset training.

## Distribusi Jumlah Gambar per Label

> **BELUM TERSEDIA**: Distribusi aktual (berapa gambar per skor per section) memerlukan listing file dari folder `Preprocessed_Dataset` atau output `ImageDataGenerator` pada notebook. Data ini tidak ada di repository saat ini.

Informasi yang diketahui:
- Setiap section memiliki **65 gambar total** (berdasarkan log notebook).
- Distribusi label per section **tidak merata** — beberapa confusion matrix menunjukkan konsentrasi prediksi pada kelas mayoritas, mengindikasikan ketidakseimbangan kelas.
