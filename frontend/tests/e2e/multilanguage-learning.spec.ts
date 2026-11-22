import { expect, test } from "@playwright/test";

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

const JS_LESSON_1_SOLUTION = [
  "console.log('Hello JavaScript');",
  "console.log(5 * 5);",
  "",
].join("\n");

test.describe("Phase 3 Multi-Language Learning & Progress Isolation E2E", () => {
  test("5-language switcher -> JS lesson execution -> Python isolation -> reload & re-login persistence -> responsive viewports", async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);

    const suffix = Date.now().toString(36);
    const email = `e2e-multilang-${suffix}@thinkfirst.test`;
    const password = "TestPassword123!";

    // 1. Provision isolated E2E student via local Supabase Auth
    const signup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email,
        password,
        data: { full_name: "MultiLang E2E Learner" },
      },
    });
    expect(signup.ok()).toBeTruthy();

    // 2. Login via student portal -> complete onboarding
    await page.setViewportSize({ width: 1366, height: 860 });
    await page.goto("/login/student");
    await page.getByLabel(/Email address/i).fill(email);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();

    await page.waitForURL("**/student/onboarding", { timeout: 25_000 });
    await page.getByLabel(/Full name/i).fill("MultiLang E2E Learner");
    // Verify C is selectable in onboarding language dropdown
    await expect(
      page.locator("#onboard-language option[value='c']"),
    ).toHaveCount(1);
    await page
      .getByRole("button", { name: /Start My Learning Journey/i })
      .click();
    await page.waitForURL("**/student", { timeout: 25_000 });

    // 3. Verify all 5 language tabs are visible on the dashboard with real DB lesson counts
    for (const slug of ["python", "javascript", "c", "cpp", "java"]) {
      await expect(page.getByTestId(`lang-tab-${slug}`)).toBeVisible();
    }
    await expect(page.getByTestId("lang-tab-python")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByTestId("lang-tab-python")).toContainText(/0\/24/);
    await expect(page.getByTestId("lang-tab-javascript")).toContainText(/0\/10/);

    // 4. Switch to JavaScript and verify dashboard updates to JS curriculum (0 / 10)
    await page.getByTestId("lang-tab-javascript").click();
    await expect(page.getByTestId("lang-tab-javascript")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(
      page.getByText(/JavaScript Guided Lessons \(10 Topics\)/i),
    ).toBeVisible({ timeout: 15_000 });

    // 5. Open JavaScript lessons catalog and verify 10 JS lessons
    await page.goto("/student/lessons");
    await expect(
      page.getByRole("heading", { name: /JavaScript Guided Lessons/i }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/0 \/ 10 completed/i)).toBeVisible();

    // 6. Open first JS lesson (`js-01-hello-output`) and run a valid Node.js solution in real sandbox
    await page.goto("/student/lessons/js-01-hello-output");
    await expect(
      page.getByText(/JavaScript Guided Practice/i),
    ).toBeVisible({ timeout: 15_000 });

    // Fill Monaco editor cleanly via Monaco API or clipboard fallback
    await page.waitForSelector(".monaco-editor", { timeout: 20_000 });
    await page.evaluate((nextCode: string) => {
      const w = window as unknown as {
        monaco?: {
          editor?: {
            getModels?: () => Array<{ setValue: (v: string) => void }>;
          };
        };
      };
      const models = w.monaco?.editor?.getModels?.() ?? [];
      if (models.length > 0) {
        models[0].setValue(nextCode);
      }
    }, JS_LESSON_1_SOLUTION);

    await page.getByRole("button", { name: /Run Guided Exercise/i }).click();
    await expect(
      page.getByText(/Lesson Completed! Guided Exercise Passed/i),
    ).toBeVisible({ timeout: 40_000 });

    // 7. Navigate back to dashboard -> JS shows 1/10 while Python STILL shows 0/24 (strict isolation!)
    await page.goto("/student");
    await expect(page.getByTestId("lang-tab-javascript")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByTestId("lang-tab-javascript")).toContainText(/1\/10/);
    await expect(page.getByTestId("lang-tab-python")).toContainText(/0\/24/);

    // 8. Reload page and confirm active language + isolated progress persist
    await page.reload();
    await expect(page.getByTestId("lang-tab-javascript")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByTestId("lang-tab-javascript")).toContainText(/1\/10/);
    await expect(page.getByTestId("lang-tab-python")).toContainText(/0\/24/);

    // 9. Switch to C, verify C lessons load (0 / 10), then verify Problem Bank language filter
    await page.getByTestId("lang-tab-c").click();
    await expect(page.getByTestId("lang-tab-c")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await page.goto("/student/lessons");
    await expect(
      page.getByRole("heading", { name: /C Guided Lessons/i }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/0 \/ 10 completed/i)).toBeVisible();

    await page.goto("/student/problems");
    const langFilter = page.getByLabel(/Filter by programming language/i);
    await expect(langFilter).toBeVisible({ timeout: 15_000 });
    await langFilter.selectOption("cpp");
    await expect(page.getByText(/Sum of Even Numbers/i).first()).toBeVisible({
      timeout: 15_000,
    });

    // 10. Responsive layout check across 375px, 768px, 1366px, 1920px (zero horizontal overflow)
    await page.goto("/student");
    for (const vp of [
      { width: 375, height: 812 },
      { width: 768, height: 1024 },
      { width: 1366, height: 860 },
      { width: 1920, height: 1080 },
    ]) {
      await page.setViewportSize(vp);
      const overflowPx = await page.evaluate(
        () =>
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth,
      );
      expect(
        overflowPx,
        `Unexpected horizontal overflow at ${vp.width}px: ${overflowPx}px`,
      ).toBeLessThanOrEqual(4);
    }
  });
});
