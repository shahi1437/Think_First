import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "@playwright/test";

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const BACKEND_PYTHON = path.join(
  REPO_ROOT,
  "backend",
  ".venv",
  "Scripts",
  "python.exe",
);
const BOOTSTRAP_SCRIPT = path.join(
  REPO_ROOT,
  "backend",
  "scripts",
  "bootstrap_first_admin.py",
);

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8100";

async function signInViaSupabaseToken(
  request: import("@playwright/test").APIRequestContext,
  email: string,
  password: string,
): Promise<string> {
  const res = await request.post(
    `${SUPABASE_URL}/auth/v1/token?grant_type=password`,
    {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      data: { email, password },
    },
  );
  expect(res.ok()).toBeTruthy();
  const payload = (await res.json()) as { access_token: string };
  return payload.access_token;
}

test.describe("Think_First Role Portals, Homepage, Registration & Security Verification", () => {
  test("verifies homepage, registration, 3-role login portals, cross-role isolation, API/RLS security, session refresh & logout", async ({
    browser,
    request,
  }) => {
    test.setTimeout(240_000);

    const suffix = Date.now().toString(36);
    const studentEmail = `qa-stu-${suffix}@thinkfirst.test`;
    const student2Email = `qa-stu2-${suffix}@thinkfirst.test`;
    const teacherEmail = `qa-tch-${suffix}@thinkfirst.test`;
    const teacher2Email = `qa-tch2-${suffix}@thinkfirst.test`;
    const adminEmail = `qa-adm-${suffix}@thinkfirst.test`;
    const password = "QaSecurePassword123!";

    // Provision real test users via Supabase Auth (each starts with ONLY student role)
    for (const [email, name] of [
      [student2Email, "QA Student Two"],
      [teacherEmail, "QA Teacher One"],
      [teacher2Email, "QA Teacher Two"],
      [adminEmail, "QA Admin"],
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

    // Bootstrap Admin role for adminEmail
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

    const adminToken = await signInViaSupabaseToken(
      request,
      adminEmail,
      password,
    );
    const student2Token = await signInViaSupabaseToken(
      request,
      student2Email,
      password,
    );
    const teacherToken = await signInViaSupabaseToken(
      request,
      teacherEmail,
      password,
    );
    const teacher2Token = await signInViaSupabaseToken(
      request,
      teacher2Email,
      password,
    );

    // Admin grants Teacher role to teacherEmail & teacher2Email via real Admin API
    const usersListRes = await request.get(
      `${API_BASE_URL}/api/v1/admin/users?q=${encodeURIComponent(suffix)}&limit=20`,
      { headers: { Authorization: `Bearer ${adminToken}` } },
    );
    expect(usersListRes.ok()).toBeTruthy();
    const usersData = (await usersListRes.json()) as {
      items: Array<{ id: string; email: string }>;
    };
    const teacher1Id = usersData.items.find((u) => u.email === teacherEmail)?.id;
    const teacher2Id = usersData.items.find(
      (u) => u.email === teacher2Email,
    )?.id;
    const student2Id = usersData.items.find(
      (u) => u.email === student2Email,
    )?.id;
    expect(teacher1Id).toBeTruthy();
    expect(teacher2Id).toBeTruthy();
    expect(student2Id).toBeTruthy();

    for (const tid of [teacher1Id!, teacher2Id!]) {
      const grantRes = await request.post(
        `${API_BASE_URL}/api/v1/admin/users/${tid}/roles`,
        {
          headers: { Authorization: `Bearer ${adminToken}` },
          data: { role: "teacher" },
        },
      );
      expect(grantRes.ok()).toBeTruthy();
    }

    // Teacher 2 creates a private class so we can verify Teacher 1 is denied access to it (Case 15)
    const createCourseRes = await request.post(
      `${API_BASE_URL}/api/v1/teacher/classes`,
      {
        headers: { Authorization: `Bearer ${teacher2Token}` },
        data: {
          code: `CS-${suffix.slice(-4).toUpperCase()}`,
          title: "Private Teacher 2 Section",
          description: "Isolated section",
          term: "Fall 2026",
          enrollment_policy: "open_with_code",
          allow_student_leave: true,
        },
      },
    );
    expect(createCourseRes.status()).toBe(201);
    const teacher2Course = (await createCourseRes.json()) as { id: string };

    // Case 12: Unauthenticated access to protected routes redirects to role login pages
    const anonContext = await browser.newContext();
    const anonPage = await anonContext.newPage();

    await anonPage.goto("/");
    await expect(
      anonPage.getByRole("link", { name: "STUDENT LOGIN", exact: true }),
    ).toBeVisible();
    await expect(
      anonPage.getByRole("link", { name: "TEACHER LOGIN", exact: true }),
    ).toBeVisible();
    await expect(
      anonPage.getByRole("link", { name: "ADMIN LOGIN", exact: true }),
    ).toBeVisible();
    await expect(
      anonPage.getByText(/Platform Connectivity Check/i),
    ).toHaveCount(0);
    await expect(anonPage.getByText(/Backend API unreachable/i)).toHaveCount(0);

    await anonPage.goto("/student");
    await anonPage.waitForURL("**/login/student**");
    await anonPage.goto("/teacher");
    await anonPage.waitForURL("**/login/teacher**");
    await anonPage.goto("/admin");
    await anonPage.waitForURL("**/login/admin**");

    // Case 18: Student registration via /register UI
    await anonPage.goto("/register");
    await anonPage.getByLabel(/Full name/i).fill("QA Student One");
    await anonPage.getByLabel(/Email address/i).fill(studentEmail);
    await anonPage.locator("#reg-password").fill(password);
    await anonPage.locator("#reg-confirm").fill(password);
    await anonPage
      .getByRole("button", { name: /Create Student Account/i })
      .click();
    await expect(
      anonPage.getByText(
        /Verify your email before signing in|Student account ready/i,
      ),
    ).toBeVisible({ timeout: 20_000 });
    await anonContext.close();

    // Sign in as Student 1 through /login/student (Case 1 + 4 + 5 + 9 + 10 + 16 + 17)
    const studentCtx = await browser.newContext();
    const studentPage = await studentCtx.newPage();

    // Case 4: Student credentials via Teacher Login -> Denied
    await studentPage.goto("/login/teacher");
    await studentPage.getByLabel(/Email address/i).fill(studentEmail);
    await studentPage.getByLabel(/Password/i).fill(password);
    await studentPage.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      studentPage.getByRole("alert").filter({ hasText: /does not have Teacher/i }),
    ).toBeVisible({ timeout: 15_000 });

    // Case 5: Student credentials via Admin Login -> Denied
    await studentPage.goto("/login/admin");
    await studentPage.getByLabel(/Email address/i).fill(studentEmail);
    await studentPage.getByLabel(/Password/i).fill(password);
    await studentPage.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      studentPage.getByRole("alert").filter({ hasText: /does not have Admin/i }),
    ).toBeVisible({ timeout: 15_000 });

    // Case 1: Student credentials via Student Login -> Onboarding -> Student Dashboard
    await studentPage.goto("/login/student");
    await studentPage.getByLabel(/Email address/i).fill(studentEmail);
    await studentPage.getByLabel(/Password/i).fill(password);
    await studentPage.getByRole("button", { name: /Sign in/i }).click();
    await studentPage.waitForURL("**/student/onboarding", { timeout: 25_000 });
    await studentPage.getByLabel(/Full name/i).fill("QA Student One");
    await studentPage
      .getByRole("button", {
        name: /Start My Learning Journey|Complete onboarding/i,
      })
      .click();
    await studentPage.waitForURL("**/student", { timeout: 25_000 });
    await expect(
      studentPage.getByRole("heading", { name: /Welcome back/i }),
    ).toBeVisible();

    // Case 17: Session refresh preserves identity & role
    await studentPage.reload();
    await expect(studentPage).toHaveURL(/\/student$/);
    await expect(
      studentPage.getByRole("heading", { name: /Welcome back/i }),
    ).toBeVisible();

    // Case 9 & 10: Student manually opens /admin & /teacher -> Access denied
    await studentPage.goto("/admin");
    await studentPage.waitForURL("**/student?error=forbidden", {
      timeout: 20_000,
    });
    await expect(
      studentPage.getByRole("alert").filter({ hasText: /Access denied/i }),
    ).toBeVisible();

    await studentPage.goto("/teacher");
    await studentPage.waitForURL("**/student?error=forbidden", {
      timeout: 20_000,
    });

    // Mobile responsiveness check on /student
    await studentPage.setViewportSize({ width: 390, height: 844 });
    const hasOverflow = await studentPage.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    );
    expect(hasOverflow).toBe(false);
    await studentPage.setViewportSize({ width: 1280, height: 800 });

    // Case 16: Logout removes access to protected sessions
    await studentPage.getByRole("button", { name: /Sign out/i }).click();
    await studentPage.waitForURL("**/login", { timeout: 20_000 });
    await studentPage.goto("/student");
    await studentPage.waitForURL("**/login/student**", { timeout: 20_000 });
    await studentCtx.close();

    // Teacher portal & negative tests (Case 2 + 6 + 7 + 11 + 17)
    const teacherCtx = await browser.newContext();
    const teacherPage = await teacherCtx.newPage();

    // Case 6: Teacher credentials via Student Login -> No silent wrong-role login
    await teacherPage.goto("/login/student");
    await teacherPage.getByLabel(/Email address/i).fill(teacherEmail);
    await teacherPage.getByLabel(/Password/i).fill(password);
    await teacherPage.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      teacherPage.getByRole("alert").filter({ hasText: /does not have Student/i }),
    ).toBeVisible({ timeout: 15_000 });

    // Case 7: Teacher credentials via Admin Login -> Denied
    await teacherPage.goto("/login/admin");
    await teacherPage.getByLabel(/Email address/i).fill(teacherEmail);
    await teacherPage.getByLabel(/Password/i).fill(password);
    await teacherPage.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      teacherPage.getByRole("alert").filter({ hasText: /does not have Admin/i }),
    ).toBeVisible({ timeout: 15_000 });

    // Case 2: Teacher credentials via Teacher Login -> Teacher Dashboard
    await teacherPage.goto("/login/teacher");
    await teacherPage.getByLabel(/Email address/i).fill(teacherEmail);
    await teacherPage.getByLabel(/Password/i).fill(password);
    await teacherPage.getByRole("button", { name: /Sign in/i }).click();
    await teacherPage.waitForURL("**/teacher", { timeout: 25_000 });
    await expect(
      teacherPage.getByRole("heading", { name: /Welcome,/i }),
    ).toBeVisible();

    // Case 17 (Teacher): Session refresh preserves Teacher Dashboard
    await teacherPage.reload();
    await expect(teacherPage).toHaveURL(/\/teacher$/);

    // Case 11: Teacher manually opens /admin -> Access denied
    await teacherPage.goto("/admin");
    await teacherPage.waitForURL("**/teacher?error=forbidden", {
      timeout: 20_000,
    });
    await expect(
      teacherPage.getByRole("alert").filter({ hasText: /Access denied/i }),
    ).toBeVisible();
    await teacherCtx.close();

    // Admin portal & negative tests (Case 3 + 8 + 17)
    const adminCtx = await browser.newContext();
    const adminPage = await adminCtx.newPage();

    // Case 8: Admin credentials via Student Login -> No silent wrong-role login
    await adminPage.goto("/login/student");
    await adminPage.getByLabel(/Email address/i).fill(adminEmail);
    await adminPage.getByLabel(/Password/i).fill(password);
    await adminPage.getByRole("button", { name: /Sign in/i }).click();
    await expect(
      adminPage.getByRole("alert").filter({ hasText: /does not have Student/i }),
    ).toBeVisible({ timeout: 15_000 });

    // Case 3: Admin credentials via Admin Login -> Admin Dashboard
    await adminPage.goto("/login/admin");
    await adminPage.getByLabel(/Email address/i).fill(adminEmail);
    await adminPage.getByLabel(/Password/i).fill(password);
    await adminPage.getByRole("button", { name: /Sign in/i }).click();
    await adminPage.waitForURL("**/admin", { timeout: 25_000 });
    await expect(
      adminPage.getByText(/Platform Connectivity Check/i),
    ).toBeVisible({ timeout: 15_000 });

    // Case 17 (Admin): Session refresh preserves Admin Dashboard
    await adminPage.reload();
    await expect(adminPage).toHaveURL(/\/admin$/);
    await adminCtx.close();

    // API & RLS isolation checks (Cases 13, 14, 15)
    const student1Token = await signInViaSupabaseToken(
      request,
      studentEmail,
      password,
    );

    // Case 13: Student requests Admin API -> 403
    const stuAdminApi = await request.get(
      `${API_BASE_URL}/api/v1/admin/users`,
      { headers: { Authorization: `Bearer ${student1Token}` } },
    );
    expect(stuAdminApi.status()).toBe(403);

    // Case 14: Student 1 cannot read Student 2's profile via Supabase PostgREST RLS
    const rlsOtherProfile = await request.get(
      `${SUPABASE_URL}/rest/v1/profiles?id=eq.${student2Id}`,
      {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${student1Token}`,
        },
      },
    );
    expect(rlsOtherProfile.ok()).toBeTruthy();
    expect(await rlsOtherProfile.json()).toEqual([]);

    // Also verify Student 2 cannot query Student 1's preferences via PostgREST RLS
    const rlsOtherPrefs = await request.get(
      `${SUPABASE_URL}/rest/v1/user_preferences?select=user_id`,
      {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${student2Token}`,
        },
      },
    );
    expect(rlsOtherPrefs.ok()).toBeTruthy();
    const visiblePrefRows = (await rlsOtherPrefs.json()) as Array<{
      user_id: string;
    }>;
    expect(visiblePrefRows.every((r) => r.user_id === student2Id)).toBe(true);

    // Case 15: Teacher 1 cannot access Teacher 2's class -> 403
    const crossTeacherCourse = await request.get(
      `${API_BASE_URL}/api/v1/teacher/classes/${teacher2Course.id}`,
      { headers: { Authorization: `Bearer ${teacherToken}` } },
    );
    expect(crossTeacherCourse.status()).toBe(403);
  });
});
