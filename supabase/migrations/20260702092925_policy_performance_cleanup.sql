drop policy if exists profile_select_own on public.profil_pengguna;
drop policy if exists profile_select_admin on public.profil_pengguna;
drop policy if exists profile_select_assigned_student on public.profil_pengguna;
create policy profile_select_authorized
on public.profil_pengguna
for select to authenticated
using (
  (select auth.uid()) = id
  or app_private.is_admin()
  or (
    role = 'mahasiswa'
    and exists (
      select 1
      from public.mahasiswa_mata_kuliah as enrollment
      join public.dosen_mata_kuliah as assignment
        on assignment.mata_kuliah_id = enrollment.mata_kuliah_id
      where enrollment.mahasiswa_id = profil_pengguna.id
        and assignment.dosen_id = (select auth.uid())
    )
  )
);

drop policy if exists profile_update_self on public.profil_pengguna;
drop policy if exists profile_admin_update on public.profil_pengguna;
create policy profile_update_authorized
on public.profil_pengguna
for update to authenticated
using ((select auth.uid()) = id or app_private.is_admin())
with check ((select auth.uid()) = id or app_private.is_admin());

drop policy if exists enrollment_select_own on public.mahasiswa_mata_kuliah;
drop policy if exists enrollment_select_lecturer on public.mahasiswa_mata_kuliah;
drop policy if exists enrollment_admin_all on public.mahasiswa_mata_kuliah;
create policy enrollment_select_authorized
on public.mahasiswa_mata_kuliah
for select to authenticated
using (
  mahasiswa_id = (select auth.uid())
  or app_private.is_lecturer_for_course(mata_kuliah_id)
  or app_private.is_admin()
);
create policy enrollment_admin_insert
on public.mahasiswa_mata_kuliah
for insert to authenticated
with check (app_private.is_admin());
create policy enrollment_admin_update
on public.mahasiswa_mata_kuliah
for update to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());
create policy enrollment_admin_delete
on public.mahasiswa_mata_kuliah
for delete to authenticated
using (app_private.is_admin());

drop policy if exists assignment_select_own on public.dosen_mata_kuliah;
drop policy if exists assignment_admin_all on public.dosen_mata_kuliah;
create policy assignment_select_authorized
on public.dosen_mata_kuliah
for select to authenticated
using (dosen_id = (select auth.uid()) or app_private.is_admin());
create policy assignment_admin_insert
on public.dosen_mata_kuliah
for insert to authenticated
with check (app_private.is_admin());
create policy assignment_admin_update
on public.dosen_mata_kuliah
for update to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());
create policy assignment_admin_delete
on public.dosen_mata_kuliah
for delete to authenticated
using (app_private.is_admin());

drop policy if exists submission_select_owner on public.pengumpulan_tugas;
drop policy if exists submission_select_lecturer on public.pengumpulan_tugas;
drop policy if exists submission_select_admin on public.pengumpulan_tugas;
create policy submission_select_authorized
on public.pengumpulan_tugas
for select to authenticated
using (
  mahasiswa_id = (select auth.uid())
  or app_private.is_lecturer_for_course(mata_kuliah_id)
  or app_private.is_admin()
);

drop policy if exists settings_authenticated_select on public.system_settings;
drop policy if exists settings_admin_all on public.system_settings;
create policy settings_authenticated_select
on public.system_settings
for select to authenticated
using (true);
create policy settings_admin_insert
on public.system_settings
for insert to authenticated
with check (app_private.is_admin());
create policy settings_admin_update
on public.system_settings
for update to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());
create policy settings_admin_delete
on public.system_settings
for delete to authenticated
using (app_private.is_admin());

drop policy if exists models_authenticated_select on public.ai_models;
drop policy if exists models_admin_all on public.ai_models;
create policy models_authenticated_select
on public.ai_models
for select to authenticated
using (true);
create policy models_admin_insert
on public.ai_models
for insert to authenticated
with check (app_private.is_admin());
create policy models_admin_update
on public.ai_models
for update to authenticated
using (app_private.is_admin())
with check (app_private.is_admin());
create policy models_admin_delete
on public.ai_models
for delete to authenticated
using (app_private.is_admin());

drop index if exists public.idx_dosen_mk_dosen_id;
drop index if exists public.idx_dosen_mk_mk_id;
drop index if exists public.idx_mahasiswa_mk_mahasiswa_id;
drop index if exists public.idx_mahasiswa_mk_mk_id;
