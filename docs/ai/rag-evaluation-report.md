# Verified RAG Knowledge Base & Retrieval Evaluation Report

## 1. Curated Knowledge Corpus
- **Approved Educational Documents:** `10` (10 Python concept & debugging areas)
- **Semantic Heading-Aware Chunks:** `19`
- **Vector Index:** PostgreSQL `pgvector` (`vector(256)` + HNSW cosine index)
- **Relevance Threshold:** `0.22` (strictly filters `status = 'approved'` docs; never indexes hidden tests or reference solutions)

## 2. Retrieval Benchmark Results
| Metric | Value |
| --- | ---: |
| In-Domain Queries Tested | 14 |
| Hit@1 | 1.0000 |
| Hit@3 | 1.0000 |
| Mean Reciprocal Rank (MRR) | 1.0000 |
| Out-of-Domain Queries Tested | 3 |
| No-Match Fallback Rejection Rate | 1.0000 |

## 3. Per-Query Breakdown
| Query | Expected Document | Top Returned | Raw Cosine | Status |
| --- | --- | --- | ---: | --- |
| initializing best = 0 fails on all negative numbers maximum  | `py-variables-and-initialization` | `py-variables-and-initialization` | 0.5443 | PASS |
| resetting accumulator total = 0 inside loop body loses sum | `py-variables-and-initialization` | `py-variables-and-initialization` | 0.5378 | PASS |
| strict greater than > vs inclusive >= boundary threshold eli | `py-conditions-and-boolean-logic` | `py-conditions-and-boolean-logic` | 0.3564 | PASS |
| boolean operator and vs or condition checking | `py-conditions-and-boolean-logic` | `py-conditions-and-boolean-logic` | 0.5848 | PASS |
| range(a, b) excludes upper endpoint off-by-one loop boundary | `py-loops-and-boundaries` | `py-loops-and-boundaries` | 0.5048 | PASS |
| range(len(arr) - 1) skips final element last iteration | `py-loops-and-boundaries` | `py-loops-and-boundaries` | 0.5043 | PASS |
| IndexError list index out of range accessing arr[len(arr)] o | `py-arrays-and-indexing` | `py-arrays-and-indexing` | 0.6285 | PASS |
| function returns None missing return statement | `py-functions-and-returns` | `py-functions-and-returns` | 0.8165 | PASS |
| premature return inside for loop exits on first iteration | `py-functions-and-returns` | `py-functions-and-returns` | 0.5882 | PASS |
| SyntaxError missing colon after if or for header unmatched p | `py-syntax-and-indentation` | `py-syntax-and-indentation` | 0.4400 | PASS |
| ZeroDivisionError TypeError NameError AttributeError traceba | `py-runtime-exceptions` | `py-runtime-exceptions` | 0.4708 | PASS |
| wrong answer hand trace variable state table operator choice | `py-logic-and-tracing` | `py-logic-and-tracing` | 0.3454 | PASS |
| dictionary frequency counting KeyError use dict.get and stri | `py-strings-and-dictionaries` | `py-strings-and-dictionaries` | 0.4681 | PASS |
| edge case tests single element all negative boundary inputs  | `py-test-design-and-edge-cases` | `py-test-design-and-edge-cases` | 0.5149 | PASS |
| medieval french cathedral flying buttress limestone masonry  | `(no match expected)` | `(no match fallback)` | — | PASS |
| sourdough bread fermentation hydration starter recipe oven t | `(no match expected)` | `(no match fallback)` | — | PASS |
| photosynthesis chlorophyll thylakoid membrane calvin cycle b | `(no match expected)` | `(no match fallback)` | — | PASS |

## 4. Reproduction
```bash
python -m ml.evaluation.evaluate_rag
```
