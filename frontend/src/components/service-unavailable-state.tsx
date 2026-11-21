"use client";

import { AlertTriangle, Home, LogOut, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

interface ServiceUnavailableStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  showSignOut?: boolean;
}

export function ServiceUnavailableState({
  title = "Learning Service Temporarily Unavailable",
  message = "We could not reach the Think_First server to load your workspace right now. Please wait a moment and try again.",
  onRetry,
  showSignOut = true,
}: ServiceUnavailableStateProps) {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  function handleRetry() {
    if (onRetry) {
      onRetry();
      return;
    }
    router.refresh();
    window.location.reload();
  }

  async function handleSignOut() {
    setSigningOut(true);
    try {
      const supabase = createSupabaseBrowserClient();
      await supabase.auth.signOut();
    } catch {
      // Ignore client signout errors if Supabase is unconfigured
    } finally {
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-50 text-amber-700">
          <AlertTriangle className="h-6 w-6" aria-hidden="true" />
        </div>

        <h1 className="mt-5 text-xl font-bold tracking-tight text-slate-900">
          {title}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{message}</p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleRetry}
            className="inline-flex items-center gap-2 rounded-lg bg-[#0b1221] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Try Again
          </button>

          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <Home className="h-4 w-4" aria-hidden="true" />
            Return Home
          </Link>

          {showSignOut ? (
            <button
              type="button"
              disabled={signingOut}
              onClick={() => {
                void handleSignOut();
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 disabled:opacity-60"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              {signingOut ? "Signing out..." : "Sign out"}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
