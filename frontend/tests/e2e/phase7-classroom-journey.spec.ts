import { execSync } from "node:child_process";
import { expect, test } from "@playwright/test";

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";

test.describe("Phase 7 Complete Teacher Classroom, Assignment, Judge0 & Grading Journey", () => {
  test("Admin authorizes Teacher -> Teacher creates Class & Invite Code -> Publishes Assignment -> Student Joins Class -> Monaco Judge0 Solve -> Teacher Requests Revision -> Student Resubmits -> Teacher Publishes Grade -> Student Views Grade + Responsive UI", async ({
    browser,
    request,
  }) => {
    test.setTimeout(180_000);

    const suffix = Date.now().toString(36);
    const teacherEmail = `e2e-p7-teacher-${suffix}@thinkfirst.test`;
    const studentEmail = `e2e-p7-student-${suffix}@thinkfirst.test`;
    const password = "TestPassword123!";

    // 1. Provision Teacher & Student via local Supabase Auth
    const teacherSignup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email: teacherEmail,
        password,
        data: { full_name: "Prof. Phase7 Teacher" },
      },
    });
    expect(teacherSignup.ok()).toBeTruthy();
    const teacherUserId = (
      (await teacherSignup.json()) as { user: { id: string } }
    ).user.id;

    const studentSignup = await request.post(`${SUPABASE_URL}/auth/v1/signup`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: {
        email: studentEmail,
        password,
        data: { full_name: "Phase7 Student" },
      },
    });
    expect(studentSignup.ok()).toBeTruthy();

    // Grant authoritative DB-backed 'teacher' role to teacherUserId
    execSync(
      `docker exec supabase_db_think-first-codementor psql -U postgres -d postgres -c "INSERT INTO public.user_roles (user_id, role, granted_by) VALUES ('${teacherUserId}', 'teacher', '${teacherUserId}') ON CONFLICT DO NOTHING;"`,
    );

    // 2. Teacher logs in, creates Class, and reads generated Invite Code
    const teacherCtx = await browser.newContext({
      viewport: { width: 1280, height: 860 },
    });
    const teacherPage = await teacherCtx.newPage();

    await teacherPage.goto("/login");
    await teacherPage.getByLabel(/Email address/i).fill(teacherEmail);
    await teacherPage.getByLabel(/Password/i).fill(password);
    await teacherPage.getByRole("button", { name: /Sign in/i }).click();
    await teacherPage.waitForURL("**/teacher", { timeout: 25_000 });
    await teacherPage.goto("/teacher/classes");

    const classCode = `CSE-${suffix.slice(-4).toUpperCase()}`;
    await teacherPage.getByLabel(/Course Code/i).fill(classCode);
    await teacherPage
      .getByLabel(/Class Title/i)
      .fill("Python Systems & Debugging");
    await teacherPage.getByRole("button", { name: /Create Class/i }).click();

    await expect(teacherPage.getByText(classCode).first()).toBeVisible({
      timeout: 15_000,
    });
    await teacherPage
      .getByRole("link", { name: /Manage Class & Roster/i })
      .first()
      .click();
    await teacherPage.waitForURL("**/teacher/classes/**");

    const inviteCodeEl = teacherPage.getByTestId("invite-code-preview").first();
    await expect(inviteCodeEl).toBeVisible();
    const inviteCode = ((await inviteCodeEl.textContent()) ?? "").trim();
    expect(inviteCode).toMatch(/^CM-[A-Z0-9]{5}-[A-Z0-9]{5}$/);

    // 3. Teacher creates & publishes Assignment with `Debug: Inclusive Range Sum`
    await teacherPage.goto("/teacher/assignments");
    await teacherPage
      .getByLabel(/Assignment Title/i)
      .fill("Assignment 1: Inclusive Range Bug");
    await teacherPage
      .getByLabel(/Instructions/i)
      .fill("Fix the off-by-one range boundary and verify on Judge0.");
    await teacherPage
      .getByRole("button", { name: /Publish Assignment Now/i })
      .click();

    await expect(
      teacherPage.getByText("Assignment 1: Inclusive Range Bug").first(),
    ).toBeVisible({ timeout: 15_000 });

    // 4. Student logs in, completes onboarding, joins class with Invite Code, and opens Assignment in Monaco
    const studentCtx = await browser.newContext({
      viewport: { width: 1280, height: 860 },
    });
    const studentPage = await studentCtx.newPage();

    await studentPage.goto("/login");
    await studentPage.getByLabel(/Email address/i).fill(studentEmail);
    await studentPage.getByLabel(/Password/i).fill(password);
    await studentPage.getByRole("button", { name: /Sign in/i }).click();

    await studentPage.waitForURL("**/student/onboarding");
    await studentPage.getByLabel(/Full name/i).fill("Phase7 Student");
    await studentPage
      .getByRole("button", { name: /Complete onboarding/i })
      .click();
    await studentPage.waitForURL("**/student");

    await studentPage.getByRole("link", { name: /^Classes$/i }).first().click();
    await studentPage.waitForURL("**/student/classes");
    await studentPage
      .getByLabel(/Class invitation code/i)
      .fill(inviteCode);
    await studentPage.getByRole("button", { name: /Join Class/i }).click();

    await expect(
      studentPage.getByText("Python Systems & Debugging"),
    ).toBeVisible({ timeout: 15_000 });

    await studentPage
      .getByRole("link", { name: /My Assignments/i })
      .first()
      .click();
    await studentPage.waitForURL("**/student/assignments");
    await expect(
      studentPage.getByText("Assignment 1: Inclusive Range Bug"),
    ).toBeVisible();
    await studentPage
      .getByRole("link", { name: /Open Assignment Workspace/i })
      .first()
      .click();
    await studentPage.waitForURL("**/student/assignments/**");

    // Wait for Monaco Editor or fallback Code editor textarea to mount, fix buggy starter code, and submit to Judge0
    await expect(
      studentPage
        .locator('.monaco-editor, textarea[aria-label="Code editor"]')
        .first(),
    ).toBeVisible({
      timeout: 25_000,
    });
    const fallbackTextarea = studentPage.getByLabel("Code editor");
    if (await fallbackTextarea.isVisible()) {
      const currentCode = await fallbackTextarea.inputValue();
      await fallbackTextarea.fill(
        currentCode.replace("range(a, b)", "range(a, b + 1)"),
      );
    } else {
      await studentPage.evaluate(() => {
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
          const cur = models[models.length - 1].getValue();
          models[models.length - 1].setValue(
            cur.replace("range(a, b)", "range(a, b + 1)"),
          );
        }
      });
    }

    await studentPage
      .getByLabel(/Notes \/ Explanation for Teacher/i)
      .fill("Fixed range(a, b + 1) to include upper bound b.");
    await studentPage
      .getByRole("button", { name: /Submit Assignment to Judge0/i })
      .click();

    await expect(
      studentPage.getByText(/Assignment Attempt #1 Recorded/i),
    ).toBeVisible({ timeout: 45_000 });

    // 5. Teacher reviews submission, requests revision -> Student resubmits -> Teacher publishes final grade
    await teacherPage.reload();
    await teacherPage
      .getByRole("link", { name: /Review & Grade/i })
      .first()
      .click();
    await teacherPage.waitForURL("**/teacher/assignments/**");

    await expect(teacherPage.getByText("Phase7 Student").first()).toBeVisible();
    await teacherPage.getByLabel(/Marks Awarded/i).fill("40");
    await teacherPage
      .getByLabel(/Written Teacher Feedback/i)
      .fill("Please add a brief comment above your loop and resubmit.");
    await teacherPage
      .getByRole("button", { name: /Request Revision/i })
      .click();
    await expect(teacherPage.getByText("revision_requested").first()).toBeVisible({
      timeout: 15_000,
    });

    // Student reloads, sees revision request feedback, and resubmits
    await studentPage.reload();
    await expect(
      studentPage.getByText(/Please add a brief comment above your loop/i),
    ).toBeVisible();
    await expect(
      studentPage
        .locator('.monaco-editor, textarea[aria-label="Code editor"]')
        .first(),
    ).toBeVisible({
      timeout: 25_000,
    });
    await studentPage
      .getByLabel(/Notes \/ Explanation for Teacher/i)
      .fill("Resubmitted after revision request.");
    await studentPage
      .getByRole("button", { name: /Submit Assignment to Judge0/i })
      .click();
    await expect(
      studentPage.getByText(/Assignment Attempt #2 Recorded/i),
    ).toBeVisible({ timeout: 45_000 });

    // Teacher publishes final grade (49 / 50)
    await teacherPage.reload();
    await teacherPage.getByLabel(/Marks Awarded/i).fill("49");
    await teacherPage
      .getByLabel(/Written Teacher Feedback/i)
      .fill("Great revision! All 5 Judge0 tests passed cleanly.");
    await teacherPage
      .getByRole("button", { name: /Publish Grade & Feedback/i })
      .click();
    await expect(teacherPage.getByText(/grade_published/i)).toBeVisible({
      timeout: 15_000,
    });

    // Student reloads and sees published grade 49 / 50 & teacher feedback
    await studentPage.reload();
    await expect(
      studentPage.getByText(/Instructor Grade \(published\): 49 \/ 50/i),
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      studentPage.getByText(/Great revision! All 5 Judge0 tests passed cleanly/i),
    ).toBeVisible();

    // 6. Teacher Dashboard reflects real aggregated data + responsive check across Desktop, Tablet, Mobile
    await teacherPage.goto("/teacher");
    await expect(
      teacherPage.getByText("Python Systems & Debugging").first(),
    ).toBeVisible();

    for (const [pageObj, routes] of [
      [teacherPage, ["/teacher", "/teacher/classes", "/teacher/assignments"]],
      [studentPage, ["/student/classes", "/student/assignments"]],
    ] as const) {
      for (const route of routes) {
        await pageObj.goto(route);
        for (const [width, height] of [
          [1280, 860],
          [768, 1024],
          [390, 844],
        ] as const) {
          await pageObj.setViewportSize({ width, height });
          const overflow = await pageObj.evaluate(
            () => document.documentElement.scrollWidth > window.innerWidth + 1,
          );
          expect(
            overflow,
            `Horizontal overflow on ${route} at ${width}px`,
          ).toBeFalsy();
        }
      }
    }

    await teacherCtx.close();
    await studentCtx.close();
  });
});
