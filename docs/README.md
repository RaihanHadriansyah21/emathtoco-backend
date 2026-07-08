# Backend Documentation

Dokumen backend aktif tidak lagi disimpan sebagai knowledge base besar di folder ini.

Gunakan folder berikut sebagai single source of truth:

- `D:\PTA\Emathtoco_Project\Emathtoco_AgentDocs\README.md`
- `D:\PTA\Emathtoco_Project\Emathtoco_AgentDocs\Brain\INDEX.md`
- `D:\PTA\Emathtoco_Project\Emathtoco_AgentDocs\Brain\BACKEND.md`
- `D:\PTA\Emathtoco_Project\Emathtoco_AgentDocs\Brain\API.md`
- `D:\PTA\Emathtoco_Project\Emathtoco_AgentDocs\Brain\AI_PIPELINE.md`

Alasan perubahan:

- knowledge base lama berisi arsitektur worker/auth/tunnel lama yang sudah tidak sesuai;
- dokumentasi aktif sekarang memakai arsitektur FastAPI + Redis/RQ + satu worker AI;
- project Supabase utama adalah `hkxxhactpwiqdzecrbxw`.

Folder ini hanya dipakai untuk catatan backend yang benar-benar spesifik repository, misalnya metodologi split dataset di `methodology/`.
