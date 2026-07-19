# Draft BAB 4 — Implementasi Model dan Pipeline AI

> Dokumen ini berisi paragraf siap pakai untuk BAB 4 tugas akhir E-MATHTOCO.
> Semua angka bersumber dari artefak repository.

---

## 4.2.4 Implementasi Model CNN-BiLSTM dan Preprocessing per Arsitektur

### Storage Layout

Model artifacts disimpan dalam struktur berikut pada server:

```
Models_New/
├── MobileNetV2/
│   ├── model_1a.h5  (14.2 MB)
│   ├── model_1b.h5  (14.2 MB)
│   ├── ...
│   └── model_4f.h5  (14.2 MB)
├── DenseNet121/
│   ├── model_1a.h5  (33.9 MB)
│   ├── ...
│   └── model_4f.h5  (33.9 MB)
├── InceptionV3/
│   ├── model_1a.h5  (93.6 MB)
│   ├── ...
│   └── model_4f.h5  (93.6 MB)
├── manifest.json
├── training_manifest.json
└── golden_inference.json
```

Total 72 file H5 dengan ukuran keseluruhan sekitar 3,4 GB. Setiap file berisi weights dan arsitektur model lengkap dalam format Keras H5.

### Manifest JSON

Runtime menggunakan `manifest.json` (schema version 2) sebagai single source of truth untuk memuat model. Setiap entry berisi:
- `section_id`, `model_name`, `h5_filename`
- `input_shape` dan `output_shape`
- `class_labels` — daftar skor yang dikenali model
- `sha256` dan `file_size_bytes` untuk verifikasi integritas
- `preprocess` — nama fungsi preprocessing Keras yang sesuai

### Model Loader dan Cache

`services/model_registry.py` memuat model secara lazy dengan LRU cache. Saat worker menerima job prediksi, model dimuat dari disk ke memori jika belum ada di cache. Setelah prediksi selesai, model tetap di cache untuk request berikutnya.

### Preprocessing Runtime

Preprocessing pada saat inference dilakukan oleh worker:

1. Gambar JPEG dari Supabase Storage di-download
2. Convert ke grayscale
3. Apply Otsu binary threshold (non-inverted: tinta hitam, latar putih)
4. Replicate binary image ke 3 channel RGB
5. Resize ke input shape arsitektur (224×224 atau 299×299) menggunakan nearest-neighbor interpolation
6. Apply `preprocess_input` sesuai arsitektur dari manifest

### Pemetaan Skor (CLASS_SCORE_MAP)

Output softmax model menghasilkan index kelas (0, 1, 2, ...). Index ini dipetakan ke skor asli melalui `CLASS_SCORE_MAP` pada `services/class_mapping.py`. Pemetaan ini menangani kasus di mana label tidak berurutan:

| Section | Index 0 → Skor | Index 1 → Skor | Index 2 → Skor | Index 3 → Skor | Index 4 → Skor | Index 5 → Skor |
|---|---|---|---|---|---|---|
| S-1A | 1 | 2 | 3 | 4 | — | — |
| S-2B | 0 | 1 | 2 | 4 | — | — |
| S-3F | 0 | 1 | 2 | 3 | 5 | — |
| S-1F | 0 | 1 | 2 | 3 | 4 | 5 |
| Mayoritas | 0 | 1 | 2 | 3 | 4 | — |

### Tabel Spesifikasi per Arsitektur

| Spesifikasi | MobileNetV2 | DenseNet121 | InceptionV3 |
|---|---|---|---|
| Input shape | 224×224×3 | 224×224×3 | 299×299×3 |
| Jumlah file H5 | 24 | 24 | 24 |
| Ukuran per file | ~14.2 MB | ~33.9 MB | ~93.6 MB |
| Total ukuran | ~340 MB | ~812 MB | ~2.2 GB |
| Preprocessing | mobilenet_v2 | densenet | inception_v3 |
| Backbone pre-trained | ImageNet | ImageNet | ImageNet |

### Golden Inference

`golden_inference.json` berisi 72 sample predictions (satu per model) yang digunakan sebagai smoke test kontrak. Setiap entry mencatat:
- Path gambar sampel dan SHA-256-nya
- True label vs predicted label
- Confidence dan distribusi probabilitas softmax
- Status: `success` atau error

Kalimat transisi:

> Setelah seluruh subsistem diintegrasikan, tahap berikutnya adalah memverifikasi kesesuaiannya terhadap spesifikasi BAB 3. BAB 5 menyajikan lingkungan uji, skenario, hasil aktual, dan analisis terhadap keberhasilan maupun batasannya.
