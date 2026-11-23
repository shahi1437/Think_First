"use client";

import { QueryClientContext } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useContext, useState } from "react";
import {
  broadcastLogoutEvent,
  clearClientAuthCaches,
} from "@/lib/auth/auth-helpers";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export function LogoutButton() {
  const router = useRouter();
  const queryClient = useContext(QueryClientContext);
  const [signingOut, setSigningOut] = useState(false);

  async function handleLogout() {
    setSigningOut(true);
    try {
      const supabase = createSupabaseBrowserClient();
      try {
        await supabase.auth.signOut({ scope: "global" });
      } catch {
        await supabase.auth.signOut();
      }
    } finally {
      queryClient?.clear();
      clearClientAuthCaches();
      broadcastLogoutEvent();
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <button
      type="button"
      onClick={() => {
        void handleLogout();
      }}
      disabled={signingOut}
      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-slate-800 disabled:opacity-60"
    >
      <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
      {signingOut ? "Signing out..." : "Sign out"}
    </button>
  );
}
