# Thesis / Viva Technical Reference — AI, ML, RAG & Verification Pipeline

## 1. End-to-End Execution & Diagnosis Loop
1. **Isolated Execution (Judge0 CE):** Student code runs against problem test cases (public + hidden, or single custom input) inside isolated Judge0 containers (Python 3.8.1 runtime). No student code is ever executed inside the FastAPI host process.
2. **Feature Extraction & Owned ML Classifier (`ml/` + `MLErrorClassifierService`):**
   - Extracts deterministic runtime signals (status code, stderr/traceback type, exit signals) + AST structural features from `source_code`.
   - Runs a locally trained, versioned `scikit-learn` TF-IDF + Calibrated Classifier (`ml/artifacts/error_classifier_v1.joblib`) over the 8-class educational error taxonomy (`syntax_error`, `runtime_error`, `indexing_error`, `loop_boundary_error`, `condition_error`, `initialization_error`, `function_return_error`, `logic_error`).
   - Emits calibrated probabilities, top-3 candidates, and explicit **uncertainty quantification** (`is_low_confidence` when top probability `< 0.55` or top-2 margin `< 0.12`).
3. **Verified pgvector RAG (`RagKnowledgeService`):**
   - Only `status = 'approved'` documents in `knowledge_documents` are embedded (256-dim deterministic domain-aligned feature hashing + pgvector cosine distance) and retrieved.
   - Enforces similarity thresholding (`rag_similarity_threshold = 0.22`) and **explicit no-match fallback** rather than fabricating citations.
4. **Bounded Socratic AI Mentor (`SocraticMentorService` + Live Gemini):**
   - Uses a strict progressive state machine (`hint_level = 1 -> 4`: Observation Nudge -> Concept Pointer -> Minimal Counterexample -> Focused Repair Scaffold).
   - Enforces **prompt-injection filtering** and **solution-leakage prevention** (output validator rejects leaked full solutions or code dumps, safely degrading to structured guidance).
   - Supports authentic bilingual **English (`en`)** and **Bangla (`bn`)** tutoring grounded in real Judge0 output + ML diagnosis + RAG citations, reporting `provider_mode = "live_llm"`.
5. **Independent Transfer & Delayed Retention Verification:**
   - Solving a coached problem alone does **not** grant Skill Graph mastery if heavy hints were used.
   - Learners must pass an **explanation gate**, solve an **unseen isomorphic transfer challenge**, and pass **delayed spaced-repetition retention checks** (`verification_attempts` + `retention_schedules`).
