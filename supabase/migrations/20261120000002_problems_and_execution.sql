-- =============================================================================
-- Migration 0002: Smart Problem Bank, Judge0 Execution, Revisions & Governance
-- Authoritative schema for CodeMentor AI (Think_First) — Phase 3
-- =============================================================================

-- 1. Supported Languages Registry (synced with Judge0 /languages)
CREATE TABLE IF NOT EXISTS public.supported_languages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9_-]{1,32}$'),
    display_name text NOT NULL,
    judge0_language_id integer NOT NULL UNIQUE CHECK (judge0_language_id > 0),
    monaco_language text NOT NULL,
    version_label text NOT NULL,
    is_enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_supported_languages_updated_at
    BEFORE UPDATE ON public.supported_languages
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 2. Problems & Immutable Problem Versions
CREATE TABLE IF NOT EXISTS public.problems (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{3,80}$'),
    current_published_version_id uuid,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    is_archived boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_problems_updated_at
    BEFORE UPDATE ON public.problems
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.problem_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id uuid NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
    version_number integer NOT NULL CHECK (version_number >= 1),
    title text NOT NULL CHECK (length(trim(title)) >= 3),
    statement_md text NOT NULL CHECK (length(trim(statement_md)) >= 10),
    difficulty text NOT NULL CHECK (difficulty IN ('beginner', 'basic', 'intermediate', 'advanced')),
    mode text NOT NULL CHECK (mode IN ('coding', 'debugging')),
    topics text[] NOT NULL DEFAULT '{}',
    skills text[] NOT NULL DEFAULT '{}',
    prerequisites text[] NOT NULL DEFAULT '{}',
    learning_objectives text[] NOT NULL DEFAULT '{}',
    examples jsonb NOT NULL DEFAULT '[]'::jsonb,
    time_limit_ms integer NOT NULL DEFAULT 2000 CHECK (time_limit_ms BETWEEN 500 AND 10000),
    memory_limit_kb integer NOT NULL DEFAULT 131072 CHECK (memory_limit_kb BETWEEN 16384 AND 524288),
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'validated', 'in_review', 'approved', 'published', 'archived')),
    validated_at timestamptz,
    published_at timestamptz,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_problem_versions_problem_num UNIQUE (problem_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_problem_versions_status ON public.problem_versions (status);
CREATE INDEX IF NOT EXISTS idx_problem_versions_mode_diff ON public.problem_versions (mode, difficulty);

CREATE TRIGGER trg_problem_versions_updated_at
    BEFORE UPDATE ON public.problem_versions
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.problems
    ADD CONSTRAINT fk_problems_current_published_version
    FOREIGN KEY (current_published_version_id)
    REFERENCES public.problem_versions(id)
    ON DELETE SET NULL;

-- 3. Language Variants (student-visible starter / buggy starter code)
CREATE TABLE IF NOT EXISTS public.problem_language_variants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_version_id uuid NOT NULL REFERENCES public.problem_versions(id) ON DELETE CASCADE,
    language_slug text NOT NULL REFERENCES public.supported_languages(slug) ON DELETE RESTRICT,
    starter_code text NOT NULL,
    buggy_starter_code text,
    debugging_prompt text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_problem_language_variants_ver_lang UNIQUE (problem_version_id, language_slug)
);

