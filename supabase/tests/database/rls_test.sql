begin;

create extension if not exists pgtap with schema extensions;

select plan(30);

select has_column(
  'public',
  'class_join_sessions',
  'token_raw',
  'join sessions retain the raw token only for authorized QR redisplay'
);
select has_column(
  'public',
  'class_join_sessions',
  'current_uses',
  'join sessions expose the current use counter expected by the UI'
);
select has_column(
  'public',
  'class_join_sessions',
  'revoked',
  'join sessions expose the revocation flag expected by the UI'
);
select ok(
  to_regprocedure(
    'public.create_class_join_session(uuid,text,timestamptz,integer,text)'
  ) is not null,
  'canonical five-argument create join RPC exists'
);
select ok(
  to_regprocedure(
    'public.create_class_join_session(uuid,text,timestamptz,integer)'
  ) is null,
  'legacy create join RPC overload is removed'
);
select ok(
  not has_function_privilege(
    'anon',
    'public.create_class_join_session(uuid,text,timestamptz,integer,text)',
    'execute'
  ),
  'anonymous cannot create QR join sessions'
);
select ok(
  has_function_privilege(
    'authenticated',
    'public.create_class_join_session(uuid,text,timestamptz,integer,text)',
    'execute'
  ),
  'authenticated lecturers can call the guarded QR join RPC'
);

select ok(
  not has_table_privilege('anon', 'public.profil_pengguna', 'select'),
  'anonymous cannot read profiles'
);
select ok(
  not has_table_privilege('anon', 'public.pengumpulan_tugas', 'select'),
  'anonymous cannot read submissions'
);
select ok(
  not has_table_privilege('anon', 'public.audit_log', 'select'),
  'anonymous cannot read audit logs'
);
select ok(
  not has_function_privilege(
    'anon',
    'public.write_audit_event(text,text,text,jsonb)',
    'execute'
  ),
  'anonymous cannot invoke audit RPC'
);
select ok(
  not has_function_privilege(
    'authenticated',
    'public.claim_ai_job(uuid,text)',
    'execute'
  ),
  'browser clients cannot claim AI jobs'
);
select ok(
  not has_function_privilege(
    'authenticated',
    'public.reconcile_stale_ai_jobs(timestamptz)',
    'execute'
  ),
  'browser clients cannot reconcile stale AI jobs'
);
select ok(
  not has_function_privilege(
    'authenticated',
    'public.admin_reset_demo_data(boolean,boolean)',
    'execute'
  ),
  'browser clients cannot invoke demo reset'
);
select ok(
  has_function_privilege(
    'service_role',
    'public.admin_reset_demo_data(boolean,boolean)',
    'execute'
  ),
  'service role can invoke demo reset'
);
select ok(
  has_function_privilege(
    'service_role',
    'public.reconcile_stale_ai_jobs(timestamptz)',
    'execute'
  ),
  'service role can reconcile stale AI jobs'
);
select ok(
  not has_table_privilege(
    'authenticated',
    'public.hasil_prediksi',
    'insert'
  ),
  'browser clients cannot write predictions'
);
select ok(
  not has_table_privilege(
    'authenticated',
    'public.pengumpulan_tugas',
    'update'
  ),
  'browser clients cannot update submission scores or statuses directly'
);
select ok(
  not has_table_privilege(
    'authenticated',
    'public.audit_log',
    'insert'
  ),
  'browser clients cannot forge audit rows'
);

insert into auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  raw_app_meta_data,
  raw_user_meta_data
)
values
  (
    '00000000-0000-0000-0000-000000000000',
    '10000000-0000-0000-0000-000000000001',
    'authenticated',
    'authenticated',
    'student-one@example.invalid',
    'test-only',
    now(),
    '{}'::jsonb,
    '{}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000000',
    '10000000-0000-0000-0000-000000000002',
    'authenticated',
    'authenticated',
    'student-two@example.invalid',
    'test-only',
    now(),
    '{}'::jsonb,
    '{}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000000',
    '20000000-0000-0000-0000-000000000001',
    'authenticated',
    'authenticated',
    'lecturer@example.invalid',
    'test-only',
    now(),
    '{}'::jsonb,
    '{}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000000',
    '30000000-0000-0000-0000-000000000001',
    'authenticated',
    'authenticated',
    'admin@example.invalid',
    'test-only',
    now(),
    '{}'::jsonb,
    '{}'::jsonb
  );

