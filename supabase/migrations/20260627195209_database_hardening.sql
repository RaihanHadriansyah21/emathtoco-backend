-- E-MATHTOCO database hardening.
-- This migration is deliberately additive with respect to the business schema:
-- no business table, column, or relationship is renamed or removed.

create schema if not exists app_private;
revoke all on schema app_private from public, anon, authenticated;
grant usage on schema app_private to authenticated, service_role;

-- Compatibility for older E-MATHTOCO cloud snapshots that only have the
-- legacy audit columns. Keep both shapes because existing frontend reports
-- still read the legacy fields while trusted backend events use the new ones.
alter table public.audit_log
  add column if not exists actor_id uuid,
  add column if not exists actor_role text,
  add column if not exists action_type text,
  add column if not exists target_type text,
  add column if not exists target_id text,
  add column if not exists description text;

update public.audit_log
set
  actor_id = coalesce(actor_id, user_id),
  actor_role = coalesce(actor_role, role, 'system'),
  action_type = coalesce(action_type, action, 'HISTORICAL_EVENT'),
  target_type = coalesce(target_type, target, 'unknown'),
  target_id = coalesce(target_id, detail ->> 'target_id', detail ->> 'id'),
  description = coalesce(
    description,
    detail ->> 'description',
    action,
    'Historical audit event.'
  )
where actor_id is null
   or actor_role is null
   or action_type is null
   or target_type is null
   or description is null;

-- Remove every pre-hardening policy on application tables. Recreating a
-- complete matrix is safer than relying on historical policy names.
do $$
declare
  policy_row record;
begin
  for policy_row in
    select schemaname, tablename, policyname
    from pg_policies
    where schemaname = 'public'
      and tablename in (
        'profil_pengguna',
        'mata_kuliah',
        'mahasiswa_mata_kuliah',
        'dosen_mata_kuliah',
        'pengumpulan_tugas',
        'lembar_jawaban',
        'hasil_prediksi',
        'audit_log',
        'system_settings',
        'ai_models'
      )
  loop
    execute format(
      'drop policy if exists %I on %I.%I',
      policy_row.policyname,
      policy_row.schemaname,
      policy_row.tablename
    );
  end loop;

  for policy_row in
    select schemaname, tablename, policyname
    from pg_policies
    where schemaname = 'storage'
      and tablename = 'objects'
      and (
        coalesce(qual, '') like '%lembar-jawaban%'
        or coalesce(with_check, '') like '%lembar-jawaban%'
        or coalesce(qual, '') like '%profile-images%'
        or coalesce(with_check, '') like '%profile-images%'
      )
  loop
    execute format(
      'drop policy if exists %I on %I.%I',
      policy_row.policyname,
      policy_row.schemaname,
      policy_row.tablename
    );
  end loop;
end
$$;

drop trigger if exists protect_admin_delete on public.profil_pengguna;
drop trigger if exists protect_primary_admin_delete on public.profil_pengguna;
drop trigger if exists protect_primary_admin_role on public.profil_pengguna;
drop trigger if exists enforce_prevent_role_escalation on public.profil_pengguna;

drop function if exists public.check_email_exists(text);
drop function if exists public.check_user_role(uuid, text);
drop function if exists public.check_admin_deletion();
drop function if exists public.prevent_primary_admin_delete();
drop function if exists public.protect_primary_admin();
drop function if exists public.prevent_role_escalation();

create or replace function app_private.current_role()
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select lower(profile.role)
  from public.profil_pengguna as profile
  where profile.id = (select auth.uid())
$$;

create or replace function app_private.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce(app_private.current_role() = 'admin', false)
$$;

