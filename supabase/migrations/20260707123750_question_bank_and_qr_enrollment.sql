-- Bank soal privat dan QR enrollment untuk demo sidang E-MATHTOCO.
--
-- Scope terkunci:
-- - Format soal tetap 4 soal x 6 bagian = 24 section (S-1A sampai S-4F).
-- - Format jumlah soal/section lain disiapkan sebagai backlog, bukan diaktifkan.
-- - Soal hanya dapat dibaca/dikelola admin atau dosen pengampu mata kuliah.
-- - Mahasiswa tidak mendapatkan akses ke bank soal.

drop function if exists public.publish_question_set(uuid);
drop function if exists public.create_class_join_session(uuid, text, timestamptz, integer);
drop function if exists public.revoke_class_join_session(uuid);
drop function if exists public.join_class_with_token(text);
drop function if exists public.remove_student_from_course(uuid, uuid, boolean);

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'question-assets',
  'question-assets',
  false,
  2097152,
  array['image/jpeg', 'image/png', 'image/webp']::text[]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create table if not exists public.question_sets (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references public.mata_kuliah(id) on delete cascade,
  title text not null,
  academic_year text,
  semester text,
  status text not null default 'draft',
  format_version text not null default 'fixed_4x6_v1',
  created_by uuid references public.profil_pengguna(id) on delete set null,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint question_sets_status_check
    check (status in ('draft', 'published', 'archived')),
  constraint question_sets_format_check
    check (format_version = 'fixed_4x6_v1'),
  constraint question_sets_course_title_unique
    unique (course_id, title)
);

create unique index if not exists question_sets_one_published_per_course
on public.question_sets(course_id)
where status = 'published';

create table if not exists public.question_sections (
  id uuid primary key default gen_random_uuid(),
  question_set_id uuid not null references public.question_sets(id) on delete cascade,
  section_code text not null,
  question_number smallint not null,
  part_label text not null,
  parent_prompt text not null default '',
  question_text text not null default '',
  helper_text text,
  max_score smallint not null,
  sort_order smallint not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint question_sections_code_check check (
    section_code in (
      'S-1A','S-1B','S-1C','S-1D','S-1E','S-1F',
      'S-2A','S-2B','S-2C','S-2D','S-2E','S-2F',
      'S-3A','S-3B','S-3C','S-3D','S-3E','S-3F',
      'S-4A','S-4B','S-4C','S-4D','S-4E','S-4F'
    )
  ),
  constraint question_sections_number_check check (question_number between 1 and 4),
  constraint question_sections_part_check check (part_label in ('A','B','C','D','E','F')),
  constraint question_sections_score_check check (
    (part_label <> 'F' and max_score = 4)
    or (part_label = 'F' and max_score = 5)
  ),
  constraint question_sections_sort_order_check check (sort_order between 1 and 24),
  constraint question_sections_code_matches_parts check (
    section_code = ('S-' || question_number::text || part_label)
  ),
  constraint question_sections_set_code_unique unique (question_set_id, section_code),
  constraint question_sections_set_sort_unique unique (question_set_id, sort_order)
);

create table if not exists public.question_assets (
  id uuid primary key default gen_random_uuid(),
  question_set_id uuid not null references public.question_sets(id) on delete cascade,
  section_code text not null,
  file_path text not null,
  mime_type text not null,
  byte_size integer not null,
  width integer,
  height integer,
  caption text,
  uploaded_by uuid references public.profil_pengguna(id) on delete set null,
  created_at timestamptz not null default now(),
  constraint question_assets_section_fk
    foreign key (question_set_id, section_code)
    references public.question_sections(question_set_id, section_code)
    on delete cascade,
  constraint question_assets_mime_check
    check (mime_type in ('image/jpeg', 'image/png', 'image/webp')),
  constraint question_assets_size_check
    check (byte_size > 0 and byte_size <= 2097152),
  constraint question_assets_dimensions_check
    check (
      (width is null or (width > 0 and width <= 2000))
      and (height is null or (height > 0 and height <= 2000))
    ),
  constraint question_assets_path_unique unique (file_path)
);

