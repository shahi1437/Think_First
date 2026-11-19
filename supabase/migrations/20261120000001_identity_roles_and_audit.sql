-- =============================================================================
-- Migration 0001: Extensions, Identity, Roles, Preferences, Audit Logs & RLS
-- Authoritative schema for CodeMentor AI (Think_First) — Phase 2
-- Compatible with Local Supabase CLI and Cloud Supabase PostgreSQL 17+
-- =============================================================================

-- 1. Required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Reusable updated_at trigger function
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- 3. Core Identity Tables

-- 3.1 User Profiles (1:1 with Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email text NOT NULL UNIQUE,
    full_name text NOT NULL DEFAULT '',
    avatar_url text,
    onboarding_completed boolean NOT NULL DEFAULT false,
    onboarding_completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT profiles_email_nonempty CHECK (length(trim(email)) > 3)
);

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 3.2 User Preferences & Smart Onboarding State (1:1 with profiles)
CREATE TABLE IF NOT EXISTS public.user_preferences (
    user_id uuid PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    programming_experience text NOT NULL DEFAULT 'none'
        CHECK (programming_experience IN ('none', 'beginner', 'basic', 'intermediate', 'advanced')),
    preferred_language text NOT NULL DEFAULT 'python'
        CHECK (preferred_language IN ('python', 'javascript', 'cpp', 'java')),
    learning_goal text NOT NULL DEFAULT 'university_coursework'
        CHECK (learning_goal IN (
            'school_fundamentals',
            'university_coursework',
            'debugging_mastery',
            'interview_prep',
            'competitive_programming'
        )),
    daily_practice_minutes integer NOT NULL DEFAULT 30
        CHECK (daily_practice_minutes BETWEEN 10 AND 240),
    preferred_explanation_language text NOT NULL DEFAULT 'en'
        CHECK (preferred_explanation_language IN ('en', 'bn')),
    starting_preference text NOT NULL DEFAULT 'diagnostic_assessment'
        CHECK (starting_preference IN ('guided_beginner', 'diagnostic_assessment')),
    recommended_entry_track text
        CHECK (recommended_entry_track IN ('foundation_lessons', 'diagnostic_assessment')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_user_preferences_updated_at
    BEFORE UPDATE ON public.user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 3.3 Protected Role Assignments (DB-backed RBAC — never client-mutable)
CREATE TABLE IF NOT EXISTS public.user_roles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('student', 'teacher', 'admin')),
    granted_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    granted_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_roles_user_role UNIQUE (user_id, role)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON public.user_roles (user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON public.user_roles (role);

-- 3.4 Immutable Governance & Security Audit Logs
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    action text NOT NULL CHECK (length(trim(action)) > 0),
    target_type text NOT NULL CHECK (length(trim(target_type)) > 0),
    target_id text NOT NULL CHECK (length(trim(target_id)) > 0),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    request_id text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON public.audit_logs (actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs (created_at DESC);

-- 4. Role Helper Function for RLS Policies (avoids RLS recursion on user_roles)
CREATE OR REPLACE FUNCTION public.has_role(target_user_id uuid, required_role text)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.user_roles ur
        WHERE ur.user_id = target_user_id
          AND ur.role = required_role
    );
$$;

REVOKE ALL ON FUNCTION public.has_role(uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.has_role(uuid, text) TO authenticated, service_role;

-- 5. Automatic Signup Provisioning Trigger
-- Always assigns ONLY the 'student' role. Client signup metadata can NEVER set a privileged role.
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    initial_name text;
BEGIN
    initial_name := COALESCE(
        NULLIF(trim(NEW.raw_user_meta_data ->> 'full_name'), ''),
        ''
    );

    INSERT INTO public.profiles (id, email, full_name)
    VALUES (NEW.id, lower(NEW.email), initial_name)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.user_roles (user_id, role, granted_by)
    VALUES (NEW.id, 'student', NULL)
    ON CONFLICT (user_id, role) DO NOTHING;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_auth_user();

-- 6. Row Level Security (RLS) Policies

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles FORCE ROW LEVEL SECURITY;

ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences FORCE ROW LEVEL SECURITY;

ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles FORCE ROW LEVEL SECURITY;

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs FORCE ROW LEVEL SECURITY;

-- 6.1 profiles policies
CREATE POLICY profiles_select_own
    ON public.profiles
    FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY profiles_select_admin
    ON public.profiles
    FOR SELECT
    TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));

CREATE POLICY profiles_update_own
    ON public.profiles
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- 6.2 user_preferences policies
CREATE POLICY user_preferences_select_own
    ON public.user_preferences
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY user_preferences_select_admin
    ON public.user_preferences
    FOR SELECT
    TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));

CREATE POLICY user_preferences_insert_own
    ON public.user_preferences
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_preferences_update_own
    ON public.user_preferences
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 6.3 user_roles policies
-- Users can ONLY read their own roles. Zero client INSERT/UPDATE/DELETE policies prevent self-escalation.
CREATE POLICY user_roles_select_own
    ON public.user_roles
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY user_roles_select_admin
    ON public.user_roles
    FOR SELECT
    TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));

-- 6.4 audit_logs policies
-- Read-only for admins; writes performed exclusively by backend privileged service.
CREATE POLICY audit_logs_select_admin
    ON public.audit_logs
    FOR SELECT
    TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));
