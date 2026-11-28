import { execFileSync, execSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "@playwright/test";

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const BACKEND_PYTHON = path.join(
  REPO_ROOT,
  "backend",
  ".venv",
  ...(process.platform === "win32"
    ? ["Scripts", "python.exe"]
    : ["bin", "python"]),
);
const BOOTSTRAP_SCRIPT = path.join(
  REPO_ROOT,
  "backend",
  "scripts",
  "bootstrap_first_admin.py",
);
const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

test.describe("Phase 12 Remaining Features E2E Verification", () => {
  test("Verifies Smart Onboarding roadmap, 5-Question Personalized Hub, Adaptive Problem Bank, Workspace Code Diff, History Filters, Teacher Class Comparison + Student Drill-Down, and Admin Observability", async ({
    browser,
    request,
  }) => {
    test.setTimeout(180_000);

    const suffix = Date.now().toString(36);
    const teacherEmail = `p12-tch-${suffix}@thinkfirst.test`;
    const studentEmail = `p12-stu-${suffix}@thinkfirst.test`;
    const adminEmail = `p12-adm-${suffix}@thinkfirst.test`;
    const password = "Phase12Password123!";

    const createAccount = async (email: string, fullName: string) => {
      const res = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          "Content-Type": "application/json",
        },
        data: { email, password, data: { full_name: fullName } },
      });
      expect(res.ok()).toBeTruthy();
      return ((await res.json()) as { user: { id: string } }).user.id;
    };

    const teacherUserId = await createAccount(teacherEmail, "Prof. Phase12");
    await createAccount(studentEmail, "Student Phase12");
    await createAccount(adminEmail, "Admin Phase12");

    execSync(
      `docker exec supabase_db_think-first-codementor psql -U postgres -d postgres -c "INSERT INTO public.user_roles (user_id, role, granted_by) VALUES ('${teacherUserId}', 'teacher', '${teacherUserId}') ON CONFLICT DO NOTHING;"`,
    );
    execFileSync(
      BACKEND_PYTHON,
      [
        BOOTSTRAP_SCRIPT,
        "--email",
        adminEmail,
        "--allow-additional",
        "--environment",
        "local",
        "--confirm",
      ],
      { cwd: path.join(REPO_ROOT, "backend"), stdio: "pipe" },
    );

    // 1. Teacher creates a class so we can verify Class Performance Comparison & Student Drill-Down
    const teacherCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const teacherPage = await teacherCtx.newPage();
    await teacherPage.goto("/login");
    await teacherPage.getByLabel(/Email address/i).fill(teacherEmail);
    await teacherPage.getByLabel(/Password/i).fill(password);
    await teacherPage.getByRole("button", { name: /Sign in/i }).click();
    await teacherPage.waitForURL("**/teacher", { timeout: 25_000 });

    await teacherPage.goto("/teacher/classes");
    const classCode = `P12-${suffix.slice(-4).toUpperCase()}`;
    await teacherPage.getByLabel(/Course Code/i).fill(classCode);
    await teacherPage
      .getByLabel(/Class Title/i)
      .fill("CS102 Adaptive Learning Lab");
    await teacherPage.getByRole("button", { name: /Create Class/i }).click();
    await expect(teacherPage.getByText(classCode).first()).toBeVisible({
      timeout: 15_000,
    });
    await teacherPage
      .getByRole("link", { name: /Manage Class & Roster/i })
      .first()
      .click();
    await teacherPage.waitForURL("**/teacher/classes/**");
    const classUrl = teacherPage.url();
    const inviteCode = (
      (await teacherPage
        .getByTestId("invite-code-preview")
        .first()
        .textContent()) ?? ""
    ).trim();

    // 2. Student logs in -> verifies Smart Onboarding Roadmap Preview -> completes onboarding
    const studentCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const studentPage = await studentCtx.newPage();
    await studentPage.goto("/login");
    await studentPage.getByLabel(/Email address/i).fill(studentEmail);
    await studentPage.getByLabel(/Password/i).fill(password);
    await studentPage.getByRole("button", { name: /Sign in/i }).click();
    await studentPage.waitForURL("**/student/onboarding", { timeout: 25_000 });

    const roadmap = studentPage.getByTestId("onboarding-roadmap-preview");
    await expect(roadmap).toBeVisible();
    await expect(roadmap).toContainText("Starting Difficulty:");

    await studentPage.getByLabel(/Full name/i).fill("Student Phase12");
    await studentPage
      .getByRole("button", {
        name: /Start My Learning Journey|Complete onboarding/i,
      })
      .click();
    await studentPage.waitForURL(
      (url) =>
        url.pathname.startsWith("/student") &&
        !url.pathname.includes("/onboarding"),
      { timeout: 25_000 },
    );

    // 3. Student Dashboard: Unified 5-Question Personalized Learning Hub
    await studentPage.goto("/student");
    const hub = studentPage.getByTestId("personalized-learning-hub");
    await expect(hub).toBeVisible({ timeout: 20_000 });
    await expect(studentPage.getByTestId("q-next")).toBeVisible();
    await expect(studentPage.getByTestId("q-weak")).toBeVisible();
    await expect(studentPage.getByTestId("q-problem")).toBeVisible();
    await expect(studentPage.getByTestId("q-progress")).toBeVisible();
    await expect(studentPage.getByTestId("q-repeat")).toBeVisible();

    // 4. Adaptive Problem Bank: Topic, Completion Status, and Recommended toggles
    await studentPage.goto("/student/problems");
    await expect(studentPage.getByTestId("problem-topic-filter")).toBeVisible({
      timeout: 20_000,
    });
    await expect(studentPage.getByTestId("problem-status-filter")).toBeVisible();
    const recBtn = studentPage.getByTestId("problem-recommended-toggle");
    await expect(recBtn).toBeVisible();
    await recBtn.click();
    await expect(recBtn).toHaveAttribute("aria-pressed", "true");
    await recBtn.click();

    // 5. Coding Workspace: Open first problem -> Revisions tab -> Diff vs Starter Code
    const firstProblemLink = studentPage
      .locator('a[href^="/student/problems/"]')
      .first();
    await expect(firstProblemLink).toBeVisible({ timeout: 15_000 });
    await firstProblemLink.click();
    await studentPage.waitForURL("**/student/problems/**", { timeout: 25_000 });
    await studentPage
      .getByRole("button", { name: /^Revisions/i })
      .click();
    await studentPage
      .getByRole("button", { name: /Diff vs Starter Code/i })
      .click();
    await expect(
      studentPage.getByTestId("code-attempt-diff-viewer"),
    ).toBeVisible();

    // 6. Student Learning History: Language, Status & Date filters
    await studentPage.goto("/student/history");
    await expect(
      studentPage.getByTestId("history-language-filter"),
    ).toBeVisible({ timeout: 20_000 });
    await expect(studentPage.getByTestId("history-status-filter")).toBeVisible();
    await expect(studentPage.getByTestId("history-date-from")).toBeVisible();
    await expect(studentPage.getByTestId("history-date-to")).toBeVisible();

    // 7. Student joins Teacher's class so Teacher can run Student Drill-Down & Class Comparison
    await studentPage.goto("/student/classes");
    await studentPage.getByPlaceholder(/CM-/i).fill(inviteCode);
    await studentPage.getByRole("button", { name: /Join Class/i }).click();
    await expect(studentPage.getByText(classCode).first()).toBeVisible({
      timeout: 15_000,
    });
    await studentCtx.close();

    // 8. Teacher verifies Class Performance Comparison on /teacher & Student Drill-Down on /teacher/classes/<id>
    await teacherPage.goto("/teacher");
    const comparison = teacherPage.getByTestId("teacher-class-comparison");
    await expect(comparison).toBeVisible({ timeout: 20_000 });
    await expect(comparison).toContainText(classCode);

    await teacherPage.goto(classUrl);
    await expect(teacherPage.getByText("Student Phase12")).toBeVisible({
      timeout: 15_000,
    });
    await teacherPage
      .getByRole("button", { name: /Inspect performance for Student Phase12/i })
      .click();
    const drilldown = teacherPage.getByTestId("teacher-student-drilldown");
    await expect(drilldown).toBeVisible({ timeout: 15_000 });
    await expect(drilldown).toContainText("Student Phase12 — Student Drill-Down");
    await teacherCtx.close();

    // 9. Admin verifies Platform Observability Execution Failure & User Activity Stats
    const adminCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const adminPage = await adminCtx.newPage();
    await adminPage.goto("/login");
    await adminPage.getByLabel(/Email address/i).fill(adminEmail);
    await adminPage.getByLabel(/Password/i).fill(password);
    await adminPage.getByRole("button", { name: /Sign in/i }).click();
    await adminPage.waitForURL("**/admin", { timeout: 25_000 });
    await expect(
      adminPage.getByTestId("admin-observability-stats"),
    ).toBeVisible({ timeout: 20_000 });
    await adminCtx.close();
  });
});
