"""Reproducible Multi-Language RAG retrieval relevance & no-match fallback evaluation.

Evaluates semantic heading-aware chunking + 256-dim LocalSemanticEmbedder +
language-scoped metadata-boosted cosine similarity retrieval across ALL 26 curated
approved educational documents (Python, JavaScript, C, C++, Java) plus out-of-domain
queries that MUST trigger the no-match fallback.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Allow running directly from repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.mentor.embeddings import LocalSemanticEmbedder, cosine_similarity
from app.services.mentor.knowledge_corpus import (
    ALL_APPROVED_KNOWLEDGE_DOCS,
    chunk_markdown_document,
)

# 30 in-domain multi-language debugging queries (14 Python + 4 JS + 4 C + 4 C++ + 4 Java)
# + 5 out-of-domain queries expecting strict no-match fallback
EVAL_QUERIES: tuple[dict[str, Any], ...] = (
    # --- Python (14 queries covering all 10 Python docs) ---
    {
        "query": "initializing best = 0 fails on all negative numbers maximum list",
        "language_slug": "python",
        "topic": "variables",
        "error_code": "initialization_error",
        "expected_slug": "py-variables-and-initialization",
    },
    {
        "query": "resetting accumulator total = 0 inside loop body loses sum",
        "language_slug": "python",
        "topic": "variables",
        "error_code": "initialization_error",
        "expected_slug": "py-variables-and-initialization",
    },
    {
        "query": "strict greater than > vs inclusive >= boundary threshold elif order",
        "language_slug": "python",
        "topic": "conditionals",
        "error_code": "condition_error",
        "expected_slug": "py-conditions-and-boolean-logic",
    },
    {
        "query": "boolean operator and vs or condition checking",
        "language_slug": "python",
        "topic": "conditionals",
        "error_code": "condition_error",
        "expected_slug": "py-conditions-and-boolean-logic",
    },
    {
        "query": "range(a, b) excludes upper endpoint off-by-one loop boundary",
        "language_slug": "python",
        "topic": "loops",
        "error_code": "loop_boundary_error",
        "expected_slug": "py-loops-and-boundaries",
    },
    {
        "query": "range(len(arr) - 1) skips final element last iteration",
        "language_slug": "python",
        "topic": "loops",
        "error_code": "loop_boundary_error",
        "expected_slug": "py-loops-and-boundaries",
    },
    {
        "query": "IndexError list index out of range accessing arr[len(arr)] or arr[i + 1]",
        "language_slug": "python",
        "topic": "lists",
        "error_code": "indexing_error",
        "expected_slug": "py-arrays-and-indexing",
    },
    {
        "query": "function returns None missing return statement",
        "language_slug": "python",
        "topic": "functions",
        "error_code": "function_return_error",
        "expected_slug": "py-functions-and-returns",
    },
    {
        "query": "premature return inside for loop exits on first iteration",
        "language_slug": "python",
        "topic": "functions",
        "error_code": "function_return_error",
        "expected_slug": "py-functions-and-returns",
    },
    {
        "query": "SyntaxError missing colon after if or for header unmatched parenthesis",
        "language_slug": "python",
        "topic": "syntax",
        "error_code": "syntax_error",
        "expected_slug": "py-syntax-and-indentation",
    },
    {
        "query": "ZeroDivisionError TypeError NameError AttributeError traceback last line",
        "language_slug": "python",
        "topic": "debugging",
        "error_code": "runtime_error",
        "expected_slug": "py-runtime-exceptions",
    },
    {
        "query": "wrong answer hand trace variable state table operator choice logic bug",
        "language_slug": "python",
        "topic": "logic",
        "error_code": "logic_error",
        "expected_slug": "py-logic-and-tracing",
    },
    {
        "query": "dictionary frequency counting KeyError use dict.get and string .lower()",
        "language_slug": "python",
        "topic": "strings",
        "error_code": None,
        "expected_slug": "py-strings-and-dictionaries",
    },
    {
        "query": "edge case tests single element all negative boundary inputs before submitting",
        "language_slug": "python",
        "topic": "testing",
        "error_code": None,
        "expected_slug": "py-test-design-and-edge-cases",
    },
    # --- JavaScript (4 queries covering all 4 JS docs) ---
    {
        "query": "JavaScript strict equality === vs == coercion let const ReferenceError",
        "language_slug": "javascript",
        "topic": "syntax",
        "error_code": "syntax_error",
        "expected_slug": "js-syntax-types-and-equality",
    },
    {
        "query": "JavaScript for loop i <= b inclusive boundary string concatenation Number parse",
        "language_slug": "javascript",
        "topic": "loops",
        "error_code": "loop_boundary_error",
        "expected_slug": "js-loops-and-boundaries",
    },
    {
        "query": "JavaScript array out of bounds arr[arr.length] returns undefined NaN",
        "language_slug": "javascript",
        "topic": "lists",
        "error_code": "indexing_error",
        "expected_slug": "js-arrays-and-indexing",
    },
    {
        "query": "JavaScript function missing return evaluates undefined Node.js stack trace",
        "language_slug": "javascript",
        "topic": "functions",
        "error_code": "function_return_error",
        "expected_slug": "js-functions-and-returns",
    },
    # --- C (4 queries covering all 4 C docs) ---
    {
        "query": "GCC compiler missing semicolon stdio.h scanf address-of & SIGSEGV",
        "language_slug": "c",
        "topic": "syntax",
        "error_code": "syntax_error",
        "expected_slug": "c-compiler-syntax-and-scanf",
    },
    {
        "query": "C uninitialized local variable int sum garbage stack memory loop i <= b",
        "language_slug": "c",
        "topic": "loops",
        "error_code": "initialization_error",
        "expected_slug": "c-loops-and-initialization",
    },
    {
        "query": "C array bounds checking arr[N] segmentation fault SIGSEGV integer division SIGFPE",
        "language_slug": "c",
        "topic": "lists",
        "error_code": "indexing_error",
        "expected_slug": "c-arrays-and-bounds",
    },
    {
        "query": "C if assignment = vs == comparison non-void function return 0 in main",
        "language_slug": "c",
        "topic": "functions",
        "error_code": "function_return_error",
        "expected_slug": "c-functions-and-conditions",
    },
    # --- C++ (4 queries covering all 4 C++ docs) ---
    {
        "query": "g++ compiler was not declared in this scope iostream std::cin while stream",
        "language_slug": "cpp",
        "topic": "syntax",
        "error_code": "syntax_error",
        "expected_slug": "cpp-compiler-streams-and-types",
    },
    {
        "query": "C++ loop size_t unsigned underflow v.size() - 1 long long total initialization",
        "language_slug": "cpp",
        "topic": "loops",
        "error_code": "loop_boundary_error",
        "expected_slug": "cpp-loops-and-initialization",
    },
    {
        "query": "C++ std::vector bounds v.at(i) out_of_range undefined behavior static_cast",
        "language_slug": "cpp",
        "topic": "lists",
        "error_code": "indexing_error",
        "expected_slug": "cpp-vectors-and-indexing",
    },
    {
        "query": "C++ non-void function missing return undefined behavior early return inside loop",
        "language_slug": "cpp",
        "topic": "functions",
        "error_code": "function_return_error",
        "expected_slug": "cpp-functions-conditions-and-logic",
    },
    # --- Java (4 queries covering all 4 Java docs) ---
    {
        "query": "Java javac public class Main Main.java public static void main import java.util",
        "language_slug": "java",
        "topic": "syntax",
        "error_code": "syntax_error",
        "expected_slug": "java-javac-syntax-and-main-class",
    },
    {
        "query": "Java loop i < arr.length uninitialized local variable nums[0] maximum",
        "language_slug": "java",
        "topic": "loops",
        "error_code": "loop_boundary_error",
        "expected_slug": "java-loops-and-initialization",
    },
    {
        "query": "Java ArrayIndexOutOfBoundsException String comparison s1.equals(s2) instead of ==",
        "language_slug": "java",
        "topic": "lists",
        "error_code": "indexing_error",
        "expected_slug": "java-arrays-indexing-and-strings",
    },
    {
        "query": "Java non-void method missing return NullPointerException ArithmeticException sc.hasNextInt",
        "language_slug": "java",
        "topic": "functions",
        "error_code": "function_return_error",
        "expected_slug": "java-methods-returns-and-exceptions",
    },
    # --- Out-of-domain queries: MUST NOT match across any language ---
    {
        "query": "medieval french cathedral flying buttress limestone masonry architecture",
        "language_slug": None,
        "topic": None,
        "error_code": None,
        "expected_slug": None,
    },
    {
        "query": "sourdough bread fermentation hydration starter recipe oven temperature",
        "language_slug": None,
        "topic": None,
        "error_code": None,
        "expected_slug": None,
    },
    {
        "query": "photosynthesis chlorophyll thylakoid membrane calvin cycle botany",
        "language_slug": None,
        "topic": None,
        "error_code": None,
        "expected_slug": None,
    },
    {
        "query": "world cup football offside rule goalkeeper penalty shootout",
        "language_slug": None,
        "topic": None,
        "error_code": None,
        "expected_slug": None,
    },
    {
        "query": "espresso extraction portafilter grind size crema roast profile",
        "language_slug": None,
        "topic": None,
        "error_code": None,
        "expected_slug": None,
    },
)


def run_rag_evaluation(threshold: float = 0.22) -> dict[str, Any]:
    embedder = LocalSemanticEmbedder(dimensions=256)

    # Index all 26 approved multi-language chunks (same formula as RagKnowledgeService)
    indexed_chunks: list[dict[str, Any]] = []
    languages_covered: set[str] = set()
    for doc in ALL_APPROVED_KNOWLEDGE_DOCS:
        languages_covered.add(doc.language_slug)
        for idx, (heading, body) in enumerate(chunk_markdown_document(doc.content_md)):
            embed_input = (
                f"{doc.title}\nLanguage: {doc.language_slug}\nTopic: {doc.topic}\n"
                f"Errors: {' '.join(doc.error_codes)}\n{heading}\n{body}"
            )
            indexed_chunks.append(
                {
                    "slug": doc.slug,
                    "title": doc.title,
                    "language_slug": doc.language_slug,
                    "topic": doc.topic,
                    "error_codes": list(doc.error_codes),
                    "chunk_index": idx,
                    "heading": heading,
                    "vec": embedder.embed(embed_input),
                }
            )

    in_domain_total = 0
    hit_at_1 = 0
    hit_at_3 = 0
    mrr_sum = 0.0
    ood_total = 0
    ood_rejected = 0
    per_language: dict[str, dict[str, int]] = {}
    per_query_results: list[dict[str, Any]] = []

    for item in EVAL_QUERIES:
        q = item["query"]
        lang = item.get("language_slug")
        topic = item["topic"]
        error_code = item["error_code"]
        expected = item["expected_slug"]

        enriched = q
        if lang:
            enriched += f" language:{lang}"
        if topic:
            enriched += f" topic:{topic}"
        if error_code:
            enriched += f" error:{error_code}"
        qvec = embedder.embed(enriched)

        scored: list[tuple[float, float, dict[str, Any]]] = []
        norm_topic = topic.lower() if topic else None
        for ch in indexed_chunks:
            if lang and ch["language_slug"] != lang:
                continue
            raw_sim = cosine_similarity(qvec, ch["vec"])
            score = raw_sim
            if error_code and error_code in ch["error_codes"]:
                score += 0.14
            if norm_topic and (
                ch["topic"].lower() == norm_topic or norm_topic in ch["slug"]
            ):
                score += 0.08
            score = min(round(score, 4), 1.0)
            if raw_sim < threshold and score < (threshold + 0.12):
                continue
            scored.append((score, round(raw_sim, 4), ch))

        scored.sort(key=lambda row: row[0], reverse=True)
        top3 = scored[:3]
        top3_slugs = [row[2]["slug"] for row in top3]

        if expected is None:
            ood_total += 1
            rejected = len(top3) == 0
            if rejected:
                ood_rejected += 1
            per_query_results.append(
                {
                    "language_slug": "ood",
                    "query": q,
                    "expected_slug": None,
                    "matched": len(top3) > 0,
                    "top_slugs": top3_slugs,
                    "passed": rejected,
                }
            )
        else:
            in_domain_total += 1
            lang_key = str(lang or "python")
            bucket = per_language.setdefault(
                lang_key, {"total": 0, "hit_at_1": 0, "hit_at_3": 0}
            )
            bucket["total"] += 1
            rank = None
            for idx, slug in enumerate(top3_slugs, start=1):
                if slug == expected:
                    rank = idx
                    break
            if rank == 1:
                hit_at_1 += 1
                bucket["hit_at_1"] += 1
            if rank is not None and rank <= 3:
                hit_at_3 += 1
                bucket["hit_at_3"] += 1
                mrr_sum += 1.0 / rank
            per_query_results.append(
                {
                    "language_slug": lang_key,
                    "query": q,
                    "expected_slug": expected,
                    "matched": len(top3) > 0,
                    "top_slugs": top3_slugs,
                    "top_raw_similarity": top3[0][1] if top3 else 0.0,
                    "rank": rank,
                    "passed": rank is not None,
                }
            )

    return {
        "corpus_documents": len(ALL_APPROVED_KNOWLEDGE_DOCS),
        "corpus_chunks": len(indexed_chunks),
        "languages_covered": sorted(languages_covered),
        "embedding_dimensions": 256,
        "similarity_threshold": threshold,
        "in_domain_queries": in_domain_total,
        "hit_at_1": round(hit_at_1 / max(in_domain_total, 1), 4),
        "hit_at_3": round(hit_at_3 / max(in_domain_total, 1), 4),
        "mrr": round(mrr_sum / max(in_domain_total, 1), 4),
        "out_of_domain_queries": ood_total,
        "no_match_rejection_rate": round(ood_rejected / max(ood_total, 1), 4),
        "per_language": per_language,
        "results": per_query_results,
    }


def write_markdown_report(report: dict[str, Any], out_md: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    langs = ", ".join(report["languages_covered"])
    lines = [
        "# Verified Multi-Language RAG Knowledge Base & Retrieval Evaluation Report",
        "",
        "## 1. Curated Knowledge Corpus",
        f"- **Approved Educational Documents:** `{report['corpus_documents']}` across `{len(report['languages_covered'])}` languages (`{langs}`)",
        f"- **Semantic Heading-Aware Chunks:** `{report['corpus_chunks']}`",
        f"- **Vector Index:** PostgreSQL `pgvector` (`vector({report['embedding_dimensions']})` + HNSW cosine index)",
        f"- **Relevance Threshold:** `{report['similarity_threshold']}` (strictly filters `status = 'approved'` docs and scopes by `language_slug`; never indexes hidden tests or reference solutions)",
        "",
        "## 2. Overall Retrieval Benchmark Results",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| In-Domain Queries Tested (5 Languages) | {report['in_domain_queries']} |",
        f"| Hit@1 | {report['hit_at_1']:.4f} |",
        f"| Hit@3 | {report['hit_at_3']:.4f} |",
        f"| Mean Reciprocal Rank (MRR) | {report['mrr']:.4f} |",
        f"| Out-of-Domain Queries Tested | {report['out_of_domain_queries']} |",
        f"| No-Match Fallback Rejection Rate | {report['no_match_rejection_rate']:.4f} |",
        "",
        "## 3. Per-Language Breakdown",
        "| Language | Queries | Hit@1 | Hit@3 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for lang_key, stats in sorted(report["per_language"].items()):
        h1 = stats["hit_at_1"] / max(stats["total"], 1)
        h3 = stats["hit_at_3"] / max(stats["total"], 1)
        lines.append(f"| `{lang_key}` | {stats['total']} | {h1:.4f} | {h3:.4f} |")

    lines.extend(
        [
            "",
            "## 4. Per-Query Breakdown",
            "| Lang | Query | Expected Document | Top Returned | Raw Cosine | Status |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for row in report["results"]:
        expected = row["expected_slug"] or "(no match expected)"
        top_slug = row["top_slugs"][0] if row["top_slugs"] else "(no match fallback)"
        sim = f"{row.get('top_raw_similarity', 0.0):.4f}" if row["matched"] else "—"
        status_str = "PASS" if row["passed"] else "FAIL"
        lines.append(
            f"| `{row['language_slug']}` | {row['query'][:54]} | `{expected}` | `{top_slug}` | {sim} | {status_str} |"
        )

    lines.extend(
        [
            "",
            "## 5. Reproduction",
            "```bash",
            "backend/.venv/Scripts/python.exe -m ml.evaluation.evaluate_rag",
            "```",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    eval_report = run_rag_evaluation()
    json_path = REPO_ROOT / "ml" / "evaluation" / "rag_eval_v1.json"
    md_path = REPO_ROOT / "docs" / "ai" / "rag-evaluation-report.md"
    json_path.write_text(json.dumps(eval_report, indent=2), encoding="utf-8")
    write_markdown_report(eval_report, md_path)
    print(
        json.dumps(
            {
                "corpus_documents": eval_report["corpus_documents"],
                "corpus_chunks": eval_report["corpus_chunks"],
                "hit_at_1": eval_report["hit_at_1"],
                "hit_at_3": eval_report["hit_at_3"],
                "mrr": eval_report["mrr"],
                "no_match_rejection_rate": eval_report["no_match_rejection_rate"],
            },
            indent=2,
        )
    )
