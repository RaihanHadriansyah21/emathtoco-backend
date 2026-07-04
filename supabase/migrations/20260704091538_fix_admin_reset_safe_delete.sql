-- Keep Supabase's safeupdate protection enabled while allowing this intentional
-- admin-only bulk reset. Both target columns are primary keys and therefore
-- cannot be null, so these predicates select every existing row explicitly.
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

    delete from public.pengumpulan_tugas as submission
    where submission.id is not null;
  end if;

  if p_delete_enrollments then
    select count(*) into enrollment_count
    from public.mahasiswa_mata_kuliah;

    delete from public.mahasiswa_mata_kuliah as enrollment
    where enrollment.id is not null;
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

revoke all on function public.admin_reset_demo_data(boolean, boolean)
from public, anon, authenticated;
grant execute on function public.admin_reset_demo_data(boolean, boolean)
to service_role;