create or replace function app_private.is_lecturer_for_course(course_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select
    coalesce(app_private.current_role() = 'dosen', false)
    and exists (
      select 1
      from public.dosen_mata_kuliah as assignment
      where assignment.dosen_id = (select auth.uid())
        and assignment.mata_kuliah_id = course_id
    )
$$;

create or replace function app_private.owns_submission(submission_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.pengumpulan_tugas as submission
    where submission.id = submission_id
      and submission.mahasiswa_id = (select auth.uid())
  )
$$;

create or replace function app_private.can_access_submission(submission_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.pengumpulan_tugas as submission
    where submission.id = submission_id
      and (
        submission.mahasiswa_id = (select auth.uid())
        or app_private.is_admin()
        or app_private.is_lecturer_for_course(submission.mata_kuliah_id)
      )
  )
$$;

revoke all on all functions in schema app_private from public, anon;
grant execute on all functions in schema app_private to authenticated, service_role;

-- Normalize historical role casing before adding a strict domain constraint.
update public.profil_pengguna
set role = lower(role)
where role is distinct from lower(role);

-- Deterministically replace only duplicate identifiers after the oldest row.
-- No previous NIM/NIP value is copied into the audit event.
do $$
declare
  duplicate_row record;
  candidate bigint;
  candidate_text text;
begin
  for duplicate_row in
    select
      ranked.id,
      case
        when ranked.nim_nip is null
          or ranked.nim_nip !~ '^[0-9]+$'
        then 'invalid_identifier'
        else 'duplicate_identifier'
      end as correction_reason
    from (
      select
        profile.id,
        profile.nim_nip,
        row_number() over (
          partition by profile.nim_nip
          order by profile.created_at nulls last, profile.id
        ) as duplicate_rank
      from public.profil_pengguna as profile
    ) as ranked
    where ranked.duplicate_rank > 1
       or ranked.nim_nip is null
       or ranked.nim_nip !~ '^[0-9]+$'
    order by ranked.id
  loop
    candidate :=
      900000000000
      + mod(
          abs(hashtextextended(duplicate_row.id::text, 0)),
          99999999999
        );
    candidate_text := candidate::text;

    while exists (
      select 1
      from public.profil_pengguna
      where nim_nip = candidate_text
        and id <> duplicate_row.id
    )
    loop
      candidate := 900000000000
        + mod(candidate - 900000000000 + 1, 99999999999);
      candidate_text := candidate::text;
    end loop;

    update public.profil_pengguna
    set nim_nip = candidate_text
    where id = duplicate_row.id;

    insert into public.audit_log (
      actor_role,
      action_type,
      target_type,
      target_id,
      description,
      role,
      action,
      target,
      detail
    )
    values (
      'admin',
      'IDENTIFIER_DEDUPLICATED',
      'profil_pengguna',
      duplicate_row.id::text,
      'Duplicate identifier replaced with a deterministic placeholder.',
      'admin',
      'IDENTIFIER_DEDUPLICATED',
      'profil_pengguna',
      jsonb_build_object(
        'profile_id', duplicate_row.id,
        'reason', duplicate_row.correction_reason
      )
    );
  end loop;
end
$$;

-- Align legacy nullability and defaults with the versioned cloud baseline.
-- Existing data has already been checked before this migration is deployed.
alter table public.mata_kuliah
  alter column nama_matkul set not null,
  alter column nama_dosen set not null;

alter table public.profil_pengguna
  alter column nama_lengkap set not null,
  alter column role set not null,
  alter column nim_nip set not null;

alter table public.mahasiswa_mata_kuliah
  alter column mahasiswa_id set not null,
  alter column mata_kuliah_id set not null;

alter table public.dosen_mata_kuliah
  alter column dosen_id set not null,
  alter column mata_kuliah_id set not null;

alter table public.pengumpulan_tugas
  alter column mahasiswa_id set not null,
  alter column mata_kuliah_id set not null,
  alter column status_submit set default 'draft';

alter table public.lembar_jawaban
  alter column pengumpulan_tugas_id set not null,
  alter column section_code set not null,
  alter column image_url set not null,
  alter column status set default 'uploaded';

alter table public.hasil_prediksi
  alter column pengumpulan_tugas_id set not null,
  alter column lembar_jawaban_id set not null,
  alter column section_code set not null,
  alter column model_ai set not null,
  alter column predicted_class set not null,
  alter column predicted_score set not null,
  alter column confidence set not null;

alter table public.system_settings
  alter column setting_key set not null;

alter table public.profil_pengguna
  add constraint profil_pengguna_role_check
  check (role in ('admin', 'dosen', 'mahasiswa')),
  add constraint profil_pengguna_nim_nip_numeric_check
  check (nim_nip ~ '^[0-9]+$'),
  add constraint profil_pengguna_nim_nip_unique
  unique (nim_nip);

alter table public.mahasiswa_mata_kuliah
  add constraint mahasiswa_mata_kuliah_unique
  unique (mahasiswa_id, mata_kuliah_id);

alter table public.dosen_mata_kuliah
  add constraint dosen_mata_kuliah_unique
  unique (dosen_id, mata_kuliah_id);

-- The older cloud snapshot uses an equivalent constraint under this name.
alter table public.pengumpulan_tugas
  drop constraint if exists uq_pengumpulan_tugas_mahasiswa_mata_kuliah;

alter table public.pengumpulan_tugas
  add constraint pengumpulan_tugas_student_course_unique
  unique (mahasiswa_id, mata_kuliah_id),
  add constraint pengumpulan_tugas_status_submit_check
  check (
    status_submit in (
      'draft',
      'reupload_required',
      'submitted',
      'processing_ai',
      'reviewed',
      'finalized',
      'failed'
    )
  ),
  add constraint pengumpulan_tugas_ai_status_check
  check (
    ai_status in (
      'idle',
      'pending',
      'processing',
      'completed',
      'failed',
      'reviewed',
      'finalized'
    )
  ),
  add constraint pengumpulan_tugas_model_check
  check (
    model_ai is null
    or model_ai in ('MobileNetV2', 'DenseNet121', 'InceptionV3')
  ),
  add constraint pengumpulan_tugas_selected_model_check
  check (
    model_ai_terpilih is null
    or model_ai_terpilih in ('MobileNetV2', 'DenseNet121', 'InceptionV3')
  ),
  add constraint pengumpulan_tugas_score_check
  check (nilai_akhir is null or nilai_akhir between 0 and 100);

alter table public.lembar_jawaban
  add constraint lembar_jawaban_section_check
  check (section_code ~ '^S-[1-4][A-F]$'),
  add constraint lembar_jawaban_status_check
  check (
    status in (
      'uploaded',
      'draft',
      'submitted',
      'processing',
      'completed',
      'reviewed',
      'reupload_required',
      'finalized',
      'failed'
    )
  ),
  add constraint lembar_jawaban_model_check
  check (
    model_ai is null
    or model_ai in ('MobileNetV2', 'DenseNet121', 'InceptionV3')
  ),
  add constraint lembar_jawaban_scores_check
  check (
    (prediksi_ai is null or prediksi_ai between 0 and 5)
    and (nilai_dosen is null or nilai_dosen between 0 and 5)
    and (nilai_final is null or nilai_final between 0 and 5)
  ),
  add constraint lembar_jawaban_reupload_count_check
  check (reupload_count >= 0);

alter table public.hasil_prediksi
  add constraint hasil_prediksi_section_check
  check (section_code ~ '^S-[1-4][A-F]$'),
  add constraint hasil_prediksi_model_check
  check (model_ai in ('MobileNetV2', 'DenseNet121', 'InceptionV3')),
  add constraint hasil_prediksi_class_check
  check (predicted_class between 0 and 5),
  add constraint hasil_prediksi_score_check
  check (predicted_score between 0 and 5),
  add constraint hasil_prediksi_confidence_check
  check (confidence between 0 and 1),
  add constraint hasil_prediksi_status_check
  check (status in ('success', 'failed'));

-- Remove duplicate indexes and keep one index per access path.
drop index if exists public.idx_audit_log_created_at_legacy;
drop index if exists public.idx_lembar_pengumpulan;
drop index if exists public.idx_pengumpulan_mahasiswa;
drop index if exists public.idx_pengumpulan_matkul;

create index if not exists idx_mahasiswa_mata_kuliah_mahasiswa
  on public.mahasiswa_mata_kuliah(mahasiswa_id);
create index if not exists idx_mahasiswa_mata_kuliah_course
  on public.mahasiswa_mata_kuliah(mata_kuliah_id);
create index if not exists idx_dosen_mata_kuliah_dosen
  on public.dosen_mata_kuliah(dosen_id);
create index if not exists idx_dosen_mata_kuliah_course
  on public.dosen_mata_kuliah(mata_kuliah_id);
create index if not exists idx_hasil_prediksi_sheet
  on public.hasil_prediksi(lembar_jawaban_id);

create or replace function app_private.protect_profile_fields()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if (select auth.uid()) is not null
       and coalesce((select auth.role()), '') <> 'service_role'
       and (
         new.id <> (select auth.uid())
         or lower(new.role) <> 'mahasiswa'
       ) then
      raise exception using errcode = '42501', message = 'profile_insert_forbidden';
    end if;
    new.role := lower(new.role);
    return new;
  end if;

  if (select auth.uid()) is not null
     and coalesce((select auth.role()), '') <> 'service_role'
     and not app_private.is_admin()
     and (
       new.id is distinct from old.id
       or new.role is distinct from old.role
       or new.created_at is distinct from old.created_at
     ) then
    raise exception using errcode = '42501', message = 'protected_profile_field';
  end if;

  new.role := lower(new.role);
  return new;
end;
$$;

create trigger protect_profile_fields
before insert or update on public.profil_pengguna
for each row execute function app_private.protect_profile_fields();

create or replace function public.update_updated_at_column()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

revoke all on function public.update_updated_at_column() from public, anon, authenticated;

-- Complete RLS matrix.
create policy profile_select_own
on public.profil_pengguna
for select to authenticated
using ((select auth.uid()) = id);

create policy profile_select_admin
on public.profil_pengguna
for select to authenticated
using (app_private.is_admin());

create policy profile_select_assigned_student
on public.profil_pengguna
for select to authenticated
using (
  role = 'mahasiswa'
  and exists (
    select 1
    from public.mahasiswa_mata_kuliah as enrollment
    join public.dosen_mata_kuliah as assignment
      on assignment.mata_kuliah_id = enrollment.mata_kuliah_id
    where enrollment.mahasiswa_id = profil_pengguna.id
      and assignment.dosen_id = (select auth.uid())
  )
);

create policy profile_insert_student_self
on public.profil_pengguna
for insert to authenticated
with check (
  (select auth.uid()) = id
  and role = 'mahasiswa'
);

create policy profile_update_self
on public.profil_pengguna
for update to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

create policy profile_admin_update
on public.profil_pengguna
for update to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());

