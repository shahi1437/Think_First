"use client";

import {
  BookOpen,
  Calendar,
  ClipboardCheck,
  ClipboardList,
  Code2,
  Dna,
  FileCheck2,
  History,
  Layers,
  LayoutDashboard,
  Loader2,
  Menu,
  RotateCcw,
  Settings,
  ShieldCheck,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
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
  layout?: "topbar" | "sidebar";
}

const ROOT_PORTAL_PATHS = new Set(["/student", "/teacher", "/admin"]);

function getNavIcon(href: string): LucideIcon {
  if (ROOT_PORTAL_PATHS.has(href)) return LayoutDashboard;
  if (href.includes("/classes")) return Users;
  if (href.includes("/assignments")) return ClipboardList;
  if (href.includes("/daily-plan")) return Calendar;
  if (href.includes("/lessons") || href.includes("/curriculum")) return BookOpen;
  if (href.includes("/diagnostic")) return ClipboardCheck;
  if (href.includes("/problems")) return Code2;
  if (href.includes("/dna")) return Dna;
  if (href.includes("/retention")) return RotateCcw;
  if (href.includes("/history")) return History;
  if (href.includes("/settings")) return Settings;
  if (href.includes("/audit")) return ShieldCheck;
  if (href.includes("/review")) return FileCheck2;
  return Layers;
}

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
  layout = "topbar",
}: NavLinksProps) {
  const pathname = usePathname() ?? "";
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pendingNav, setPendingNav] = useState<{
    from: string;
    to: string;
  } | null>(null);
  const pendingHref =
    pendingNav && pendingNav.from === pathname ? pendingNav.to : null;

  const portals = buildPortalList(
    authorizedPortals,
    activeRole,
    showTeacherPortal,
    showAdminStudio,
  );
  const showPortalSwitcher = portals.length > 1;

  function handleNavClick(href: string) {
    if (!isNavLinkActive(pathname, href)) {
      setPendingNav({ from: pathname, to: href });
    }
    setMobileOpen(false);
  }

  if (layout === "sidebar") {
    return (
      <>
        {/* Desktop Sidebar Navigation */}
        <div className="hidden md:flex md:w-64 md:shrink-0 md:flex-col md:border-r md:border-slate-200 md:bg-white">
          <div className="sticky top-16 flex max-h-[calc(100vh-4rem)] flex-col overflow-y-auto px-3.5 py-5">
            {showPortalSwitcher ? (
              <div className="mb-5">
                <p className="mb-2 px-2 text-xs font-medium text-slate-500">
                  Authorized Portals
                </p>
                <div
                  role="group"
                  aria-label="Portal switcher"
                  className="grid grid-cols-3 gap-1 rounded-lg border border-slate-200 bg-slate-100/80 p-1"
                >
                  {portals.map((portal) => {
                    const isActivePortal = activeRole === portal;
                    return (
                      <Link
                        key={portal}
                        href={PORTAL_PATHS[portal]}
                        onClick={() => handleNavClick(PORTAL_PATHS[portal])}
                        aria-current={isActivePortal ? "true" : undefined}
                        className={`rounded-md px-2 py-1.5 text-center text-xs font-semibold transition-colors ${
                          isActivePortal
                            ? portal === "admin"
                              ? "bg-slate-900 text-white shadow-xs"
                              : portal === "teacher"
                                ? "bg-teal-700 text-white shadow-xs"
                                : "bg-[#0b1221] text-white shadow-xs"
                            : "text-slate-600 hover:bg-white hover:text-slate-900"
                        }`}
                      >
                        {PORTAL_LABELS[portal]}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ) : null}

            <p className="mb-2 px-2 text-xs font-medium text-slate-500">
              {PORTAL_LABELS[activeRole]} Workspace
            </p>
            <nav
              aria-label="Primary navigation"
              className="flex flex-col gap-0.5"
            >
              {navLinks.map((item) => {
                const active = isNavLinkActive(pathname, item.href);
                const isPending = pendingHref === item.href && !active;
                const Icon = getNavIcon(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => handleNavClick(item.href)}
                    aria-current={active ? "page" : undefined}
                    aria-busy={isPending || undefined}
                    className={`group flex items-center justify-between gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      active
                        ? "bg-teal-50/90 text-teal-950 ring-1 ring-inset ring-teal-200"
                        : isPending
                          ? "bg-slate-100 text-slate-900"
                          : "text-slate-700 hover:bg-slate-100/80 hover:text-slate-950"
                    }`}
                  >
                    <span className="flex items-center gap-2.5">
                      <Icon
                        className={`h-4 w-4 shrink-0 transition-colors ${
                          active
                            ? "text-teal-700"
                            : isPending
                              ? "text-teal-700"
                              : "text-slate-400 group-hover:text-slate-700"
                        }`}
                        aria-hidden="true"
                      />
                      <span>{item.label}</span>
                    </span>
                    {isPending ? (
                      <Loader2
                        className="h-3.5 w-3.5 animate-spin text-teal-700"
                        aria-hidden="true"
                      />
                    ) : null}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Mobile Compact Bar & Collapsible Drawer */}
        <div className="relative border-b border-slate-200 bg-white px-4 py-2.5 md:hidden">
          {pendingHref ? (
            <div
              aria-hidden="true"
              className="absolute inset-x-0 top-0 h-0.5 bg-teal-600"
            />
          ) : null}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold capitalize text-slate-700">
                {PORTAL_LABELS[activeRole]} Navigation
              </span>
              {pendingHref ? (
                <span
                  role="status"
                  className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-semibold text-teal-800"
                >
                  <Loader2
                    className="h-3 w-3 animate-spin text-teal-600"
                    aria-hidden="true"
                  />
                  <span>Loading…</span>
                </span>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => setMobileOpen((prev) => !prev)}
              aria-expanded={mobileOpen}
              aria-label={
                mobileOpen ? "Close navigation menu" : "Open navigation menu"
              }
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-slate-50 px-3 py-1.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-100"
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
              className="tf-drawer-enter mt-3 flex flex-col gap-1 border-t border-slate-200 pt-3"
            >
              {showPortalSwitcher ? (
                <div
                  role="group"
                  aria-label="Mobile portal switcher"
                  className="mb-2 flex flex-wrap items-center gap-1.5 border-b border-slate-200 pb-3"
                >
                  <span className="mr-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Portal:
                  </span>
                  {portals.map((portal) => {
                    const isActivePortal = activeRole === portal;
                    return (
                      <Link
                        key={portal}
                        href={PORTAL_PATHS[portal]}
                        onClick={() => handleNavClick(PORTAL_PATHS[portal])}
                        aria-current={isActivePortal ? "true" : undefined}
                        className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                          isActivePortal
                            ? portal === "admin"
                              ? "bg-indigo-600 text-white"
                              : portal === "teacher"
                                ? "bg-teal-600 text-white"
                                : "bg-[#0b1221] text-white"
                            : "border border-slate-300 text-slate-700 hover:bg-slate-100"
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
                const isPending = pendingHref === item.href && !active;
                const Icon = getNavIcon(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => handleNavClick(item.href)}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center justify-between gap-2.5 rounded-xl px-3.5 py-2.5 text-[15px] font-medium transition ${
                      active
                        ? "bg-[#0b1221] text-white"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    <span className="flex items-center gap-3">
                      <Icon
                        className={`h-4 w-4 ${active ? "text-teal-300" : "text-slate-400"}`}
                        aria-hidden="true"
                      />
                      <span>{item.label}</span>
                    </span>
                    {isPending ? (
                      <Loader2
                        className="h-4 w-4 animate-spin text-teal-600"
                        aria-hidden="true"
                      />
                    ) : null}
                  </Link>
                );
              })}
            </nav>
          ) : null}
        </div>
      </>
    );
  }

  return (
    <>
      <nav
        aria-label="Primary navigation"
        className="hidden flex-wrap items-center gap-1.5 md:flex"
      >
        {navLinks.map((item) => {
          const active = isNavLinkActive(pathname, item.href);
          const isPending = pendingHref === item.href && !active;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => handleNavClick(item.href)}
              aria-current={active ? "page" : undefined}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                active
                  ? "bg-slate-800 text-teal-300"
                  : isPending
                    ? "bg-slate-800/80 text-white"
                    : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
              }`}
            >
              <span>{item.label}</span>
              {isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : null}
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
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
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
          aria-label={
            mobileOpen ? "Close navigation menu" : "Open navigation menu"
          }
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
                onClick={() => handleNavClick(item.href)}
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
