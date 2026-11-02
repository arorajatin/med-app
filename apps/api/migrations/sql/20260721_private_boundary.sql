-- This file belongs to the sole undeployed Alembic baseline.
-- Runtime roles never own tables, bypass RLS, or obtain the signing secret.
CREATE SCHEMA med_app_private;
REVOKE ALL ON SCHEMA med_app_private FROM PUBLIC;
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

DO $roles$
DECLARE role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY['med_app_api', 'med_app_request', 'med_app_storage', 'med_app_cleanup'] LOOP
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', role_name);
        END IF;
    END LOOP;
END
$roles$;
GRANT med_app_request TO med_app_api;
GRANT USAGE ON SCHEMA public, med_app_private TO med_app_request;
GRANT USAGE ON SCHEMA med_app_private TO med_app_api, med_app_cleanup;
GRANT SELECT ON public.alembic_version TO med_app_api;

CREATE TABLE med_app_private.configuration (
    key text PRIMARY KEY,
    value text NOT NULL
);
REVOKE ALL ON med_app_private.configuration FROM PUBLIC;

CREATE FUNCTION med_app_private.subject() RETURNS text
LANGUAGE sql STABLE SET search_path = pg_catalog AS $fn$
    SELECT nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'
$fn$;

CREATE FUNCTION med_app_private.current_account() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $fn$
    SELECT account_id FROM public.auth_identities
    WHERE provider = 'supabase' AND provider_subject = med_app_private.subject()
$fn$;

-- Account creation is the only privileged row mutation in a normal request.
-- It derives the subject from verified transaction claims, never an account ID.
CREATE FUNCTION med_app_private.ensure_account(verified_email text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $fn$
DECLARE subject_id text := med_app_private.subject(); owned_account text;
BEGIN
    IF subject_id IS NULL OR subject_id = '' THEN
        RAISE EXCEPTION 'Verified identity required' USING ERRCODE = '42501';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(subject_id, 0));
    SELECT account_id INTO owned_account FROM public.auth_identities
        WHERE provider = 'supabase' AND provider_subject = subject_id;
    IF owned_account IS NULL THEN
        owned_account := gen_random_uuid()::text;
        INSERT INTO public.accounts(id, onboarding_status, created_at, updated_at)
            VALUES (owned_account, 'not_started', now(), now());
        INSERT INTO public.auth_identities(id, account_id, provider, provider_subject,
            upstream_provider, email, verified_at, created_at)
            VALUES (gen_random_uuid()::text, owned_account, 'supabase', subject_id,
                'google', verified_email, now(), now());
    ELSE
        UPDATE public.auth_identities SET email = verified_email, upstream_provider = 'google'
            WHERE account_id = owned_account AND provider = 'supabase' AND provider_subject = subject_id;
    END IF;
END
$fn$;

