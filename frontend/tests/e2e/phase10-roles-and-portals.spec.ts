import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "@playwright/test";

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const BACKEND_PYTHON = path.join(REPO_ROOT, "backend", ".venv", "Scripts", "python.exe");
const BOOTSTRAP_SCRIPT = path.join(REPO_ROOT, "backend", "scripts", "bootstrap_first_admin.py");

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

test.describe("Phase 10 Role-Aware Login, Portal Switcher & Multi-Role Access", () => {
  test("Student blocked from Teacher/Admin; Admin (without teacher role) -> /admin, grants Teacher via UI, accesses /teacher & /student; Teacher -> /teacher & blocked from /admin", async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);

    const suffix = Date.now().toString(36);
    const studentEmail = `p10-stu-${suffix}@thinkfirst.test`;
    const teacherEmail = `p10-tch-${suffix}@thinkfirst.test`;
    const adminEmail = `p10-adm-${suffix}@thinkfirst.test`;
    const password = "Phase10Password123!";

    // 1. Provision 3 real accounts via local Supabase Auth (auto-assigned student only)
    for (const [email, name] of [
      [studentEmail, "P10 Student"],
      [teacherEmail, "P10 Teacher"],
      [adminEmail, "P10 Admin"],
    ] as const) {
      const signup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          "Content-Type": "application/json",
        },
        data: {
          email,
          password,
          data: { full_name: name },
        },
      });
      expect(signup.ok()).toBeTruthy();
    }

    // 2. Student-only login -> completes onboarding, lands on /student, sees NO Portal Switcher, blocked from /teacher & /admin
    await page.goto("/login");
    await page.getByLabel(/Email address/i).fill(studentEmail);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();
    await page.waitForURL("**/student/onboarding", { timeout: 25_000 });
    await page.getByLabel(/Full name/i).fill("P10 Student");
    await page.getByRole("button", { name: /Complete onboarding/i }).click();
    await page.waitForURL("**/student", { timeout: 25_000 });
    await expect(page.getByRole("group", { name: "Portal switcher" })).toHaveCount(0);

    await page.goto("/teacher");
    await page.waitForURL("**/student?error=forbidden", { timeout: 20_000 });
    await expect(page.getByRole("alert").filter({ hasText: /Access denied/i })).toBeVisible();

    await page.goto("/admin");
    await page.waitForURL("**/student?error=forbidden", { timeout: 20_000 });
    await expect(page.getByRole("alert").filter({ hasText: /Access denied/i })).toBeVisible();
    await page.getByRole("button", { name: /Sign out/i }).click();
    await page.waitForURL("**/login", { timeout: 20_000 });

    // 3. Bootstrap ONLY 'admin' role (NO explicit 'teacher' role) via audited CLI script
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

    // 4. Admin login -> role-aware redirect straight to /admin, visits all 5 Admin routes,
    //    grants Teacher via Admin UI, and uses Portal Switcher to open /teacher & /student
    await page.goto("/login");
    await page.getByLabel(/Email address/i).fill(adminEmail);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();
    await page.waitForURL("**/admin", { timeout: 25_000 });

    const admSwitcher = page.getByRole("group", { name: "Portal switcher" });
    await expect(admSwitcher.getByRole("link", { name: "Student" })).toBeVisible();
    await expect(admSwitcher.getByRole("link", { name: "Teacher" })).toBeVisible();
    await expect(admSwitcher.getByRole("link", { name: "Admin" })).toBeVisible();

    for (const adminSubRoute of [
      "/admin/problems",
      "/admin/curriculum",
      "/admin/diagnostics",
      "/admin/audit",
    ]) {
      await page.goto(adminSubRoute);
      await expect(page).toHaveURL(new RegExp(adminSubRoute.replace("/", "\\/")));
    }

    // Grant Teacher role to teacherEmail cleanly through Admin UI
    const teacherRow = page.locator("tr", { hasText: teacherEmail });
    await expect(teacherRow).toBeVisible({ timeout: 15_000 });
    await teacherRow.getByRole("button", { name: "Grant Teacher" }).click();
    await expect(page.getByText(/Granted 'teacher' role/i)).toBeVisible({
      timeout: 15_000,
    });

    // Switch to Teacher portal from Admin Portal Switcher without explicit teacher role
    await page
      .getByRole("group", { name: "Portal switcher" })
      .getByRole("link", { name: "Teacher" })
      .click();
    await page.waitForURL("**/teacher", { timeout: 20_000 });
    await expect(page.getByText(/Teacher Command Center|Classes/i).first()).toBeVisible();

    // Switch to Student portal from Portal Switcher (admin hasn't onboarded yet, so goes cleanly to onboarding or dashboard)
    await page
      .getByRole("group", { name: "Portal switcher" })
      .getByRole("link", { name: "Student" })
      .click();
    await page.waitForURL("**/student**", { timeout: 20_000 });

    await page.getByRole("button", { name: /Sign out/i }).click();
    await page.waitForURL("**/login", { timeout: 20_000 });

    // 5. Teacher login -> role-aware redirect straight to /teacher, sees Student + Teacher switcher, blocked from /admin
    await page.goto("/login");
    await page.getByLabel(/Email address/i).fill(teacherEmail);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();
    await page.waitForURL("**/teacher", { timeout: 25_000 });

    const tchSwitcher = page.getByRole("group", { name: "Portal switcher" });
    await expect(tchSwitcher.getByRole("link", { name: "Student" })).toBeVisible();
    await expect(tchSwitcher.getByRole("link", { name: "Teacher" })).toBeVisible();
    await expect(tchSwitcher.getByRole("link", { name: "Admin" })).toHaveCount(0);

    await page.goto("/admin");
    await page.waitForURL("**/teacher?error=forbidden", { timeout: 20_000 });
    await expect(page.getByRole("alert").filter({ hasText: /Access denied/i })).toBeVisible();
  });
});
