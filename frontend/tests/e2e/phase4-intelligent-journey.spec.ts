import { expect, test } from "@playwright/test";

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

test.describe("Phase 4 Complete Live Intelligent Debugging & Transfer Verification Journey", () => {
  test("Student Login -> Debugging Problem -> Monaco -> Judge0 Error -> ML Diagnosis -> pgvector RAG -> Socratic Mentor (EN/BN) -> Fix Accepted -> Independent Transfer Verified -> Responsive UI", async ({
    page,
    request,
  }) => {
    test.setTimeout(150_000);

    const suffix = Date.now().toString(36);
    const email = `e2e-p4-${suffix}@thinkfirst.test`;
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
        data: { full_name: "Phase4 E2E Learner" },
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
    await page.getByLabel(/Full name/i).fill("Phase4 E2E Learner");
    await page.getByRole("button", { name: /Complete onboarding/i }).click();
    await page.waitForURL("**/student");

    // 3. Open Debugging Problem (`Debug: Inclusive Range Sum`)
    await page.getByRole("link", { name: /Problem Bank/i }).first().click();
    await page.waitForURL("**/student/problems");
    const debugCard = page
      .locator("article")
      .filter({ hasText: "Debug: Inclusive Range Sum" });
    await debugCard.getByRole("link", { name: /Open Debugger/i }).click();
    await page.waitForURL("**/student/problems/**");

    await expect(page.locator(".monaco-editor").first()).toBeVisible({
      timeout: 25_000,
    });

    // 4. Verify Transfer Check is initially LOCKED
    await page.getByRole("button", { name: /^Transfer Check$/i }).click();
    await expect(
      page.getByText(/Independent Transfer Verification \(Locked\)/i),
    ).toBeVisible();

    // 5. Run buggy starter code on real Judge0 -> Wrong Answer (0/2)
    await page.getByRole("button", { name: /Run Code/i }).click();
    await expect(page.getByText("0 / 2 tests passed")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText("Wrong Answer").first()).toBeVisible();

    // 6. Open Socratic AI Mentor -> Run real ML Diagnosis + pgvector RAG citations + Progressive Hint 1
    await page
      .getByRole("button", { name: /Ask Socratic AI Mentor/i })
      .click();
    await page.getByRole("button", { name: /Start AI Diagnosis/i }).click();

    await expect(page.getByText(/ML Error Diagnosis/i)).toBeVisible({
      timeout: 20_000,
    });
    await expect(
      page.getByText(/Loop Boundary Error/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Deterministic Socratic Fallback/i),
    ).toBeVisible();
    await expect(
      page.getByText(/Verified Knowledge Citations/i),
    ).toBeVisible();
    await expect(
      page.getByText(/Loops & Off-By-One Boundary Reasoning/i).first(),
    ).toBeVisible();

    await page.getByRole("button", { name: "Hint 1" }).click();
    await expect(page.getByText(/Hint \(Level 1\)/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/Progressive Hints \(1 \/ 3 used\)/i)).toBeVisible();

    // 7. Switch to Bangla and send a student reasoning turn -> verify Bangla Socratic reply
    await page.getByRole("button", { name: "বাংলা" }).click();
    await expect(page.getByText(/তোমার ধারণা বা ট্রেস/i)).toBeVisible();
    await page
      .locator("#mentor-student-reply")
      .fill("range(a, b) শেষ সংখ্যা b বাদ দিচ্ছে");
    await page.getByRole("button", { name: /^Send$/i }).click();
    await expect(page.getByText(/সবচেয়ে ছোট/i).first()).toBeVisible({
      timeout: 15_000,
    });

    // 8. Student fixes code in Monaco Editor and submits -> Real Judge0 Accepted (5/5)
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

    // 9. Transfer Challenge automatically unlocks -> Open Transfer Check & solve independently
    const transferTab = page.getByRole("button", {
      name: /Transfer Check \(Unlocked\)/i,
    });
    await expect(transferTab).toBeVisible({ timeout: 15_000 });
    await transferTab.click();

    await expect(
      page.getByText(/Transfer Challenge: Inclusive Step Range Sum/i),
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText(/Zero-Hint Independent Check \(0 hints\)/i),
    ).toBeVisible();

    // Wait for Transfer Monaco Editor model (2nd model mounted)
    await page.waitForFunction(() => {
      const win = window as unknown as {
        monaco?: { editor: { getModels: () => unknown[] } };
      };
      return (win.monaco?.editor.getModels().length ?? 0) >= 2;
    });

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
      const transferModel = models[models.length - 1];
      transferModel.setValue(
        [
          "def step_range_sum(start: int, end: int, step: int) -> int:",
          "    total = 0",
          "    for value in range(start, end + 1, step):",
          "        total += value",
          "    return total",
          "",
          'if __name__ == "__main__":',
          "    start, end, step = map(int, input().split())",
          "    print(step_range_sum(start, end, step))",
          "",
        ].join("\n"),
      );
    });

    await page
      .locator("#transfer-explanation")
      .fill(
        "Used range(start, end + 1, step) so end is included whenever it lands on the step.",
      );
    await page
      .getByRole("button", { name: /Submit Independent Verification/i })
      .click();

    // 10. Assert factual Judge0-backed Independent Verification persisted
    await expect(
      page.getByText(/Verified Independent Understanding/i),
    ).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/5 \/ 5 Judge0 tests/i)).toBeVisible();

    // 11. Reload page and verify persisted transfer outcome survives reload
    await page.reload();
    await page
      .getByRole("button", { name: /Transfer Check \(Unlocked\)/i })
      .click();
    await expect(
      page.getByText(/Verified Independent Understanding/i),
    ).toBeVisible({ timeout: 15_000 });

    // 12. Verify zero horizontal overflow across Desktop (1280px), Tablet (768px), and Mobile (390px)
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

    // Verify Mobile ARIA tabs including Mentor & Transfer
    await expect(page.getByRole("tab", { name: "Mentor" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Transfer" })).toBeVisible();
  });
});
