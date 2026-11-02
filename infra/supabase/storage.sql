-- Apply after the Alembic baseline using a provisioning connection only.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('medical-records', 'medical-records', false, 15000000,
    ARRAY['application/pdf', 'image/jpeg', 'image/png'])
ON CONFLICT (id) DO UPDATE SET public = false, file_size_limit = 15000000,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

GRANT med_app_storage TO authenticator;
-- Hosted Storage switches JWT roles through authenticator. Its reserved
-- supabase_storage_admin role cannot be modified by the provisioning login.
GRANT USAGE ON SCHEMA storage TO med_app_storage;
GRANT SELECT, INSERT, DELETE ON storage.objects TO med_app_storage;
GRANT SELECT ON storage.buckets TO med_app_storage;

-- Restrictive policies protect this bucket even if an unrelated bucket later
-- gains a broad permissive policy. Normal browser JWTs cannot use these grants.
DROP POLICY IF EXISTS med_app_private_bucket ON storage.buckets;
CREATE POLICY med_app_private_bucket ON storage.buckets AS RESTRICTIVE
TO PUBLIC USING (id <> 'medical-records' OR current_user = 'med_app_storage')
WITH CHECK (id <> 'medical-records' OR current_user = 'med_app_storage');

DROP POLICY IF EXISTS med_app_bucket_read ON storage.buckets;
CREATE POLICY med_app_bucket_read ON storage.buckets FOR SELECT TO med_app_storage
USING (id = 'medical-records' AND NOT public);

DROP POLICY IF EXISTS med_app_object_boundary ON storage.objects;
CREATE POLICY med_app_object_boundary ON storage.objects AS RESTRICTIVE
TO PUBLIC USING (bucket_id <> 'medical-records' OR (
    current_user = 'med_app_storage'
    AND name = (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'object_key')
    AND split_part(name, '/', 2) = (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'account_id')
)) WITH CHECK (bucket_id <> 'medical-records' OR (
    current_user = 'med_app_storage'
    AND name = (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'object_key')
    AND split_part(name, '/', 2) = (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'account_id')
));

DROP POLICY IF EXISTS med_app_object_upload ON storage.objects;
CREATE POLICY med_app_object_upload ON storage.objects AS RESTRICTIVE FOR INSERT TO med_app_storage
WITH CHECK (bucket_id = 'medical-records'
    AND (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'operation') = 'upload');

DROP POLICY IF EXISTS med_app_object_read ON storage.objects;
CREATE POLICY med_app_object_read ON storage.objects AS RESTRICTIVE FOR SELECT TO med_app_storage
USING (bucket_id = 'medical-records'
    AND (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'operation') IN ('read', 'verify', 'delete'));

DROP POLICY IF EXISTS med_app_object_delete ON storage.objects;
CREATE POLICY med_app_object_delete ON storage.objects AS RESTRICTIVE FOR DELETE TO med_app_storage
USING (bucket_id = 'medical-records'
    AND (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'operation') = 'delete');

DROP POLICY IF EXISTS med_app_object_access ON storage.objects;
CREATE POLICY med_app_object_access ON storage.objects FOR ALL TO med_app_storage
USING (bucket_id = 'medical-records') WITH CHECK (bucket_id = 'medical-records');

DROP POLICY IF EXISTS med_app_object_no_replace ON storage.objects;
CREATE POLICY med_app_object_no_replace ON storage.objects AS RESTRICTIVE FOR UPDATE TO PUBLIC
USING (bucket_id <> 'medical-records') WITH CHECK (bucket_id <> 'medical-records');
