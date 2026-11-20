-- =============================================================================
-- Migration 0003: ML Error Taxonomy/Diagnoses, pgvector RAG Knowledge Base,
--                 Stateful Socratic AI Mentor, Learning Events & Transfer Verification
-- Authoritative schema for CodeMentor AI (Think_First) — Phase 4
-- =============================================================================

-- 1. Error Taxonomy & Versioned ML Models
CREATE TABLE IF NOT EXISTS public.error_taxonomy (
    code text PRIMARY KEY CHECK (code ~ '^[a-z0-9_]{3,48}$'),
    display_name text NOT NULL,
    description text NOT NULL,
    is_observable_runtime boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.model_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_tag text NOT NULL UNIQUE,
    model_type text NOT NULL,
    dataset_version text NOT NULL,
    metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    artifact_path text NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.error_diagnoses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id uuid NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    model_version_id uuid REFERENCES public.model_versions(id) ON DELETE SET NULL,
    model_version_tag text NOT NULL,
    predicted_error_code text NOT NULL REFERENCES public.error_taxonomy(code) ON DELETE RESTRICT,
    confidence double precision NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    is_low_confidence boolean NOT NULL DEFAULT false,
    top_candidates jsonb NOT NULL DEFAULT '[]'::jsonb,
    feature_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_error_diagnoses_submission ON public.error_diagnoses (submission_id);
CREATE INDEX IF NOT EXISTS idx_error_diagnoses_student ON public.error_diagnoses (student_id, created_at DESC);

-- 2. Instructor-Reviewable RAG Knowledge Base + pgvector Chunks
CREATE TABLE IF NOT EXISTS public.knowledge_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{3,80}$'),
    title text NOT NULL,
    language_slug text NOT NULL DEFAULT 'python',
    topic text NOT NULL,
    error_codes text[] NOT NULL DEFAULT '{}',
    source_name text NOT NULL,
    source_version text NOT NULL DEFAULT '1.0',
    content_md text NOT NULL CHECK (length(trim(content_md)) >= 20),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'archived')),
    approved_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    approved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_docs_status_topic ON public.knowledge_documents (status, topic);

CREATE TRIGGER trg_knowledge_documents_updated_at
    BEFORE UPDATE ON public.knowledge_documents
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.knowledge_chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES public.knowledge_documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    heading text NOT NULL DEFAULT '',
    content text NOT NULL CHECK (length(trim(content)) >= 10),
    topic text NOT NULL,
    error_codes text[] NOT NULL DEFAULT '{}',
    token_count integer NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    embedding vector(256) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_knowledge_chunks_doc_idx UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_doc ON public.knowledge_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw
    ON public.knowledge_chunks USING hnsw (embedding vector_cosine_ops);

