"use client";

import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Loader2,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  acceptTeacherInvitation,
  inspectTeacherInvitation,
} from "@/lib/api-client";
import { isSupabaseConfigured } from "@/lib/env";
import { formatUtcDateTime } from "@/lib/format-date";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { TeacherInvitationInspectResponse } from "@/types/admin";

interface AcceptTeacherInviteClientProps {
  token?: string;
}

export function AcceptTeacherInviteClient({
  token,
}: AcceptTeacherInviteClientProps) {
  const [inspectState, setInspectState] = useState<
    "loading" | "ready" | "error" | "accepted"
  >(token ? "loading" : "error");
  const [invitation, setInvitation] =
    useState<TeacherInvitationInspectResponse | null>(null);
  const [signedInEmail, setSignedInEmail] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(
    token
      ? null
      : "No teacher invitation token was provided. Please open the complete invitation link from your administrator.",
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    async function load() {
      try {
        const info = await inspectTeacherInvitation(token!);
        if (cancelled) return;
        setInvitation(info);

        if (isSupabaseConfigured()) {
          const supabase = createSupabaseBrowserClient();
          const {
            data: { session },
          } = await supabase.auth.getSession();
          if (!cancelled && session?.access_token) {
            setAccessToken(session.access_token);
            setSignedInEmail(session.user?.email ?? null);
          }
        }

        if (!info.is_valid) {
          setErrorMsg(info.message);
          setInspectState("error");
        } else {
          setInspectState("ready");
        }
      } catch (err) {
        if (!cancelled) {
          setErrorMsg(
            err instanceof Error
              ? err.message
              : "Invalid or expired teacher invitation link.",
          );
          setInspectState("error");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleAccept() {
    if (!token || !accessToken) return;
    setAccepting(true);
    setErrorMsg(null);
    try {
      await acceptTeacherInvitation(accessToken, token);
      setInspectState("accepted");
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Unable to accept teacher invitation.",
      );
    } finally {
      setAccepting(false);
    }
  }

  const nextParam = token
    ? encodeURIComponent(`/accept-teacher-invite?token=${token}`)
    : "";

  if (inspectState === "loading") {
    return (
      <div
        role="status"
        className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-6 py-10 text-center"
      >
        <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
        <p className="text-sm font-semibold text-slate-800">
          Verifying teacher invitation...
        </p>
      </div>
    );
  }

  if (inspectState === "accepted") {
    return (
      <div className="space-y-4 rounded-2xl border border-teal-200 bg-teal-50/80 p-6 text-slate-900">
        <div className="flex items-center gap-2.5 text-base font-bold text-teal-950">
          <CheckCircle2 className="h-5 w-5 text-teal-700" />
          <span>Teacher access activated</span>
        </div>
        <p className="text-sm leading-relaxed text-slate-700">
          Your identity has been verified and the{" "}
          <strong className="font-semibold">Teacher</strong> role is now active
          on your account. You can now access the Teacher Portal to manage
          classes, assignments, and student submissions.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/teacher"
            className="inline-flex items-center gap-2 rounded-xl bg-[#0b1221] px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            <span>Open Teacher Dashboard</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/login/teacher"
            className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Teacher Login Portal
          </Link>
        </div>
      </div>
    );
  }

  if (inspectState === "error") {
    return (
      <div className="space-y-4 rounded-2xl border border-rose-200 bg-rose-50/80 p-6 text-slate-900">
        <div role="alert" className="flex items-start gap-2.5">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
          <div className="space-y-1">
            <p className="font-bold text-rose-950">
              Teacher invitation unavailable
            </p>
            <p className="text-sm leading-relaxed text-rose-900">
              {errorMsg ??
                "This teacher invitation link is invalid, expired, or has already been used."}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <Link
            href="/login/teacher"
            className="inline-flex items-center rounded-xl bg-[#0b1221] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Go to Teacher Login
          </Link>
          <Link
            href="/"
            className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {errorMsg ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      ) : null}

      {invitation ? (
        <div className="space-y-2 rounded-2xl border border-indigo-200 bg-indigo-50/70 p-5 text-sm text-slate-800">
          <div className="flex items-center gap-2 font-bold text-indigo-950">
            <ShieldCheck className="h-5 w-5 text-indigo-700" />
            <span>Verified Teacher Invitation</span>
          </div>
          <p>
            Invited Email:{" "}
            <strong className="font-mono text-slate-950">
              {invitation.email}
            </strong>
          </p>
          {invitation.full_name ? (
            <p>
              Instructor Name: <strong>{invitation.full_name}</strong>
            </p>
          ) : null}
          <p className="text-xs text-slate-600">
            Expires: {formatUtcDateTime(invitation.expires_at)}
          </p>
        </div>
      ) : null}

      {accessToken ? (
        <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <p className="text-sm text-slate-700">
            Currently signed in as{" "}
            <strong className="font-mono text-slate-950">
              {signedInEmail ?? "authenticated user"}
            </strong>
            . Click below to verify your invitation and activate Teacher access.
          </p>
          <button
            type="button"
            disabled={accepting}
            onClick={() => void handleAccept()}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#0b1221] px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
          >
            {accepting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Activating Teacher Access...</span>
              </>
            ) : (
              <>
                <UserCheck className="h-4 w-4" />
                <span>Accept Invitation &amp; Activate Teacher Role</span>
              </>
            )}
          </button>
        </div>
      ) : (
        <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-700">
          <p className="leading-relaxed">
            To accept this Teacher invitation, sign in with{" "}
            <strong className="font-mono text-slate-950">
              {invitation?.email}
            </strong>{" "}
            (or create your account with that exact email address and establish
            your password first).
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href={`/login?next=${nextParam}`}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-[#0b1221] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              <span>Sign In to Accept</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/register"
              className="inline-flex flex-1 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-100"
            >
              Create Account First
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