create policy profile_admin_delete
on public.profil_pengguna
for delete to authenticated
using (app_private.is_admin() and role <> 'admin');

create policy course_authenticated_select
on public.mata_kuliah
for select to authenticated
using (true);

create policy course_admin_insert
on public.mata_kuliah
for insert to authenticated
with check (app_private.is_admin());

create policy course_admin_update
on public.mata_kuliah
for update to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());

create policy course_admin_delete
on public.mata_kuliah
for delete to authenticated
using (app_private.is_admin());

create policy enrollment_select_own
on public.mahasiswa_mata_kuliah
for select to authenticated
using (mahasiswa_id = (select auth.uid()));

create policy enrollment_select_lecturer
on public.mahasiswa_mata_kuliah
for select to authenticated
using (app_private.is_lecturer_for_course(mata_kuliah_id));

create policy enrollment_admin_all
on public.mahasiswa_mata_kuliah
for all to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());

create policy assignment_select_own
on public.dosen_mata_kuliah
for select to authenticated
using (dosen_id = (select auth.uid()));

create policy assignment_admin_all
on public.dosen_mata_kuliah
for all to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());

create policy submission_select_owner
on public.pengumpulan_tugas
for select to authenticated
using (mahasiswa_id = (select auth.uid()));

create policy submission_select_lecturer
on public.pengumpulan_tugas
for select to authenticated
using (app_private.is_lecturer_for_course(mata_kuliah_id));

create policy submission_select_admin
on public.pengumpulan_tugas
for select to authenticated
using (app_private.is_admin());

create policy sheet_select_authorized
on public.lembar_jawaban
for select to authenticated
using (app_private.can_access_submission(pengumpulan_tugas_id));

create policy prediction_select_authorized
on public.hasil_prediksi
for select to authenticated
using (app_private.can_access_submission(pengumpulan_tugas_id));

create policy audit_admin_select
on public.audit_log
for select to authenticated
using (app_private.is_admin());

create policy settings_authenticated_select
on public.system_settings
for select to authenticated
using (true);

create policy settings_admin_all
on public.system_settings
for all to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());

create policy models_authenticated_select
on public.ai_models
for select to authenticated
using (true);

create policy models_admin_all
on public.ai_models
for all to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());

-- Storage objects are immutable. Replacement creates a new versioned path,
-- commits metadata through RPC, and removes the old object afterwards.
create policy answer_object_insert_owner
on storage.objects
for insert to authenticated
with check (
  bucket_id = 'lembar-jawaban'
  and (storage.foldername(name))[1] = (select auth.uid())::text
  and app_private.owns_submission(
    ((storage.foldername(name))[2])::uuid
  )
);

create policy answer_object_select_authorized
on storage.objects
for select to authenticated
using (
  bucket_id = 'lembar-jawaban'
  and app_private.can_access_submission(
    ((storage.foldername(name))[2])::uuid
  )
);

create policy answer_object_delete_owner
on storage.objects
for delete to authenticated
using (
  bucket_id = 'lembar-jawaban'
  and (storage.foldername(name))[1] = (select auth.uid())::text
  and exists (
    select 1
    from public.pengumpulan_tugas as submission
    where submission.id = ((storage.foldername(name))[2])::uuid
      and submission.mahasiswa_id = (select auth.uid())
      and submission.status_submit in ('draft', 'reupload_required')
  )
);

