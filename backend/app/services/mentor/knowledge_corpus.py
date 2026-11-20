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
