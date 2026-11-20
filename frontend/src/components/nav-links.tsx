"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

export interface AppNavLink {
  href: string;
  label: string;
}

interface NavLinksProps {
  navLinks: AppNavLink[];
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

export function NavLinks({
  navLinks,
  showTeacherPortal = false,
  showAdminStudio = false,
}: NavLinksProps) {
  const pathname = usePathname() ?? "";
  const [mobileOpen, setMobileOpen] = useState(false);

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
        {showTeacherPortal ? (
          <Link
            href="/teacher"
            className="rounded-md px-2.5 py-1 text-sm font-medium text-teal-300 transition hover:bg-slate-800/70 hover:text-teal-200"
          >
            Teacher Portal
          </Link>
        ) : null}
        {showAdminStudio ? (
          <Link
            href="/admin"
            className="rounded-md px-2.5 py-1 text-sm font-medium text-indigo-300 transition hover:bg-slate-800/70 hover:text-indigo-200"
          >
            Admin Studio
          </Link>
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
          {showTeacherPortal ? (
            <Link
              href="/teacher"
              onClick={() => setMobileOpen(false)}
              className="rounded-lg px-3 py-2 text-sm font-medium text-teal-300 transition hover:bg-slate-800/70"
            >
              Teacher Portal
            </Link>
          ) : null}
          {showAdminStudio ? (
            <Link
              href="/admin"
              onClick={() => setMobileOpen(false)}
              className="rounded-lg px-3 py-2 text-sm font-medium text-indigo-300 transition hover:bg-slate-800/70"
            >
              Admin Studio
            </Link>
          ) : null}
        </nav>
      ) : null}
    </>
  );
}
