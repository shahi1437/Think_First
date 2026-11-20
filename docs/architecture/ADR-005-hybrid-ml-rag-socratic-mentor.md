# ADR-005: Hybrid Own ML Error Classifier, Verified pgvector RAG, Bounded Socratic Mentor, and Independent Transfer Verification

- **Status:** Accepted (Phase 4)
- **Date:** 2026-11-20
- **Decision Makers:** CodeMentor AI Architecture Team

## Context

In Phase 4, CodeMentor AI transitions from a real Judge0 coding/debugging platform into an intelligent educational debugging mentor. Three architectural requirements guide this design:

1. **Academic & Pedagogical Honesty:** Do not disguise prompt-only chatbots as custom ML, do not fabricate mastery metrics, and do not hide fallback operation when no external LLM key is configured.
2. **Zero Leakage & Strict Safety:** Never leak private reference solutions or hidden Judge0 test cases into RAG corpora or LLM outputs; never trust student code, stderr, or messages as system instructions; enforce strict cross-student isolation via JWT + DB-backed RBAC + PostgreSQL `FORCE ROW LEVEL SECURITY`.
3. **Evidence-Grounded Learning Verification:** Prove genuine understanding after AI-guided debugging by unlocking a distinct unseen transfer problem with `max_hints_allowed = 0` evaluated on real Judge0.

## Decisions

### 1. Own Supervised ML Error Diagnosis Pipeline (`ml/`)
- Built an original, execution-validated Python mistake dataset (`ml/datasets/python_errors_v1.csv`) spanning 42 distinct program families across 8 error classes: `syntax_error`, `runtime_error`, `indexing_error`, `loop_boundary_error`, `condition_error`, `initialization_error`, `function_return_error`, and `logic_error`.
- Every candidate mutation is executed against its unit test suite in an isolated offline subprocess; passing mutations are rejected automatically.
- Feature engineering (`ml/preprocessing/features.py`) combines code tokens, AST structural signals (e.g., `ast_return_in_loop`, `ast_range_len_plus_1`, `ast_init_zero_in_max_min`, `ast_missing_return`), and execution evidence (`verdict`, exception class, actual vs expected output signals).
- Leakage prevention uses `StratifiedGroupKFold(n_splits=5)` grouped strictly by `program_family` (0 shared families between train and held-out test).
- Compares a deterministic `RuleBasedErrorClassifier` baseline against `TF-IDF + Logistic Regression` and `TF-IDF + Random Forest`, persisting the versioned artifact (`ml/artifacts/error_classifier_v1.joblib`) and evaluation report (`ml/evaluation/eval_report_v1.json`, `docs/ai/ml-evaluation-report.md`).
- Inference (`MLErrorClassifierService`) exposes top-3 probabilities and explicitly sets `is_low_confidence = True` with an `uncertainty_note` when top probability falls below `ML_LOW_CONFIDENCE_THRESHOLD` (default `0.55`).

### 2. Verified PostgreSQL `pgvector` RAG (`knowledge_documents`, `knowledge_chunks`)
- Curated 10 instructor-reviewable educational Python documents covering variables, conditionals, loops/boundaries, lists/indexing, functions/returns, syntax, runtime exceptions, logic tracing, strings/dictionaries, and edge-case test design.
- Stored in PostgreSQL with `pgvector` (`vector(256)` + HNSW `vector_cosine_ops` index) using heading-aware semantic chunking and a deterministic local 256-dim semantic embedder (`LocalSemanticEmbedder`).
- Retrieval strictly enforces `status = 'approved'` (enforced both in SQL repository queries and PostgreSQL `FORCE ROW LEVEL SECURITY`), applies topic/error-code metadata boost, filters below `RAG_SIMILARITY_THRESHOLD`, returns genuine source citations (`source_title`, `source_version`, `heading`, `similarity`, `excerpt`), and falls back transparently with zero fabricated citations when no approved chunk matches.

### 3. Bounded Stateful Socratic AI Mentor (`SocraticMentorService` + `SocraticLLMClient`)
- Implemented as an explicit bounded state machine (`awaiting_submission -> diagnosing -> asking_question -> awaiting_student_response -> giving_hint (L1..L3) -> awaiting_revision -> verifying -> completed | fallback`).
- Enforces:
  - Student ownership & Admin-only knowledge management.
  - Per-student mentor turn rate limit (`MENTOR_RATE_LIMIT_PER_MINUTE`).
  - Maximum 3 progressive hint levels on debugging problems, and **0 hints** (`TRANSFER_HINTS_DISABLED`) on linked independent transfer problems.
  - Bilingual English (`en`) and Bangla (`bn`) guidance adapted to onboarding learner level (`beginner`, `intermediate`, `advanced`).
  - Prompt-injection detection (`detect_prompt_injection`) and server-side full-solution leakage blocking (`contains_solution_leak` checking against the private reference solution without ever returning it to the client).
  - Explicit `provider_mode` (`"live_llm"` for configured OpenAI/Gemini/Ollama vs `"deterministic_fallback"` when unconfigured or on timeout/error).

### 4. Independent Transfer Verification (`VerificationService`)
- `verification_links` maps debugging problems to genuinely distinct unseen transfer problems (`debug-range-sum-off-by-one -> transfer-step-range-sum`; `debug-max-negative-init -> transfer-min-temperature`).
- Locked (`409 TRANSFER_LOCKED`) until the student has a persisted `accepted` Judge0 `submit` on the source debugging problem.
- Transfer submissions run through the real Judge0 `ExecutionService`, inspect real DB hint usage on the transfer problem, persist `verification_attempts` and `learning_events`, and report factual outcomes (`verified_independent` vs `attempted_not_verified`) without fabricated mastery scores.

## Consequences
- Every ML metric, RAG citation, LLM provider mode, and verification outcome is reproducible, auditable, and explainable in a capstone viva.
- Offline CI can verify ML training/inference, RAG retrieval evaluation, Socratic state machine, security guardrails, and frontend UI without requiring paid external LLM keys, while live Docker environments can additionally verify live `pgvector` HNSW queries, PostgreSQL `FORCE RLS`, and real Judge0 sandboxing.
