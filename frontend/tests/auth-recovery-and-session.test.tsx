import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GET as authCallbackGet } from "@/app/auth/callback/route";
import { AuthSessionSync } from "@/components/auth-session-sync";
import { LogoutButton } from "@/components/logout-button";
import { ForgotPasswordForm } from "@/features/auth/forgot-password-form";
import { formatAuthError, LoginForm } from "@/features/auth/login-form";
import { ResetPasswordForm } from "@/features/auth/reset-password-form";
import { ApiClientError, BackendUnavailableError } from "@/lib/api-client";
import {
  AUTH_LOGOUT_STORAGE_KEY,
  buildAuthCallbackUrl,
  formatRecoveryRequestError,
  mapAuthPageError,
  sanitizeCallbackNextPath,
} from "@/lib/auth/auth-helpers";
import { proxy } from "@/proxy";

const pushMock = vi.fn();
const replaceMock = vi.fn();
const refreshMock = vi.fn();

const mockSignInWithPassword = vi.fn();
const mockGetSession = vi.fn();
const mockGetUser = vi.fn();
const mockSignOut = vi.fn();
const mockResend = vi.fn();
const mockResetPasswordForEmail = vi.fn();
const mockVerifyOtp = vi.fn();
const mockExchangeCodeForSession = vi.fn();
const mockSetSession = vi.fn();
const mockUpdateUser = vi.fn();
const mockOnAuthStateChange = vi.fn();

const mockServerVerifyOtp = vi.fn();
const mockServerExchangeCode = vi.fn();
const mockServerGetSession = vi.fn();
const mockServerGetUser = vi.fn();

const mockFetchCurrentUser = vi.fn();
const mockVerifyLoginPortal = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock,
    refresh: refreshMock,
  }),
}));

vi.mock("@/lib/env", () => ({
  publicEnv: {
    NEXT_PUBLIC_APP_URL: "https://think-first-pi.vercel.app",
    NEXT_PUBLIC_API_BASE_URL: "https://codementor-ai-backend-6sbr.onrender.com",
    NEXT_PUBLIC_SUPABASE_URL: "https://vsmrwfoqqjvomtjpypyv.supabase.co",
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-public-anon-key-value-123456",
  },
  isSupabaseConfigured: () => true,
  normalizeBaseUrl: (raw: string) => raw.trim().replace(/\/+$/, ""),
}));

vi.mock("@/lib/supabase/client", () => ({
  createSupabaseBrowserClient: () => ({
    auth: {
      signInWithPassword: mockSignInWithPassword,
      getSession: mockGetSession,
      getUser: mockGetUser,
      signOut: mockSignOut,
      resend: mockResend,
      resetPasswordForEmail: mockResetPasswordForEmail,
      verifyOtp: mockVerifyOtp,
      exchangeCodeForSession: mockExchangeCodeForSession,
      setSession: mockSetSession,
      updateUser: mockUpdateUser,
      onAuthStateChange: mockOnAuthStateChange,
    },
  }),
}));

vi.mock("@supabase/ssr", () => ({
  createServerClient: (
    _url: string,
    _key: string,
    opts?: {
      cookies?: {
        setAll?: (
          cookiesToSet: Array<{
            name: string;
            value: string;
            options: Record<string, unknown>;
          }>,
        ) => void;
      };
    },
  ) => ({
    auth: {
      verifyOtp: async (...args: unknown[]) => {
        const res = await mockServerVerifyOtp(...args);
        if (!res?.error) {
          opts?.cookies?.setAll?.([
            {
              name: "sb-vsmrwfoqqjvomtjpypyv-auth-token",
              value: "mock-session-cookie",
              options: { path: "/" },
            },
          ]);
        }
        return res;
      },
      exchangeCodeForSession: async (...args: unknown[]) => {
        const res = await mockServerExchangeCode(...args);
        if (!res?.error) {
          opts?.cookies?.setAll?.([
            {
              name: "sb-vsmrwfoqqjvomtjpypyv-auth-token",
              value: "mock-session-cookie",
              options: { path: "/" },
            },
          ]);
        }
        return res;
      },
      getSession: mockServerGetSession,
      getUser: mockServerGetUser,
    },
  }),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    fetchCurrentUser: (...args: unknown[]) => mockFetchCurrentUser(...args),
    verifyLoginPortal: (...args: unknown[]) => mockVerifyLoginPortal(...args),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
  mockSignOut.mockResolvedValue({ error: null });
  mockOnAuthStateChange.mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  });
  window.history.replaceState(null, "", "/");
  window.location.hash = "";
});