CREATE TRIGGER trg_problem_language_variants_updated_at
    BEFORE UPDATE ON public.problem_language_variants
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 4. Private Reference Solutions (strictly isolated table — Admin-only RLS)
CREATE TABLE IF NOT EXISTS public.problem_reference_solutions (
    variant_id uuid PRIMARY KEY REFERENCES public.problem_language_variants(id) ON DELETE CASCADE,
    reference_solution text NOT NULL CHECK (length(trim(reference_solution)) > 0),
    expected_bug_summary text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_problem_reference_solutions_updated_at
    BEFORE UPDATE ON public.problem_reference_solutions
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 5. Test Cases (public & hidden — hidden rows strictly blocked by RLS for students)
CREATE TABLE IF NOT EXISTS public.test_cases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_version_id uuid NOT NULL REFERENCES public.problem_versions(id) ON DELETE CASCADE,
    ordinal integer NOT NULL CHECK (ordinal >= 1),
    name text NOT NULL,
    input_data text NOT NULL DEFAULT '',
    expected_output text NOT NULL,
    is_hidden boolean NOT NULL DEFAULT false,
    weight integer NOT NULL DEFAULT 1 CHECK (weight >= 1),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_test_cases_version_ordinal UNIQUE (problem_version_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_test_cases_version_hidden ON public.test_cases (problem_version_id, is_hidden);

-- 6. Student Code Submissions & Execution Results
CREATE TABLE IF NOT EXISTS public.submissions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    problem_id uuid NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
    problem_version_id uuid NOT NULL REFERENCES public.problem_versions(id) ON DELETE RESTRICT,
    language_slug text NOT NULL REFERENCES public.supported_languages(slug) ON DELETE RESTRICT,
    submission_kind text NOT NULL CHECK (submission_kind IN ('run', 'submit')),
    source_code text NOT NULL,
    prediction_text text,
    explanation_text text,
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    verdict text NOT NULL DEFAULT 'pending'
        CHECK (verdict IN (
            'pending',
            'accepted',
            'wrong_answer',
            'compilation_error',
            'runtime_error',
            'time_limit_exceeded',
            'memory_limit_exceeded',
            'internal_error'
        )),
    passed_tests integer NOT NULL DEFAULT 0 CHECK (passed_tests >= 0),
    total_tests integer NOT NULL DEFAULT 0 CHECK (total_tests >= 0),
    runtime_ms integer,
    memory_kb integer,
    execution_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_submissions_student_created ON public.submissions (student_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_problem_ver ON public.submissions (problem_version_id);

CREATE TRIGGER trg_submissions_updated_at
    BEFORE UPDATE ON public.submissions
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.execution_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id uuid NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    test_case_id uuid NOT NULL REFERENCES public.test_cases(id) ON DELETE RESTRICT,
    is_hidden boolean NOT NULL DEFAULT false,
    judge0_token text,
    judge0_status_id integer,
    verdict text NOT NULL CHECK (verdict IN (
        'accepted',
        'wrong_answer',
        'compilation_error',
        'runtime_error',
        'time_limit_exceeded',
        'memory_limit_exceeded',
        'internal_error'
    )),
    stdout text,
    stderr text,
    compile_output text,
    runtime_ms integer,
    memory_kb integer,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_execution_results_submission ON public.execution_results (submission_id);

-- 7. Code Revisions (Autosave & Debugging Journey History)
CREATE TABLE IF NOT EXISTS public.code_revisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    problem_version_id uuid NOT NULL REFERENCES public.problem_versions(id) ON DELETE CASCADE,
    language_slug text NOT NULL REFERENCES public.supported_languages(slug) ON DELETE RESTRICT,
    source_code text NOT NULL,
    prediction_text text,
    explanation_text text,
    revision_type text NOT NULL DEFAULT 'autosave'
        CHECK (revision_type IN ('autosave', 'manual', 'run', 'submit')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_code_revisions_student_ver
    ON public.code_revisions (student_id, problem_version_id, created_at DESC);

-- 8. Content Governance & Publishing Reviews
CREATE TABLE IF NOT EXISTS public.content_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_version_id uuid NOT NULL REFERENCES public.problem_versions(id) ON DELETE CASCADE,
    reviewer_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    action text NOT NULL CHECK (action IN ('validated', 'submitted_for_review', 'approved', 'rejected', 'published')),
    notes text NOT NULL DEFAULT '',
    validation_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_reviews_version ON public.content_reviews (problem_version_id, created_at DESC);

-- 9. Row Level Security (RLS) Policies

ALTER TABLE public.supported_languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.supported_languages FORCE ROW LEVEL SECURITY;

ALTER TABLE public.problems ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.problems FORCE ROW LEVEL SECURITY;

ALTER TABLE public.problem_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.problem_versions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.problem_language_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.problem_language_variants FORCE ROW LEVEL SECURITY;

ALTER TABLE public.problem_reference_solutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.problem_reference_solutions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_cases FORCE ROW LEVEL SECURITY;

ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.execution_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.execution_results FORCE ROW LEVEL SECURITY;

ALTER TABLE public.code_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.code_revisions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.content_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_reviews FORCE ROW LEVEL SECURITY;

-- 9.1 supported_languages: readable by authenticated users (enabled only) or admin
CREATE POLICY supported_languages_select_enabled
    ON public.supported_languages FOR SELECT TO authenticated
    USING (is_enabled = true OR public.has_role(auth.uid(), 'admin'));

-- 9.2 problems & problem_versions: students see ONLY published, non-archived problems; admins see all
CREATE POLICY problems_select_published_or_admin
    ON public.problems FOR SELECT TO authenticated
    USING (
        (is_archived = false AND current_published_version_id IS NOT NULL)
        OR public.has_role(auth.uid(), 'admin')
    );

CREATE POLICY problem_versions_select_published_or_admin
    ON public.problem_versions FOR SELECT TO authenticated
    USING (status = 'published' OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY problem_variants_select_published_or_admin
    ON public.problem_language_variants FOR SELECT TO authenticated
    USING (
        public.has_role(auth.uid(), 'admin')
        OR EXISTS (
            SELECT 1 FROM public.problem_versions pv
            WHERE pv.id = problem_version_id AND pv.status = 'published'
        )
    );

-- 9.3 problem_reference_solutions: STRICTLY ADMIN-ONLY (never readable by students or teachers)
CREATE POLICY problem_reference_solutions_admin_only
    ON public.problem_reference_solutions FOR SELECT TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));

-- 9.4 test_cases: Students see ONLY non-hidden tests of published versions; Admins see all
CREATE POLICY test_cases_select_public_or_admin
    ON public.test_cases FOR SELECT TO authenticated
    USING (
        public.has_role(auth.uid(), 'admin')
        OR (
            is_hidden = false
            AND EXISTS (
                SELECT 1 FROM public.problem_versions pv
                WHERE pv.id = problem_version_id AND pv.status = 'published'
            )
        )
    );

-- 9.5 submissions & execution_results: Student strictly sees ONLY own rows; Admin sees all
CREATE POLICY submissions_select_own_or_admin
    ON public.submissions FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY execution_results_select_own_public_or_admin
    ON public.execution_results FOR SELECT TO authenticated
    USING (
        public.has_role(auth.uid(), 'admin')
        OR (
            is_hidden = false
            AND EXISTS (
                SELECT 1 FROM public.submissions s
                WHERE s.id = submission_id AND s.student_id = auth.uid()
            )
        )
    );

-- 9.6 code_revisions: Student strictly owns own revisions
CREATE POLICY code_revisions_select_own
    ON public.code_revisions FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY code_revisions_insert_own
    ON public.code_revisions FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = student_id);

-- 9.7 content_reviews: Admin-only
CREATE POLICY content_reviews_admin_only
    ON public.content_reviews FOR SELECT TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));
