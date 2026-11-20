import Link from "next/link";
import { redirect } from "next/navigation";
import { LoginForm } from "@/features/auth/login-form";
import { fetchCurrentUser } from "@/lib/api-client";
import { resolvePostLoginRedirect } from "@/lib/auth/roles";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

interface LoginPageProps {
  searchParams: Promise<{ next?: string; error?: string }>;
}

function mapLoginError(errorCode?: string): string | undefined {
  if (errorCode === "auth_callback_failed") {
    return "Authentication link verification failed or expired. Please sign in again.";
  }
  if (errorCode === "supabase_unconfigured") {
    return "Supabase authentication is not configured for this environment yet.";
  }
  return undefined;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;

  const supabase = await createSupabaseServerClient();
  if (supabase) {
    const {
      data: { user: authUser },
    } = await supabase.auth.getUser();
    if (authUser) {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
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
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900"
          >
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-[#0b1221] text-xs font-bold text-teal-300">
              CM
            </span>
            CodeMentor AI
          </Link>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
            Sign in to your account
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Think First. Code Better.
          </p>
        </div>

        <LoginForm
          nextPath={params.next}
          initialError={mapLoginError(params.error)}
        />
      </div>
    </main>
  );
}