DO $policies$
DECLARE table_name text; client_role text;
BEGIN
    FOR table_name IN
        SELECT c.table_name FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.column_name = 'account_id'
        UNION ALL SELECT 'accounts'
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC', table_name);
        FOREACH client_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = client_role) THEN
                EXECUTE format('REVOKE ALL ON public.%I FROM %I', table_name, client_role);
            END IF;
        END LOOP;
        IF table_name = 'accounts' THEN
            EXECUTE 'CREATE POLICY owner_rows ON public.accounts TO med_app_request
                USING (id = (SELECT med_app_private.current_account()))
                WITH CHECK (id = (SELECT med_app_private.current_account()))';
            GRANT SELECT ON public.accounts TO med_app_request;
            GRANT UPDATE(onboarding_status, updated_at) ON public.accounts TO med_app_request;
        ELSIF table_name = 'auth_identities' THEN
            EXECUTE 'CREATE POLICY owner_rows ON public.auth_identities TO med_app_request
                USING (provider = ''supabase'' AND provider_subject = (SELECT med_app_private.subject()))';
            GRANT SELECT ON public.auth_identities TO med_app_request;
        ELSE
            EXECUTE format('CREATE POLICY owner_rows ON public.%I TO med_app_request
                USING (account_id = (SELECT med_app_private.current_account()))
                WITH CHECK (account_id = (SELECT med_app_private.current_account()))', table_name);
            EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO med_app_request', table_name);
        END IF;
    END LOOP;
END
$policies$;

CREATE FUNCTION med_app_private.base64url(payload bytea) RETURNS text
LANGUAGE sql IMMUTABLE SET search_path = pg_catalog AS $fn$
    SELECT translate(replace(encode(payload, 'base64'), E'\n', ''), '+/=', '-_')
$fn$;

-- Internal signer: no workload role can call this function or read configuration.
CREATE FUNCTION med_app_private.sign_storage_token(subject_id text, owned_account text,
    object_key text, operation text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $fn$
DECLARE secret text; project_url text; header text; payload text; unsigned text;
BEGIN
    SELECT value INTO secret FROM med_app_private.configuration WHERE key = 'storage_jwt_secret';
    SELECT value INTO project_url FROM med_app_private.configuration WHERE key = 'supabase_url';
    IF secret IS NULL OR length(secret) < 32 OR project_url IS NULL THEN
        RAISE EXCEPTION 'Private storage is not configured' USING ERRCODE = '55000';
    END IF;
    header := med_app_private.base64url(convert_to(jsonb_build_object('alg', 'HS256', 'typ', 'JWT')::text, 'utf8'));
    payload := med_app_private.base64url(convert_to(jsonb_build_object(
        'iss', project_url || '/auth/v1', 'sub', subject_id, 'role', 'med_app_storage',
        'iat', floor(extract(epoch FROM clock_timestamp())),
        'exp', floor(extract(epoch FROM clock_timestamp())) + 60,
        'account_id', owned_account, 'object_key', object_key, 'operation', operation
    )::text, 'utf8'));
    unsigned := header || '.' || payload;
    RETURN unsigned || '.' || med_app_private.base64url(
        extensions.hmac(convert_to(unsigned, 'utf8'), convert_to(secret, 'utf8'), 'sha256'));
END
$fn$;

CREATE FUNCTION med_app_private.issue_storage_token(operation text, object_key text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $fn$
DECLARE owned_account text := med_app_private.current_account();
BEGIN
    IF owned_account IS NULL OR split_part(object_key, '/', 2) <> owned_account
       OR object_key !~ '^accounts/[0-9a-f-]{36}/ingestions/[0-9a-f-]{36}/parts/[0-9a-f-]{36}/[0-9a-f-]{36}$'
       OR operation NOT IN ('upload', 'verify', 'read', 'delete') THEN
        RAISE EXCEPTION 'Object not available' USING ERRCODE = '42501';
    END IF;
    IF operation IN ('upload', 'verify') AND NOT EXISTS (
        SELECT FROM public.ingestions i WHERE i.id = split_part(object_key, '/', 4)
        AND i.account_id = owned_account AND i.upload_state = 'receiving' AND i.tombstoned_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Upload not available' USING ERRCODE = '42501';
    END IF;
    IF operation = 'read' AND NOT EXISTS (
        SELECT FROM public.ingestion_parts p JOIN public.ingestions i ON i.id = p.ingestion_id
        WHERE p.object_key = issue_storage_token.object_key AND p.account_id = owned_account
        AND i.account_id = owned_account AND i.upload_state = 'complete' AND i.tombstoned_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Report not available' USING ERRCODE = '42501';
    END IF;
    IF operation = 'delete' AND EXISTS (
        SELECT FROM public.ingestion_parts p JOIN public.ingestions i ON i.id = p.ingestion_id
        WHERE p.object_key = issue_storage_token.object_key AND i.tombstoned_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Live report cannot be purged' USING ERRCODE = '42501';
    END IF;
    RETURN med_app_private.sign_storage_token(med_app_private.subject(), owned_account, object_key, operation);
END
$fn$;

-- Cleanup can enumerate only opaque due IDs. It cannot select private tables.
CREATE FUNCTION med_app_private.due_cleanup_ids(batch_size integer) RETURNS SETOF text
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog AS $fn$
    SELECT id FROM public.storage_cleanup_intents WHERE reconcile_after <= now()
    ORDER BY reconcile_after, id LIMIT greatest(1, least(batch_size, 100))
$fn$;

CREATE FUNCTION med_app_private.claim_cleanup(work_id text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $fn$
DECLARE work public.storage_cleanup_intents; subject_id text;
BEGIN
    SELECT * INTO work FROM public.storage_cleanup_intents WHERE id = work_id
        AND reconcile_after <= now() FOR UPDATE SKIP LOCKED;
    IF NOT FOUND THEN RETURN NULL; END IF;
    -- A completed metadata transaction owns this object. Preserve it and finish
    -- the intent left behind by the original upload, including after a crash.
    IF EXISTS (SELECT FROM public.ingestion_parts p JOIN public.ingestions i ON i.id = p.ingestion_id
        WHERE p.object_key = work.object_key AND i.tombstoned_at IS NULL) THEN
        DELETE FROM public.storage_cleanup_intents WHERE id = work.id;
        RETURN NULL;
    END IF;
    -- Fence a stalled source transaction: once cleanup has claimed the intent,
    -- that upload cannot finish. The API locks its intent before metadata commit.
    UPDATE public.storage_cleanup_intents SET state = 'cleaning', reconcile_after = now() + interval '5 minutes'
        WHERE id = work.id;
    SELECT provider_subject INTO subject_id FROM public.auth_identities
        WHERE account_id = work.account_id AND provider = 'supabase';
    RETURN jsonb_build_object('id', work.id, 'account_id', work.account_id,
        'object_key', work.object_key, 'bucket', work.storage_bucket,
        'token', med_app_private.sign_storage_token(subject_id, work.account_id, work.object_key, 'delete'));
END
$fn$;

CREATE FUNCTION med_app_private.complete_cleanup(work_id text) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog AS $fn$
    DELETE FROM public.storage_cleanup_intents WHERE id = work_id AND state = 'cleaning'
$fn$;

CREATE FUNCTION med_app_private.boundary_status() RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $fn$
DECLARE bucket_private boolean := false; policies_present boolean := false;
BEGIN
    IF to_regclass('storage.buckets') IS NOT NULL THEN
        EXECUTE 'SELECT EXISTS(SELECT FROM storage.buckets WHERE id = ''medical-records'' AND NOT public)'
            INTO bucket_private;
        SELECT count(*) = 8 INTO policies_present FROM pg_policies
            WHERE schemaname = 'storage' AND policyname IN ('med_app_private_bucket',
                'med_app_bucket_read', 'med_app_object_boundary', 'med_app_object_upload',
                'med_app_object_read', 'med_app_object_delete', 'med_app_object_access',
                'med_app_object_no_replace');
        policies_present := policies_present AND NOT EXISTS (
            SELECT FROM pg_policies WHERE schemaname = 'storage'
            AND policyname IN ('med_app_private_bucket', 'med_app_object_boundary',
                'med_app_object_upload', 'med_app_object_read', 'med_app_object_delete',
                'med_app_object_no_replace') AND permissive <> 'RESTRICTIVE');
        policies_present := policies_present AND NOT EXISTS (
            SELECT FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'storage' AND c.relname IN ('objects', 'buckets') AND NOT c.relrowsecurity);
    END IF;
    RETURN jsonb_build_object(
        'login', session_user,
        'roles_safe', NOT EXISTS (SELECT FROM pg_roles r WHERE
            (r.rolname IN ('med_app_api', 'med_app_request', 'med_app_storage', 'med_app_cleanup')
                OR pg_has_role('med_app_api', r.oid, 'MEMBER')
                OR pg_has_role('med_app_request', r.oid, 'MEMBER')
                OR pg_has_role('med_app_storage', r.oid, 'MEMBER')
                OR pg_has_role('med_app_cleanup', r.oid, 'MEMBER'))
            AND (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb
                OR EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relowner = r.oid AND n.nspname IN ('public', 'med_app_private', 'storage')))),
        'rls_enabled', NOT EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> 'alembic_version'
            AND NOT c.relrowsecurity),
        'bucket_private', bucket_private,
        'storage_policies', policies_present,
        'version', '20260916_upload_storage_v1',
        'project_ref', (SELECT value FROM med_app_private.configuration WHERE key = 'project_ref'),
        'region', (SELECT value FROM med_app_private.configuration WHERE key = 'region')
    );
END
$fn$;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA med_app_private FROM PUBLIC;
GRANT EXECUTE ON FUNCTION med_app_private.subject(), med_app_private.current_account(),
    med_app_private.ensure_account(text), med_app_private.issue_storage_token(text, text) TO med_app_request;
GRANT EXECUTE ON FUNCTION med_app_private.due_cleanup_ids(integer), med_app_private.claim_cleanup(text),
    med_app_private.complete_cleanup(text) TO med_app_cleanup;
GRANT EXECUTE ON FUNCTION med_app_private.boundary_status() TO med_app_api, med_app_cleanup;
