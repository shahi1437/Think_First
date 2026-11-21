import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NavLinks } from "@/components/nav-links";
import { LoginForm } from "@/features/auth/login-form";
import { normalizeBaseUrl } from "@/lib/env";
import {
  canAccessPortal,
  getAuthorizedPortals,
  resolveDefaultPortalPath,
  resolvePostLoginRedirect,
} from "@/lib/auth/roles";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
  usePathname: () => "/admin",
}));

describe("Phase 10 Role-Aware Login & Portal Switcher", () => {
  it("computes authorized portals and default priority cleanly (Admin > Teacher > Student)", () => {
    expect(getAuthorizedPortals(["student"])).toEqual(["student"]);
    expect(getAuthorizedPortals(["student", "teacher"])).toEqual([
      "student",
      "teacher",
    ]);
    // Admin inherits Teacher portal access even without explicit teacher role
    expect(getAuthorizedPortals(["student", "admin"])).toEqual([
      "student",
      "teacher",
      "admin",
    ]);
    expect(canAccessPortal(["admin"], "teacher")).toBe(true);
    expect(canAccessPortal(["student"], "teacher")).toBe(false);
    expect(canAccessPortal(["teacher"], "admin")).toBe(false);

    expect(resolveDefaultPortalPath(["student"])).toBe("/student");
    expect(resolveDefaultPortalPath(["student", "teacher"])).toBe("/teacher");
    expect(resolveDefaultPortalPath(["student", "teacher", "admin"])).toBe(
      "/admin",
    );
  });

  it("enforces role authorization on requested post-login redirects", () => {
    expect(resolvePostLoginRedirect(["student"], undefined)).toBe("/student");
    expect(resolvePostLoginRedirect(["student", "teacher"], undefined)).toBe(
      "/teacher",
    );
    expect(resolvePostLoginRedirect(["student", "admin"], undefined)).toBe(
      "/admin",
    );
    expect(resolvePostLoginRedirect(["admin"], "/teacher/classes")).toBe(
      "/teacher/classes",
    );
    expect(resolvePostLoginRedirect(["student"], "/admin/problems")).toBe(
      "/student",
    );
    expect(resolvePostLoginRedirect(["teacher"], "/admin")).toBe("/teacher");
    expect(resolvePostLoginRedirect(["admin"], "//evil.example")).toBe("/admin");
  });

  it("routes LoginForm based on verified backend roles", async () => {
    pushMock.mockClear();
    refreshMock.mockClear();

    const firstRender = render(
      <LoginForm
        onAuthenticate={async () => ["student", "admin"]}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "admin@university.edu" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/admin");
    });

    firstRender.unmount();
    pushMock.mockClear();
    render(
      <LoginForm
        onAuthenticate={async () => ["student", "teacher"]}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "teacher@university.edu" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "Password123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/teacher");
    });
  });

  it("shows Student/Teacher/Admin portal switcher to Admin without teacher role and hides it from Student", () => {
    const { rerender } = render(
      <NavLinks
        navLinks={[{ href: "/student", label: "Dashboard" }]}
        activeRole="student"
        authorizedPortals={getAuthorizedPortals(["student"])}
      />,
    );
    expect(screen.queryByRole("group", { name: "Portal switcher" })).toBeNull();

    rerender(
      <NavLinks
        navLinks={[{ href: "/admin", label: "Overview" }]}
        activeRole="admin"
        authorizedPortals={getAuthorizedPortals(["student", "admin"])}
      />,
    );
    const switcher = screen.getByRole("group", { name: "Portal switcher" });
    expect(switcher).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Student" })).toHaveAttribute(
      "href",
      "/student",
    );
    expect(screen.getByRole("link", { name: "Teacher" })).toHaveAttribute(
      "href",
      "/teacher",
    );
    expect(screen.getByRole("link", { name: "Admin" })).toHaveAttribute(
      "href",
      "/admin",
    );
  });

  it("normalizes public API and app URLs without duplicate /api/v1 or trailing slashes", () => {
    expect(
      normalizeBaseUrl(
        " https://codementor-ai-backend-6sbr.onrender.com/api/v1/ ",
        true,
      ),
    ).toBe("https://codementor-ai-backend-6sbr.onrender.com");
    expect(
      normalizeBaseUrl("https://codementor-ai-backend-6sbr.onrender.com///", true),
    ).toBe("https://codementor-ai-backend-6sbr.onrender.com");
    expect(normalizeBaseUrl("https://think-first-pi.vercel.app/")).toBe(
      "https://think-first-pi.vercel.app",
    );
  });
});
