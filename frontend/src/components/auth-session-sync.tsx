"use client";

import { QueryClientContext } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useContext, useEffect, useRef } from "react";
import {
  AUTH_LOGOUT_CHANNEL,
  AUTH_LOGOUT_STORAGE_KEY,
  clearClientAuthCaches,
} from "@/lib/auth/auth-helpers";
import { PORTAL_LOGIN_PATHS } from "@/lib/auth/roles";
import { isSupabaseConfigured } from "@/lib/env";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { RoleName } from "@/types/identity";

interface AuthSessionSyncProps {
  activeRole: RoleName;
}

/**
 * Keeps protected portal tabs synchronized on logout, session revocation,
 * and Browser Back (BFCache) restoration without causing redirect loops.
 */
export function AuthSessionSync({ activeRole }: AuthSessionSyncProps) {
  const router = useRouter();
  const queryClient = useContext(QueryClientContext);
  const redirectingRef = useRef(false);

  useEffect(() => {
    if (!isSupabaseConfigured()) {
      return;
    }

    const supabase = createSupabaseBrowserClient();
    const loginPath = PORTAL_LOGIN_PATHS[activeRole] ?? "/login";

    const handleSessionEnded = (reason: "logout" | "expired") => {
      if (redirectingRef.current) return;
      redirectingRef.current = true;
      queryClient?.clear();
      clearClientAuthCaches();
      const target =
        reason === "expired" ? `${loginPath}?error=session_expired` : "/login";
      router.replace(target);
      router.refresh();
    };

    const verifyActiveSession = async () => {
      if (redirectingRef.current) return;
      try {
        const {
          data: { user },
          error,
        } = await supabase.auth.getUser();
        if (error || !user) {
          handleSessionEnded("expired");
        }
      } catch {
        // Ignore transient offline network blips; server guard re-verifies on navigation
      }
    };

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        handleSessionEnded("logout");
      } else if (event === "TOKEN_REFRESHED" && !session) {
        handleSessionEnded("expired");
      }
    });

    let channel: BroadcastChannel | null = null;
    try {
      if (typeof BroadcastChannel !== "undefined") {
        channel = new BroadcastChannel(AUTH_LOGOUT_CHANNEL);
        channel.onmessage = (event: MessageEvent) => {
          if (
            event.data &&
            typeof event.data === "object" &&
            (event.data as { type?: string }).type === "LOGOUT"
          ) {
            handleSessionEnded("logout");
          }
        };
      }
    } catch {
      channel = null;
    }

    const onStorage = (event: StorageEvent) => {
      if (event.key === AUTH_LOGOUT_STORAGE_KEY && event.newValue) {
        handleSessionEnded("logout");
      }
    };

    const onPageShow = (event: PageTransitionEvent) => {
      // Browser Back/Forward restored a cached protected view (BFCache)
      if (event.persisted) {
        void verifyActiveSession();
      }
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void verifyActiveSession();
      }
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener("pageshow", onPageShow);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      subscription.unsubscribe();
      channel?.close();
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("pageshow", onPageShow);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [activeRole, queryClient, router]);

  return null;
}
