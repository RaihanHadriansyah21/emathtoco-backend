# Draft BAB 3 — Spesifikasi Dataset dan Model Deep Learning

> Dokumen ini berisi paragraf siap pakai untuk BAB 3 tugas akhir E-MATHTOCO.
> Semua angka bersumber dari artefak repository. Frasa guardrail diterapkan sesuai `08_ACADEMIC_CLAIM_GUARDRAILS.md`.

---

## 3.1.2 Spesifikasi Data Masukan

Dataset yang digunakan untuk melatih model berasal dari lembar jawab ujian mata kuliah Steganografi TT-46-G1. Setiap lembar jawab terdiri dari 24 section (S-1A hingga S-4F) yang masing-masing berisi jawaban tulisan tangan mahasiswa untuk satu soal. Berdasarkan log 72 training notebook, dataset mencakup 65 gambar per section, sehingga total target adalah 65 × 24 = 1.560 record section-image. Namun, audit terpisah pada folder preprocessed menemukan 1.536 file, setara dengan 64 × 24. Perbedaan 24 file ini belum direkonsiliasi.

Setiap gambar section di-preprocessing menjadi citra biner non-inverted (tinta hitam pada latar putih) menggunakan thresholding Otsu, kemudian disimpan dalam format PNG. Gambar biner ini kemudian direplikasi ke tiga channel RGB sebelum di-resize sesuai input shape arsitektur model.

## 3.1.4 Spesifikasi Model Deep Learning

Sistem menggunakan tiga arsitektur backbone CNN-BiLSTM sebagai berikut:

| Arsitektur | Input Shape | Preprocessing Keras | Total Parameter (approx.) |
|---|---|---|---|
| MobileNetV2 | 224 × 224 × 3 | `mobilenet_v2.preprocess_input` | ~3.5M |
| DenseNet121 | 224 × 224 × 3 | `densenet.preprocess_input` | ~8M |
| InceptionV3 | 299 × 299 × 3 | `inception_v3.preprocess_input` | ~23.8M |

Masing-masing arsitektur dilatih secara terpisah untuk setiap 24 section, menghasilkan total **3 × 24 = 72 file model** dalam format Keras H5. Jumlah output neuron bervariasi per section: 4 kelas untuk S-1A dan S-2B, 6 kelas untuk S-1F, S-2F, dan S-4F, serta 5 kelas untuk 19 section lainnya.

## 3.1.5 Batasan Sistem dan Batas Klaim

Model digunakan sebagai **rekomendasi awal** dalam mekanisme human-in-the-loop; keputusan skor akhir tetap berada pada dosen. Rata-rata validation accuracy MobileNetV2 adalah 55,45% dan macro F1 0,3156 pada agregasi 24 section fixed 80:20. Beberapa confusion matrix menunjukkan konsentrasi prediksi pada kelas mayoritas.

Klaim berikut belum mempunyai bukti repository yang memadai:
- Manifest anonim yang membuktikan identitas 65 subjek
- Split benar-benar dilakukan by-student (bukan by-image) pada dataset asli
- Kesamaan bit-per-bit preprocessing training dengan runtime (alignment visual sudah diperbaiki)

## 3.2.3 Arsitektur CNN-BiLSTM per Backbone

Setiap model terdiri dari backbone CNN pre-trained (ImageNet) yang diikuti oleh layer BiLSTM untuk menangkap fitur sekuensial dari tulisan tangan, kemudian dense layer dengan aktivasi softmax. Skor yang diprediksi oleh model dipetakan kembali ke nilai asli melalui `CLASS_SCORE_MAP` pada `services/class_mapping.py`.

Terdapat tiga anomali label encoding yang perlu dicatat:
1. **S-1A**: tidak memiliki skor 0 pada dataset training (hanya [1,2,3,4])
2. **S-2B**: skor 3 tidak ada pada dataset training (label [0,1,2,4])
3. **S-3F**: skor 4 tidak ada pada dataset training (label [0,1,2,3,5])

## 3.2.4 Desain Eksperimen

Eksperimen menggunakan fixed split 80:20 pada 65 gambar per section. Metrik evaluasi yang digunakan adalah validation accuracy, precision, recall, macro F1-score, dan confusion matrix. Seluruh 72 notebook menggunakan split yang sama tanpa cross-validation.

Kalimat transisi:

> Spesifikasi dan desain tersebut menjadi dasar realisasi E-MATHTOCO. BAB 4 menjelaskan implementasi setiap subsistem, hubungan antarkomponen, serta prosedur pengoperasian solusi yang dibangun.
