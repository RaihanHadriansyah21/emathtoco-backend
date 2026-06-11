-- migration_check_email.sql
-- Create a helper function running as SECURITY DEFINER to check if an email exists in auth.users
CREATE OR REPLACE FUNCTION public.check_email_exists(email_to_check text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER -- runs with service_role/admin privileges to query auth.users
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM auth.users WHERE email = email_to_check
  );
END;
$$;

-- Grant execute permission to both guest (anon) and authenticated roles
GRANT EXECUTE ON FUNCTION public.check_email_exists(text) TO anon, authenticated;
