import { expect, test } from "@playwright/test";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

test.describe("Phase 3 Live Student Journey & Responsive UI", () => {
  test("Student Login -> Problem Bank -> Monaco -> Run -> Fix -> Submit -> History + Responsive check", async ({
    page,
    request,
  }) => {
    const suffix = Date.now().toString(36);
    const email = `e2e-student-${suffix}@thinkfirst.test`;
    const password = "TestPassword123!";

    // 1. Provision real student via local Supabase Auth
    const signup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email,
        password,
        data: { full_name: "E2E Learner" },
      },
    });
    expect(signup.ok()).toBeTruthy();

    // 2. Public Landing Page + redesigned portal links + no dev diagnostics exposed
    await page.goto("/");
    await expect(
      page.getByRole("heading", {
        name: /Master Python programming through practice, error diagnosis, and guided reasoning/i,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Create Student Account/i }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "STUDENT LOGIN" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "TEACHER LOGIN" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "ADMIN LOGIN" }),
    ).toBeVisible();
    await expect(page.getByText("API Server Connected")).toHaveCount(0);
    await expect(page.getByText("PostgreSQL: Ready")).toHaveCount(0);

    // 3. Login via real UI form
    await page.goto("/login");
    await page.getByLabel(/Email address/i).fill(email);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();

    // 4. First-time student redirected to Smart Onboarding -> Complete onboarding
    await page.waitForURL("**/student/onboarding");
    await page.getByLabel(/Full name/i).fill("E2E Learner");
    await page
      .getByRole("button", {
        name: /Start My Learning Journey|Complete onboarding/i,
      })
      .click();
    await page.waitForURL("**/student");

    // 5. Navigate to Problem Bank & open Debugging challenge
    await page.getByRole("link", { name: /Problem Bank/i }).first().click();
    await page.waitForURL("**/student/problems");
    await expect(page.getByText("Debug: Inclusive Range Sum")).toBeVisible();

    const debugCard = page
      .locator("article")
      .filter({ hasText: "Debug: Inclusive Range Sum" });
    await debugCard.getByRole("link", { name: /Open Debugger/i }).click();
    await page.waitForURL("**/student/problems/**");

    // Verify zero horizontal overflow on desktop
    const desktopOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(desktopOverflow).toBeFalsy();

    // Wait for Monaco editor to mount
    await expect(page.locator(".monaco-editor").first()).toBeVisible({
      timeout: 25_000,
    });

    // 6. Predict & Run buggy starter code -> Real Judge0 Wrong Answer (0/2)
    await page
      .getByLabel(/Output prediction/i)
      .fill("range(3, 5) will print 7 instead of 12.");
    await page.getByRole("button", { name: /Run Code/i }).click();
    await expect(page.getByText("0 / 2 tests passed")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText("Wrong Answer").first()).toBeVisible();

    // 7. Explain bug, fix code in Monaco via model API, and Submit -> Real Judge0 Accepted (5/5)
    await page
      .getByLabel(/Bug explanation/i)
      .fill("Python range excludes upper bound; changed range(a, b) to range(a, b + 1).");

    await page.evaluate(() => {
      const win = window as unknown as {
        monaco?: {
          editor: {
            getModels: () => Array<{
              getValue: () => string;
              setValue: (v: string) => void;
            }>;
          };
        };
      };
      const models = win.monaco?.editor.getModels() ?? [];
      if (models.length > 0) {
        const current = models[0].getValue();
        models[0].setValue(current.replace("range(a, b)", "range(a, b + 1)"));
      }
    });

    await page.getByRole("button", { name: /Submit Code/i }).click();
    await expect(page.getByText("5 / 5 tests passed")).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.getByText("Accepted").first()).toBeVisible();
    await expect(
      page.getByText(/Hidden test input and expected output remain private/i).first(),
    ).toBeVisible();

    // 8. Check saved Submission History
    await page.getByRole("button", { name: /Submissions \(2\)/i }).click();
    await expect(page.getByText("5/5 passed")).toBeVisible();

    // 9. Verify Mobile (390x844) & Tablet (768x1024) layouts have accessible tabs & zero overflow
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.getByRole("tab", { name: "Editor" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Results" })).toBeVisible();
    const mobileOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(mobileOverflow).toBeFalsy();

    await page.setViewportSize({ width: 768, height: 1024 });
    const tabletOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(tabletOverflow).toBeFalsy();

    // 10. Ordinary Student cannot access Admin Problem Studio
    await page.goto("/admin/problems");
    await page.waitForURL("**/student?error=forbidden");
  });
});
