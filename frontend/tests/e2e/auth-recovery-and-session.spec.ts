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
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8100";
const MAILPIT_URL = process.env.MAILPIT_URL || "http://127.0.0.1:54324";

async function signInViaSupabaseToken(
  request: import("@playwright/test").APIRequestContext,
  email: string,
  password: string,
): Promise<string> {
  const res = await request.post(
    `${SUPABASE_URL}/auth/v1/token?grant_type=password`,
    {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: { email, password },
    },
  );
  expect(res.ok()).toBeTruthy();
  const payload = (await res.json()) as { access_token: string };
  return payload.access_token;
}

async function fetchLatestRecoveryLink(
  request: import("@playwright/test").APIRequestContext,
  recipientEmail: string,
): Promise<string> {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const res = await request.get(`${MAILPIT_URL}/api/v1/messages`);
    if (res.ok()) {
      const data = (await res.json()) as {
        messages?: Array<{
          ID: string;
          To?: Array<{ Address: string }>;
          Subject?: string;
        }>;
      };
      const match = (data.messages ?? []).find((msg) =>
        (msg.To ?? []).some(
          (to) => to.Address.toLowerCase() === recipientEmail.toLowerCase(),
        ),
      );
      if (match) {
        const detailRes = await request.get(
          `${MAILPIT_URL}/api/v1/message/${match.ID}`,
        );
        expect(detailRes.ok()).toBeTruthy();
        const detail = (await detailRes.json()) as {
          Text?: string;
          HTML?: string;
        };
        const body = `${detail.HTML ?? ""}\n${detail.Text ?? ""}`.replaceAll(
          "&amp;",
          "&",
        );
        const urlMatch = body.match(/https?:\/\/[^\s"'<>]+verify[^\s"'<>]*/i);
        if (urlMatch) {
          return urlMatch[0];
        }
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`No recovery email found in Mailpit for ${recipientEmail}`);
}

test.describe("Complete Auth, Recovery, Multi-Tab & Mobile Responsive Matrix", () => {
  test("verifies all 3 login portals, error distinctions, real email password recovery on desktop & mobile, logout, Back button, stale cookie cleanup, and multi-tab sync", async ({
    browser,
    request,
  }) => {
    test.setTimeout(240_000);

    const suffix = Date.now().toString(36);
    const studentEmail = `auth-stu-${suffix}@thinkfirst.test`;
    const teacherEmail = `auth-tch-${suffix}@thinkfirst.test`;
    const adminEmail = `auth-adm-${suffix}@thinkfirst.test`;
    const initialPassword = "AuthMatrixPassword1!";
    const updatedTeacherPassword = "UpdatedTeacherPass2!";

    // Provision 3 isolated local QA users
    for (const [email, name] of [
      [studentEmail, "Auth QA Student"],
      [teacherEmail, "Auth QA Teacher"],
      [adminEmail, "Auth QA Admin"],
    ] as const) {
      const signup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          "Content-Type": "application/json",
        },
        data: { email, password: initialPassword, data: { full_name: name } },
      });
      expect(signup.ok()).toBeTruthy();
    }

    // Bootstrap isolated QA Admin and grant Teacher role to isolated QA Teacher
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
    const adminToken = await signInViaSupabaseToken(
      request,
      adminEmail,
      initialPassword,
    );
    const listRes = await request.get(
      `${API_BASE_URL}/api/v1/admin/users?q=${encodeURIComponent(suffix)}&limit=20`,
      { headers: { Authorization: `Bearer ${adminToken}` } },
    );
    expect(listRes.ok()).toBeTruthy();
    const listData = (await listRes.json()) as {
      items: Array<{ id: string; email: string }>;
    };
    const teacherId = listData.items.find((u) => u.email === teacherEmail)?.id;
    expect(teacherId).toBeTruthy();
    const grantRes = await request.post(
      `${API_BASE_URL}/api/v1/admin/users/${teacherId!}/roles`,
      {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: { role: "teacher" },
      },
    );
    expect(grantRes.ok()).toBeTruthy();

    // 1. Responsive & zero-5xx verification across desktop/tablet/mobile viewports
    const responsiveCtx = await browser.newContext();
    const responsivePage = await responsiveCtx.newPage();
    const serverErrors: string[] = [];
    responsivePage.on("response", (resp) => {
      if (resp.status() >= 500) {
        serverErrors.push(`${resp.status()} ${resp.url()}`);
      }
    });

    for (const vp of [
      { width: 375, height: 812 },
      { width: 390, height: 844 },
      { width: 768, height: 1024 },
      { width: 1440, height: 900 },
    ]) {
      await responsivePage.setViewportSize(vp);
      for (const route of [
        "/login/student",
        "/login/teacher",
        "/login/admin",
        "/forgot-password?portal=teacher",
        "/reset-password?portal=teacher&error=recovery_expired",
      ]) {
        await responsivePage.goto(route);
        const overflow = await responsivePage.evaluate(
          () =>
            document.documentElement.scrollWidth >
            document.documentElement.clientWidth,
        );
        expect(overflow, `Overflow at ${vp.width}x${vp.height} on ${route}`).toBe(
          false,
        );
      }
    }
    expect(serverErrors).toEqual([]);

    // 2. Callback negative cases: expired/invalid/missing token & open redirect protection
    await responsivePage.goto(
      "/auth/callback?error=access_denied&error_code=otp_expired&next=%2Freset-password%3Fportal%3Dteacher",
    );
    await responsivePage.waitForURL(
      "**/reset-password?error=recovery_expired&portal=teacher",
    );
    await expect(
      responsivePage.getByText(/Password recovery link unavailable/i),
    ).toBeVisible();

    await responsivePage.goto("/auth/callback?next=%2Freset-password");
    await responsivePage.waitForURL("**/reset-password?error=recovery_missing");
    await expect(
      responsivePage.getByRole("link", { name: /Request a New Reset Link/i }),
    ).toBeVisible();

    await responsivePage.goto("/reset-password");
    await expect(
      responsivePage.getByText(/Password recovery link unavailable/i),
    ).toBeVisible({ timeout: 15_000 });
    await responsiveCtx.close();

    // 3. Wrong Student password vs Portal Access Denied distinction + Multi-tab Logout Sync + Browser Back
    const studentCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const tabA = await studentCtx.newPage();

    // Wrong password
    await tabA.goto("/login/student");
    await tabA.getByLabel(/Email address/i).fill(studentEmail);
    await tabA.getByLabel(/Password/i).fill("WrongPassword999!");
    await tabA.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      tabA.getByRole("alert").filter({ hasText: /Invalid email or password/i }),
    ).toBeVisible();

    // Valid Student credentials on Teacher Portal -> password accepted, portal denied + Student link!
    await tabA.goto("/login/teacher");
    await tabA.getByLabel(/Email address/i).fill(studentEmail);
    await tabA.getByLabel(/Password/i).fill(initialPassword);
    await tabA.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      tabA.getByRole("alert").filter({
        hasText:
          /password was accepted, but this account does not have Teacher portal access/i,
      }),
    ).toBeVisible();
    await expect(
      tabA.getByRole("link", { name: /Open Student Login/i }),
    ).toBeVisible();

    // Valid Student login + onboarding + refresh
    await tabA.goto("/login/student");
    await tabA.getByLabel(/Email address/i).fill(studentEmail);
    await tabA.getByLabel(/Password/i).fill(initialPassword);
    await tabA.getByRole("button", { name: /Sign in/i }).click();
    await tabA.waitForURL("**/student/onboarding", { timeout: 25_000 });
    await tabA.getByLabel(/Full name/i).fill("Auth QA Student");
    await tabA
      .getByRole("button", {
        name: /Start My Learning Journey|Complete onboarding/i,
      })
      .click();
    await tabA.waitForURL("**/student", { timeout: 25_000 });
    await tabA.reload();
    await expect(tabA).toHaveURL(/\/student$/);

    // Open Tab B on /student while Tab A logs out -> Tab B must sync to /login!
    const tabB = await studentCtx.newPage();
    await tabB.goto("/student");
    await expect(tabB).toHaveURL(/\/student$/);

    await tabA.getByRole("button", { name: /Sign out/i }).click();
    await tabA.waitForURL("**/login", { timeout: 20_000 });
    await tabB.waitForURL("**/login**", { timeout: 15_000 });

    // Browser Back after logout & direct protected route must not show dashboard
    await tabA.goBack();
    await tabA.waitForURL("**/login**", { timeout: 15_000 });
    await tabA.goto("/student");
    await tabA.waitForURL("**/login/student**", { timeout: 15_000 });

    // Stale/tampered sb-* cookie -> cleared cleanly with session_expired (zero redirect loop!)
    await studentCtx.addCookies([
      {
        name: "sb-local-auth-token",
        value: "tampered-expired-session-value",
        url: "http://localhost:3100",
      },
    ]);
    await tabA.goto("/student");
    await tabA.waitForURL("**/login/student?next=%2Fstudent&error=session_expired", {
      timeout: 15_000,
    });
    await expect(
      tabA.getByRole("alert").filter({ hasText: /session expired/i }),
    ).toBeVisible();
    await studentCtx.close();

    // 4. REAL Forgot Password + Email Link + Mobile Viewport (390x844) Recovery + Refresh + New Password Login
    const mobileCtx = await browser.newContext({
      viewport: { width: 390, height: 844 },
    });
    const mobilePage = await mobileCtx.newPage();

    await mobilePage.goto("/forgot-password?portal=teacher");
    await mobilePage.getByLabel(/Account email/i).fill(teacherEmail);
    await mobilePage
      .getByRole("button", { name: /Send password reset link/i })
      .click();
    await expect(mobilePage.getByText(/Recovery link sent/i)).toBeVisible({
      timeout: 15_000,
    });

    const recoveryLink = await fetchLatestRecoveryLink(request, teacherEmail);
    await mobilePage.goto(recoveryLink);
    await mobilePage.waitForURL("**/reset-password**", { timeout: 20_000 });
    await expect(mobilePage.getByLabel(/^New password$/i)).toBeVisible({
      timeout: 15_000,
    });

    // Browser refresh during active recovery session must keep reset form usable!
    await mobilePage.reload();
    await expect(mobilePage.getByLabel(/^New password$/i)).toBeVisible({
      timeout: 15_000,
    });

    // Weak password & confirm mismatch checks
    await mobilePage.getByLabel(/^New password$/i).fill("weak");
    await mobilePage.getByLabel(/Confirm new password/i).fill("weak");
    await mobilePage.getByRole("button", { name: /Save New Password/i }).click();
    await expect(
      mobilePage.getByText(/Password must be at least 8 characters/i),
    ).toBeVisible();

    await mobilePage.getByLabel(/^New password$/i).fill(updatedTeacherPassword);
    await mobilePage
      .getByLabel(/Confirm new password/i)
      .fill("DifferentPass999!");
    await mobilePage.getByRole("button", { name: /Save New Password/i }).click();
    await expect(mobilePage.getByText(/Passwords do not match/i)).toBeVisible();

    // Save valid new password
    await mobilePage
      .getByLabel(/Confirm new password/i)
      .fill(updatedTeacherPassword);
    await mobilePage.getByRole("button", { name: /Save New Password/i }).click();
    await expect(
      mobilePage.getByText(/Password updated successfully/i),
    ).toBeVisible({ timeout: 20_000 });

    // Reusing the already-used recovery link must show clear error!
    await mobilePage.goto(recoveryLink);
    await mobilePage.waitForURL("**/reset-password**", { timeout: 20_000 });
    await expect(
      mobilePage.getByText(/Password recovery link unavailable/i),
    ).toBeVisible({ timeout: 15_000 });

    // Old password must fail; new password must log into /teacher cleanly!
    await mobilePage.goto("/login/teacher");
    await mobilePage.getByLabel(/Email address/i).fill(teacherEmail);
    await mobilePage.getByLabel(/Password/i).fill(initialPassword);
    await mobilePage.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      mobilePage
        .getByRole("alert")
        .filter({ hasText: /Invalid email or password/i }),
    ).toBeVisible();

    await mobilePage.getByLabel(/Password/i).fill(updatedTeacherPassword);
    await mobilePage.getByRole("button", { name: /Sign in/i }).click();
    await mobilePage.waitForURL((url) => url.pathname === "/teacher", {
      timeout: 25_000,
    });
    await expect(
      mobilePage.getByRole("heading", { name: /Welcome,/i }),
    ).toBeVisible();

    // Teacher blocked from /admin
    await mobilePage.goto("/admin");
    await mobilePage.waitForURL("**/teacher?error=forbidden", {
      timeout: 20_000,
    });
    await mobileCtx.close();

    // 5. Admin Login + Refresh + Logout
    const adminCtx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const adminPage = await adminCtx.newPage();
    await adminPage.goto("/login/admin");
    await adminPage.getByLabel(/Email address/i).fill(adminEmail);
    await adminPage.getByLabel(/Password/i).fill(initialPassword);
    await adminPage.getByRole("button", { name: /Sign in/i }).click();
    await adminPage.waitForURL((url) => url.pathname === "/admin", {
      timeout: 25_000,
    });
    await expect(
      adminPage.getByText(/Platform Connectivity Check/i),
    ).toBeVisible({ timeout: 15_000 });
    await adminPage.reload();
    await expect(adminPage).toHaveURL(/\/admin$/);
    await adminPage.getByRole("button", { name: /Sign out/i }).click();
    await adminPage.waitForURL((url) => url.pathname === "/login", {
      timeout: 20_000,
    });
    await adminCtx.close();
  });
});