describe("auth-helpers security & formatting", () => {
  it("validates same-origin callback paths and rejects open redirects", () => {
    const origin = "https://think-first-pi.vercel.app";
    expect(
      sanitizeCallbackNextPath("/reset-password?portal=teacher", origin),
    ).toBe("/reset-password?portal=teacher");
    expect(sanitizeCallbackNextPath("/student/lessons", origin)).toBe(
      "/student/lessons",
    );
    expect(sanitizeCallbackNextPath("//evil.example.com", origin)).toBeNull();
    expect(
      sanitizeCallbackNextPath("https://evil.example.com/steal", origin),
    ).toBeNull();
    expect(sanitizeCallbackNextPath("/\\evil.example.com", origin)).toBeNull();
    expect(sanitizeCallbackNextPath("/login/student", origin)).toBeNull();
    expect(sanitizeCallbackNextPath("/auth/callback", origin)).toBeNull();
  });

  it("builds safe callback URLs and maps recovery/session error codes", () => {
    expect(
      buildAuthCallbackUrl(
        "/reset-password?portal=admin",
        "https://think-first-pi.vercel.app",
      ),
    ).toBe(
      "https://think-first-pi.vercel.app/auth/callback?next=%2Freset-password%3Fportal%3Dadmin",
    );
    expect(mapAuthPageError("recovery_expired")).toMatch(/invalid, expired/i);
    expect(mapAuthPageError("session_expired")).toMatch(/expired or was signed out/i);
    expect(formatRecoveryRequestError("Email rate limit exceeded (429)")).toMatch(
      /Too many recovery requests/i,
    );
    expect(formatAuthError("Email not confirmed", "student")).toMatch(
      /not confirmed yet/i,
    );
  });
});

describe("GET /auth/callback route handler", () => {
  it("verifies cross-device/mobile token_hash recovery links and propagates cookies", async () => {
    mockServerVerifyOtp.mockResolvedValue({
      data: { session: { access_token: "tok-recovery" } },
      error: null,
    });

    const req = new NextRequest(
      "https://think-first-pi.vercel.app/auth/callback?token_hash=hash123&type=recovery&next=%2Freset-password%3Fportal%3Dteacher",
    );
    const res = await authCallbackGet(req);

    expect(mockServerVerifyOtp).toHaveBeenCalledWith({
      token_hash: "hash123",
      type: "recovery",
    });
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "https://think-first-pi.vercel.app/reset-password?portal=teacher",
    );
    expect(res.headers.get("cache-control")).toContain("no-store");
    expect(res.headers.get("set-cookie")).toContain(
      "sb-vsmrwfoqqjvomtjpypyv-auth-token=mock-session-cookie",
    );
  });

  it("routes expired or failed recovery callbacks to /reset-password?error=recovery_expired", async () => {
    mockServerExchangeCode.mockResolvedValue({
      data: { session: null },
      error: { message: "PKCE code verifier not found" },
    });

    const req = new NextRequest(
      "https://think-first-pi.vercel.app/auth/callback?code=bad-mobile-code&next=%2Freset-password%3Fportal%3Dadmin",
    );
    const res = await authCallbackGet(req);

    expect(res.headers.get("location")).toBe(
      "https://think-first-pi.vercel.app/reset-password?error=recovery_expired&portal=admin",
    );
  });

  it("handles Supabase otp_expired error query params cleanly", async () => {
    const req = new NextRequest(
      "https://think-first-pi.vercel.app/auth/callback?error=access_denied&error_code=otp_expired&next=%2Freset-password%3Fportal%3Dstudent",
    );
    const res = await authCallbackGet(req);

    expect(res.headers.get("location")).toBe(
      "https://think-first-pi.vercel.app/reset-password?error=recovery_expired&portal=student",
    );
  });

  it("blocks open-redirect targets on verified signup callback", async () => {
    mockServerVerifyOtp.mockResolvedValue({
      data: { session: { access_token: "tok-stu" } },
      error: null,
    });
    mockFetchCurrentUser.mockResolvedValue({
      id: "u1",
      email: "s@thinkfirst.test",
      full_name: "Student",
      roles: ["student"],
      onboarding_completed: true,
    });

    const req = new NextRequest(
      "https://think-first-pi.vercel.app/auth/callback?token_hash=ok&type=signup&next=//evil.example.com",
    );
    const res = await authCallbackGet(req);

    expect(res.headers.get("location")).toBe(
      "https://think-first-pi.vercel.app/student",
    );
  });
});

