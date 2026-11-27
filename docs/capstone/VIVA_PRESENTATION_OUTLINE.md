# CodeMentor AI (Think_First) — Capstone Thesis & Viva Presentation Outline

1. **Title & Motivation:** *Think First. Code Better.* — Why standard LLM coding chatbots erode debugging reasoning through instant answer leakage, and how evidence-driven Socratic tutoring solves it.
2. **Research Gap & Design Principles:** Contrast ungrounded LLM wrappers vs CodeMentor AI's 5 invariants (Judge0 sandboxed truth, owned ML diagnosis, approved-only RAG, bounded Socratic progression, independent transfer verification).
3. **System Architecture:** Modular Monolith (Next.js 16 + FastAPI + Supabase PostgreSQL/`pgvector` + Judge0 CE + Gemini) with asymmetric JWKS + DB RBAC + `FORCE RLS` (`57/57` tables).
4. **Isolated Execution & Security Model:** Why untrusted student code runs strictly inside Judge0 (`network=false`), how hidden tests & reference solutions stay isolated from browsers, and public vs private curriculum separation.
5. **Owned ML Error Classifier (`error-clf-v1.0.0`):** `309` execution-validated samples across `42` families, `StratifiedGroupKFold` (`0` family leakage), `0.7196` Macro F1 vs `0.5945` rule baseline, uncertainty flagging (`<0.55` / margin `<0.12`).
6. **Verified `pgvector` RAG & Bounded Gemini Mentor:** Semantic chunking over approved docs only (`Hit@1 = 1.0000`, `MRR = 1.0000`, `1.0000` OOD rejection), prompt-injection + solution-leakage guards, EN/BN bilingual guidance.
7. **Adaptive Curriculum & Skill Graph:** 4 learner tracks, 24 bilingual lessons, 8-domain adaptive diagnostic, 18-node prerequisite DAG, evidence states (`unseen -> introduced -> guided -> independent -> retained`).
8. **Learning DNA, Daily Plan & Spaced Retention:** 6-axis longitudinal profile, deterministic study-budget planner, and 24-hour spaced retention enforcement.
9. **Classroom Ecosystem & Admin Governance:** Teacher courses/invitations, pinned assignment grading loop, Admin Judge0 validation engine & audit trail.
10. **Quality Assurance & Verification:** Summary of `ruff`, `mypy`, `51+` pytest, `ml/tests`, `25` Vitest, `6/6` Playwright E2E, `npm audit` (`0` vulnerabilities), and disposable DB restore verification.
11. **Live System Demonstration:** Concise walkthrough following `DEMO_SCRIPTS.md`.
12. **Limitations, Ethics & Future Work:** Single-process rate-limiter note, Judge0 VM requirement, pending IRB/user-study cohort protocol, multi-language expansion.

## Key Examiner Viva Q&A Notes
- **Q: Why train your own scikit-learn classifier alongside Gemini?** Deterministic latency, calibrated top-k probability & low-confidence transparency (`error-clf-v1.0.0`), zero hallucinated error labels, and graceful functioning even when external LLM APIs fail or time out.
- **Q: How do you prevent students from gaming mastery using hints?** Skill Graph mastery requires passing an **unseen Transfer Challenge with 0 hints** (`verification_attempts`) and delayed 24-hour retention verification—passing coached hints alone stops at `guided`.
- **Q: How do you ensure hidden test cases or Gemini keys never reach the browser?** `problem_reference_solutions` and `test_cases` hidden I/O are protected by DB RLS + backend projection schemas, and `LLM_API_KEY` lives strictly inside backend server environment variables.
