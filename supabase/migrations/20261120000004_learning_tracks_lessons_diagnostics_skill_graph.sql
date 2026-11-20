-- =============================================================================
-- Migration 0004: Learning Tracks, Beginner Lessons, Adaptive Diagnostics,
--                 Prerequisite Skill Graph & Explainable Recommendations
-- Authoritative schema for CodeMentor AI (Think_First) — Phase 5
-- =============================================================================

-- 1. Four Evidence-Based Learning Tracks & Student Track Enrollments
CREATE TABLE IF NOT EXISTS public.learning_tracks (
    slug text PRIMARY KEY CHECK (slug IN (
        'absolute_beginner',
        'basic_university',
        'intermediate',
        'advanced'
    )),
    title_en text NOT NULL,
    title_bn text NOT NULL,
    summary_en text NOT NULL,
    summary_bn text NOT NULL,
    target_audience_en text NOT NULL,
    target_audience_bn text NOT NULL,
    display_order integer NOT NULL UNIQUE CHECK (display_order >= 1),
    recommended_focus_skills text[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.student_track_enrollments (
    student_id uuid PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    selected_track_slug text NOT NULL REFERENCES public.learning_tracks(slug) ON DELETE RESTRICT,
    recommended_track_slug text REFERENCES public.learning_tracks(slug) ON DELETE SET NULL,
    recommendation_source text NOT NULL DEFAULT 'onboarding_initial'
        CHECK (recommendation_source IN (
            'onboarding_initial',
            'diagnostic_evidence',
            'manual_selection'
        )),
    recommendation_reason text NOT NULL DEFAULT '',
    diagnostic_session_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_student_track_enrollments_updated_at
    BEFORE UPDATE ON public.student_track_enrollments
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 2. Prerequisite-Aware Skill Graph (DAG Nodes, Edges, Evidence-Based States & Transitions)
CREATE TABLE IF NOT EXISTS public.skill_nodes (
    slug text PRIMARY KEY CHECK (slug ~ '^[a-z0-9_]{3,64}$'),
    title_en text NOT NULL,
    title_bn text NOT NULL,
    description_en text NOT NULL,
    description_bn text NOT NULL,
    domain_slug text NOT NULL,
    tier integer NOT NULL CHECK (tier BETWEEN 1 AND 5),
    display_order integer NOT NULL CHECK (display_order >= 1),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.skill_prerequisites (
    skill_slug text NOT NULL REFERENCES public.skill_nodes(slug) ON DELETE CASCADE,
    prerequisite_slug text NOT NULL REFERENCES public.skill_nodes(slug) ON DELETE CASCADE,
    PRIMARY KEY (skill_slug, prerequisite_slug),
    CONSTRAINT chk_skill_prereq_not_self CHECK (skill_slug <> prerequisite_slug)
);

CREATE TABLE IF NOT EXISTS public.student_skill_states (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    skill_slug text NOT NULL REFERENCES public.skill_nodes(slug) ON DELETE CASCADE,
    state text NOT NULL DEFAULT 'unobserved'
        CHECK (state IN (
            'unobserved',
            'introduced',
            'guided',
            'independent',
            'transferred',
            'retained'
        )),
    evidence_count integer NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    uncertainty_note text NOT NULL DEFAULT 'No direct evidence recorded yet.',
    last_evidence_type text,
    last_evidence_at timestamptz,
    first_verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_student_skill_state UNIQUE (student_id, skill_slug)
);

CREATE INDEX IF NOT EXISTS idx_student_skill_states_student
    ON public.student_skill_states (student_id, state);

CREATE TRIGGER trg_student_skill_states_updated_at
    BEFORE UPDATE ON public.student_skill_states
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.skill_state_transitions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    skill_slug text NOT NULL REFERENCES public.skill_nodes(slug) ON DELETE CASCADE,
    from_state text NOT NULL,
    to_state text NOT NULL,
    evidence_source text NOT NULL,
    evidence_ref_id text,
    reason text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_skill_transitions_student
    ON public.skill_state_transitions (student_id, created_at DESC);

-- 3. Beginner Learning Lessons (Versioned, Admin-Published, Bilingual, Judge0 Practice)
CREATE TABLE IF NOT EXISTS public.lessons (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{3,80}$'),
    skill_slug text NOT NULL REFERENCES public.skill_nodes(slug) ON DELETE RESTRICT,
    display_order integer NOT NULL CHECK (display_order >= 1),
    current_published_version_id uuid,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_lessons_updated_at
    BEFORE UPDATE ON public.lessons
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.lesson_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id uuid NOT NULL REFERENCES public.lessons(id) ON DELETE CASCADE,
    version_number integer NOT NULL CHECK (version_number >= 1),
    title_en text NOT NULL,
    title_bn text NOT NULL,
    summary_en text NOT NULL,
    summary_bn text NOT NULL,
    content_en_md text NOT NULL,
    content_bn_md text NOT NULL,
    learning_objectives text[] NOT NULL DEFAULT '{}',
    prerequisite_lesson_slugs text[] NOT NULL DEFAULT '{}',
    track_slugs text[] NOT NULL DEFAULT '{}',
    interactive_examples jsonb NOT NULL DEFAULT '[]'::jsonb,
    guided_exercise jsonb NOT NULL DEFAULT '{}'::jsonb,
    estimated_minutes integer NOT NULL DEFAULT 15 CHECK (estimated_minutes BETWEEN 5 AND 120),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    published_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_lesson_versions_num UNIQUE (lesson_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_lesson_versions_status ON public.lesson_versions (lesson_id, status);

CREATE TRIGGER trg_lesson_versions_updated_at
    BEFORE UPDATE ON public.lesson_versions
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.lessons
    ADD CONSTRAINT fk_lessons_current_published_version
    FOREIGN KEY (current_published_version_id)
    REFERENCES public.lesson_versions(id)
    ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS public.lesson_progress (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    lesson_id uuid NOT NULL REFERENCES public.lessons(id) ON DELETE CASCADE,
    lesson_version_id uuid NOT NULL REFERENCES public.lesson_versions(id) ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('not_started', 'in_progress', 'completed')),
    reading_completed boolean NOT NULL DEFAULT false,
    exercise_passed boolean NOT NULL DEFAULT false,
    exercise_attempts integer NOT NULL DEFAULT 0 CHECK (exercise_attempts >= 0),
    last_code text,
    last_verdict text,
    last_stdout text,
    last_stderr text,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_lesson_progress_student_lesson UNIQUE (student_id, lesson_id)
);

CREATE INDEX IF NOT EXISTS idx_lesson_progress_student
    ON public.lesson_progress (student_id, updated_at DESC);

CREATE TRIGGER trg_lesson_progress_updated_at
    BEFORE UPDATE ON public.lesson_progress
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 4. Adaptive Diagnostic Assessment (8 Domains + Isolated Private Answer Keys)
CREATE TABLE IF NOT EXISTS public.diagnostic_questions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{3,80}$'),
    domain_slug text NOT NULL CHECK (domain_slug IN (
        'variables',
        'syntax_runtime_debugging',
        'conditions',
        'loop_boundaries',
        'arrays_lists',
        'indexing',
        'functions',
        'mixed_logic'
    )),
    skill_slug text NOT NULL REFERENCES public.skill_nodes(slug) ON DELETE RESTRICT,
    difficulty text NOT NULL CHECK (difficulty IN ('foundation', 'core', 'stretch')),
    question_type text NOT NULL CHECK (question_type IN ('mcq', 'code_execution')),
    prompt_en text NOT NULL,
    prompt_bn text NOT NULL,
    code_snippet text,
    options jsonb NOT NULL DEFAULT '[]'::jsonb,
    starter_code text,
    language_slug text NOT NULL DEFAULT 'python',
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'approved', 'published', 'archived')),
    reviewed_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diagnostic_questions_domain_diff
    ON public.diagnostic_questions (status, domain_slug, difficulty);

CREATE TRIGGER trg_diagnostic_questions_updated_at
    BEFORE UPDATE ON public.diagnostic_questions
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- Private answer key & hidden execution tests: ADMIN-ONLY via strict RLS!
CREATE TABLE IF NOT EXISTS public.diagnostic_question_answers (
    question_id uuid PRIMARY KEY REFERENCES public.diagnostic_questions(id) ON DELETE CASCADE,
    correct_option_id text,
    explanation_en text NOT NULL,
    explanation_bn text NOT NULL,
    evaluation_tests jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_diagnostic_question_answers_updated_at
    BEFORE UPDATE ON public.diagnostic_question_answers
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.diagnostic_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    explanation_language text NOT NULL DEFAULT 'en' CHECK (explanation_language IN ('en', 'bn')),
    question_queue jsonb NOT NULL DEFAULT '[]'::jsonb,
    current_index integer NOT NULL DEFAULT 0 CHECK (current_index >= 0),
    adaptive_followups_added integer NOT NULL DEFAULT 0 CHECK (adaptive_followups_added >= 0),
    recommended_track_slug text REFERENCES public.learning_tracks(slug) ON DELETE SET NULL,
    domain_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    recommendation_rationale text,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diagnostic_sessions_student
    ON public.diagnostic_sessions (student_id, created_at DESC);

CREATE TRIGGER trg_diagnostic_sessions_updated_at
    BEFORE UPDATE ON public.diagnostic_sessions
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.diagnostic_responses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES public.diagnostic_sessions(id) ON DELETE CASCADE,
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    question_id uuid NOT NULL REFERENCES public.diagnostic_questions(id) ON DELETE RESTRICT,
    domain_slug text NOT NULL,
    difficulty text NOT NULL,
    question_type text NOT NULL,
    selected_option_id text,
    submitted_code text,
    is_correct boolean NOT NULL,
    execution_verdict text,
    passed_tests integer NOT NULL DEFAULT 0 CHECK (passed_tests >= 0),
    total_tests integer NOT NULL DEFAULT 0 CHECK (total_tests >= 0),
    execution_stderr text,
    response_time_ms integer CHECK (response_time_ms IS NULL OR response_time_ms >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_diagnostic_response_session_question UNIQUE (session_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_diagnostic_responses_session
    ON public.diagnostic_responses (session_id, created_at ASC);

-- 5. Persisted Explainable Recommendations
CREATE TABLE IF NOT EXISTS public.student_recommendations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    recommendation_type text NOT NULL CHECK (recommendation_type IN (
        'diagnostic_assessment',
        'lesson',
        'problem',
        'transfer_challenge'
    )),
    target_id text NOT NULL,
    target_slug text NOT NULL,
    title text NOT NULL,
    priority integer NOT NULL CHECK (priority >= 1),
    reason_en text NOT NULL,
    reason_bn text NOT NULL,
    evidence_factors jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_student_recommendations_student
    ON public.student_recommendations (student_id, priority ASC);

-- 6. Strict Row Level Security (FORCE ROW LEVEL SECURITY on EVERY Phase 5 table)
ALTER TABLE public.learning_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_tracks FORCE ROW LEVEL SECURITY;

ALTER TABLE public.student_track_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_track_enrollments FORCE ROW LEVEL SECURITY;

ALTER TABLE public.skill_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.skill_nodes FORCE ROW LEVEL SECURITY;

ALTER TABLE public.skill_prerequisites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.skill_prerequisites FORCE ROW LEVEL SECURITY;

ALTER TABLE public.student_skill_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_skill_states FORCE ROW LEVEL SECURITY;

ALTER TABLE public.skill_state_transitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.skill_state_transitions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lessons FORCE ROW LEVEL SECURITY;

ALTER TABLE public.lesson_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lesson_versions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.lesson_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lesson_progress FORCE ROW LEVEL SECURITY;

ALTER TABLE public.diagnostic_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.diagnostic_questions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.diagnostic_question_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.diagnostic_question_answers FORCE ROW LEVEL SECURITY;

ALTER TABLE public.diagnostic_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.diagnostic_sessions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.diagnostic_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.diagnostic_responses FORCE ROW LEVEL SECURITY;

ALTER TABLE public.student_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_recommendations FORCE ROW LEVEL SECURITY;

-- Catalog / Published read policies
CREATE POLICY learning_tracks_select_auth ON public.learning_tracks
    FOR SELECT TO authenticated USING (true);

CREATE POLICY skill_nodes_select_auth ON public.skill_nodes
    FOR SELECT TO authenticated USING (true);

CREATE POLICY skill_prerequisites_select_auth ON public.skill_prerequisites
    FOR SELECT TO authenticated USING (true);

CREATE POLICY lessons_select_published_or_admin ON public.lessons
    FOR SELECT TO authenticated
    USING (current_published_version_id IS NOT NULL OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY lesson_versions_select_published_or_admin ON public.lesson_versions
    FOR SELECT TO authenticated
    USING (status = 'published' OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY diagnostic_questions_select_published_or_admin ON public.diagnostic_questions
    FOR SELECT TO authenticated
    USING (status = 'published' OR public.has_role(auth.uid(), 'admin'));

-- CRITICAL SECURITY POLICY: Private answer keys & hidden diagnostic tests are ADMIN-ONLY!
CREATE POLICY diagnostic_question_answers_admin_only ON public.diagnostic_question_answers
    FOR SELECT TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));

-- Strictly student-owned or admin-readable tables
CREATE POLICY student_track_enrollments_select_own_or_admin ON public.student_track_enrollments
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY student_skill_states_select_own_or_admin ON public.student_skill_states
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY skill_state_transitions_select_own_or_admin ON public.skill_state_transitions
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY lesson_progress_select_own_or_admin ON public.lesson_progress
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY diagnostic_sessions_select_own_or_admin ON public.diagnostic_sessions
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY diagnostic_responses_select_own_or_admin ON public.diagnostic_responses
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY student_recommendations_select_own_or_admin ON public.student_recommendations
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));
