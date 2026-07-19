# Draft BAB 5 — Analisis Dataset dan Model

> Dokumen ini berisi paragraf siap pakai untuk BAB 5 tugas akhir E-MATHTOCO.
> Semua angka bersumber dari artefak repository. Guardrail akademik diterapkan.

---

## 5.2.7 Pengujian Model: Dataset Statistics dan Distribusi Label

### Statistik Dataset

Dataset training terdiri dari gambar lembar jawab yang telah di-preprocessing menjadi citra biner PNG. Berdasarkan log 72 training notebook, setiap section memiliki 65 gambar, sehingga total adalah 65 × 24 = 1.560 record section-image. Angka ini belum diverifikasi dengan dataset uji asli; audit terpisah menemukan 1.536 file pada folder preprocessed.

### Distribusi Kelas

Dari 24 section, terdapat variasi jumlah kelas output:

- **2 section dengan 4 kelas**: S-1A (skor [1,2,3,4], tanpa skor 0) dan S-2B (skor [0,1,2,4], tanpa skor 3)
- **19 section dengan 5 kelas**: mayoritas section dengan skor [0,1,2,3,4]
- **3 section dengan 6 kelas**: S-1F, S-2F, S-4F dengan skor [0,1,2,3,4,5]

Terdapat satu anomali tambahan: S-3F memiliki 5 kelas namun dengan skor [0,1,2,3,5] — skor 4 tidak ada pada dataset training.

Distribusi jumlah gambar per skor per section belum tersedia karena memerlukan listing file per folder label dari `Preprocessed_Dataset`. Berdasarkan pola confusion matrix yang menunjukkan konsentrasi prediksi pada kelas tertentu, diduga terdapat ketidakseimbangan kelas (*class imbalance*) pada beberapa section.

### Rekonsiliasi 1.560 vs 1.536

Terdapat perbedaan antara dua sumber penghitungan:

| Sumber | Jumlah | Perhitungan |
|---|---|---|
| Log 72 notebook | 1.560 | 65 gambar × 24 section |
| Audit folder preprocessed | 1.536 | — |

Gap sebesar 24 gambar setara dengan 1 subjek × 24 section, sehingga hipotesis yang paling mungkin adalah satu mahasiswa dikeluarkan antara sesi preprocessing dan sesi training, atau sebaliknya. Rekonsiliasi definitif memerlukan listing file aktual pada folder `Preprocessed_Dataset`.

### Keterbatasan Evidence

| Klaim | Evidence Level | Catatan |
|---|---|---|
| 65 mahasiswa per section | B (log notebook) | Bukan listing file aktual |
| Preprocessing binary non-inverted | B (sample verified) | Notebook preprocessing memiliki polarity mismatch |
| Split 80:20 fixed | B (notebook code) | Belum dibuktikan by-student |
| Tidak ada data leakage | B (log notebook) | Count 0 pada notebook, tapi split method belum diverifikasi |
| 72 model H5 ada dan utuh | A (file on disk + SHA-256) | Terverifikasi |

### Implikasi untuk Klaim Hasil

Pada agregasi 24 section fixed 80:20, MobileNetV2 memperoleh rata-rata validation accuracy 55,45% dan macro F1 0,3156. Beberapa confusion matrix menunjukkan konsentrasi prediksi pada kelas mayoritas. Oleh karena itu, model digunakan sebagai rekomendasi awal dalam mekanisme human-in-the-loop, bukan sebagai penentu nilai akhir tanpa validasi dosen.

Seluruh metrik yang dilaporkan adalah **validation accuracy dari split fixed 80:20**, bukan accuracy pada holdout test set terpisah. Oleh karena itu, istilah yang digunakan adalah **validation set**, bukan test set.

### Anomali Label dan Dampaknya

Untuk section S-1A, S-2B, dan S-3F, model tidak dapat memprediksi skor yang tidak ada dalam dataset training. Jika seorang mahasiswa mendapat skor 0 pada S-1A, skor 3 pada S-2B, atau skor 4 pada S-3F, model akan memberikan prediksi yang salah. Hal ini merupakan keterbatasan inheren dari dataset training yang perlu dicatat.
