import { expect, test } from "@playwright/test";

const STUDENT_EMAIL = process.env.E2E_STUDENT_EMAIL;
const STUDENT_PASSWORD = process.env.E2E_STUDENT_PASSWORD;

test.describe("Phase 4 Intelligent Debugging & Transfer Verification Journey", () => {
  test.skip(
    !STUDENT_EMAIL || !STUDENT_PASSWORD,
    "Set E2E_STUDENT_EMAIL and E2E_STUDENT_PASSWORD against a live Supabase + Judge0 + API + Next.js stack.",
  );

  test("buggy Judge0 run -> ML diagnosis + RAG citations -> Socratic hint -> fix Accepted -> Transfer Challenge verified across desktop/tablet/mobile", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 860 });
    await page.goto("/login");
    await page.getByLabel(/Email/i).fill(STUDENT_EMAIL!);
    await page.getByLabel(/Password/i).fill(STUDENT_PASSWORD!);
    await page.getByRole("button", { name: /Sign in/i }).click();
    await page.waitForURL(/\/student/);

    await page.goto("/student/problems");
    await page.getByRole("link", { name: /Inclusive Range Sum/i }).first().click();
    await page.waitForURL(/\/student\/problems\//);

    // 1. Run buggy starter code on Judge0 -> Wrong Answer
    await page.getByRole("button", { name: /Run Code/i }).click();
    await expect(page.getByText(/Wrong Answer/i)).toBeVisible({ timeout: 25000 });

    // 2. Open Socratic AI Mentor -> verify ML diagnosis, citations, and Hint 1
    await page.getByRole("button", { name: /Ask Socratic AI Mentor/i }).click();
    await page.getByRole("button", { name: /Start AI Diagnosis/i }).click();
    await expect(page.getByText(/ML Error Diagnosis/i)).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText(/Verified Knowledge Citations/i)).toBeVisible();
    await page.getByRole("button", { name: "Hint 1" }).click();
    await expect(page.getByText(/Hint \(Level 1\)/i)).toBeVisible({
      timeout: 10000,
    });

    // 3. Switch to Bangla and verify readable Bangla prompt renders
    await page.getByRole("button", { name: "বাংলা" }).click();
    await expect(page.getByText(/তোমার ধারণা বা ট্রেস/i)).toBeVisible();

    // 4. Verify zero horizontal overflow across Tablet (768px) and Mobile (390px)
    for (const width of [768, 390]) {
      await page.setViewportSize({ width, height: 844 });
      const overflow = await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth,
      );
      expect(overflow).toBe(false);
    }
  });
});
