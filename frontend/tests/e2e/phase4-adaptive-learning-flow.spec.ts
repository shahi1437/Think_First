import { expect, test } from "@playwright/test";

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

const LESSON_1_SOLUTION = 'print("CodeMentor")\nprint(6 * 7)\n';
const LESSON_2_SOLUTION =
  "price = int(input())\ncount = int(input())\nprint(price * count)\n";

const READINESS_CORRECT_ANSWERS: Array<{ match: RegExp; option: RegExp }> = [
  {
    match: /Why does initializing `best = 0` fail/i,
    option: /0 is larger than every negative number/i,
  },
  { match: /print\("4" \+ "5"\)/i, option: /^45$/ },
  { match: /Which exception does the code below raise/i, option: /^KeyError$/ },
  { match: /if x = 5:/i, option: /= is assignment/i },
  { match: /If `score = 90`/i, option: /^C$/ },
  { match: /at least 18/i, option: /age >= 18/ },
  { match: /exact output of the loop below/i, option: /^9$/ },
  { match: /for i in range\(4\):/i, option: /4 times/i },
  { match: /sum all elements of `nums`/i, option: /total = 0 is inside the loop/i },
];

async function setMonacoValue(
  page: import("@playwright/test").Page,
  code: string,
) {
  await expect(page.locator(".monaco-editor").first()).toBeVisible({
    timeout: 25_000,
  });
  await page.evaluate((nextCode: string) => {
    const win = window as unknown as {
      monaco?: {
        editor?: {
          getModels?: () => Array<{ setValue: (v: string) => void }>;
        };
      };
    };
    const models = win.monaco?.editor?.getModels?.() ?? [];
    if (models.length > 0) {
      models[models.length - 1].setValue(nextCode);
    }
  }, code);
}

