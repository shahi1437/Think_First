"""Curated, instructor-reviewable Python educational knowledge base for RAG.

Covers all 10 required areas: variables, conditions, loops, boundaries, arrays,
indexing, functions, runtime errors, logic errors, and test design.
Strictly educational conceptual guidance — never contains hidden tests or private solutions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeedKnowledgeDoc:
    slug: str
    title: str
    topic: str
    error_codes: tuple[str, ...]
    source_name: str
    source_version: str
    content_md: str
    language_slug: str = "python"


APPROVED_PYTHON_KNOWLEDGE_DOCS: tuple[SeedKnowledgeDoc, ...] = (
    SeedKnowledgeDoc(
        slug="py-variables-and-initialization",
        title="Variables & Safe Accumulator Initialization",
        topic="variables",
        error_codes=("initialization_error",),
        source_name="CodeMentor Python Foundations Guide",
        source_version="1.0",
        content_md=(
            "## Choosing Safe Starting Values\n"
            "Every accumulator or extremum variable must start from a neutral identity value that "
            "matches the operation and domain. Sums start at `0`, products start at `1`, and "
            "counters start at `0`.\n\n"
            "## Maximum and Minimum Initialization Pitfall\n"
            "Initializing `best = 0` when searching for a maximum fails whenever every input value "
            "is negative, because `0` is greater than all negative numbers. Similarly, initializing "
            "`lowest = 0` fails on all-positive lists. Instead, initialize from the first input "
            "element (`best = nums[0]`) after confirming the list is non-empty.\n\n"
            "## Do Not Reset Accumulators Inside Loops\n"
            "Placing `total = 0` or `prod = 1` inside a loop body resets progress on every "
            "iteration so only the final element survives. Initialize once before the loop begins."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-conditions-and-boolean-logic",
        title="Conditions, Comparators & Boolean Operators",
        topic="conditionals",
        error_codes=("condition_error",),
        source_name="CodeMentor Python Foundations Guide",
        source_version="1.0",
        content_md=(
            "## Strict vs Inclusive Comparisons\n"
            "Check boundary cases carefully: `>` excludes equality whereas `>=` includes it. "
            "When grading thresholds say 'at least 90' or 'strictly positive', verify the exact "
            "boundary value (`90` or `0`) by hand.\n\n"
            "## Combining Conditions with `and` vs `or`\n"
            "`A and B` requires both predicates to be true; `A or B` succeeds when either holds. "
            "In `if / elif / else` chains, Python stops at the first matching branch, so order "
            "narrower or higher thresholds before broader ones."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-loops-and-boundaries",
        title="Loops & Off-By-One Boundary Reasoning",
        topic="loops",
        error_codes=("loop_boundary_error",),
        source_name="CodeMentor Python Foundations Guide",
        source_version="1.0",
        content_md=(
            "## How Python `range(start, stop, step)` Works\n"
            "Python's `range(start, stop)` generates integers starting at `start` and stopping "
            "**before** `stop` (half-open interval `[start, stop)`). If a problem requires an "
            "inclusive range from `a` through `b`, the stop argument must be `b + 1`.\n\n"
            "## Checking First and Last Iterations\n"
            "To catch off-by-one loop boundary bugs, trace a tiny 2-element or 3-element input "
            "and write down the exact first value and last value of the loop variable. Check "
            "whether `range(len(arr) - 1)` unintentionally skips the final element."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-arrays-and-indexing",
        title="Lists, 0-Based Indexing & Preventing IndexError",
        topic="lists",
        error_codes=("indexing_error",),
        source_name="CodeMentor Python Foundations Guide",
        source_version="1.0",
        content_md=(
            "## Valid Index Bounds in Python Lists\n"
            "A Python list `arr` of length `N` has valid non-negative indices from `0` through "
            "`N - 1`. Accessing `arr[len(arr)]` always raises `IndexError: list index out of range`.\n\n"
            "## Comparing Adjacent Pairs Safely\n"
            "When accessing `arr[i]` and `arr[i + 1]` inside a loop, `i` must stop at `len(arr) - 2`, "
            "which corresponds to `for i in range(len(arr) - 1)`. Using `range(len(arr))` steps "
            "one element past the end on the last iteration."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-functions-and-returns",
        title="Functions, Return Statements & Early Exit Bugs",
        topic="functions",
        error_codes=("function_return_error",),
        source_name="CodeMentor Python Foundations Guide",
        source_version="1.0",
        content_md=(
            "## Missing Return Produces `None`\n"
            "If a Python function computes a value or calls `print()` without executing a `return` "
            "statement, the function implicitly returns `None`. When the caller prints that return "
            "value, the program outputs `None`.\n\n"
            "## Premature `return` Inside a Loop\n"
            "Placing `return` unconditionally inside a `for` or `while` loop exits the function on "
            "the very first iteration before scanning the remaining items. For search or universal "
            "checks (`all_even`, `is_sorted`), only return early when a definitive counterexample "
            "is found, and return the default conclusion after the loop finishes."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-syntax-and-indentation",
        title="Python Syntax, Colons & Indentation Rules",
        topic="syntax",
        error_codes=("syntax_error",),
        source_name="CodeMentor Python Debugging Handbook",
        source_version="1.0",
        content_md=(
            "## Common Python Syntax Errors\n"
            "Every `def`, `if`, `elif`, `else`, `for`, and `while` header must end with a colon `:`. "
            "Use `==` for equality comparison rather than `=` (assignment). Verify that every "
            "opening parenthesis `(`, bracket `[`, and string quote has a matching closing delimiter.\n\n"
            "## Reading Syntax Error Tracebacks\n"
            "When Python reports `SyntaxError` on line `L`, check both line `L` and the immediately "
            "preceding line `L - 1`, because an unclosed parenthesis or missing colon on `L - 1` "
            "often surfaces on the next line."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-runtime-exceptions",
        title="Diagnosing Common Python Runtime Exceptions",
        topic="debugging",
        error_codes=("runtime_error",),
        source_name="CodeMentor Python Debugging Handbook",
        source_version="1.0",
        content_md=(
            "## Reading the Last Line of a Traceback\n"
            "Start at the bottom line of the traceback: it names the exception class and cause.\n"
            "- `ZeroDivisionError`: divisor evaluated to `0`.\n"
            "- `TypeError`: incompatible types combined (e.g., adding `str` and `int` or iterating an `int`).\n"
            "- `NameError`: misspelled variable or function used before assignment.\n"
            "- `KeyError`: dictionary lookup accessed a missing key — consider `.get(key, default)`.\n"
            "- `AttributeError`: method name does not exist on that object type."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-logic-and-tracing",
        title="Tracing Logic Errors & Variable State Tables",
        topic="logic",
        error_codes=("logic_error",),
        source_name="CodeMentor Python Debugging Handbook",
        source_version="1.0",
        content_md=(
            "## Hand-Tracing When Code Runs Without Crashing\n"
            "When code runs cleanly but produces `Wrong Answer`, build a 3-column state table "
            "(step, variable values, expected value) on the smallest failing test case. Locate the "
            "first line where actual state diverges from expected state.\n\n"
            "## Common Logic Pitfalls\n"
            "Check operator choice (`+` vs `*`, `//` vs `/`, `%` vs `//`), whether you are adding "
            "a value versus counting (`+= n` vs `+= 1`), and whether two variables depend on each "
            "other's old values during an update (use simultaneous tuple unpacking `a, b = b, a % b`)."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-strings-and-dictionaries",
        title="Strings, Case Normalization & Dictionary Counting",
        topic="strings",
        error_codes=("runtime_error", "condition_error", "logic_error"),
        source_name="CodeMentor Python Foundations Guide",
        source_version="1.0",
        content_md=(
            "## Safe Frequency Counting with Dictionaries\n"
            "When counting occurrences in a dictionary `counts`, use `counts[key] = counts.get(key, 0) + 1` "
            "instead of `counts[key] += 1` on an uninitialized key (which raises `KeyError`), and "
            "avoid overwriting with `counts[key] = 1`.\n\n"
            "## Case-Insensitive String Checks\n"
            "Uppercase and lowercase letters compare differently in Python (`'A' != 'a'`). Normalize "
            "with `.lower()` before membership checks when case should not matter."
        ),
    ),
    SeedKnowledgeDoc(
        slug="py-test-design-and-edge-cases",
        title="Designing Edge-Case Tests Before Submitting",
        topic="testing",
        error_codes=(
            "initialization_error",
            "loop_boundary_error",
            "condition_error",
            "indexing_error",
        ),
        source_name="CodeMentor Python Debugging Handbook",
        source_version="1.0",
        content_md=(
            "## High-Value Edge Cases to Test Independently\n"
            "Public examples rarely cover every boundary. Before submitting, mentally trace:\n"
            "1. Single-element inputs (`len == 1` or `start == end`).\n"
            "2. All-negative and all-positive inputs (exposes `best = 0` initialization bugs).\n"
            "3. Exact boundary values (target at index `0`, target at index `len - 1`, or exact threshold).\n"
            "4. Duplicate values and zero values."
        ),
    ),
)

APPROVED_MULTILANG_KNOWLEDGE_DOCS: tuple[SeedKnowledgeDoc, ...] = (
    # --- JavaScript (Node.js) ---
    SeedKnowledgeDoc(
        slug="js-syntax-types-and-equality",
        title="JavaScript Syntax, Types, `let`/`const` & Strict Equality",
        topic="syntax",
        error_codes=("syntax_error", "condition_error", "runtime_error"),
        source_name="CodeMentor JavaScript Foundations Guide",
        source_version="1.0",
        language_slug="javascript",
        content_md=(
            "## Strict Equality (`===`) vs Loose Equality (`==`)\n"
            "In JavaScript, `==` performs implicit type coercion (so `'5' == 5` is true), while "
            "`===` checks both type and value. Always convert stdin strings with `Number(...)` "
            "and prefer `===` and `!==` for predictable comparisons.\n\n"
            "## Avoiding ReferenceError & TypeError\n"
            "Declare every variable with `let` or `const` before using it. Reassigning a `const` "
            "variable throws `TypeError: Assignment to constant variable`."
        ),
    ),
    SeedKnowledgeDoc(
        slug="js-loops-and-boundaries",
        title="JavaScript Loops, Off-By-One Bounds & Accumulators",
        topic="loops",
        error_codes=("loop_boundary_error", "initialization_error"),
        source_name="CodeMentor JavaScript Foundations Guide",
        source_version="1.0",
        language_slug="javascript",
        content_md=(
            "## Inclusive vs Exclusive Loop Conditions\n"
            "In JavaScript `for (let i = a; i <= b; i++)`, using `<` stops before `b` while `<=` "
            "includes `b`. Trace the first and last value of `i` on a tiny range like `3..5`.\n\n"
            "## Safe Accumulator & Maximum Initialization\n"
            "Never initialize a maximum to `0` when inputs can be negative — start from `nums[0]`. "
            "Also watch for string concatenation (`'3' + '4' === '34'`): parse numbers first."
        ),
    ),
    SeedKnowledgeDoc(
        slug="js-arrays-and-indexing",
        title="JavaScript Arrays, `.length` Bounds & `undefined` Traps",
        topic="lists",
        error_codes=("indexing_error", "logic_error"),
        source_name="CodeMentor JavaScript Foundations Guide",
        source_version="1.0",
        language_slug="javascript",
        content_md=(
            "## Out-of-Bounds Reads Return `undefined`\n"
            "Unlike Python or Java, reading `arr[arr.length]` in JavaScript does not throw an "
            "index error — it silently returns `undefined`, which turns arithmetic into `NaN`. "
            "Keep loop indices strictly within `0 <= i < arr.length`.\n\n"
            "## Adjacent Element Traversal\n"
            "When reading `arr[i]` and `arr[i + 1]`, stop at `i < arr.length - 1`."
        ),
    ),
    SeedKnowledgeDoc(
        slug="js-functions-and-returns",
        title="JavaScript Functions, Explicit `return` & Debugging",
        topic="functions",
        error_codes=("function_return_error", "runtime_error", "logic_error"),
        source_name="CodeMentor JavaScript Debugging Handbook",
        source_version="1.0",
        language_slug="javascript",
        content_md=(
            "## Missing `return` Evaluates to `undefined`\n"
            "A JavaScript function without a `return` statement returns `undefined`. Check that "
            "`return` is placed after your loop completes rather than inside the first iteration.\n\n"
            "## Reading Node.js Stack Traces\n"
            "Start with the error type (`SyntaxError`, `ReferenceError`, `TypeError`) and the line "
            "number in `main.js` before tracing variable values."
        ),
    ),
    # --- C (GCC) ---
    SeedKnowledgeDoc(
        slug="c-compiler-syntax-and-scanf",
        title="C Compiler Diagnostics, Semicolons & Safe `scanf` Usage",
        topic="syntax",
        error_codes=("syntax_error", "runtime_error"),
        source_name="CodeMentor C Foundations Guide",
        source_version="1.0",
        language_slug="c",
        content_md=(
            "## Reading GCC Compiler Errors First\n"
            "Always fix the FIRST compiler error reported by GCC — missing `;`, unmatched `{}`, "
            "or a missing `#include <stdio.h>` causes cascading errors on later lines.\n\n"
            "## Passing Addresses to `scanf`\n"
            'Scalar variables passed to `scanf("%d", &n)` require the `&` address-of operator. '
            "Forgetting `&` causes undefined behavior or a segmentation fault (`SIGSEGV`)."
        ),
    ),
    SeedKnowledgeDoc(
        slug="c-loops-and-initialization",
        title="C Loops, Boundaries & Uninitialized Local Variables",
        topic="loops",
        error_codes=("loop_boundary_error", "initialization_error"),
        source_name="CodeMentor C Foundations Guide",
        source_version="1.0",
        language_slug="c",
        content_md=(
            "## Uninitialized Local Variables Hold Garbage\n"
            "In C, `int sum;` without `= 0` contains indeterminate stack memory. Always initialize "
            "accumulators explicitly (`int sum = 0;`) and start maximum/minimum searches from `arr[0]`.\n\n"
            "## Loop Boundaries (`<` vs `<=`)\n"
            "Verify whether an inclusive range from `a` to `b` uses `i <= b` while 0-based array "
            "iteration over `n` items uses `i < n`."
        ),
    ),
    SeedKnowledgeDoc(
        slug="c-arrays-and-bounds",
        title="C Arrays, 0-Based Indexing & Preventing `SIGSEGV`",
        topic="lists",
        error_codes=("indexing_error", "runtime_error"),
        source_name="CodeMentor C Foundations Guide",
        source_version="1.0",
        language_slug="c",
        content_md=(
            "## C Does Not Perform Automatic Bounds Checking\n"
            "Valid indices for `int arr[N]` are `0` through `N - 1`. Accessing `arr[N]` or `arr[-1]` "
            "corrupts memory or crashes with `SIGSEGV` (Segmentation Fault).\n\n"
            "## Integer Division & Overflow Awareness\n"
            "Dividing two `int` values truncates the fractional part, and dividing by `0` triggers `SIGFPE`."
        ),
    ),
    SeedKnowledgeDoc(
        slug="c-functions-and-conditions",
        title="C Functions, Return Types & Boolean Conditions",
        topic="functions",
        error_codes=("function_return_error", "condition_error", "logic_error"),
        source_name="CodeMentor C Debugging Handbook",
        source_version="1.0",
        language_slug="c",
        content_md=(
            "## Return Values & `=` vs `==` Pitfall\n"
            "In C, `if (x = 5)` assigns `5` instead of comparing! Always use `==` for equality and "
            "ensure every non-`void` function returns a value along every control path, including `return 0;` in `main`."
        ),
    ),
    # --- C++ (GCC) ---
    SeedKnowledgeDoc(
        slug="cpp-compiler-streams-and-types",
        title="C++ Compiler Errors, `std::cin`/`std::cout` & Types",
        topic="syntax",
        error_codes=("syntax_error", "runtime_error"),
        source_name="CodeMentor C++ Foundations Guide",
        source_version="1.0",
        language_slug="cpp",
        content_md=(
            "## Fixing the First `g++` Error\n"
            "Check `#include <iostream>`, `#include <vector>`, missing semicolons `;`, and `std::` "
            "namespace qualification when `g++` reports `was not declared in this scope`.\n\n"
            "## Stream Reading in Loops\n"
            "Use `while (cin >> x)` to safely read an unknown number of space-separated integers."
        ),
    ),
    SeedKnowledgeDoc(
        slug="cpp-loops-and-initialization",
        title="C++ Loops, Boundaries & Safe Initialization",
        topic="loops",
        error_codes=("loop_boundary_error", "initialization_error"),
        source_name="CodeMentor C++ Foundations Guide",
        source_version="1.0",
        language_slug="cpp",
        content_md=(
            "## Loop Boundaries & Signed/Unsigned Sizes\n"
            "Compare inclusive math bounds (`for (int i = a; i <= b; ++i)`) against 0-based container "
            "bounds (`for (size_t i = 0; i < v.size(); ++i)`). Avoid `v.size() - 1` when `v` could be empty "
            "because unsigned `size_t` underflows to a huge number.\n\n"
            "## Initializing Extremes & Sums\n"
            "Initialize `long long total = 0;` for sums and `int best = nums[0];` for maximum/minimum."
        ),
    ),
    SeedKnowledgeDoc(
        slug="cpp-vectors-and-indexing",
        title="C++ `std::vector`, Bounds Safety & `out_of_range`",
        topic="lists",
        error_codes=("indexing_error", "runtime_error"),
        source_name="CodeMentor C++ Foundations Guide",
        source_version="1.0",
        language_slug="cpp",
        content_md=(
            "## Safe Vector Access\n"
            "`v[i]` does not bounds-check and causes undefined behavior if `i >= v.size()`, while "
            "`v.at(i)` throws `std::out_of_range`. Always check `i >= 0 && i < static_cast<int>(v.size())`."
        ),
    ),
    SeedKnowledgeDoc(
        slug="cpp-functions-conditions-and-logic",
        title="C++ Functions, References & Condition Boundaries",
        topic="functions",
        error_codes=("function_return_error", "condition_error", "logic_error"),
        source_name="CodeMentor C++ Debugging Handbook",
        source_version="1.0",
        language_slug="cpp",
        content_md=(
            "## Missing Return & Early Return\n"
            "Falling off the end of a non-void C++ function is undefined behavior. Verify your "
            "`return` statement sits outside loops unless you are intentionally returning on an early match."
        ),
    ),
    # --- Java (OpenJDK) ---
    SeedKnowledgeDoc(
        slug="java-javac-syntax-and-main-class",
        title="Java `javac` Compilation, `public class Main` & Types",
        topic="syntax",
        error_codes=("syntax_error", "runtime_error"),
        source_name="CodeMentor Java Foundations Guide",
        source_version="1.0",
        language_slug="java",
        content_md=(
            "## Entry Point & Class Name Requirement\n"
            "In sandbox execution, the file is named `Main.java`, so your public entry class must be "
            "`public class Main` containing `public static void main(String[] args)`.\n\n"
            "## Common `javac` Errors\n"
            "Check missing semicolons `;`, unmatched braces `{ }`, `import java.util.*;`, and "
            "strict static typing (`int` vs `String`)."
        ),
    ),
    SeedKnowledgeDoc(
        slug="java-loops-and-initialization",
        title="Java Loops, Off-By-One Bounds & Initialization",
        topic="loops",
        error_codes=("loop_boundary_error", "initialization_error"),
        source_name="CodeMentor Java Foundations Guide",
        source_version="1.0",
        language_slug="java",
        content_md=(
            "## Loop Boundaries (`<` vs `<=`)\n"
            "Use `i <= b` for inclusive numeric ranges `[a, b]` and `i < arr.length` for 0-based "
            "arrays. Initialize local variables before use (Java refuses to compile uninitialized locals) "
            "and initialize maximum/minimum searches from `nums[0]` instead of `0`."
        ),
    ),
    SeedKnowledgeDoc(
        slug="java-arrays-indexing-and-strings",
        title="Java Arrays, `ArrayIndexOutOfBoundsException` & `.equals()`",
        topic="lists",
        error_codes=("indexing_error", "condition_error"),
        source_name="CodeMentor Java Foundations Guide",
        source_version="1.0",
        language_slug="java",
        content_md=(
            "## Array Bounds & String Comparison\n"
            "Arrays have indices `0` through `arr.length - 1`; accessing `arr[arr.length]` throws "
            "`ArrayIndexOutOfBoundsException`. For `String` equality, always use `s1.equals(s2)` instead of `==`."
        ),
    ),
    SeedKnowledgeDoc(
        slug="java-methods-returns-and-exceptions",
        title="Java Methods, Missing Return & Runtime Exceptions",
        topic="functions",
        error_codes=("function_return_error", "runtime_error", "logic_error"),
        source_name="CodeMentor Java Debugging Handbook",
        source_version="1.0",
        language_slug="java",
        content_md=(
            "## Return Paths & Null Safety\n"
            "Every non-`void` Java method must return a matching type on all code paths. Guard "
            "against `NullPointerException`, `ArithmeticException` (divide by zero), and `NoSuchElementException` "
            "by checking `sc.hasNextInt()` before reading."
        ),
    ),
)

ALL_APPROVED_KNOWLEDGE_DOCS: tuple[SeedKnowledgeDoc, ...] = (
    APPROVED_PYTHON_KNOWLEDGE_DOCS + APPROVED_MULTILANG_KNOWLEDGE_DOCS
)


def chunk_markdown_document(content_md: str) -> list[tuple[str, str]]:
    """Split markdown into semantic heading-aware chunks (heading, body)."""
    chunks: list[tuple[str, str]] = []
    current_heading = "Overview"
    buffer: list[str] = []

    for line in content_md.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if buffer:
                body = "\n".join(buffer).strip()
                if len(body) >= 10:
                    chunks.append((current_heading, body))
                buffer = []
            current_heading = stripped[3:].strip()
        else:
            buffer.append(line)

    if buffer:
        body = "\n".join(buffer).strip()
        if len(body) >= 10:
            chunks.append((current_heading, body))

    return chunks
