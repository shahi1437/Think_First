import {
  ArrowRight,
  BookOpen,
  Bug,
  CheckCircle2,
  ClipboardList,
  Code2,
  Compass,
  GraduationCap,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  TrendingUp,
  Users,
} from "lucide-react";
import Link from "next/link";
import { PublicFooter } from "@/components/public-footer";
import { PublicNavbar } from "@/components/public-navbar";

const portalCards = [
  {
    role: "STUDENT LOGIN",
    href: "/login/student",
    icon: GraduationCap,
    description:
      "Access Python lessons, practice problems, class assignments, and your learning progress.",
    buttonStyle:
      "bg-teal-400 text-slate-950 hover:bg-teal-300 focus-visible:outline-teal-300",
    cardBorder: "border-teal-400/30 bg-slate-900/80 hover:border-teal-300/60",
    iconBg: "bg-teal-400/15 text-teal-300",
  },
  {
    role: "TEACHER LOGIN",
    href: "/login/teacher",
    icon: Users,
    description:
      "Manage assigned classes, publish coding assignments, review student work, and grade submissions.",
    buttonStyle:
      "bg-white text-slate-950 hover:bg-slate-100 focus-visible:outline-white",
    cardBorder: "border-slate-700 bg-slate-900/80 hover:border-slate-500",
    iconBg: "bg-indigo-400/15 text-indigo-300",
  },
  {
    role: "ADMIN LOGIN",
    href: "/login/admin",
    icon: ShieldCheck,
    description:
      "Oversee users, role authorizations, curriculum standards, courses, and platform operations.",
    buttonStyle:
      "border border-slate-500 bg-slate-800 text-white hover:bg-slate-700 focus-visible:outline-slate-400",
    cardBorder: "border-slate-700 bg-slate-900/80 hover:border-slate-500",
    iconBg: "bg-slate-700/80 text-slate-200",
  },
];

const features = [
  {
    icon: Code2,
    title: "Learn Python",
    description:
      "Start from core fundamentals or build toward intermediate problem solving with structured Python study tracks.",
  },
  {
    icon: BookOpen,
    title: "Interactive Lessons",
    description:
      "Study clear programming concepts with runnable examples and guided hands-on exercises.",
  },
  {
    icon: TerminalSquare,
    title: "Practice Problems",
    description:
      "Write, run, and test real Python solutions against verified test cases to strengthen coding fluency.",
  },
  {
    icon: ClipboardList,
    title: "Assignments & Classes",
    description:
      "Join instructor-led classes, submit coursework before deadlines, and review written teacher feedback.",
  },
  {
    icon: Bug,
    title: "Error Diagnosis",
    description:
      "Identify syntax, runtime, and logic mistakes clearly so you understand why code fails and how to fix it.",
  },
  {
    icon: TrendingUp,
    title: "Learning Progress",
    description:
      "Follow personalized daily study plans, track skill growth over time, and revisit concepts to build retention.",
  },
  {
    icon: Sparkles,
    title: "AI Learning Assistance",
    description:
      "Receive step-by-step guided hints when enabled, helping you reason through bugs instead of skipping ahead.",
  },
];

