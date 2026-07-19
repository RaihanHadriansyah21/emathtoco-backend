# SHA-256 Registry — 72 Model H5 E-MATHTOCO

> Sumber: `Models_New/manifest.json` dan `Models_New/training_manifest.json`
> Verifikasi disk: sample MobileNetV2/model_1a.h5 dikonfirmasi cocok via `certutil` pada 2026-07-18.
> Evidence level: **B** (manifest + file checksum lokal).

## Ringkasan

| Arsitektur   | Jumlah H5 | Input Shape  | Total Size (disk) |
|---|---|---|---|
| MobileNetV2  | 24         | 224×224×3    | ~340 MB |
| DenseNet121  | 24         | 224×224×3    | ~812 MB |
| InceptionV3  | 24         | 299×299×3   | ~2.2 GB |
| **Total**    | **72**     |              | **~3.4 GB** |

---

## MobileNetV2 (24 files)

| Section | File | Size (bytes) | SHA-256 | Output Classes |
|---|---|---|---|---|
| S-1A | model_1a.h5 | 14196712 | `2600ed71...23517d` | 4: [1,2,3,4] |
| S-1B | model_1b.h5 | 14197224 | `38c1159c...cec5b6` | 5: [0,1,2,3,4] |
| S-1C | model_1c.h5 | 14197224 | `fb024a40...d186c` | 5: [0,1,2,3,4] |
| S-1D | model_1d.h5 | 14197224 | `2fd090ff...feea9` | 5: [0,1,2,3,4] |
| S-1E | model_1e.h5 | 14197224 | `3ed85077...a9272` | 5: [0,1,2,3,4] |
| S-1F | model_1f.h5 | 14197736 | `29e5bd1d...79f7` | 6: [0,1,2,3,4,5] |
| S-2A | model_2a.h5 | 14197224 | `d07db42c...c30b` | 5: [0,1,2,3,4] |
| S-2B | model_2b.h5 | 14196712 | `04c1bbbb...ce72` | 4: [0,1,2,4] |
| S-2C | model_2c.h5 | 14197224 | `416c5570...2ce2` | 5: [0,1,2,3,4] |
| S-2D | model_2d.h5 | 14197224 | `b72944d6...8ea1` | 5: [0,1,2,3,4] |
| S-2E | model_2e.h5 | 14197224 | `7d1754e3...87e1` | 5: [0,1,2,3,4] |
| S-2F | model_2f.h5 | 14197736 | `e131de5a...0603` | 6: [0,1,2,3,4,5] |
| S-3A | model_3a.h5 | 14197224 | `d2f3781b...d60f` | 5: [0,1,2,3,4] |
| S-3B | model_3b.h5 | 14197224 | `abbe78bd...bb91` | 5: [0,1,2,3,4] |
| S-3C | model_3c.h5 | 14197224 | `44abfab5...7843` | 5: [0,1,2,3,4] |
| S-3D | model_3d.h5 | 14197224 | `cb9bcb7e...9782` | 5: [0,1,2,3,4] |
| S-3E | model_3e.h5 | 14197224 | `76da58c3...9781` | 5: [0,1,2,3,4] |
| S-3F | model_3f.h5 | 14197224 | `23058c47...933a` | 5: [0,1,2,3,5] |
| S-4A | model_4a.h5 | 14197224 | `1814b962...2d43` | 5: [0,1,2,3,4] |
| S-4B | model_4b.h5 | 14197224 | `8093feda...6082` | 5: [0,1,2,3,4] |
| S-4C | model_4c.h5 | 14197224 | `8f8c3f9e...d437` | 5: [0,1,2,3,4] |
| S-4D | model_4d.h5 | 14197224 | `1813f82c...b4af` | 5: [0,1,2,3,4] |
| S-4E | model_4e.h5 | 14197224 | `8ec0bf0c...2ca7` | 5: [0,1,2,3,4] |
| S-4F | model_4f.h5 | 14197736 | `5dba1422...42d3` | 6: [0,1,2,3,4,5] |

## DenseNet121 (24 files)

