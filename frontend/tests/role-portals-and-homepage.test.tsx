import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LandingPage from "@/app/(public)/page";
import { NavLinks } from "@/components/nav-links";
import { formatAuthError, LoginForm } from "@/features/auth/login-form";
import {
  getPortalMismatchMessage,
  isAuthorizedForLoginPortal,
  resolvePortalLoginPath,
} from "@/lib/auth/roles";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
  usePathname: () => "/teacher",
}));

describe("Public Homepage & Strict Role Portal Isolation", () => {
  it("renders three distinct role login links and excludes developer connectivity diagnostics from public homepage", () => {
    render(<LandingPage />);

    const studentLogin = screen.getByRole("link", { name: "STUDENT LOGIN" });
    const teacherLogin = screen.getByRole("link", { name: "TEACHER LOGIN" });
    const adminLogin = screen.getByRole("link", { name: "ADMIN LOGIN" });

    expect(studentLogin).toHaveAttribute("href", "/login/student");
    expect(teacherLogin).toHaveAttribute("href", "/login/teacher");
    expect(adminLogin).toHaveAttribute("href", "/login/admin");

    expect(screen.queryByText(/Platform Connectivity Check/i)).toBeNull();
    expect(screen.queryByText(/Backend API unreachable/i)).toBeNull();
    expect(screen.queryByText(/Core Educational Architecture/i)).toBeNull();
  });

  it("enforces strict portal role matching helpers", () => {
    expect(isAuthorizedForLoginPortal(["student"], "student")).toBe(true);
    expect(isAuthorizedForLoginPortal(["student"], "teacher")).toBe(false);
    expect(isAuthorizedForLoginPortal(["student"], "admin")).toBe(false);
    expect(isAuthorizedForLoginPortal(["student", "teacher"], "teacher")).toBe(
      true,
    );
    expect(isAuthorizedForLoginPortal(["student", "teacher"], "student")).toBe(
      false,
    );
    expect(isAuthorizedForLoginPortal(["student", "teacher"], "admin")).toBe(
      false,
    );
    expect(isAuthorizedForLoginPortal(["student", "admin"], "admin")).toBe(
      true,
    );
    expect(isAuthorizedForLoginPortal(["student", "admin"], "student")).toBe(
      false,
    );

    expect(resolvePortalLoginPath("/student/lessons")).toBe("/login/student");
    expect(resolvePortalLoginPath("/teacher/classes")).toBe("/login/teacher");
    expect(resolvePortalLoginPath("/admin/audit")).toBe("/login/admin");
    expect(getPortalMismatchMessage("teacher", ["student"])).toContain(
      "does not have Teacher access",
    );
  });

  it("blocks wrong-role login attempts on dedicated portals without redirecting", async () => {
    pushMock.mockClear();
    render(
      <LoginForm
        portal="teacher"
        onAuthenticate={async () => ["student"]}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "student@university.edu" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "SecurePass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /does not have Teacher access/i,
      );
    });
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("toggles password visibility on LoginForm", () => {
    render(<LoginForm portal="student" onAuthenticate={vi.fn()} />);

    const input = screen.getByLabelText(/Password/i);
    expect(input).toHaveAttribute("type", "password");

    const toggle = screen.getByRole("button", { name: /Toggle visibility/i });
    fireEvent.click(toggle);
    expect(input).toHaveAttribute("type", "text");
  });

  it("renders sidebar navigation with portal switcher and immediate pending feedback", () => {
    render(
      <NavLinks
        layout="sidebar"
        activeRole="teacher"
        authorizedPortals={["student", "teacher"]}
        navLinks={[
          { href: "/teacher", label: "Dashboard" },
          { href: "/teacher/classes", label: "My Classes" },
          { href: "/teacher/assignments", label: "Assignments" },
        ]}
      />,
    );

    expect(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Portal switcher" }),
    ).toBeInTheDocument();

    const classesLink = screen.getByRole("link", { name: "My Classes" });
    fireEvent.click(classesLink);
    expect(classesLink).toHaveAttribute("aria-busy", "true");
  });

  it("maps raw Supabase Invalid login credentials into a clear portal-aware message", () => {
    const teacherMsg = formatAuthError("Invalid login credentials", "teacher");
    expect(teacherMsg).toContain("Invalid email or password");
    expect(teacherMsg).toContain("Teacher");
    expect(teacherMsg).toContain("Forgot password");

    const unconfirmedMsg = formatAuthError("Email not confirmed", "student");
    expect(unconfirmedMsg).toContain("not confirmed");
  });
});
