-- migration_profile_image.sql
-- Step 1: Add foto_profil_url column to public.profil_pengguna
ALTER TABLE public.profil_pengguna ADD COLUMN IF NOT EXISTS foto_profil_url TEXT;

-- Step 2: Configure storage policies for the 'profile-images' bucket
-- Allow public select access to the profile-images bucket
CREATE POLICY "Public Read Access for Avatars" ON storage.objects
  FOR SELECT USING (bucket_id = 'profile-images');

-- Allow authenticated users to insert/update/delete their own avatar under their UUID folder
CREATE POLICY "Allow authenticated users to insert their own avatar" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'profile-images' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "Allow authenticated users to update their own avatar" ON storage.objects
  FOR UPDATE TO authenticated
  USING (bucket_id = 'profile-images' AND (storage.foldername(name))[1] = auth.uid()::text)
  WITH CHECK (bucket_id = 'profile-images' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "Allow authenticated users to delete their own avatar" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'profile-images' AND (storage.foldername(name))[1] = auth.uid()::text);
