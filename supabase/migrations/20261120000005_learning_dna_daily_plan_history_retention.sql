-- =============================================================================
-- Think_First (CodeMentor AI) — Phase 6 Schema Migration
-- Learning DNA Snapshots, Adaptive Daily Learning Plans, Persistent Timeline
-- Support, and Spaced Retention Verification
-- =============================================================================

-- 1. Evidence-based Learning DNA Snapshots
CREATE TABLE IF NOT EXISTS public.learning_dna_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    selected_track_slug VARCHAR(48) NOT NULL REFERENCES public.learning_tracks(slug) ON DELETE RESTRICT,
    dimensions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    skill_state_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    strengths TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    growth_areas TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    source_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_dna_snapshots_student_time
    ON public.learning_dna_snapshots (student_id, computed_at DESC);

-- 2. Adaptive Daily Learning Plans (versioned per date for plan regeneration history)
CREATE TABLE IF NOT EXISTS public.daily_learning_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    plan_date DATE NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1 CHECK (version_number >= 1),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    selected_track_slug VARCHAR(48) NOT NULL REFERENCES public.learning_tracks(slug) ON DELETE RESTRICT,
    available_minutes INTEGER NOT NULL DEFAULT 45 CHECK (available_minutes BETWEEN 15 AND 240),
    total_estimated_minutes INTEGER NOT NULL DEFAULT 0 CHECK (total_estimated_minutes >= 0),
    generation_reason_en TEXT NOT NULL DEFAULT '',
    generation_reason_bn TEXT NOT NULL DEFAULT '',
    evidence_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (student_id, plan_date, version_number)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_learning_plans_active_unique
    ON public.daily_learning_plans (student_id, plan_date)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_daily_learning_plans_student_date
    ON public.daily_learning_plans (student_id, plan_date DESC, version_number DESC);