create policy profile_object_insert_owner
on storage.objects
for insert to authenticated
with check (
  bucket_id = 'profile-images'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

create policy profile_object_delete_owner
on storage.objects
for delete to authenticated
using (
  bucket_id = 'profile-images'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

-- Explicit Data API grants. Anonymous clients receive no application data.
revoke all on all tables in schema public from anon;
revoke all on all functions in schema public from anon;

revoke all on all tables in schema public from authenticated;
grant select on
  public.profil_pengguna,
  public.mata_kuliah,
  public.mahasiswa_mata_kuliah,
  public.dosen_mata_kuliah,
  public.pengumpulan_tugas,
  public.lembar_jawaban,
  public.hasil_prediksi,
  public.audit_log,
  public.system_settings,
  public.ai_models
to authenticated;

grant insert, update, delete on public.profil_pengguna to authenticated;
grant insert, update, delete on public.mata_kuliah to authenticated;
grant insert, update, delete on public.mahasiswa_mata_kuliah to authenticated;
grant insert, update, delete on public.dosen_mata_kuliah to authenticated;
grant insert, update, delete on public.system_settings to authenticated;
grant insert, update, delete on public.ai_models to authenticated;

grant all on all tables in schema public to service_role;
grant all on all functions in schema public to service_role;

create or replace function app_private.uuid_or_null(value text)
returns uuid
language plpgsql
immutable
set search_path = ''
as $$
begin
  return value::uuid;
exception
  when invalid_text_representation then
    return null;
end;
$$;

revoke all on function app_private.uuid_or_null(text) from public, anon;
grant execute on function app_private.uuid_or_null(text)
to authenticated, service_role;

drop policy answer_object_insert_owner on storage.objects;
create policy answer_object_insert_owner
on storage.objects
for insert to authenticated
with check (
  bucket_id = 'lembar-jawaban'
  and (storage.foldername(name))[1] = (select auth.uid())::text
  and app_private.owns_submission(
    app_private.uuid_or_null((storage.foldername(name))[2])
  )
);

drop policy answer_object_select_authorized on storage.objects;
create policy answer_object_select_authorized
on storage.objects
for select to authenticated
using (
  bucket_id = 'lembar-jawaban'
  and app_private.can_access_submission(
    app_private.uuid_or_null((storage.foldername(name))[2])
  )
);

drop policy answer_object_delete_owner on storage.objects;
create policy answer_object_delete_owner
on storage.objects
for delete to authenticated
using (
  bucket_id = 'lembar-jawaban'
  and (storage.foldername(name))[1] = (select auth.uid())::text
  and exists (
    select 1
    from public.pengumpulan_tugas as submission
    where submission.id =
      app_private.uuid_or_null((storage.foldername(name))[2])
      and submission.mahasiswa_id = (select auth.uid())
      and submission.status_submit in ('draft', 'reupload_required')
  )
);

create or replace function app_private.write_audit(
  action_name text,
  target_name text,
  target_identifier text,
  event_detail jsonb default '{}'::jsonb
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor_name text;
  actor_role text;
begin
  select profile.nama_lengkap, lower(profile.role)
  into actor_name, actor_role
  from public.profil_pengguna as profile
  where profile.id = (select auth.uid());

  insert into public.audit_log (
    actor_id,
    actor_role,
    action_type,
    target_type,
    target_id,
    description,
    user_id,
    user_name,
    role,
    action,
    target,
    detail
  )
  values (
    (select auth.uid()),
    actor_role,
    action_name,
    target_name,
    target_identifier,
    action_name,
    (select auth.uid()),
    actor_name,
    actor_role,
    action_name,
    target_name,
    coalesce(event_detail, '{}'::jsonb)
  );
end;
$$;

revoke all on function app_private.write_audit(text, text, text, jsonb)
from public, anon, authenticated;
grant execute on function app_private.write_audit(text, text, text, jsonb)
to service_role;

create or replace function public.create_submission(
  p_mata_kuliah_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  submission_id uuid;
begin
  if app_private.current_role() <> 'mahasiswa' then
    raise exception using errcode = '42501', message = 'student_role_required';
  end if;

  if not exists (
    select 1
    from public.mahasiswa_mata_kuliah as enrollment
    where enrollment.mahasiswa_id = (select auth.uid())
      and enrollment.mata_kuliah_id = p_mata_kuliah_id
  ) then
    raise exception using errcode = '42501', message = 'course_enrollment_required';
  end if;

  select submission.id
  into submission_id
  from public.pengumpulan_tugas as submission
  where submission.mahasiswa_id = (select auth.uid())
    and submission.mata_kuliah_id = p_mata_kuliah_id
  for update;

  if submission_id is null then
    insert into public.pengumpulan_tugas (
      mahasiswa_id,
      mata_kuliah_id,
      waktu_submit,
      status_penilaian,
      status_submit,
      ai_status
    )
    values (
      (select auth.uid()),
      p_mata_kuliah_id,
      null,
      'menunggu_koreksi',
      'draft',
      'idle'
    )
    returning id into submission_id;
  end if;

  return submission_id;
end;
$$;

create or replace function public.upsert_answer_metadata(
  p_submission_id uuid,
  p_section_code text,
  p_image_url text
)
returns table (
  sheet_id uuid,
  previous_image_url text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  submission_row public.pengumpulan_tugas%rowtype;
  existing_sheet public.lembar_jawaban%rowtype;
  expected_prefix text;
begin
  select *
  into submission_row
  from public.pengumpulan_tugas
  where id = p_submission_id
  for update;

  if not found or submission_row.mahasiswa_id <> (select auth.uid()) then
    raise exception using errcode = '42501', message = 'submission_not_owned';
  end if;

  if p_section_code !~ '^S-[1-4][A-F]$' then
    raise exception using errcode = '22023', message = 'invalid_section';
  end if;

  expected_prefix :=
    (select auth.uid())::text
    || '/'
    || p_submission_id::text
    || '/'
    || p_section_code
    || '/';

  if p_image_url is null
     or length(p_image_url) > 2048
     or p_image_url not like expected_prefix || '%.jpg' then
    raise exception using errcode = '22023', message = 'invalid_object_path';
  end if;

  select *
  into existing_sheet
  from public.lembar_jawaban
  where pengumpulan_tugas_id = p_submission_id
    and section_code = p_section_code
  for update;

  if found then
    if submission_row.status_submit not in ('draft', 'reupload_required')
       and existing_sheet.status <> 'reupload_required' then
      raise exception using errcode = '42501', message = 'submission_not_editable';
    end if;

    update public.lembar_jawaban
    set
      image_url = p_image_url,
      status = 'draft',
      prediksi_ai = null,
      nilai_dosen = null,
      nilai_final = null,
      rejection_reason = null,
      was_reuploaded =
        existing_sheet.status = 'reupload_required'
        or existing_sheet.was_reuploaded,
      last_reupload_at = case
        when existing_sheet.status = 'reupload_required' then now()
        else existing_sheet.last_reupload_at
      end,
      reupload_count = case
        when existing_sheet.status = 'reupload_required'
          then existing_sheet.reupload_count + 1
        else existing_sheet.reupload_count
      end
    where id = existing_sheet.id;

    sheet_id := existing_sheet.id;
    previous_image_url := existing_sheet.image_url;
  else
    if submission_row.status_submit <> 'draft' then
      raise exception using errcode = '42501', message = 'submission_not_editable';
    end if;

    insert into public.lembar_jawaban (
      pengumpulan_tugas_id,
      section_code,
      image_url,
      status
    )
    values (
      p_submission_id,
      p_section_code,
      p_image_url,
      'draft'
    )
    returning id into sheet_id;

    previous_image_url := null;
  end if;

  perform app_private.write_audit(
    case
      when previous_image_url is null then 'ANSWER_UPLOADED'
      else 'ANSWER_REPLACED'
    end,
    'lembar_jawaban',
    sheet_id::text,
    jsonb_build_object('section', p_section_code)
  );

  return next;
end;
$$;

create or replace function public.delete_answer_metadata(
  p_submission_id uuid,
  p_section_code text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  submission_row public.pengumpulan_tugas%rowtype;
  deleted_path text;
begin
  select *
  into submission_row
  from public.pengumpulan_tugas
  where id = p_submission_id
  for update;

  if not found or submission_row.mahasiswa_id <> (select auth.uid()) then
    raise exception using errcode = '42501', message = 'submission_not_owned';
  end if;

  if submission_row.status_submit not in ('draft', 'reupload_required') then
    raise exception using errcode = '42501', message = 'submission_not_editable';
  end if;

  delete from public.lembar_jawaban
  where pengumpulan_tugas_id = p_submission_id
    and section_code = p_section_code
  returning image_url into deleted_path;

  if deleted_path is null then
    raise exception using errcode = 'P0002', message = 'answer_not_found';
  end if;

  perform app_private.write_audit(
    'ANSWER_DELETED',
    'lembar_jawaban',
    p_submission_id::text,
    jsonb_build_object('section', p_section_code)
  );

  if not exists (
    select 1
    from public.lembar_jawaban
    where pengumpulan_tugas_id = p_submission_id
  ) and submission_row.status_submit = 'draft' then
    delete from public.pengumpulan_tugas
    where id = p_submission_id;
  end if;

  return deleted_path;
end;
$$;

create or replace function public.submit_submission(
  p_submission_id uuid,
  p_model_ai text default 'MobileNetV2'
)
returns public.pengumpulan_tugas
language plpgsql
security definer
set search_path = ''
as $$
declare
  submission_row public.pengumpulan_tugas%rowtype;
  submitted_row public.pengumpulan_tugas%rowtype;
  section_count integer;
begin
  if p_model_ai not in ('MobileNetV2', 'DenseNet121', 'InceptionV3') then
    raise exception using errcode = '22023', message = 'invalid_model';
  end if;

  select *
  into submission_row
  from public.pengumpulan_tugas
  where id = p_submission_id
  for update;

  if not found or submission_row.mahasiswa_id <> (select auth.uid()) then
    raise exception using errcode = '42501', message = 'submission_not_owned';
  end if;

  if submission_row.status_submit not in ('draft', 'reupload_required', 'failed') then
    raise exception using errcode = '42501', message = 'submission_not_submittable';
  end if;

  select count(distinct sheet.section_code)
  into section_count
  from public.lembar_jawaban as sheet
  where sheet.pengumpulan_tugas_id = p_submission_id
    and sheet.section_code ~ '^S-[1-4][A-F]$'
    and sheet.image_url is not null;

  if section_count <> 24 then
    raise exception using errcode = '22023', message = 'twenty_four_sections_required';
  end if;

  update public.lembar_jawaban
  set status = 'submitted'
  where pengumpulan_tugas_id = p_submission_id;

  update public.pengumpulan_tugas
  set
    waktu_submit = now(),
    status_penilaian = 'menunggu_koreksi',
    status_submit = 'submitted',
    ai_status = 'pending',
    model_ai = p_model_ai,
    model_ai_terpilih = p_model_ai,
    nilai_akhir = null,
    ai_processed_at = null
  where id = p_submission_id
  returning * into submitted_row;

  perform app_private.write_audit(
    'SUBMISSION_SUBMITTED',
    'pengumpulan_tugas',
    p_submission_id::text,
    jsonb_build_object('model', p_model_ai, 'sections', section_count)
  );

  return submitted_row;
end;
$$;

create or replace function app_private.apply_review_payload(
  p_submission_id uuid,
  p_scores jsonb,
  p_finalize boolean
)
returns real
language plpgsql
security definer
set search_path = ''
as $$
declare
  review_item jsonb;
  section_name text;
  manual_score real;
  final_score real;
  feedback_text text;
  item_count integer;
  distinct_count integer;
  overall_score real;
begin
  if jsonb_typeof(p_scores) <> 'array' then
    raise exception using errcode = '22023', message = 'review_payload_must_be_array';
  end if;

  item_count := jsonb_array_length(p_scores);
  select count(distinct item ->> 'section_code')
  into distinct_count
  from jsonb_array_elements(p_scores) as item;

  if item_count <> 24 or distinct_count <> 24 then
    raise exception using errcode = '22023', message = 'twenty_four_unique_scores_required';
  end if;

  for review_item in
    select value
    from jsonb_array_elements(p_scores)
  loop
    section_name := review_item ->> 'section_code';
    manual_score := nullif(review_item ->> 'nilai_dosen', '')::real;
    final_score := nullif(review_item ->> 'nilai_final', '')::real;
    feedback_text := review_item ->> 'feedback';

    if section_name !~ '^S-[1-4][A-F]$' then
      raise exception using errcode = '22023', message = 'invalid_section';
    end if;

    if manual_score is not null and manual_score not between 0 and 5 then
      raise exception using errcode = '22023', message = 'invalid_manual_score';
    end if;

    if final_score is not null and final_score not between 0 and 5 then
      raise exception using errcode = '22023', message = 'invalid_final_score';
    end if;

    if p_finalize and final_score is null then
      raise exception using errcode = '22023', message = 'final_score_required';
    end if;

    if length(coalesce(feedback_text, '')) > 2000 then
      raise exception using errcode = '22023', message = 'feedback_too_long';
    end if;

    update public.lembar_jawaban
    set
      nilai_dosen = manual_score,
      nilai_final = final_score,
      feedback = feedback_text,
      status = case when p_finalize then 'finalized' else 'reviewed' end
    where pengumpulan_tugas_id = p_submission_id
      and section_code = section_name;

    if not found then
      raise exception using errcode = 'P0002', message = 'answer_section_not_found';
    end if;
  end loop;

  select sum(coalesce(sheet.nilai_final, sheet.nilai_dosen, sheet.prediksi_ai, 0))
  into overall_score
  from public.lembar_jawaban as sheet
  where sheet.pengumpulan_tugas_id = p_submission_id;

  return coalesce(overall_score, 0);
end;
$$;

revoke all on function app_private.apply_review_payload(uuid, jsonb, boolean)
from public, anon, authenticated;
grant execute on function app_private.apply_review_payload(uuid, jsonb, boolean)
to service_role;

create or replace function public.save_submission_review(
  p_submission_id uuid,
  p_scores jsonb,
  p_model_ai text
)
returns real
language plpgsql
security definer
set search_path = ''
as $$
declare
  submission_row public.pengumpulan_tugas%rowtype;
  overall_score real;
begin
  if p_model_ai not in ('MobileNetV2', 'DenseNet121', 'InceptionV3') then
    raise exception using errcode = '22023', message = 'invalid_model';
  end if;

  select *
  into submission_row
  from public.pengumpulan_tugas
  where id = p_submission_id
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'submission_not_found';
  end if;

  if not (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(submission_row.mata_kuliah_id)
  ) then
    raise exception using errcode = '42501', message = 'lecturer_assignment_required';
  end if;

  if submission_row.status_submit = 'finalized' then
    raise exception using errcode = '42501', message = 'submission_already_finalized';
  end if;

  overall_score :=
    app_private.apply_review_payload(p_submission_id, p_scores, false);

  update public.pengumpulan_tugas
  set
    nilai_akhir = overall_score,
    model_ai = p_model_ai,
    status_submit = 'reviewed',
    ai_status = 'reviewed',
    status_penilaian = 'sudah_dikoreksi'
  where id = p_submission_id;

  perform app_private.write_audit(
    'REVIEW_DRAFT_SAVED',
    'pengumpulan_tugas',
    p_submission_id::text,
    jsonb_build_object('score', overall_score)
  );

  return overall_score;
end;
$$;

create or replace function public.finalize_submission_review(
  p_submission_id uuid,
  p_scores jsonb,
  p_model_ai text
)
returns real
language plpgsql
security definer
set search_path = ''
as $$
declare
  submission_row public.pengumpulan_tugas%rowtype;
  overall_score real;
begin
  if p_model_ai not in ('MobileNetV2', 'DenseNet121', 'InceptionV3') then
    raise exception using errcode = '22023', message = 'invalid_model';
  end if;

  select *
  into submission_row
  from public.pengumpulan_tugas
  where id = p_submission_id
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'submission_not_found';
  end if;

  if not (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(submission_row.mata_kuliah_id)
  ) then
    raise exception using errcode = '42501', message = 'lecturer_assignment_required';
  end if;

  if submission_row.status_submit = 'finalized' then
    raise exception using errcode = '42501', message = 'submission_already_finalized';
  end if;

  overall_score :=
    app_private.apply_review_payload(p_submission_id, p_scores, true);

  update public.pengumpulan_tugas
  set
    nilai_akhir = overall_score,
    model_ai = p_model_ai,
    status_submit = 'finalized',
    ai_status = 'finalized',
    status_penilaian = 'selesai'
  where id = p_submission_id;

  perform app_private.write_audit(
    'FINAL_SCORE_SUBMITTED',
    'pengumpulan_tugas',
    p_submission_id::text,
    jsonb_build_object(
      'old_score', submission_row.nilai_akhir,
      'new_score', overall_score
    )
  );

  return overall_score;
end;
$$;

create or replace function public.request_answer_reupload(
  p_submission_id uuid,
  p_section_code text,
  p_reason text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  submission_row public.pengumpulan_tugas%rowtype;
begin
  if p_section_code !~ '^S-[1-4][A-F]$' then
    raise exception using errcode = '22023', message = 'invalid_section';
  end if;

  if length(trim(coalesce(p_reason, ''))) not between 1 and 1000 then
    raise exception using errcode = '22023', message = 'invalid_reupload_reason';
  end if;

  select *
  into submission_row
  from public.pengumpulan_tugas
  where id = p_submission_id
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'submission_not_found';
  end if;

  if not (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(submission_row.mata_kuliah_id)
  ) then
    raise exception using errcode = '42501', message = 'lecturer_assignment_required';
  end if;

  if submission_row.status_submit = 'finalized' then
    raise exception using errcode = '42501', message = 'submission_already_finalized';
  end if;

  update public.lembar_jawaban
  set
    status = 'reupload_required',
    rejection_reason = trim(p_reason),
    prediksi_ai = null,
    nilai_dosen = null,
    nilai_final = null
  where pengumpulan_tugas_id = p_submission_id
    and section_code = p_section_code;

  if not found then
    raise exception using errcode = 'P0002', message = 'answer_section_not_found';
  end if;

  update public.pengumpulan_tugas
  set
    status_submit = 'reupload_required',
    ai_status = 'failed',
    nilai_akhir = null
  where id = p_submission_id;

  perform app_private.write_audit(
    'REUPLOAD_REQUESTED',
    'lembar_jawaban',
    p_submission_id::text,
    jsonb_build_object(
      'section', p_section_code,
      'reason', trim(p_reason)
    )
  );
end;
$$;

create or replace function public.claim_ai_job(
  p_submission_id uuid,
  p_model_ai text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  submission_row public.pengumpulan_tugas%rowtype;
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  if p_model_ai not in ('MobileNetV2', 'DenseNet121', 'InceptionV3') then
    raise exception using errcode = '22023', message = 'invalid_model';
  end if;

  select *
  into submission_row
  from public.pengumpulan_tugas
  where id = p_submission_id
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'submission_not_found';
  end if;

  if submission_row.status_submit = 'finalized' then
    return jsonb_build_object(
      'claimed', false,
      'reason', 'submission_finalized'
    );
  end if;

  if submission_row.ai_status = 'processing' then
    return jsonb_build_object(
      'claimed', false,
      'reason', 'already_processing'
    );
  end if;

  if (
    select count(distinct sheet.section_code)
    from public.lembar_jawaban as sheet
    where sheet.pengumpulan_tugas_id = p_submission_id
      and sheet.section_code ~ '^S-[1-4][A-F]$'
  ) <> 24 then
    return jsonb_build_object(
      'claimed', false,
      'reason', 'incomplete_submission'
    );
  end if;

  update public.pengumpulan_tugas
  set
    status_submit = 'processing_ai',
    ai_status = 'processing',
    model_ai = p_model_ai,
    model_ai_terpilih = p_model_ai,
    ai_processed_at = null
  where id = p_submission_id;

  return jsonb_build_object(
    'claimed', true,
    'previous_status_submit', submission_row.status_submit,
    'previous_ai_status', submission_row.ai_status,
    'model', p_model_ai
  );
end;
$$;

create or replace function public.release_ai_job(
  p_submission_id uuid,
  p_previous_status_submit text,
  p_previous_ai_status text
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  if p_previous_status_submit not in (
    'draft',
    'reupload_required',
    'submitted',
    'reviewed',
    'failed'
  ) or p_previous_ai_status not in (
    'idle',
    'pending',
    'completed',
    'failed',
    'reviewed'
  ) then
    raise exception using errcode = '22023', message = 'invalid_previous_status';
  end if;

  update public.pengumpulan_tugas
  set
    status_submit = p_previous_status_submit,
    ai_status = p_previous_ai_status
  where id = p_submission_id
    and status_submit = 'processing_ai'
    and ai_status = 'processing';

  return found;
end;
$$;

create or replace function public.fail_ai_job(
  p_submission_id uuid,
  p_error_code text
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  if p_error_code !~ '^[A-Z0-9_]{1,64}$' then
    raise exception using errcode = '22023', message = 'invalid_error_code';
  end if;

  update public.pengumpulan_tugas
  set
    status_submit = 'failed',
    ai_status = 'failed',
    ai_processed_at = now()
  where id = p_submission_id
    and status_submit <> 'finalized';

  if found then
    insert into public.audit_log (
      actor_role,
      action_type,
      target_type,
      target_id,
      description,
      role,
      action,
      target,
      detail
    )
    values (
      'system',
      'AI_PROCESS_FAILED',
      'pengumpulan_tugas',
      p_submission_id::text,
      'AI processing failed.',
      'system',
      'AI_PROCESS_FAILED',
      'pengumpulan_tugas',
      jsonb_build_object('error_code', p_error_code)
    );
  end if;

  return found;
end;
$$;

create or replace function public.complete_ai_job(
  p_submission_id uuid,
  p_total_score real
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  if p_total_score not between 0 and 100 then
    raise exception using errcode = '22023', message = 'invalid_total_score';
  end if;

  update public.pengumpulan_tugas
  set
    status_submit = 'submitted',
    ai_status = 'completed',
    nilai_akhir = p_total_score,
    ai_processed_at = now()
  where id = p_submission_id
    and status_submit = 'processing_ai'
    and ai_status = 'processing';

  if found then
    update public.lembar_jawaban
    set status = 'completed'
    where pengumpulan_tugas_id = p_submission_id
      and status <> 'reupload_required';

    insert into public.audit_log (
      actor_role,
      action_type,
      target_type,
      target_id,
      description,
      role,
      action,
      target,
      detail
    )
    values (
      'system',
      'AI_PROCESS_COMPLETED',
      'pengumpulan_tugas',
      p_submission_id::text,
      'AI processing completed.',
      'system',
      'AI_PROCESS_COMPLETED',
      'pengumpulan_tugas',
      jsonb_build_object('total_score', p_total_score)
    );
  end if;

  return found;
end;
$$;

create or replace function public.write_audit_event(
  p_action text,
  p_target text,
  p_target_id text default null,
  p_detail jsonb default '{}'::jsonb
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_role text;
  allowed_actions text[];
begin
  caller_role := app_private.current_role();

  if caller_role = 'mahasiswa' then
    allowed_actions := array[
      'STUDENT_LOGIN',
      'ANSWER_UPLOADED',
      'ANSWER_REPLACED',
      'ANSWER_DELETED',
      'SUBMISSION_SUBMITTED'
    ];
  elsif caller_role = 'dosen' then
    allowed_actions := array[
      'LECTURER_LOGIN',
      'REVIEW_DRAFT_SAVED',
      'FINAL_SCORE_SUBMITTED',
      'REUPLOAD_REQUESTED'
    ];
  elsif caller_role = 'admin' then
    allowed_actions := array[
      'ADMIN_LOGIN',
      'SYSTEM_RESET',
      'ACTIVE_MODEL_CHANGED',
      'SYSTEM_SETTING_CHANGED',
      'STORAGE_PRUNE',
      'AUDIT_TEST'
    ];
  else
    raise exception using errcode = '42501', message = 'authenticated_profile_required';
  end if;

  if not (p_action = any(allowed_actions)) then
    raise exception using errcode = '42501', message = 'audit_action_not_allowed';
  end if;

  if p_target is null
     or length(p_target) not between 1 and 64
     or p_target !~ '^[a-z_]+$' then
    raise exception using errcode = '22023', message = 'invalid_audit_target';
  end if;

  if octet_length(coalesce(p_detail, '{}'::jsonb)::text) > 8192 then
    raise exception using errcode = '22023', message = 'audit_detail_too_large';
  end if;

  perform app_private.write_audit(
    p_action,
    p_target,
    p_target_id,
    coalesce(p_detail, '{}'::jsonb)
  );
end;
$$;

create or replace function public.admin_delete_user_data(
  p_user_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  object_paths jsonb;
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  if exists (
    select 1
    from public.profil_pengguna
    where id = p_user_id and role = 'admin'
  ) then
    raise exception using errcode = '42501', message = 'admin_deletion_forbidden';
  end if;

  select coalesce(jsonb_agg(sheet.image_url), '[]'::jsonb)
  into object_paths
  from public.lembar_jawaban as sheet
  join public.pengumpulan_tugas as submission
    on submission.id = sheet.pengumpulan_tugas_id
  where submission.mahasiswa_id = p_user_id;

  delete from auth.users
  where id = p_user_id;

  return jsonb_build_object('object_paths', object_paths);
end;
$$;

create or replace function public.admin_delete_course_data(
  p_course_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  object_paths jsonb;
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  select coalesce(jsonb_agg(sheet.image_url), '[]'::jsonb)
  into object_paths
  from public.lembar_jawaban as sheet
  join public.pengumpulan_tugas as submission
    on submission.id = sheet.pengumpulan_tugas_id
  where submission.mata_kuliah_id = p_course_id;

  delete from public.mata_kuliah
  where id = p_course_id;

  return jsonb_build_object('object_paths', object_paths);
end;
$$;

create or replace function public.admin_delete_enrollment_data(
  p_student_id uuid,
  p_course_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  object_paths jsonb;
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  select coalesce(jsonb_agg(sheet.image_url), '[]'::jsonb)
  into object_paths
  from public.lembar_jawaban as sheet
  join public.pengumpulan_tugas as submission
    on submission.id = sheet.pengumpulan_tugas_id
  where submission.mahasiswa_id = p_student_id
    and submission.mata_kuliah_id = p_course_id;

  delete from public.pengumpulan_tugas
  where mahasiswa_id = p_student_id
    and mata_kuliah_id = p_course_id;

  delete from public.mahasiswa_mata_kuliah
  where mahasiswa_id = p_student_id
    and mata_kuliah_id = p_course_id;

  return jsonb_build_object('object_paths', object_paths);
end;
$$;

create or replace function public.admin_reset_demo_data(
  p_delete_submissions boolean,
  p_delete_enrollments boolean
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  object_paths jsonb := '[]'::jsonb;
  submission_count integer := 0;
  answer_count integer := 0;
  prediction_count integer := 0;
  enrollment_count integer := 0;
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  if not p_delete_submissions and not p_delete_enrollments then
    raise exception using errcode = '22023', message = 'reset_scope_required';
  end if;

  if p_delete_submissions then
    select
      coalesce(jsonb_agg(sheet.image_url), '[]'::jsonb),
      count(distinct submission.id),
      count(distinct sheet.id),
      count(distinct prediction.id)
    into
      object_paths,
      submission_count,
      answer_count,
      prediction_count
    from public.pengumpulan_tugas as submission
    left join public.lembar_jawaban as sheet
      on sheet.pengumpulan_tugas_id = submission.id
    left join public.hasil_prediksi as prediction
      on prediction.pengumpulan_tugas_id = submission.id;

    delete from public.pengumpulan_tugas;
  end if;

  if p_delete_enrollments then
    select count(*) into enrollment_count
    from public.mahasiswa_mata_kuliah;
    delete from public.mahasiswa_mata_kuliah;
  end if;

  return jsonb_build_object(
    'object_paths', object_paths,
    'submissions_deleted', submission_count,
    'answer_sheets_deleted', answer_count,
    'predictions_deleted', prediction_count,
    'enrollments_deleted', enrollment_count
  );
end;
$$;

revoke all on all functions in schema public from public, anon;
revoke all on all functions in schema public from authenticated;

grant execute on function public.create_submission(uuid) to authenticated;
grant execute on function public.upsert_answer_metadata(uuid, text, text)
to authenticated;
grant execute on function public.delete_answer_metadata(uuid, text)
to authenticated;
grant execute on function public.submit_submission(uuid, text)
to authenticated;
grant execute on function public.save_submission_review(uuid, jsonb, text)
to authenticated;
grant execute on function public.finalize_submission_review(uuid, jsonb, text)
to authenticated;
grant execute on function public.request_answer_reupload(uuid, text, text)
to authenticated;
grant execute on function public.write_audit_event(text, text, text, jsonb)
to authenticated;

grant execute on function public.claim_ai_job(uuid, text) to service_role;
grant execute on function public.release_ai_job(uuid, text, text) to service_role;
grant execute on function public.fail_ai_job(uuid, text) to service_role;
grant execute on function public.complete_ai_job(uuid, real) to service_role;
grant execute on function public.admin_delete_user_data(uuid) to service_role;
grant execute on function public.admin_delete_course_data(uuid) to service_role;
grant execute on function public.admin_delete_enrollment_data(uuid, uuid)
to service_role;
grant execute on function public.admin_reset_demo_data(boolean, boolean)
to service_role;

-- Service role remains the only writer for predictions and audit rows.
revoke insert, update, delete on public.pengumpulan_tugas from authenticated;
revoke insert, update, delete on public.lembar_jawaban from authenticated;
revoke insert, update, delete on public.hasil_prediksi from authenticated;
revoke insert, update, delete on public.audit_log from authenticated;
