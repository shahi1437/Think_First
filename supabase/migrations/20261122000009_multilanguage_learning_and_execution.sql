-- Phase 3 (Multi-Language Learning System + Judge0/Piston Execution Fallback)
-- Strictly additive, non-destructive migration preserving all existing Python lessons,
-- student progress, submissions, diagnostics, Skill Graph states, and RLS policies.

-- 1. Register and enable all 5 official programming languages (live-verified Judge0 CE 1.13.1 IDs)
INSERT INTO public.supported_languages (
    slug,
    display_name,
    judge0_language_id,
    monaco_language,
    version_label,
    is_enabled
)
VALUES
    ('python', 'Python 3', 71, 'python', 'Python (3.8.1)', TRUE),
    ('javascript', 'JavaScript (Node.js)', 63, 'javascript', 'JavaScript (Node.js 12.14.0)', TRUE),
    ('c', 'C (GCC)', 50, 'c', 'C (GCC 9.2.0)', TRUE),
    ('cpp', 'C++ (GCC)', 54, 'cpp', 'C++ (GCC 9.2.0)', TRUE),
    ('java', 'Java (OpenJDK)', 62, 'java', 'Java (OpenJDK 13.0.1)', TRUE)
ON CONFLICT (slug) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    judge0_language_id = EXCLUDED.judge0_language_id,
    monaco_language = EXCLUDED.monaco_language,
    version_label = EXCLUDED.version_label,
    is_enabled = TRUE;

-- 2. User preferences: allow 'c' in preferred_language and add active_language_slug
ALTER TABLE public.user_preferences
    DROP CONSTRAINT IF EXISTS user_preferences_preferred_language_check;

ALTER TABLE public.user_preferences
    ADD CONSTRAINT user_preferences_preferred_language_check
    CHECK (preferred_language IN ('python', 'javascript', 'c', 'cpp', 'java'));

ALTER TABLE public.user_preferences
    ADD COLUMN IF NOT EXISTS active_language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

UPDATE public.user_preferences
SET active_language_slug = preferred_language
WHERE active_language_slug = 'python'
  AND preferred_language IN ('python', 'javascript', 'c', 'cpp', 'java')
  AND preferred_language <> 'python';

-- 3. Lessons: add language_slug defaulting to 'python' (preserves all 24 existing Python lessons)
ALTER TABLE public.lessons
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_lessons_language_order
    ON public.lessons (language_slug, display_order);

-- 4. Student Track Enrollments: scope per (student_id, language_slug)
ALTER TABLE public.student_track_enrollments
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

ALTER TABLE public.student_track_enrollments
    DROP CONSTRAINT IF EXISTS student_track_enrollments_pkey;

ALTER TABLE public.student_track_enrollments
    ADD CONSTRAINT student_track_enrollments_pkey PRIMARY KEY (student_id, language_slug);

CREATE INDEX IF NOT EXISTS idx_student_track_enrollments_student_lang
    ON public.student_track_enrollments (student_id, language_slug);

-- 5. Diagnostic Sessions & Questions index: scope per language_slug
ALTER TABLE public.diagnostic_sessions
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_diagnostic_sessions_student_lang
    ON public.diagnostic_sessions (student_id, language_slug, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_diagnostic_questions_lang_status_domain
    ON public.diagnostic_questions (language_slug, status, domain_slug);

-- 6. Skill Graph States & Transitions: independent skill progression per (student_id, language_slug, skill_slug)
ALTER TABLE public.student_skill_states
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

ALTER TABLE public.student_skill_states
    DROP CONSTRAINT IF EXISTS uq_student_skill_state;

ALTER TABLE public.student_skill_states
    ADD CONSTRAINT uq_student_skill_state UNIQUE (student_id, language_slug, skill_slug);

CREATE INDEX IF NOT EXISTS idx_student_skill_states_student_lang
    ON public.student_skill_states (student_id, language_slug, state);

ALTER TABLE public.skill_state_transitions
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_skill_state_transitions_student_lang
    ON public.skill_state_transitions (student_id, language_slug, created_at DESC);

-- 7. Student Recommendations: scope per language_slug
ALTER TABLE public.student_recommendations
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_student_recommendations_student_lang
    ON public.student_recommendations (student_id, language_slug, priority ASC);

-- 8. Growth Layer (Learning DNA, Daily Plans, Retention Schedules): scope per language_slug
ALTER TABLE public.learning_dna_snapshots
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_learning_dna_snapshots_student_lang
    ON public.learning_dna_snapshots (student_id, language_slug, computed_at DESC);

ALTER TABLE public.daily_learning_plans
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

ALTER TABLE public.daily_learning_plans
    DROP CONSTRAINT IF EXISTS daily_learning_plans_student_id_plan_date_version_number_key;

ALTER TABLE public.daily_learning_plans
    DROP CONSTRAINT IF EXISTS daily_learning_plans_student_lang_date_version_key;

ALTER TABLE public.daily_learning_plans
    ADD CONSTRAINT daily_learning_plans_student_lang_date_version_key
    UNIQUE (student_id, language_slug, plan_date, version_number);

DROP INDEX IF EXISTS public.idx_daily_learning_plans_active_unique;

CREATE UNIQUE INDEX idx_daily_learning_plans_active_unique
    ON public.daily_learning_plans (student_id, language_slug, plan_date)
    WHERE is_active = TRUE;

DROP INDEX IF EXISTS public.idx_daily_learning_plans_student_date;

CREATE INDEX idx_daily_learning_plans_student_date
    ON public.daily_learning_plans (student_id, language_slug, plan_date DESC, version_number DESC);

ALTER TABLE public.retention_schedules
    ADD COLUMN IF NOT EXISTS language_slug text NOT NULL DEFAULT 'python'
        REFERENCES public.supported_languages(slug) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_retention_schedules_student_lang
    ON public.retention_schedules (student_id, language_slug, due_at ASC);

-- 9. Submissions & Execution Results: track active execution provider ('judge0' | 'piston')
ALTER TABLE public.submissions
    ADD COLUMN IF NOT EXISTS execution_provider text NOT NULL DEFAULT 'judge0';

ALTER TABLE public.submissions
    DROP CONSTRAINT IF EXISTS submissions_execution_provider_check;

ALTER TABLE public.submissions
    ADD CONSTRAINT submissions_execution_provider_check
    CHECK (execution_provider IN ('judge0', 'piston'));

CREATE INDEX IF NOT EXISTS idx_submissions_student_lang
    ON public.submissions (student_id, language_slug, created_at DESC);

ALTER TABLE public.execution_results
    ADD COLUMN IF NOT EXISTS execution_provider text NOT NULL DEFAULT 'judge0';

ALTER TABLE public.execution_results
    DROP CONSTRAINT IF EXISTS execution_results_execution_provider_check;

ALTER TABLE public.execution_results
    ADD CONSTRAINT execution_results_execution_provider_check
    CHECK (execution_provider IN ('judge0', 'piston'));

-- 10. RAG Knowledge Documents: index language_slug + status for strict language-scoped retrieval
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_lang_status
    ON public.knowledge_documents (language_slug, status);
