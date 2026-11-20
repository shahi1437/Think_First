# ADR-009: Advanced Admin Studio, Curriculum Validation Engine & Protected Content Governance

**Status:** Accepted  
**Date:** 2026-11-20  
**Phase:** Phase 8  

## Context
CodeMentor AI needed a full curriculum and assessment governance console so verified Administrators can author, Judge0-validate, review, reject with feedback, approve, publish, compare versions, and archive coding/debugging problems, bilingual lessons, diagnostic challenges, and RAG knowledge documents without breaking historical teacher assignments or committing private answer keys into public Git.

## Decision
1. **Complete Lifecycle & Immutable Versioning (`Draft → Validated → In Review → Approved → Published → Archived`):**
   - Editing a `published` problem automatically creates `version_number + 1` in `draft`, leaving previously published versions pinned by `assignment_problem_links.problem_version_id` and `submissions.problem_version_id` intact.
   - `reject` returns non-published candidate versions back to `draft` with mandatory reviewer feedback in `content_reviews`.
   - `archive` removes a problem from student Problem Bank discovery while retaining historical versions for active classroom assignments (`assigned_courses_count`).
2. **Isolated Real Validation Engine (`ProblemService.validate_problem`, `AdminCurriculumService`):**
   - Runs non-executing Python AST syntax checks (`ast.parse`) and test-suite quality checks (contradictory inputs/outputs, duplicate pairs, constant-output suites).
   - Executes all public & hidden test cases inside isolated **Judge0 CE** workers against the private reference solution, plus verifies that debugging `buggy_starter_code` genuinely fails and classifies its observed failure category.
   - Records every validation run in `curriculum_validations` (Admin-only RLS).
3. **Public Repository Hygiene & Protected Deployment Content:**
   - Public seeds (`supabase/seed/004_phase8_curriculum_skills.sql`) store only Skill Graph nodes, prerequisites, and track metadata.
   - Protected curriculum bundles (`*.local.json`, excluded via `.gitignore`) are validated through Judge0 CE using `backend/scripts/import_curriculum_bundle.py` or `POST /api/v1/admin/learning/import-bundle`.

## Consequences
- Zero unvalidated coding problems can reach `published`.
- Zero hidden tests or production reference solutions are leaked in public Git history or student APIs.
- Intermediate (8 lessons, 6 problems) and Advanced (8 lessons, 6 problems, stretch diagnostics) expand the platform across all 4 learner tracks.
