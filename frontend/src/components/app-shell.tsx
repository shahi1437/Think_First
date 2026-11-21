import Link from "next/link";
import type { ReactNode } from "react";
import { LogoutButton } from "@/components/logout-button";
import { NavLinks } from "@/components/nav-links";
import { getAuthorizedPortals, PORTAL_LABELS } from "@/lib/auth/roles";
import type { RoleName, UserMeResponse } from "@/types/identity";

interface NavLink {
  href: string;
  label: string;
}

interface AppShellProps {
  user: UserMeResponse;
  activeRole: RoleName;
  navLinks: NavLink[];
  children: ReactNode;
}

export function AppShell({
  user,
  activeRole,
  navLinks,
  children,
}: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-800/90 bg-[#0b1221] text-white shadow-sm">
        <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-teal-400 to-indigo-500 text-sm font-bold text-slate-950 shadow-sm">
              TF
            </span>
            <div className="leading-tight">
              <span className="block text-base font-bold tracking-tight text-white">
                Think_First
              </span>
              <span className="hidden text-[11px] font-medium text-teal-300 sm:block">
                Think First. Code Better.
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <span className="rounded-full border border-teal-400/30 bg-teal-500/15 px-3 py-1 text-xs font-semibold text-teal-200">
              {PORTAL_LABELS[activeRole]} Portal
            </span>
            <span className="hidden max-w-[200px] truncate text-sm font-medium text-slate-200 sm:inline">
              {user.full_name || user.email}
            </span>
            <LogoutButton />
          </div>
        </div>
      </header>

      <div className="flex flex-1 flex-col md:flex-row">
        <NavLinks
          layout="sidebar"
          navLinks={navLinks}
          activeRole={activeRole}
          authorizedPortals={getAuthorizedPortals(user.roles)}
        />

        <main className="min-w-0 flex-1">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