describe("LoginForm portal verification & error distinction", () => {
  it("distinguishes valid password with wrong portal role and suggests authorized portal", async () => {
    mockSignInWithPassword.mockResolvedValue({ error: null });
    mockGetSession.mockResolvedValue({
      data: { session: { access_token: "valid-jwt" } },
    });
    mockVerifyLoginPortal.mockRejectedValue(
      new ApiClientError(
        "This account does not have Teacher portal access.",
        403,
        "PORTAL_ACCESS_DENIED",
      ),
    );
    mockFetchCurrentUser.mockResolvedValue({
      id: "stu-1",
      email: "student@thinkfirst.test",
      full_name: "Student",
      roles: ["student"],
      onboarding_completed: true,
    });

    render(<LoginForm portal="teacher" />);
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "student@thinkfirst.test" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "ValidPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in as Teacher/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /password was accepted, but this account does not have Teacher portal access/i,
      );
    });
    expect(
      screen.getByRole("link", { name: /Open Student Login/i }),
    ).toHaveAttribute("href", "/login/student");
    expect(mockSignOut).toHaveBeenCalled();
  });

  it("shows distinct confirmation guidance and resend button for unconfirmed email", async () => {
    mockSignInWithPassword.mockResolvedValue({
      error: { message: "Email not confirmed" },
    });
    mockResend.mockResolvedValue({ error: null });

    render(<LoginForm portal="student" />);
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "pending@thinkfirst.test" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "ValidPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in as Student/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/not confirmed yet/i);
    });

    fireEvent.click(
      screen.getByRole("button", { name: /Resend confirmation email/i }),
    );
    await waitFor(() => {
      expect(mockResend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "signup",
          email: "pending@thinkfirst.test",
        }),
      );
    });
  });

  it("shows distinct JWT error on backend 401 and connectivity error when backend is unreachable", async () => {
    mockSignInWithPassword.mockResolvedValue({ error: null });
    mockGetSession.mockResolvedValue({
      data: { session: { access_token: "expired-jwt" } },
    });
    mockVerifyLoginPortal.mockRejectedValueOnce(
      new ApiClientError("Invalid JWT", 401, "UNAUTHORIZED"),
    );

    const { unmount } = render(<LoginForm portal="admin" />);
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "admin@thinkfirst.test" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "ValidPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in as Admin/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /could not be verified by the learning server/i,
      );
    });
    unmount();

    mockVerifyLoginPortal.mockRejectedValueOnce(new BackendUnavailableError());
    render(<LoginForm portal="teacher" />);
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "teacher@thinkfirst.test" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "ValidPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in as Teacher/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /learning server is temporarily unreachable/i,
      );
    });
  });
});

