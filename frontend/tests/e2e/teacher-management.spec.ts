import { execFileSync } from "node:child_process";
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

test.describe("Admin Teacher Management & Verified Invitation Workflow", () => {
  test("Admin promotes existing account (Case A), invites new Teacher & completes verified acceptance (Case B), enforces strict role isolation, and revokes Teacher access", async ({
    browser,
    request,
  }) => {
    test.setTimeout(240_000);

    const suffix = Date.now().toString(36);
    const adminEmail = `tm-adm-${suffix}@thinkfirst.test`;
    const existingCandidateEmail = `tm-existing-${suffix}@thinkfirst.test`;
    const invitedTeacherEmail = `tm-invited-${suffix}@thinkfirst.test`;
    const password = "TeacherMgmtPass123!";

    // Provision Admin + Existing Student account (invitedTeacherEmail is NOT registered yet!)
    for (const [email, name] of [
      [adminEmail, "TM Admin"],
      [existingCandidateEmail, "Dr. Existing Candidate"],
    ] as const) {
      const signup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          "Content-Type": "application/json",
        },
        data: { email, password, data: { full_name: name } },
      });
      expect(signup.ok()).toBeTruthy();
    }

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

    const adminCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const adminPage = await adminCtx.newPage();

    // 1. Admin signs into /admin and sees TEACHER MANAGEMENT section
    await adminPage.goto("/login/admin");
    await adminPage.getByLabel(/Email address/i).fill(adminEmail);
    await adminPage.getByLabel(/Password/i).fill(password);
    await adminPage.getByRole("button", { name: /Sign in/i }).click();
    await adminPage.waitForURL((url) => url.pathname === "/admin", {
      timeout: 25_000,
    });
    await expect(
      adminPage.getByRole("heading", { name: "TEACHER MANAGEMENT" }),
    ).toBeVisible();

    // 2. CASE A: Lookup existing account -> Confirm & Grant Teacher Role
    await adminPage
      .getByLabel(/Teacher email address/i)
      .fill(existingCandidateEmail);
    await adminPage
      .getByRole("button", { name: /Check Email Status/i })
      .click();
    await expect(adminPage.getByTestId("teacher-lookup-result")).toContainText(
      /existing user not teacher/i,
    );
    await adminPage
      .getByRole("button", { name: /Confirm & Grant Teacher Role/i })
      .click();
    await expect(
      adminPage.getByTestId(`active-teacher-row-${existingCandidateEmail}`),
    ).toBeVisible({ timeout: 15_000 });

    // 3. CASE B: Invite brand-new Teacher email -> inspect Pending / Delivery Blocked + accept link
    await adminPage
      .getByLabel(/Teacher email address/i)
      .fill(invitedTeacherEmail);
    await adminPage
      .getByLabel(/Instructor name/i)
      .fill("Dr. Invited Instructor");
    await adminPage
      .getByRole("button", { name: /Invite New Teacher/i })
      .click();

    const invRow = adminPage.getByTestId(
      `teacher-invitation-row-${invitedTeacherEmail}`,
    );
    await expect(invRow).toBeVisible({ timeout: 15_000 });
    await expect(invRow).toContainText(/Pending \/ Delivery Blocked/i);

    const acceptPath = (
      await adminPage.getByTestId("teacher-invite-accept-link").textContent()
    )?.trim();
    expect(acceptPath).toMatch(/^\/accept-teacher-invite\?token=tfi_/);

    // 4. Invited Teacher registers their own account, opens the invitation link, and activates Teacher access
    const invitedSignup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email: invitedTeacherEmail,
        password,
        data: { full_name: "Dr. Invited Instructor" },
      },
    });
    expect(invitedSignup.ok()).toBeTruthy();

    const teacherCtx = await browser.newContext({
      viewport: { width: 1280, height: 800 },
    });
    const teacherPage = await teacherCtx.newPage();

    await teacherPage.goto("/login");
    await teacherPage.getByLabel(/Email address/i).fill(invitedTeacherEmail);
    await teacherPage.getByLabel(/Password/i).fill(password);
    await teacherPage.getByRole("button", { name: /Sign in/i }).click();
    await teacherPage.waitForURL("**/student**", { timeout: 25_000 });

    await teacherPage.goto(acceptPath!);
    await expect(
      teacherPage.getByText(/Verified Teacher Invitation/i),
    ).toBeVisible({ timeout: 15_000 });
    await teacherPage
      .getByRole("button", {
        name: /Accept Invitation & Activate Teacher Role/i,
      })
      .click();
    await expect(
      teacherPage.getByText(/Teacher access activated/i),
    ).toBeVisible({ timeout: 15_000 });

    // 5. Activated Teacher opens Teacher Dashboard (/teacher) and is blocked from /admin
    await teacherPage
      .getByRole("link", { name: /Open Teacher Dashboard/i })
      .click();
    await teacherPage.waitForURL((url) => url.pathname === "/teacher", {
      timeout: 20_000,
    });
    await expect(
      teacherPage.getByRole("heading", { name: /Welcome,/i }),
    ).toBeVisible();

    await teacherPage.goto("/admin");
    await teacherPage.waitForURL("**/teacher?error=forbidden", {
      timeout: 20_000,
    });
    await teacherCtx.close();

    // 6. Admin refreshes & revokes Teacher access from existingCandidateEmail
    await adminPage.reload();
    const existingRow = adminPage.getByTestId(
      `active-teacher-row-${existingCandidateEmail}`,
    );
    await expect(existingRow).toBeVisible({ timeout: 15_000 });
    await existingRow
      .getByRole("button", { name: /Revoke Teacher Access/i })
      .click();
    await expect(
      adminPage.getByTestId(`active-teacher-row-${existingCandidateEmail}`),
    ).toHaveCount(0);

    // Revoked user can no longer sign into /login/teacher
    const revokedCtx = await browser.newContext();
    const revokedPage = await revokedCtx.newPage();
    await revokedPage.goto("/login/teacher");
    await revokedPage.getByLabel(/Email address/i).fill(existingCandidateEmail);
    await revokedPage.getByLabel(/Password/i).fill(password);
    await revokedPage.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      revokedPage
        .getByRole("alert")
        .filter({ hasText: /does not have Teacher/i }),
    ).toBeVisible({ timeout: 15_000 });
    await revokedCtx.close();
    await adminCtx.close();
  });
});