| Section | File | Size (bytes) | SHA-256 | Output Classes |
|---|---|---|---|---|
| S-1A | model_1a.h5 | 33852192 | `c1c85672...db6c` | 4: [1,2,3,4] |
| S-1B | model_1b.h5 | 33852704 | `e2abc14c...1061` | 5: [0,1,2,3,4] |
| S-1C | model_1c.h5 | 33852704 | `36e498e0...2842` | 5: [0,1,2,3,4] |
| S-1D | model_1d.h5 | 33852704 | `a0ee7e0f...7978` | 5: [0,1,2,3,4] |
| S-1E | model_1e.h5 | 33852704 | `c325447e...8c75` | 5: [0,1,2,3,4] |
| S-1F | model_1f.h5 | 33853216 | `9829dd6d...1eb0` | 6: [0,1,2,3,4,5] |
| S-2A | model_2a.h5 | 33852704 | `c9ec9124...5ce4` | 5: [0,1,2,3,4] |
| S-2B | model_2b.h5 | 33852192 | `12439980...0693` | 4: [0,1,2,4] |
| S-2C | model_2c.h5 | 33852704 | `0d41da53...16c6` | 5: [0,1,2,3,4] |
| S-2D | model_2d.h5 | 33852704 | `a67b7532...83e4` | 5: [0,1,2,3,4] |
| S-2E | model_2e.h5 | 33852704 | `77c57f81...195c` | 5: [0,1,2,3,4] |
| S-2F | model_2f.h5 | 33853216 | `3c22d30d...26bc` | 6: [0,1,2,3,4,5] |
| S-3A | model_3a.h5 | 33852704 | `ee238078...1ea0` | 5: [0,1,2,3,4] |
| S-3B | model_3b.h5 | 33852704 | `9ce2652b...4212` | 5: [0,1,2,3,4] |
| S-3C | model_3c.h5 | 33852704 | `8e12ed4d...0cec` | 5: [0,1,2,3,4] |
| S-3D | model_3d.h5 | 33852704 | `c34f0679...749e` | 5: [0,1,2,3,4] |
| S-3E | model_3e.h5 | 33852704 | `f764b48c...ece4` | 5: [0,1,2,3,4] |
| S-3F | model_3f.h5 | 33852704 | `29b57197...3290` | 5: [0,1,2,3,5] |
| S-4A | model_4a.h5 | 33852704 | `9422fa36...32d7` | 5: [0,1,2,3,4] |
| S-4B | model_4b.h5 | 33852704 | `a0fdf3fe...0d1e` | 5: [0,1,2,3,4] |
| S-4C | model_4c.h5 | 33852704 | `261eada5...05f` | 5: [0,1,2,3,4] |
| S-4D | model_4d.h5 | 33852704 | `1cd56107...d5a4` | 5: [0,1,2,3,4] |
| S-4E | model_4e.h5 | 33852704 | `2cf8a599...233b` | 5: [0,1,2,3,4] |
| S-4F | model_4f.h5 | 33853216 | `a49310e3...0954` | 6: [0,1,2,3,4,5] |

## InceptionV3 (24 files)

| Section | File | Size (bytes) | SHA-256 | Output Classes |
|---|---|---|---|---|
| S-1A | model_1a.h5 | 93608680 | `576791fd...108b` | 4: [1,2,3,4] |
| S-1B | model_1b.h5 | 93609192 | `c9839dd9...49bd` | 5: [0,1,2,3,4] |
| S-1C | model_1c.h5 | 93609192 | `5919a3f5...299f` | 5: [0,1,2,3,4] |
| S-1D | model_1d.h5 | 93609192 | `8b916c81...8ac7` | 5: [0,1,2,3,4] |
| S-1E | model_1e.h5 | 93609192 | `688bd632...aeb8` | 5: [0,1,2,3,4] |
| S-1F | model_1f.h5 | 93609704 | `285a4fdf...6645` | 6: [0,1,2,3,4,5] |
| S-2A | model_2a.h5 | 93609192 | `f4e215f3...11a4` | 5: [0,1,2,3,4] |
| S-2B | model_2b.h5 | 93608680 | `9bd423d0...ac63` | 4: [0,1,2,4] |
| S-2C | model_2c.h5 | 93609192 | `4c69d4ce...9b7f` | 5: [0,1,2,3,4] |
| S-2D | model_2d.h5 | 93609192 | `72c31bef...857c` | 5: [0,1,2,3,4] |
| S-2E | model_2e.h5 | 93609192 | `276c92a2...77e6` | 5: [0,1,2,3,4] |
| S-2F | model_2f.h5 | 93609704 | `11014659...d754` | 6: [0,1,2,3,4,5] |
| S-3A | model_3a.h5 | 93609192 | `72b4c421...ef2a` | 5: [0,1,2,3,4] |
| S-3B | model_3b.h5 | 93609192 | `7cbcdf42...6fc2` | 5: [0,1,2,3,4] |
| S-3C | model_3c.h5 | 93609192 | `30eb64bd...0335` | 5: [0,1,2,3,4] |
| S-3D | model_3d.h5 | 93609192 | `e6ba68dd...ad02` | 5: [0,1,2,3,4] |
| S-3E | model_3e.h5 | 93609192 | `6966f9ab...0acc` | 5: [0,1,2,3,4] |
| S-3F | model_3f.h5 | 93609192 | `4be7ed15...04e5` | 5: [0,1,2,3,5] |
| S-4A | model_4a.h5 | 93609192 | `61cf1bc5...e752` | 5: [0,1,2,3,4] |
| S-4B | model_4b.h5 | 93609192 | `3d72fd70...09dc` | 5: [0,1,2,3,4] |
| S-4C | model_4c.h5 | 93609192 | `ab454013...5479` | 5: [0,1,2,3,4] |
| S-4D | model_4d.h5 | 93609192 | `6de38754...1094` | 5: [0,1,2,3,4] |
| S-4E | model_4e.h5 | 93609192 | `5e0284d7...1a44` | 5: [0,1,2,3,4] |
| S-4F | model_4f.h5 | 93609704 | `bae983e4...fa08` | 6: [0,1,2,3,4,5] |

## Cross-reference SHA-256

SHA-256 pada `training_manifest.json` (Colab) dan `manifest.json` (runtime) **cocok** untuk semua 72 file. Satu file MobileNetV2/model_1a.h5 diverifikasi langsung via `certutil -hashfile` pada disk lokal dan hasilnya cocok (`2600ed71...23517d`).

## Preprocessing Sample SHA-256

Dua file PNG dari Preprocessed_Dataset yang diverifikasi pada 2026-07-17:

| SHA-256 | Keterangan |
|---|---|
| `674e82df1629eb1d00fa75f3bc845f2867789a5e152861af94bf87e06193c729` | Sample 1 — binary non-inverted confirmed |
| `048227d3d6d961b71bf52145429e1bd0180d09e3de29c5cf95fcb6536bb84c83` | Sample 2 — binary non-inverted confirmed |
