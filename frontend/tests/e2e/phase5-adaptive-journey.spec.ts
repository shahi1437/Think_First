import { expect, test } from "@playwright/test";

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

const CORRECT_BY_TEXT: Array<{ match: RegExp; option: RegExp }> = [
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
  { match: /len\(\[10, 20, 30\]\)/i, option: /^3$/ },
  { match: /adjacent-pair comparison raise `IndexError`/i, option: /requests arr\[4\]/i },
  { match: /what is `nums\[1\]`/i, option: /^20$/ },
  { match: /print\(add\(3, 4\)\)/i, option: /^None$/ },
  { match: /all_even\(\[2, 4, 5, 8\]\)/i, option: /returns True on the first even number/i },
];

function getCodeForPrompt(prompt: string): string {
  if (/inclusive/i.test(prompt)) {
    return "a, b = map(int, input().split())\nprint(sum(range(a, b + 1)))\n";
  }
  if (/find_min/i.test(prompt)) {
    return (
      "def find_min(nums):\n    low = nums[0]\n    for x in nums[1:]:\n" +
      "        if x < low:\n            low = x\n    return low\n" +
      "print(find_min([int(x) for x in input().split()]))\n"
    );
  }
  if (/adjacent strictly increasing/i.test(prompt)) {
    return (
      "nums = [int(x) for x in input().split()]\n" +
      "print(sum(1 for i in range(len(nums) - 1) if nums[i + 1] > nums[i]))\n"
    );
  }
  return (
    "nums = [int(x) for x in input().split()]\n" +
    "best = nums[0]\nfor x in nums[1:]:\n    if x > best:\n        best = x\nprint(best)\n"
  );
}

