# CodeMentor AI (Think_First) — Capstone Live Demonstration Scripts

## 1. Student Workflow Demonstration Script
1. **Landing & Onboarding (`/`, `/register`, `/student/onboarding`):**
   - Register a new student account, verify automatic assignment of `student` role only (no client privilege escalation), and complete onboarding preferences (language `en`/`bn`, goal, daily practice budget).
2. **Adaptive 8-Domain Diagnostic (`/student/diagnostic`):**
   - Start diagnostic session; answer MCQ tracing items and submit a Python check executed on real Judge0 CE.
   - Show evidence-based track recommendation (`Absolute Beginner`, `Basic University`, `Intermediate`, or `Advanced`) and prerequisite Skill Graph updates (`/student`).
3. **Bilingual Guided Lessons (`/student/lessons`):**
   - Toggle English / Bangla (`বাংলা`), mark reading complete (`introduced` state — not mastery!), and pass the guided coding exercise via Judge0 CE (`guided` state).
4. **Debugging, ML Classifier, RAG & Live Gemini Mentor (`/student/problems/[id]`):**
   - Open a debugging problem, enter a buggy change or run the starter bug in Monaco Editor via Judge0 CE.
   - Open the **AI Mentor** tab: show real `error-clf-v1.0.0` calibrated probabilities + uncertainty indicator, approved `pgvector` RAG citations, progressive Hint `1 -> 3` without solution leakage, and bilingual Bangla explanation (`provider_mode=live_llm`).
   - Fix the code, pass all public + hidden tests (hidden inputs/outputs remain masked), then solve the **Independent Transfer Challenge** (0 hints allowed) to earn verified Skill Graph mastery.
5. **Growth & Spaced Retention (`/student/dna`, `/student/daily-plan`, `/student/history`, `/student/retention`):**
   - Show 6-dimension Learning DNA snapshot, time-budgeted Adaptive Daily Plan regeneration, longitudinal History filters, and 24-hour Spaced Retention schedule gating.

## 2. Teacher Workflow Demonstration Script
1. **Teacher Portal (`/teacher`):** Sign in with Admin-authorized `teacher` account and inspect real aggregated class KPIs, pending grading queue, Judge0 verdicts, and misconception trends.
2. **Classroom & Invitation Code (`/teacher/classes`):** Create a course (`CSE-201`), generate a high-entropy SHA-256 hashed invitation code (`CM-XXXXX-XXXXX`), and confirm student enrollment.
3. **Assignment Creation & Judge0 Grading (`/teacher/assignments`):** Pin an Admin-published problem version to an assignment, let the student submit via Monaco + Judge0 CE, request a revision, accept resubmission, and publish the final grade + written feedback with immutable audit logging.

## 3. Admin Studio Demonstration Script
1. **Operations Health & Overview (`/admin`):** Show live DB problem/lesson/diagnostic/RAG counts alongside **Live Infrastructure & AI Operations Telemetry** (`postgresql`, `ml_classifier`, `judge0`, `socratic_llm`).
2. **Problem Governance Lifecycle (`/admin/problems`):** Author a new Python problem + public/hidden tests + reference solution -> run real Judge0 validation (`Draft -> Validated`) -> submit review -> approve -> publish -> confirm student Problem Bank visibility.
3. **Curriculum, Diagnostics & Audit (`/admin/curriculum`, `/admin/diagnostics`, `/admin/audit`):** Review 4-track lessons, stretch diagnostic questions, RAG document approvals, and immutable `audit_logs` + role management.
