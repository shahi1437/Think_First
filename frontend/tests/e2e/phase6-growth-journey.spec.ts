import { expect, test } from "@playwright/test";

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

test.describe("Phase 6 Complete Adaptive Growth E2E (Learning DNA, Daily Plan, History & Retention)", () => {
  test("Login -> Onboarding -> Guided Lesson Judge0 Pass -> Learning DNA -> Daily Plan Complete & Regenerate -> Searchable History -> Retention Check -> Responsive Desktop/Tablet/Mobile", async ({
    page,
    request,
  }) => {
    test.setTimeout(150_000);

    const suffix = Date.now().toString(36);
    const email = `e2e-p6-${suffix}@thinkfirst.test`;
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
        data: { full_name: "Phase6 E2E Learner" },
      },
    });
    expect(signup.ok()).toBeTruthy();

    // 2. Login via UI & complete Smart Onboarding
    await page.setViewportSize({ width: 1280, height: 860 });
    await page.goto("/login");
    await page.getByLabel(/Email address/i).fill(email);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();

    await page.waitForURL("**/student/onboarding");
    await page.getByLabel(/Full name/i).fill("Phase6 E2E Learner");
    await page.getByRole("button", { name: /Complete onboarding/i }).click();
    await page.waitForURL("**/student");

    // Verify Phase 6 Growth Hub cards are integrated directly into Student Dashboard
    await expect(page.getByText(/Adaptive Daily Plan/i).first()).toBeVisible();
    await expect(page.getByText(/Learning DNA/i).first()).toBeVisible();
    await expect(page.getByText(/Retention Verification/i).first()).toBeVisible();
    await expect(page.getByText(/Persistent History/i).first()).toBeVisible();

    // 3. Complete Lesson 1 (`intro-to-programming`) with real Judge0 execution to generate real evidence
    await page.goto("/student/lessons/intro-to-programming");
    await page.getByRole("button", { name: /Mark Reading Complete/i }).click();
    await expect(page.getByText(/Reading Completed/i)).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.locator(".monaco-editor").first()).toBeVisible({
      timeout: 25_000,
    });
    await page.evaluate(() => {
      const win = window as unknown as {
        monaco?: {
          editor: {
            getModels: () => Array<{ setValue: (v: string) => void }>;
          };
        };
      };
      const models = win.monaco?.editor.getModels() ?? [];
      if (models.length > 0) {
        models[models.length - 1].setValue(
          'print("CodeMentor")\nprint(6 * 7)\n',
        );
      }
    });

    const exRunPromise = page.waitForResponse(
      (res) =>
        res.url().includes("/exercise/run") && res.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: /Run Guided Exercise/i })
      .click();
    const exRunRes = await exRunPromise;
    expect(exRunRes.ok()).toBeTruthy();
    await expect(
      page.getByText(/Lesson Completed! Guided Exercise Passed/i),
    ).toBeVisible({
      timeout: 25_000,
    });

    // 4. Open Learning DNA -> verify 6 dimensions & Bangla toggle
    await page.getByRole("link", { name: /^Learning DNA$/i }).first().click();
    await page.waitForURL("**/student/dna");
    await expect(
      page.getByRole("heading", { name: /Code Tracing & Prediction/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Python Implementation/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Long-Term Retention/i }),
    ).toBeVisible();

    await page.getByRole("button", { name: "বাংলা" }).click();
    await expect(
      page.getByRole("heading", { name: /কোড ট্রেসিং ও পূর্বাভাস/i }),
    ).toBeVisible();
    await page.getByRole("button", { name: "English" }).click();

    // 5. Open Adaptive Daily Plan -> complete first task -> regenerate v2 with 30m budget
    await page.getByRole("link", { name: /^Daily Plan$/i }).first().click();
    await page.waitForURL("**/student/daily-plan");
    await expect(page.getByText(/v1 · 0\//i)).toBeVisible();

    const firstCheckbox = page
      .getByRole("button", { name: /Mark .* completed/i })
      .first();
    await firstCheckbox.click();
    await expect(page.getByText(/v1 · 1\//i)).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: "30m" }).click();
    const regenPromise = page.waitForResponse(
      (res) =>
        res.url().includes("/api/v1/growth/daily-plan/regenerate") &&
        res.request().method() === "POST",
    );
    await page.getByRole("button", { name: /Regenerate Plan/i }).click();
    expect((await regenPromise).ok()).toBeTruthy();
    await expect(page.getByText(/v2 · 0\//i)).toBeVisible({ timeout: 15_000 });

    // 6. Open Persistent Learning History -> verify persisted Lesson & Daily Plan events + search
    await page.getByRole("link", { name: /^History$/i }).first().click();
    await page.waitForURL("**/student/history");
    await expect(
      page.getByText(/Your Complete Learning Timeline/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Lesson: Introduction to Programming/i).first(),
    ).toBeVisible();

    await page.getByLabel(/Search learning history/i).fill("Introduction");
    await page.getByRole("button", { name: /^Search$/i }).click();
    await expect(
      page.getByText(/Lesson: Introduction to Programming/i).first(),
    ).toBeVisible();

    // 7. Open Retention Verification -> verify auto-scheduled 24h check appears honestly
    await page.getByRole("link", { name: /^Retention$/i }).first().click();
    await page.waitForURL("**/student/retention");
    await expect(
      page.getByText(/Prove Long-Term Retention with Delayed Judge0 Checks/i),
    ).toBeVisible();
    await expect(page.getByText(/Scheduled Retention Checks/i)).toBeVisible();

    // 8. Responsive overflow check across Desktop (1280px), Tablet (768px), Mobile (390px)
    for (const route of [
      "/student/dna",
      "/student/daily-plan",
      "/student/history",
      "/student/retention",
    ]) {
      await page.goto(route);
      for (const [width, height] of [
        [1280, 860],
        [768, 1024],
        [390, 844],
      ] as const) {
        await page.setViewportSize({ width, height });
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth + 1,
        );
        expect(overflow, `Horizontal overflow on ${route} at ${width}px`).toBeFalsy();
      }
    }
  });
});
