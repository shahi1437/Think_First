import { publicEnv } from "@/lib/env";
import type { RoleName } from "@/types/identity";

export const AUTH_LOGOUT_CHANNEL = "thinkfirst-auth-sync";
export const AUTH_LOGOUT_STORAGE_KEY = "thinkfirst:auth:logout-at";

const VALID_PORTALS: ReadonlySet<string> = new Set([
  "student",
  "teacher",
  "admin",
]);

export function parsePortalParam(raw?: string | null): RoleName | undefined {
  if (!raw) return undefined;
  const normalized = raw.trim().toLowerCase();
  if (VALID_PORTALS.has(normalized)) {
    return normalized as RoleName;
  }
  return undefined;
}

export function getAuthRedirectOrigin(): string {
  if (typeof window !== "undefined") {
    const browserOrigin = window.location.origin;
    if (
      browserOrigin.startsWith("http://") ||
      browserOrigin.startsWith("https://")
    ) {
      return browserOrigin.replace(/\/+$/, "");
    }
  }
  return publicEnv.NEXT_PUBLIC_APP_URL;
}

export function sanitizeCallbackNextPath(
  rawNext: string | null | undefined,
  origin: string,
): string | null {
  if (!rawNext) return null;
  const trimmed = rawNext.trim();
  if (
    !trimmed.startsWith("/") ||
    trimmed.startsWith("//") ||
    trimmed.includes("\\")
  ) {
    return null;
  }

  try {
    const base = new URL(origin);
    const parsed = new URL(trimmed, base);
    if (parsed.origin !== base.origin) {
      return null;
    }

    const pathname = parsed.pathname;
    if (
      pathname === "/login" ||
      pathname.startsWith("/login/") ||
      pathname === "/register" ||
      pathname.startsWith("/register/") ||
      pathname === "/auth/callback" ||
      pathname.startsWith("/auth/callback/")
    ) {
      return null;
    }

    if (pathname === "/reset-password") {
      const portal = parsePortalParam(parsed.searchParams.get("portal"));
      return portal ? `/reset-password?portal=${portal}` : "/reset-password";
    }

    return `${pathname}${parsed.search}`;
  } catch {
    return null;
  }
}

export function isRecoveryNextPath(rawNext?: string | null): boolean {
  if (!rawNext) return false;
  const trimmed = rawNext.trim();
  return (
    trimmed === "/reset-password" ||
    trimmed.startsWith("/reset-password?") ||
    trimmed.startsWith("/reset-password/")
  );
}

export function extractPortalFromNextPath(
  rawNext?: string | null,
): RoleName | undefined {
  if (!rawNext) return undefined;
  try {
    const parsed = new URL(rawNext, "http://localhost");
    const explicit = parsePortalParam(parsed.searchParams.get("portal"));
    if (explicit) return explicit;
    if (
      parsed.pathname === "/admin" ||
      parsed.pathname.startsWith("/admin/")
    ) {
      return "admin";
    }
    if (
      parsed.pathname === "/teacher" ||
      parsed.pathname.startsWith("/teacher/")
    ) {
      return "teacher";
    }
    if (
      parsed.pathname === "/student" ||
      parsed.pathname.startsWith("/student/")
    ) {
      return "student";
    }
    return undefined;
  } catch {
    return undefined;
  }
}

export function buildAuthCallbackUrl(
  nextPath: string,
  origin: string = getAuthRedirectOrigin(),
): string {
  const safeNext = sanitizeCallbackNextPath(nextPath, origin) ?? "/student";
  return `${origin.replace(/\/+$/, "")}/auth/callback?next=${encodeURIComponent(safeNext)}`;
}

export function mapAuthPageError(errorCode?: string | null): string | undefined {
  if (!errorCode) return undefined;
  switch (errorCode) {
    case "auth_callback_failed":
      return "Authentication link verification failed or expired. Please request a fresh link or sign in again.";
    case "recovery_expired":
      return "Your password recovery link is invalid, expired, or has already been used. Please request a new reset link below.";
    case "recovery_missing":
      return "No active password recovery link was detected. Please request a fresh password reset email to continue.";
    case "session_expired":
      return "Your session expired or was signed out. Please sign in again to continue.";
    case "verification_unavailable":
      return "Unable to verify your account permissions right now. Please sign in again in a moment.";
    case "supabase_unconfigured":
      return "Authentication service is not configured for this environment yet.";
    default:
      return undefined;
  }
}

export function formatRecoveryRequestError(rawMessage: string): string {
  const normalized = rawMessage.toLowerCase();
  if (
    normalized.includes("rate limit") ||
    normalized.includes("too many requests") ||
    normalized.includes("only request this after") ||
    normalized.includes("429")
  ) {
    return "Too many recovery requests were sent recently. Please wait a minute and check your inbox (including spam) before requesting another link.";
  }
  if (
    normalized.includes("smtp") ||
    normalized.includes("error sending recovery email") ||
    normalized.includes("error sending") ||
    normalized.includes("mailer")
  ) {
    return "Our email delivery service could not send the recovery email right now. Please try again shortly or contact your administrator.";
  }
  if (
    normalized.includes("failed to fetch") ||
    normalized.includes("network")
  ) {
    return "Unable to reach the authentication service. Please check your internet connection and try again.";
  }
  return rawMessage || "Unable to request password reset right now.";
}

export function clearClientAuthCaches(): void {
  if (typeof window === "undefined") return;
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < window.sessionStorage.length; i += 1) {
      const key = window.sessionStorage.key(i);
      if (key && key.startsWith("thinkfirst:")) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((key) => window.sessionStorage.removeItem(key));
  } catch {
    // Ignore storage restrictions in private browsing modes
  }
}

export function broadcastLogoutEvent(): void {
  if (typeof window === "undefined") return;
  try {
    if (typeof BroadcastChannel !== "undefined") {
      const channel = new BroadcastChannel(AUTH_LOGOUT_CHANNEL);
      channel.postMessage({ type: "LOGOUT", at: Date.now() });
      channel.close();
    }
  } catch {
    // Fallback to storage event below
  }

  try {
    window.localStorage.setItem(AUTH_LOGOUT_STORAGE_KEY, String(Date.now()));
  } catch {
    // Ignore storage restrictions in private browsing modes
  }
}
