-- E-MATHTOCO cloud baseline.
-- This migration represents the schema that existed before the hardening
-- migrations. It is marked as applied on the existing cloud project and is
-- executed only when rebuilding a local database from scratch.

create table public.mata_kuliah (
  id uuid primary key default gen_random_uuid(),
  nama_matkul text not null,
  nama_dosen text not null,
  icon_name text,
  kode_matkul text,
  created_at timestamptz default now()
);

create table public.profil_pengguna (
  id uuid primary key references auth.users(id) on delete cascade,
  role text not null,
  nama_lengkap text not null,
  nim_nip text not null,
  kelas text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  foto_profil_url text
);

create table public.pengumpulan_tugas (
  id uuid primary key default gen_random_uuid(),
  mahasiswa_id uuid references public.profil_pengguna(id) on delete cascade,
  mata_kuliah_id uuid references public.mata_kuliah(id) on delete cascade,
  waktu_submit timestamptz default now(),
  status_penilaian text default 'menunggu_koreksi',
  model_ai_terpilih text,
  nilai_akhir real,
  status_submit text default 'draft',
  updated_at timestamptz default now(),
  created_at timestamptz default now(),
  model_ai text,
  ai_status varchar default 'pending',
  ai_processed_at timestamptz
);

create table public.lembar_jawaban (
  id uuid primary key default gen_random_uuid(),
  pengumpulan_tugas_id uuid not null
    references public.pengumpulan_tugas(id) on delete cascade,
  section_code text not null,
  image_url text not null,
  model_ai text,
  prediksi_ai real,
  nilai_dosen real,
  nilai_final real,
  feedback text,
  status text default 'uploaded',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  rejection_reason text,
  was_reuploaded boolean default false,
  last_reupload_at timestamptz,
  reupload_count integer default 0,
  constraint unique_section_per_submission
    unique (pengumpulan_tugas_id, section_code)
);

comment on column public.lembar_jawaban.rejection_reason is
  'Stores the lecturer rejection reason when a section requires re-upload. NULL when not rejected.';

create table public.dosen_mata_kuliah (
  id uuid primary key default gen_random_uuid(),
  dosen_id uuid not null references public.profil_pengguna(id) on delete cascade,
  mata_kuliah_id uuid not null references public.mata_kuliah(id) on delete cascade,
  created_at timestamptz default now()
);

create table public.mahasiswa_mata_kuliah (
  id uuid primary key default gen_random_uuid(),
  mahasiswa_id uuid not null references public.profil_pengguna(id) on delete cascade,
  mata_kuliah_id uuid not null references public.mata_kuliah(id) on delete cascade,
  created_at timestamptz default now()
);

create table public.ai_models (
  id uuid primary key default gen_random_uuid(),
  model_name text not null,
  technology text not null,
  section_code text,
  version text,
  status text default 'inactive',
  file_path text,
  created_at timestamptz default now()
);

create table public.audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid,
  actor_role text,
  action_type text,
  target_type text,
  target_id text,
  description text,
  created_at timestamptz default now(),
  user_id uuid,
  user_name text,
  role text,
  action text,
  target text,
  detail jsonb
);

create table public.system_settings (
  id uuid primary key default gen_random_uuid(),
  setting_key text unique,
  setting_value text,
  updated_at timestamptz default now()
);

create table public.hasil_prediksi (
  id uuid primary key default gen_random_uuid(),
  pengumpulan_tugas_id uuid not null
    references public.pengumpulan_tugas(id) on delete cascade,
  lembar_jawaban_id uuid references public.lembar_jawaban(id),
  section_code varchar not null,
  model_ai varchar not null,
  predicted_class integer not null,
  predicted_score integer not null,
  confidence double precision not null,
  status varchar default 'success',
  error_message text,
  created_at timestamptz default now(),
  constraint uq_hasil_prediksi_submission_section
    unique (pengumpulan_tugas_id, section_code)
);

create or replace function public.check_user_role(user_id uuid, target_role text)
returns boolean
language plpgsql
security definer
as $$
declare
  has_role boolean;
begin
  select exists (
    select 1
    from public.profil_pengguna
    where id = user_id and lower(role) = lower(target_role)
  ) into has_role;
  return has_role;
end;
$$;

create or replace function public.update_updated_at_column()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace function public.check_admin_deletion()
returns trigger
language plpgsql
as $$
begin
  if old.role = 'admin' then
    raise exception 'Deletion denied: Administrator accounts are protected and cannot be deleted.';
  end if;
  return old;
end;
$$;

create or replace function public.protect_primary_admin()
returns trigger
language plpgsql
as $$
begin
  if old.id = 'eb34d26b-76d9-4b9f-b43a-7f635bf2fc00'
     and new.role <> 'admin' then
    raise exception 'Primary administrator role cannot be changed';
  end if;
  return new;