create table if not exists public.class_join_sessions (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references public.mata_kuliah(id) on delete cascade,
  created_by uuid not null references public.profil_pengguna(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  max_uses integer,
  used_count integer not null default 0,
  created_at timestamptz not null default now(),
  constraint class_join_sessions_hash_check check (token_hash ~ '^[a-f0-9]{64}$'),
  constraint class_join_sessions_expiry_check check (
    expires_at > created_at and expires_at <= created_at + interval '24 hours'
  ),
  constraint class_join_sessions_uses_check check (
    max_uses is null or max_uses between 1 and 500
  ),
  constraint class_join_sessions_used_check check (used_count >= 0)
);

create index if not exists class_join_sessions_course_idx
on public.class_join_sessions(course_id, expires_at desc);

create table if not exists public.class_join_logs (
  id uuid primary key default gen_random_uuid(),
  join_session_id uuid not null references public.class_join_sessions(id) on delete cascade,
  course_id uuid not null references public.mata_kuliah(id) on delete cascade,
  student_id uuid not null references public.profil_pengguna(id) on delete cascade,
  joined_at timestamptz not null default now(),
  detail jsonb not null default '{}'::jsonb,
  constraint class_join_logs_once_per_session unique (join_session_id, student_id)
);

create index if not exists question_sets_course_status_idx
on public.question_sets(course_id, status);
create index if not exists question_sections_set_order_idx
on public.question_sections(question_set_id, sort_order);
create index if not exists question_assets_set_section_idx
on public.question_assets(question_set_id, section_code);
create index if not exists class_join_logs_course_student_idx
on public.class_join_logs(course_id, student_id);

alter table public.question_sets enable row level security;
alter table public.question_sections enable row level security;
alter table public.question_assets enable row level security;
alter table public.class_join_sessions enable row level security;
alter table public.class_join_logs enable row level security;

drop policy if exists question_sets_select_manager on public.question_sets;
drop policy if exists question_sets_insert_manager on public.question_sets;
drop policy if exists question_sets_update_manager on public.question_sets;
drop policy if exists question_sets_delete_manager on public.question_sets;
drop policy if exists question_sections_select_manager on public.question_sections;
drop policy if exists question_sections_insert_manager on public.question_sections;
drop policy if exists question_sections_update_manager on public.question_sections;
drop policy if exists question_sections_delete_manager on public.question_sections;
drop policy if exists question_assets_select_manager on public.question_assets;
drop policy if exists question_assets_insert_manager on public.question_assets;
drop policy if exists question_assets_update_manager on public.question_assets;
drop policy if exists question_assets_delete_manager on public.question_assets;
drop policy if exists class_join_sessions_select_manager on public.class_join_sessions;
drop policy if exists class_join_sessions_insert_manager on public.class_join_sessions;
drop policy if exists class_join_sessions_update_manager on public.class_join_sessions;
drop policy if exists class_join_logs_select_manager_or_self on public.class_join_logs;
drop policy if exists question_asset_object_select_manager on storage.objects;
drop policy if exists question_asset_object_insert_manager on storage.objects;
drop policy if exists question_asset_object_delete_manager on storage.objects;

create or replace function app_private.can_manage_question_set(p_question_set_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.question_sets as question_set
    where question_set.id = p_question_set_id
      and (
        app_private.is_admin()
        or app_private.is_lecturer_for_course(question_set.course_id)
      )
  )
$$;

create or replace function app_private.can_manage_question_asset_path(p_path text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select
    array_length(storage.foldername(p_path), 1) >= 3
    and (
      app_private.is_admin()
      or app_private.is_lecturer_for_course(
        app_private.uuid_or_null((storage.foldername(p_path))[1])
      )
    )
    and (storage.foldername(p_path))[3] in (
      'S-1A','S-1B','S-1C','S-1D','S-1E','S-1F',
      'S-2A','S-2B','S-2C','S-2D','S-2E','S-2F',
      'S-3A','S-3B','S-3C','S-3D','S-3E','S-3F',
      'S-4A','S-4B','S-4C','S-4D','S-4E','S-4F'
    )
$$;

revoke all on function app_private.can_manage_question_set(uuid) from public, anon;
revoke all on function app_private.can_manage_question_asset_path(text) from public, anon;
grant execute on function app_private.can_manage_question_set(uuid) to authenticated, service_role;
grant execute on function app_private.can_manage_question_asset_path(text) to authenticated, service_role;

create policy question_sets_select_manager
on public.question_sets
for select to authenticated
using (app_private.is_admin() or app_private.is_lecturer_for_course(course_id));

create policy question_sets_insert_manager
on public.question_sets
for insert to authenticated
with check (
  app_private.is_admin()
  or app_private.is_lecturer_for_course(course_id)
);

create policy question_sets_update_manager
on public.question_sets
for update to authenticated
using (app_private.is_admin() or app_private.is_lecturer_for_course(course_id))
with check (app_private.is_admin() or app_private.is_lecturer_for_course(course_id));

create policy question_sets_delete_manager
on public.question_sets
for delete to authenticated
using (app_private.is_admin() or app_private.is_lecturer_for_course(course_id));

create policy question_sections_select_manager
on public.question_sections
for select to authenticated
using (app_private.can_manage_question_set(question_set_id));

create policy question_sections_insert_manager
on public.question_sections
for insert to authenticated
with check (app_private.can_manage_question_set(question_set_id));

create policy question_sections_update_manager
on public.question_sections
for update to authenticated
using (app_private.can_manage_question_set(question_set_id))
with check (app_private.can_manage_question_set(question_set_id));

create policy question_sections_delete_manager
on public.question_sections
for delete to authenticated
using (app_private.can_manage_question_set(question_set_id));

create policy question_assets_select_manager
on public.question_assets
for select to authenticated
using (app_private.can_manage_question_set(question_set_id));

create policy question_assets_insert_manager
on public.question_assets
for insert to authenticated
with check (app_private.can_manage_question_set(question_set_id));

create policy question_assets_update_manager
on public.question_assets
for update to authenticated
using (app_private.can_manage_question_set(question_set_id))
with check (app_private.can_manage_question_set(question_set_id));

create policy question_assets_delete_manager
on public.question_assets
for delete to authenticated
using (app_private.can_manage_question_set(question_set_id));

create policy class_join_sessions_select_manager
on public.class_join_sessions
for select to authenticated
using (
  app_private.is_admin()
  or app_private.is_lecturer_for_course(course_id)
);

create policy class_join_sessions_insert_manager
on public.class_join_sessions
for insert to authenticated
with check (
  created_by = (select auth.uid())
  and (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(course_id)
  )
);

create policy class_join_sessions_update_manager
on public.class_join_sessions
for update to authenticated
using (
  app_private.is_admin()
  or app_private.is_lecturer_for_course(course_id)
)
with check (
  app_private.is_admin()
  or app_private.is_lecturer_for_course(course_id)
);

create policy class_join_logs_select_manager_or_self
on public.class_join_logs
for select to authenticated
using (
  student_id = (select auth.uid())
  or app_private.is_admin()
  or app_private.is_lecturer_for_course(course_id)
);

create policy question_asset_object_select_manager
on storage.objects
for select to authenticated
using (
  bucket_id = 'question-assets'
  and app_private.can_manage_question_asset_path(name)
);

create policy question_asset_object_insert_manager
on storage.objects
for insert to authenticated
with check (
  bucket_id = 'question-assets'
  and app_private.can_manage_question_asset_path(name)
);

create policy question_asset_object_delete_manager
on storage.objects
for delete to authenticated
using (
  bucket_id = 'question-assets'
  and app_private.can_manage_question_asset_path(name)
);

grant select, insert, update, delete on
  public.question_sets,
  public.question_sections,
  public.question_assets,
  public.class_join_sessions,
  public.class_join_logs
to authenticated;

grant all on
  public.question_sets,
  public.question_sections,
  public.question_assets,
  public.class_join_sessions,
  public.class_join_logs
to service_role;

create or replace function public.publish_question_set(
  p_question_set_id uuid
)
returns public.question_sets
language plpgsql
security definer
set search_path = ''
as $$
declare
  question_set_row public.question_sets%rowtype;
  section_count integer;
begin
  select *
  into question_set_row
  from public.question_sets
  where id = p_question_set_id
  for update;

  if not found then
    raise exception 'QUESTION_SET_NOT_FOUND';
  end if;

  if not (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(question_set_row.course_id)
  ) then
    raise exception 'FORBIDDEN';
  end if;

  select count(*)
  into section_count
  from public.question_sections
  where question_set_id = p_question_set_id;

  if section_count <> 24 then
    raise exception 'QUESTION_SET_REQUIRES_24_SECTIONS';
  end if;

  update public.question_sets
  set
    status = 'archived',
    updated_at = now()
  where course_id = question_set_row.course_id
    and status = 'published'
    and id <> p_question_set_id;

  update public.question_sets
  set
    status = 'published',
    published_at = coalesce(published_at, now()),
    updated_at = now()
  where id = p_question_set_id
  returning * into question_set_row;

  return question_set_row;
end;
$$;

create or replace function public.create_class_join_session(
  p_course_id uuid,
  p_token_hash text,
  p_expires_at timestamptz,
  p_max_uses integer default null
)
returns public.class_join_sessions
language plpgsql
security definer
set search_path = ''
as $$
declare
  created_row public.class_join_sessions%rowtype;
begin
  if not (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(p_course_id)
  ) then
    raise exception 'FORBIDDEN';
  end if;

  if p_token_hash !~ '^[a-f0-9]{64}$' then
    raise exception 'INVALID_TOKEN_HASH';
  end if;

  if p_expires_at <= now()
     or p_expires_at > now() + interval '24 hours' then
    raise exception 'INVALID_EXPIRY';
  end if;

  if p_max_uses is not null and (p_max_uses < 1 or p_max_uses > 500) then
    raise exception 'INVALID_MAX_USES';
  end if;

  insert into public.class_join_sessions (
    course_id,
    created_by,
    token_hash,
    expires_at,
    max_uses
  )
  values (
    p_course_id,
    (select auth.uid()),
    p_token_hash,
    p_expires_at,
    p_max_uses
  )
  returning * into created_row;

  return created_row;
end;
$$;

create or replace function public.revoke_class_join_session(
  p_join_session_id uuid
)
returns public.class_join_sessions
language plpgsql
security definer
set search_path = ''
as $$
declare
  session_row public.class_join_sessions%rowtype;
begin
  select *
  into session_row
  from public.class_join_sessions
  where id = p_join_session_id
  for update;

  if not found then
    raise exception 'JOIN_SESSION_NOT_FOUND';
  end if;

  if not (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(session_row.course_id)
  ) then
    raise exception 'FORBIDDEN';
  end if;

  update public.class_join_sessions
  set revoked_at = coalesce(revoked_at, now())
  where id = p_join_session_id
  returning * into session_row;

  return session_row;
end;
$$;

create or replace function public.join_class_with_token(
  p_token_hash text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  session_row public.class_join_sessions%rowtype;
  student_role text;
  enrollment_id uuid;
  already_enrolled boolean := false;
begin
  student_role := app_private.current_role();

  if student_role <> 'mahasiswa' then
    raise exception 'ONLY_STUDENTS_CAN_JOIN';
  end if;

  if p_token_hash !~ '^[a-f0-9]{64}$' then
    raise exception 'INVALID_TOKEN';
  end if;

  select *
  into session_row
  from public.class_join_sessions
  where token_hash = p_token_hash
    and revoked_at is null
    and expires_at > now()
  for update;

  if not found then
    raise exception 'JOIN_TOKEN_EXPIRED_OR_INVALID';
  end if;

  if session_row.max_uses is not null
     and session_row.used_count >= session_row.max_uses then
    raise exception 'JOIN_TOKEN_LIMIT_REACHED';
  end if;

  select exists (
    select 1
    from public.mahasiswa_mata_kuliah
    where mahasiswa_id = (select auth.uid())
      and mata_kuliah_id = session_row.course_id
  )
  into already_enrolled;

  if already_enrolled then
    select id
    into enrollment_id
    from public.mahasiswa_mata_kuliah
    where mahasiswa_id = (select auth.uid())
      and mata_kuliah_id = session_row.course_id
    limit 1;
  else
    insert into public.mahasiswa_mata_kuliah (
      mahasiswa_id,
      mata_kuliah_id
    )
    values (
      (select auth.uid()),
      session_row.course_id
    )
    returning id into enrollment_id;

    update public.class_join_sessions
    set used_count = used_count + 1
    where id = session_row.id;
  end if;

  insert into public.class_join_logs (
    join_session_id,
    course_id,
    student_id,
    detail
  )
  values (
    session_row.id,
    session_row.course_id,
    (select auth.uid()),
    jsonb_build_object('source', 'qr_join')
  )
  on conflict (join_session_id, student_id) do nothing;

  return jsonb_build_object(
    'success', true,
    'course_id', session_row.course_id,
    'enrollment_id', enrollment_id
  );
end;
$$;

create or replace function public.remove_student_from_course(
  p_student_id uuid,
  p_course_id uuid,
  p_delete_submissions boolean default true
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  deleted_enrollments integer := 0;
  deleted_submissions integer := 0;
begin
  if not (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(p_course_id)
  ) then
    raise exception 'FORBIDDEN';
  end if;

  if p_delete_submissions then
    delete from public.pengumpulan_tugas
    where mahasiswa_id = p_student_id
      and mata_kuliah_id = p_course_id;
    get diagnostics deleted_submissions = row_count;
  end if;

  delete from public.mahasiswa_mata_kuliah
  where mahasiswa_id = p_student_id
    and mata_kuliah_id = p_course_id;
  get diagnostics deleted_enrollments = row_count;

  return jsonb_build_object(
    'success', true,
    'enrollments_deleted', deleted_enrollments,
    'submissions_deleted', deleted_submissions
  );
end;
$$;

revoke all on function public.publish_question_set(uuid) from public, anon;
revoke all on function public.create_class_join_session(uuid, text, timestamptz, integer) from public, anon;
revoke all on function public.revoke_class_join_session(uuid) from public, anon;
revoke all on function public.join_class_with_token(text) from public, anon;
revoke all on function public.remove_student_from_course(uuid, uuid, boolean) from public, anon;
grant execute on function public.publish_question_set(uuid) to authenticated, service_role;
grant execute on function public.create_class_join_session(uuid, text, timestamptz, integer) to authenticated, service_role;
grant execute on function public.revoke_class_join_session(uuid) to authenticated, service_role;
grant execute on function public.join_class_with_token(text) to authenticated, service_role;
grant execute on function public.remove_student_from_course(uuid, uuid, boolean) to authenticated, service_role;

-- Seed paket soal UTS Steganografi dan Watermarking dari dokumen Word pengguna.
-- Seed hanya berjalan bila course AAK4IBB3 sudah ada.
update public.question_sets
set
  status = 'archived',
  updated_at = now()
where course_id in (
    select id
    from public.mata_kuliah
    where kode_matkul = 'AAK4IBB3'
  )
  and status = 'published'
  and title <> 'UTS Steganografi-Watermarking 2526 Genap';

with target_courses as (
  select id
  from public.mata_kuliah
  where kode_matkul = 'AAK4IBB3'
),
existing_sets as (
  select distinct on (question_sets.course_id)
    question_sets.id,
    question_sets.course_id
  from public.question_sets
  join target_courses on target_courses.id = question_sets.course_id
  where question_sets.title = 'UTS Steganografi-Watermarking 2526 Genap'
  order by question_sets.course_id, question_sets.created_at, question_sets.id
),
updated_sets as (
  update public.question_sets
  set
    academic_year = '2025/2026',
    semester = 'Genap',
    status = 'published',
    format_version = 'fixed_4x6_v1',
    published_at = coalesce(public.question_sets.published_at, now()),
    updated_at = now()
  where id in (select id from existing_sets)
  returning id, course_id
),
inserted_sets as (
  insert into public.question_sets (
    course_id,
    title,
    academic_year,
    semester,
    status,
    format_version,
    created_by,
    published_at
  )
  select
    target_courses.id,
    'UTS Steganografi-Watermarking 2526 Genap',
    '2025/2026',
    'Genap',
    'published',
    'fixed_4x6_v1',
    null,
    now()
  from target_courses
  where not exists (
    select 1
    from existing_sets
    where existing_sets.course_id = target_courses.id
  )
  returning id, course_id
),
seeded_sets as (
  select id, course_id from updated_sets
  union all
  select id, course_id from inserted_sets
),
removed_duplicate_sets as (
  delete from public.question_sets
  where course_id in (select id from target_courses)
    and title = 'UTS Steganografi-Watermarking 2526 Genap'
    and id not in (select id from seeded_sets)
  returning id
),
cleared_sections as (
  delete from public.question_sections
  where question_set_id in (select id from seeded_sets)
  returning id
),
seed_rows(section_code, question_number, part_label, parent_prompt, question_text, helper_text, max_score, sort_order) as (
  values
    ('S-1A', 1, 'A',
     'Essay. Jawab pertanyaan dengan tepat dan jelas pada kotak kosong yang telah disediakan di halaman jawaban.' || E'\n\n' ||
     'Jawablah pertanyaan konsep penyembunyian informasi berikut [Nilai: 25].',
     'Mengapa watermarking diperlukan?', null, 4, 1),
    ('S-1B', 1, 'B',
     'Essay. Jawab pertanyaan dengan tepat dan jelas pada kotak kosong yang telah disediakan di halaman jawaban.' || E'\n\n' ||
     'Jawablah pertanyaan konsep penyembunyian informasi berikut [Nilai: 25].',
     'Mengapa steganografi diperlukan?', null, 4, 2),
    ('S-1C', 1, 'C',
     'Essay. Jawab pertanyaan dengan tepat dan jelas pada kotak kosong yang telah disediakan di halaman jawaban.' || E'\n\n' ||
     'Jawablah pertanyaan konsep penyembunyian informasi berikut [Nilai: 25].',
     'Parameter kinerja apa yang paling penting pada watermarking? Dan jelaskan mengapa?', null, 4, 3),
    ('S-1D', 1, 'D',
     'Essay. Jawab pertanyaan dengan tepat dan jelas pada kotak kosong yang telah disediakan di halaman jawaban.' || E'\n\n' ||
     'Jawablah pertanyaan konsep penyembunyian informasi berikut [Nilai: 25].',
     'Parameter kinerja apa yang paling penting pada steganografi? Dan jelaskan mengapa?', null, 4, 4),
    ('S-1E', 1, 'E',
     'Essay. Jawab pertanyaan dengan tepat dan jelas pada kotak kosong yang telah disediakan di halaman jawaban.' || E'\n\n' ||
     'Jawablah pertanyaan konsep penyembunyian informasi berikut [Nilai: 25].',
     'Jelaskan gambar di atas ini apa relevansinya dengan mata kuliah ini?', 'Gambar diagram watermarking ditampilkan sebagai aset pendukung section ini.', 4, 5),
    ('S-1F', 1, 'F',
     'Essay. Jawab pertanyaan dengan tepat dan jelas pada kotak kosong yang telah disediakan di halaman jawaban.' || E'\n\n' ||
     'Jawablah pertanyaan konsep penyembunyian informasi berikut [Nilai: 25].',
     'Apa yang dimaksud dynamic masking pada domain frekuensi? Penjelasan akan lebih baik jika ditambahkan dengan ilustrasi/gambar.', null, 5, 6),

    ('S-2A', 2, 'A',
     'Diketahui suatu sinyal audio X = [1/9 1 4/9 0 1 1].' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Menggunakan metode SMM [Nilai: 25].',
     'Hitunglah audio terwatermark Xw di segmen 1 atau Xw1!', null, 4, 7),
    ('S-2B', 2, 'B',
     'Diketahui suatu sinyal audio X = [1/9 1 4/9 0 1 1].' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Menggunakan metode SMM [Nilai: 25].',
     'Hitunglah audio terwatermark Xw di segmen 2 atau Xw2!', null, 4, 8),
    ('S-2C', 2, 'C',
     'Diketahui suatu sinyal audio X = [1/9 1 4/9 0 1 1].' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Menggunakan metode SMM [Nilai: 25].',
     'Hitunglah audio terwatermark Xn untuk kedua segmen, dimana Xn = Xw + N, N merupakan noise DC sebesar 0.1 volt.', null, 4, 9),
    ('S-2D', 2, 'D',
     'Diketahui suatu sinyal audio X = [1/9 1 4/9 0 1 1].' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Menggunakan metode SMM [Nilai: 25].',
     'Hitunglah hasil ekstraksi watermark dari Xw untuk kedua segmen dan hitung BER!', null, 4, 10),
    ('S-2E', 2, 'E',
     'Diketahui suatu sinyal audio X = [1/9 1 4/9 0 1 1].' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Menggunakan metode SMM [Nilai: 25].',
     'Hitunglah hasil ekstraksi watermark dari Xn untuk kedua segmen dan hitung BER!', null, 4, 11),
    ('S-2F', 2, 'F',
     'Diketahui suatu sinyal audio X = [1/9 1 4/9 0 1 1].' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Menggunakan metode SMM [Nilai: 25].',
     'Hitunglah berapa payload atau kapasitas watermark dalam bps jika frekuensi sampling audio = 44.1 kHz!', null, 5, 12),

    ('S-3A', 3, 'A',
     'X seperti soal no. 2.' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Kode PN acak adalah [1 -1 1].' || E'\n' ||
     'Menggunakan metode SS [Nilai: 25].',
     'Hitunglah audio terwatermark Xw di segmen 1 atau Xw1!', null, 4, 13),
    ('S-3B', 3, 'B',
     'X seperti soal no. 2.' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Kode PN acak adalah [1 -1 1].' || E'\n' ||
     'Menggunakan metode SS [Nilai: 25].',
     'Hitunglah audio terwatermark Xw di segmen 2 atau Xw2!', null, 4, 14),
    ('S-3C', 3, 'C',
     'X seperti soal no. 2.' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Kode PN acak adalah [1 -1 1].' || E'\n' ||
     'Menggunakan metode SS [Nilai: 25].',
     'Hitunglah audio terwatermark Xn untuk kedua segmen, dimana Xn = Xw + N, N merupakan noise DC sebesar -0.1 volt.', null, 4, 15),
    ('S-3D', 3, 'D',
     'X seperti soal no. 2.' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Kode PN acak adalah [1 -1 1].' || E'\n' ||
     'Menggunakan metode SS [Nilai: 25].',
     'Hitunglah hasil ekstraksi watermark dari Xw untuk kedua segmen dan hitung BER!', null, 4, 16),
    ('S-3E', 3, 'E',
     'X seperti soal no. 2.' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Kode PN acak adalah [1 -1 1].' || E'\n' ||
     'Menggunakan metode SS [Nilai: 25].',
     'Hitunglah hasil ekstraksi watermark dari Xn untuk kedua segmen dan hitung BER!', null, 4, 17),
    ('S-3F', 3, 'F',
     'X seperti soal no. 2.' || E'\n' ||
     'Panjang segmen adalah 3 sampel/segmen.' || E'\n' ||
     'Penguat watermark α = 0.9.' || E'\n' ||
     'Bit yang disisipkan adalah w = [1 -1].' || E'\n' ||
     'Kode PN acak adalah [1 -1 1].' || E'\n' ||
     'Menggunakan metode SS [Nilai: 25].',
     'Hitunglah berapa payload atau kapasitas watermark dalam bps jika frekuensi sampling audio = 44.1 kHz!', null, 5, 18),

    ('S-4A', 4, 'A',
     'Diketahui suatu citra 2x4 berikut:' || E'\n\n' ||
     'X =' || E'\n' ||
     '[0  1  7  4' || E'\n' ||
     ' 3  6  9  1]' || E'\n\n' ||
     'Watermark yang akan disembunyikan dengan metode LSB adalah:' || E'\n\n' ||
     'w = [0 1 0 1 1 0 1 0]' || E'\n\n' ||
     '[Nilai: 25]',
     'Jika watermark disisipkan pada LSB ke-0, hitunglah Xw!', null, 4, 19),
    ('S-4B', 4, 'B',
     'Diketahui suatu citra 2x4 berikut:' || E'\n\n' ||
     'X =' || E'\n' ||
     '[0  1  7  4' || E'\n' ||
     ' 3  6  9  1]' || E'\n\n' ||
     'Watermark yang akan disembunyikan dengan metode LSB adalah:' || E'\n\n' ||
     'w = [0 1 0 1 1 0 1 0]' || E'\n\n' ||
     '[Nilai: 25]',
     'Dari soal A, hitunglah MSE dan PSNR!', null, 4, 20),
    ('S-4C', 4, 'C',
     'Diketahui suatu citra 2x4 berikut:' || E'\n\n' ||
     'X =' || E'\n' ||
     '[0  1  7  4' || E'\n' ||
     ' 3  6  9  1]' || E'\n\n' ||
     'Watermark yang akan disembunyikan dengan metode LSB adalah:' || E'\n\n' ||
     'w = [0 1 0 1 1 0 1 0]' || E'\n\n' ||
     '[Nilai: 25]',
     'Jika watermark disisipkan pada LSB ke-2, hitunglah Xw!', null, 4, 21),
    ('S-4D', 4, 'D',
     'Diketahui suatu citra 2x4 berikut:' || E'\n\n' ||
     'X =' || E'\n' ||
     '[0  1  7  4' || E'\n' ||
     ' 3  6  9  1]' || E'\n\n' ||
     'Watermark yang akan disembunyikan dengan metode LSB adalah:' || E'\n\n' ||
     'w = [0 1 0 1 1 0 1 0]' || E'\n\n' ||
     '[Nilai: 25]',
     'Dari soal C, hitunglah MSE dan PSNR!', null, 4, 22),
    ('S-4E', 4, 'E',
     'Diketahui suatu citra 2x4 berikut:' || E'\n\n' ||
     'X =' || E'\n' ||
     '[0  1  7  4' || E'\n' ||
     ' 3  6  9  1]' || E'\n\n' ||
     'Watermark yang akan disembunyikan dengan metode LSB adalah:' || E'\n\n' ||
     'w = [0 1 0 1 1 0 1 0]' || E'\n\n' ||
     '[Nilai: 25]',
     'Jika Xw dari soal C diserang noise berikut, hitunglah Xn, dimana Xn = Xw + N.',
     'N =' || E'\n' ||
     '[0  0  2  1' || E'\n' ||
     ' 1  0  0  2]',
     4, 23),
    ('S-4F', 4, 'F',
     'Diketahui suatu citra 2x4 berikut:' || E'\n\n' ||
     'X =' || E'\n' ||
     '[0  1  7  4' || E'\n' ||
     ' 3  6  9  1]' || E'\n\n' ||
     'Watermark yang akan disembunyikan dengan metode LSB adalah:' || E'\n\n' ||
     'w = [0 1 0 1 1 0 1 0]' || E'\n\n' ||
     '[Nilai: 25]',
     'Hitunglah BER hasil deteksi watermark terhadap Xn dari soal E!', null, 5, 24)
)
insert into public.question_sections (
  question_set_id,
  section_code,
  question_number,
  part_label,
  parent_prompt,
  question_text,
  helper_text,
  max_score,
  sort_order
)
select
  seeded_sets.id,
  seed_rows.section_code,
  seed_rows.question_number,
  seed_rows.part_label,
  seed_rows.parent_prompt,
  seed_rows.question_text,
  seed_rows.helper_text,
  seed_rows.max_score,
  seed_rows.sort_order
from seeded_sets
cross join seed_rows
cross join (
  select
    (select count(*) from cleared_sections) as deleted_section_count,
    (select count(*) from removed_duplicate_sets) as deleted_duplicate_set_count
) as cleared_summary;
