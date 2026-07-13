-- Make the QR enrollment schema deterministic for both a fresh local reset
-- and the existing cloud project. This migration preserves the business
-- tables and upgrades only columns/functions used by the current frontend.

alter table public.class_join_sessions
  add column if not exists token_raw text,
  add column if not exists current_uses integer not null default 0,
  add column if not exists revoked boolean not null default false;

do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'class_join_sessions'
      and column_name = 'used_count'
  ) then
    update public.class_join_sessions
    set current_uses = greatest(current_uses, used_count);
  end if;

  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'class_join_sessions'
      and column_name = 'revoked_at'
  ) then
    update public.class_join_sessions
    set revoked = true
    where revoked_at is not null;
  end if;
end;
$$;

alter table public.class_join_sessions
  drop constraint if exists class_join_sessions_current_uses_check,
  add constraint class_join_sessions_current_uses_check
    check (current_uses >= 0),
  drop constraint if exists class_join_sessions_token_raw_check,
  add constraint class_join_sessions_token_raw_check
    check (token_raw is null or token_raw ~ '^[A-Za-z0-9_-]{43}$');

drop function if exists public.create_class_join_session(
  uuid,
  text,
  timestamptz,
  integer
);

create or replace function public.create_class_join_session(
  p_course_id uuid,
  p_token_hash text,
  p_expires_at timestamptz,
  p_max_uses integer default null,
  p_token_raw text default null
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

  if p_token_raw is null or p_token_raw !~ '^[A-Za-z0-9_-]{43}$' then
    raise exception 'INVALID_RAW_TOKEN';
  end if;

  if p_expires_at <= now()
     or p_expires_at > now() + interval '24 hours' then
    raise exception 'INVALID_EXPIRY';
  end if;

  if p_max_uses is not null and (p_max_uses < 1 or p_max_uses > 500) then
    raise exception 'INVALID_MAX_USES';
  end if;

  update public.class_join_sessions
  set
    revoked = true
  where course_id = p_course_id
    and revoked = false;

  insert into public.class_join_sessions (
    course_id,
    created_by,
    token_hash,
    token_raw,
    expires_at,
    max_uses,
    current_uses,
    revoked
  )
  values (
    p_course_id,
    (select auth.uid()),
    p_token_hash,
    p_token_raw,
    p_expires_at,
    p_max_uses,
    0,
    false
  )
  returning * into created_row;

  return created_row;
end;
$$;

drop function if exists public.revoke_class_join_session(uuid);

create or replace function public.revoke_class_join_session(
  p_join_session_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  session_course_id uuid;
begin
  select course_id
  into session_course_id
  from public.class_join_sessions
  where id = p_join_session_id
  for update;

  if not found then
    raise exception 'JOIN_SESSION_NOT_FOUND';
  end if;

  if not (
    app_private.is_admin()
    or app_private.is_lecturer_for_course(session_course_id)
  ) then
    raise exception 'FORBIDDEN';
  end if;

  update public.class_join_sessions
  set
    revoked = true
  where id = p_join_session_id;

  return jsonb_build_object('success', true, 'session_id', p_join_session_id);
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
    and revoked = false
    and expires_at > now()
  for update;

  if not found then
    raise exception 'JOIN_TOKEN_EXPIRED_OR_INVALID';
  end if;

  if session_row.max_uses is not null
     and session_row.current_uses >= session_row.max_uses then
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
    set
      current_uses = current_uses + 1
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

revoke all on function public.create_class_join_session(
  uuid,
  text,
  timestamptz,
  integer,
  text
) from public, anon;
revoke all on function public.revoke_class_join_session(uuid) from public, anon;
revoke all on function public.join_class_with_token(text) from public, anon;

grant execute on function public.create_class_join_session(
  uuid,
  text,
  timestamptz,
  integer,
  text
) to authenticated, service_role;
grant execute on function public.revoke_class_join_session(uuid)
to authenticated, service_role;
grant execute on function public.join_class_with_token(text)
to authenticated, service_role;

alter table public.class_join_sessions
  drop column if exists used_count,
  drop column if exists revoked_at;
