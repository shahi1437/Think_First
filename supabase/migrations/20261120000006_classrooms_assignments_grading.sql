-- =============================================================================
-- Think_First (CodeMentor AI) — Phase 7 Schema Migration
-- Classrooms/Courses, Memberships, Secure Invitations, Teacher Assignments,
-- Reproducible Problem Version Links, Judge0 Assignment Attempts, Auditable
-- Teacher Grading, and Written Feedback
-- =============================================================================

-- 1. Courses / Classes
CREATE TABLE IF NOT EXISTS public.courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    code VARCHAR(32) NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    term VARCHAR(64) NOT NULL DEFAULT '',
    enrollment_policy VARCHAR(32) NOT NULL DEFAULT 'open_with_code' CHECK (
        enrollment_policy IN ('open_with_code', 'approval_required')
    ),
    allow_student_leave BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(24) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_courses_teacher_status
    ON public.courses (teacher_id, status, created_at DESC);

-- 2. Class Invitations (Teacher/Admin-only table; never readable directly by students)
CREATE TABLE IF NOT EXISTS public.class_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    code_hash TEXT NOT NULL UNIQUE,
    code_preview VARCHAR(32) NOT NULL,
    max_uses INTEGER CHECK (max_uses IS NULL OR max_uses >= 1),
    uses_count INTEGER NOT NULL DEFAULT 0 CHECK (uses_count >= 0),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_class_invitations_course_active
    ON public.class_invitations (course_id, is_active, created_at DESC);

