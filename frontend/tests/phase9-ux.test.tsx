import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import nextConfig from "../next.config";
import { isNavLinkActive, NavLinks } from "../src/components/nav-links";

vi.mock("next/navigation", () => ({
  usePathname: () => "/student/problems",
}));

describe("Phase 9 UX & Security Hardening", () => {
  it("matches exact portal root vs active sub-routes accurately", () => {
    expect(isNavLinkActive("/student", "/student")).toBe(true);
    expect(isNavLinkActive("/student/problems", "/student")).toBe(false);
    expect(isNavLinkActive("/student/problems", "/student/problems")).toBe(true);
    expect(isNavLinkActive("/student/problems/two-sum", "/student/problems")).toBe(true);
    expect(isNavLinkActive("/admin/problems", "/admin")).toBe(false);
  });

  it("highlights active route and opens accessible mobile menu", () => {
    render(
      <NavLinks
        navLinks={[
          { href: "/student", label: "Overview" },
          { href: "/student/problems", label: "Problems" },
          { href: "/student/history", label: "History" },
        ]}
        showTeacherPortal
      />,
    );

    const activeLinks = screen.getAllByRole("link", { name: "Problems" });
    expect(activeLinks[0]).toHaveAttribute("aria-current", "page");

    const menuButton = screen.getByRole("button", {
      name: "Open navigation menu",
    });
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(menuButton);
    expect(
      screen.getByRole("navigation", { name: "Mobile navigation" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Close navigation menu" }),
    ).toHaveAttribute("aria-expanded", "true");
  });

  it("declares strict HTTP security headers in Next.js config", async () => {
    expect(nextConfig.poweredByHeader).toBe(false);
    const headerRules = await nextConfig.headers?.();
    expect(headerRules).toBeDefined();
    const rootRule = headerRules?.[0];
    const headerMap = Object.fromEntries(
      (rootRule?.headers ?? []).map((h) => [h.key, h.value]),
    );
    expect(headerMap["X-Content-Type-Options"]).toBe("nosniff");
    expect(headerMap["X-Frame-Options"]).toBe("DENY");
    expect(headerMap["Referrer-Policy"]).toBe(
      "strict-origin-when-cross-origin",
    );
  });
});
