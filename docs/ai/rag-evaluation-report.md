# Verified Multi-Language RAG Knowledge Base & Retrieval Evaluation Report

## 1. Curated Knowledge Corpus
- **Approved Educational Documents:** `26` across `5` languages (`c, cpp, java, javascript, python`)
- **Semantic Heading-Aware Chunks:** `45`
- **Vector Index:** PostgreSQL `pgvector` (`vector(256)` + HNSW cosine index)
- **Relevance Threshold:** `0.22` (strictly filters `status = 'approved'` docs and scopes by `language_slug`; never indexes hidden tests or reference solutions)

## 2. Overall Retrieval Benchmark Results
| Metric | Value |
| --- | ---: |
| In-Domain Queries Tested (5 Languages) | 30 |
| Hit@1 | 1.0000 |
| Hit@3 | 1.0000 |
| Mean Reciprocal Rank (MRR) | 1.0000 |
| Out-of-Domain Queries Tested | 5 |
| No-Match Fallback Rejection Rate | 1.0000 |

## 3. Per-Language Breakdown
| Language | Queries | Hit@1 | Hit@3 |
| --- | ---: | ---: | ---: |
| `c` | 4 | 1.0000 | 1.0000 |
| `cpp` | 4 | 1.0000 | 1.0000 |
| `java` | 4 | 1.0000 | 1.0000 |
| `javascript` | 4 | 1.0000 | 1.0000 |
| `python` | 14 | 1.0000 | 1.0000 |

## 4. Per-Query Breakdown
| Lang | Query | Expected Document | Top Returned | Raw Cosine | Status |
| --- | --- | --- | --- | ---: | --- |
| `python` | initializing best = 0 fails on all negative numbers ma | `py-variables-and-initialization` | `py-variables-and-initialization` | 0.6025 | PASS |
| `python` | resetting accumulator total = 0 inside loop body loses | `py-variables-and-initialization` | `py-variables-and-initialization` | 0.5851 | PASS |
| `python` | strict greater than > vs inclusive >= boundary thresho | `py-conditions-and-boolean-logic` | `py-conditions-and-boolean-logic` | 0.3681 | PASS |
| `python` | boolean operator and vs or condition checking | `py-conditions-and-boolean-logic` | `py-conditions-and-boolean-logic` | 0.6190 | PASS |
| `python` | range(a, b) excludes upper endpoint off-by-one loop bo | `py-loops-and-boundaries` | `py-loops-and-boundaries` | 0.5047 | PASS |
| `python` | range(len(arr) - 1) skips final element last iteration | `py-loops-and-boundaries` | `py-loops-and-boundaries` | 0.4886 | PASS |
| `python` | IndexError list index out of range accessing arr[len(a | `py-arrays-and-indexing` | `py-arrays-and-indexing` | 0.6633 | PASS |
| `python` | function returns None missing return statement | `py-functions-and-returns` | `py-functions-and-returns` | 0.8056 | PASS |
| `python` | premature return inside for loop exits on first iterat | `py-functions-and-returns` | `py-functions-and-returns` | 0.5921 | PASS |
| `python` | SyntaxError missing colon after if or for header unmat | `py-syntax-and-indentation` | `py-syntax-and-indentation` | 0.5073 | PASS |
| `python` | ZeroDivisionError TypeError NameError AttributeError t | `py-runtime-exceptions` | `py-runtime-exceptions` | 0.5057 | PASS |
| `python` | wrong answer hand trace variable state table operator  | `py-logic-and-tracing` | `py-logic-and-tracing` | 0.3999 | PASS |
| `python` | dictionary frequency counting KeyError use dict.get an | `py-strings-and-dictionaries` | `py-strings-and-dictionaries` | 0.4992 | PASS |
| `python` | edge case tests single element all negative boundary i | `py-test-design-and-edge-cases` | `py-test-design-and-edge-cases` | 0.4937 | PASS |
| `javascript` | JavaScript strict equality === vs == coercion let cons | `js-syntax-types-and-equality` | `js-syntax-types-and-equality` | 0.5671 | PASS |
| `javascript` | JavaScript for loop i <= b inclusive boundary string c | `js-loops-and-boundaries` | `js-loops-and-boundaries` | 0.5106 | PASS |
| `javascript` | JavaScript array out of bounds arr[arr.length] returns | `js-arrays-and-indexing` | `js-arrays-and-indexing` | 0.6514 | PASS |
| `javascript` | JavaScript function missing return evaluates undefined | `js-functions-and-returns` | `js-functions-and-returns` | 0.7354 | PASS |
| `c` | GCC compiler missing semicolon stdio.h scanf address-o | `c-compiler-syntax-and-scanf` | `c-compiler-syntax-and-scanf` | 0.6303 | PASS |
| `c` | C uninitialized local variable int sum garbage stack m | `c-loops-and-initialization` | `c-loops-and-initialization` | 0.4958 | PASS |
| `c` | C array bounds checking arr[N] segmentation fault SIGS | `c-arrays-and-bounds` | `c-arrays-and-bounds` | 0.5682 | PASS |
| `c` | C if assignment = vs == comparison non-void function r | `c-functions-and-conditions` | `c-functions-and-conditions` | 0.6993 | PASS |
| `cpp` | g++ compiler was not declared in this scope iostream s | `cpp-compiler-streams-and-types` | `cpp-compiler-streams-and-types` | 0.5906 | PASS |
| `cpp` | C++ loop size_t unsigned underflow v.size() - 1 long l | `cpp-loops-and-initialization` | `cpp-loops-and-initialization` | 0.5684 | PASS |
| `cpp` | C++ std::vector bounds v.at(i) out_of_range undefined  | `cpp-vectors-and-indexing` | `cpp-vectors-and-indexing` | 0.6397 | PASS |
| `cpp` | C++ non-void function missing return undefined behavio | `cpp-functions-conditions-and-logic` | `cpp-functions-conditions-and-logic` | 0.7615 | PASS |
| `java` | Java javac public class Main Main.java public static v | `java-javac-syntax-and-main-class` | `java-javac-syntax-and-main-class` | 0.7104 | PASS |
| `java` | Java loop i < arr.length uninitialized local variable  | `java-loops-and-initialization` | `java-loops-and-initialization` | 0.5516 | PASS |
| `java` | Java ArrayIndexOutOfBoundsException String comparison  | `java-arrays-indexing-and-strings` | `java-arrays-indexing-and-strings` | 0.5899 | PASS |
| `java` | Java non-void method missing return NullPointerExcepti | `java-methods-returns-and-exceptions` | `java-methods-returns-and-exceptions` | 0.6602 | PASS |
| `ood` | medieval french cathedral flying buttress limestone ma | `(no match expected)` | `(no match fallback)` | — | PASS |
| `ood` | sourdough bread fermentation hydration starter recipe  | `(no match expected)` | `(no match fallback)` | — | PASS |
| `ood` | photosynthesis chlorophyll thylakoid membrane calvin c | `(no match expected)` | `(no match fallback)` | — | PASS |
| `ood` | world cup football offside rule goalkeeper penalty sho | `(no match expected)` | `(no match fallback)` | — | PASS |
| `ood` | espresso extraction portafilter grind size crema roast | `(no match expected)` | `(no match fallback)` | — | PASS |

## 5. Reproduction
```bash
backend/.venv/Scripts/python.exe -m ml.evaluation.evaluate_rag
```
