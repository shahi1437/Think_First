import Link from "next/link";
import type { ReactNode } from "react";
import { AuthSessionSync } from "@/components/auth-session-sync";
import { LogoutButton } from "@/components/logout-button";
import { NavLinks } from "@/components/nav-links";
import { NotificationCenter } from "@/components/notification-center";
import { getAuthorizedPortals, PORTAL_LABELS } from "@/lib/auth/roles";
import type { RoleName, UserMeResponse } from "@/types/identity";

interface NavLink {
  href: string;
  label: string;
}

interface AppShellProps {
  user: UserMeResponse;
  accessToken?: string;
  activeRole: RoleName;
  navLinks: NavLink[];
  children: ReactNode;
}

export function AppShell({
  user,
  accessToken,
  activeRole,
  navLinks,
  children,
}: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden bg-[#f7f8fa] text-slate-900">
      <AuthSessionSync activeRole={activeRole} />
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 text-slate-900 backdrop-blur">
        <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[#0b1221] font-mono text-xs font-bold tracking-tight text-teal-300 ring-1 ring-slate-900/10">
              TF
            </span>
            <div className="leading-tight">
              <span className="block text-sm font-bold tracking-tight text-slate-950 sm:text-base">
                Think_First
              </span>
              <span className="hidden text-[11px] font-medium text-slate-500 sm:block">
                CodeMentor AI · {PORTAL_LABELS[activeRole]} Portal
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-2.5 sm:gap-3">
            <span className="hidden rounded-md border border-teal-200 bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-800 md:inline-flex">
              {PORTAL_LABELS[activeRole]} Portal
            </span>
            <NotificationCenter
              accessToken={accessToken}
              activeRole={activeRole}
            />
            <span className="hidden max-w-[180px] truncate text-sm font-medium text-slate-700 sm:inline">
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
