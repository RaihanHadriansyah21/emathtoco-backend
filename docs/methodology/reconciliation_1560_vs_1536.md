# Rekonsiliasi 1.560 vs 1.536

> Tanggal: 2026-07-18
> Sumber: `08_ACADEMIC_CLAIM_GUARDRAILS.md`, `07_EVIDENCE_REGISTER.md`, notebook logs
> Evidence level: **B/D** — analisis hipotesis berdasarkan metadata.

## Dua Angka yang Beredar

| Angka | Asal | Perhitungan |
|---|---|---|
| **1.560** | 72 training notebook | 65 gambar/section × 24 section |
| **1.536** | Audit preprocessing | Muncul di `PREPROCESSING_PROVENANCE_AUDIT_2026-07-16.md` |

Gap: **1.560 − 1.536 = 24 gambar**

## Hipotesis Sumber Gap

### Hipotesis 1: Satu subjek dikeluarkan (PALING MUNGKIN)

Jika satu mahasiswa dikeluarkan dari dataset, maka:
- 64 subjek × 24 section = **1.536** ← cocok
- Gap = 1 subjek × 24 section = 24 gambar

Kemungkinan alasan exclusion:
- Mahasiswa tidak mengerjakan semua 24 section
- Kualitas scan terlalu rendah
- Duplikasi subjek (dua scan dari satu orang)
- Informed consent / izin penggunaan data

### Hipotesis 2: Satu section penuh hilang

24 section × 1 section hilang dari beberapa subjek... Tidak cocok karena 24 gambar = tepat 1 section dari semua 65 subjek, tapi notebook melaporkan semua section memiliki 65 gambar.

**Ditolak**: log notebook konsisten 65 per section.

### Hipotesis 3: Perbedaan konteks penghitungan

Mungkin 1.536 mengacu ke jumlah file pada snapshot tertentu dari `Preprocessed_Dataset`, sementara 1.560 adalah angka yang dilaporkan notebook. Jika 24 file ditambahkan setelah snapshot...

**Tidak dapat dikonfirmasi** tanpa timestamp kedua sumber.

### Hipotesis 4: 1.536 adalah angka training-only

Jika split 80:20 dari 65 = 52 train + 13 val per section:
- 52 × 24 = 1.248 (bukan 1.536)
- 13 × 24 = 312

Atau 64 × 24 = 1.536 total, lalu 65 × 24 = 1.560 terbaru.

**Hipotesis 1 (64 vs 65 subjek) tetap paling mungkin.**

## Dampak terhadap Klaim Akademik

| Aspek | Dampak |
|---|---|
| Accuracy model | Minimal — 24 gambar dari ~1.560 (~1.5%) |
| Klaim "65 mahasiswa" | Harus diberi catatan: "65 tercatat di notebook, namun salah satu audit preprocessing menemukan 1.536 file, setara 64 subjek" |
| Klaim representatif | Tidak terpengaruh secara signifikan |
| Reproducibility | Memerlukan rekonsiliasi definitif |

## Langkah Rekonsiliasi

Untuk menyelesaikan gap ini secara definitif:

1. **Listing file aktual**: Jalankan di Colab:
   ```python
   import os
   base = "/content/drive/MyDrive/2026-Caps02/Dataset/Preprocessed_Dataset"
   students = set()
   total = 0
   for root, dirs, files in os.walk(base):
       for f in files:
           if f.endswith('.png'):
               total += 1
               nim = f.split('_')[0]
               students.add(nim)
   print(f"Total PNG: {total}, Unique students: {len(students)}")
   ```

2. **Identifikasi subjek yang hilang** (jika 64 vs 65):
   ```python
   from golden_inference import ...  # extract all NIM from golden
   # bandingkan NIM di notebook vs NIM di folder
   ```

3. **Dokumentasikan dalam BAB 5** sebagai keterbatasan yang jujur.

## Rekomendasi Penulisan

Gunakan frasa:

> Dataset terdiri dari lembar jawab **65 mahasiswa** berdasarkan log 72 training notebook. Audit terpisah pada folder preprocessed menemukan **1.536 file PNG**, yang setara dengan 64 × 24. Perbedaan 24 file belum direkonsiliasi dan menjadi keterbatasan verifikasi dataset.
