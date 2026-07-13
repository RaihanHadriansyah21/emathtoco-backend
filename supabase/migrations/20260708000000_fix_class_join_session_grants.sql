-- Perbaikan drift keamanan pada fungsi QR join kelas.
--
-- Root cause: migration `question_bank_cloud_cleanup` men-drop dan membuat
-- ulang `create_class_join_session` dengan signature baru (menambah
-- `p_token_raw text`) tanpa menerapkan ulang REVOKE dari public/anon.
-- PostgreSQL memberi grant EXECUTE default ke PUBLIC saat fungsi baru dibuat,
-- sehingga `create_class_join_session` dan `revoke_class_join_session`
-- (yang ikut dibuat ulang) sempat bisa dipanggil oleh peran `anon` melalui
-- `/rest/v1/rpc/...` walau internalnya tetap menolak (FORBIDDEN) karena
-- `app_private.is_admin()` / `is_lecturer_for_course()` mengembalikan false
-- untuk pengguna anonim. Tetap harus ditutup sebagai defense-in-depth dan
-- untuk menghapus temuan Supabase security advisor
-- `anon_security_definer_function_executable`.
--
-- Kedua fungsi ini SECURITY DEFINER dan hanya boleh dipanggil oleh dosen/admin
-- yang sudah authenticated.

-- Cloud already had the five-argument overload when this migration was first
-- applied, while a bootstrap from an empty database did not. Guard the grant
-- repair so historical drift cannot make `db reset` fail before the forward
-- parity migration creates the canonical function.
do $$
begin
  if to_regprocedure(
    'public.create_class_join_session(uuid,text,timestamptz,integer,text)'
  ) is not null then
    execute 'revoke all on function public.create_class_join_session(uuid, text, timestamptz, integer, text) from public, anon';
    execute 'grant execute on function public.create_class_join_session(uuid, text, timestamptz, integer, text) to authenticated, service_role';
  end if;

  if to_regprocedure('public.revoke_class_join_session(uuid)') is not null then
    execute 'revoke all on function public.revoke_class_join_session(uuid) from public, anon';
    execute 'grant execute on function public.revoke_class_join_session(uuid) to authenticated, service_role';
  end if;
end;
$$;