test.describe("Phase 5 Complete Adaptive Learning, Diagnostic, Lesson & Skill Graph E2E", () => {
  test("Login -> Onboarding -> 8-Domain Adaptive Diagnostic (with Judge0) -> Track Recommendation -> Beginner Lesson -> Guided Judge0 Practice -> Skill Graph Update -> Next Recommendation + Responsive", async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);

    const suffix = Date.now().toString(36);
    const email = `e2e-p5-${suffix}@thinkfirst.test`;
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
        data: { full_name: "Phase5 E2E Learner" },
      },
    });
    expect(signup.ok()).toBeTruthy();

    // 2. Login -> Complete Smart Onboarding -> Arrive at Adaptive Learning Dashboard
    await page.setViewportSize({ width: 1280, height: 860 });
    await page.goto("/login");
    await page.getByLabel(/Email address/i).fill(email);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();

    await page.waitForURL("**/student/onboarding");
    await page.getByLabel(/Full name/i).fill("Phase5 E2E Learner");
    await page
      .getByRole("button", {
        name: /Start My Learning Journey|Complete onboarding/i,
      })
      .click();
    await page.waitForURL("**/student");

    await expect(
      page.getByText(/Student Learning Workspace|Adaptive Learning Dashboard/i),
    ).toBeVisible();
    await expect(
      page.getByText(/Prerequisite-Aware Skill Graph/i),
    ).toBeVisible();
    await expect(page.getByText(/Four Learning Tracks/i)).toBeVisible();

    // 3. Open 8-Domain Adaptive Diagnostic from Dashboard Recommendation
    await page
      .getByRole("link", { name: /Start 8-Domain Diagnostic/i })
      .click();
    await page.waitForURL("**/student/diagnostic");

    await page
      .getByRole("button", { name: /Start Adaptive Diagnostic/i })
      .click();

    // Answer every adaptive question (MCQs + real Judge0 stretch execution checks) until completed
    for (let step = 0; step < 15; step++) {
      const doneVisible = await page
        .getByText(/Diagnostic Completed — Evidence-Based Track Placement/i)
        .isVisible();
      if (doneVisible) break;

      const heading = page.locator("h2").first();
      await expect(heading).toBeVisible({ timeout: 20_000 });
      const promptText = (await heading.textContent()) || "";

      const isCodeExec = await page
        .getByText("Real Judge0 Execution Check", { exact: true })
        .isVisible();

      if (isCodeExec) {
        await expect(page.locator(".monaco-editor").first()).toBeVisible({
          timeout: 25_000,
        });
        const solutionCode = getCodeForPrompt(promptText);
        await page.evaluate((codeStr) => {
          const win = window as unknown as {
            monaco?: {
              editor: {
                getModels: () => Array<{ setValue: (v: string) => void }>;
              };
            };
          };
          const models = win.monaco?.editor.getModels() ?? [];
          if (models.length > 0) {
            models[models.length - 1].setValue(codeStr);
          }
        }, solutionCode);
      } else {
        // Deliberately pick a wrong option on conditions to trigger an adaptive foundation follow-up
        const matched = CORRECT_BY_TEXT.find((item) =>
          item.match.test(promptText),
        );
        if (/If `score = 90`/i.test(promptText)) {
          await page.getByLabel(/^Nothing$/).click();
        } else if (matched) {
          await page.getByLabel(matched.option).first().click();
        } else {
          await page.locator('input[type="radio"]').first().click();
        }
      }

      await Promise.all([
        page.waitForResponse(
          (resp) =>
            resp.url().includes("/diagnostics/sessions/") &&
            resp.url().endsWith("/answers") &&
            resp.status() === 200,
          { timeout: 45_000 },
        ),
        page.getByRole("button", { name: /Submit Answer/i }).click(),
      ]);
    }

    // 4. Verify Evidence-Based Track Placement & 8-Domain Summary
    await expect(
      page.getByText(/Diagnostic Completed — Evidence-Based Track Placement/i),
    ).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/Recommended Track:/i)).toBeVisible();

    // 5. Navigate to Beginner Python Lessons -> Open Lesson 1 (`intro-to-programming`)
    await page
      .getByRole("link", { name: /Start Beginner Python Lessons/i })
      .click();
    await page.waitForURL("**/student/lessons");
    await expect(
      page.getByText(/Introduction to Programming & Python Execution/i),
    ).toBeVisible();

    const firstLessonCard = page
      .locator("article")
      .filter({ hasText: "Introduction to Programming & Python Execution" });
    await firstLessonCard
      .getByRole("link", { name: /Open Lesson & Practice/i })
      .click();
    await page.waitForURL("**/student/lessons/intro-to-programming");

    // Verify Bangla toggle works smoothly
    await page.getByRole("button", { name: "বাংলা" }).click();
    await expect(page.getByText(/প্রোগ্রামিং পরিচিতি/i)).toBeVisible();
    await page.getByRole("button", { name: "English" }).click();

    // Mark reading complete -> then solve guided exercise on REAL Judge0!
    await page
      .getByRole("button", { name: /Mark Reading Complete/i })
      .click();
    await expect(
      page.getByRole("button", { name: /Reading Completed/i }),
    ).toBeVisible({ timeout: 15_000 });

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

    await page
      .getByRole("button", { name: /Run Guided Exercise/i })
      .click();
    await expect(
      page.getByText(/Lesson Completed! Guided Exercise Passed/i),
    ).toBeVisible({ timeout: 45_000 });

    // 6. Return to Dashboard -> Verify Updated Skill Graph, Completed Lesson & Next Recommendation
    await page
      .getByRole("link", {
        name: /View Updated Skill Graph & Next Recommendation/i,
      })
      .click();
    await page.waitForURL("**/student");

    await expect(page.getByText(/^1 \/ (8|24)$/)).toBeVisible();
    await expect(page.getByText(/Recommended Next Steps/i)).toBeVisible();
    await expect(page.getByText(/Backed by diagnostic evidence/i)).toBeVisible();

    // 7. Responsive Zero Horizontal Overflow Check across Desktop (1280px), Tablet (768px), Mobile (390px)
    for (const [width, height] of [
      [1280, 860],
      [768, 1024],
      [390, 844],
    ] as const) {
      await page.setViewportSize({ width, height });
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth + 1,
      );
      expect(overflow).toBeFalsy();
    }
  });
});
