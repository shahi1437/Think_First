import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { resolvePortalLoginPath } from "@/lib/auth/roles";

const PROTECTED_PREFIXES = ["/student", "/teacher", "/admin"];

function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function getSupabaseAuthCookieNames(request: NextRequest): string[] {
  return request.cookies
    .getAll()
    .filter((cookie) => cookie.name.startsWith("sb-") && cookie.value.length > 0)
    .map((cookie) => cookie.name);
}

function applyNoStoreHeaders(response: NextResponse): NextResponse {
  response.headers.set(
    "Cache-Control",
    "no-store, no-cache, must-revalidate, private",
  );
  response.headers.set("Pragma", "no-cache");
  return response;
}

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Skip unnecessary Supabase auth network checks on public pages for faster navigation
  if (!isProtectedPath(pathname)) {
    return NextResponse.next({ request });
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";
  const authCookieNames = getSupabaseAuthCookieNames(request);

  if (
    !supabaseUrl.startsWith("http") ||
    supabaseAnonKey.length <= 10 ||
    supabaseAnonKey.includes("replace-with") ||
    authCookieNames.length === 0
  ) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = resolvePortalLoginPath(pathname);
    loginUrl.search = "";
    loginUrl.searchParams.set("next", pathname);
    return applyNoStoreHeaders(NextResponse.redirect(loginUrl));
  }

  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value),
        );
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options),
        );
      },
    },
  });

  // Refresh session token if expired. Authorization is always re-verified in Server Components and FastAPI.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = resolvePortalLoginPath(pathname);
    loginUrl.search = "";
    loginUrl.searchParams.set("next", pathname);
    loginUrl.searchParams.set("error", "session_expired");
    const redirectResponse = NextResponse.redirect(loginUrl);

    // Propagate any cleared Supabase cookies and explicitly expire stale sb-* cookies to prevent redirect loops
    supabaseResponse.cookies.getAll().forEach((cookie) => {
      redirectResponse.cookies.set(cookie);
    });
    authCookieNames.forEach((name) => {
      redirectResponse.cookies.set(name, "", {
        path: "/",
        maxAge: 0,
      });
    });

    return applyNoStoreHeaders(redirectResponse);
  }

  return applyNoStoreHeaders(supabaseResponse);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
