import Link from "next/link";
import { LoginForm } from "@/features/auth/login-form";

interface LoginPageProps {
  searchParams: Promise<{ next?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;

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

        <LoginForm nextPath={params.next} />
      </div>
    </main>
  );
}