end;
$$;

create or replace function public.prevent_primary_admin_delete()
returns trigger
language plpgsql
as $$
begin
  if old.id = 'eb34d26b-76d9-4b9f-b43a-7f635bf2fc00' then
    raise exception 'Primary administrator account cannot be deleted';
  end if;
  return old;
end;
$$;

create trigger update_pengumpulan_updated_at
before update on public.pengumpulan_tugas
for each row execute function public.update_updated_at_column();

create trigger update_lembar_updated_at
before update on public.lembar_jawaban
for each row execute function public.update_updated_at_column();

create trigger protect_admin_delete
before delete on public.profil_pengguna
for each row execute function public.check_admin_deletion();

create trigger protect_primary_admin_delete
before delete on public.profil_pengguna
for each row execute function public.prevent_primary_admin_delete();

create trigger protect_primary_admin_role
before update on public.profil_pengguna
for each row execute function public.protect_primary_admin();

create index idx_audit_log_action on public.audit_log(action);
create index idx_audit_log_action_created on public.audit_log(action, created_at desc);
create index idx_audit_log_action_type on public.audit_log(action_type);
create index idx_audit_log_actor_role on public.audit_log(actor_role);
create index idx_audit_log_created_at on public.audit_log(created_at desc);
create index idx_audit_log_created_at_legacy on public.audit_log(created_at desc);
create index idx_audit_log_role on public.audit_log(role);
create index idx_audit_log_user_id on public.audit_log(user_id);
create index idx_hasil_prediksi_submission
  on public.hasil_prediksi(pengumpulan_tugas_id);
create index idx_lembar_jawaban_pengumpulan_tugas_id
  on public.lembar_jawaban(pengumpulan_tugas_id);
create index idx_lembar_pengumpulan
  on public.lembar_jawaban(pengumpulan_tugas_id);
create index idx_lembar_section on public.lembar_jawaban(section_code);
create index idx_pengumpulan_mahasiswa
  on public.pengumpulan_tugas(mahasiswa_id);
create index idx_pengumpulan_matkul
  on public.pengumpulan_tugas(mata_kuliah_id);
create index idx_pengumpulan_tugas_mahasiswa_id
  on public.pengumpulan_tugas(mahasiswa_id);
create index idx_pengumpulan_tugas_mata_kuliah_id
  on public.pengumpulan_tugas(mata_kuliah_id);
create index idx_pengumpulan_tugas_status_submit
  on public.pengumpulan_tugas(status_submit);

alter table public.mata_kuliah enable row level security;
alter table public.profil_pengguna enable row level security;
alter table public.pengumpulan_tugas enable row level security;
alter table public.lembar_jawaban enable row level security;
alter table public.dosen_mata_kuliah enable row level security;
alter table public.mahasiswa_mata_kuliah enable row level security;
alter table public.ai_models enable row level security;
alter table public.audit_log enable row level security;
alter table public.system_settings enable row level security;
alter table public.hasil_prediksi enable row level security;

-- The final hardening migration replaces all baseline policies atomically.
-- These permissive policies are retained here so a local rebuild accurately
-- models the pre-hardening exposure.
create policy baseline_profile_read on public.profil_pengguna
for select to authenticated using (true);
create policy baseline_profile_insert on public.profil_pengguna
for insert to authenticated with check ((select auth.uid()) = id);
create policy baseline_profile_update on public.profil_pengguna
for update to authenticated using ((select auth.uid()) = id);

create policy baseline_course_read on public.mata_kuliah
for select to authenticated using (true);
create policy baseline_enrollment_read on public.mahasiswa_mata_kuliah
for select to authenticated using (true);
create policy baseline_assignment_read on public.dosen_mata_kuliah
for select to authenticated using (true);

create policy baseline_submission_read on public.pengumpulan_tugas
for select to authenticated using (true);
create policy baseline_submission_insert on public.pengumpulan_tugas
for insert to authenticated with check ((select auth.uid()) = mahasiswa_id);
create policy baseline_submission_update on public.pengumpulan_tugas
for update to authenticated using (true);

create policy baseline_sheet_read on public.lembar_jawaban
for select to authenticated using (true);
create policy baseline_sheet_write on public.lembar_jawaban
for all to authenticated using (true) with check (true);

create policy baseline_prediction_read on public.hasil_prediksi
for select to authenticated using (true);
create policy baseline_audit_read on public.audit_log
for select to authenticated using (true);

grant usage on schema public to anon, authenticated, service_role;
grant all on all tables in schema public to anon, authenticated, service_role;
grant all on all functions in schema public to anon, authenticated, service_role;