insert into public.profil_pengguna (id, role, nama_lengkap, nim_nip)
values
  (
    '10000000-0000-0000-0000-000000000001',
    'mahasiswa',
    'Student One',
    '100000000001'
  ),
  (
    '10000000-0000-0000-0000-000000000002',
    'mahasiswa',
    'Student Two',
    '100000000002'
  ),
  (
    '20000000-0000-0000-0000-000000000001',
    'dosen',
    'Lecturer',
    '200000000001'
  ),
  (
    '30000000-0000-0000-0000-000000000001',
    'admin',
    'Administrator',
    '300000000001'
  );

insert into public.mata_kuliah (id, nama_matkul, nama_dosen, kode_matkul)
values
  (
    '40000000-0000-0000-0000-000000000001',
    'Assigned Course',
    'Lecturer',
    'TEST-1'
  ),
  (
    '40000000-0000-0000-0000-000000000002',
    'Other Course',
    'Other Lecturer',
    'TEST-2'
  );

insert into public.mahasiswa_mata_kuliah (
  mahasiswa_id,
  mata_kuliah_id
)
values
  (
    '10000000-0000-0000-0000-000000000001',
    '40000000-0000-0000-0000-000000000001'
  ),
  (
    '10000000-0000-0000-0000-000000000002',
    '40000000-0000-0000-0000-000000000002'
  );

insert into public.dosen_mata_kuliah (dosen_id, mata_kuliah_id)
values (
  '20000000-0000-0000-0000-000000000001',
  '40000000-0000-0000-0000-000000000001'
);

insert into public.pengumpulan_tugas (
  id,
  mahasiswa_id,
  mata_kuliah_id,
  status_submit,
  ai_status
)
values
  (
    '50000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '40000000-0000-0000-0000-000000000001',
    'draft',
    'idle'
  ),
  (
    '50000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000002',
    '40000000-0000-0000-0000-000000000002',
    'draft',
    'idle'
  );

set local role authenticated;
select set_config(
  'request.jwt.claims',
  '{"sub":"10000000-0000-0000-0000-000000000001","role":"authenticated"}',
  true
);

select is(
  (select count(*) from public.pengumpulan_tugas),
  1::bigint,
  'student sees only their submission'
);
select is(
  (select count(*) from public.audit_log),
  0::bigint,
  'student cannot read audit rows'
);
select throws_ok(
  $$update public.pengumpulan_tugas set nilai_akhir = 100$$,
  '42501',
  null,
  'student cannot directly change a score'
);
select throws_ok(
  $$insert into public.profil_pengguna (
      id, role, nama_lengkap, nim_nip
    ) values (
      '10000000-0000-0000-0000-000000000001',
      'admin',
      'Escalated',
      '999999999999'
    )$$,
  '42501',
  null,
  'student cannot create an admin profile'
);

select set_config(
  'request.jwt.claims',
  '{"sub":"20000000-0000-0000-0000-000000000001","role":"authenticated"}',
  true
);

select is(
  (select count(*) from public.pengumpulan_tugas),
  1::bigint,
  'lecturer sees only submissions in assigned courses'
);
select is(
  (
    select mahasiswa_id
    from public.pengumpulan_tugas
    limit 1
  ),
  '10000000-0000-0000-0000-000000000001'::uuid,
  'lecturer sees the assigned student'
);

select set_config(
  'request.jwt.claims',
  '{"sub":"30000000-0000-0000-0000-000000000001","role":"authenticated"}',
  true
);

select is(
  (select count(*) from public.pengumpulan_tugas),
  2::bigint,
  'admin can read all submissions'
);
select lives_ok(
  $$update public.system_settings
    set setting_value = 'true'
    where setting_key = 'verbose_logging'$$,
  'admin can update system settings'
);

set local role service_role;
select set_config(
  'request.jwt.claims',
  '{"role":"service_role"}',
  true
);

select is(
  (
    public.admin_reset_demo_data(true, true)
    ->> 'submissions_deleted'
  )::integer,
  2,
  'demo reset reports deleted submissions'
);
select is(
  (select count(*) from public.pengumpulan_tugas),
  0::bigint,
  'demo reset deletes every submission with an explicit predicate'
);
select is(
  (select count(*) from public.mahasiswa_mata_kuliah),
  0::bigint,
  'demo reset deletes every enrollment with an explicit predicate'
);

select * from finish();
rollback;
