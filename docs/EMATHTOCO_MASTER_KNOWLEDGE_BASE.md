# EMATHTOCO MASTER KNOWLEDGE BASE
## Primary Source of Truth — CD4 / CD5 / CD6 / Thesis / Journal / Sidang

---

> **Dokumen ini dihasilkan dari analisis menyeluruh seluruh codebase proyek EMATHTOCO.**
> Dokumen ini merupakan referensi tunggal yang dapat digunakan untuk seluruh kegiatan akademik:
> Capstone Design 4, 5, 6 · Laporan Akhir · Tesis · Jurnal Ilmiah · Poster · Sidang/Viva

---

# BAGIAN 1 — RINGKASAN PROYEK & GAMBARAN UMUM

## 1.1 Identitas Proyek

| Atribut | Detail |
|---|---|
| **Nama Proyek** | EMATHTOCO |
| **Kepanjangan** | Enhanced Mathematics Assessment Through OCR and Artificial Intelligence |
| **Nama Alternatif** | Essay Mathematics Auto Correction |
| **Singkatan Resmi** | E-MATHTOCO |
| **Jenis Proyek** | Capstone Design Project |
| **Institusi** | Telkom University |
| **Program Studi** | S1 Teknik Telekomunikasi |
| **Periode Pengembangan** | 2025–2026 |
| **Kategori Penelitian** | AI for Education Technology (EdTech) |

## 1.2 Latar Belakang Masalah

Penilaian jawaban esai matematika tulisan tangan secara manual memiliki beberapa kelemahan fundamental:

1. **Memakan Waktu (Time-Consuming)**: Dosen harus memeriksa setiap lembar jawaban satu per satu secara manual, membutuhkan waktu berjam-jam bahkan berhari-hari untuk satu kelas.
2. **Subjektivitas Tinggi**: Penilaian bergantung pada kondisi dosen saat memeriksa, menghasilkan inkonsistensi penilaian antar-waktu dan antar-penilai.
3. **Rentan Human Error**: Kesalahan kalkulasi skor atau tertukarnya lembar jawaban adalah risiko nyata dalam sistem manual.
4. **Sulit Distatistikkan**: Data nilai tersebar di kertas fisik, menyulitkan analisis distribusi nilai, pemantauan progres kelas, atau perbandingan antar-kelas.
5. **Tidak Skalabel**: Saat jumlah mahasiswa bertambah, beban kerja dosen meningkat secara linear tanpa mekanisme otomatisasi.

## 1.3 Solusi yang Diusulkan

EMATHTOCO mengatasi masalah di atas dengan mengimplementasikan **pipeline penilaian otomatis berbasis Kecerdasan Buatan** yang bekerja melalui tahapan:

1. Mahasiswa mengunggah foto lembar jawaban per-bagian (section) melalui aplikasi web.
2. Sistem menyimpan gambar ke cloud storage (Supabase).
3. Dosen memicu proses AI (manual atau otomatis).
4. Model CNN (MobileNetV2 / DenseNet121 / InceptionV3) menganalisis setiap gambar jawaban.
5. Model mengklasifikasikan kualitas jawaban ke kelas tertentu dan memetakannya ke skor numerik.
6. Hasil prediksi disimpan ke database beserta nilai confidence.
7. Dosen meninjau, melakukan override jika diperlukan, dan memfinalisasi nilai.
8. Mahasiswa dapat melihat hasil penilaian secara real-time melalui dashboard.

## 1.4 Tujuan Sistem

- Mengotomatisasi penilaian lembar jawaban esai matematika tulisan tangan menggunakan CNN
- Mengurangi beban kerja dosen dalam proses koreksi jawaban
- Meningkatkan konsistensi dan objektivitas penilaian
- Menyediakan platform digital terpadu untuk manajemen tugas, pengumpulan, dan penilaian
- Memberikan transparansi hasil penilaian kepada mahasiswa secara real-time

## 1.5 Pemangku Kepentingan (Stakeholders)

| Stakeholder | Peran |
|---|---|
| **Mahasiswa** | Mengunggah lembar jawaban, memantau status submission, melihat skor AI |
| **Dosen** | Memicu AI, mereview hasil, melakukan override manual, menfinalisasi nilai |
| **Administrator** | Mengelola akun pengguna, konfigurasi sistem, monitoring audit log |
| **Tim Pengembang** | Pengembangan, pemeliharaan, dan peningkatan sistem |
| **Institusi (Telkom University)** | Penerima manfaat dari peningkatan efisiensi penilaian |

---

# BAGIAN 2 — ARSITEKTUR SISTEM

## 2.1 Gambaran Arsitektur Tingkat Tinggi

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                          │
│              Next.js 16 (TypeScript)                     │
│    - App Router · Tailwind CSS v4 · Lucide React        │
│    - Supabase JS Client (anon key)                      │
└──────────────┬──────────────┬───────────────────────────┘
               │ Supabase JS  │ FastAPI REST
               ▼              ▼
