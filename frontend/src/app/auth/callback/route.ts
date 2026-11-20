import { NextResponse, type NextRequest } from "next/server";
import { fetchCurrentUser } from "@/lib/api-client";
import { resolvePostLoginRedirect, sanitizeInternalPath } from "@/lib/auth/roles";
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
        let target = sanitizeInternalPath(rawNext) ?? "/student";
        const accessToken = data.session?.access_token;
        if (accessToken) {
          try {
            const user = await fetchCurrentUser(accessToken);
            target = resolvePostLoginRedirect(user.roles, rawNext);
          } catch {
            target = sanitizeInternalPath(rawNext) ?? "/student";
          }
        }
        return NextResponse.redirect(`${origin}${target}`);
      }
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`);
}
