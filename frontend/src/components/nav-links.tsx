"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { PORTAL_LABELS, PORTAL_PATHS } from "@/lib/auth/roles";
import type { RoleName } from "@/types/identity";

export interface AppNavLink {
  href: string;
  label: string;
}

interface NavLinksProps {
  navLinks: AppNavLink[];
  activeRole?: RoleName;
  authorizedPortals?: RoleName[];
  showTeacherPortal?: boolean;
  showAdminStudio?: boolean;
}

const ROOT_PORTAL_PATHS = new Set(["/student", "/teacher", "/admin"]);

export function isNavLinkActive(pathname: string, href: string): boolean {
  if (ROOT_PORTAL_PATHS.has(href)) {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function buildPortalList(
  authorizedPortals?: RoleName[],
  activeRole?: RoleName,
  showTeacherPortal?: boolean,
  showAdminStudio?: boolean,
): RoleName[] {
  if (authorizedPortals && authorizedPortals.length > 0) {
    return authorizedPortals;
  }
  const derived: RoleName[] = ["student"];
  if (showTeacherPortal || activeRole === "teacher") derived.push("teacher");
  if (showAdminStudio || activeRole === "admin") derived.push("admin");
  return Array.from(new Set(derived));
}

export function NavLinks({
  navLinks,
  activeRole = "student",
  authorizedPortals,
  showTeacherPortal = false,
  showAdminStudio = false,
}: NavLinksProps) {
  const pathname = usePathname() ?? "";
  const [mobileOpen, setMobileOpen] = useState(false);

  const portals = buildPortalList(
    authorizedPortals,
    activeRole,
    showTeacherPortal,
    showAdminStudio,
  );
  const showPortalSwitcher = portals.length > 1;

  return (
    <>
      <nav
        aria-label="Primary navigation"
        className="hidden flex-wrap items-center gap-1.5 md:flex"
      >
        {navLinks.map((item) => {
          const active = isNavLinkActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-md px-2.5 py-1 text-sm font-medium transition ${
                active
                  ? "bg-slate-800 text-teal-300"
                  : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          );
        })}

        {showPortalSwitcher ? (
          <div
            role="group"
            aria-label="Portal switcher"
            className="ml-2 flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900/90 p-0.5"
          >
            {portals.map((portal) => {
              const isActivePortal = activeRole === portal;
              return (
                <Link
                  key={portal}
                  href={PORTAL_PATHS[portal]}
                  aria-current={isActivePortal ? "true" : undefined}
                  className={`rounded-md px-2 py-0.5 text-xs font-semibold transition ${
                    isActivePortal
                      ? portal === "admin"
                        ? "bg-indigo-600 text-white"
                        : portal === "teacher"
                          ? "bg-teal-500 text-slate-950"
                          : "bg-slate-700 text-white"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  {PORTAL_LABELS[portal]}
                </Link>
              );
            })}
          </div>
        ) : null}
      </nav>

      <div className="md:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen((prev) => !prev)}
          aria-expanded={mobileOpen}
          aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-slate-200 transition hover:border-slate-500 hover:text-white"
        >
          {mobileOpen ? (
            <X className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Menu className="h-4 w-4" aria-hidden="true" />
          )}
          <span>Menu</span>
        </button>
      </div>

      {mobileOpen ? (
        <nav
          aria-label="Mobile navigation"
          className="order-last mt-2 flex w-full flex-col gap-1 border-t border-slate-800 pt-3 md:hidden"
        >
          {showPortalSwitcher ? (
            <div
              role="group"
              aria-label="Mobile portal switcher"
              className="mb-2 flex flex-wrap items-center gap-1.5 border-b border-slate-800 pb-2.5"
            >
              <span className="mr-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Portal:
              </span>
              {portals.map((portal) => {
                const isActivePortal = activeRole === portal;
                return (
                  <Link
                    key={portal}
                    href={PORTAL_PATHS[portal]}
                    onClick={() => setMobileOpen(false)}
                    aria-current={isActivePortal ? "true" : undefined}
                    className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
                      isActivePortal
                        ? portal === "admin"
                          ? "bg-indigo-600 text-white"
                          : portal === "teacher"
                            ? "bg-teal-500 text-slate-950"
                            : "bg-slate-700 text-white"
                        : "border border-slate-700 text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    {PORTAL_LABELS[portal]}
                  </Link>
                );
              })}
            </div>
          ) : null}

          {navLinks.map((item) => {
            const active = isNavLinkActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                aria-current={active ? "page" : undefined}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-slate-800 text-teal-300"
                    : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      ) : null}
    </>
  );
}