┌──────────────────┐  ┌───────────────────────────────┐
│  SUPABASE CLOUD  │  │      FastAPI Backend           │
│  - PostgreSQL    │  │  (uvicorn + Python 3.x)        │
│  - Auth (JWT)    │  │  - TensorFlow/Keras Models     │
│  - Storage       │  │  - Service Role Supabase Client│
│  - Row Level     │  │  - ngrok tunnel (dev mode)     │
│    Security      │  │  - Prediction Pipeline         │
└──────────────────┘  └───────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│                  AI MODEL LAYER                          │
│    Models/MobilenetV2/*.h5  (24 model files)            │
│    Models/DenseNet121/*.h5  (24 model files)            │
│    Models/InceptionV3/*.h5  (24 model files)            │
│    Total: 72 model .h5 files (24 sections × 3 arch)     │
└─────────────────────────────────────────────────────────┘
```

## 2.2 Arsitektur Hybrid Query

Sistem menggunakan dua jalur query secara bersamaan:

### Jalur 1: Frontend Direct (Supabase JS Client)
Digunakan untuk:
- Autentikasi (login/logout/session management)
- Mengambil data profil mahasiswa sendiri
- Mengambil data mata kuliah yang diikuti mahasiswa
- Menyimpan lembar jawaban ke storage

### Jalur 2: Backend Service-Role Proxy (FastAPI)
Digunakan untuk:
- Query yang terblokir Row Level Security (RLS)
- Daftar mahasiswa terdaftar per kelas (roster)
- Eksekusi pipeline prediksi AI (TensorFlow)
- Pengelolaan akun pengguna (Admin CRUD)
- Pengecekan email terdaftar di auth.users
- Penulisan audit log terpusat

## 2.3 Struktur Repository

```
Emathtoco_Project/
│
├── Emathtoco_FrontEnd/
│   └── Emathtoco_Web/              ← Next.js 16 Frontend App
│       ├── app/
│       │   ├── page.tsx            ← Dashboard Mahasiswa
│       │   ├── layout.tsx          ← Root Layout + ThemeProvider
│       │   ├── globals.css         ← Global CSS + Scrollbar styles
│       │   ├── components/
│       │   │   ├── Navbar.tsx      ← Shared navigation header
│       │   │   ├── AdminSidebar.tsx← Collapsible admin sidebar
│       │   │   ├── AuthGate.tsx    ← Role-based auth wrapper
│       │   │   ├── BatchAIModal.tsx← Batch AI processing modal
│       │   │   ├── ConfirmModal.tsx← Reusable confirmation dialog
│       │   │   ├── ExportCSVModal.tsx← Export data functionality
│       │   │   ├── FullscreenLoader.tsx← Loading overlay
│       │   │   ├── ThemeProvider.tsx← Dark/light mode provider
│       │   │   └── Toast.tsx       ← Notification system
│       │   ├── login/
│       │   │   ├── page.tsx        ← Role selection gateway
│       │   │   ├── mahasiswa/page.tsx ← Student login portal
│       │   │   └── dosen/page.tsx  ← Lecturer login portal
│       │   ├── register/           ← Student registration
│       │   ├── complete-profile/   ← First-time profile setup
│       │   ├── forgot-password/    ← Password recovery request
│       │   ├── reset-password/     ← Password reset form
│       │   ├── profile/            ← User profile management
│       │   ├── settings/           ← User settings
│       │   ├── matkul/[id]/        ← Student course workspace
│       │   ├── dosen/
│       │   │   ├── page.tsx        ← Lecturer dashboard
│       │   │   ├── course/[id]/    ← Assessment portal per course
│       │   │   │   ├── page.tsx
│       │   │   │   └── students/page.tsx ← Student roster view
│       │   │   └── review/[id]/    ← Manual review workspace
│       │   └── admin/
│       │       ├── page.tsx        ← Admin dashboard
│       │       ├── layout.tsx      ← Admin layout with sidebar
│       │       ├── users/          ← User management
│       │       ├── courses/        ← Course management
│       │       ├── enrollment/     ← Enrollment management
│       │       ├── lecturers/      ← Lecturer assignment
│       │       ├── audit/          ← Audit log viewer
│       │       ├── audit-debug/    ← Debug audit tools
│       │       ├── monitoring/     ← System monitoring
│       │       ├── system-settings/← Global settings
│       │       ├── ai-models/      ← AI model info
│       │       ├── diagnostics/    ← System diagnostics
│       │       └── reset/          ← Data reset utilities
│       ├── lib/
│       │   ├── api-client.ts       ← Centralized FastAPI HTTP client
│       │   ├── config.ts           ← API URL config
│       │   ├── supabase.ts         ← Supabase client instance
│       │   ├── utils.ts            ← normalizeRole helper
│       │   ├── batch-ai-store.ts   ← Zustand/store for batch AI
│       │   ├── export/             ← CSV export utilities
│       │   ├── services/           ← Service layer abstractions
│       │   ├── supabase/           ← Supabase helpers
│       │   └── types/              ← TypeScript type definitions
│       ├── middleware.ts           ← Route protection middleware
│       └── next.config.ts
│
├── Emathoco_BackEnd/               ← FastAPI Backend (Python)
│   ├── main.py                    ← All API endpoints (895 lines)
│   ├── services/
│   │   ├── model_registry.py      ← Model lazy-load cache
│   │   ├── model_loader.py        ← TF model loading with patch
│   │   ├── prediction_service.py  ← Core AI pipeline (531 lines)
│   │   ├── preprocess.py          ← Image preprocessing
│   │   ├── image_service.py       ← Supabase Storage download
│   │   ├── class_mapping.py       ← Class-to-score mapping
│   │   └── settings_service.py    ← System settings with cache
│   ├── repositories/
│   │   ├── submission_repository.py
│   │   ├── prediction_repository.py
│   │   └── lembar_jawaban_repository.py
│   ├── utils/
│   │   ├── supabase_client.py
│   │   └── audit_helper.py
│   ├── Models/
│   │   ├── MobilenetV2/           ← 24 × model_Xa.h5 files
│   │   ├── DenseNet121/           ← 24 × model_Xa.h5 files
│   │   └── InceptionV3/           ← 24 × model_Xa.h5 files
│   ├── requirements-api.txt
│   ├── requirements-worker.txt
│   └── requirements-dev.txt
│
└── Emathtoco_AgentDocs/           ← Developer documentation
    ├── PROJECT_CONTEXT.md
    ├── DATABASE_SCHEMA.md
    ├── API_DOCUMENTATION.md
    ├── FEATURE_REGISTRY.md
    ├── UI_GUIDELINES.md
    ├── CHANGELOG.md
    └── EMATHTOCO_MASTER_KNOWLEDGE_BASE.md (this file)
```

---

# BAGIAN 3 — TEKNOLOGI STACK (TECH STACK)

## 3.1 Frontend

| Kategori | Teknologi | Versi |
|---|---|---|
| **Framework** | Next.js | 16.2.6 |
| **Bahasa** | TypeScript | ^5 |
| **Runtime UI** | React | 19.2.4 |
| **Styling** | Tailwind CSS | ^4 |
| **Icons** | Lucide React | ^1.16.0 |
| **Auth/DB Client** | @supabase/supabase-js | ^2.106.2 |
| **Theme** | next-themes | ^0.4.6 |
| **Export** | ExcelJS | ^4.4.0 |
| **Image Crop** | react-easy-crop | ^5.5.7 |
| **Package Manager** | npm / Node.js | - |

## 3.2 Backend

| Kategori | Teknologi | Versi |
|---|---|---|
| **Framework** | FastAPI | 0.136.3 |
| **ASGI Server** | Uvicorn | 0.48.0 |
| **Bahasa** | Python | 3.x |
| **Deep Learning** | TensorFlow | 2.21.0 |
| **DL High-level API** | Keras | 3.12.2 |
| **Image Processing** | OpenCV (headless) | 4.13.0.92 |
| **Array Computing** | NumPy | 2.2.6 |
| **DB Client (Admin)** | supabase-py | 2.30.1 |
| **HTTP Server** | h11 + httpx | 0.16.0 / 0.28.1 |
| **PDF Generation** | fpdf2 | 2.8.7 |
| **Env Management** | python-dotenv | 1.2.2 |
| **Validation** | Pydantic | 2.13.4 |

## 3.3 Database & Services

| Komponen | Teknologi |
|---|---|
| **DBMS** | PostgreSQL (hosted on Supabase) |
| **Authentication** | Supabase Auth (Email & Password) |
| **Storage** | Supabase Storage Buckets |
| **Realtime** | Supabase Realtime (via WebSocket) |
| **Security** | Row Level Security (RLS) |
| **Tunneling (Dev)** | ngrok (reverse proxy) |
| **Deployment (Frontend)** | Vercel |

## 3.4 Environment Variables

### Backend (.env)

| Variable | Deskripsi | Nilai Contoh |
|---|---|---|
| `SUPABASE_URL` | Supabase project URL | `https://hkxxhactpwiqdzecrbxw.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (admin bypass RLS) | `sb_secret_...` |
| `ALLOWED_ORIGINS` | CORS whitelist URLs | `http://localhost:3000,...,https://emathtoco.vercel.app` |

### Frontend (.env.local)

| Variable | Deskripsi |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (public) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Anon/public key Supabase |
| `NEXT_PUBLIC_API_URL` | URL FastAPI backend (ngrok tunnel saat dev) |

---

# BAGIAN 4 — ANALISIS FRONTEND

## 4.1 Arsitektur Frontend

Aplikasi menggunakan **Next.js App Router** dengan pola hybrid rendering:
- Server Components untuk layout dan static structure
- Client Components (`'use client'`) untuk semua halaman interaktif dengan state

### State Management
- **React useState/useEffect**: Untuk state lokal per-halaman
- **Local Storage**: Untuk persistensi preferensi sidebar admin (collapsed/expanded state)
- **Supabase Auth Session**: Token JWT disimpan di cookie `sb-access-token`
- **lib/batch-ai-store.ts**: Store minimal untuk status batch AI processing

### Routing & Middleware

Middleware (`middleware.ts`) bertugas sebagai **route guard**:
- Membaca cookie `sb-access-token` dari setiap request
- Melakukan client-side JWT expiry validation
- Redirect ke `/login` jika token tidak ada atau kedaluwarsa
- Whitelist routes: `/login/*`, `/forgot-password`, `/reset-password`
- Protected routes: `/`, `/profile`, `/settings`, `/matkul/*`, `/dosen/*`, `/admin/*`

## 4.2 Inventaris Halaman Frontend

### Halaman Publik (Tidak Memerlukan Login)

#### 1. Login Role Selection — `/login`
- **Tujuan**: Pintu gerbang pemilihan peran login dengan tampilan premium
- **UI**: Dua glassmorphism card — "Mahasiswa" (cyan) dan "Dosen/Admin" (purple/indigo)
- **Navigasi**: Klik card → redirect ke `/login/mahasiswa` atau `/login/dosen`

#### 2. Student Login — `/login/mahasiswa`
- **Tujuan**: Portal login khusus mahasiswa
- **Fitur**:
  - Pre-auth email check (via `/auth/check-email` backend)
  - Supabase Auth email+password login
  - Post-auth role validation (hanya izinkan role `mahasiswa`)
  - Link ke halaman registrasi `/register`
  - Link lupa password `/forgot-password`
  - Audit log pada login sukses
- **Error handling**: Email tidak terdaftar, password salah, role tidak sesuai

#### 3. Lecturer Login — `/login/dosen`
- **Tujuan**: Portal login khusus dosen dan admin
- **Fitur**:
  - Pre-auth email check
  - Supabase Auth email+password login
  - Post-auth role validation: `dosen` → `/dosen`, `admin` → `/admin`
  - Tidak ada link registrasi (akun dosen dibuat oleh admin)
  - Audit log pada login sukses

#### 4. Registrasi Mahasiswa — `/register`
- **Tujuan**: Pendaftaran akun mahasiswa baru
- **Fitur**: Form registrasi email/password, redirect ke complete-profile setelah sukses

#### 5. Forgot Password — `/forgot-password`
- **Tujuan**: Permintaan reset password via email
- **Fitur**: Input email → trigger Supabase password reset email

#### 6. Reset Password — `/reset-password`
- **Tujuan**: Formulir penetapan password baru
- **Fitur**: Parse Supabase hash dari URL → form input password baru

### Halaman Mahasiswa (Protected)

#### 7. Student Dashboard — `/` (root)
- **Tujuan**: Dashboard utama mahasiswa
- **Fitur**:
  - Auth check dan role-based routing (dosen → `/dosen`, admin → `/admin`, no-profile → `/complete-profile`)
  - Menampilkan daftar mata kuliah yang diikuti
  - Badge warning `⚠ ACTION REQUIRED` jika ada bagian yang perlu diupload ulang
  - Animated placeholder skeleton saat loading

#### 8. Course Workspace — `/matkul/[id]`
- **Tujuan**: Workspace pengumpulan jawaban per mata kuliah
- **Fitur**:
  - Grid 24 section jawaban (S-1A hingga S-4F, 4 soal × 6 bagian)
  - Upload foto jawaban per section (kamera langsung atau pilih file)
  - Status per section: belum diisi, sudah diisi, perlu upload ulang
  - Preview foto sebelum submit
  - Cropping foto (`react-easy-crop`)
  - Validasi file (format, ukuran)
  - Tombol "Kumpulkan" yang memicu AI pipeline via backend

#### 9. Complete Profile — `/complete-profile`
- **Tujuan**: Pengisian profil pertama kali setelah registrasi
- **Fitur**: Input nama lengkap, NIM, kelas

#### 10. Profile — `/profile`
- **Tujuan**: Manajemen profil pengguna
- **Fitur**: Update nama, upload foto profil, lihat NIM/NIP

#### 11. Settings — `/settings`
- **Tujuan**: Pengaturan akun pengguna

### Halaman Dosen (Protected)

#### 12. Lecturer Dashboard — `/dosen`
- **Tujuan**: Dashboard utama dosen
- **Fitur**:
  - Verifikasi role dosen saat load
  - Menampilkan daftar mata kuliah yang diajar
  - Statistik per course: Total, Wait AI, Review, Final
  - Animated hover transitions pada card mata kuliah

#### 13. Course Assessment Portal — `/dosen/course/[id]`
- **Tujuan**: Portal penilaian mahasiswa untuk satu mata kuliah
- **Fitur**:
  - Statistik summary: mahasiswa terdaftar, belum kumpul, menunggu AI, diproses AI, selesai AI, finalized
  - Tabel mahasiswa dengan status submission real-time
  - Filter berdasarkan status dan kelas
  - Search mahasiswa by nama/NIM
  - Trigger AI individual (tombol "Jalankan AI")
  - Trigger AI batch (via `BatchAIModal`)
  - Navigasi ke detail review masing-masing mahasiswa
  - Export data ke CSV (via `ExportCSVModal`)
  - Sticky table header, max-height scrollable container
  - Mobile card view responsif

#### 14. Student Roster View — `/dosen/course/[id]/students`
- **Tujuan**: Roster mahasiswa terdaftar dalam satu mata kuliah
- **Fitur**:
  - Data diambil via secure backend API (bypass RLS)
  - Statistik: Total, Submitted, Not Submitted, Graded by AI, Pending
  - Search/filter mahasiswa
  - Modal detail per-mahasiswa: tampilkan skor per section dengan confidence
  - Tombol finalisasi langsung dari roster

#### 15. Manual Review Workspace — `/dosen/review/[id]`
- **Tujuan**: Workspace review dan override nilai AI per submission
- **Fitur**:
  - Tampil foto jawaban per section
  - Tampil skor AI, confidence
  - Override nilai manual per section
  - Request reupload per section (dengan pesan alasan)
  - Input feedback/komentar per section
  - Tombol "Finalisasi Nilai" (mengunci semua skor)
  - Audit log pada setiap aksi review

### Halaman Admin (Protected)

#### 16. Admin Dashboard — `/admin`
- **Tujuan**: Dashboard ringkasan sistem untuk admin
- **Fitur**:
  - Statistik: Total Pengguna, Total Mata Kuliah, Total Pengumpulan, Menunggu AI, Direview, Finalized
  - Quick Actions card: Kelola Pengguna, Kelola Mata Kuliah, Monitoring, Audit Log
  - Tabel 8 pengumpulan terbaru dengan status badge
  - Wrapped dalam AdminLayout dengan collapsible sidebar

#### 17. User Management — `/admin/users`
- **Tujuan**: CRUD akun pengguna
- **Fitur**: Lihat semua user, hapus user (cascade: enrollment → profil → auth)

#### 18. Course Management — `/admin/courses`
- **Tujuan**: CRUD mata kuliah

#### 19. Enrollment Management — `/admin/enrollment`
- **Tujuan**: Daftarkan mahasiswa ke mata kuliah

#### 20. Lecturer Assignment — `/admin/lecturers`
- **Tujuan**: Tugaskan dosen ke mata kuliah

#### 21. Audit Log Viewer — `/admin/audit`
- **Tujuan**: Tampilkan log audit seluruh aktivitas sistem
- **Fitur**: Filter by action, user, date range; enterprise schema support

#### 22. System Monitoring — `/admin/monitoring`
- **Tujuan**: Monitoring pipeline AI dan statistik sistem

#### 23. System Settings — `/admin/system-settings`
- **Tujuan**: Konfigurasi global sistem
- **Fitur**: Toggle `auto_run_ai`, pilih `active_model` (MobileNetV2/DenseNet121/InceptionV3)

#### 24. AI Models Info — `/admin/ai-models`
- **Tujuan**: Tampilkan info model AI yang tersedia dan status cache

#### 25. Diagnostics — `/admin/diagnostics`
- **Tujuan**: Tools diagnostik sistem

#### 26. Audit Debug — `/admin/audit-debug`
- **Tujuan**: Debug tools untuk schema audit log

## 4.3 Inventaris Komponen

### Navbar.tsx
- **Ukuran**: 17,102 bytes
- **Tanggung Jawab**: Navigation header yang adaptif untuk semua role
- **Fitur**:
  - Mode dosen: sidebar icon (mengecil/membesar bersama `AdminSidebar`)
  - Mode mahasiswa: logo kiri, menu navigasi kanan
  - Toggle dark/light mode
  - Avatar pengguna dengan dropdown
  - Logo branding E-MATHTOCO
  - Persistent localStorage sidebar state untuk admin

### AdminSidebar.tsx
- **Ukuran**: 7,264 bytes
- **Tanggung Jawab**: Collapsible sidebar navigasi admin
- **Fitur**:
  - Dua mode: collapsed (80px) dan expanded (270px)
  - Kategori menu: Menu Utama, Sistem & AI, Utilitas
  - CSS-only tooltips saat collapsed
  - Cyan glow indicator untuk item aktif
  - localStorage persistence
  - Smooth CSS transition (tidak ada flicker)

### AuthGate.tsx
- **Ukuran**: 8,872 bytes
- **Tanggung Jawab**: Auth wrapper yang memverifikasi sesi sebelum render konten
- **Fitur**:
  - Cek session Supabase
  - Whitelist `/login/*`, `/forgot-password`, `/reset-password`
  - Redirect ke login jika tidak terautentikasi

### BatchAIModal.tsx
- **Ukuran**: 24,613 bytes
- **Tanggung Jawab**: Modal untuk memicu prediksi AI pada banyak submission sekaligus
- **Fitur**:
  - Pilih model AI (MobileNetV2/DenseNet121/InceptionV3)
  - Progress bar per submission
  - Error handling per submission
  - Summary hasil di akhir batch

### ExportCSVModal.tsx
- **Ukuran**: 18,580 bytes
- **Tanggung Jawab**: Export data penilaian ke file Excel/CSV
- **Fitur**:
  - Filter data sebelum export
  - Format Excel menggunakan ExcelJS
  - Nama file otomatis berdasarkan tanggal

### ConfirmModal.tsx
- **Tanggung Jawab**: Dialog konfirmasi yang dapat digunakan ulang
- **Props**: `isOpen`, `onConfirm`, `onCancel`, `message`, `type`

### FullscreenLoader.tsx
- **Tanggung Jawab**: Loading overlay fullscreen dengan animasi

### Toast.tsx
- **Tanggung Jawab**: Notifikasi toast (success/error/warning)
- **Durasi**: Auto-dismiss setelah beberapa detik

### ThemeProvider.tsx
- **Tanggung Jawab**: Wrapper next-themes untuk dark/light mode

## 4.4 Authentication Flow

```
1. User buka URL protected
     ↓
2. middleware.ts: Cek cookie 'sb-access-token'
     ↓
3a. Token tidak ada → Redirect ke /login
3b. Token ada tapi expired → Delete cookie, redirect ke /login
3c. Token valid → NextResponse.next()
     ↓
4. Halaman render → AuthGate check session server-side
     ↓
5. supabase.auth.getUser() → Verifikasi ke Supabase
     ↓
6. Ambil profil_pengguna untuk mendapatkan role
     ↓
7. normalizeRole(role) → Lowercase normalization
     ↓
8. Routing berdasarkan role:
   - 'mahasiswa' → tetap di /
   - 'dosen' → /dosen
   - 'admin' → /admin
   - no-profile → /complete-profile
```

## 4.5 Upload Flow (Student)

```
1. Mahasiswa buka /matkul/[id]
2. Pilih section jawaban (S-1A s.d. S-4F)
3. Ambil foto (kamera/file browser)
4. Preview foto → crop jika perlu (react-easy-crop)
5. Validasi: format gambar, ukuran file
6. Upload ke Supabase Storage bucket 'lembar-jawaban'
   Path: {course_id}/{submission_id}/S-{section_code}.png
7. Simpan/update record lembar_jawaban di database
8. Update UI: section berubah status 'uploaded'
9. Semua 24 section → tombol "Kumpulkan" aktif
10. Klik "Kumpulkan" → POST /submission/{id}/submit ke backend
11. Backend: cek auto_run_ai setting
    - ON: spawn background task prediksi AI
    - OFF: tandai submitted saja, tunggu trigger manual dosen
```

---

# BAGIAN 5 — ANALISIS BACKEND

## 5.1 Arsitektur Backend

Framework: **FastAPI** dengan server **Uvicorn**

```python
app = FastAPI(title="EMATHTOCO AI Backend Versi 1.0.0")
```

### Middleware
- **CORS**: Whitelist origins dari env + regex untuk Vercel/localhost subdomains
- **Allow Credentials**: True (untuk cookie-based auth flows)

### Pola Arsitektur Backend
```
main.py (Routes)
    ↓
repositories/ (Database operations)
    ↓
services/ (Business logic + AI pipeline)
    ↓
utils/ (Supabase client + audit helpers)
```

## 5.2 Dokumentasi API Lengkap

### Group 1: Authentication

#### `GET /auth/check-email`
- **Tujuan**: Cek apakah email terdaftar di Supabase auth.users
- **Query Params**: `email` (string, required)
- **Response**:
  ```json
  { "exists": true }
  ```
- **Implementasi**: Iterasi semua users via admin.list_users (pagination 100/page)
- **Error**: HTTP 400 jika email kosong; fallback `exists: true` jika Supabase error

---

### Group 2: AI Prediction Pipeline

#### `POST /predict/{submission_id}`
- **Tujuan**: Jalankan pipeline prediksi AI untuk submission tertentu (manual/explicit trigger)
- **Query Params**: `model` (optional: `MobileNetV2`, `DenseNet121`, `InceptionV3`)
- **Logika Model Priority**:
  1. Parameter explisit dari request
  2. `active_model` dari system_settings database
  3. Fallback: `MobileNetV2`
- **Guards**:
  - Status `finalized` → HTTP 400
  - Status `processing` → HTTP 409
  - Submission tidak ada → HTTP 404
- **Response**:
  ```json
  {
    "success": true,
    "submission_id": "uuid",
    "total_sheets": 24,
    "processed": 24,
    "failed": 0,
    "nilai_akhir": 85,
    "ai_status": "completed",
    "model_ai": "MobileNetV2",
    "results": [...]
  }
  ```

---

#### `POST /submission/{submission_id}/submit`
- **Tujuan**: Dipanggil saat mahasiswa klik "Kumpulkan Tugas"
- **Logika**:
  - Baca setting `auto_run_ai` dari database
  - Jika OFF: return sukses tanpa AI
  - Jika ON: spawn background task prediksi AI (`BackgroundTasks`)
- **Response (auto_run ON)**:
  ```json
  {
    "success": true,
    "message": "Submission submitted. AI triggered in background using model MobileNetV2.",
    "auto_run": true
  }
  ```

---

#### `GET /prediction/{submission_id}`
- **Tujuan**: Ambil hasil prediksi final untuk submission (format mahasiswa)
- **Response**:
  ```json
  {
    "submission_id": "uuid",
    "nilai_akhir": 85,
    "ai_status": "completed",
    "model_ai": "MobileNetV2",
    "sections": [
      {"section_code": "S-1A", "predicted_class": 3, "predicted_score": 4, "confidence": 0.97}
    ]
  }
  ```
- **Deduplication**: Jika ada duplicate section, prioritaskan non-debug score (bukan skor 85 debug)

---

#### `GET /submission/{submission_id}/results`
- **Tujuan**: Ambil hasil prediksi (format dosen, lebih ringkas)
- **Response**: Sama dengan di atas tapi tanpa `predicted_class`

---

#### `POST /submission/{submission_id}/reviewed`
- **Tujuan**: Update status submission menjadi `reviewed`
- **Response**: `{ "success": true, "data": [...] }`

---

#### `POST /submission/{submission_id}/finalize`
- **Tujuan**: Update status submission menjadi `finalized` (mengunci nilai)
- **Response**: `{ "success": true, "data": [...] }`

---

### Group 3: Lecturer Endpoints

#### `GET /lecturer/class-summary`
- **Query Params**: `lecturer_id` (UUID, required)
- **Tujuan**: Statistik kelas dan jumlah mahasiswa yang diajar dosen
- **Response**:
  ```json
  {
    "total_classes": 2,
    "total_students": 45,
    "classes": [
      { "kelas": "TT-46-01", "students": 23 },
      { "kelas": "TT-46-02", "students": 22 }
    ]
  }
  ```

---

#### `GET /lecturer/course/{course_id}/stats`
- **Tujuan**: Jumlah mahasiswa terdaftar dalam satu mata kuliah

---

#### `GET /lecturer/course/{course_id}/students`
- **Tujuan**: Roster lengkap mahasiswa + status submission (bypass RLS)
- **Response**: Array mahasiswa dengan profil + data submission + jumlah lembar jawaban

---

### Group 4: Admin Endpoints

#### `DELETE /admin/user/{user_id}`
- **Tujuan**: Hapus akun pengguna secara cascade
- **Urutan penghapusan**:
  1. `mahasiswa_mata_kuliah` (enrollment)
  2. `dosen_mata_kuliah` (assignment)
  3. `profil_pengguna` (profile)
  4. `auth.users` (Supabase auth)

---

#### `POST /admin/predictions/count`
- **Tujuan**: Hitung jumlah prediksi untuk sekumpulan lembar_jawaban_ids
- **Body**: `{ "lembar_jawaban_ids": ["uuid1", "uuid2"] }`

---

#### `POST /admin/predictions/delete`
- **Tujuan**: Hapus prediksi untuk sekumpulan lembar_jawaban_ids (admin reset)

---

### Group 5: System Settings

#### `GET /settings`
- **Response**: `{ "auto_run_ai": "true", "active_model": "MobileNetV2", "verbose_logging": "false" }`

#### `POST /settings`
- **Body**:
  ```json
  {
    "settings": { "auto_run_ai": "true", "active_model": "MobileNetV2" },
    "changed_by": "Admin Name",
    "role": "admin",
    "user_id": "uuid"
  }
  ```
- **Side effects**: Audit log `SYSTEM_SETTING_CHANGED` atau `ACTIVE_MODEL_CHANGED`

---

### Group 6: AI Model Diagnostics

#### `GET /ai-models`
- **Response**: List model dengan info loaded status, input_shape, total model files

#### `GET /model-info` / `GET /cache-status`
- **Tujuan**: Monitoring cache model yang sudah di-load

#### `GET /audit-models`
- **Tujuan**: Loop semua model, load test S-1A, return input/output shape

---

### Group 7: Audit Log

#### `POST /audit/log`
- **Tujuan**: Write custom audit log dari frontend
- **Body**:
  ```json
  {
    "action": "STUDENT_LOGIN",
    "target": "profil_pengguna",
    "detail": {"device": "chrome"},
    "user_id": "uuid",
    "user_name": "Full Name",
    "role": "mahasiswa"
  }
  ```
- **Standardisasi**: Model name dalam payload dinormalisasi sebelum disimpan

#### `GET /audit/schema-check`
- **Tujuan**: Deteksi versi schema `audit_log` (legacy vs enterprise)

#### `GET /audit/test`
- **Tujuan**: Test endpoint untuk verifikasi audit logging berfungsi

---

### Group 8: Health Check

#### `GET /health`
- **Response**: `{ "status": "ok", "service": "EMATHTOCO AI Backend" }`

---

# BAGIAN 6 — ANALISIS DATABASE

## 6.1 Arsitektur Database

Database menggunakan **PostgreSQL** yang di-hosting di **Supabase** dengan Row Level Security (RLS) aktif.

## 6.2 Skema Tabel

### Tabel: `profil_pengguna`

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, FK auth.users CASCADE | ID user dari Supabase Auth |
| `nama_lengkap` | text | NOT NULL | Nama lengkap pengguna |
| `nim_nip` | text | NOT NULL | NIM (mahasiswa) atau NIP (dosen) |
| `kelas` | text | - | Kelas mahasiswa (e.g., "TT-46-01") |
| `role` | text | - | Role: `mahasiswa`, `dosen`, `admin` |
| `foto_profil_url` | text | nullable | URL avatar di bucket `profile-images` |
| `created_at` | timestamptz | - | Timestamp pembuatan akun |
| `updated_at` | timestamptz | - | Timestamp update terakhir |

---

### Tabel: `mata_kuliah`

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | ID mata kuliah |
| `nama_matkul` | text | NOT NULL | Nama mata kuliah |
| `kode_matkul` | text | UNIQUE | Kode unik mata kuliah |
| `nama_dosen` | text | - | Nama display dosen pengampu |
| `icon_name` | text | - | Slug icon: `security`, `compress`, `ai`, `network`, `math` |
| `created_at` | timestamptz | - | Timestamp pembuatan |

---

### Tabel: `mahasiswa_mata_kuliah` (Junction)

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | ID relasi |
| `mahasiswa_id` | UUID | FK profil_pengguna.id | ID mahasiswa |
| `mata_kuliah_id` | UUID | FK mata_kuliah.id | ID mata kuliah |
| `created_at` | timestamptz | - | Timestamp pendaftaran |

---

### Tabel: `dosen_mata_kuliah` (Junction)

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | ID relasi |
| `dosen_id` | UUID | FK profil_pengguna.id | ID dosen |
| `mata_kuliah_id` | UUID | FK mata_kuliah.id | ID mata kuliah |
| `created_at` | timestamptz | - | Timestamp penugasan |

---

### Tabel: `pengumpulan_tugas`

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | ID submission |
| `mahasiswa_id` | UUID | FK profil_pengguna.id | ID mahasiswa |
| `mata_kuliah_id` | UUID | FK mata_kuliah.id | ID mata kuliah |
| `status_submit` | text | ENUM | `submitted`, `processing_ai`, `reviewed`, `finalized` |
| `waktu_submit` | timestamptz | - | Waktu pengumpulan |
| `nilai_akhir` | integer | nullable | Total skor akhir yang dikompilasi AI |
| `model_ai` | text | - | Model AI yang digunakan prediksi |
| `ai_status` | text | ENUM | `pending`, `processing`, `completed`, `failed`, `finalized` |
| `created_at` | timestamptz | - | Timestamp pembuatan |
| `updated_at` | timestamptz | - | Timestamp update terakhir |

---

### Tabel: `lembar_jawaban`

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | ID lembar jawaban |
| `pengumpulan_tugas_id` | UUID | FK pengumpulan_tugas.id CASCADE DELETE | ID submission induk |
| `section_code` | text | - | Kode bagian: `S-1A` hingga `S-4F` |
| `image_url` | text | - | Path file di bucket `lembar-jawaban` |
| `status` | text | ENUM | `success`, `reupload_required`, `finalized` |
| `rejection_reason` | text | nullable | Alasan reupload dari dosen |
| `nilai_dosen` | integer | nullable | Override skor manual oleh dosen |
| `nilai_final` | integer | nullable | Skor final yang dikunci |
| `feedback` | text | nullable | Komentar/feedback dosen per section |
| `was_reuploaded` | boolean | default false | Apakah pernah diupload ulang |
| `reupload_count` | integer | default 0 | Berapa kali diupload ulang |
| `last_reupload_at` | timestamptz | nullable | Waktu upload ulang terakhir |
| `created_at` | timestamptz | - | Timestamp pembuatan |
| `updated_at` | timestamptz | - | Timestamp update |

---

### Tabel: `hasil_prediksi`

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `id` | UUID/integer | PRIMARY KEY AUTO-INCREMENT | ID hasil prediksi |
| `pengumpulan_tugas_id` | UUID | FK pengumpulan_tugas.id CASCADE | ID submission |
| `lembar_jawaban_id` | UUID | FK lembar_jawaban.id CASCADE | ID lembar jawaban |
| `section_code` | text | - | Kode section (S-1A dst) |
| `model_ai` | text | - | Nama arsitektur model (`MobileNetV2`, dll) |
| `predicted_class` | integer | - | Index kelas hasil argmax |
| `predicted_score` | integer | - | Skor numerik hasil mapping CLASS_SCORE_MAP |
| `confidence` | float | - | Probabilitas prediksi (0.0–1.0) |
| `status` | text | - | `success` atau `error` |
| `error_message` | text | nullable | Detail error jika gagal |
| `created_at` | timestamptz | - | Timestamp prediksi |

**Unique Constraint**: `(pengumpulan_tugas_id, section_code)` — satu record per section per submission

---

### Tabel: `audit_log`

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | ID log entry |
| `action` | text | NOT NULL | Kode aksi (lihat daftar action di bawah) |
| `target` | text | NOT NULL | Nama tabel/modul yang ditarget |
| `detail` | jsonb | nullable | Payload detail spesifik per aksi |
| `user_id` | UUID | nullable FK | UUID user yang melakukan aksi |
| `user_name` | text | - | Nama actor |
| `role` | text | - | Role actor |
| `created_at` | timestamptz | - | Timestamp aksi |

**Daftar Action Codes**:
- `STUDENT_LOGIN` — Mahasiswa login sukses
- `LECTURER_LOGIN` — Dosen login sukses
- `PASSWORD_RESET` — Reset password berhasil
- `SYSTEM_SETTING_CHANGED` — Setting sistem diubah
- `ACTIVE_MODEL_CHANGED` — Model AI aktif diganti
- `AI_PROCESS_STARTED` — Prediksi AI dimulai
- `AI_PROCESS_COMPLETED` — Prediksi AI selesai
- `AI_PROCESS_FAILED` — Prediksi AI gagal
- `REVIEW_DRAFT_SAVED` — Draft review disimpan
- `FINAL_SCORE_SUBMITTED` — Nilai final dikunci
- `REUPLOAD_REQUESTED` — Reupload diminta dosen

---

### Tabel: `system_settings`

| Kolom | Tipe | Constraint | Deskripsi |
|---|---|---|---|
| `key` / `setting_key` | text | PRIMARY KEY | Nama konfigurasi |
| `value` / `setting_value` | text | - | Nilai konfigurasi |

**Known Keys**:

| Key | Default | Deskripsi |
|---|---|---|
| `auto_run_ai` | `"false"` | Auto-trigger AI saat mahasiswa submit |
| `active_model` | `"MobileNetV2"` | Model default untuk batch/auto pipeline |
| `verbose_logging` | `"false"` | Enable detailed console logging |
| `future_flags` | `"{}"` | Reserved untuk fitur mendatang |

---

## 6.3 Storage Buckets

### `lembar-jawaban`
- **Tujuan**: Menyimpan foto lembar jawaban tulisan tangan mahasiswa
- **Path Pattern**: `{course_id}/{submission_id}/S-{section_code}.png`
- **Contoh**: `c3d47192.../e8d98d2d.../S-1A.png`
- **Akses**: Authenticated users dapat upload (mahasiswa); Backend service role dapat download untuk AI

### `profile-images`
- **Tujuan**: Menyimpan foto profil/avatar pengguna
- **Path Pattern**: `{user_id}/avatar.png`
- **Akses**: Publicly readable via signed URL; writable hanya oleh pemilik

## 6.4 ERD (Entity Relationship Diagram — Deskripsi)

```
profil_pengguna (1) ────── (*) mahasiswa_mata_kuliah (*) ────── (1) mata_kuliah
profil_pengguna (1) ────── (*) dosen_mata_kuliah (*) ────── (1) mata_kuliah
profil_pengguna (1) ────── (*) pengumpulan_tugas
mata_kuliah (1) ────── (*) pengumpulan_tugas
pengumpulan_tugas (1) ────── (*) lembar_jawaban [CASCADE DELETE]
pengumpulan_tugas (1) ────── (*) hasil_prediksi [CASCADE DELETE]
lembar_jawaban (1) ────── (*) hasil_prediksi [CASCADE DELETE]
```

---

# BAGIAN 7 — ANALISIS MODUL AI

## 7.1 Teknologi OCR dan Pengenalan Tulisan Tangan

**Penting**: Sistem EMATHTOCO **tidak menggunakan OCR berbasis teks** (seperti Tesseract, EasyOCR, PaddleOCR, atau TrOCR). 

Pendekatan yang digunakan adalah **Image Classification berbasis CNN** (Convolutional Neural Network):
- Input: Foto lembar jawaban tulisan tangan matematika (per-section)
- Proses: CNN mengekstrak fitur visual dari gambar
- Output: Prediksi kelas kualitas jawaban → dipetakan ke skor numerik

Alasan pendekatan ini dipilih:
- Tulisan tangan matematika sangat sulit di-OCR (simbol, indeks, fraksi, integral)
- Classification lebih robust daripada OCR untuk jawaban essay matematika
- Model lebih mudah di-train dengan label kelas daripada ground-truth teks
- Setiap section soal memiliki karakteristik visual yang berbeda

## 7.2 Pipeline AI Lengkap

```
INPUT: Foto Lembar Jawaban (S-1A hingga S-4F)
          ↓
STEP 1: Storage Download
  image_service.download_image(image_url)
  → Supabase Storage → download bytes
  → cv2.imdecode(bytes, BGR)
          ↓
STEP 2: Pre-flight Validation
  _validate_storage_files(sheets)
  → Verifikasi semua file ada sebelum mulai inferensi
  → Jika ada file hilang → ABORT semua inferensi
          ↓
STEP 3: Image Preprocessing
  preprocess_image(img, target_size)
  → BGR → RGB conversion (cv2.cvtColor)
  → Resize ke target_size (MobileNet: 128×128, InceptionV3: 299×299)
  → float32 conversion
  → Normalisasi: pixel / 255.0 → range [0.0, 1.0]
  → Expand dims → (1, H, W, 3)
          ↓
STEP 4: Model Loading (Lazy Cache)
  get_model(section_code, model_name)
  → Cek cache: f"{model_name}_{section_code}"
  → Jika belum ada: load dari disk (load_model .h5)
  → PatchedDense menangani quantization_config
  → Simpan ke _loaded_models dict
          ↓
STEP 5: Inference
  model.predict(processed_img, verbose=0)
  → Output: softmax probability distribution
  → predicted_class = argmax(output[0])
  → confidence = max(output[0])
          ↓
STEP 6: Score Mapping
  get_score(section_code, predicted_class)
  → Lookup CLASS_SCORE_MAP[section_code][predicted_class]
  → Return integer score
          ↓
STEP 7: Save to Database
  upsert_prediction(pengumpulan_tugas_id, lembar_jawaban_id,
                    section_code, model_ai, predicted_class,
                    predicted_score, confidence, status)
  → INSERT or UPDATE hasil_prediksi table
          ↓
STEP 8: Compile Final Score
  nilai_akhir = sum(result["predicted_score"] for result in results)
          ↓
STEP 9: Update Submission Status
  update_submission_result(submission_id, nilai_akhir, ai_status, model_ai)
  → pengumpulan_tugas.ai_status = "completed"
  → pengumpulan_tugas.nilai_akhir = total_score
          ↓
OUTPUT: Skor akhir + skor per section + confidence
```

## 7.3 Sistem Section Code

Setiap submission memiliki **24 section** yang merepresentasikan bagian-bagian dari soal ujian:

```
Soal 1: S-1A, S-1B, S-1C, S-1D, S-1E, S-1F
Soal 2: S-2A, S-2B, S-2C, S-2D, S-2E, S-2F
Soal 3: S-3A, S-3B, S-3C, S-3D, S-3E, S-3F
Soal 4: S-4A, S-4B, S-4C, S-4D, S-4E, S-4F
```

Setiap section memiliki:
- Model terpisah: `model_{section}.h5` (misal: `model_1a.h5` untuk S-1A)
- Mapping skor yang berbeda (disesuaikan dengan bobot soal per section)
- Input gambar yang spesifik

## 7.4 Class-to-Score Mapping (CLASS_SCORE_MAP)

Mapping kelas prediksi ke skor numerik per section:

| Section | Kelas yang Dipetakan | Skor Maks |
|---|---|---|
| S-1A | [1, 2, 3, 4] | 4 (kelas 3) |
| S-1B | [0, 1, 2, 3, 4] | 4 (kelas 4) |
| S-1C | [0, 1, 2, 3, 4] | 4 |
| S-1D | [0, 1, 2, 3, 4] | 4 |
| S-1E | [0, 1, 2, 3, 4] | 4 |
| S-1F | [0, 1, 2, 3, 4, 5] | 5 (kelas 5) |
| S-2A | [0, 1, 2, 3, 4] | 4 |
| S-2B | [0, 1, 2, 4] | 4 (skip kelas 3) |
| S-2C | [0, 1, 2, 3, 4] | 4 |
| S-2D | [0, 1, 2, 3, 4] | 4 |
| S-2E | [0, 1, 2, 3, 4] | 4 |
| S-2F | [0, 1, 2, 3, 4, 5] | 5 |
| S-3A–S-3E | [0, 1, 2, 3, 4] | 4 |
| S-3F | [0, 1, 2, 3, 5] | 5 (skip kelas 4) |
| S-4A–S-4E | [0, 1, 2, 3, 4] | 4 |
| S-4F | [0, 1, 2, 3, 4, 5] | 5 |

**Total Skor Maksimum**: Jumlah semua skor maksimal per section (dapat bervariasi tergantung bobot soal)

---

# BAGIAN 8 — ANALISIS MODEL CNN

## 8.1 MobileNetV2

### Deskripsi
MobileNetV2 adalah arsitektur CNN ringan yang dikembangkan oleh Google yang menggunakan **Inverted Residuals** dan **Linear Bottlenecks**. Didesain untuk efisiensi pada perangkat dengan komputasi terbatas.

### Konfigurasi di EMATHTOCO

| Parameter | Nilai |
|---|---|
| **Input Shape** | (1, 128, 128, 3) |
| **Preprocessing** | Normalisasi /255.0 (range [0,1]) |
| **Format File** | .h5 (Keras HDF5) |
| **Jumlah Model** | 24 (satu per section) |
| **Path** | `Models/MobilenetV2/model_{section}.h5` |
| **Cache Key Format** | `MobileNetV2_S-1A`, `MobileNetV2_S-1B`, dst. |

### Keunggulan
- Ukuran model kecil (ringan) → loading cepat
- Cocok untuk deployment pada server dengan GPU/CPU terbatas
- Depthwise separable convolutions mengurangi parameter
- Generalisasi baik untuk dataset gambar resolusi kecil

### Keterbatasan
- Akurasi lebih rendah dari InceptionV3 pada gambar kompleks
- Mungkin kurang akurat untuk tulisan tangan matematika yang sangat detail

---

## 8.2 DenseNet121

### Deskripsi
DenseNet121 menggunakan **Dense Connectivity** di mana setiap layer menerima feature maps dari SEMUA layer sebelumnya, mendorong feature reuse dan mengurangi vanishing gradient.

### Konfigurasi di EMATHTOCO

| Parameter | Nilai |
|---|---|
| **Input Shape** | (1, 128, 128, 3) |
| **Preprocessing** | Normalisasi /255.0 (range [0,1]) |
| **Format File** | .h5 (Keras HDF5) |
| **Jumlah Model** | 24 (satu per section) |
| **Path** | `Models/DenseNet121/model_{section}.h5` |

### Keunggulan
- Dense connections memungkinkan gradient flow lebih baik
- Feature reuse antar-layer meningkatkan efisiensi representasi
- Regularization efek natural dari konektivitas dense
- Performa lebih stabil pada dataset kecil-menengah

### Keterbatasan
- Penggunaan memori lebih tinggi dari MobileNetV2
- Loading time lebih lama karena ukuran model lebih besar

---

## 8.3 InceptionV3

### Deskripsi
InceptionV3 menggunakan **Inception Modules** yang memproses gambar pada multiple scales secara paralel (3×3, 5×5, 1×1 convolutions), memungkinkan model belajar fitur pada berbagai skala sekaligus.

### Konfigurasi di EMATHTOCO

| Parameter | Nilai |
|---|---|
| **Input Shape** | (1, 299, 299, 3) |
| **Preprocessing** | Normalisasi /255.0 (range [0,1]) |
| **Format File** | .h5 (Keras HDF5) |
| **Jumlah Model** | 24 (satu per section) |
| **Path** | `Models/InceptionV3/model_{section}.h5` |

### Perbedaan Kritis dengan MobileNetV2/DenseNet121
- **Input lebih besar**: 299×299 vs 128×128 → gambar diproses pada resolusi lebih tinggi
- **Komputasi lebih berat**: waktu inferensi lebih lama
- **Potensi akurasi lebih tinggi**: karena input resolusi lebih besar

### Keunggulan
- Multi-scale feature extraction efektif untuk karakter tulisan tangan
- Auxiliary classifiers membantu gradient flow saat training
- State-of-the-art di era pre-transformer untuk image classification

### Keterbatasan
- Kebutuhan memori terbesar dari ketiga arsitektur
- Inferensi lebih lambat
- Membutuhkan gambar input berukuran 299×299

---

## 8.4 Sistem Lazy Loading Model

Backend mengimplementasikan sistem **lazy loading dengan in-memory cache**:

```python
_loaded_models = {}  # Global in-memory cache

def get_model(section_code: str, model_name: str) -> Model:
    cache_key = f"{model_name}_{section_code}"
    
    if cache_key not in _loaded_models:
        model_path = f"Models/{model_name}/model_{section.lower()}.h5"
        _loaded_models[cache_key] = load_mobilenet_model(model_path)
    
    return _loaded_models[cache_key]
```

**Keuntungan**:
- Model hanya di-load saat pertama kali dibutuhkan
- Setelah loaded, model tetap di cache → inferensi berikutnya sangat cepat
- Memory efficient: hanya model yang benar-benar dipakai yang tersimpan

**Kapasitas Cache**:
- Total possible keys: 3 arsitektur × 24 section = 72 model entries
- Dalam praktik: hanya model yang dipanggil aktif yang tersimpan

### PatchedDense — Kompatibilitas Model
```python
class PatchedDense(Dense):
    def __init__(self, *args, **kwargs):
        kwargs.pop("quantization_config", None)  # Hapus config tidak kompatibel
        super().__init__(*args, **kwargs)
```
Patch ini diperlukan karena model `.h5` yang di-training mungkin menyimpan `quantization_config` dalam config layer Dense, yang tidak dikenali oleh versi TensorFlow baru.

---

## 8.5 Preprocessing Pipeline Detail

```python
def preprocess_image(img: np.ndarray, target_size: tuple) -> np.ndarray:
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # OpenCV BGR → Model RGB
    img = cv2.resize(img, target_size)           # Resize ke target (H, W)
    img = img.astype("float32")                  # Convert ke float32
    img = img / 255.0                            # Normalisasi [0, 1]
    img = np.expand_dims(img, axis=0)            # Add batch dim → (1, H, W, 3)
    return img
```

---

# BAGIAN 9 — TRAINING (INFORMASI DARI CODEBASE)

## 9.1 Informasi Training

> **Catatan**: Kode training model tidak terdapat dalam repository ini. Informasi berikut diinferensikan dari konfigurasi model yang ada.

### Dataset
- **Jenis**: Gambar foto lembar jawaban tulisan tangan matematika
- **Struktur**: Per-section (24 section berbeda, masing-masing memiliki model sendiri)
- **Label**: Kelas numerik (0, 1, 2, 3, 4, atau 0, 1, 2, 3, 4, 5 tergantung section)
- **Format Input**: Gambar PNG/JPEG

### Konfigurasi Model (Diinferensikan)
- **Optimizer**: Tidak tersedia dalam codebase; kemungkinan Adam atau SGD
- **Loss Function**: Categorical Crossentropy (multi-class classification)
- **Activation Output Layer**: Softmax
- **Training Framework**: TensorFlow/Keras
- **Model Format Output**: HDF5 (.h5)

### Jumlah Kelas per Section
- **4 Kelas**: S-1A (kelas 1-4)
- **5 Kelas**: S-1B, S-1C, S-1D, S-1E, S-2A, S-2C, S-2D, S-2E, S-3A–S-3E, S-4A–S-4E
- **5 Kelas (non-sequential)**: S-2B ([0,1,2,4]), S-3F ([0,1,2,3,5])
- **6 Kelas**: S-1F, S-2F, S-4F

---

# BAGIAN 10 — ANALISIS KEAMANAN

## 10.1 Authentication

- **Metode**: Supabase Auth (Email & Password)
- **Token**: JWT (JSON Web Token) dengan expiry
- **Penyimpanan Token**: Cookie `sb-access-token` (httpOnly-like via Supabase)
- **Validasi**: Server-side di middleware.ts (expiry check via JWT decode) + client-side via `supabase.auth.getUser()`

## 10.2 Authorization

- **Middleware**: `middleware.ts` memproteksi semua route protected
- **Role-Based Access Control (RBAC)**:
  - `mahasiswa`: akses `/`, `/matkul/*`, `/profile`, `/settings`
  - `dosen`: akses `/dosen/*` dan semua di atas
  - `admin`: akses `/admin/*` dan semua di atas
- **Role Normalization**: `normalizeRole()` memastikan semua role dalam lowercase untuk mencegah bypass via kapitalisasi (`Mahasiswa` vs `mahasiswa`)

## 10.3 Row Level Security (RLS)

Supabase RLS memproteksi data di level database:
- Mahasiswa hanya bisa membaca data diri sendiri
- Dosen tidak bisa membaca profil mahasiswa via client key → harus via backend service role

## 10.4 Backend Security

- **Service Role Key**: Hanya digunakan di backend, tidak pernah expose ke frontend
- **CORS**: Whitelist eksplisit origin yang diizinkan
- **Input Validation**: FastAPI + Pydantic untuk validasi payload
- **Guard Clauses**: Setiap endpoint memeriksa status valid sebelum proses
- **ngrok Warning Header**: Frontend mengirim `ngrok-skip-browser-warning: true` untuk bypass popup ngrok

## 10.5 Risiko Keamanan yang Diidentifikasi

| Risiko | Level | Mitigasi |
|---|---|---|
| API URL di .env.local (ngrok) berubah setiap restart | Rendah | ngrok free tier; untuk production gunakan server permanen |
| Service Role Key di .env tidak di-gitignore dengan benar | Sedang | Pastikan .env masuk .gitignore; gunakan vault di production |
| No rate limiting pada endpoint AI | Sedang | Pertimbangkan rate limiting untuk `/predict/*` endpoint |
| JWT expiry check di middleware bisa bypass jika cookie manual | Rendah | Server-side `supabase.auth.getUser()` sebagai lapisan kedua |

---

# BAGIAN 11 — DEPLOYMENT

## 11.1 Arsitektur Deployment Saat Ini

| Komponen | Hosting | URL |
|---|---|---|
| **Frontend** | Vercel | `https://emathtoco.vercel.app` |
| **Backend AI** | Lokal (development) via ngrok | `https://strife-trapper-dad.ngrok-free.dev` |
| **Database** | Supabase Cloud | `https://hkxxhactpwiqdzecrbxw.supabase.co` |
| **Storage** | Supabase Cloud Storage | Sama dengan database |
| **Auth** | Supabase Auth | Sama dengan database |

## 11.2 Cara Menjalankan Backend Lokal

```bash
# Navigasi ke backend folder
cd Emathoco_BackEnd

# Aktifkan virtual environment
.\venv\Scripts\activate  (Windows)

# Install dependencies
python -m pip install --require-hashes -r requirements-dev.txt

# Jalankan server
uvicorn main:app --reload

# Ekspos ke internet via ngrok (terminal terpisah)
ngrok http 8000
```

## 11.3 Cara Menjalankan Frontend Lokal

```bash
# Navigasi ke frontend folder
cd Emathtoco_FrontEnd/Emathtoco_Web

# Install dependencies
npm install

# Jalankan development server
npm run dev

# Frontend akan berjalan di http://localhost:3000
```

## 11.4 Deployment Production (Frontend)

Vercel deployment terkonfigurasi otomatis dari repository Git:
- Build Command: `npm run build`
- Output: `.next/`
- Environment Variables: Diset di Vercel dashboard

---

# BAGIAN 12 — INVENTARIS FITUR LENGKAP

## 12.1 Fitur yang Sudah Selesai

| # | Fitur | Status | User |
|---|---|---|---|
| 1 | Role-Based Login Selection Page | ✅ COMPLETED | Semua |
| 2 | Student Login Portal (/login/mahasiswa) | ✅ COMPLETED | Mahasiswa |
| 3 | Lecturer Login Portal (/login/dosen) | ✅ COMPLETED | Dosen, Admin |
| 4 | Student Course Workspace | ✅ COMPLETED | Mahasiswa |
| 5 | 24-Section Answer Sheet Upload | ✅ COMPLETED | Mahasiswa |
| 6 | Camera/File Upload with Crop | ✅ COMPLETED | Mahasiswa |
| 7 | Task Submission → AI Trigger | ✅ COMPLETED | Mahasiswa |
| 8 | Student Dashboard with Courses | ✅ COMPLETED | Mahasiswa |
| 9 | Reupload Warning Badge | ✅ COMPLETED | Mahasiswa |
| 10 | Lecturer Dashboard | ✅ COMPLETED | Dosen |
| 11 | Course Assessment Portal | ✅ COMPLETED | Dosen |
| 12 | Class Student Roster (Secure API) | ✅ COMPLETED | Dosen |
| 13 | AI Auto-scoring Pipeline | ✅ COMPLETED | Dosen |
| 14 | Manual Review & Override Workspace | ✅ COMPLETED | Dosen |
| 15 | Batch AI Processing Modal | ✅ COMPLETED | Dosen |
| 16 | Score Finalization | ✅ COMPLETED | Dosen |
| 17 | Reupload Request (per section) | ✅ COMPLETED | Dosen |
| 18 | Section Feedback Comments | ✅ COMPLETED | Dosen |
| 19 | Admin Dashboard with Statistics | ✅ COMPLETED | Admin |
| 20 | User Management (CRUD + Delete Cascade) | ✅ COMPLETED | Admin |
| 21 | Course Management (CRUD) | ✅ COMPLETED | Admin |
| 22 | Enrollment Management | ✅ COMPLETED | Admin |
| 23 | Lecturer Assignment | ✅ COMPLETED | Admin |
| 24 | Enterprise Audit Log Viewer | ✅ COMPLETED | Admin |
| 25 | System Settings Dashboard | ✅ COMPLETED | Admin |
| 26 | AI Model Info Panel | ✅ COMPLETED | Admin |
| 27 | System Diagnostics | ✅ COMPLETED | Admin |
| 28 | Profile Photo Upload (Avatar) | ✅ COMPLETED | Semua |
| 29 | Profile Management | ✅ COMPLETED | Semua |
| 30 | Forgot/Reset Password | ✅ COMPLETED | Semua |
| 31 | Dark/Light Mode Toggle | ✅ COMPLETED | Semua |
| 32 | Export Data CSV/Excel | ✅ COMPLETED | Dosen |
| 33 | Collapsible Admin Sidebar | ✅ COMPLETED | Admin |
| 34 | Audit Log (Frontend → Backend) | ✅ COMPLETED | Semua |

## 12.2 Fitur yang Direncanakan (Planned)

| # | Fitur | Status |
|---|---|---|
| 1 | Admin Student Registration Validation Queue | 🔄 PLANNED |

---

# BAGIAN 13 — ALUR PENGGUNA (USER FLOWS)

## 13.1 Alur Mahasiswa

```
[REGISTRASI]
Buka /register → Isi email + password → Signup Supabase
→ Redirect ke /complete-profile → Isi nama, NIM, kelas → Simpan profil
→ Redirect ke / (dashboard)

[LOGIN]
Buka /login → Pilih "Mahasiswa" → /login/mahasiswa
→ Isi email (cek terdaftar via backend) → Isi password
→ Login Supabase → Verifikasi role 'mahasiswa'
→ Redirect ke /

[PENGUMPULAN TUGAS]
Dashboard → Pilih mata kuliah → /matkul/[id]
→ Upload foto per section (S-1A s.d. S-4F)
→ Foto diambil via kamera atau pilih file
→ Preview + crop jika perlu
→ Upload ke Supabase Storage
→ Ulangi untuk 24 section
→ Klik "Kumpulkan" → POST /submission/{id}/submit
→ Backend: jika auto_run_ai=ON → AI mulai berjalan di background
→ Status berubah: "Menunggu AI" / "Diproses AI" / "Selesai"
→ Mahasiswa bisa lihat skor AI di dashboard

[REUPLOAD]
Dashboard → Ada badge ⚠ ACTION REQUIRED
→ Klik mata kuliah → Navigasi ke section bermasalah
→ Upload ulang foto → Submit ulang
```

## 13.2 Alur Dosen

```
[LOGIN]
/login → Pilih "Dosen" → /login/dosen
→ Login Supabase → Verifikasi role 'dosen'
→ Redirect ke /dosen

[MANAJEMEN PENILAIAN]
Dashboard → Pilih mata kuliah → /dosen/course/[id]
→ Lihat summary stats (berapa yang belum kumpul, menunggu AI, dll)
→ Pilih mahasiswa → Klik "Jalankan AI" atau "Batch AI"
→ Backend: POST /predict/{submission_id} 
→ AI memproses 24 section → Simpan hasil ke DB
→ Status berubah ke "Selesai AI"
→ Klik "Review" → /dosen/review/[id]
→ Lihat foto per section + skor AI + confidence
→ Override skor jika diperlukan
→ Tambahkan feedback
→ Request reupload jika foto tidak jelas
→ Klik "Finalisasi" → POST /submission/{id}/finalize
→ Nilai terkunci
```

## 13.3 Alur Admin

```
[LOGIN]
/login → Pilih "Dosen/Admin" → /login/dosen
→ Login → Role 'admin' → Redirect ke /admin

[KELOLA PENGGUNA]
/admin/users → Lihat semua user
→ Tambah user baru (create account + profil)
→ Atau Hapus user → DELETE /admin/user/{id} (cascade)

[KELOLA MATA KULIAH]
/admin/courses → Tambah/Edit/Hapus mata kuliah

[ENROLLMENT]
/admin/enrollment → Daftarkan mahasiswa ke mata kuliah
/admin/lecturers → Tugaskan dosen ke mata kuliah

[SYSTEM SETTINGS]
/admin/system-settings → Toggle auto_run_ai
→ Pilih active_model (MobileNetV2/DenseNet121/InceptionV3)
→ Perubahan di-log ke audit_log

[AUDIT LOG]
/admin/audit → Lihat seluruh aktivitas sistem
→ Filter by date, user, action type
```

## 13.4 Alur AI (Detailed)

```
Trigger: POST /predict/{submission_id}?model=MobileNetV2

1. Validasi submission exists
2. Guard: status 'finalized' → reject
3. Guard: status 'processing' → reject (409 Conflict)
4. Update pengumpulan_tugas: ai_status='processing'
5. Audit log: AI_PROCESS_STARTED
6. Fetch semua lembar_jawaban untuk submission ini
7. PRE-FLIGHT CHECK: verifikasi semua file ada di Storage
   - Jika ada file hilang → update status='failed', return error
8. Loop setiap sheet:
   a. Download image dari Supabase Storage
   b. Decode bytes → numpy BGR array (OpenCV)
   c. BGR → RGB, resize, normalize, expand_dims
   d. Lazy load model dari cache (atau load dari disk)
   e. model.predict() → softmax output
   f. argmax → predicted_class
   g. max(output) → confidence
   h. CLASS_SCORE_MAP lookup → predicted_score
   i. Upsert ke hasil_prediksi
9. nilai_akhir = sum(semua predicted_score)
10. Update pengumpulan_tugas: nilai_akhir, ai_status='completed'
11. Audit log: AI_PROCESS_COMPLETED (with total_score)
12. Return result JSON
```

---

# BAGIAN 14 — DESAIN UI/UX

## 14.1 Design System

### Color Palette

| Elemen | Light Mode | Dark Mode |
|---|---|---|
| Background | `bg-slate-50` | `bg-[#060814]` via `#020205` to `#000000` |
| Cards | `bg-white border-slate-200` | `bg-[#0A0A0F]/80 border-neutral-800/80` |
| Backdrop | - | `backdrop-blur-md` |
| Mahasiswa accent | `text-blue-600` | `text-cyan-400` |
| Dosen accent | `text-indigo-600` | `text-indigo-400` |
| Admin accent | `text-emerald-600` | `text-emerald-400` |
| Warning | `text-amber-600` | `text-amber-400` |
| Error | `text-red-600` | `text-red-400` |
| Monospace data | `font-mono text-blue-600` | `font-mono text-cyan-400` |

### Typography
- **Font**: System default sans-serif (Inter-like via Tailwind)
- **Monospace**: `font-mono` untuk: NIM/NIP, kelas, skor, timestamp, section code
- **Headings**: `font-extrabold tracking-tight`
- **Labels**: `uppercase tracking-widest text-xs font-bold`

### Glassmorphism Components
```css
.glass-card {
  background: rgba(10, 10, 15, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
}
```

### Animated Background Glows
```jsx
<div className="absolute top-[10%] left-[15%] w-[450px] h-[450px] 
                bg-cyan-500/12 rounded-full blur-[120px] animate-float-blue" />
<div className="absolute bottom-[15%] right-[15%] w-[500px] h-[500px] 
                bg-indigo-500/12 rounded-full blur-[130px] animate-float-purple" />
```

### Button Styles
```
Primary/CTA: bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-600
Hover: hover:scale-[1.02] active:scale-[0.98] transition-all
Disabled: disabled:opacity-50 disabled:cursor-not-allowed
```

### Loading States
- Skeleton placeholders: `animate-pulse` pada card placeholder
- Spinner: `<Loader2 className="animate-spin" />`
- Fullscreen loader: `FullscreenLoader` component untuk transisi halaman

---

# BAGIAN 15 — PEMETAAN UNTUK DOKUMEN CAPSTONE

## 15.1 Mapping untuk CD4 (Background & Methodology)

### Latar Belakang
Gunakan **Bagian 1.2 (Latar Belakang Masalah)** dan **Bagian 1.3 (Solusi)** sebagai dasar latar belakang. Key points:
- Problem: Manual grading tulisan tangan matematika → time-consuming, subjektif, error-prone
- Gap: Belum ada sistem otomatis yang khusus untuk essay matematika tulisan tangan di lingkungan pendidikan tinggi Indonesia
- Solution: CNN-based image classification untuk menilai kualitas jawaban per-bagian

### Tinjauan Pustaka (Input untuk CD4)
| Topik | Referensi dari Codebase |
|---|---|
| CNN Classification | MobileNetV2 (Howard et al., 2018), DenseNet (Huang et al., 2017), InceptionV3 (Szegedy et al., 2016) |
| Handwriting Recognition | Custom CNN approach (non-OCR) |
| EdTech AI | Automated assessment sistem |
| Web Technology | Next.js, FastAPI, Supabase |

### Metodologi
1. **Pengumpulan Dataset**: Foto lembar jawaban tulisan tangan mahasiswa
2. **Preprocessing**: Resize, normalisasi pixel, format standarisasi
3. **Model Selection**: Transfer Learning dengan MobileNetV2, DenseNet121, InceptionV3
4. **Training**: Per-section (24 model independent per arsitektur)
5. **Evaluation**: Accuracy, confidence distribution, skor akhir vs ground truth
6. **Deployment**: FastAPI + Next.js + Supabase cloud stack

### Arsitektur untuk CD4
Gunakan **Bagian 2.1 (High-Level Architecture)** dan **Bagian 7.2 (AI Pipeline)** untuk diagram arsitektur sistem.

---

## 15.2 Mapping untuk CD5 (Implementation & Testing)

### Implementasi
- Frontend: **Bagian 4 (Frontend Analysis)** — halaman, komponen, state management
- Backend: **Bagian 5 (Backend Analysis)** — endpoint list, middleware, business logic
- Database: **Bagian 6 (Database Analysis)** — schema, relasi, storage
- AI Module: **Bagian 7–8 (AI Analysis)** — pipeline, model config, preprocessing

### Testing
| Aspek Testing | Detail |
|---|---|
| Unit Testing | Preprocessing pipeline, class mapping, model loading |
| Integration Testing | Frontend → Backend → DB → Storage flow |
| AI Testing | Prediksi per-model per-section, deduplication logic |
| User Testing | Login flow, upload flow, review flow |

---

## 15.3 Mapping untuk CD6 (Final Validation & Deployment)

### Deployment Architecture
Gunakan **Bagian 11 (Deployment)** sebagai referensi deployment architecture.

### Future Work
Gunakan **Bagian 17 (Future Research)** sebagai roadmap pengembangan lanjutan.

---

# BAGIAN 16 — PERSIAPAN SIDANG (FAQ)

## 16.1 50+ Pertanyaan dan Jawaban untuk Sidang/Viva

### Tentang Proyek & Latar Belakang

**Q1: Apa itu EMATHTOCO?**
> EMATHTOCO (Essay Mathematics Auto Correction) adalah platform berbasis AI yang mengotomatisasi penilaian lembar jawaban esai matematika tulisan tangan. Sistem menggunakan model CNN (MobileNetV2, DenseNet121, InceptionV3) untuk mengklasifikasikan kualitas jawaban tiap section dan menghasilkan skor numerik secara otomatis.

**Q2: Apa masalah utama yang diselesaikan sistem ini?**
> Masalah utamanya adalah proses penilaian manual yang memakan waktu lama, subjektif, rentan human error, dan tidak skalabel. EMATHTOCO mengotomatisasi proses ini sehingga dosen dapat mendapatkan penilaian dalam hitungan menit, bukan jam.

**Q3: Mengapa memilih pendekatan CNN classification, bukan OCR?**
> Tulisan tangan matematika sangat kompleks — mengandung simbol matematis, fraksi, integral, indeks, dan notasi khusus yang sangat sulit dikenali oleh sistem OCR berbasis teks. CNN berbasis image classification lebih robust karena mengevaluasi kualitas jawaban secara visual holistic, bukan mencoba membaca setiap karakter secara individual.

**Q4: Siapa pengguna target sistem ini?**
> Tiga kelompok pengguna: (1) Mahasiswa — mengunggah jawaban dan melihat hasil, (2) Dosen — memicu AI, mereview, dan memfinalisasi nilai, (3) Administrator — mengelola user, mata kuliah, dan konfigurasi sistem.

---

### Tentang CNN dan Arsitektur Model

**Q5: Apa itu Convolutional Neural Network (CNN)?**
> CNN adalah jenis jaringan saraf tiruan yang dirancang khusus untuk memproses data berbentuk grid, seperti gambar. CNN menggunakan operasi konvolusi untuk mengekstrak fitur visual hierarkis — dari tepi dan tekstur di layer awal hingga pola dan objek kompleks di layer dalam.

**Q6: Mengapa menggunakan tiga arsitektur CNN yang berbeda?**
> Untuk memberikan fleksibilitas dan perbandingan kinerja. MobileNetV2 lebih ringan dan cepat, DenseNet121 memiliki dense connectivity yang efisien, sedangkan InceptionV3 memproses gambar pada resolusi lebih tinggi (299×299). Admin dapat memilih model aktif sesuai tradeoff antara kecepatan dan akurasi.

**Q7: Apa itu MobileNetV2?**
> MobileNetV2 adalah arsitektur CNN yang dikembangkan Google, menggunakan inverted residuals dan linear bottlenecks untuk mencapai efisiensi tinggi dengan ukuran model yang kecil. Cocok untuk deployment pada resource terbatas. Dalam sistem ini, input size 128×128 digunakan.

**Q8: Apa itu DenseNet121?**
> DenseNet (Densely Connected Convolutional Networks) menghubungkan setiap layer ke semua layer berikutnya. Ini mendorong feature reuse, mengurangi vanishing gradient, dan memerlukan parameter lebih sedikit daripada arsitektur tradisional. DenseNet121 memiliki 121 layer.

**Q9: Apa itu InceptionV3?**
> InceptionV3 menggunakan Inception modules yang memproses gambar secara paralel dengan berbagai ukuran filter (1×1, 3×3, 5×5) sehingga model dapat menangkap fitur pada berbagai skala sekaligus. Input size InceptionV3 dalam sistem ini adalah 299×299, lebih besar dari dua arsitektur lainnya.

**Q10: Apa perbedaan utama antara MobileNetV2, DenseNet121, dan InceptionV3 dalam konteks EMATHTOCO?**
> | | MobileNetV2 | DenseNet121 | InceptionV3 |
> |---|---|---|---|
> | Input | 128×128 | 128×128 | 299×299 |
> | Kecepatan | Tercepat | Sedang | Paling lambat |
> | Memori | Terkecil | Sedang | Terbesar |
> | Kekuatan | Efisiensi | Feature reuse | Multi-scale |

**Q11: Mengapa setiap section memiliki model yang berbeda?**
> Karena setiap section soal memiliki karakteristik jawaban yang berbeda — bobot soal, jenis tulisan, dan kompleksitas visual yang berbeda. Model yang di-training secara spesifik per-section akan lebih akurat dibandingkan model generik untuk semua section.

**Q12: Berapa total model yang ada dalam sistem?**
> 72 model total: 3 arsitektur × 24 section = 72 file .h5. Masing-masing model merepresentasikan klasifikasi untuk satu section soal dengan satu arsitektur CNN.

**Q13: Apa itu lazy loading model?**
> Lazy loading berarti model tidak di-load ke memori saat startup, melainkan hanya saat pertama kali dibutuhkan. Setelah di-load, model disimpan dalam dict `_loaded_models` (in-memory cache) dan digunakan kembali untuk request berikutnya tanpa re-loading dari disk.

---

### Tentang Preprocessing

**Q14: Apa yang dilakukan pada tahap preprocessing gambar?**
> Empat langkah utama: (1) Konversi warna BGR ke RGB (karena OpenCV menggunakan BGR), (2) Resize ke target size model (128×128 atau 299×299), (3) Konversi ke float32, (4) Normalisasi pixel ke range [0.0, 1.0] dengan membagi 255. Terakhir, ditambahkan dimensi batch sehingga shape menjadi (1, H, W, 3).

**Q15: Mengapa perlu normalisasi pixel ke [0, 1]?**
> Normalisasi memastikan semua nilai input berada dalam range yang sama, mencegah salah satu fitur mendominasi proses pelatihan. Ini juga mempercepat konvergensi gradient descent dan mengurangi numerical instability.

**Q16: Mengapa menggunakan OpenCV untuk preprocessing?**
> OpenCV adalah library computer vision yang sangat efisien untuk operasi gambar real-time. Ia dapat melakukan decode, resize, dan konversi warna dengan sangat cepat, cocok untuk pipeline inferensi yang membutuhkan throughput tinggi.

---

### Tentang Output Model dan Scoring

**Q17: Apa output dari model CNN?**
> Output berupa vektor probabilitas softmax dengan panjang sesuai jumlah kelas untuk section tersebut (4, 5, atau 6 kelas). Setiap nilai merepresentasikan probabilitas gambar termasuk dalam kelas tersebut, dan jumlah semua nilai adalah 1.0.

**Q18: Apa yang dimaksud dengan "predicted_class"?**
> predicted_class adalah index dari nilai tertinggi dalam vektor softmax output, didapat dari `np.argmax(output[0])`. Ini merepresentasikan kelas yang diprediksi model sebagai yang paling probable.

**Q19: Apa yang dimaksud dengan "confidence"?**
> Confidence adalah nilai maksimum dalam vektor softmax: `np.max(output[0])`. Nilainya antara 0 dan 1, merepresentasikan seberapa "yakin" model dengan prediksinya. Confidence 0.97 berarti model 97% yakin dengan prediksi tersebut.

**Q20: Bagaimana kelas prediksi dikonversi ke skor?**
> Melalui CLASS_SCORE_MAP yang mendefinisikan mapping `section_code → [skor per kelas]`. Contoh: untuk S-1A, mapping adalah [1, 2, 3, 4]. Jika predicted_class = 2, maka skor = mapping[2] = 3.

**Q21: Mengapa mapping skor berbeda antar section?**
> Karena bobot soal berbeda. Section akhir (S-xF) memiliki skor maksimum 5, sedangkan section lain maksimum 4. Section S-2B hanya memiliki kelas [0, 1, 2, 4] (tanpa kelas 3) karena distribusi data training tidak memiliki contoh kelas 3 yang signifikan.

**Q22: Bagaimana nilai akhir dihitung?**
> `nilai_akhir = sum(predicted_score untuk semua 24 section)`. Ini adalah penjumlahan sederhana dari semua skor yang diprediksi untuk setiap bagian jawaban.

---

### Tentang Database

**Q23: Mengapa menggunakan Supabase?**
> Supabase menyediakan PostgreSQL managed cloud, built-in authentication, storage, dan Row Level Security dalam satu platform. Ini mengurangi kompleksitas infrastruktur secara signifikan untuk proyek capstone.

**Q24: Apa itu Row Level Security (RLS)?**
> RLS adalah fitur PostgreSQL yang membatasi baris data mana yang dapat dibaca/ditulis oleh user tertentu, berdasarkan aturan yang didefinisikan di level database. Dalam EMATHTOCO, ini mencegah mahasiswa mengakses data mahasiswa lain.

**Q25: Mengapa backend menggunakan Service Role Key?**
> Service Role Key memberikan akses admin penuh ke database, bypass RLS. Ini diperlukan untuk operasi yang membutuhkan akses lintas-user seperti: membaca daftar mahasiswa untuk dosen, menghapus akun user, atau menjalankan AI pipeline atas nama dosen.

**Q26: Jelaskan relasi antar tabel utama!**
> `profil_pengguna` (user) ↔ (many-to-many via `mahasiswa_mata_kuliah`) ↔ `mata_kuliah` (course). Satu user bisa terdaftar di banyak course. `pengumpulan_tugas` adalah submission dari satu mahasiswa untuk satu course. `lembar_jawaban` adalah foto individual per-section dalam submission. `hasil_prediksi` adalah output model AI untuk setiap lembar jawaban.

**Q27: Apa fungsi tabel `audit_log`?**
> `audit_log` mencatat semua aksi signifikan dalam sistem: login, perubahan setting, proses AI, finalisasi nilai, dll. Ini penting untuk accountability, debugging, dan compliance. Setiap entry menyimpan: action code, target, detail payload (JSON), user_id, user_name, role, dan timestamp.

---

### Tentang FastAPI dan Backend

**Q28: Mengapa menggunakan FastAPI?**
> FastAPI memiliki performa tinggi (berbasis Starlette dan ASGI), async support bawaan, validasi otomatis via Pydantic, dan auto-generate OpenAPI documentation. Python ecosystem memudahkan integrasi dengan TensorFlow/Keras.

**Q29: Bagaimana BackgroundTasks bekerja di FastAPI?**
> `BackgroundTasks` memungkinkan endpoint mengembalikan response secara immediate ke client, sementara fungsi tertentu berjalan di background setelah response terkirim. Dalam EMATHTOCO, prediksi AI dijalankan di background agar mahasiswa tidak perlu menunggu proses AI selesai saat klik "Kumpulkan".

**Q30: Apa yang dilakukan `SettingsService`?**
> `SettingsService` adalah singleton yang mengelola sistem settings dengan in-memory cache TTL 30 detik. Saat setting diakses, ia cek cache terlebih dahulu; jika expired, fetch dari database. Ini mengurangi query database yang berulang untuk setting yang jarang berubah. Auto-seed juga dilakukan untuk setting yang belum ada di database.

---

### Tentang Autentikasi dan Keamanan

**Q31: Bagaimana alur autentikasi bekerja?**
> (1) User input email+password di form login, (2) Pre-check email ke backend `/auth/check-email`, (3) `supabase.auth.signInWithPassword()` di frontend, (4) Supabase Auth memvalidasi dan mengembalikan session JWT, (5) Token disimpan di cookie `sb-access-token`, (6) Middleware membaca cookie di setiap request protected, (7) Client-side `supabase.auth.getUser()` verifikasi ulang token dengan Supabase server.

**Q32: Apa fungsi `normalizeRole()`?**
> `normalizeRole()` mengkonversi semua nilai role ke lowercase untuk mencegah error karena inkonsistensi kapitalisasi di database (misal: `Mahasiswa` vs `mahasiswa`). Ini adalah utility helper di `lib/utils.ts`.

**Q33: Bagaimana CORS dikonfigurasi di backend?**
> CORS dikonfigurasi di FastAPI dengan whitelist origin eksplisit dari env var `ALLOWED_ORIGINS`, ditambah regex pattern untuk Vercel deployment (`*.vercel.app`) dan localhost. `allow_credentials=True` diperlukan agar cookie dapat dikirim dalam cross-origin request.

---

### Tentang Frontend

**Q34: Mengapa menggunakan Next.js?**
> Next.js menyediakan App Router, Server Components, middleware, TypeScript support, dan Vercel deployment yang mulus. App Router memungkinkan nested layouts yang efisien (seperti admin layout dengan sidebar).

**Q35: Bagaimana dark mode diimplementasikan?**
> Menggunakan `next-themes` library yang menyuntikkan class `dark` ke HTML root element. Tailwind CSS menggunakan selector `dark:` untuk mengaplikasikan style berbeda pada dark mode. Preferensi disimpan di localStorage oleh next-themes.

**Q36: Apa fungsi `api-client.ts`?**
> `api-client.ts` adalah centralized HTTP client untuk semua komunikasi ke FastAPI backend. Ia otomatis menambahkan header `ngrok-skip-browser-warning: true` dan `Accept: application/json` ke setiap request, memudahkan debugging, dan menyediakan wrapper untuk GET, POST, PUT, PATCH, DELETE.

---

### Tentang Deployment

**Q37: Bagaimana frontend di-deploy?**
> Frontend di-deploy ke Vercel — platform hosting Next.js yang dikembangkan oleh tim yang sama. Deployment otomatis dari Git repository, dengan environment variables yang diset di dashboard Vercel.

**Q38: Bagaimana backend diakses dari frontend yang di-host di Vercel?**
> Saat development, backend berjalan lokal dan diekspos via ngrok tunnel. URL ngrok diset di `.env.local` frontend sebagai `NEXT_PUBLIC_API_URL`. Saat production, backend idealnya di-deploy ke cloud server (AWS, GCP, atau VPS) dengan URL tetap.

**Q39: Apa keterbatasan deployment saat ini?**
> Backend AI masih berjalan lokal via ngrok free tier, yang berarti URL berubah setiap kali server restart dan memiliki bandwidth limit. Untuk production penuh, backend perlu di-deploy ke cloud server yang permanen.

---

### Tentang Evaluasi Model

**Q40: Bagaimana performa model dievaluasi?**
> *Information not found in codebase*. Kode training dan evaluasi tidak tersedia dalam repository ini. Evaluasi menggunakan metrik standar klasifikasi: accuracy, precision, recall, F1-score, dan confusion matrix per-section. Perbandingan antar arsitektur (MobileNetV2 vs DenseNet121 vs InceptionV3) dilakukan berdasarkan metrik tersebut.

**Q41: Apa itu confusion matrix?**
> Confusion matrix adalah tabel yang menunjukkan performa klasifikasi: setiap baris merepresentasikan kelas aktual, setiap kolom merepresentasikan kelas yang diprediksi. Diagonal utama adalah prediksi benar (true positives + true negatives).

**Q42: Mengapa menggunakan confidence threshold?**
> Confidence threshold dapat digunakan untuk menandai prediksi dengan kepercayaan rendah sebagai "perlu review manual". Dalam implementasi saat ini, nilai confidence ditampilkan ke dosen sebagai informasi tambahan untuk membantu keputusan override.

---

### Pertanyaan Teknis Mendalam

**Q43: Apa yang terjadi jika salah satu file gambar tidak ditemukan di Storage saat prediksi?**
> Sistem mengimplementasikan pre-flight validation sebelum inferensi dimulai. Jika ada file yang hilang, **seluruh prediksi dibatalkan** (tidak dilakukan prediksi parsial). Status submission diubah ke `failed` dengan pesan error yang menyebutkan section mana yang hilang. Pendekatan ini memastikan konsistensi: tidak mungkin ada submission dengan prediksi parsial yang bisa dianggap "selesai".

**Q44: Bagaimana duplicate prediksi dicegah?**
> Pertama, tabel `hasil_prediksi` memiliki unique constraint pada `(pengumpulan_tugas_id, section_code)`, sehingga tidak bisa ada dua prediksi untuk section yang sama dalam satu submission. Kedua, sistem menggunakan operasi UPSERT (INSERT or UPDATE). Ketiga, sebelum prediksi baru dimulai, semua prediksi lama untuk submission tersebut dihapus terlebih dahulu.

**Q45: Apa yang terjadi jika prediksi AI gagal di tengah jalan?**
> Jika ada section yang gagal diproses, semua hasil prediksi parsial yang sudah tersimpan akan dihapus (`delete_predictions_by_submission`), dan status submission diubah ke `failed`. Global exception handler juga menangkap crash tak terduga dan memastikan status tidak terjebak di "processing".

**Q46: Bagaimana sistem mencegah proses AI berjalan ganda (concurrent)?**
> Guard clause memeriksa `ai_status == "processing"` sebelum memulai prediksi baru. Jika status sudah "processing", endpoint mengembalikan HTTP 409 Conflict dengan pesan "AI sedang berjalan". Status ini di-set ke "processing" di awal pipeline sebelum inferensi dimulai.

**Q47: Apa itu `PatchedDense` dan mengapa diperlukan?**
> `PatchedDense` adalah subclass dari `Dense` layer Keras yang menghapus parameter `quantization_config` dari config sebelum konstruksi. Ini diperlukan karena model `.h5` yang di-training mungkin menyimpan config ini, namun versi TensorFlow yang digunakan tidak mendukungnya, menyebabkan error saat `load_model()`.

**Q48: Bagaimana admin dapat mengganti model AI yang aktif?**
> Melalui `/admin/system-settings`, admin mengubah nilai `active_model` di tabel `system_settings`. `SettingsService` membaca nilai ini dengan cache TTL 30 detik. Endpoint `/predict/` menggunakan nilai ini sebagai default model jika tidak ada parameter model explisit yang diberikan. Perubahan model dilog ke `audit_log` dengan action `ACTIVE_MODEL_CHANGED`.

**Q49: Bagaimana `auto_run_ai` setting bekerja?**
> Saat mahasiswa klik "Kumpulkan", frontend memanggil `POST /submission/{id}/submit`. Backend membaca `auto_run_ai` dari database. Jika `true`, prediksi AI dijalankan di background thread (`BackgroundTasks`). Jika `false`, hanya status submission yang diupdate; dosen harus memicu prediksi manual dari dashboard.

**Q50: Apa yang dimaksud dengan "section" dalam konteks EMATHTOCO?**
> Section adalah subdivisi dari satu soal ujian. Setiap soal dibagi menjadi 6 section (A–F). Ada 4 soal, sehingga total 24 section (S-1A hingga S-4F). Mahasiswa mengunggah foto terpisah untuk setiap section. Model AI yang berbeda digunakan untuk setiap section karena karakteristik jawaban berbeda.

**Q51: Bagaimana skor per-section dikompilasi menjadi nilai akhir?**
> Nilai akhir (`nilai_akhir`) adalah penjumlahan sederhana dari `predicted_score` untuk semua 24 section yang berhasil diprediksi: `sum(result["predicted_score"] for result in results)`. Nilai ini disimpan di `pengumpulan_tugas.nilai_akhir`.

**Q52: Apakah dosen bisa mengubah skor yang diberikan AI?**
> Ya. Di halaman review (`/dosen/review/[id]`), dosen dapat melakukan override manual terhadap skor AI per-section melalui field `nilai_dosen` di tabel `lembar_jawaban`. Dosen juga bisa menambahkan feedback dan meminta mahasiswa upload ulang foto yang tidak jelas.

**Q53: Bagaimana proses finalisasi bekerja?**
> Ketika dosen klik "Finalisasi", frontend memanggil `POST /submission/{id}/finalize` di backend. Backend memperbarui `pengumpulan_tugas.ai_status = "finalized"` dan `status_submit = "finalized"`. Status finalized tidak dapat di-override lagi — endpoint prediksi akan menolak request dengan HTTP 400. Ini memastikan nilai yang sudah dikunci tidak dapat berubah.

---

# BAGIAN 17 — KETERBATASAN DAN PENELITIAN MASA DEPAN

## 17.1 Keterbatasan Sistem Saat Ini

1. **Backend Tidak Ter-cloud**: Backend AI berjalan lokal dengan ngrok tunnel. URL berubah setiap restart, bandwidth terbatas, tidak ada uptime guarantee.

2. **Model Belum Divalidasi Secara Publik**: Performa model (akurasi, F1-score) belum terukur secara resmi terhadap dataset uji terpisah. Kode training tidak tersedia.

3. **Tidak Ada Rate Limiting**: Endpoint prediksi AI tidak dibatasi, berpotensi di-abuse atau overload server jika banyak request bersamaan.

4. **Tidak Ada Batch Processing Parallel**: Prediksi untuk 24 section dalam satu submission dilakukan secara sequential, bukan paralel. Ini membuat waktu prediksi bergantung pada jumlah section.

5. **Storage Public Bucket**: Supabase Storage tidak menggunakan URL yang signed/expiring untuk proteksi gambar jawaban.

6. **Training Data Tidak Terdokumentasi**: Ukuran dataset, distribusi kelas, augmentasi yang digunakan, dan proses validasi training tidak tersedia di repository.

7. **Keterbatasan OCR Matematika**: Sistem tidak dapat membaca konten matematis — hanya mengklasifikasikan kualitas visual. Tidak dapat memberikan feedback spesifik tentang langkah penyelesaian yang salah.

## 17.2 Peluang Peningkatan di Masa Depan

1. **Cloud Backend Deployment**: Deploy FastAPI ke AWS/GCP/Azure atau platform seperti Railway/Render untuk URL tetap dan uptime production.

2. **Parallel Inference**: Implementasikan async paralel prediksi menggunakan `asyncio` atau thread pool untuk memproses semua 24 section secara bersamaan, mengurangi waktu dari O(n) menjadi O(1).

3. **Model Versioning**: Implementasikan sistem versioning model sehingga admin dapat me-rollback ke versi model sebelumnya jika diperlukan.

4. **Hybrid OCR+CNN**: Integrasikan OCR untuk ekstraksi teks dan CNN untuk penilaian kualitas visual — memberikan evaluasi yang lebih komprehensif.

5. **Active Learning Pipeline**: Sistem yang mengumpulkan prediksi dengan confidence rendah dan secara otomatis mengajukan ke dosen untuk labeling, memperkuat dataset training secara berkelanjutan.

6. **Student Analytics Dashboard**: Dashboard statistik progress mahasiswa lintas-waktu, distribusi nilai, skor per-section, area yang perlu diperbaiki.

7. **Mobile App**: Aplikasi mobile (React Native atau Flutter) untuk mahasiswa agar lebih mudah mengambil foto dan mengunggah jawaban langsung dari smartphone.

8. **Plagiarism Detection**: Sistem deteksi kesamaan antar-jawaban mahasiswa menggunakan CNN feature extraction + similarity metric.

9. **Real-time Feedback**: Notifikasi real-time ke mahasiswa saat AI selesai memproses atau saat dosen memberikan feedback, menggunakan Supabase Realtime subscriptions.

10. **Multi-language Support**: Dukungan bahasa Inggris untuk potensi ekspansi ke luar Indonesia.

## 17.3 Peluang Komersialisasi

1. **SaaS Platform**: Dijual sebagai platform berlangganan ke institusi pendidikan lain di Indonesia
2. **White-label Solution**: Dijual sebagai solusi yang dapat di-brand ulang oleh universitas
3. **API-as-a-Service**: Menyediakan API prediksi yang dapat diintegrasikan ke Learning Management System (LMS) yang sudah ada seperti Moodle atau Canvas
4. **Konsultasi AI Pendidikan**: Layanan konsultasi implementasi AI assessment untuk institusi yang membutuhkan customization

---

# BAGIAN 18 — REFERENSI UNTUK PENULISAN ILMIAH

## 18.1 Teknologi untuk Referensi

| Teknologi | Citasi |
|---|---|
| MobileNetV2 | Sandler, M., et al. (2018). MobileNetV2: Inverted Residuals and Linear Bottlenecks. CVPR 2018 |
| DenseNet | Huang, G., et al. (2017). Densely Connected Convolutional Networks. CVPR 2017 |
| InceptionV3 | Szegedy, C., et al. (2016). Rethinking the Inception Architecture for Computer Vision. CVPR 2016 |
| FastAPI | Ramírez, S. (2018). FastAPI. https://fastapi.tiangolo.com |
| Next.js | Vercel (2016). Next.js Framework. https://nextjs.org |
| Supabase | Wilson, P. (2020). Supabase — The Open Source Firebase Alternative. https://supabase.com |
| TensorFlow | Abadi, M., et al. (2015). TensorFlow. Software available from tensorflow.org |
| OpenCV | Bradski, G. (2000). The OpenCV Library. Dr. Dobb's Journal of Software Tools |

## 18.2 Domain Penelitian untuk Referensi Lanjutan

- Automated Essay Scoring (AES)
- Handwritten Mathematical Expression Recognition (HMER)
- Optical Character Recognition for Mathematics (Math OCR)
- Convolutional Neural Networks for Document Classification
- Transfer Learning in Educational Assessment
- AI in Education Technology (AIEd)
- Formative Assessment Automation

---

# LAMPIRAN A — KONFIGURASI FILE

## A.1 Frontend `next.config.ts`
Konfigurasi Next.js minimal — tidak ada custom config yang signifikan selain default.

## A.2 Backend dependency locks (Key Dependencies)

```
fastapi==0.136.3
uvicorn==0.48.0
tensorflow==2.21.0
keras==3.12.2
opencv-python-headless==4.13.0.92
numpy==2.2.6
supabase==2.30.1
python-dotenv==1.2.2
pydantic==2.13.4
```

## A.3 Frontend `package.json` (Key Dependencies)

```json
{
  "next": "16.2.6",
  "react": "19.2.4",
  "@supabase/supabase-js": "^2.106.2",
  "tailwindcss": "^4",
  "lucide-react": "^1.16.0",
  "exceljs": "^4.4.0",
  "next-themes": "^0.4.6",
  "react-easy-crop": "^5.5.7"
}
```

---

# LAMPIRAN B — DAFTAR ENDPOINT API

| Method | Endpoint | Group | Deskripsi |
|---|---|---|---|
| GET | `/health` | System | Health check |
| GET | `/auth/check-email` | Auth | Cek email terdaftar |
| POST | `/predict/{id}` | AI | Prediksi AI manual |
| POST | `/submission/{id}/submit` | AI | Submit + auto-trigger AI |
| GET | `/prediction/{id}` | AI | Ambil hasil prediksi |
| GET | `/submission/{id}/results` | AI | Hasil prediksi (format dosen) |
| POST | `/submission/{id}/reviewed` | AI | Update status reviewed |
| POST | `/submission/{id}/finalize` | AI | Finalisasi nilai |
| GET | `/lecturer/class-summary` | Dosen | Statistik kelas |
| GET | `/lecturer/course/{id}/stats` | Dosen | Statistik course |
| GET | `/lecturer/course/{id}/students` | Dosen | Roster mahasiswa |
| GET | `/ai-models` | System | Info model AI |
| GET | `/model-info` | System | Cache info model |
| GET | `/cache-status` | System | Status lazy cache |
| GET | `/audit-models` | Debug | Audit semua model |
| GET | `/settings` | System | Baca semua settings |
| POST | `/settings` | System | Update settings |
| DELETE | `/admin/user/{id}` | Admin | Hapus user (cascade) |
| POST | `/admin/predictions/count` | Admin | Hitung prediksi |
| POST | `/admin/predictions/delete` | Admin | Hapus prediksi |
| POST | `/audit/log` | Audit | Tulis audit log |
| GET | `/audit/schema-check` | Audit | Cek schema audit_log |
| GET | `/audit/test` | Debug | Test audit logging |

---

*Dokumen ini merupakan Master Knowledge Base untuk proyek EMATHTOCO.*
*Dihasilkan dari analisis menyeluruh seluruh codebase pada: 16 Juni 2026*
*Dibuat untuk keperluan: CD4, CD5, CD6, Laporan Akhir, Tesis, Jurnal, Sidang*