-- 3. Course Memberships (Enrollments)
CREATE TABLE IF NOT EXISTS public.course_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    status VARCHAR(24) NOT NULL DEFAULT 'active' CHECK (
        status IN ('pending', 'active', 'removed', 'left')
    ),
    joined_via_invitation_id UUID REFERENCES public.class_invitations(id) ON DELETE SET NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    removed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (course_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_course_memberships_student_status
    ON public.course_memberships (student_id, status);

CREATE INDEX IF NOT EXISTS idx_course_memberships_course_status
    ON public.course_memberships (course_id, status);

-- 4. Assignments
CREATE TABLE IF NOT EXISTS public.assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    instructions_md TEXT NOT NULL DEFAULT '',
    opens_at TIMESTAMPTZ,
    due_at TIMESTAMPTZ,
    max_marks NUMERIC(6, 2) NOT NULL DEFAULT 100.00 CHECK (max_marks > 0),
    grading_policy VARCHAR(32) NOT NULL DEFAULT 'judge0_assisted_manual' CHECK (
        grading_policy IN ('manual_review', 'judge0_assisted_manual')
    ),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1 AND max_attempts <= 50),
    allow_ai_hints BOOLEAN NOT NULL DEFAULT TRUE,
    hint_limit INTEGER NOT NULL DEFAULT 2 CHECK (hint_limit BETWEEN 0 AND 3),
    allow_late_submissions BOOLEAN NOT NULL DEFAULT FALSE,
    allow_resubmission_on_revision BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(24) NOT NULL DEFAULT 'draft' CHECK (
        status IN ('draft', 'published', 'archived')
    ),
    published_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assignments_course_status
    ON public.assignments (course_id, status, due_at ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_assignments_teacher_status
    ON public.assignments (teacher_id, status, created_at DESC);

-- 5. Assignment Problem Links (pins exact approved problem_version_id)
CREATE TABLE IF NOT EXISTS public.assignment_problem_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    problem_id UUID NOT NULL REFERENCES public.problems(id) ON DELETE RESTRICT,
    problem_version_id UUID NOT NULL REFERENCES public.problem_versions(id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
    points NUMERIC(6, 2) NOT NULL DEFAULT 100.00 CHECK (points >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (assignment_id, problem_id),
    UNIQUE (assignment_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_assignment_problem_links_assignment
    ON public.assignment_problem_links (assignment_id, ordinal ASC);

-- 6. Assignment Submissions (per student per assignment workflow envelope)
CREATE TABLE IF NOT EXISTS public.assignment_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'in_progress' CHECK (
        status IN (
            'not_started',
            'in_progress',
            'submitted',
            'revision_requested',
            'resubmitted',
            'graded'
        )
    ),
    attempts_used INTEGER NOT NULL DEFAULT 0 CHECK (attempts_used >= 0),
    latest_attempt_id UUID,
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at TIMESTAMPTZ,
    resubmitted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (assignment_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_assignment_submissions_assignment_status
    ON public.assignment_submissions (assignment_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_assignment_submissions_student
    ON public.assignment_submissions (student_id, updated_at DESC);

-- 7. Assignment Attempts (immutable student submission attempts backed by real Judge0)
CREATE TABLE IF NOT EXISTS public.assignment_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_submission_id UUID NOT NULL REFERENCES public.assignment_submissions(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    problem_id UUID NOT NULL REFERENCES public.problems(id) ON DELETE RESTRICT,
    problem_version_id UUID NOT NULL REFERENCES public.problem_versions(id) ON DELETE RESTRICT,
    execution_submission_id UUID REFERENCES public.submissions(id) ON DELETE SET NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    language_slug VARCHAR(32) NOT NULL DEFAULT 'python',
    source_code TEXT NOT NULL,
    student_notes TEXT NOT NULL DEFAULT '',
    verdict VARCHAR(32) NOT NULL,
    passed_tests INTEGER NOT NULL DEFAULT 0,
    total_tests INTEGER NOT NULL DEFAULT 0,
    hints_used INTEGER NOT NULL DEFAULT 0,
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (assignment_submission_id, problem_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS idx_assignment_attempts_submission
    ON public.assignment_attempts (assignment_submission_id, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_assignment_attempts_course_student
    ON public.assignment_attempts (course_id, student_id, submitted_at DESC);

-- 8. Assignment Grades (draft vs published; students can NEVER read draft or other students' grades)
CREATE TABLE IF NOT EXISTS public.assignment_grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_submission_id UUID NOT NULL UNIQUE REFERENCES public.assignment_submissions(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    graded_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    marks_awarded NUMERIC(6, 2) NOT NULL CHECK (marks_awarded >= 0),
    max_marks NUMERIC(6, 2) NOT NULL CHECK (max_marks > 0),
    status VARCHAR(24) NOT NULL DEFAULT 'draft' CHECK (
        status IN ('draft', 'published', 'revision_requested')
    ),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (marks_awarded <= max_marks)
);

CREATE INDEX IF NOT EXISTS idx_assignment_grades_assignment
    ON public.assignment_grades (assignment_id, status);

CREATE INDEX IF NOT EXISTS idx_assignment_grades_student
    ON public.assignment_grades (student_id, status);

-- 9. Teacher Feedback Entries
CREATE TABLE IF NOT EXISTS public.teacher_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_submission_id UUID NOT NULL REFERENCES public.assignment_submissions(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    feedback_type VARCHAR(32) NOT NULL DEFAULT 'comment' CHECK (
        feedback_type IN ('comment', 'revision_request', 'grade_release')
    ),
    body_md TEXT NOT NULL,
    is_visible_to_student BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teacher_feedback_submission
    ON public.teacher_feedback (assignment_submission_id, created_at DESC);

-- 10. Grading Audit Events (Append-only immutable audit log; teacher/admin visible only)
CREATE TABLE IF NOT EXISTS public.grading_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_submission_id UUID NOT NULL REFERENCES public.assignment_submissions(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    actor_user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    action VARCHAR(32) NOT NULL CHECK (
        action IN (
            'grade_draft_saved',
            'grade_published',
            'grade_updated',
            'revision_requested',
            'feedback_posted'
        )
    ),
    previous_marks NUMERIC(6, 2),
    new_marks NUMERIC(6, 2),
    previous_status VARCHAR(32),
    new_status VARCHAR(32),
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_grading_audit_events_submission
    ON public.grading_audit_events (assignment_submission_id, created_at DESC);

-- =============================================================================
-- Authorization helper functions for non-recursive RLS
-- =============================================================================
CREATE OR REPLACE FUNCTION public.is_course_teacher(p_course_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.courses c
        WHERE c.id = p_course_id
          AND c.teacher_id = p_user_id
    );
$$;

CREATE OR REPLACE FUNCTION public.is_enrolled_student(p_course_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.course_memberships m
        WHERE m.course_id = p_course_id
          AND m.student_id = p_user_id
          AND m.status = 'active'
    );
$$;

-- =============================================================================
-- Updated-at triggers
-- =============================================================================
DROP TRIGGER IF EXISTS trg_courses_updated_at ON public.courses;
CREATE TRIGGER trg_courses_updated_at
    BEFORE UPDATE ON public.courses
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_course_memberships_updated_at ON public.course_memberships;
CREATE TRIGGER trg_course_memberships_updated_at
    BEFORE UPDATE ON public.course_memberships
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_assignments_updated_at ON public.assignments;
CREATE TRIGGER trg_assignments_updated_at
    BEFORE UPDATE ON public.assignments
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_assignment_submissions_updated_at ON public.assignment_submissions;
CREATE TRIGGER trg_assignment_submissions_updated_at
    BEFORE UPDATE ON public.assignment_submissions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_assignment_grades_updated_at ON public.assignment_grades;
CREATE TRIGGER trg_assignment_grades_updated_at
    BEFORE UPDATE ON public.assignment_grades
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- Strict Row-Level Security (FORCE ROW LEVEL SECURITY on all 10 Phase 7 tables)
-- =============================================================================
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courses FORCE ROW LEVEL SECURITY;

ALTER TABLE public.class_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.class_invitations FORCE ROW LEVEL SECURITY;

ALTER TABLE public.course_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.course_memberships FORCE ROW LEVEL SECURITY;

ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignments FORCE ROW LEVEL SECURITY;

ALTER TABLE public.assignment_problem_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignment_problem_links FORCE ROW LEVEL SECURITY;

ALTER TABLE public.assignment_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignment_submissions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.assignment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignment_attempts FORCE ROW LEVEL SECURITY;

ALTER TABLE public.assignment_grades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignment_grades FORCE ROW LEVEL SECURITY;

ALTER TABLE public.teacher_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teacher_feedback FORCE ROW LEVEL SECURITY;

ALTER TABLE public.grading_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.grading_audit_events FORCE ROW LEVEL SECURITY;

-- 1. courses policies
DROP POLICY IF EXISTS courses_select ON public.courses;
CREATE POLICY courses_select ON public.courses
    FOR SELECT USING (
        teacher_id = auth.uid()
        OR public.is_enrolled_student(id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

DROP POLICY IF EXISTS courses_teacher_write ON public.courses;
CREATE POLICY courses_teacher_write ON public.courses
    FOR ALL
    USING (
        (teacher_id = auth.uid() AND public.has_role(auth.uid(), 'teacher'))
        OR public.has_role(auth.uid(), 'admin')
    )
    WITH CHECK (
        (teacher_id = auth.uid() AND public.has_role(auth.uid(), 'teacher'))
        OR public.has_role(auth.uid(), 'admin')
    );

-- 2. class_invitations policies (strictly teacher-owner or admin — NEVER students)
DROP POLICY IF EXISTS class_invitations_teacher_all ON public.class_invitations;
CREATE POLICY class_invitations_teacher_all ON public.class_invitations
    FOR ALL
    USING (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    )
    WITH CHECK (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

-- 3. course_memberships policies
DROP POLICY IF EXISTS course_memberships_select ON public.course_memberships;
CREATE POLICY course_memberships_select ON public.course_memberships
    FOR SELECT USING (
        student_id = auth.uid()
        OR public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

DROP POLICY IF EXISTS course_memberships_teacher_write ON public.course_memberships;
CREATE POLICY course_memberships_teacher_write ON public.course_memberships
    FOR ALL
    USING (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    )
    WITH CHECK (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

-- 4. assignments policies
DROP POLICY IF EXISTS assignments_select ON public.assignments;
CREATE POLICY assignments_select ON public.assignments
    FOR SELECT USING (
        public.is_course_teacher(course_id, auth.uid())
        OR (status = 'published' AND public.is_enrolled_student(course_id, auth.uid()))
        OR public.has_role(auth.uid(), 'admin')
    );

DROP POLICY IF EXISTS assignments_teacher_write ON public.assignments;
CREATE POLICY assignments_teacher_write ON public.assignments
    FOR ALL
    USING (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    )
    WITH CHECK (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

-- 5. assignment_problem_links policies
DROP POLICY IF EXISTS assignment_problem_links_select ON public.assignment_problem_links;
CREATE POLICY assignment_problem_links_select ON public.assignment_problem_links
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.assignments a
            WHERE a.id = assignment_id
              AND (
                  public.is_course_teacher(a.course_id, auth.uid())
                  OR (a.status = 'published' AND public.is_enrolled_student(a.course_id, auth.uid()))
                  OR public.has_role(auth.uid(), 'admin')
              )
        )
    );

DROP POLICY IF EXISTS assignment_problem_links_teacher_write ON public.assignment_problem_links;
CREATE POLICY assignment_problem_links_teacher_write ON public.assignment_problem_links
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.assignments a
            WHERE a.id = assignment_id
              AND (public.is_course_teacher(a.course_id, auth.uid()) OR public.has_role(auth.uid(), 'admin'))
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.assignments a
            WHERE a.id = assignment_id
              AND (public.is_course_teacher(a.course_id, auth.uid()) OR public.has_role(auth.uid(), 'admin'))
        )
    );

-- 6. assignment_submissions policies
DROP POLICY IF EXISTS assignment_submissions_select ON public.assignment_submissions;
CREATE POLICY assignment_submissions_select ON public.assignment_submissions
    FOR SELECT USING (
        student_id = auth.uid()
        OR public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

DROP POLICY IF EXISTS assignment_submissions_student_write ON public.assignment_submissions;
CREATE POLICY assignment_submissions_student_write ON public.assignment_submissions
    FOR INSERT WITH CHECK (
        student_id = auth.uid() AND public.is_enrolled_student(course_id, auth.uid())
    );

DROP POLICY IF EXISTS assignment_submissions_teacher_update ON public.assignment_submissions;
CREATE POLICY assignment_submissions_teacher_update ON public.assignment_submissions
    FOR UPDATE USING (
        student_id = auth.uid()
        OR public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

-- 7. assignment_attempts policies
DROP POLICY IF EXISTS assignment_attempts_select ON public.assignment_attempts;
CREATE POLICY assignment_attempts_select ON public.assignment_attempts
    FOR SELECT USING (
        student_id = auth.uid()
        OR public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

DROP POLICY IF EXISTS assignment_attempts_student_insert ON public.assignment_attempts;
CREATE POLICY assignment_attempts_student_insert ON public.assignment_attempts
    FOR INSERT WITH CHECK (
        student_id = auth.uid() AND public.is_enrolled_student(course_id, auth.uid())
    );

-- 8. assignment_grades policies (students NEVER see draft grades or other students' grades!)
DROP POLICY IF EXISTS assignment_grades_select ON public.assignment_grades;
CREATE POLICY assignment_grades_select ON public.assignment_grades
    FOR SELECT USING (
        (student_id = auth.uid() AND status IN ('published', 'revision_requested'))
        OR public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

DROP POLICY IF EXISTS assignment_grades_teacher_write ON public.assignment_grades;
CREATE POLICY assignment_grades_teacher_write ON public.assignment_grades
    FOR ALL
    USING (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    )
    WITH CHECK (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

-- 9. teacher_feedback policies
DROP POLICY IF EXISTS teacher_feedback_select ON public.teacher_feedback;
CREATE POLICY teacher_feedback_select ON public.teacher_feedback
    FOR SELECT USING (
        (student_id = auth.uid() AND is_visible_to_student = TRUE)
        OR public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

DROP POLICY IF EXISTS teacher_feedback_teacher_write ON public.teacher_feedback;
CREATE POLICY teacher_feedback_teacher_write ON public.teacher_feedback
    FOR ALL
    USING (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    )
    WITH CHECK (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

-- 10. grading_audit_events policies (append-only; strictly teacher-owner or admin)
DROP POLICY IF EXISTS grading_audit_events_teacher_select ON public.grading_audit_events;
CREATE POLICY grading_audit_events_teacher_select ON public.grading_audit_events
    FOR SELECT USING (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );

DROP POLICY IF EXISTS grading_audit_events_teacher_insert ON public.grading_audit_events;
CREATE POLICY grading_audit_events_teacher_insert ON public.grading_audit_events
    FOR INSERT WITH CHECK (
        public.is_course_teacher(course_id, auth.uid())
        OR public.has_role(auth.uid(), 'admin')
    );
