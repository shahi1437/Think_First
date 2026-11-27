-- =============================================================================
-- Migration 0011: In-App Notification Center (Role-Scoped & Strictly RLS-Protected)
-- Strictly additive, non-destructive migration preserving all existing 57 tables,
-- curriculum, submissions, classrooms, progress, and RLS policies.
--
-- Rollback instructions (safe because no existing tables are altered):
--   DROP TABLE IF EXISTS public.user_notifications;
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.user_notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    actor_user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    recipient_role text NOT NULL DEFAULT 'student'
        CHECK (recipient_role IN ('student', 'teacher', 'admin')),
    category text NOT NULL
        CHECK (
            category IN (
                'assignment',
                'submission_feedback',
                'grading',
                'announcement',
                'classroom',
                'ai_reminder',
                'system'
            )
        ),
    title text NOT NULL,
    body text NOT NULL,
    href text,
    source_key text,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_read boolean NOT NULL DEFAULT false,
    read_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Prevent duplicate derived notifications per recipient while allowing explicit announcements
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_notifications_recipient_source_key
    ON public.user_notifications (recipient_user_id, source_key)
    WHERE source_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_notifications_recipient_unread
    ON public.user_notifications (recipient_user_id, recipient_role, is_read, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_notifications_recipient_created
    ON public.user_notifications (recipient_user_id, created_at DESC);

-- Strict Row Level Security (58/58 public.* tables with ENABLE + FORCE RLS)
ALTER TABLE public.user_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_notifications FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_notifications_self_select ON public.user_notifications;
CREATE POLICY user_notifications_self_select
    ON public.user_notifications FOR SELECT TO authenticated
    USING (auth.uid() = recipient_user_id);

DROP POLICY IF EXISTS user_notifications_self_update ON public.user_notifications;
CREATE POLICY user_notifications_self_update
    ON public.user_notifications FOR UPDATE TO authenticated
    USING (auth.uid() = recipient_user_id)
    WITH CHECK (auth.uid() = recipient_user_id);

DROP POLICY IF EXISTS user_notifications_admin_select ON public.user_notifications;
CREATE POLICY user_notifications_admin_select
    ON public.user_notifications FOR SELECT TO authenticated
    USING (public.has_role(auth.uid(), 'admin'));