-- 3. Stateful Socratic AI Mentor Sessions, Turns & Hint Events
CREATE TABLE IF NOT EXISTS public.mentor_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    problem_id uuid NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
    problem_version_id uuid NOT NULL REFERENCES public.problem_versions(id) ON DELETE RESTRICT,
    latest_submission_id uuid REFERENCES public.submissions(id) ON DELETE SET NULL,
    current_state text NOT NULL DEFAULT 'awaiting_submission'
        CHECK (current_state IN (
            'awaiting_submission',
            'diagnosing',
            'asking_question',
            'awaiting_student_response',
            'giving_hint',
            'awaiting_revision',
            'verifying',
            'completed',
            'fallback'
        )),
    explanation_language text NOT NULL DEFAULT 'en' CHECK (explanation_language IN ('en', 'bn')),
    learner_level text NOT NULL DEFAULT 'beginner'
        CHECK (learner_level IN ('none', 'beginner', 'basic', 'intermediate', 'advanced')),
    hints_used integer NOT NULL DEFAULT 0 CHECK (hints_used BETWEEN 0 AND 3),
    provider_mode text NOT NULL DEFAULT 'deterministic_fallback'
        CHECK (provider_mode IN ('live_llm', 'deterministic_fallback')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mentor_sessions_student_problem
    ON public.mentor_sessions (student_id, problem_id, updated_at DESC);

CREATE TRIGGER trg_mentor_sessions_updated_at
    BEFORE UPDATE ON public.mentor_sessions
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.mentor_turns (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES public.mentor_sessions(id) ON DELETE CASCADE,
    turn_index integer NOT NULL CHECK (turn_index >= 1),
    role text NOT NULL CHECK (role IN ('student', 'mentor', 'system')),
    state_after text NOT NULL,
    message_text text NOT NULL,
    structured_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    cited_chunk_ids uuid[] NOT NULL DEFAULT '{}',
    diagnosis_id uuid REFERENCES public.error_diagnoses(id) ON DELETE SET NULL,
    provider_mode text NOT NULL DEFAULT 'deterministic_fallback',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_mentor_turns_session_idx UNIQUE (session_id, turn_index)
);

CREATE INDEX IF NOT EXISTS idx_mentor_turns_session ON public.mentor_turns (session_id, turn_index ASC);

CREATE TABLE IF NOT EXISTS public.hint_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES public.mentor_sessions(id) ON DELETE CASCADE,
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    submission_id uuid REFERENCES public.submissions(id) ON DELETE SET NULL,
    hint_level integer NOT NULL CHECK (hint_level BETWEEN 1 AND 3),
    hint_text text NOT NULL,
    cited_chunk_ids uuid[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hint_events_student ON public.hint_events (student_id, created_at DESC);

-- 4. Traceable Learning Events & Independent Understanding Verification
CREATE TABLE IF NOT EXISTS public.learning_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    problem_id uuid REFERENCES public.problems(id) ON DELETE SET NULL,
    problem_version_id uuid REFERENCES public.problem_versions(id) ON DELETE SET NULL,
    language_slug text,
    submission_id uuid REFERENCES public.submissions(id) ON DELETE SET NULL,
    diagnosis_id uuid REFERENCES public.error_diagnoses(id) ON DELETE SET NULL,
    event_type text NOT NULL CHECK (length(trim(event_type)) >= 3),
    hints_used integer NOT NULL DEFAULT 0 CHECK (hints_used >= 0),
    verdict text,
    verification_outcome text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_learning_events_student ON public.learning_events (student_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.verification_links (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_problem_id uuid NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
    transfer_problem_id uuid NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
    skill_focus text NOT NULL,
    max_hints_allowed integer NOT NULL DEFAULT 0 CHECK (max_hints_allowed >= 0),
    instructions_md text NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_verification_links_pair UNIQUE (source_problem_id, transfer_problem_id),
    CONSTRAINT chk_verification_distinct_problems CHECK (source_problem_id <> transfer_problem_id)
);

CREATE TABLE IF NOT EXISTS public.verification_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    verification_link_id uuid NOT NULL REFERENCES public.verification_links(id) ON DELETE RESTRICT,
    source_submission_id uuid REFERENCES public.submissions(id) ON DELETE SET NULL,
    transfer_submission_id uuid REFERENCES public.submissions(id) ON DELETE SET NULL,
    transfer_problem_id uuid NOT NULL REFERENCES public.problems(id) ON DELETE RESTRICT,
    hints_used integer NOT NULL DEFAULT 0 CHECK (hints_used >= 0),
    student_explanation text NOT NULL DEFAULT '',
    outcome text NOT NULL DEFAULT 'in_progress'
        CHECK (outcome IN ('in_progress', 'verified_independent', 'attempted_not_verified')),
    verdict text NOT NULL DEFAULT 'pending',
    passed_tests integer NOT NULL DEFAULT 0 CHECK (passed_tests >= 0),
    total_tests integer NOT NULL DEFAULT 0 CHECK (total_tests >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verification_attempts_student
    ON public.verification_attempts (student_id, created_at DESC);

CREATE TRIGGER trg_verification_attempts_updated_at
    BEFORE UPDATE ON public.verification_attempts
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 5. Strict Row Level Security (FORCE ROW LEVEL SECURITY)
ALTER TABLE public.error_taxonomy ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.error_taxonomy FORCE ROW LEVEL SECURITY;

ALTER TABLE public.model_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_versions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.error_diagnoses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.error_diagnoses FORCE ROW LEVEL SECURITY;

ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_documents FORCE ROW LEVEL SECURITY;

ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_chunks FORCE ROW LEVEL SECURITY;

ALTER TABLE public.mentor_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mentor_sessions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.mentor_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mentor_turns FORCE ROW LEVEL SECURITY;

ALTER TABLE public.hint_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hint_events FORCE ROW LEVEL SECURITY;

ALTER TABLE public.learning_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_events FORCE ROW LEVEL SECURITY;

ALTER TABLE public.verification_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_links FORCE ROW LEVEL SECURITY;

ALTER TABLE public.verification_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_attempts FORCE ROW LEVEL SECURITY;

-- Reference/catalog read policies
CREATE POLICY error_taxonomy_select_auth ON public.error_taxonomy
    FOR SELECT TO authenticated USING (true);

CREATE POLICY model_versions_select_admin ON public.model_versions
    FOR SELECT TO authenticated USING (public.has_role(auth.uid(), 'admin'));

CREATE POLICY knowledge_docs_select_approved_or_admin ON public.knowledge_documents
    FOR SELECT TO authenticated
    USING (status = 'approved' OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY knowledge_chunks_select_approved_or_admin ON public.knowledge_chunks
    FOR SELECT TO authenticated
    USING (
        public.has_role(auth.uid(), 'admin')
        OR EXISTS (
            SELECT 1 FROM public.knowledge_documents kd
            WHERE kd.id = document_id AND kd.status = 'approved'
        )
    );

CREATE POLICY verification_links_select_active ON public.verification_links
    FOR SELECT TO authenticated
    USING (is_active = true OR public.has_role(auth.uid(), 'admin'));

-- Strictly student-owned or admin-readable tables
CREATE POLICY error_diagnoses_select_own_or_admin ON public.error_diagnoses
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY mentor_sessions_select_own_or_admin ON public.mentor_sessions
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY mentor_turns_select_own_or_admin ON public.mentor_turns
    FOR SELECT TO authenticated
    USING (
        public.has_role(auth.uid(), 'admin')
        OR EXISTS (
            SELECT 1 FROM public.mentor_sessions ms
            WHERE ms.id = session_id AND ms.student_id = auth.uid()
        )
    );

CREATE POLICY hint_events_select_own_or_admin ON public.hint_events
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY learning_events_select_own_or_admin ON public.learning_events
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY verification_attempts_select_own_or_admin ON public.verification_attempts
    FOR SELECT TO authenticated
    USING (auth.uid() = student_id OR public.has_role(auth.uid(), 'admin'));
