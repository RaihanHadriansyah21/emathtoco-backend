# Laporan Missing/Duplicate

> Tanggal: 2026-07-18
> Sumber: file on disk + manifest.json + training_manifest.json

## 1. Model Artifacts (72 H5 files)

### Status: ✅ LENGKAP — Semua 72 file ada di disk

Verifikasi dilakukan dengan membandingkan listing file di `Models_New/{Architecture}/` terhadap 72 entry di `manifest.json`.

#### MobileNetV2 — 24/24 ✅

| File | On Disk | Size Match | In Manifest |
|---|---|---|---|
| model_1a.h5 | ✅ | ✅ 14196712 | ✅ |
| model_1b.h5 | ✅ | ✅ 14197224 | ✅ |
| model_1c.h5 | ✅ | ✅ 14197224 | ✅ |
| model_1d.h5 | ✅ | ✅ 14197224 | ✅ |
| model_1e.h5 | ✅ | ✅ 14197224 | ✅ |
| model_1f.h5 | ✅ | ✅ 14197736 | ✅ |
| model_2a.h5 | ✅ | ✅ 14197224 | ✅ |
| model_2b.h5 | ✅ | ✅ 14196712 | ✅ |
| model_2c.h5 | ✅ | ✅ 14197224 | ✅ |
| model_2d.h5 | ✅ | ✅ 14197224 | ✅ |
| model_2e.h5 | ✅ | ✅ 14197224 | ✅ |
| model_2f.h5 | ✅ | ✅ 14197736 | ✅ |
| model_3a.h5 | ✅ | ✅ 14197224 | ✅ |
| model_3b.h5 | ✅ | ✅ 14197224 | ✅ |
| model_3c.h5 | ✅ | ✅ 14197224 | ✅ |
| model_3d.h5 | ✅ | ✅ 14197224 | ✅ |
| model_3e.h5 | ✅ | ✅ 14197224 | ✅ |
| model_3f.h5 | ✅ | ✅ 14197224 | ✅ |
| model_4a.h5 | ✅ | ✅ 14197224 | ✅ |
| model_4b.h5 | ✅ | ✅ 14197224 | ✅ |
| model_4c.h5 | ✅ | ✅ 14197224 | ✅ |
| model_4d.h5 | ✅ | ✅ 14197224 | ✅ |
| model_4e.h5 | ✅ | ✅ 14197224 | ✅ |
| model_4f.h5 | ✅ | ✅ 14197736 | ✅ |

#### DenseNet121 — 24/24 ✅
Semua 24 file hadir di disk dengan size cocok terhadap manifest.

#### InceptionV3 — 24/24 ✅
Semua 24 file hadir di disk dengan size cocok terhadap manifest.

### Duplikasi SHA-256 antar model

Tidak ditemukan SHA-256 yang duplikat antar file model. Setiap file H5 memiliki hash unik, yang mengonfirmasi bahwa tidak ada file yang secara tidak sengaja di-copy.

### Catatan: training_manifest naming discrepancy

Pada `training_manifest.json`, entry MobileNetV2 section 4f tercatat sebagai `Section_4f.h5` (huruf kapital S), sementara file di disk lokal bernama `model_4f.h5`. SHA-256 cocok (`5dba1422...42d3`), sehingga ini adalah rename yang telah direncanakan, bukan file berbeda.

---

## 2. Dataset Images (1.560 target)

### Status: ❌ BELUM DAPAT DIVERIFIKASI

File dataset PNG/JPEG hanya tersedia di Google Drive dan belum didownload ke mesin lokal. Tidak ada listing file `Preprocessed_Dataset` di repository.

Yang dibutuhkan:
- Download `Preprocessed_Dataset` atau jalankan listing command di Colab.
- Hitung: `ls -R Preprocessed_Dataset/ | wc -l`
- Identifikasi file PNG yang ada tapi tidak seharusnya, atau seharusnya ada tapi tidak ada.

---

## 3. Manifest Coverage

| Artifact | Entries di manifest | File di disk | Missing | Extra |
|---|---|---|---|---|
| MobileNetV2 H5 | 24 | 24 | 0 | 0 |
| DenseNet121 H5 | 24 | 24 | 0 | 0 |
| InceptionV3 H5 | 24 | 24 | 0 | 0 |
| golden_inference.json | 1 | 1 | 0 | 0 |
| training_manifest.json | 1 | 1 | 0 | 0 |
| Preprocessing.ipynb | 1 | 1 | 0 | 0 |
| **Total** | **74** | **74** | **0** | **0** |

Extra files di disk yang **tidak** ada di manifest:
- `Models_New/MobileNetV2/Notebook/` — folder notebook training (expected, bukan artifact runtime)
- `Models_New/DenseNet121/Notebook/` — idem
- `Models_New/InceptionV3/Notebook/` — idem
