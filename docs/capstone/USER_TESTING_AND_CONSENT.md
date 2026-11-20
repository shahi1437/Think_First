# CodeMentor AI (Think_First) — Real User Testing Plan & Consent Materials

> **Study Status:** **PENDING** (Materials prepared; **no live human participant trials or empirical learning-gain data have been collected or claimed yet**.)

## 1. Study Objective & Ethical Guardrails
Evaluate usability, hint usefulness without answer leakage, bilingual (English/Bangla) comprehension, and independent transfer mastery among undergraduate CS/SWE students using CodeMentor AI, without fabricating metrics or coercive grading.

## 2. Proposed Cohort & Experimental Protocol (Pending Approval)
- **Target Sample:** Introductory and intermediate programming volunteers (`N = 20–30`, adult learners `>= 18` years, anonymized participant IDs `P01..P30`).
- **Session Structure (~60 minutes):**
  1. Informed Consent & Baseline Survey (zero-coding self-report vs actual diagnostic).
  2. 8-Domain Adaptive Diagnostic + 1 Guided Bilingual Lesson (`15 min`).
  3. 2 Debugging Problems with Judge0 + ML + Socratic Mentor (`25 min`).
  4. Unseen Independent Transfer Challenge with 0 AI hints (`15 min`).
  5. Post-Session Usability & NASA-TLX / SUS Feedback Survey (`5 min`).
- **Measured Objective Signals (from PostgreSQL `learning_events`):**
  - Time-to-diagnosis & resubmission count
  - Hint escalation depth (`level 1 -> 3`)
  - Independent Transfer pass rate (`verified_independent`) vs coached pass rate

## 3. Participant Informed Consent Template
- **Project Title:** CodeMentor AI (*Think First. Code Better.*) — Evidence-Based Adaptive Debugging Tutor
- **Voluntary Participation:** Participation is 100% voluntary; declining or withdrawing at any point carries zero academic penalty.
- **Data Privacy:** Only pseudonymous interaction logs, submitted code snippets, and survey responses are analyzed; real names/emails are excluded from thesis tables and publications.
- **Consent Checkboxes:**
  - [ ] I confirm I am 18 years or older and consent voluntarily.
  - [ ] I understand anonymized debugging attempts and survey ratings may appear in capstone reporting.
  - [ ] I understand I may withdraw my data before final dataset anonymization.