-- 3. Adaptive Daily Plan Tasks
CREATE TABLE IF NOT EXISTS public.daily_plan_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES public.daily_learning_plans(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    task_order INTEGER NOT NULL CHECK (task_order >= 1),
    task_type VARCHAR(32) NOT NULL CHECK (
        task_type IN ('diagnostic', 'lesson', 'problem', 'debugging', 'transfer', 'retention')
    ),
    skill_slug VARCHAR(64) REFERENCES public.skill_nodes(slug) ON DELETE SET NULL,
    target_id TEXT NOT NULL,
    target_slug TEXT NOT NULL,
    title_en TEXT NOT NULL,
    title_bn TEXT NOT NULL,
    reason_en TEXT NOT NULL,
    reason_bn TEXT NOT NULL,
    href TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL DEFAULT 15 CHECK (estimated_minutes BETWEEN 5 AND 120),
    status VARCHAR(24) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
    completed_at TIMESTAMPTZ,
    completion_evidence_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_plan_tasks_plan_order
    ON public.daily_plan_tasks (plan_id, task_order ASC);

CREATE INDEX IF NOT EXISTS idx_daily_plan_tasks_student_status
    ON public.daily_plan_tasks (student_id, status, updated_at DESC);

-- 4. Retention Verification Schedules
CREATE TABLE IF NOT EXISTS public.retention_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    skill_slug VARCHAR(64) NOT NULL REFERENCES public.skill_nodes(slug) ON DELETE CASCADE,
    problem_id UUID NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
    source_evidence_type VARCHAR(48) NOT NULL CHECK (
        source_evidence_type IN (
            'phase4_transfer',
            'zero_hint_submit',
            'diagnostic_code_check',
            'lesson_guided_pass'
        )
    ),
    source_evidence_ref_id TEXT,
    source_verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_at TIMESTAMPTZ NOT NULL,
    interval_hours INTEGER NOT NULL DEFAULT 24 CHECK (interval_hours >= 24),
    status VARCHAR(24) NOT NULL DEFAULT 'scheduled' CHECK (
        status IN ('scheduled', 'due', 'passed_retained', 'needs_review')
    ),
    last_attempt_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_retention_schedules_student_due
    ON public.retention_schedules (student_id, due_at ASC);

CREATE INDEX IF NOT EXISTS idx_retention_schedules_student_skill
    ON public.retention_schedules (student_id, skill_slug, created_at DESC);

-- 5. Retention Verification Attempts (backed by real Judge0 submissions)
CREATE TABLE IF NOT EXISTS public.retention_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES public.retention_schedules(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    skill_slug VARCHAR(64) NOT NULL REFERENCES public.skill_nodes(slug) ON DELETE CASCADE,
    problem_id UUID NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
    submission_id UUID REFERENCES public.submissions(id) ON DELETE SET NULL,
    language_slug VARCHAR(32) NOT NULL DEFAULT 'python',
    source_code TEXT NOT NULL,
    student_explanation TEXT NOT NULL,
    verdict VARCHAR(32) NOT NULL,
    passed_tests INTEGER NOT NULL DEFAULT 0,
    total_tests INTEGER NOT NULL DEFAULT 0,
    elapsed_hours_since_initial DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    outcome VARCHAR(32) NOT NULL CHECK (
        outcome IN ('retained_verified', 'passed_too_early', 'needs_review')
    ),
    summary_message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_retention_attempts_student_time
    ON public.retention_attempts (student_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_retention_attempts_schedule
    ON public.retention_attempts (schedule_id, created_at DESC);

-- =============================================================================
-- Updated-at triggers (reusing public.set_updated_at() from Phase 2 migration)
-- =============================================================================
DROP TRIGGER IF EXISTS trg_daily_learning_plans_updated_at ON public.daily_learning_plans;
CREATE TRIGGER trg_daily_learning_plans_updated_at
    BEFORE UPDATE ON public.daily_learning_plans
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_daily_plan_tasks_updated_at ON public.daily_plan_tasks;
CREATE TRIGGER trg_daily_plan_tasks_updated_at
    BEFORE UPDATE ON public.daily_plan_tasks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_retention_schedules_updated_at ON public.retention_schedules;
CREATE TRIGGER trg_retention_schedules_updated_at
    BEFORE UPDATE ON public.retention_schedules
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- Strict Row-Level Security (FORCE ROW LEVEL SECURITY on all 5 Phase 6 tables)
-- =============================================================================
ALTER TABLE public.learning_dna_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_dna_snapshots FORCE ROW LEVEL SECURITY;

ALTER TABLE public.daily_learning_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_learning_plans FORCE ROW LEVEL SECURITY;

ALTER TABLE public.daily_plan_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_plan_tasks FORCE ROW LEVEL SECURITY;

ALTER TABLE public.retention_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.retention_schedules FORCE ROW LEVEL SECURITY;

ALTER TABLE public.retention_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.retention_attempts FORCE ROW LEVEL SECURITY;

-- Student own-row + admin policies for learning_dna_snapshots
DROP POLICY IF EXISTS learning_dna_snapshots_owner_select ON public.learning_dna_snapshots;
CREATE POLICY learning_dna_snapshots_owner_select ON public.learning_dna_snapshots
    FOR SELECT USING (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'));

DROP POLICY IF EXISTS learning_dna_snapshots_owner_insert ON public.learning_dna_snapshots;
CREATE POLICY learning_dna_snapshots_owner_insert ON public.learning_dna_snapshots
    FOR INSERT WITH CHECK (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'));

-- Student own-row + admin policies for daily_learning_plans
DROP POLICY IF EXISTS daily_learning_plans_owner_all ON public.daily_learning_plans;
CREATE POLICY daily_learning_plans_owner_all ON public.daily_learning_plans
    FOR ALL
    USING (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'))
    WITH CHECK (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'));

-- Student own-row + admin policies for daily_plan_tasks
DROP POLICY IF EXISTS daily_plan_tasks_owner_all ON public.daily_plan_tasks;
CREATE POLICY daily_plan_tasks_owner_all ON public.daily_plan_tasks
    FOR ALL
    USING (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'))
    WITH CHECK (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'));

-- Student own-row + admin policies for retention_schedules
DROP POLICY IF EXISTS retention_schedules_owner_all ON public.retention_schedules;
CREATE POLICY retention_schedules_owner_all ON public.retention_schedules
    FOR ALL
    USING (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'))
    WITH CHECK (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'));

-- Student own-row + admin policies for retention_attempts
DROP POLICY IF EXISTS retention_attempts_owner_select ON public.retention_attempts;
CREATE POLICY retention_attempts_owner_select ON public.retention_attempts
    FOR SELECT USING (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'));

DROP POLICY IF EXISTS retention_attempts_owner_insert ON public.retention_attempts;
CREATE POLICY retention_attempts_owner_insert ON public.retention_attempts
    FOR INSERT WITH CHECK (student_id = auth.uid() OR public.has_role(auth.uid(), 'admin'));
