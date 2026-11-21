"use client";

import { GraduationCap, LogIn, Menu, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/#features", label: "Features" },
  { href: "/#how-it-works", label: "How It Works" },
  { href: "/#about", label: "About" },
];

export function PublicNavbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-[#0b1221]/95 text-white backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-teal-400 to-indigo-500 text-sm font-bold text-slate-950 shadow-sm">
            TF
          </span>
          <div className="leading-tight">
            <span className="block text-sm font-bold tracking-tight text-white sm:text-base">
              Think_First
            </span>
            <span className="block text-[11px] font-medium text-teal-300">
              CodeMentor AI
            </span>
          </div>
        </Link>

        <nav
          aria-label="Public navigation"
          className="hidden items-center gap-1 md:flex"
        >
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800/80 hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-2.5 md:flex">
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900/70 px-3.5 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-500 hover:bg-slate-800"
          >
            <LogIn className="h-4 w-4 text-teal-300" aria-hidden="true" />
            Login
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center gap-1.5 rounded-lg bg-teal-400 px-3.5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-300"
          >
            <GraduationCap className="h-4 w-4" aria-hidden="true" />
            Student Sign Up
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen((prev) => !prev)}
          aria-expanded={mobileOpen}
          aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-slate-500 md:hidden"
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
        <div className="border-t border-slate-800 bg-[#0b1221] px-4 py-3 md:hidden">
          <nav aria-label="Mobile public navigation" className="flex flex-col gap-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 hover:text-white"
              >
                {item.label}
              </Link>
            ))}
            <div className="mt-2 grid grid-cols-2 gap-2 border-t border-slate-800 pt-3">
              <Link
                href="/login"
                onClick={() => setMobileOpen(false)}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
              >
                <LogIn className="h-4 w-4 text-teal-300" aria-hidden="true" />
                Login
              </Link>
              <Link
                href="/register"
                onClick={() => setMobileOpen(false)}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-teal-400 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-teal-300"
              >
                Sign Up
              </Link>
            </div>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
