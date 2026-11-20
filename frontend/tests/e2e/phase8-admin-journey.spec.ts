import { execSync } from "node:child_process";
import { expect, test } from "@playwright/test";

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

test.describe("Phase 8 Complete Admin Studio, Validation, Curriculum & Student Discovery E2E", () => {
  test("Admin Login -> Overview Metrics -> Problem Studio Judge0 Validate & Publish -> Student Discovers & Solves -> Unauthorized Role Redirected -> Responsive Check", async ({
    browser,
    request,
  }) => {
    test.setTimeout(180_000);

    const suffix = Date.now().toString(36);
    const adminEmail = `e2e-p8-admin-${suffix}@thinkfirst.test`;
    const studentEmail = `e2e-p8-student-${suffix}@thinkfirst.test`;
    const password = "TestPassword123!";

    const adminSignup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email: adminEmail,
        password,
        data: { full_name: "Prof. Phase8 Admin" },
      },
    });
    expect(adminSignup.ok()).toBeTruthy();
    const adminId = ((await adminSignup.json()) as { user: { id: string } })
      .user.id;

    const studentSignup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email: studentEmail,
        password,
        data: { full_name: "Phase8 Student" },
      },
    });
    expect(studentSignup.ok()).toBeTruthy();

    execSync(
      `docker exec supabase_db_think-first-codementor psql -U postgres -d postgres -c "INSERT INTO public.user_roles (user_id, role, granted_by) VALUES ('${adminId}', 'admin', '${adminId}') ON CONFLICT DO NOTHING;"`,
    );

    // 1. Admin logs in and inspects Overview, Curriculum, Diagnostics & Audit
    const adminCtx = await browser.newContext({
      viewport: { width: 1280, height: 860 },
    });
    const adminPage = await adminCtx.newPage();
    await adminPage.goto("/login");
    await adminPage.getByLabel(/Email address/i).fill(adminEmail);
    await adminPage.getByLabel(/Password/i).fill(password);
    await adminPage.getByRole("button", { name: /Sign in/i }).click();
    await adminPage.waitForURL("**/admin", { timeout: 25_000 });

    await adminPage.goto("/admin");
    await expect(
      adminPage.getByText(/Curriculum & Assessment Control Center/i),
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      adminPage.getByText(/12 Intermediate & Advanced/i),
    ).toBeVisible();

    await adminPage.getByRole("link", { name: /Curriculum & Lessons|Manage Lessons & Tracks/i }).first().click();
    await adminPage.waitForURL("**/admin/curriculum");
    await expect(
      adminPage.getByText(/Curriculum Lessons \(24\)/i),
    ).toBeVisible({ timeout: 15_000 });

    // 2. Admin authors a new Intermediate Problem -> Judge0 Validate -> Submit Review -> Approve -> Publish
    await adminPage.goto("/admin/problems");
    const newSlug = `e2e-p8-triple-${suffix}`;
    const newTitle = `E2E Phase 8 Cube Plus One (${suffix})`;

    await adminPage
      .getByPlaceholder("sum-of-even-numbers")
      .fill(newSlug);
    await adminPage.getByPlaceholder("Problem title").fill(newTitle);
    await adminPage
      .locator("select")
      .nth(1)
      .selectOption("intermediate");
    await adminPage
      .locator("textarea")
      .nth(0)
      .fill("Read integer n and print n * n + 1.");
    await adminPage
      .locator("textarea")
      .nth(1)
      .fill("n = int(input())\n# print n * n + 1\n");
    await adminPage
      .locator("textarea")
      .nth(2)
      .fill("n = int(input())\nprint(n * n + 1)\n");
    // Expected outputs in default test cases (input 5 -> 26, -3 -> 10)
    await adminPage.locator("textarea").nth(4).fill("26");
    await adminPage.locator("textarea").nth(6).fill("10");

    await adminPage.getByRole("button", { name: /Save Draft/i }).click();
    await expect(
      adminPage.getByText(/Saved version v1 \(draft\)/i),
    ).toBeVisible({ timeout: 15_000 });

    await adminPage
      .getByRole("button", { name: /Validate via Judge0/i })
      .click();
    await expect(
      adminPage.getByText(/Judge0 Validation Report: PASSED/i),
    ).toBeVisible({ timeout: 30_000 });

    await adminPage.getByRole("button", { name: /Submit Review/i }).click();
    await expect(
      adminPage.getByText(/Problem moved to In-Review queue/i),
    ).toBeVisible({ timeout: 15_000 });

    await adminPage.getByRole("button", { name: /^Approve$/i }).click();
    await expect(
      adminPage.getByText(/Problem approved by reviewer/i),
    ).toBeVisible({ timeout: 15_000 });

    await adminPage.getByRole("button", { name: /^Publish$/i }).click();
    await expect(
      adminPage.getByText(/published live to the Student Problem Bank/i),
    ).toBeVisible({ timeout: 15_000 });

    // 3. Student logs in -> verifies /admin is denied -> discovers new published problem -> solves on Judge0
    const studentCtx = await browser.newContext({
      viewport: { width: 1280, height: 860 },
    });
    const studentPage = await studentCtx.newPage();
    await studentPage.goto("/login");
    await studentPage.getByLabel(/Email address/i).fill(studentEmail);
    await studentPage.getByLabel(/Password/i).fill(password);
    await studentPage.getByRole("button", { name: /Sign in/i }).click();
    await studentPage.waitForURL("**/student/onboarding");
    await studentPage.getByLabel(/Full name/i).fill("Phase8 Student");
    await studentPage
      .getByRole("button", { name: /Complete onboarding/i })
      .click();
    await studentPage.waitForURL("**/student");

    // Unauthorized Student cannot access /admin
    await studentPage.goto("/admin");
    await studentPage.waitForURL("**/student**");

    await studentPage.goto("/student/problems");
    await expect(studentPage.getByText(newTitle).first()).toBeVisible({
      timeout: 15_000,
    });
    const card = studentPage.locator("article").filter({ hasText: newTitle });
    await card.getByRole("link", { name: /Solve Problem/i }).click();
    await studentPage.waitForURL("**/student/problems/**");

    await expect(
      studentPage
        .locator('.monaco-editor, textarea[aria-label="Code editor"]')
        .first(),
    ).toBeVisible({ timeout: 25_000 });
    await studentPage.evaluate(() => {
      const win = window as unknown as {
        monaco?: {
          editor: { getModels: () => Array<{ setValue: (v: string) => void }> };
        };
      };
      const models = win.monaco?.editor.getModels() ?? [];
      if (models.length > 0) {
        models[models.length - 1].setValue("n = int(input())\nprint(n * n + 1)\n");
      }
    });
    await studentPage.getByRole("button", { name: /Submit Code/i }).click();
    await expect(studentPage.getByText("2 / 2 tests passed")).toBeVisible({
      timeout: 35_000,
    });

    // Cleanly archive the synthetic E2E problem via Admin Studio & verify responsive UI across Admin routes
    await adminPage.on("dialog", (dialog) => dialog.accept());
    await adminPage.getByRole("button", { name: /^Archive$/i }).click();
    await expect(
      adminPage.getByText(/Problem archived from new discovery/i),
    ).toBeVisible({ timeout: 15_000 });

    for (const route of [
      "/admin",
      "/admin/problems",
      "/admin/curriculum",
      "/admin/diagnostics",
      "/admin/audit",
    ]) {
      await adminPage.goto(route);
      for (const [width, height] of [
        [1280, 860],
        [768, 1024],
        [390, 844],
      ] as const) {
        await adminPage.setViewportSize({ width, height });
        const overflow = await adminPage.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth + 1,
        );
        expect(
          overflow,
          `Horizontal overflow on ${route} at ${width}px`,
        ).toBeFalsy();
      }
    }

    await adminCtx.close();
    await studentCtx.close();
  });
});
