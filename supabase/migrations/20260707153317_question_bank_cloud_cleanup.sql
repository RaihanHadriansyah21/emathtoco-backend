-- Cleanup drift from earlier failed question-bank apply attempts.
-- Removes obsolete duplicate policies/functions and adds covering FK indexes.

drop function if exists public.create_class_join_session(uuid, text, timestamptz, integer, text);

drop policy if exists question_sets_select_authorized on public.question_sets;
drop policy if exists question_sets_insert_authorized on public.question_sets;
drop policy if exists question_sets_update_authorized on public.question_sets;
drop policy if exists question_sets_delete_authorized on public.question_sets;

drop policy if exists question_sections_select_authorized on public.question_sections;
drop policy if exists question_sections_insert_authorized on public.question_sections;
drop policy if exists question_sections_update_authorized on public.question_sections;
drop policy if exists question_sections_delete_authorized on public.question_sections;

drop policy if exists question_assets_select_authorized on public.question_assets;
drop policy if exists question_assets_insert_authorized on public.question_assets;
drop policy if exists question_assets_delete_authorized on public.question_assets;

drop policy if exists join_session_select_authorized on public.class_join_sessions;

create index if not exists class_join_logs_student_id_idx
on public.class_join_logs(student_id);

create index if not exists class_join_sessions_created_by_idx
on public.class_join_sessions(created_by);

create index if not exists question_assets_uploaded_by_idx
on public.question_assets(uploaded_by);

create index if not exists question_sets_created_by_idx
on public.question_sets(created_by);
