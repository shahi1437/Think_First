import { GraduationCap, KeyRound, ShieldCheck, Users } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { LoginForm } from "@/features/auth/login-form";
import { fetchCurrentUser } from "@/lib/api-client";
import { mapAuthPageError } from "@/lib/auth/auth-helpers";
import { resolvePostLoginRedirect } from "@/lib/auth/roles";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

interface LoginPageProps {
  searchParams: Promise<{ next?: string; error?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;

  const supabase = await createSupabaseServerClient();
  if (supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.access_token) {
      const {
        data: { user: authUser },
      } = await supabase.auth.getUser();
      if (authUser) {
        let target: string | null = null;
        try {
          const user = await fetchCurrentUser(session.access_token);
          target = resolvePostLoginRedirect(user.roles, params.next);
        } catch {
          target = null;
        }
        if (target) {
          redirect(target);
        }
      }
    }
  }

  return (
    <AuthPortalShell
      badge="Portal Sign In"
      title="Choose your login portal"
      subtitle="Select your dedicated role portal below, or sign in directly to be routed to your authorized workspace."
      icon={KeyRound}
      accent="indigo"
      footerLinks={[
        { href: "/register", label: "Create Student Account" },
        { href: "/", label: "Back to Home" },
      ]}
    >
      <div className="mb-6 grid grid-cols-3 gap-2">
        <Link
          href="/login/student"
          className="flex flex-col items-center gap-1 rounded-xl border border-teal-200 bg-teal-50/70 px-2 py-2.5 text-center text-xs font-semibold text-teal-900 transition hover:bg-teal-100"
        >
          <GraduationCap className="h-4 w-4 text-teal-700" aria-hidden="true" />
          <span>Student</span>
        </Link>
        <Link
          href="/login/teacher"
          className="flex flex-col items-center gap-1 rounded-xl border border-indigo-200 bg-indigo-50/70 px-2 py-2.5 text-center text-xs font-semibold text-indigo-900 transition hover:bg-indigo-100"
        >
          <Users className="h-4 w-4 text-indigo-700" aria-hidden="true" />
          <span>Teacher</span>
        </Link>
        <Link
          href="/login/admin"
          className="flex flex-col items-center gap-1 rounded-xl border border-slate-300 bg-slate-100 px-2 py-2.5 text-center text-xs font-semibold text-slate-900 transition hover:bg-slate-200"
        >
          <ShieldCheck className="h-4 w-4 text-slate-700" aria-hidden="true" />
          <span>Admin</span>
        </Link>
      </div>

      <LoginForm
        nextPath={params.next}
        initialError={mapAuthPageError(params.error)}
      />
    </AuthPortalShell>
  );
}
