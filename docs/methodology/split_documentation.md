# Dataset Split Methodology

Dokumen ini menjelaskan aturan validasi split dataset untuk model E-MATHTOCO.

## Prinsip utama

Untuk menghindari data leakage, split dataset wajib berbasis mahasiswa, bukan berbasis gambar/lembar.

- Salah: satu mahasiswa muncul di train dan test pada section berbeda.
- Benar: seluruh gambar milik satu mahasiswa hanya boleh masuk ke satu subset.

Dengan aturan ini, model diuji pada tulisan tangan mahasiswa yang tidak pernah muncul pada data training.

## Input wajib

Script validasi tidak boleh membuat data simulasi atau student ID mock.

Input yang wajib tersedia:

- manifest dataset asli;
- setiap record memiliki `student_id`, `image_path`, `section_code`, dan `score`;
- file gambar asli tersedia dan dapat diaudit terpisah.

Script aktif:

```powershell
cd D:\PTA\Emathtoco_Project\Emathoco_BackEnd
py -3.10 scripts\train_split_validation.py --dataset-manifest <path-ke-manifest-json>
```

Jika manifest tidak tersedia, script harus keluar nonzero. Kondisi ini benar dan tidak boleh diganti dengan metrik simulasi.

## Metrik akademik

Saat ini repository belum memiliki dataset uji asli dan ground truth dosen yang cukup untuk mengklaim:

- accuracy;
- precision/recall/F1;
- Cohen's Kappa;
- confusion matrix final;
- klaim 0% leakage verified.

Angka metrik baru boleh ditulis ke laporan setelah:

1. dataset manifest asli tersedia;
2. train/test split mahasiswa terbukti tidak overlap;
3. evaluasi dijalankan pada gambar asli;
4. hasil dapat direproduksi dari script dan manifest yang sama.

Sampai syarat tersebut terpenuhi, semua dokumen laporan harus menggunakan frasa “belum diverifikasi dengan dataset uji asli”.