test.describe("Phase 4 Adaptive Learning Journey, Smart Onboarding, Readiness Check & Motion/A11y E2E", () => {
  test("Journey A & C & J: Absolute Beginner foundation lessons -> Short Readiness Check -> Persistence -> Responsive 320-1920px & prefers-reduced-motion", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);

    const suffix = Date.now().toString(36);
    const email = `e2e-p4-beg-${suffix}@thinkfirst.test`;
    const password = "TestPassword123!";

    // 1. Provision isolated beginner student
    const signup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email,
        password,
        data: { full_name: "Beginner Flow Learner" },
      },
    });
    expect(signup.ok()).toBeTruthy();

    // 2. Login -> Complete Smart Onboarding as absolute beginner
    await page.setViewportSize({ width: 1366, height: 860 });
    await page.goto("/login/student");
    await page.getByLabel(/Email address/i).fill(email);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();

    await page.waitForURL("**/student/onboarding", { timeout: 25_000 });
    await page.getByLabel(/Full name/i).fill("Beginner Flow Learner");
    await page.getByLabel(/^Programming experience$/i).selectOption("none");
    await page
      .getByLabel(/Preferred starting path/i)
      .selectOption("guided_beginner");
    await page
      .getByRole("button", { name: /Start My Learning Journey/i })
      .click();

    // Beginners go smoothly to /student (NOT forced straight into 8-domain diagnostic!)
    await page.waitForURL("**/student", { timeout: 25_000 });

    const continueCta = page.getByTestId("continue-learning-cta");
    await expect(continueCta).toBeVisible();
    await expect(continueCta).toHaveAttribute(
      "href",
      /\/student\/lessons\/intro-to-programming/,
    );
    await expect(page.getByText(/Beginner Foundation Path: 0\/2/i)).toBeVisible();

    // 3. Click CONTINUE LEARNING -> Lesson 1 -> Mark reading only (verify honest 0/24 progress!)
    await continueCta.click();
    await page.waitForURL("**/student/lessons/intro-to-programming", {
      timeout: 20_000,
    });
    await expect(page.getByText(/Understand Concept/i)).toBeVisible();
    await page.getByRole("button", { name: /Mark Reading Complete/i }).click();
    await expect(
      page.getByRole("button", { name: /Reading Completed/i }),
    ).toBeVisible({ timeout: 15_000 });

    // Return to /student before passing exercise -> lesson MUST still show 0/24 (not falsely completed!)
    await page.goto("/student");
    await expect(page.getByText(/^0 \/ 24$/)).toBeVisible();
    await expect(page.getByTestId("continue-learning-cta")).toHaveAttribute(
      "href",
      /\/student\/lessons\/intro-to-programming/,
    );

    // 4. Resume Lesson 1 -> pass guided exercise -> follow Next Recommended Activity to Lesson 2
    await page.getByTestId("continue-learning-cta").click();
    await page.waitForURL("**/student/lessons/intro-to-programming", {
      timeout: 20_000,
    });
    await setMonacoValue(page, LESSON_1_SOLUTION);
    await page.getByRole("button", { name: /Run Guided Exercise/i }).click();
    await expect(
      page.getByText(/Lesson Completed! Guided Exercise Passed/i),
    ).toBeVisible({ timeout: 45_000 });

    const nextAfterLesson1 = page.getByTestId("lesson-next-activity-cta");
    await expect(nextAfterLesson1).toBeVisible();
    await expect(nextAfterLesson1).toHaveAttribute(
      "href",
      /\/student\/lessons\/variables-and-data-types/,
    );
    await nextAfterLesson1.click();

    // 5. Complete Lesson 2 -> verify Short 4-Domain Readiness Check is now unlocked as next action!
    await page.waitForURL("**/student/lessons/variables-and-data-types", {
      timeout: 20_000,
    });
    await setMonacoValue(page, LESSON_2_SOLUTION);
    await page.getByRole("button", { name: /Run Guided Exercise/i }).click();
    await expect(
      page.getByText(/Lesson Completed! Guided Exercise Passed/i),
    ).toBeVisible({ timeout: 45_000 });

    const nextAfterLesson2 = page.getByTestId("lesson-next-activity-cta");
    await expect(nextAfterLesson2).toBeVisible();
    await expect(nextAfterLesson2).toHaveAttribute(
      "href",
      /\/student\/diagnostic\?mode=readiness/,
    );

    // 6. Launch Short Foundation Readiness Check (4 Domains) & complete it
    await nextAfterLesson2.click();
    await page.waitForURL("**/student/diagnostic?mode=readiness", {
      timeout: 20_000,
    });
    await expect(
      page.getByTestId("start-readiness-check-btn"),
    ).toBeVisible();
    await page.getByTestId("start-readiness-check-btn").click();

    for (let step = 0; step < 8; step++) {
      const done = await page
        .getByText(/Diagnostic Completed — Evidence-Based Track Placement/i)
        .isVisible();
      if (done) break;

      const heading = page.locator("h2").first();
      await expect(heading).toBeVisible({ timeout: 20_000 });
      const promptText = (await heading.textContent()) || "";
      const matched = READINESS_CORRECT_ANSWERS.find((item) =>
        item.match.test(promptText),
      );
      if (matched) {
        await page.getByLabel(matched.option).first().click();
      } else {
        await page.locator('input[type="radio"]').first().click();
      }

      await Promise.all([
        page.waitForResponse(
          (resp) =>
            resp.url().includes("/diagnostics/sessions/") &&
            resp.url().endsWith("/answers") &&
            resp.status() === 200,
          { timeout: 35_000 },
        ),
        page.getByRole("button", { name: /Submit Answer/i }).click(),
      ]);
    }

    await expect(
      page.getByText(/Diagnostic Completed — Evidence-Based Track Placement/i),
    ).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/Short Foundation Readiness Check/i)).toBeVisible();

    // 7. Return to Dashboard, reload, confirm 2/24 lessons + 1 diagnostic persisted & no dead end
    await page.goto("/student");
    await expect(page.getByText(/^2 \/ 24$/)).toBeVisible();
    await expect(page.getByTestId("continue-learning-cta")).toBeVisible();
    await page.reload();
    await expect(page.getByText(/^2 \/ 24$/)).toBeVisible();

    // 8. Journey J: Responsive Zero Horizontal Overflow (320px .. 1920px), Readable Typography & prefers-reduced-motion
    for (const vp of [
      { width: 320, height: 740 },
      { width: 375, height: 812 },
      { width: 390, height: 844 },
      { width: 768, height: 1024 },
      { width: 1024, height: 768 },
      { width: 1366, height: 860 },
      { width: 1920, height: 1080 },
    ]) {
      await page.setViewportSize(vp);
      const metrics = await page.evaluate(() => ({
        overflowPx:
          document.documentElement.scrollWidth - window.innerWidth,
        bodyFontSize: parseFloat(
          window.getComputedStyle(document.body).fontSize || "0",
        ),
      }));
      expect(
        metrics.overflowPx,
        `Horizontal overflow at ${vp.width}px`,
      ).toBeLessThanOrEqual(2);
      expect(metrics.bodyFontSize).toBeGreaterThanOrEqual(15);
    }

    // Verify prefers-reduced-motion disables animations cleanly
    await page.emulateMedia({ reducedMotion: "reduce" });
    const animName = await page.evaluate(() => {
      const el = document.querySelector(".tf-animate-enter");
      return el ? window.getComputedStyle(el).animationName : "none";
    });
    expect(animName).toBe("none");
  });

  test("Journey B: Experienced Student choosing diagnostic_assessment routes directly to Full Diagnostic in chosen language", async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);

    const suffix = Date.now().toString(36);
    const email = `e2e-p4-exp-${suffix}@thinkfirst.test`;
    const password = "TestPassword123!";

    const signup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email,
        password,
        data: { full_name: "Experienced JS Learner" },
      },
    });
    expect(signup.ok()).toBeTruthy();

    await page.setViewportSize({ width: 1366, height: 860 });
    await page.goto("/login/student");
    await page.getByLabel(/Email address/i).fill(email);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();

    await page.waitForURL("**/student/onboarding", { timeout: 25_000 });
    await page.getByLabel(/Full name/i).fill("Experienced JS Learner");
    await page
      .getByLabel(/^Programming experience$/i)
      .selectOption("intermediate");
    await page
      .getByLabel(/Preferred programming language/i)
      .selectOption("javascript");
    await page
      .getByLabel(/Preferred starting path/i)
      .selectOption("diagnostic_assessment");

    await page
      .getByRole("button", { name: /Start My Learning Journey/i })
      .click();

    // Experienced students choosing diagnostic_assessment land DIRECTLY on Full Diagnostic!
    await page.waitForURL("**/student/diagnostic?mode=full&entry=onboarding", {
      timeout: 25_000,
    });
    await expect(
      page.getByText(/JavaScript Adaptive Entry Assessment/i),
    ).toBeVisible();
    await expect(
      page.getByTestId("start-full-diagnostic-btn"),
    ).toBeVisible();

    // Start the JS full diagnostic and verify first JS question renders
    await page.getByTestId("start-full-diagnostic-btn").click();
    await expect(page.getByText(/8-Domain Diagnostic/i)).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.locator("h2").first()).toBeVisible();
  });
});