describe("ForgotPasswordForm & ResetPasswordForm", () => {
  it("submits password recovery with portal context and safe non-enumerating feedback", async () => {
    mockResetPasswordForEmail.mockResolvedValue({ error: null });
    render(<ForgotPasswordForm portal="teacher" />);

    fireEvent.change(screen.getByLabelText(/Account email/i), {
      target: { value: "Teacher@ThinkFirst.test" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Send password reset link/i }),
    );

    await waitFor(() => {
      expect(mockResetPasswordForEmail).toHaveBeenCalledWith(
        "teacher@thinkfirst.test",
        expect.objectContaining({
          redirectTo: expect.stringContaining(
            "/auth/callback?next=%2Freset-password%3Fportal%3Dteacher",
          ),
        }),
      );
    });
    expect(screen.getByText(/Recovery link sent/i)).toBeInTheDocument();
  });

  it("renders clear expired-link recovery state when recovery link is invalid or missing", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null }, error: null });
    mockGetSession.mockResolvedValue({ data: { session: null } });

    render(
      <ResetPasswordForm portal="teacher" initialErrorCode="recovery_expired" />,
    );

    expect(
      screen.getByText(/Password recovery link unavailable/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Request a New Reset Link/i }),
    ).toHaveAttribute("href", "/forgot-password?portal=teacher");
  });

  it("verifies token_hash directly, validates password, updates password, and signs out globally", async () => {
    window.history.replaceState(
      null,
      "",
      "/reset-password?portal=teacher&token_hash=direct-hash&type=recovery",
    );
    mockVerifyOtp.mockResolvedValue({ error: null });
    mockUpdateUser.mockResolvedValue({ error: null });

    render(<ResetPasswordForm portal="teacher" />);

    await waitFor(() => {
      expect(screen.getByLabelText(/^New password$/i)).toBeInTheDocument();
    });
    expect(mockVerifyOtp).toHaveBeenCalledWith({
      token_hash: "direct-hash",
      type: "recovery",
    });

    fireEvent.change(screen.getByLabelText(/^New password$/i), {
      target: { value: "NewSecurePass123!" },
    });
    fireEvent.change(screen.getByLabelText(/Confirm new password/i), {
      target: { value: "MismatchPass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save New Password/i }));

    await waitFor(() => {
      expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Confirm new password/i), {
      target: { value: "NewSecurePass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save New Password/i }));

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({
        password: "NewSecurePass123!",
      });
      expect(mockSignOut).toHaveBeenCalledWith({ scope: "global" });
      expect(
        screen.getByText(/Password updated successfully/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("link", { name: /Continue to Teacher Login/i }),
    ).toHaveAttribute("href", "/login/teacher");
  });
});

describe("LogoutButton, AuthSessionSync & proxy session protection", () => {
  it("clears React Query cache, broadcasts logout, and replaces route to /login", async () => {
    const queryClient = new QueryClient();
    const clearSpy = vi.spyOn(queryClient, "clear");

    render(
      <QueryClientProvider client={queryClient}>
        <LogoutButton />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Sign out/i }));

    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalledWith({ scope: "global" });
      expect(clearSpy).toHaveBeenCalled();
      expect(replaceMock).toHaveBeenCalledWith("/login");
      expect(refreshMock).toHaveBeenCalled();
    });
  });

  it("synchronizes logout across tabs via storage event", async () => {
    const queryClient = new QueryClient();
    const clearSpy = vi.spyOn(queryClient, "clear");

    render(
      <QueryClientProvider client={queryClient}>
        <AuthSessionSync activeRole="student" />
      </QueryClientProvider>,
    );

    window.dispatchEvent(
      new StorageEvent("storage", {
        key: AUTH_LOGOUT_STORAGE_KEY,
        newValue: String(Date.now()),
      }),
    );

    await waitFor(() => {
      expect(clearSpy).toHaveBeenCalled();
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
  });

  it("clears stale sb-* cookies and redirects with session_expired when proxy getUser fails", async () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL =
      "https://vsmrwfoqqjvomtjpypyv.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-public-anon-key-value-123456";
    mockServerGetUser.mockResolvedValue({ data: { user: null } });

    const req = new NextRequest("https://think-first-pi.vercel.app/teacher", {
      headers: {
        cookie: "sb-vsmrwfoqqjvomtjpypyv-auth-token=stale-expired-value",
      },
    });
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "https://think-first-pi.vercel.app/login/teacher?next=%2Fteacher&error=session_expired",
    );
    expect(res.headers.get("cache-control")).toContain("no-store");
    expect(res.headers.get("set-cookie")).toContain("Max-Age=0");
  });
});
