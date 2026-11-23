import { createServerClient, type CookieOptions } from "@supabase/ssr";
import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse, type NextRequest } from "next/server";
import { fetchCurrentUser } from "@/lib/api-client";
import {
  extractPortalFromNextPath,
  isRecoveryNextPath,
  parsePortalParam,
  sanitizeCallbackNextPath,
} from "@/lib/auth/auth-helpers";
import { PORTAL_LOGIN_PATHS, resolvePostLoginRedirect } from "@/lib/auth/roles";
import { isSupabaseConfigured, publicEnv } from "@/lib/env";

const ALLOWED_OTP_TYPES: ReadonlySet<EmailOtpType> = new Set([
  "recovery",
  "signup",
  "magiclink",
  "email",
  "email_change",
  "invite",
]);

function parseOtpType(raw: string | null): EmailOtpType | null {
  if (!raw) return null;
  const normalized = raw.trim().toLowerCase() as EmailOtpType;
  return ALLOWED_OTP_TYPES.has(normalized) ? normalized : null;
}

function createNoStoreRedirect(
  url: string,
  pendingCookies: Array<{ name: string; value: string; options: CookieOptions }> = [],
): NextResponse {
  const response = NextResponse.redirect(url);
  response.headers.set(
    "Cache-Control",
    "no-store, no-cache, must-revalidate, private",
  );
  response.headers.set("Pragma", "no-cache");
  for (const { name, value, options } of pendingCookies) {
    response.cookies.set(name, value, options);
  }
  return response;
}

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const tokenHash = searchParams.get("token_hash");
  const otpType = parseOtpType(searchParams.get("type"));
  const rawNext = searchParams.get("next");
  const errorParam = searchParams.get("error");
  const errorCodeParam = searchParams.get("error_code");

  const safeNext = sanitizeCallbackNextPath(rawNext, origin);
  const portal =
    parsePortalParam(searchParams.get("portal")) ??
    extractPortalFromNextPath(safeNext ?? rawNext);
  const isRecoveryFlow =
    otpType === "recovery" || isRecoveryNextPath(safeNext ?? rawNext);

  const recoveryFailureUrl = (errorCode: "recovery_expired" | "recovery_missing") => {
    const params = new URLSearchParams({ error: errorCode });
    if (portal) params.set("portal", portal);
    return `${origin}/reset-password?${params.toString()}`;
  };

  const loginFailureUrl = (errorCode: string) => {
    const baseLogin = portal ? PORTAL_LOGIN_PATHS[portal] : "/login";
    return `${origin}${baseLogin}?error=${encodeURIComponent(errorCode)}`;
  };

  if (errorParam || errorCodeParam) {
    if (isRecoveryFlow) {
      return createNoStoreRedirect(recoveryFailureUrl("recovery_expired"));
    }
    return createNoStoreRedirect(loginFailureUrl("auth_callback_failed"));
  }

  if (!isSupabaseConfigured()) {
    return createNoStoreRedirect(loginFailureUrl("supabase_unconfigured"));
  }

  if (!code && !(tokenHash && otpType)) {
    if (isRecoveryFlow) {
      return createNoStoreRedirect(recoveryFailureUrl("recovery_missing"));
    }
    return createNoStoreRedirect(loginFailureUrl("auth_callback_failed"));
  }

  const pendingCookies: Array<{
    name: string;
    value: string;
    options: CookieOptions;
  }> = [];

  const supabase = createServerClient(
    publicEnv.NEXT_PUBLIC_SUPABASE_URL,
    publicEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            pendingCookies.push({ name, value, options });
          });
        },
      },
    },
  );

  let accessToken: string | undefined;

  if (tokenHash && otpType) {
    // Supports cross-device and mobile email links without requiring a PKCE verifier cookie
    const { data, error } = await supabase.auth.verifyOtp({
      token_hash: tokenHash,
      type: otpType,
    });
    if (error) {
      return createNoStoreRedirect(
        isRecoveryFlow
          ? recoveryFailureUrl("recovery_expired")
          : loginFailureUrl("auth_callback_failed"),
      );
    }
    accessToken = data.session?.access_token;
  } else if (code) {
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      return createNoStoreRedirect(
        isRecoveryFlow
          ? recoveryFailureUrl("recovery_expired")
          : loginFailureUrl("auth_callback_failed"),
      );
    }
    accessToken = data.session?.access_token;
  }

  if (isRecoveryFlow) {
    const resetTarget = portal
      ? `/reset-password?portal=${portal}`
      : "/reset-password";
    return createNoStoreRedirect(`${origin}${resetTarget}`, pendingCookies);
  }

  if (!accessToken) {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    accessToken = session?.access_token;
  }

  if (accessToken) {
    try {
      const user = await fetchCurrentUser(accessToken);
      const target = resolvePostLoginRedirect(user.roles, safeNext);
      return createNoStoreRedirect(`${origin}${target}`, pendingCookies);
    } catch {
      return createNoStoreRedirect(
        loginFailureUrl("verification_unavailable"),
        pendingCookies,
      );
    }
  }

  return createNoStoreRedirect(loginFailureUrl("auth_callback_failed"));
}
