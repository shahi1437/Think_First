import { NextResponse, type NextRequest } from "next/server";
import { fetchCurrentUser } from "@/lib/api-client";
import { resolvePostLoginRedirect } from "@/lib/auth/roles";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const rawNext = searchParams.get("next");

  if (code) {
    const supabase = await createSupabaseServerClient();
    if (supabase) {
      const { data, error } = await supabase.auth.exchangeCodeForSession(code);
      if (!error) {
        if (rawNext && rawNext.startsWith("/reset-password")) {
          try {
            const parsed = new URL(rawNext, origin);
            if (
              parsed.origin === origin &&
              parsed.pathname === "/reset-password"
            ) {
              return NextResponse.redirect(
                `${origin}${parsed.pathname}${parsed.search}`,
              );
            }
          } catch {
            // Fall through to standard role-based redirect
          }
        }
        const accessToken = data.session?.access_token;
        if (accessToken) {
          try {
            const user = await fetchCurrentUser(accessToken);
            const target = resolvePostLoginRedirect(user.roles, rawNext);
            return NextResponse.redirect(`${origin}${target}`);
          } catch {
            return NextResponse.redirect(
              `${origin}/login?error=verification_unavailable`,
            );
          }
        }
      }
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`);
}
