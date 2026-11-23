-- =============================================================================
-- Migration 0010: Outbound Execution Worker Queue (Free Local Judge0 Bridge)
-- Strictly additive, non-destructive migration preserving all existing 55 tables,
-- curriculum, student submissions, progress, and RLS policies.
--
-- Rollback instructions (safe because no existing tables are altered):
--   DROP TABLE IF EXISTS public.execution_jobs;
--   DROP TABLE IF EXISTS public.execution_workers;
-- =============================================================================

-- 1. Registered Outbound Execution Workers (heartbeats & liveness observability)
CREATE TABLE IF NOT EXISTS public.execution_workers (
    worker_id text PRIMARY KEY CHECK (worker_id ~ '^[a-zA-Z0-9._-]{3,64}$'),
    display_name text NOT NULL DEFAULT 'Local Judge0 Runner',
    status text NOT NULL DEFAULT 'online'
        CHECK (status IN ('online', 'draining', 'offline')),
    judge0_version text,
    supported_languages text[] NOT NULL DEFAULT '{}',
    active_job_count integer NOT NULL DEFAULT 0 CHECK (active_job_count >= 0),
    total_jobs_completed integer NOT NULL DEFAULT 0 CHECK (total_jobs_completed >= 0),
    total_jobs_failed integer NOT NULL DEFAULT 0 CHECK (total_jobs_failed >= 0),
    last_heartbeat_at timestamptz NOT NULL DEFAULT now(),
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_execution_workers_status_hb
    ON public.execution_workers (status, last_heartbeat_at DESC);

DROP TRIGGER IF EXISTS trg_execution_workers_updated_at ON public.execution_workers;
CREATE TRIGGER trg_execution_workers_updated_at
    BEFORE UPDATE ON public.execution_workers
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 2. Transactional Outbound Execution Jobs Queue
CREATE TABLE IF NOT EXISTS public.execution_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type text NOT NULL CHECK (job_type IN ('submission', 'test_case')),
    submission_id uuid REFERENCES public.submissions(id) ON DELETE CASCADE,
    requested_by uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    language_slug text NOT NULL REFERENCES public.supported_languages(slug) ON DELETE RESTRICT,
    judge0_language_id integer NOT NULL CHECK (judge0_language_id > 0),
    dedup_hash text,
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'timed_out')),
    payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    result_json jsonb,
    claimed_by_worker_id text REFERENCES public.execution_workers(worker_id) ON DELETE SET NULL,
    claim_token uuid,
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts integer NOT NULL DEFAULT 2 CHECK (max_attempts >= 1 AND max_attempts <= 5),
    error_code text,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    claimed_at timestamptz,
    lease_expires_at timestamptz,
    expires_at timestamptz NOT NULL,
    completed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_execution_jobs_claimable
    ON public.execution_jobs (created_at ASC)
    WHERE status = 'queued';

CREATE INDEX IF NOT EXISTS idx_execution_jobs_submission
    ON public.execution_jobs (submission_id)
    WHERE submission_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_execution_jobs_user_active
    ON public.execution_jobs (requested_by, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_execution_jobs_lease
    ON public.execution_jobs (status, lease_expires_at)
    WHERE status IN ('queued', 'running');

DROP TRIGGER IF EXISTS trg_execution_jobs_updated_at ON public.execution_jobs;
CREATE TRIGGER trg_execution_jobs_updated_at
    BEFORE UPDATE ON public.execution_jobs
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 3. Strict Row Level Security (100% FORCE RLS across all public.* tables)
ALTER TABLE public.execution_workers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.execution_workers FORCE ROW LEVEL SECURITY;

ALTER TABLE public.execution_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.execution_jobs FORCE ROW LEVEL SECURITY;

-- Only Admins may inspect internal worker/job tables directly via PostgREST.
-- Payload may include hidden test cases; students receive sanitized responses strictly via FastAPI.
DROP POLICY IF EXISTS execution_workers_admin_select ON public.execution_workers;
CREATE POLICY execution_workers_admin_select
    ON public.execution_workers FOR SELECT TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));

DROP POLICY IF EXISTS execution_jobs_admin_select ON public.execution_jobs;
CREATE POLICY execution_jobs_admin_select
    ON public.execution_jobs FOR SELECT TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));
