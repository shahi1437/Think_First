import { execFileSync, execSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "@playwright/test";

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const BACKEND_PYTHON = path.join(
  REPO_ROOT,
  "backend",
  ".venv",
  "Scripts",
  "python.exe",
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

const SCREENSHOT_DIR = process.env.CAPTURE_REDESIGN_SCREENSHOTS_DIR || "";

test.describe("Phase 11 Product Redesign & Special Learning Features E2E", () => {
  test("Verifies redesigned portals, Teacher Announcement -> Student Notification Center, Verified Learning Progress, and AI Debugging Timeline", async ({
    browser,
    request,
  }) => {
    test.setTimeout(180_000);

    const suffix = Date.now().toString(36);
    const teacherEmail = `p11-tch-${suffix}@thinkfirst.test`;
    const studentEmail = `p11-stu-${suffix}@thinkfirst.test`;
    const adminEmail = `p11-adm-${suffix}@thinkfirst.test`;
    const password = "Phase11Password123!";

    // Provision Teacher, Student, and Admin accounts via local Supabase Auth
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

    const teacherUserId = await createAccount(teacherEmail, "Prof. Redesign");
    await createAccount(studentEmail, "Student Redesign");
    await createAccount(adminEmail, "Admin Redesign");

    // Grant DB-backed teacher & admin roles cleanly
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

    // 1. Capture public Homepage & Student Login desktop + mobile views
    const pubCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const pubPage = await pubCtx.newPage();
    await pubPage.goto("/");
    await expect(
      pubPage.getByRole("heading", {
        name: /Master Python programming through practice, error diagnosis, and guided reasoning/i,
      }),
    ).toBeVisible();
    if (SCREENSHOT_DIR) {
      await pubPage.screenshot({
        path: path.join(SCREENSHOT_DIR, "after_homepage_1440px.png"),
        fullPage: true,
      });
      await pubPage.setViewportSize({ width: 390, height: 844 });
      await pubPage.screenshot({
        path: path.join(SCREENSHOT_DIR, "after_homepage_390px.png"),
        fullPage: false,
      });
      await pubPage.setViewportSize({ width: 1440, height: 900 });
      await pubPage.goto("/login/student");
      await pubPage.screenshot({
        path: path.join(SCREENSHOT_DIR, "after_login_student_1440px.png"),
        fullPage: false,
      });
    }
    await pubCtx.close();

    // 2. Teacher logs in, verifies redesigned dashboard, creates a class
    const teacherCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const teacherPage = await teacherCtx.newPage();
    await teacherPage.goto("/login");
    await teacherPage.getByLabel(/Email address/i).fill(teacherEmail);
    await teacherPage.getByLabel(/Password/i).fill(password);
    await teacherPage.getByRole("button", { name: /Sign in/i }).click();
    await teacherPage.waitForURL("**/teacher", { timeout: 25_000 });
    await expect(
      teacherPage.getByRole("heading", { name: /Welcome, Prof\. Redesign/i }),
    ).toBeVisible({ timeout: 20_000 });
    await expect(teacherPage.getByTestId("notification-bell-button")).toBeVisible();

    if (SCREENSHOT_DIR) {
      await teacherPage.screenshot({
        path: path.join(SCREENSHOT_DIR, "after_teacher_dashboard_1440px.png"),
        fullPage: true,
      });
    }

    await teacherPage.goto("/teacher/classes");
    const classCode = `RED-${suffix.slice(-4).toUpperCase()}`;
    await teacherPage.getByLabel(/Course Code/i).fill(classCode);
    await teacherPage.getByLabel(/Class Title/i).fill("CS201 Structured Debugging");
    await teacherPage.getByRole("button", { name: /Create Class/i }).click();
    await expect(teacherPage.getByText(classCode).first()).toBeVisible({
      timeout: 15_000,
    });
    await teacherPage
      .getByRole("link", { name: /Manage Class & Roster/i })
      .first()
      .click();
    await teacherPage.waitForURL("**/teacher/classes/**");
    const inviteCode = (
      (await teacherPage
        .getByTestId("invite-code-preview")
        .first()
        .textContent()) ?? ""
    ).trim();

    // 3. Student completes onboarding, joins class, verifies Verified Progress & Debugging Timeline
    const studentCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const studentPage = await studentCtx.newPage();
    await studentPage.goto("/login");
    await studentPage.getByLabel(/Email address/i).fill(studentEmail);
    await studentPage.getByLabel(/Password/i).fill(password);
    await studentPage.getByRole("button", { name: /Sign in/i }).click();
    await studentPage.waitForURL("**/student/onboarding", { timeout: 25_000 });
    await studentPage.getByLabel(/Full name/i).fill("Student Redesign");
    await studentPage
      .getByRole("button", {
        name: /Start My Learning Journey|Complete onboarding/i,
      })
      .click();
    await studentPage.waitForURL("**/student", { timeout: 25_000 });

    await expect(studentPage.getByTestId("continue-learning-card")).toBeVisible();
    await expect(studentPage.getByTestId("verified-progress-panel")).toBeVisible();
    await expect(studentPage.getByTestId("verified-achievements-group")).toBeVisible();
    await expect(studentPage.getByTestId("estimated-progress-group")).toBeVisible();
    await expect(studentPage.getByTestId("ai-debugging-timeline")).toBeVisible();

    // Student joins teacher's class using invite code
    await studentPage.goto("/student/classes");
    await studentPage.getByPlaceholder(/CM-/i).fill(inviteCode);
    await studentPage.getByRole("button", { name: /Join Class/i }).click();
    await expect(studentPage.getByText(classCode).first()).toBeVisible({
      timeout: 15_000,
    });

    // 4. Teacher posts a real Class Announcement -> Student receives it in Notification Center!
    await teacherPage.getByLabel(/^Title$/i).fill("Lab 1 Kickoff");
    await teacherPage
      .getByLabel(/^Message$/i)
      .fill("Please finish the loop debugging exercise before Friday.");
    await teacherPage.getByTestId("teacher-announcement-submit").click();
    await expect(
      teacherPage.getByTestId("teacher-announcement-success"),
    ).toContainText("1 active student(s)");
    await teacherCtx.close();

    // Student returns to /student and opens Notification Center
    await studentPage.goto("/student");
    await expect(
      studentPage.getByTestId("notification-unread-badge"),
    ).toBeVisible({ timeout: 15_000 });
    await studentPage.getByTestId("notification-bell-button").click();
    await expect(
      studentPage.getByTestId("notification-center-panel"),
    ).toBeVisible();
    await expect(studentPage.getByText(/Lab 1 Kickoff/i).first()).toBeVisible();

    if (SCREENSHOT_DIR) {
      await studentPage.screenshot({
        path: path.join(SCREENSHOT_DIR, "after_student_dashboard_1440px.png"),
        fullPage: false,
      });
    }

    await studentPage.getByTestId("notification-mark-all-read").click();
    await expect(
      studentPage.getByTestId("notification-unread-badge"),
    ).toHaveCount(0);
    await studentPage.getByRole("button", { name: "Close notifications" }).click();

    if (SCREENSHOT_DIR) {
      await studentPage
        .getByTestId("verified-progress-panel")
        .scrollIntoViewIfNeeded();
      await studentPage.screenshot({
        path: path.join(
          SCREENSHOT_DIR,
          "after_student_verified_progress_1440px.png",
        ),
        fullPage: false,
      });
    }

    // Check mobile layout + Student History AI Debugging Timeline
    if (SCREENSHOT_DIR) {
      await studentPage.setViewportSize({ width: 390, height: 844 });
      await studentPage.screenshot({
        path: path.join(SCREENSHOT_DIR, "after_student_dashboard_390px.png"),
        fullPage: false,
      });
      await studentPage.setViewportSize({ width: 1440, height: 900 });
    }
    await studentPage.goto("/student/history");
    await expect(studentPage.getByTestId("ai-debugging-timeline")).toBeVisible();
    if (SCREENSHOT_DIR) {
      await studentPage.screenshot({
        path: path.join(SCREENSHOT_DIR, "after_student_history_1440px.png"),
        fullPage: true,
      });
    }
    await studentCtx.close();

    // 5. Admin logs in and verifies redesigned Admin Control Center
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
      adminPage.getByText(/Curriculum & Assessment Control Center/i),
    ).toBeVisible();
    await expect(adminPage.getByTestId("notification-bell-button")).toBeVisible();
    if (SCREENSHOT_DIR) {
      await adminPage.screenshot({
        path: path.join(SCREENSHOT_DIR, "after_admin_dashboard_1440px.png"),
        fullPage: true,
      });
    }
    await adminCtx.close();
  });
});
