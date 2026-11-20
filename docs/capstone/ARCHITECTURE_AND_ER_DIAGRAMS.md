# CodeMentor AI (Think_First) — Final Architecture, Workflow & Database ER Diagrams

## 1. Final Production System Architecture
```mermaid
flowchart TB
    User["Student / Teacher / Admin Browser"] -->|"HTTPS + Security Headers"| Vercel["Vercel: Next.js 16 Frontend (Root: frontend/)"]
    Vercel -->|"Supabase SSR + Anon Key"| SupaAuth["Supabase Cloud Auth (JWKS RS256/ES256)"]
    Vercel -->|"HTTPS REST + Bearer JWT"| FastAPI["FastAPI Modular Monolith (backend.Dockerfile)"]
    FastAPI -->|"Verify JWT via JWKS + Enforce DB RBAC"| SupaAuth
    FastAPI -->|"AsyncPG + FORCE RLS (55 tables)"| PG["Supabase PostgreSQL 17 + pgvector"]
    FastAPI -->|"Isolated Untrusted Code Execution"| Judge0["Isolated Judge0 CE Sandbox + Workers"]
    FastAPI -->|"Calibrated Inference"| ML["Own scikit-learn Classifier (error-clf-v1.0.0)"]
    FastAPI -->|"Cosine Similarity (status='approved')"| PG
    FastAPI -->|"Server-Side API Key + Leakage Guard"| Gemini["Google Gemini Socratic LLM"]
```

## 2. Hybrid Execution → ML → RAG → Gemini → Transfer Workflow
```mermaid
sequenceDiagram
    autonumber
    actor S as Student
    participant UI as Monaco Workspace (Next.js)
    participant API as FastAPI Backend
    participant J0 as Judge0 CE Sandbox
    participant ML as Own ML Classifier
    participant RAG as pgvector RAG
    participant LLM as Gemini Socratic Engine
    participant TV as Transfer Verification

    S->>UI: Write code + debugging prediction, click Run/Submit
    UI->>API: POST /api/v1/submissions (Bearer JWT)
    API->>J0: Submit code + public/hidden tests (network=false)
    J0-->>API: Verdict, stdout, stderr, runtime_ms, memory_kb
    API-->>UI: Sanitized test results (hidden test I/O masked)
    S->>API: Request AI Mentor Diagnosis / Hint
    API->>ML: Execution cues + AST features -> calibrated probabilities
    ML-->>API: Top error class + uncertainty flag (<0.55 or margin <0.12)
    API->>RAG: Query approved knowledge_chunks (cosine >= 0.22)
    RAG-->>API: Top approved chunks (or explicit no-match fallback)
    API->>LLM: Prompt-injection filtered context + progressive hint state (1..4)
    LLM-->>API: Bilingual EN/BN Socratic nudge (solution-leakage checked)
    API-->>UI: Coach response + ML diagnosis + citations (provider_mode=live_llm)
    S->>UI: Fix bug -> Accepted -> Unlock unseen Transfer Challenge
    S->>TV: Solve Transfer Challenge (0 AI hints)
    TV->>J0: Verify on unseen tests -> update Skill Graph & Learning DNA
```

## 3. Core Database Entity-Relationship Diagram (PostgreSQL + `pgvector`)
```mermaid
erDiagram
    PROFILES ||--o{ USER_ROLES : holds
    PROFILES ||--o| USER_PREFERENCES : configures
    PROFILES ||--o{ SUBMISSIONS : writes
    PROFILES ||--o{ MENTOR_SESSIONS : starts
    PROFILES ||--o{ COURSE_MEMBERSHIPS : joins
    PROFILES ||--o{ AUDIT_LOGS : triggers

    PROBLEMS ||--o{ PROBLEM_VERSIONS : versions
    PROBLEM_VERSIONS ||--o{ PROBLEM_LANGUAGE_VARIANTS : has
    PROBLEM_LANGUAGE_VARIANTS ||--o| PROBLEM_REFERENCE_SOLUTIONS : protected_key
    PROBLEM_VERSIONS ||--o{ TEST_CASES : tested_by
    PROBLEM_VERSIONS ||--o{ SUBMISSIONS : evaluated_on

    SUBMISSIONS ||--o{ EXECUTION_RESULTS : produces
    SUBMISSIONS ||--o| ERROR_DIAGNOSES : diagnosed_as
    ERROR_DIAGNOSES ||--o{ MENTOR_SESSIONS : guides
    KNOWLEDGE_DOCUMENTS ||--o{ KNOWLEDGE_CHUNKS : embeds_pgvector

    LEARNING_TRACKS ||--o{ LESSONS : organizes
    SKILL_NODES ||--o{ SKILL_PREREQUISITES : requires
    PROFILES ||--o{ DIAGNOSTIC_SESSIONS : completes
    PROFILES ||--o{ LEARNING_DNA_SNAPSHOTS : measures
    PROFILES ||--o{ DAILY_LEARNING_PLANS : schedules
    PROFILES ||--o{ RETENTION_SCHEDULES : retains

    COURSES ||--o{ COURSE_MEMBERSHIPS : enrolls
    COURSES ||--o{ CLASS_INVITATIONS : invites
    COURSES ||--o{ ASSIGNMENTS : assigns
    ASSIGNMENTS ||--o{ ASSIGNMENT_SUBMISSIONS : collects
```