const steps = [
  {
    step: "01",
    title: "Create Your Student Account",
    description:
      "Register with your email, verify your account, and set your preferred pace and learning goals.",
  },
  {
    step: "02",
    title: "Find Your Starting Level",
    description:
      "Begin with structured Python lessons or take a quick diagnostic check to highlight where to focus first.",
  },
  {
    step: "03",
    title: "Practice & Diagnose Mistakes",
    description:
      "Solve coding problems, inspect test results, and use targeted error diagnosis and hints to improve.",
  },
  {
    step: "04",
    title: "Grow Across Classes & Skills",
    description:
      "Complete assignments, track steady progress across programming skills, and verify long-term retention.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <PublicNavbar />

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-[#0b1221] text-white">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(45,212,191,0.16),_transparent_50%),radial-gradient(ellipse_at_bottom_left,_rgba(79,70,229,0.18),_transparent_55%)]"
        />

        <div className="relative mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-20 lg:py-24">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-teal-400/30 bg-teal-500/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-teal-300">
              Think First. Code Better.
            </span>

            <h1 className="mt-5 text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-[52px] lg:leading-[1.1]">
              Master Python programming through practice, error diagnosis, and
              guided reasoning.
            </h1>

            <p className="mt-5 max-w-2xl text-base leading-relaxed text-slate-300 sm:text-[18px]">
              Think_First (CodeMentor AI) helps university and school learners
              build real coding habits—combining structured lessons, hands-on
              practice problems, mistake diagnosis, and classroom assignments in
              one focused workspace.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3.5">
              <Link
                href="/register"
                prefetch={true}
                className="inline-flex items-center gap-2 rounded-xl bg-teal-400 px-6 py-3.5 text-[15px] font-semibold text-slate-950 shadow-sm transition hover:bg-teal-300 sm:text-base"
              >
                <GraduationCap className="h-4 w-4" aria-hidden="true" />
                Create Student Account
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-600 bg-slate-900/60 px-6 py-3.5 text-[15px] font-semibold text-slate-100 transition hover:border-slate-400 hover:bg-slate-800 sm:text-base"
              >
                <Compass className="h-4 w-4 text-teal-300" aria-hidden="true" />
                See How It Works
              </a>
            </div>
          </div>

          {/* Three Dedicated Role Login Portals */}
          <div id="portals" className="mt-14">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Choose Your Authorized Portal
            </p>
            <div className="mt-3.5 grid gap-5 md:grid-cols-3">
              {portalCards.map((portal) => {
                const Icon = portal.icon;
                return (
                  <div
                    key={portal.role}
                    className={`flex flex-col justify-between rounded-2xl border p-6 transition duration-200 ${portal.cardBorder}`}
                  >
                    <div>
                      <div className="flex items-center gap-3">
                        <div
                          className={`flex h-11 w-11 items-center justify-center rounded-xl ${portal.iconBg}`}
                        >
                          <Icon className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <h2 className="text-base font-bold tracking-wide text-white">
                          {portal.role}
                        </h2>
                      </div>
                      <p className="mt-3.5 text-[15px] leading-relaxed text-slate-300">
                        {portal.description}
                      </p>
                    </div>

                    <Link
                      href={portal.href}
                      prefetch={true}
                      className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-[15px] font-semibold transition ${portal.buttonStyle}`}
                    >
                      <Icon className="h-4 w-4" aria-hidden="true" />
                      <span>{portal.role}</span>
                      <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </Link>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <main className="flex-1">
        {/* Features Section */}
        <section
          id="features"
          aria-labelledby="features-heading"
          className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20"
        >
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
              Platform Capabilities
            </p>
            <h2
              id="features-heading"
              className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl"
            >
              Everything learners and instructors need for coding mastery
            </h2>
            <p className="mt-3 text-base text-slate-600">
              Focused tools that guide learners from understanding syntax to
              diagnosing bugs and completing real coursework.
            </p>
          </div>

          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <article
                  key={feature.title}
                  className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900 text-teal-300 transition group-hover:bg-teal-600 group-hover:text-white">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 text-lg font-bold text-slate-900 sm:text-[20px]">
                    {feature.title}
                  </h3>
                  <p className="mt-2 text-base leading-relaxed text-slate-600">
                    {feature.description}
                  </p>
                </article>
              );
            })}
          </div>
        </section>

        {/* How It Works Section */}
        <section
          id="how-it-works"
          aria-labelledby="how-it-works-heading"
          className="border-y border-slate-200 bg-white"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
                How It Works
              </p>
              <h2
                id="how-it-works-heading"
                className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl"
              >
                A clear four-step path from first line to confident coding
              </h2>
            </div>

            <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {steps.map((item) => (
                <div
                  key={item.step}
                  className="relative rounded-2xl border border-slate-200 bg-slate-50/70 p-6"
                >
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[#0b1221] text-xs font-bold text-teal-300">
                    {item.step}
                  </span>
                  <h3 className="mt-4 text-base font-bold text-slate-900">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* About & Academic Role Separation Section */}
        <section
          id="about"
          aria-labelledby="about-heading"
          className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20"
        >
          <div className="grid items-center gap-8 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm lg:grid-cols-12 lg:p-10">
            <div className="lg:col-span-7">
              <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
                About Think_First
              </p>
              <h2
                id="about-heading"
                className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl"
              >
                Built for deep comprehension, not shortcut copying
              </h2>
              <p className="mt-4 text-base leading-relaxed text-slate-600">
                Think_First / CodeMentor AI encourages learners to reason
                through logic, read error diagnostics carefully, and verify
                solutions independently. With dedicated workspaces for Students,
                Teachers, and Administrators, academic teams keep learning,
                instruction, and oversight cleanly separated.
              </p>
            </div>

            <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-6 lg:col-span-5">
              <h3 className="text-sm font-bold text-slate-900">
                Role-Separated Experience
              </h3>
              <ul className="space-y-2.5 text-sm text-slate-700">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0 text-teal-600"
                    aria-hidden="true"
                  />
                  <span>
                    <strong>Students</strong> learn Python, practice debugging,
                    and submit class assignments.
                  </span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600"
                    aria-hidden="true"
                  />
                  <span>
                    <strong>Teachers</strong> create classes, assign problems,
                    and review student progress.
                  </span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0 text-slate-700"
                    aria-hidden="true"
                  />
                  <span>
                    <strong>Administrators</strong> govern user access, courses,
                    and curriculum quality.
                  </span>
                </li>
              </ul>

              <div className="pt-2">
                <Link
                  href="/register"
                  className="inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:text-teal-800 hover:underline"
                >
                  Start as a Student
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
