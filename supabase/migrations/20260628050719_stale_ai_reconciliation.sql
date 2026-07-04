create or replace function public.reconcile_stale_ai_jobs(
  p_stale_before timestamptz
)
returns setof uuid
language plpgsql
security definer
set search_path = ''
as $$
begin
  if coalesce((select auth.role()), '') <> 'service_role' then
    raise exception using errcode = '42501', message = 'service_role_required';
  end if;

  if p_stale_before is null
     or p_stale_before > now() - interval '5 minutes'
     or p_stale_before < now() - interval '7 days' then
    raise exception using errcode = '22023', message = 'invalid_stale_cutoff';
  end if;

  return query
  with stale as (
    update public.pengumpulan_tugas as submission
    set
      status_submit = 'failed',
      ai_status = 'failed',
      ai_processed_at = now()
    where submission.status_submit = 'processing_ai'
      and submission.ai_status = 'processing'
      and submission.updated_at < p_stale_before
    returning submission.id
  ),
  audit_rows as (
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
    select
      'system',
      'AI_PROCESS_STALE_RECONCILED',
      'pengumpulan_tugas',
      stale.id::text,
      'A stale AI processing state was reconciled.',
      'system',
      'AI_PROCESS_STALE_RECONCILED',
      'pengumpulan_tugas',
      jsonb_build_object('error_code', 'AI_JOB_STALE')
    from stale
    returning target_id
  )
  select stale.id
  from stale
  left join audit_rows on audit_rows.target_id = stale.id::text;
end;
$$;

revoke all on function public.reconcile_stale_ai_jobs(timestamptz)
from public, anon, authenticated;
grant execute on function public.reconcile_stale_ai_jobs(timestamptz)
to service_role;
