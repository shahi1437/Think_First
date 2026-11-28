import Link from "next/link";

export function PublicFooter() {
  return (
    <footer className="border-t border-slate-800 bg-[#0b1221] text-slate-300">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
        <div className="lg:col-span-2">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-teal-400 font-mono text-xs font-bold text-slate-950">
              TF
            </span>
            <div>
              <span className="text-base font-bold text-white">
                Think_First · CodeMentor AI
              </span>
            </div>
          </div>
          <p className="mt-3 text-sm font-medium text-teal-300">
            Think First. Code Better.
          </p>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-400">
            A structured multi-language programming and debugging platform
            (Python, JavaScript, C, C++, Java) designed for students,
            instructors, and academic programs.
          </p>
        </div>

        <div>
          <h3 className="text-xs font-semibold text-slate-300">
            Platform
          </h3>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <Link href="/" className="transition hover:text-white">
                Home
              </Link>
            </li>
            <li>
              <Link href="/#features" className="transition hover:text-white">
                Features
              </Link>
            </li>
            <li>
              <Link href="/#how-it-works" className="transition hover:text-white">
                How It Works
              </Link>
            </li>
            <li>
              <Link href="/#about" className="transition hover:text-white">
                About
              </Link>
            </li>
          </ul>
        </div>

        <div>
          <h3 className="text-xs font-semibold text-slate-300">
            Authorized Portals
          </h3>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <Link
                href="/login/student"
                className="transition hover:text-teal-300"
              >
                Student Login
              </Link>
            </li>
            <li>
              <Link
                href="/login/teacher"
                className="transition hover:text-teal-300"
              >
                Teacher Login
              </Link>
            </li>
            <li>
              <Link
                href="/login/admin"
                className="transition hover:text-teal-300"
              >
                Admin Login
              </Link>
            </li>
            <li>
              <Link href="/register" className="transition hover:text-teal-300">
                Create Student Account
              </Link>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-slate-800/80">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-5 text-xs text-slate-400 sm:px-6">
          <p>© {new Date().getUTCFullYear()} Think_First · CodeMentor AI.</p>
          <p>Python Programming · Error Diagnosis · Guided Learning</p>
        </div>
      </div>
    </footer>
  );
}
