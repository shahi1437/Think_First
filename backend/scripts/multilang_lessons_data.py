"""40 bilingual, real-sandbox lessons for JavaScript (10), C (10), C++ (10), and Java (10).

Preserves all 24 existing Python lessons completely untouched.
Every lesson includes:
- Bilingual English & Bangla titles, summaries, and markdown concept explanations
- Learning objectives & worked interactive example
- Guided coding exercise with starter code, 2-3 real test cases, and a verified reference solution
"""

from __future__ import annotations

from typing import Any


def _lesson(
    *,
    slug: str,
    language_slug: str,
    skill_slug: str,
    display_order: int,
    title_en: str,
    title_bn: str,
    summary_en: str,
    summary_bn: str,
    content_en_md: str,
    content_bn_md: str,
    objectives: list[str],
    prereqs: list[str],
    tracks: list[str],
    example_title: str,
    example_code: str,
    example_input: str,
    example_output: str,
    example_en: str,
    example_bn: str,
    prompt_en: str,
    prompt_bn: str,
    starter_code: str,
    reference_solution: str,
    test_cases: list[tuple[str, str, str]],
    estimated_minutes: int = 15,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "language_slug": language_slug,
        "skill_slug": skill_slug,
        "display_order": display_order,
        "title_en": title_en,
        "title_bn": title_bn,
        "summary_en": summary_en,
        "summary_bn": summary_bn,
        "content_en_md": content_en_md,
        "content_bn_md": content_bn_md,
        "learning_objectives": objectives,
        "prerequisite_lesson_slugs": prereqs,
        "track_slugs": tracks,
        "interactive_examples": [
            {
                "title": example_title,
                "code": example_code,
                "input_data": example_input,
                "expected_output": example_output,
                "explanation_en": example_en,
                "explanation_bn": example_bn,
            }
        ],
        "guided_exercise": {
            "prompt_en": prompt_en,
            "prompt_bn": prompt_bn,
            "language_slug": language_slug,
            "starter_code": starter_code,
            "test_cases": [
                {"name": name, "input_data": inp, "expected_output": out}
                for name, inp, out in test_cases
            ],
        },
        "reference_solution": reference_solution,
        "estimated_minutes": estimated_minutes,
    }


JAVASCRIPT_LESSONS: list[dict[str, Any]] = [
    _lesson(
        slug="js-01-hello-output",
        language_slug="javascript",
        skill_slug="programming_basics",
        display_order=1,
        title_en="JS 01: Output with console.log",
        title_bn="JS 01: console.log দিয়ে আউটপুট দেখানো",
        summary_en="Print clean text and calculated values in Node.js using console.log.",
        summary_bn="Node.js-এ console.log ব্যবহার করে টেক্সট ও গণনার ফলাফল প্রিন্ট করা শেখো।",
        content_en_md=(
            "## Running JavaScript in Node.js\n"
            "JavaScript runs both in web browsers and on servers using **Node.js**. To display output "
            "to standard output (stdout), call `console.log(value)`.\n\n"
            "Each `console.log(...)` automatically adds a newline at the end. Strings can be wrapped "
            "in single quotes `'...'`, double quotes `\"...\"`, or backticks `` `...` ``."
        ),
        content_bn_md=(
            "## Node.js-এ JavaScript চালানো\n"
            "JavaScript ব্রাউজার এবং **Node.js** উভয় পরিবেশেই চলে। আউটপুট দেখাতে `console.log(value)` "
            "ব্যবহার করা হয়।\n\n"
            "প্রতিটি `console.log(...)` স্বয়ংক্রিয়ভাবে শেষে একটি নতুন লাইন যোগ করে।"
        ),
        objectives=["Call console.log to emit exact output", "Format strings and numeric results"],
        prereqs=[],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Printing a greeting and sum",
        example_code="console.log('Think First');\nconsole.log(4 + 6);\n",
        example_input="",
        example_output="Think First\n10",
        example_en="Two console.log calls print two separate lines.",
        example_bn="দুটি console.log কল আলাদা দুটি লাইনে আউটপুট দেখায়।",
        prompt_en="Print the exact line `Hello JavaScript` on line 1 and `25` (the result of 5 * 5) on line 2.",
        prompt_bn="প্রথম লাইনে `Hello JavaScript` এবং দ্বিতীয় লাইনে `25` (5 * 5-এর ফল) প্রিন্ট করো।",
        starter_code="// Print Hello JavaScript and 5 * 5 on two lines\nconsole.log('Hello JavaScript');\n",
        reference_solution="console.log('Hello JavaScript');\nconsole.log(5 * 5);\n",
        test_cases=[("Exact greeting and product", "", "Hello JavaScript\n25")],
        estimated_minutes=10,
    ),
    _lesson(
        slug="js-02-variables-types",
        language_slug="javascript",
        skill_slug="variables",
        display_order=2,
        title_en="JS 02: let, const, Numbers & Template Strings",
        title_bn="JS 02: let, const, সংখ্যা এবং টেমপ্লেট স্ট্রিং",
        summary_en="Declare immutable const bindings, mutable let variables, and format values safely.",
        summary_bn="const ও let ভেরিয়েবল ঘোষণা এবং সংখ্যা-স্ট্রিং ফরম্যাটিং শেখো।",
        content_en_md=(
            "## `const` vs `let`\n"
            "Prefer `const` for values that will not be reassigned and `let` for counters or accumulators "
            "that change. Avoid legacy `var` because it ignores block scope.\n\n"
            "## Template Literals\n"
            "Use backticks with `${expr}` to embed numbers cleanly: `` `Total: ${total}` ``."
        ),
        content_bn_md=(
            "## `const` বনাম `let`\n"
            "যে মান বদলাবে না তার জন্য `const`, আর যে মান লুপে বা হিসাবের সময় বদলাবে তার জন্য `let` ব্যবহার করো।\n\n"
            "## টেমপ্লেট স্ট্রিং\n"
            "ব্যাকটিক ব্যবহার করে `` `Total: ${total}` `` লিখলে সহজেই স্ট্রিংয়ে মান বসানো যায়।"
        ),
        objectives=["Choose const vs let appropriately", "Avoid string + number coercion bugs"],
        prereqs=["js-01-hello-output"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Computing rectangle area",
        example_code="const w = 6;\nconst h = 4;\nconsole.log(`Area=${w * h}`);\n",
        example_input="",
        example_output="Area=24",
        example_en="Template literals evaluate expressions inside ${...}.",
        example_bn="টেমপ্লেট লিটারাল ${...}-এর ভেতরের এক্সপ্রেশন হিসাব করে বসায়।",
        prompt_en="Read two space-separated integers `a` and `b` from stdin, store their sum and product in variables, and print `sum product`.",
        prompt_bn="এক লাইনে দুটি পূর্ণসংখ্যা `a` ও `b` পড়ে তাদের যোগফল ও গুণফল `sum product` আকারে প্রিন্ট করো।",
        starter_code=(
            "const fs = require('fs');\n"
            "const parts = fs.readFileSync(0, 'utf8').trim().split(/\\s+/);\n"
            "const a = Number(parts[0]);\n"
            "const b = Number(parts[1]);\n"
            "// Compute sum and product and print `${sum} ${product}`\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const parts = fs.readFileSync(0, 'utf8').trim().split(/\\s+/);\n"
            "const a = Number(parts[0]);\n"
            "const b = Number(parts[1]);\n"
            "const sum = a + b;\n"
            "const prod = a * b;\n"
            "console.log(`${sum} ${prod}`);\n"
        ),
        test_cases=[
            ("Positive pair", "3 5\n", "8 15"),
            ("Negative and positive", "-4 6\n", "2 -24"),
            ("Zero case", "0 9\n", "9 0"),
        ],
    ),
    _lesson(
        slug="js-03-stdin-parsing",
        language_slug="javascript",
        skill_slug="input_output",
        display_order=3,
        title_en="JS 03: Reading & Parsing Standard Input in Node.js",
        title_bn="JS 03: Node.js-এ স্ট্যান্ডার্ড ইনপুট পড়া ও পার্স করা",
        summary_en="Parse multi-token numeric input cleanly with fs.readFileSync and Number().",
        summary_bn="fs.readFileSync ও Number() ব্যবহার করে ইনপুটকে সংখ্যায় রূপান্তর শেখো।",
        content_en_md=(
            "## Why Explicit `Number(...)` Conversion Matters\n"
            "Input read from `fs.readFileSync(0, 'utf8')` is always a **string**. Writing `'10' + '5'` "
            "produces `'105'` instead of `15`! Always convert tokens with `Number(token)`."
        ),
        content_bn_md=(
            "## `Number(...)` কনভার্সন কেন জরুরি\n"
            "`fs.readFileSync(0, 'utf8')` সবসময় স্ট্রিং দেয়। `'10' + '5'` লিখলে `'105'` হবে, `15` নয়! "
            "তাই `Number(...)` দিয়ে সংখ্যায় রূপান্তর করতে হয়।"
        ),
        objectives=[
            "Read stdin safely in Node.js",
            "Convert string tokens into numbers before arithmetic",
        ],
        prereqs=["js-02-variables-types"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Parsing three numbers",
        example_code=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "console.log(nums[0] + nums[1] + nums[2]);\n"
        ),
        example_input="2 5 8\n",
        example_output="15",
        example_en="`.map(Number)` turns every token string into a numeric value.",
        example_bn="`.map(Number)` প্রতিটি স্ট্রিং টোকেনকে সংখ্যায় পরিণত করে।",
        prompt_en="Read three integers `x`, `y`, `z` and print `(x + y) * z`.",
        prompt_bn="তিনটি পূর্ণসংখ্যা `x`, `y`, `z` পড়ে `(x + y) * z` প্রিন্ট করো।",
        starter_code=(
            "const fs = require('fs');\n"
            "const [x, y, z] = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "// Print (x + y) * z\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const [x, y, z] = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "console.log((x + y) * z);\n"
        ),
        test_cases=[
            ("Basic trio", "2 3 4\n", "20"),
            ("Negative value", "-5 2 3\n", "-9"),
            ("Zero multiplier", "7 8 0\n", "0"),
        ],
    ),
    _lesson(
        slug="js-04-conditions-equality",
        language_slug="javascript",
        skill_slug="conditions",
        display_order=4,
        title_en="JS 04: Conditions & Strict Equality (===)",
        title_bn="JS 04: শর্ত (if/else) এবং স্ট্রিক্ট সমতা (===)",
        summary_en="Write clean branching logic with ===, !==, &&, and || without coercion surprises.",
        summary_bn="===, !==, && এবং || ব্যবহার করে নির্ভুল শর্তভিত্তিক কোড লেখো।",
        content_en_md=(
            "## Always Prefer `===` Over `==`\n"
            "Strict equality `===` checks both type and value. Combine conditions with `&&` (AND) and "
            "`||` (OR), and always check boundary values like `0` or exact thresholds."
        ),
        content_bn_md=(
            "## `==`-এর বদলে `===` ব্যবহার\n"
            "`===` মান ও ডেটা টাইপ দুটোই যাচাই করে। শর্ত জোড়ার জন্য `&&` (AND) এবং `||` (OR) ব্যবহার করো।"
        ),
        objectives=["Apply if / else if / else cleanly", "Check inclusive vs strict boundaries"],
        prereqs=["js-03-stdin-parsing"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Sign check",
        example_code=(
            "const n = -3;\n"
            "if (n > 0) console.log('positive');\n"
            "else if (n < 0) console.log('negative');\n"
            "else console.log('zero');\n"
        ),
        example_input="",
        example_output="negative",
        example_en="Checks positive, negative, and zero cleanly.",
        example_bn="ধনাত্মক, ঋণাত্মক ও শূন্য আলাদাভাবে যাচাই করে।",
        prompt_en="Read an integer score `s` (0..100). Print `A` if `s >= 80`, `B` if `s >= 60`, `C` if `s >= 40`, else `F`.",
        prompt_bn="একটি পূর্ণসংখ্যা নম্বর `s` (0..100) পড়ো। `s >= 80` হলে `A`, `s >= 60` হলে `B`, `s >= 40` হলে `C`, নাহলে `F` প্রিন্ট করো।",
        starter_code=(
            "const fs = require('fs');\n"
            "const s = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "// Write if / else if / else grading logic\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const s = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "if (s >= 80) console.log('A');\n"
            "else if (s >= 60) console.log('B');\n"
            "else if (s >= 40) console.log('C');\n"
            "else console.log('F');\n"
        ),
        test_cases=[
            ("Boundary 80", "80\n", "A"),
            ("Boundary 60", "60\n", "B"),
            ("Boundary 40", "40\n", "C"),
            ("Failing 39", "39\n", "F"),
        ],
    ),
    _lesson(
        slug="js-05-loops-boundaries",
        language_slug="javascript",
        skill_slug="loops",
        display_order=5,
        title_en="JS 05: Loops & Inclusive Boundary Reasoning",
        title_bn="JS 05: লুপ এবং সীমানা (Boundary) বিশ্লেষণ",
        summary_en="Master for/while loop stop conditions (< vs <=) to prevent off-by-one bugs.",
        summary_bn="for ও while লুপে `<` বনাম `<=` বুঝে অফ-বাই-ওয়ান বাগ এড়ানো শেখো।",
        content_en_md=(
            "## Tracing Loop Boundaries\n"
            "In `for (let i = a; i <= b; i++)`, `i` visits every integer from `a` through `b` **inclusively**. "
            "Changing `<=` to `<` drops `b`! Always verify both endpoints on a tiny range."
        ),
        content_bn_md=(
            "## লুপের প্রথম ও শেষ ধাপ ট্রেস করা\n"
            "`for (let i = a; i <= b; i++)` লুপে `a` থেকে `b` পর্যন্ত সব সংখ্যা অন্তর্ভুক্ত হয়। `<=`-এর বদলে `<` লিখলে `b` বাদ পড়ে যায়।"
        ),
        objectives=["Write inclusive numeric loops", "Accumulate totals outside loop bodies"],
        prereqs=["js-04-conditions-equality"],
        tracks=["absolute_beginner", "basic_university", "intermediate"],
        example_title="Sum 1 to 4",
        example_code="let total = 0;\nfor (let i = 1; i <= 4; i++) total += i;\nconsole.log(total);\n",
        example_input="",
        example_output="10",
        example_en="Adds 1 + 2 + 3 + 4 = 10.",
        example_bn="১ + ২ + ৩ + ৪ = ১০ যোগ করে।",
        prompt_en="Read two integers `a` and `b` (`a <= b`) and print the sum of all **odd** integers from `a` to `b` inclusive.",
        prompt_bn="দুটি পূর্ণসংখ্যা `a` ও `b` (`a <= b`) পড়ে `a` থেকে `b` পর্যন্ত (উভয় প্রান্তসহ) সব বিজোড় সংখ্যার যোগফল প্রিন্ট করো।",
        starter_code=(
            "const fs = require('fs');\n"
            "const [a, b] = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "let total = 0;\n"
            "// Loop from a to b inclusive and add odd integers\n"
            "console.log(total);\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const [a, b] = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "let total = 0;\n"
            "for (let i = a; i <= b; i++) {\n"
            "  if (Math.abs(i) % 2 === 1) total += i;\n"
            "}\n"
            "console.log(total);\n"
        ),
        test_cases=[
            ("Range 1..5", "1 5\n", "9"),
            ("Single odd", "7 7\n", "7"),
            ("Negative range", "-3 3\n", "0"),
        ],
    ),
    _lesson(
        slug="js-06-arrays-iteration",
        language_slug="javascript",
        skill_slug="lists",
        display_order=6,
        title_en="JS 06: Arrays & Safe Accumulators",
        title_bn="JS 06: অ্যারে এবং নিরাপদ অ্যাকিউমুলেটর",
        summary_en="Traverse JavaScript arrays and initialize extrema from arr[0] instead of 0.",
        summary_bn="JavaScript অ্যারে ট্রাভার্স করা এবং arr[0] দিয়ে নিরাপদ সর্বোচ্চ/সর্বনিম্ন বের করা শেখো।",
        content_en_md=(
            "## Initializing Maximum & Minimum Safely\n"
            "Never initialize `best = 0` when finding the largest number in an array — all-negative "
            "arrays like `[-10, -3, -25]` would wrongly output `0`. Start with `let best = nums[0]`."
        ),
        content_bn_md=(
            "## অ্যারেতে নিরাপদ সর্বোচ্চ মান নির্ণয়\n"
            "সর্বোচ্চ মান খুঁজতে `best = 0` ধরলে সব ঋণাত্মক সংখ্যার অ্যারেতে ভুল উত্তর আসে। তাই `let best = nums[0]` দিয়ে শুরু করো।"
        ),
        objectives=["Iterate arrays using .length", "Initialize extrema from the first array item"],
        prereqs=["js-05-loops-boundaries"],
        tracks=["absolute_beginner", "basic_university", "intermediate"],
        example_title="Count positives",
        example_code="const arr = [-2, 5, 0, 8];\nlet cnt = 0;\nfor (const x of arr) if (x > 0) cnt++;\nconsole.log(cnt);\n",
        example_input="",
        example_output="2",
        example_en="Counts elements strictly greater than 0.",
        example_bn="০-এর চেয়ে বড় উপাদানের সংখ্যা গোনে।",
        prompt_en="Read one line of space-separated integers and print the **minimum** value.",
        prompt_bn="এক লাইনে স্পেস-সেপারেটেড পূর্ণসংখ্যাগুলো পড়ে **সর্বনিম্ন** মানটি প্রিন্ট করো।",
        starter_code=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "// Find and print the minimum value safely (works for all-positive & all-negative!)\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "let best = nums[0];\n"
            "for (let i = 1; i < nums.length; i++) {\n"
            "  if (nums[i] < best) best = nums[i];\n"
            "}\n"
            "console.log(best);\n"
        ),
        test_cases=[
            ("All positive", "18 24 15 30\n", "15"),
            ("All negative", "-4 -12 -7\n", "-12"),
            ("Single element", "42\n", "42"),
        ],
    ),
    _lesson(
        slug="js-07-indexing-bounds",
        language_slug="javascript",
        skill_slug="indexing",
        display_order=7,
        title_en="JS 07: 0-Based Indexing & Avoiding undefined Traps",
        title_bn="JS 07: ০-ভিত্তিক ইনডেক্সিং ও undefined ফাঁদ এড়ানো",
        summary_en="Keep indices within 0..arr.length-1 so out-of-bounds reads never produce undefined/NaN.",
        summary_bn="০ থেকে arr.length-1 সীমার মধ্যে ইনডেক্স রেখে undefined/NaN ত্রুটি এড়াও।",
        content_en_md=(
            "## Silent `undefined` Out-of-Bounds Reads\n"
            "Reading `arr[arr.length]` in JavaScript returns `undefined` instead of crashing immediately! "
            "When comparing adjacent pairs `arr[i]` and `arr[i + 1]`, stop the loop at `i < arr.length - 1`."
        ),
        content_bn_md=(
            "## নীরব `undefined` সমস্যা\n"
            "JavaScript-এ `arr[arr.length]` পড়লে ক্র্যাশ না করে `undefined` দেয়। পাশাপাশি দুটি উপাদান তুলনা করতে `i < arr.length - 1` পর্যন্ত লুপ চালাও।"
        ),
        objectives=["Respect 0..length-1 bounds", "Compare adjacent pairs safely"],
        prereqs=["js-06-arrays-iteration"],
        tracks=["basic_university", "intermediate"],
        example_title="Adjacent pair check",
        example_code="const a = [2, 5, 4, 9];\nlet inc = 0;\nfor (let i = 0; i < a.length - 1; i++) if (a[i + 1] > a[i]) inc++;\nconsole.log(inc);\n",
        example_input="",
        example_output="2",
        example_en="Pairs (2,5) and (4,9) strictly increase.",
        example_bn="(2,5) এবং (4,9) জোড়া দুটি বৃদ্ধি পেয়েছে।",
        prompt_en="Read one line of integers and count how many adjacent pairs satisfy `nums[i + 1] > nums[i]`.",
        prompt_bn="এক লাইনের পূর্ণসংখ্যাগুলো পড়ে কতটি পাশাপাশি জোড়ায় `nums[i + 1] > nums[i]` সত্য তা প্রিন্ট করো।",
        starter_code=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "let count = 0;\n"
            "// Safely iterate adjacent pairs without stepping past nums.length - 1\n"
            "console.log(count);\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "let count = 0;\n"
            "for (let i = 0; i < nums.length - 1; i++) {\n"
            "  if (nums[i + 1] > nums[i]) count++;\n"
            "}\n"
            "console.log(count);\n"
        ),
        test_cases=[
            ("Mixed sequence", "1 3 2 5 6\n", "3"),
            ("Strictly decreasing", "9 7 4 1\n", "0"),
            ("Single item", "5\n", "0"),
        ],
    ),
    _lesson(
        slug="js-08-functions-returns",
        language_slug="javascript",
        skill_slug="functions",
        display_order=8,
        title_en="JS 08: Functions, Parameters & Explicit Returns",
        title_bn="JS 08: ফাংশন, প্যারামিটার এবং স্পষ্ট Return",
        summary_en="Structure reusable JavaScript functions and avoid missing or premature return bugs.",
        summary_bn="পুনর্ব্যবহারযোগ্য ফাংশন লেখা এবং ভুল জায়গায় return দেওয়ার বাগ এড়ানো শেখো।",
        content_en_md=(
            "## Explicit Return Values\n"
            "If a function forgets `return`, callers receive `undefined`. If `return` sits inside a loop "
            "unconditionally, the function exits on iteration 1."
        ),
        content_bn_md=(
            "## স্পষ্ট `return` মান\n"
            "ফাংশনে `return` না থাকলে `undefined` ফিরে আসে, আর লুপের ভেতরে ভুল করে `return` দিলে প্রথম ধাপেই ফাংশন বের হয়ে যায়।"
        ),
        objectives=["Write pure helper functions", "Place return statements after full loop scans"],
        prereqs=["js-07-indexing-bounds"],
        tracks=["basic_university", "intermediate"],
        example_title="Pure helper function",
        example_code="function square(x) { return x * x; }\nconsole.log(square(6));\n",
        example_input="",
        example_output="36",
        example_en="Returns the computed square back to the caller.",
        example_bn="হিসাব করা বর্গমান কল করা স্থানে ফেরত দেয়।",
        prompt_en="Complete `isSorted(nums)` so it returns `true` if every adjacent pair satisfies `nums[i] <= nums[i + 1]`, else `false`, and print `YES` or `NO`.",
        prompt_bn="`isSorted(nums)` ফাংশন সম্পূর্ণ করো যাতে অ্যারেটি non-decreasing হলে `YES`, নাহলে `NO` প্রিন্ট হয়।",
        starter_code=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "function isSorted(arr) {\n"
            "  // Return false on the first decreasing pair; return true after loop finishes\n"
            "}\n"
            "console.log(isSorted(nums) ? 'YES' : 'NO');\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "function isSorted(arr) {\n"
            "  for (let i = 0; i < arr.length - 1; i++) {\n"
            "    if (arr[i] > arr[i + 1]) return false;\n"
            "  }\n"
            "  return true;\n"
            "}\n"
            "console.log(isSorted(nums) ? 'YES' : 'NO');\n"
        ),
        test_cases=[
            ("Sorted with duplicate", "1 2 2 5\n", "YES"),
            ("Unsorted at end", "1 3 5 4\n", "NO"),
            ("Single element", "10\n", "YES"),
        ],
    ),
    _lesson(
        slug="js-09-debugging-errors",
        language_slug="javascript",
        skill_slug="debugging_basics",
        display_order=9,
        title_en="JS 09: Debugging Node.js Errors & Off-By-One Bugs",
        title_bn="JS 09: Node.js এরর ও লজিক বাগ ডিবাগিং",
        summary_en="Diagnose ReferenceError, TypeError, NaN, and loop boundary bugs systematically.",
        summary_bn="ReferenceError, TypeError, NaN এবং লুপ বাগ ধাপে ধাপে ঠিক করা শেখো।",
        content_en_md=(
            "## Systematic Debugging Checklist\n"
            "1. Read the error name (`SyntaxError`, `ReferenceError`, `TypeError`) and exact line.\n"
            "2. Check numeric parsing (`Number(...)`) so you never concatenate strings.\n"
            "3. Trace the smallest failing input by hand."
        ),
        content_bn_md=(
            "## ডিবাগিং চেকলিস্ট\n"
            "১. এররের নাম ও লাইন নম্বর পড়ো।\n"
            "২. স্ট্রিং বনাম সংখ্যা টাইপ যাচাই করো।\n"
            "৩. সবচেয়ে ছোট ইনপুট হাতে ট্রেস করো।"
        ),
        objectives=[
            "Fix off-by-one and type bugs in existing JS code",
            "Verify fixes across edge cases",
        ],
        prereqs=["js-08-functions-returns"],
        tracks=["basic_university", "intermediate", "advanced"],
        example_title="Fixing const reassignment",
        example_code="let sum = 0;\nfor (let i = 1; i <= 3; i++) sum += i;\nconsole.log(sum);\n",
        example_input="",
        example_output="6",
        example_en="Using `let` allows updating `sum` inside the loop.",
        example_bn="`let` ব্যবহার করলে লুপের ভেতরে `sum` আপডেট করা যায়।",
        prompt_en="The starter code has TWO bugs (`const` accumulator and `<` instead of `<=`). Fix both so it prints the inclusive sum from `1` to `n`.",
        prompt_bn="স্টার্টার কোডে দুটি বাগ আছে (`const` অ্যাকিউমুলেটর ও `<` বনাম `<=`)। দুটিই ঠিক করে `1` থেকে `n` পর্যন্ত যোগফল প্রিন্ট করো।",
        starter_code=(
            "const fs = require('fs');\n"
            "const n = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "const total = 0;\n"
            "for (let i = 1; i < n; i++) {\n"
            "  total += i;\n"
            "}\n"
            "console.log(total);\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const n = Number(fs.readFileSync(0, 'utf8').trim());\n"
            "let total = 0;\n"
            "for (let i = 1; i <= n; i++) {\n"
            "  total += i;\n"
            "}\n"
            "console.log(total);\n"
        ),
        test_cases=[
            ("n = 5", "5\n", "15"),
            ("n = 1", "1\n", "1"),
            ("n = 10", "10\n", "55"),
        ],
    ),
    _lesson(
        slug="js-10-mixed-problem-solving",
        language_slug="javascript",
        skill_slug="mixed_problem_solving",
        display_order=10,
        title_en="JS 10: Mixed Problem Solving (Filter, Count & Edge Cases)",
        title_bn="JS 10: সমন্বিত সমস্যা সমাধান ও এজ-কেস যাচাই",
        summary_en="Combine parsing, loops, conditions, and functions to solve a multi-step JS problem.",
        summary_bn="ইনপুট পার্সিং, লুপ, শর্ত ও ফাংশন মিলিয়ে বাস্তব সমস্যা সমাধান করো।",
        content_en_md=(
            "## Combining All Core Skills\n"
            "Before coding, identify the input format, accumulator identity, boundary cases (empty/zero/negative), "
            "and exact output format."
        ),
        content_bn_md=(
            "## সব মৌলিক দক্ষতার সমন্বয়\n"
            "কোড লেখার আগে ইনপুট ফরম্যাট, শূন্য/ঋণাত্মক এজ-কেস এবং আউটপুট ফরম্যাট পরিষ্কারভাবে যাচাই করে নাও।"
        ),
        objectives=[
            "Combine loops, conditions, and arrays cleanly",
            "Handle all edge cases accurately",
        ],
        prereqs=["js-09-debugging-errors"],
        tracks=["intermediate", "advanced"],
        example_title="Count multiples of 3",
        example_code="const a = [3, 4, 6, 9];\nconsole.log(a.filter(x => x % 3 === 0).length);\n",
        example_input="",
        example_output="3",
        example_en="Filters multiples of 3 and prints the count.",
        example_bn="৩-এর গুণিতকগুলো ছেঁকে নিয়ে সংখ্যা প্রিন্ট করে।",
        prompt_en="Read one line of integers and print two numbers `evenCount evenSum`: the count and sum of all even integers.",
        prompt_bn="এক লাইনের পূর্ণসংখ্যাগুলো পড়ে জোড় সংখ্যার সংখ্যা ও যোগফল `evenCount evenSum` আকারে প্রিন্ট করো।",
        starter_code=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "// Compute evenCount and evenSum and print `${evenCount} ${evenSum}`\n"
        ),
        reference_solution=(
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
            "let evenCount = 0;\n"
            "let evenSum = 0;\n"
            "for (const x of nums) {\n"
            "  if (x % 2 === 0) {\n"
            "    evenCount++;\n"
            "    evenSum += x;\n"
            "  }\n"
            "}\n"
            "console.log(`${evenCount} ${evenSum}`);\n"
        ),
        test_cases=[
            ("Mixed numbers", "1 2 3 4 5 6\n", "3 12"),
            ("No evens", "1 3 5\n", "0 0"),
            ("Negatives and zero", "-4 -1 0 2\n", "3 -2"),
        ],
    ),
]


C_LESSONS: list[dict[str, Any]] = [
    _lesson(
        slug="c-01-hello-printf",
        language_slug="c",
        skill_slug="programming_basics",
        display_order=1,
        title_en="C 01: Program Structure, #include & printf",
        title_bn="C 01: প্রোগ্রাম কাঠামো, #include এবং printf",
        summary_en="Write and compile your first C program with stdio.h, main(), and printf.",
        summary_bn="stdio.h, main() ও printf দিয়ে তোমার প্রথম C প্রোগ্রাম কম্পাইল ও রান করো।",
        content_en_md=(
            "## Anatomy of a C Program\n"
            "Every C program starts at `int main(void)` and returns `0` on success. Include `<stdio.h>` "
            "to use `printf`, end statements with semicolons `;`, and use `\\n` for a newline."
        ),
        content_bn_md=(
            "## C প্রোগ্রামের মৌলিক গঠন\n"
            "প্রতিটি C প্রোগ্রাম `int main(void)` থেকে শুরু হয় এবং সফল হলে `return 0;` দেয়। `printf` "
            "ব্যবহার করতে `#include <stdio.h>` লিখতে হয় এবং প্রতিটি স্টেটমেন্ট `;` দিয়ে শেষ হয়।"
        ),
        objectives=["Write a valid main() function", "Print formatted lines using printf and \\n"],
        prereqs=[],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Basic C output",
        example_code='#include <stdio.h>\nint main(void) {\n    printf("Think First\\n");\n    return 0;\n}\n',
        example_input="",
        example_output="Think First",
        example_en="Includes stdio.h and prints one line.",
        example_bn="stdio.h যুক্ত করে এক লাইন টেক্সট প্রিন্ট করে।",
        prompt_en="Print `Hello C` on line 1 and `49` (7 * 7) on line 2 using `printf`.",
        prompt_bn="`printf` ব্যবহার করে প্রথম লাইনে `Hello C` এবং দ্বিতীয় লাইনে `49` (7 * 7) প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint main(void) {\n    printf("Hello C\\n");\n    // Print 7 * 7 on the next line\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    printf("Hello C\\n");\n    printf("%d\\n", 7 * 7);\n    return 0;\n}\n',
        test_cases=[("Exact output", "", "Hello C\n49")],
        estimated_minutes=10,
    ),
    _lesson(
        slug="c-02-variables-types",
        language_slug="c",
        skill_slug="variables",
        display_order=2,
        title_en="C 02: Data Types, Initialization & Format Specifiers",
        title_bn="C 02: ডেটা টাইপ, ইনিশিয়ালাইজেশন এবং ফরম্যাট স্পেসিফায়ার",
        summary_en="Declare typed int/long long variables and avoid uninitialized stack garbage.",
        summary_bn="সঠিক ডেটা টাইপ ঘোষণা ও আনইনিশিয়ালাইজড গার্বেজ মান এড়ানো শেখো।",
        content_en_md=(
            "## Always Initialize Local Variables\n"
            "In C, an uninitialized local variable like `int total;` holds unpredictable memory garbage! "
            "Match format specifiers carefully: `%d` for `int`, `%lld` for `long long`."
        ),
        content_bn_md=(
            "## লোকাল ভেরিয়েবল অবশ্যই ইনিশিয়ালাইজ করো\n"
            "C-তে `int total;` লিখলে তাতে গার্বেজ মান থাকে! `int`-এর জন্য `%d` এবং `long long`-এর জন্য `%lld` ব্যবহার করো।"
        ),
        objectives=[
            "Initialize C variables explicitly",
            "Match printf format specifiers to variable types",
        ],
        prereqs=["c-01-hello-printf"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Typed arithmetic",
        example_code='#include <stdio.h>\nint main(void) {\n    int a = 6, b = 4;\n    printf("%d %d\\n", a + b, a * b);\n    return 0;\n}\n',
        example_input="",
        example_output="10 24",
        example_en="Prints sum and product separated by a space.",
        example_bn="যোগফল ও গুণফল স্পেস দিয়ে প্রিন্ট করে।",
        prompt_en="Read two integers `a` and `b` and print `a + b` and `a - b` separated by a single space.",
        prompt_bn="দুটি পূর্ণসংখ্যা `a` ও `b` পড়ে `a + b` এবং `a - b` স্পেস দিয়ে প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint main(void) {\n    int a = 0, b = 0;\n    if (scanf("%d %d", &a, &b) == 2) {\n        // Print sum and difference\n    }\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    int a = 0, b = 0;\n    if (scanf("%d %d", &a, &b) == 2) {\n        printf("%d %d\\n", a + b, a - b);\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Basic pair", "10 4\n", "14 6"),
            ("Negative values", "-3 5\n", "2 -8"),
            ("Equal values", "7 7\n", "14 0"),
        ],
    ),
    _lesson(
        slug="c-03-scanf-input",
        language_slug="c",
        skill_slug="input_output",
        display_order=3,
        title_en="C 03: Reading Input Safely with scanf & Address-of (&)",
        title_bn="C 03: scanf ও অ্যাড্রেস অপারেটর (&) দিয়ে ইনপুট নেওয়া",
        summary_en="Pass memory addresses with & to scanf and check its return count.",
        summary_bn="scanf-এ & ব্যবহার করা এবং সঠিকভাবে একাধিক ইনপুট পড়া শেখো।",
        content_en_md=(
            "## Why `scanf` Needs `&`\n"
            "`scanf(\"%d\", &n)` writes into `n`'s memory address. Forgetting `&` passes `n`'s value as a "
            "pointer, causing a `SIGSEGV` segmentation fault."
        ),
        content_bn_md=(
            "## `scanf`-এ `&` কেন প্রয়োজন\n"
            "`scanf` ভেরিয়েবলের মেমোরি ঠিকানায় মান লেখে। `&` না দিলে প্রোগ্রাম ক্র্যাশ (`SIGSEGV`) করতে পারে।"
        ),
        objectives=["Use & with scalar variables in scanf", "Compute integer expressions cleanly"],
        prereqs=["c-02-variables-types"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Reading three ints",
        example_code='#include <stdio.h>\nint main(void) {\n    int x, y, z;\n    scanf("%d %d %d", &x, &y, &z);\n    printf("%d\\n", x + y + z);\n    return 0;\n}\n',
        example_input="2 3 5\n",
        example_output="10",
        example_en="Reads three space-separated integers with &x, &y, &z.",
        example_bn="&x, &y, &z দিয়ে তিনটি সংখ্যা পড়ে যোগফল প্রিন্ট করে।",
        prompt_en="Read three integers `x`, `y`, `z` and print `(x + y) * z`.",
        prompt_bn="তিনটি পূর্ণসংখ্যা `x`, `y`, `z` পড়ে `(x + y) * z` প্রিন্ট করো।",
        starter_code="#include <stdio.h>\n\nint main(void) {\n    int x = 0, y = 0, z = 0;\n    // Read x, y, z with scanf and print (x + y) * z\n    return 0;\n}\n",
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    int x = 0, y = 0, z = 0;\n    if (scanf("%d %d %d", &x, &y, &z) == 3) {\n        printf("%d\\n", (x + y) * z);\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Positive trio", "2 3 4\n", "20"),
            ("Negative trio", "-5 2 3\n", "-9"),
            ("Zero multiplier", "7 8 0\n", "0"),
        ],
    ),
    _lesson(
        slug="c-04-conditions-logic",
        language_slug="c",
        skill_slug="conditions",
        display_order=4,
        title_en="C 04: if / else if / else & == vs = Pitfall",
        title_bn="C 04: শর্ত (if/else) এবং == বনাম = সতর্কতা",
        summary_en="Write clear C conditionals and never confuse assignment (=) with equality (==).",
        summary_bn="সঠিক তুলনা অপারেটর (==, >=, &&, ||) দিয়ে শর্ত লেখো।",
        content_en_md=(
            "## Equality (`==`) vs Assignment (`=`)\n"
            "In C, `if (x = 5)` silently assigns `5` and evaluates as truthy! Always use `==` for equality, "
            "`&&` for AND, and `||` for OR."
        ),
        content_bn_md=(
            "## `==` বনাম `=` ফাঁদ\n"
            "C-তে `if (x = 5)` ভুলবশত মান বসিয়ে দেয়! সমতা যাচাইয়ের জন্য সবসময় `==` ব্যবহার করো।"
        ),
        objectives=["Write ordered if/else if/else branches", "Check exact boundary thresholds"],
        prereqs=["c-03-scanf-input"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Even or Odd",
        example_code='#include <stdio.h>\nint main(void) {\n    int n = 4;\n    if (n % 2 == 0) printf("EVEN\\n");\n    else printf("ODD\\n");\n    return 0;\n}\n',
        example_input="",
        example_output="EVEN",
        example_en="Uses modulo operator `%` and `==` comparison.",
        example_bn="মডুলো `%` ও `==` ব্যবহার করে জোড়-বিজোড় নির্ণয় করে।",
        prompt_en="Read an integer `n`. Print `POSITIVE` if `n > 0`, `NEGATIVE` if `n < 0`, or `ZERO` if `n == 0`.",
        prompt_bn="একটি পূর্ণসংখ্যা `n` পড়ো। `n > 0` হলে `POSITIVE`, `n < 0` হলে `NEGATIVE`, এবং `0` হলে `ZERO` প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint main(void) {\n    int n = 0;\n    if (scanf("%d", &n) == 1) {\n        // Print POSITIVE, NEGATIVE, or ZERO\n    }\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    int n = 0;\n    if (scanf("%d", &n) == 1) {\n        if (n > 0) printf("POSITIVE\\n");\n        else if (n < 0) printf("NEGATIVE\\n");\n        else printf("ZERO\\n");\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Positive", "12\n", "POSITIVE"),
            ("Negative", "-7\n", "NEGATIVE"),
            ("Zero boundary", "0\n", "ZERO"),
        ],
    ),
    _lesson(
        slug="c-05-loops-boundaries",
        language_slug="c",
        skill_slug="loops",
        display_order=5,
        title_en="C 05: for & while Loops and Off-By-One Bounds",
        title_bn="C 05: for ও while লুপ এবং সীমানা যাচাই",
        summary_en="Control inclusive vs exclusive loop bounds accurately in C.",
        summary_bn="C-তে লুপের `<` বনাম `<=` সীমা নিখুঁতভাবে ব্যবহার শেখো।",
        content_en_md=(
            "## Inclusive Loop Boundaries\n"
            "For an inclusive range `[a, b]`, write `for (int i = a; i <= b; i++)`. Always initialize your "
            "accumulator (`long long sum = 0;`) before the loop starts."
        ),
        content_bn_md=(
            "## লুপে উভয় প্রান্ত অন্তর্ভুক্ত করা\n"
            "`a` থেকে `b` পর্যন্ত সব সংখ্যা নিতে `for (int i = a; i <= b; i++)` লেখো এবং লুপের আগে `sum = 0` নির্ধারণ করো।"
        ),
        objectives=["Write inclusive C loops", "Use long long when sums may grow large"],
        prereqs=["c-04-conditions-logic"],
        tracks=["absolute_beginner", "basic_university", "intermediate"],
        example_title="Sum 1..5",
        example_code='#include <stdio.h>\nint main(void) {\n    int s = 0;\n    for (int i = 1; i <= 5; i++) s += i;\n    printf("%d\\n", s);\n    return 0;\n}\n',
        example_input="",
        example_output="15",
        example_en="Adds 1 through 5 inclusively.",
        example_bn="১ থেকে ৫ পর্যন্ত যোগ করে।",
        prompt_en="Read two integers `a` and `b` (`a <= b`) and print the inclusive sum of all integers from `a` to `b`.",
        prompt_bn="দুটি পূর্ণসংখ্যা `a` ও `b` (`a <= b`) পড়ে `a` থেকে `b` পর্যন্ত (উভয় প্রান্তসহ) সব সংখ্যার যোগফল প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint main(void) {\n    int a = 0, b = 0;\n    if (scanf("%d %d", &a, &b) == 2) {\n        long long total = 0;\n        // Add every integer from a to b inclusive\n        printf("%lld\\n", total);\n    }\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    int a = 0, b = 0;\n    if (scanf("%d %d", &a, &b) == 2) {\n        long long total = 0;\n        for (int i = a; i <= b; i++) {\n            total += i;\n        }\n        printf("%lld\\n", total);\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Range 3..5", "3 5\n", "12"),
            ("Single item", "4 4\n", "4"),
            ("Negative range", "-2 2\n", "0"),
        ],
    ),
    _lesson(
        slug="c-06-arrays-traversal",
        language_slug="c",
        skill_slug="lists",
        display_order=6,
        title_en="C 06: Fixed Arrays & Safe Maximum Initialization",
        title_bn="C 06: অ্যারে ট্রাভার্সাল এবং নিরাপদ সর্বোচ্চ মান",
        summary_en="Store N integers in a C array and initialize extrema from arr[0].",
        summary_bn="C অ্যারেতে Nটি সংখ্যা রেখে নিরাপদভাবে সর্বোচ্চ মান বের করো।",
        content_en_md=(
            "## Reading Into a C Array\n"
            "When input gives `n` followed by `n` integers, store them in `arr[0..n-1]` and initialize "
            "`int best = arr[0];` so all-negative inputs are handled accurately."
        ),
        content_bn_md=(
            "## C অ্যারে ও নেগেটিভ মানের সতর্কতা\n"
            "`best = 0` ধরলে সব ঋণাত্মক সংখ্যায় ভুল উত্তর আসে। তাই `int best = arr[0];` দিয়ে শুরু করো।"
        ),
        objectives=["Read N values into an array", "Initialize maximum from arr[0]"],
        prereqs=["c-05-loops-boundaries"],
        tracks=["absolute_beginner", "basic_university", "intermediate"],
        example_title="Array sum",
        example_code='#include <stdio.h>\nint main(void) {\n    int arr[3] = {4, 7, 2}, s = 0;\n    for (int i = 0; i < 3; i++) s += arr[i];\n    printf("%d\\n", s);\n    return 0;\n}\n',
        example_input="",
        example_output="13",
        example_en="Sums elements at indices 0, 1, and 2.",
        example_bn="০, ১ ও ২ ইনডেক্সের উপাদানগুলো যোগ করে।",
        prompt_en="Read integer `n` (1..1000) followed by `n` integers, and print the **maximum** integer.",
        prompt_bn="প্রথমে `n` (1..1000) এবং তারপর `n`টি পূর্ণসংখ্যা পড়ে **সর্বোচ্চ** মানটি প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint main(void) {\n    int n = 0;\n    int arr[1005];\n    if (scanf("%d", &n) == 1 && n > 0) {\n        for (int i = 0; i < n; i++) scanf("%d", &arr[i]);\n        // Find and print the maximum value in arr[0..n-1]\n    }\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    int n = 0;\n    int arr[1005];\n    if (scanf("%d", &n) == 1 && n > 0) {\n        for (int i = 0; i < n; i++) scanf("%d", &arr[i]);\n        int best = arr[0];\n        for (int i = 1; i < n; i++) {\n            if (arr[i] > best) best = arr[i];\n        }\n        printf("%d\\n", best);\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Mixed values", "4\n3 9 2 7\n", "9"),
            ("All negative", "3\n-10 -3 -25\n", "-3"),
            ("Single element", "1\n-99\n", "-99"),
        ],
    ),
    _lesson(
        slug="c-07-indexing-bounds",
        language_slug="c",
        skill_slug="indexing",
        display_order=7,
        title_en="C 07: 0-Based Array Bounds & Preventing Out-of-Bounds",
        title_bn="C 07: ০-ভিত্তিক অ্যারে সীমা ও মেমোরি নিরাপত্তা",
        summary_en="Keep every C array access strictly within 0..n-1 to avoid undefined behavior.",
        summary_bn="০ থেকে n-1 সীমার মধ্যে ইনডেক্স রেখে মেমোরি ক্র্যাশ (SIGSEGV) এড়াও।",
        content_en_md=(
            "## C Does Not Check Array Bounds\n"
            "Accessing `arr[n]` reads memory past the array! When scanning adjacent elements `arr[i]` "
            "and `arr[i + 1]`, your loop MUST stop at `i < n - 1`."
        ),
        content_bn_md=(
            "## C স্বয়ংক্রিয় বাউন্ড চেক করে না\n"
            "`arr[n]` অ্যাক্সেস করলে মেমোরি ত্রুটি হয়। পাশাপাশি উপাদান `arr[i]` ও `arr[i+1]` দেখতে হলে `i < n - 1` পর্যন্ত লুপ চালাও।"
        ),
        objectives=["Avoid accessing arr[n]", "Compare adjacent array elements safely"],
        prereqs=["c-06-arrays-traversal"],
        tracks=["basic_university", "intermediate"],
        example_title="First and last element",
        example_code='#include <stdio.h>\nint main(void) {\n    int a[4] = {10, 20, 30, 40};\n    printf("%d %d\\n", a[0], a[3]);\n    return 0;\n}\n',
        example_input="",
        example_output="10 40",
        example_en="Index 0 is first and index n - 1 is last.",
        example_bn="ইনডেক্স ০ প্রথম এবং n - 1 শেষ উপাদান।",
        prompt_en="Read `n` (1..1000) and `n` integers. Print how many adjacent pairs have `arr[i] == arr[i + 1]`.",
        prompt_bn="`n` এবং `n`টি পূর্ণসংখ্যা পড়ে কতটি পাশাপাশি জোড়া সমান (`arr[i] == arr[i + 1]`) তা প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint main(void) {\n    int n = 0, arr[1005];\n    if (scanf("%d", &n) == 1) {\n        for (int i = 0; i < n; i++) scanf("%d", &arr[i]);\n        int count = 0;\n        // Safely check adjacent pairs\n        printf("%d\\n", count);\n    }\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    int n = 0, arr[1005];\n    if (scanf("%d", &n) == 1) {\n        for (int i = 0; i < n; i++) scanf("%d", &arr[i]);\n        int count = 0;\n        for (int i = 0; i + 1 < n; i++) {\n            if (arr[i] == arr[i + 1]) count++;\n        }\n        printf("%d\\n", count);\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Adjacent duplicates", "5\n2 2 3 3 3\n", "3"),
            ("All distinct", "4\n1 2 3 4\n", "0"),
            ("Single item", "1\n8\n", "0"),
        ],
    ),
    _lesson(
        slug="c-08-functions-prototypes",
        language_slug="c",
        skill_slug="functions",
        display_order=8,
        title_en="C 08: Functions, Signatures & Return Values",
        title_bn="C 08: C ফাংশন, রিটার্ন টাইপ এবং প্যারামিটার",
        summary_en="Write typed helper functions in C that return values cleanly along every path.",
        summary_bn="সঠিক রিটার্ন টাইপসহ পরিষ্কার C ফাংশন লেখা শেখো।",
        content_en_md=(
            "## Typed Functions in C\n"
            "Declare return type and parameter types explicitly (e.g. `int gcd(int a, int b)`). Every "
            "path in a non-`void` function must execute a `return` statement."
        ),
        content_bn_md=(
            "## C-তে টাইপড ফাংশন\n"
            "ফাংশনের রিটার্ন টাইপ ও প্যারামিটার টাইপ স্পষ্টভাবে লিখতে হয় এবং সব শাখায় `return` থাকতে হয়।"
        ),
        objectives=["Write a non-void helper function", "Call helper functions from main()"],
        prereqs=["c-07-indexing-bounds"],
        tracks=["basic_university", "intermediate"],
        example_title="Helper function",
        example_code='#include <stdio.h>\nint dbl(int x) { return x * 2; }\nint main(void) { printf("%d\\n", dbl(9)); return 0; }\n',
        example_input="",
        example_output="18",
        example_en="Calls helper `dbl(9)` and prints returned integer.",
        example_bn="`dbl(9)` কল করে ফলাফল প্রিন্ট করে।",
        prompt_en="Complete `int max_of_three(int a, int b, int c)` and print the maximum of three input integers.",
        prompt_bn="`int max_of_three(int a, int b, int c)` ফাংশন সম্পূর্ণ করে তিনটি ইনপুট সংখ্যার সর্বোচ্চটি প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint max_of_three(int a, int b, int c) {\n    // Return the largest of a, b, c\n    return a;\n}\n\nint main(void) {\n    int a, b, c;\n    if (scanf("%d %d %d", &a, &b, &c) == 3) {\n        printf("%d\\n", max_of_three(a, b, c));\n    }\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint max_of_three(int a, int b, int c) {\n    int m = a;\n    if (b > m) m = b;\n    if (c > m) m = c;\n    return m;\n}\n\nint main(void) {\n    int a, b, c;\n    if (scanf("%d %d %d", &a, &b, &c) == 3) {\n        printf("%d\\n", max_of_three(a, b, c));\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Middle largest", "3 9 5\n", "9"),
            ("All negative", "-8 -2 -5\n", "-2"),
            ("Ties", "4 4 4\n", "4"),
        ],
    ),
    _lesson(
        slug="c-09-debugging-gcc-errors",
        language_slug="c",
        skill_slug="debugging_basics",
        display_order=9,
        title_en="C 09: Reading GCC Compiler Errors & Fixing Bugs",
        title_bn="C 09: GCC কম্পাইলার এরর পড়া ও বাগ ঠিক করা",
        summary_en="Diagnose missing semicolons, uninitialized variables, and off-by-one loop bugs.",
        summary_bn="GCC এরর মেসেজ পড়ে সিনট্যাক্স ও লজিক বাগ সমাধান করো।",
        content_en_md=(
            "## Reading GCC Diagnostics\n"
            "GCC prints `file:line:col: error: ...`. Always fix the **first** error first — missing `;` "
            "or `{` causes follow-on errors on later lines."
        ),
        content_bn_md=(
            "## GCC এরর পড়ার নিয়ম\n"
            "সবসময় প্রথম এররটি আগে ঠিক করো—একটি বাদ পড়া `;` পরের একাধিক লাইনে এরর তৈরি করতে পারে।"
        ),
        objectives=[
            "Fix GCC compile errors",
            "Fix uninitialized accumulator and loop boundary bugs",
        ],
        prereqs=["c-08-functions-prototypes"],
        tracks=["basic_university", "intermediate", "advanced"],
        example_title="Clean factorial loop",
        example_code='#include <stdio.h>\nint main(void) {\n    long long f = 1;\n    for (int i = 2; i <= 5; i++) f *= i;\n    printf("%lld\\n", f);\n    return 0;\n}\n',
        example_input="",
        example_output="120",
        example_en="Initializes product `f = 1` and multiplies up to 5.",
        example_bn="গুণফল `f = 1` ধরে ৫ পর্যন্ত গুণ করে।",
        prompt_en="Fix the buggy starter code (product initialized to 0 + missing semicolon + `<` instead of `<=`) to print `n!` for `0 <= n <= 12`.",
        prompt_bn="বাগযুক্ত কোডটি ঠিক করে `0 <= n <= 12`-এর ফ্যাক্টোরিয়াল `n!` প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint main(void) {\n    int n = 0;\n    if (scanf("%d", &n) == 1) {\n        long long fact = 0;\n        for (int i = 1; i < n; i++) {\n            fact *= i;\n        }\n        printf("%lld\\n", fact)\n    }\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    int n = 0;\n    if (scanf("%d", &n) == 1) {\n        long long fact = 1;\n        for (int i = 1; i <= n; i++) {\n            fact *= i;\n        }\n        printf("%lld\\n", fact);\n    }\n    return 0;\n}\n',
        test_cases=[
            ("5!", "5\n", "120"),
            ("0! boundary", "0\n", "1"),
            ("1!", "1\n", "1"),
        ],
    ),
    _lesson(
        slug="c-10-mixed-problem-solving",
        language_slug="c",
        skill_slug="mixed_problem_solving",
        display_order=10,
        title_en="C 10: Mixed Problem Solving (Loops, Arrays & Conditions)",
        title_bn="C 10: সমন্বিত C সমস্যা সমাধান",
        summary_en="Solve a complete multi-step C problem with edge-case verification.",
        summary_bn="লুপ, অ্যারে ও শর্ত মিলিয়ে সম্পূর্ণ C সমস্যা সমাধান করো।",
        content_en_md=(
            "## Putting C Fundamentals Together\n"
            "Combine safe `scanf`, explicit initialization, bounded loops, and `long long` sums to handle "
            "large inputs and edge cases cleanly."
        ),
        content_bn_md=(
            "## C-এর সব দক্ষতার প্রয়োগ\n"
            "নিরাপদ `scanf`, সঠিক ইনিশিয়ালাইজেশন এবং `long long` যোগফল ব্যবহার করে নির্ভুল সমাধান তৈরি করো।"
        ),
        objectives=[
            "Integrate arrays, conditionals, and loops in C",
            "Verify negative and zero edge cases",
        ],
        prereqs=["c-09-debugging-gcc-errors"],
        tracks=["intermediate", "advanced"],
        example_title="Count even items",
        example_code='#include <stdio.h>\nint main(void) {\n    int a[4] = {1, 2, 3, 4}, c = 0;\n    for (int i = 0; i < 4; i++) if (a[i] % 2 == 0) c++;\n    printf("%d\\n", c);\n    return 0;\n}\n',
        example_input="",
        example_output="2",
        example_en="Counts even numbers in an array.",
        example_bn="অ্যারের জোড় সংখ্যাগুলো গোনে।",
        prompt_en="Read `n` (1..1000) followed by `n` integers. Print `posCount negCount zeroCount`.",
        prompt_bn="`n` এবং `n`টি পূর্ণসংখ্যা পড়ে ধনাত্মক, ঋণাত্মক ও শূন্যের সংখ্যা `posCount negCount zeroCount` আকারে প্রিন্ট করো।",
        starter_code='#include <stdio.h>\n\nint main(void) {\n    int n = 0;\n    if (scanf("%d", &n) == 1) {\n        int pos = 0, neg = 0, zero = 0;\n        // Read n integers and count pos, neg, zero\n        printf("%d %d %d\\n", pos, neg, zero);\n    }\n    return 0;\n}\n',
        reference_solution='#include <stdio.h>\n\nint main(void) {\n    int n = 0;\n    if (scanf("%d", &n) == 1) {\n        int pos = 0, neg = 0, zero = 0;\n        for (int i = 0; i < n; i++) {\n            int x = 0;\n            scanf("%d", &x);\n            if (x > 0) pos++;\n            else if (x < 0) neg++;\n            else zero++;\n        }\n        printf("%d %d %d\\n", pos, neg, zero);\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Mixed", "5\n-2 0 4 -1 7\n", "2 2 1"),
            ("All zeros", "3\n0 0 0\n", "0 0 3"),
            ("Single positive", "1\n9\n", "1 0 0"),
        ],
    ),
]


CPP_LESSONS: list[dict[str, Any]] = [
    _lesson(
        slug="cpp-01-hello-iostream",
        language_slug="cpp",
        skill_slug="programming_basics",
        display_order=1,
        title_en="C++ 01: Output with iostream & std::cout",
        title_bn="C++ 01: iostream এবং std::cout দিয়ে আউটপুট",
        summary_en="Compile and run your first C++ program with <iostream> and cout.",
        summary_bn="<iostream> এবং cout ব্যবহার করে প্রথম C++ প্রোগ্রাম লেখো ও চালাও।",
        content_en_md=(
            "## C++ Standard Output\n"
            "Include `<iostream>` and use `std::cout << value << '\\n';` to emit fast, type-safe output."
        ),
        content_bn_md=(
            "## C++ স্ট্যান্ডার্ড আউটপুট\n"
            "`#include <iostream>` যুক্ত করে `cout << মান << '\\n';` দিয়ে আউটপুট দেখানো হয়।"
        ),
        objectives=["Write a valid C++ main() program", "Use cout and newline formatting"],
        prereqs=[],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Simple cout",
        example_code='#include <iostream>\nusing namespace std;\nint main() {\n    cout << "Think First" << "\\n";\n    return 0;\n}\n',
        example_input="",
        example_output="Think First",
        example_en="Outputs a line with cout.",
        example_bn="cout দিয়ে এক লাইন প্রিন্ট করে।",
        prompt_en="Print `Hello C++` on line 1 and `64` (8 * 8) on line 2.",
        prompt_bn="প্রথম লাইনে `Hello C++` এবং দ্বিতীয় লাইনে `64` (8 * 8) প্রিন্ট করো।",
        starter_code='#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello C++" << "\\n";\n    // Print 8 * 8 on line 2\n    return 0;\n}\n',
        reference_solution='#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello C++" << "\\n";\n    cout << (8 * 8) << "\\n";\n    return 0;\n}\n',
        test_cases=[("Exact greeting and product", "", "Hello C++\n64")],
        estimated_minutes=10,
    ),
    _lesson(
        slug="cpp-02-variables-types",
        language_slug="cpp",
        skill_slug="variables",
        display_order=2,
        title_en="C++ 02: int, long long, double & std::string",
        title_bn="C++ 02: int, long long, double এবং std::string",
        summary_en="Choose overflow-safe numeric types and initialize C++ variables cleanly.",
        summary_bn="সঠিক সংখ্যা টাইপ (int, long long) এবং ভেরিয়েবল ইনিশিয়ালাইজেশন শেখো।",
        content_en_md=(
            "## Preventing 32-bit Overflow\n"
            "When multiplying or summing large integers (like `100000 * 100000`), use `long long` instead "
            "of 32-bit `int` so the result never wraps around."
        ),
        content_bn_md=(
            "## ৩২-বিট ওভারফ্লো এড়ানো\n"
            "বড় সংখ্যার গুণ বা যোগে `int`-এর বদলে `long long` ব্যবহার করলে ওভারফ্লো হয় না।"
        ),
        objectives=[
            "Use long long for large integer products",
            "Initialize local variables explicitly",
        ],
        prereqs=["cpp-01-hello-iostream"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Safe long long product",
        example_code="#include <iostream>\nusing namespace std;\nint main() {\n    long long a = 100000, b = 100000;\n    cout << a * b << '\\n';\n    return 0;\n}\n",
        example_input="",
        example_output="10000000000",
        example_en="Uses 64-bit long long to prevent overflow.",
        example_bn="৬৪-বিট long long ব্যবহারে ওভারফ্লো হয় না।",
        prompt_en="Read two integers `a` and `b` (`long long`) and print `a + b` and `a * b` separated by a space.",
        prompt_bn="দুটি পূর্ণসংখ্যা `a` ও `b` (`long long`) পড়ে `a + b` এবং `a * b` স্পেস দিয়ে প্রিন্ট করো।",
        starter_code="#include <iostream>\nusing namespace std;\n\nint main() {\n    long long a = 0, b = 0;\n    if (cin >> a >> b) {\n        // Print sum and product\n    }\n    return 0;\n}\n",
        reference_solution="#include <iostream>\nusing namespace std;\n\nint main() {\n    long long a = 0, b = 0;\n    if (cin >> a >> b) {\n        cout << (a + b) << ' ' << (a * b) << '\\n';\n    }\n    return 0;\n}\n",
        test_cases=[
            ("Small numbers", "4 7\n", "11 28"),
            ("Large 64-bit product", "100000 100000\n", "200000 10000000000"),
            ("Negative", "-5 6\n", "1 -30"),
        ],
    ),
    _lesson(
        slug="cpp-03-cin-input",
        language_slug="cpp",
        skill_slug="input_output",
        display_order=3,
        title_en="C++ 03: Reading Streams with std::cin",
        title_bn="C++ 03: std::cin দিয়ে স্ট্রিম ইনপুট পড়া",
        summary_en="Read known and unknown-length integer streams cleanly using while (cin >> x).",
        summary_bn="while (cin >> x) ব্যবহার করে যেকোনো সংখ্যক ইনপুট পড়া শেখো।",
        content_en_md=(
            "## Stream Loops (`while (cin >> x)`)\n"
            "`cin >> x` automatically skips spaces and newlines and stops cleanly at EOF, making it ideal "
            "for reading space-separated lines without knowing `N` ahead of time."
        ),
        content_bn_md=(
            "## `while (cin >> x)` লুপ\n"
            "`cin >> x` স্পেস ও নিউলাইন বাদ দিয়ে শেষ পর্যন্ত সব সংখ্যা নিরাপদভাবে পড়ে।"
        ),
        objectives=["Read arbitrary-length integer streams", "Accumulate values cleanly until EOF"],
        prereqs=["cpp-02-variables-types"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Stream count",
        example_code="#include <iostream>\nusing namespace std;\nint main() {\n    int x, c = 0;\n    while (cin >> x) c++;\n    cout << c << '\\n';\n    return 0;\n}\n",
        example_input="4 8 15\n",
        example_output="3",
        example_en="Counts all integers read until EOF.",
        example_bn="ইনপুট শেষ হওয়া পর্যন্ত মোট কতটি সংখ্যা আছে তা গোনে।",
        prompt_en="Read one line of space-separated integers using `while (cin >> x)` and print their total sum.",
        prompt_bn="`while (cin >> x)` দিয়ে স্পেস-সেপারেটেড পূর্ণসংখ্যাগুলো পড়ে তাদের যোগফল প্রিন্ট করো।",
        starter_code="#include <iostream>\nusing namespace std;\n\nint main() {\n    long long x = 0, total = 0;\n    // Read every integer until EOF and add to total\n    cout << total << '\\n';\n    return 0;\n}\n",
        reference_solution="#include <iostream>\nusing namespace std;\n\nint main() {\n    long long x = 0, total = 0;\n    while (cin >> x) {\n        total += x;\n    }\n    cout << total << '\\n';\n    return 0;\n}\n",
        test_cases=[
            ("Four integers", "1 2 3 4\n", "10"),
            ("Negative values", "-5 10 -3\n", "2"),
            ("Single number", "42\n", "42"),
        ],
    ),
    _lesson(
        slug="cpp-04-conditions-logic",
        language_slug="cpp",
        skill_slug="conditions",
        display_order=4,
        title_en="C++ 04: Conditionals & Boolean Boundary Checks",
        title_bn="C++ 04: শর্ত এবং বুলিয়ান সীমানা যাচাই",
        summary_en="Combine comparisons with && and || cleanly in C++.",
        summary_bn="&& ও || ব্যবহার করে নির্ভুল শর্তভিত্তিক C++ কোড লেখো।",
        content_en_md=(
            "## Checking Ranges Properly\n"
            "Never write `1 <= x <= 10` in C++ (that evaluates `(1 <= x)` as `0` or `1`, then compares "
            "`<= 10` which is always true!). Always write `1 <= x && x <= 10`."
        ),
        content_bn_md=(
            "## C++-এ রেঞ্জ চেক করার নিয়ম\n"
            "কখনো `1 <= x <= 10` লিখবে না! সঠিক উপায় হলো `1 <= x && x <= 10`।"
        ),
        objectives=[
            "Write compound range conditions with &&",
            "Avoid chained-comparison bugs in C++",
        ],
        prereqs=["cpp-03-cin-input"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Range check",
        example_code='#include <iostream>\nusing namespace std;\nint main() {\n    int x = 5;\n    cout << ((x >= 1 && x <= 10) ? "IN" : "OUT") << "\\n";\n    return 0;\n}\n',
        example_input="",
        example_output="IN",
        example_en="Checks both lower and upper bounds explicitly with &&.",
        example_bn="&& দিয়ে নিচের ও উপরের উভয় সীমা যাচাই করে।",
        prompt_en="Read three integers `x`, `low`, `high`. Print `INSIDE` if `low <= x && x <= high`, otherwise print `OUTSIDE`.",
        prompt_bn="তিনটি পূর্ণসংখ্যা `x`, `low`, `high` পড়ো। `low <= x && x <= high` হলে `INSIDE`, নাহলে `OUTSIDE` প্রিন্ট করো।",
        starter_code="#include <iostream>\nusing namespace std;\n\nint main() {\n    int x = 0, low = 0, high = 0;\n    if (cin >> x >> low >> high) {\n        // Print INSIDE or OUTSIDE\n    }\n    return 0;\n}\n",
        reference_solution='#include <iostream>\nusing namespace std;\n\nint main() {\n    int x = 0, low = 0, high = 0;\n    if (cin >> x >> low >> high) {\n        if (x >= low && x <= high) cout << "INSIDE\\n";\n        else cout << "OUTSIDE\\n";\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Inside middle", "5 1 10\n", "INSIDE"),
            ("Exact lower bound", "1 1 10\n", "INSIDE"),
            ("Above upper bound", "11 1 10\n", "OUTSIDE"),
        ],
    ),
    _lesson(
        slug="cpp-05-loops-boundaries",
        language_slug="cpp",
        skill_slug="loops",
        display_order=5,
        title_en="C++ 05: Loops, Step Sizes & Off-By-One Safety",
        title_bn="C++ 05: লুপ, স্টেপ সাইজ ও অফ-বাই-ওয়ান নিরাপত্তা",
        summary_en="Use for loops with custom step increments safely over inclusive intervals.",
        summary_bn="কাস্টম স্টেপসহ লুপ চালিয়ে সীমানা ঠিক রাখা শেখো।",
        content_en_md=(
            "## Stepped Loops in C++\n"
            "Writing `for (int i = start; i <= end; i += step)` visits `start, start + step, ...` up to `end` "
            "inclusively as long as `step > 0`."
        ),
        content_bn_md=(
            "## স্টেপ লুপ\n"
            "`for (int i = start; i <= end; i += step)` দিয়ে নির্দিষ্ট ব্যবধানে `end` পর্যন্ত লুপ চালানো যায়।"
        ),
        objectives=["Write stepped for loops", "Verify exact endpoint inclusion"],
        prereqs=["cpp-04-conditions-logic"],
        tracks=["absolute_beginner", "basic_university", "intermediate"],
        example_title="Stepped loop",
        example_code="#include <iostream>\nusing namespace std;\nint main() {\n    int s = 0;\n    for (int i = 2; i <= 6; i += 2) s += i;\n    cout << s << '\\n';\n    return 0;\n}\n",
        example_input="",
        example_output="12",
        example_en="Adds 2 + 4 + 6 = 12.",
        example_bn="২ + ৪ + ৬ = ১২ যোগ করে।",
        prompt_en="Read three integers `start`, `end`, `step` (`step > 0`) and print the sum of `start, start+step, ...` while `<= end`.",
        prompt_bn="`start`, `end`, `step` (`step > 0`) পড়ে `start` থেকে `step` করে বাড়িয়ে `end` পর্যন্ত সংখ্যাগুলোর যোগফল প্রিন্ট করো।",
        starter_code="#include <iostream>\nusing namespace std;\n\nint main() {\n    int start = 0, end = 0, step = 1;\n    if (cin >> start >> end >> step) {\n        long long total = 0;\n        // Write stepped inclusive loop\n        cout << total << '\\n';\n    }\n    return 0;\n}\n",
        reference_solution="#include <iostream>\nusing namespace std;\n\nint main() {\n    int start = 0, end = 0, step = 1;\n    if (cin >> start >> end >> step) {\n        long long total = 0;\n        for (int i = start; i <= end; i += step) {\n            total += i;\n        }\n        cout << total << '\\n';\n    }\n    return 0;\n}\n",
        test_cases=[
            ("Even step", "2 10 2\n", "30"),
            ("Exact end hit", "1 7 3\n", "12"),
            ("Single value", "5 5 2\n", "5"),
        ],
    ),
    _lesson(
        slug="cpp-06-vectors-stl",
        language_slug="cpp",
        skill_slug="lists",
        display_order=6,
        title_en="C++ 06: std::vector & Dynamic Collections",
        title_bn="C++ 06: std::vector এবং ডাইনামিক কালেকশন",
        summary_en="Store dynamic input in std::vector<int> and iterate cleanly with range-based for.",
        summary_bn="std::vector<int>-এ ডেটা সংরক্ষণ ও রেঞ্জ-বেজড লুপ ব্যবহার শেখো।",
        content_en_md=(
            "## Why `std::vector` Beats Raw Arrays\n"
            "`std::vector<int>` grows automatically with `.push_back(x)` and knows its `.size()`. "
            "Always initialize maximum/minimum from `v[0]` after checking `!v.empty()`."
        ),
        content_bn_md=(
            "## `std::vector`-এর সুবিধা\n"
            "`std::vector<int>` নিজে থেকেই বড় হয় এবং `.size()` জানে। সর্বোচ্চ/সর্বনিম্ন মান `v[0]` দিয়ে শুরু করো।"
        ),
        objectives=["Build a vector from stdin", "Iterate safely with range-based for"],
        prereqs=["cpp-05-loops-boundaries"],
        tracks=["absolute_beginner", "basic_university", "intermediate"],
        example_title="Vector push_back",
        example_code="#include <iostream>\n#include <vector>\nusing namespace std;\nint main() {\n    vector<int> v = {3, 6, 9};\n    cout << v.size() << '\\n';\n    return 0;\n}\n",
        example_input="",
        example_output="3",
        example_en="Prints number of items in vector.",
        example_bn="ভেক্টরের উপাদান সংখ্যা প্রিন্ট করে।",
        prompt_en="Read space-separated integers into a `vector<int>` and print them in **reverse** order separated by single spaces.",
        prompt_bn="স্পেস-সেপারেটেড পূর্ণসংখ্যাগুলো `vector<int>`-এ পড়ে **উল্টো** ক্রমে এক স্পেস পরপর প্রিন্ট করো।",
        starter_code="#include <iostream>\n#include <vector>\nusing namespace std;\n\nint main() {\n    vector<int> v;\n    int x;\n    while (cin >> x) v.push_back(x);\n    // Print v in reverse order separated by spaces\n    return 0;\n}\n",
        reference_solution="#include <iostream>\n#include <vector>\nusing namespace std;\n\nint main() {\n    vector<int> v;\n    int x;\n    while (cin >> x) v.push_back(x);\n    for (int i = static_cast<int>(v.size()) - 1; i >= 0; --i) {\n        if (i < static_cast<int>(v.size()) - 1) cout << ' ';\n        cout << v[i];\n    }\n    cout << '\\n';\n    return 0;\n}\n",
        test_cases=[
            ("Four items", "1 2 3 4\n", "4 3 2 1"),
            ("Negative items", "-5 0 9\n", "9 0 -5"),
            ("Single item", "7\n", "7"),
        ],
    ),
    _lesson(
        slug="cpp-07-indexing-bounds",
        language_slug="cpp",
        skill_slug="indexing",
        display_order=7,
        title_en="C++ 07: Safe Vector Indexing & Unsigned size_t Trap",
        title_bn="C++ 07: নিরাপদ ভেক্টর ইনডেক্সিং ও size_t সতর্কতা",
        summary_en="Avoid unsigned underflow in v.size() - 1 and keep indices within 0..size-1.",
        summary_bn="v.size() - 1-এর আনসাইনড আন্ডারফ্লো এবং আউট-অফ-বাউন্ড ত্রুটি এড়াও।",
        content_en_md=(
            "## Beware Unsigned `v.size() - 1`\n"
            "`v.size()` is unsigned `size_t`. When `v` is empty, `v.size() - 1` underflows to a huge positive "
            "number! Prefer `for (size_t i = 0; i + 1 < v.size(); ++i)`."
        ),
        content_bn_md=(
            "## আনসাইনড `v.size() - 1` ফাঁদ\n"
            "`v` ফাঁকা হলে `v.size() - 1` বিশাল ধনাত্মক সংখ্যায় পরিণত হয়! তাই `i + 1 < v.size()` ব্যবহার করা সবচেয়ে নিরাপদ।"
        ),
        objectives=["Write underflow-safe adjacent index loops", "Prevent out_of_range errors"],
        prereqs=["cpp-06-vectors-stl"],
        tracks=["basic_university", "intermediate"],
        example_title="Safe adjacent check",
        example_code="#include <iostream>\n#include <vector>\nusing namespace std;\nint main() {\n    vector<int> v = {4, 4, 2};\n    int eq = 0;\n    for (size_t i = 0; i + 1 < v.size(); ++i) if (v[i] == v[i + 1]) eq++;\n    cout << eq << '\\n';\n    return 0;\n}\n",
        example_input="",
        example_output="1",
        example_en="Uses `i + 1 < v.size()` so even empty or 1-element vectors are safe.",
        example_bn="`i + 1 < v.size()` ব্যবহারে ১-উপাদান বা ফাঁকা ভেক্টরেও নিরাপদ থাকে।",
        prompt_en="Read space-separated integers into a vector and print the maximum absolute difference `|v[i + 1] - v[i]|` between adjacent elements (print `0` if fewer than 2 elements).",
        prompt_bn="পূর্ণসংখ্যাগুলো পড়ে পাশাপাশি দুটি উপাদানের পরম পার্থক্য `|v[i + 1] - v[i]|`-এর সর্বোচ্চ মান প্রিন্ট করো (২টির কম সংখ্যা হলে `0`)।",
        starter_code="#include <cmath>\n#include <iostream>\n#include <vector>\nusing namespace std;\n\nint main() {\n    vector<int> v;\n    int x;\n    while (cin >> x) v.push_back(x);\n    int best = 0;\n    // Compute max adjacent absolute difference safely\n    cout << best << '\\n';\n    return 0;\n}\n",
        reference_solution="#include <cstdlib>\n#include <iostream>\n#include <vector>\nusing namespace std;\n\nint main() {\n    vector<int> v;\n    int x;\n    while (cin >> x) v.push_back(x);\n    int best = 0;\n    for (size_t i = 0; i + 1 < v.size(); ++i) {\n        int diff = abs(v[i + 1] - v[i]);\n        if (diff > best) best = diff;\n    }\n    cout << best << '\\n';\n    return 0;\n}\n",
        test_cases=[
            ("Basic gaps", "2 9 4 10\n", "7"),
            ("Negative jump", "-5 5 2\n", "10"),
            ("Single element", "8\n", "0"),
        ],
    ),
    _lesson(
        slug="cpp-08-functions-references",
        language_slug="cpp",
        skill_slug="functions",
        display_order=8,
        title_en="C++ 08: Functions, const References & Return Guarantees",
        title_bn="C++ 08: C++ ফাংশন, const রেফারেন্স এবং রিটার্ন",
        summary_en="Pass vectors efficiently by const reference and ensure every code path returns.",
        summary_bn="const রেফারেন্সে ভেক্টর পাস করা এবং নির্ভুল রিটার্ন মান নিশ্চিত করা শেখো।",
        content_en_md=(
            "## Passing `const vector<int>&`\n"
            "Passing a vector by `const vector<int>&` avoids unnecessary copying while preventing accidental "
            "mutation inside the helper function."
        ),
        content_bn_md=(
            "## `const vector<int>&` ব্যবহার\n"
            "`const vector<int>&` দিয়ে প্যারামিটার নিলে অপ্রয়োজনীয় কপি হয় না এবং মূল ডেটা সুরক্ষিত থাকে।"
        ),
        objectives=[
            "Pass containers by const reference",
            "Return values cleanly from helper functions",
        ],
        prereqs=["cpp-07-indexing-bounds"],
        tracks=["basic_university", "intermediate"],
        example_title="Const ref helper",
        example_code="#include <iostream>\n#include <vector>\nusing namespace std;\nint countPos(const vector<int>& v) {\n    int c = 0; for (int x : v) if (x > 0) c++; return c;\n}\nint main() { cout << countPos({-1, 3, 5}) << '\\n'; }\n",
        example_input="",
        example_output="2",
        example_en="Reads vector without copying it.",
        example_bn="কপি না করেই ভেক্টর থেকে ধনাত্মক সংখ্যা গোনে।",
        prompt_en="Complete `long long sumEvens(const vector<int>& nums)` to return the sum of all even integers.",
        prompt_bn="`long long sumEvens(const vector<int>& nums)` ফাংশন সম্পূর্ণ করে সব জোড় সংখ্যার যোগফল প্রিন্ট করো।",
        starter_code="#include <iostream>\n#include <vector>\nusing namespace std;\n\nlong long sumEvens(const vector<int>& nums) {\n    // Return sum of even integers\n    return 0;\n}\n\nint main() {\n    vector<int> nums;\n    int x;\n    while (cin >> x) nums.push_back(x);\n    cout << sumEvens(nums) << '\\n';\n    return 0;\n}\n",
        reference_solution="#include <iostream>\n#include <vector>\nusing namespace std;\n\nlong long sumEvens(const vector<int>& nums) {\n    long long total = 0;\n    for (int x : nums) {\n        if (x % 2 == 0) total += x;\n    }\n    return total;\n}\n\nint main() {\n    vector<int> nums;\n    int x;\n    while (cin >> x) nums.push_back(x);\n    cout << sumEvens(nums) << '\\n';\n    return 0;\n}\n",
        test_cases=[
            ("Mixed", "1 2 3 4 5 6\n", "12"),
            ("No evens", "1 3 5\n", "0"),
            ("Negative evens", "-4 -3 -2 0\n", "-6"),
        ],
    ),
    _lesson(
        slug="cpp-09-debugging-gpp-errors",
        language_slug="cpp",
        skill_slug="debugging_basics",
        display_order=9,
        title_en="C++ 09: Debugging g++ Compiler & Logic Errors",
        title_bn="C++ 09: g++ কম্পাইলার ও লজিক বাগ ডিবাগিং",
        summary_en="Fix missing headers, initialization bugs, and boundary errors in C++ code.",
        summary_bn="হেডার মিসিং, ইনিশিয়ালাইজেশন এবং বাউন্ডারি বাগ ঠিক করা শেখো।",
        content_en_md=(
            "## Diagnosing `g++` Errors\n"
            "Look at the very first compiler message: `was not declared in this scope` usually means a "
            "missing `#include` or typo. Then verify logic on negative and boundary inputs."
        ),
        content_bn_md=(
            "## `g++` এরর বিশ্লেষণ\n"
            "প্রথম এররটি দেখো—`was not declared` মানে সাধারণত হেডার বা বানান ভুল। এরপর নেগেটিভ এজ-কেস যাচাই করো।"
        ),
        objectives=["Fix g++ compile errors", "Fix bad zero-initialization in maximum search"],
        prereqs=["cpp-08-functions-references"],
        tracks=["basic_university", "intermediate", "advanced"],
        example_title="Safe maximum",
        example_code="#include <iostream>\n#include <vector>\nusing namespace std;\nint main() {\n    vector<int> v = {-5, -2, -9};\n    int best = v[0];\n    for (int x : v) if (x > best) best = x;\n    cout << best << '\\n';\n}\n",
        example_input="",
        example_output="-2",
        example_en="Initializes `best = v[0]` so negative lists return -2.",
        example_bn="`best = v[0]` ধরায় ঋণাত্মক লিস্টেও সঠিক ফল -2 আসে।",
        prompt_en="Fix the buggy C++ starter code (missing `<vector>` include and `best = 0` bug) so it prints the true maximum of any non-empty integer line.",
        prompt_bn="বাগযুক্ত C++ কোডটি (`<vector>` হেডার ও `best = 0` বাগ) ঠিক করে সর্বোচ্চ মান প্রিন্ট করো।",
        starter_code="#include <iostream>\nusing namespace std;\n\nint main() {\n    vector<int> nums;\n    int x;\n    while (cin >> x) nums.push_back(x);\n    int best = 0;\n    for (int v : nums) {\n        if (v > best) best = v;\n    }\n    cout << best << '\\n';\n    return 0;\n}\n",
        reference_solution="#include <iostream>\n#include <vector>\nusing namespace std;\n\nint main() {\n    vector<int> nums;\n    int x;\n    while (cin >> x) nums.push_back(x);\n    int best = nums[0];\n    for (int v : nums) {\n        if (v > best) best = v;\n    }\n    cout << best << '\\n';\n    return 0;\n}\n",
        test_cases=[
            ("Positive", "4 9 2\n", "9"),
            ("All negative", "-10 -3 -25\n", "-3"),
            ("Single negative", "-99\n", "-99"),
        ],
    ),
    _lesson(
        slug="cpp-10-mixed-problem-solving",
        language_slug="cpp",
        skill_slug="mixed_problem_solving",
        display_order=10,
        title_en="C++ 10: Mixed Problem Solving with STL Map & Sorting",
        title_bn="C++ 10: STL Map ও সমন্বিত C++ সমস্যা সমাধান",
        summary_en="Use std::map to count frequencies in sorted key order cleanly.",
        summary_bn="std::map ব্যবহার করে সাজানো ক্রমে ফ্রিকোয়েন্সি গোনা শেখো।",
        content_en_md=(
            "## Ordered Counting with `std::map`\n"
            "`std::map<string, int>` automatically keeps keys sorted alphabetically and zero-initializes "
            "new entries when you write `freq[word]++`."
        ),
        content_bn_md=(
            "## `std::map` দিয়ে সাজানো কাউন্টিং\n"
            "`std::map<string, int>` নিজে থেকেই কীগুলো বর্ণানুক্রমে সাজিয়ে রাখে এবং `freq[word]++` করলে ০ থেকে বাড়ায়।"
        ),
        objectives=[
            "Count word frequencies with std::map",
            "Output deterministic sorted key:value pairs",
        ],
        prereqs=["cpp-09-debugging-gpp-errors"],
        tracks=["intermediate", "advanced"],
        example_title="Sorted frequency map",
        example_code='#include <iostream>\n#include <map>\n#include <string>\nusing namespace std;\nint main() {\n    map<string, int> m; m["b"]++; m["a"]++;\n    for (const auto& kv : m) cout << kv.first << ":" << kv.second << "\\n";\n}\n',
        example_input="",
        example_output="a:1\nb:1",
        example_en="Iterating std::map visits keys in ascending lexicographical order.",
        example_bn="std::map-এ লুপ চালালে বর্ণানুক্রমে কী পাওয়া যায়।",
        prompt_en="Read words from stdin and print each unique word and its count as `word:count` sorted alphabetically.",
        prompt_bn="ইনপুট থেকে শব্দগুলো পড়ে বর্ণানুক্রমে প্রতিটি শব্দের সংখ্যা `word:count` আকারে প্রিন্ট করো।",
        starter_code="#include <iostream>\n#include <map>\n#include <string>\nusing namespace std;\n\nint main() {\n    map<string, int> freq;\n    string w;\n    // Read words and print word:count in sorted order\n    return 0;\n}\n",
        reference_solution='#include <iostream>\n#include <map>\n#include <string>\nusing namespace std;\n\nint main() {\n    map<string, int> freq;\n    string w;\n    while (cin >> w) {\n        freq[w]++;\n    }\n    for (const auto& entry : freq) {\n        cout << entry.first << ":" << entry.second << "\\n";\n    }\n    return 0;\n}\n',
        test_cases=[
            ("Repeated words", "code think code learn\n", "code:2\nlearn:1\nthink:1"),
            ("Single word", "cpp\n", "cpp:1"),
            ("Reverse alpha", "zeta beta alpha\n", "alpha:1\nbeta:1\nzeta:1"),
        ],
    ),
]


JAVA_LESSONS: list[dict[str, Any]] = [
    _lesson(
        slug="java-01-hello-main",
        language_slug="java",
        skill_slug="programming_basics",
        display_order=1,
        title_en="Java 01: public class Main & System.out.println",
        title_bn="Java 01: public class Main এবং System.out.println",
        summary_en="Write, compile with javac, and run your first Java program inside class Main.",
        summary_bn="Main ক্লাস ও System.out.println দিয়ে প্রথম Java প্রোগ্রাম কম্পাইল ও রান করো।",
        content_en_md=(
            "## Java Entry Point\n"
            "In sandboxed Java execution, the source file is `Main.java`, so your public class MUST be "
            "`public class Main` containing `public static void main(String[] args)`."
        ),
        content_bn_md=(
            "## Java প্রোগ্রামের প্রবেশদ্বার\n"
            "স্যান্ডবক্সে ফাইলটির নাম `Main.java`, তাই পাবলিক ক্লাসটি অবশ্যই `public class Main` হতে হবে "
            "এবং এর ভেতরে `public static void main(String[] args)` থাকতে হবে।"
        ),
        objectives=["Write a valid public class Main", "Print exact lines with System.out.println"],
        prereqs=[],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Basic Java output",
        example_code='public class Main {\n    public static void main(String[] args) {\n        System.out.println("Think First");\n    }\n}\n',
        example_input="",
        example_output="Think First",
        example_en="Prints a single line using System.out.println.",
        example_bn="System.out.println দিয়ে এক লাইন আউটপুট দেখায়।",
        prompt_en="Print `Hello Java` on line 1 and `81` (9 * 9) on line 2.",
        prompt_bn="প্রথম লাইনে `Hello Java` এবং দ্বিতীয় লাইনে `81` (9 * 9) প্রিন্ট করো।",
        starter_code='public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello Java");\n        // Print 9 * 9 on line 2\n    }\n}\n',
        reference_solution='public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello Java");\n        System.out.println(9 * 9);\n    }\n}\n',
        test_cases=[("Exact lines", "", "Hello Java\n81")],
        estimated_minutes=10,
    ),
    _lesson(
        slug="java-02-variables-types",
        language_slug="java",
        skill_slug="variables",
        display_order=2,
        title_en="Java 02: Primitive Types, long & String Concatenation",
        title_bn="Java 02: প্রিমিটিভ টাইপ, long এবং স্ট্রিং ফরম্যাটিং",
        summary_en="Declare int/long variables and avoid string-concatenation precedence traps.",
        summary_bn="int/long ভেরিয়েবল ঘোষণা ও স্ট্রিং কনক্যাটেনেশন ত্রুটি এড়ানো শেখো।",
        content_en_md=(
            '## Watch Out for `"Sum: " + a + b`\n'
            'In Java, `"Sum: " + 3 + 4` evaluates left-to-right as `"Sum: 34"`! Wrap arithmetic in '
            'parentheses: `"Sum: " + (a + b)`.'
        ),
        content_bn_md=(
            '## `"Sum: " + a + b` সতর্কতা\n'
            'Java-তে `"Sum: " + 3 + 4` দিলে `"Sum: 34"` হয়! সঠিক যোগফলের জন্য `(a + b)` ব্র্যাকেটে রাখো।'
        ),
        objectives=["Avoid string concatenation traps", "Use long for large integer arithmetic"],
        prereqs=["java-01-hello-main"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Parenthesized arithmetic",
        example_code='public class Main {\n    public static void main(String[] args) {\n        int a = 3, b = 4;\n        System.out.println("Sum=" + (a + b));\n    }\n}\n',
        example_input="",
        example_output="Sum=7",
        example_en="Parentheses ensure integer addition runs before string concatenation.",
        example_bn="ব্র্যাকেট থাকায় আগে যোগ হয়, তারপর স্ট্রিং যুক্ত হয়।",
        prompt_en='Read two `long` integers `a` and `b` and print `(a + b) + " " + (a * b)`.',
        prompt_bn="দুটি `long` পূর্ণসংখ্যা `a` ও `b` পড়ে তাদের যোগফল ও গুণফল এক স্পেস পরপর প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        long a = sc.nextLong();\n        long b = sc.nextLong();\n        // Print sum and product separated by a space\n    }\n}\n",
        reference_solution='import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        long a = sc.nextLong();\n        long b = sc.nextLong();\n        System.out.println((a + b) + " " + (a * b));\n    }\n}\n',
        test_cases=[
            ("Basic pair", "5 6\n", "11 30"),
            ("Negative", "-4 9\n", "5 -36"),
            ("Large long", "100000 100000\n", "200000 10000000000"),
        ],
    ),
    _lesson(
        slug="java-03-scanner-input",
        language_slug="java",
        skill_slug="input_output",
        display_order=3,
        title_en="Java 03: Reading Input Safely with Scanner",
        title_bn="Java 03: Scanner দিয়ে নিরাপদ ইনপুট পড়া",
        summary_en="Use hasNextInt() and nextInt() to read arbitrary-length integer input.",
        summary_bn="hasNextInt() ও nextInt() ব্যবহার করে ইনপুট স্ট্রিম পড়া শেখো।",
        content_en_md=(
            "## Guarding Reads with `sc.hasNextInt()`\n"
            "Calling `sc.nextInt()` when no token remains throws `NoSuchElementException`. Loop with "
            "`while (sc.hasNextInt())` to safely consume every integer on stdin."
        ),
        content_bn_md=(
            "## `sc.hasNextInt()` ব্যবহার\n"
            "ইনপুট শেষ হয়ে গেলে `sc.nextInt()` এরর দেয়। তাই `while (sc.hasNextInt())` লুপ দিয়ে সব সংখ্যা নিরাপদভাবে পড়ো।"
        ),
        objectives=["Import java.util.Scanner", "Read unknown counts of integers safely"],
        prereqs=["java-02-variables-types"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="Counting input tokens",
        example_code="import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int c = 0;\n        while (sc.hasNextInt()) { sc.nextInt(); c++; }\n        System.out.println(c);\n    }\n}\n",
        example_input="3 6 9\n",
        example_output="3",
        example_en="Counts every integer token safely.",
        example_bn="সবকটি পূর্ণসংখ্যা টোকেন নিরাপদভাবে গোনে।",
        prompt_en="Read all integers from stdin using `while (sc.hasNextInt())` and print their sum.",
        prompt_bn="`while (sc.hasNextInt())` ব্যবহার করে ইনপুটের সব পূর্ণসংখ্যার যোগফল প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        long total = 0;\n        // Sum all integers from sc\n        System.out.println(total);\n    }\n}\n",
        reference_solution="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        long total = 0;\n        while (sc.hasNextInt()) {\n            total += sc.nextInt();\n        }\n        System.out.println(total);\n    }\n}\n",
        test_cases=[
            ("Basic list", "2 4 6 8\n", "20"),
            ("Mixed signs", "-3 10 -2\n", "5"),
            ("Single value", "99\n", "99"),
        ],
    ),
    _lesson(
        slug="java-04-conditions-logic",
        language_slug="java",
        skill_slug="conditions",
        display_order=4,
        title_en="Java 04: Conditionals & String .equals() vs ==",
        title_bn="Java 04: শর্ত এবং স্ট্রিং তুলনায় .equals() বনাম ==",
        summary_en="Compare numbers with == and Strings with .equals() to avoid reference bugs.",
        summary_bn="সংখ্যায় == এবং স্ট্রিংয়ে .equals() ব্যবহার করে নির্ভুল শর্ত লেখো।",
        content_en_md=(
            "## Never Compare Java Strings with `==`\n"
            "For `String` objects, `==` checks memory reference identity, NOT text content! Always write "
            '`word.equals("admin")`.'
        ),
        content_bn_md=(
            "## Java-তে স্ট্রিং তুলনায় `.equals()`\n"
            '`String`-এর ক্ষেত্রে `==` মেমোরি ঠিকানা তুলনা করে, লেখা নয়! তাই সবসময় `word.equals("...")` ব্যবহার করো।'
        ),
        objectives=["Use .equals() for String comparison", "Write clean if/else if/else branches"],
        prereqs=["java-03-scanner-input"],
        tracks=["absolute_beginner", "basic_university"],
        example_title="String equality",
        example_code='import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String s = sc.next();\n        System.out.println(s.equals("java") ? "MATCH" : "OTHER");\n    }\n}\n',
        example_input="java\n",
        example_output="MATCH",
        example_en="Uses `.equals()` to compare String contents.",
        example_bn="`.equals()` দিয়ে স্ট্রিংয়ের মান তুলনা করে।",
        prompt_en="Read a single word `cmd`. Print `RUN` if it equals `start`, `HALT` if it equals `stop`, else `UNKNOWN`.",
        prompt_bn="একটি শব্দ `cmd` পড়ো। `start` হলে `RUN`, `stop` হলে `HALT`, নাহলে `UNKNOWN` প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String cmd = sc.next();\n        // Compare cmd with .equals() and print RUN, HALT, or UNKNOWN\n    }\n}\n",
        reference_solution='import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String cmd = sc.next();\n        if (cmd.equals("start")) System.out.println("RUN");\n        else if (cmd.equals("stop")) System.out.println("HALT");\n        else System.out.println("UNKNOWN");\n    }\n}\n',
        test_cases=[
            ("start command", "start\n", "RUN"),
            ("stop command", "stop\n", "HALT"),
            ("other command", "pause\n", "UNKNOWN"),
        ],
    ),
    _lesson(
        slug="java-05-loops-boundaries",
        language_slug="java",
        skill_slug="loops",
        display_order=5,
        title_en="Java 05: Loops & Inclusive Boundary Checks",
        title_bn="Java 05: লুপ এবং সীমানা যাচাই",
        summary_en="Write off-by-one-free for/while loops over numeric intervals in Java.",
        summary_bn="Java-তে নির্ভুল লুপ সীমানা (`<` বনাম `<=`) ব্যবহার শেখো।",
        content_en_md=(
            "## Inclusive Numeric Ranges\n"
            "To process every integer from `a` through `b` inclusive, write `for (int i = a; i <= b; i++)`."
        ),
        content_bn_md=(
            "## উভয় প্রান্তসহ লুপ\n"
            "`a` থেকে `b` পর্যন্ত প্রতিটি সংখ্যার জন্য `for (int i = a; i <= b; i++)` ব্যবহার করো।"
        ),
        objectives=["Use <= for inclusive ranges", "Accumulate in long to avoid overflow"],
        prereqs=["java-04-conditions-logic"],
        tracks=["absolute_beginner", "basic_university", "intermediate"],
        example_title="Inclusive sum",
        example_code="public class Main {\n    public static void main(String[] args) {\n        int s = 0;\n        for (int i = 3; i <= 5; i++) s += i;\n        System.out.println(s);\n    }\n}\n",
        example_input="",
        example_output="12",
        example_en="Adds 3 + 4 + 5 = 12.",
        example_bn="৩ + ৪ + ৫ = ১২ যোগ করে।",
        prompt_en="Read two integers `a` and `b` (`a <= b`) and print the inclusive sum of all integers from `a` to `b`.",
        prompt_bn="দুটি পূর্ণসংখ্যা `a` ও `b` (`a <= b`) পড়ে `a` থেকে `b` পর্যন্ত সব পূর্ণসংখ্যার যোগফল প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int a = sc.nextInt();\n        int b = sc.nextInt();\n        long total = 0;\n        // Sum from a to b inclusive\n        System.out.println(total);\n    }\n}\n",
        reference_solution="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int a = sc.nextInt();\n        int b = sc.nextInt();\n        long total = 0;\n        for (int i = a; i <= b; i++) {\n            total += i;\n        }\n        System.out.println(total);\n    }\n}\n",
        test_cases=[
            ("Range 3..5", "3 5\n", "12"),
            ("Single number", "1 1\n", "1"),
            ("Negative range", "-5 -3\n", "-12"),
        ],
    ),
    _lesson(
        slug="java-06-arrays-arraylist",
        language_slug="java",
        skill_slug="lists",
        display_order=6,
        title_en="Java 06: ArrayList & Safe Extremum Initialization",
        title_bn="Java 06: ArrayList এবং নিরাপদ সর্বোচ্চ/সর্বনিম্ন মান",
        summary_en="Collect dynamic integers into ArrayList<Integer> and initialize extrema from list.get(0).",
        summary_bn="ArrayList<Integer>-এ সংখ্যা রেখে list.get(0) দিয়ে নিরাপদ মান বের করো।",
        content_en_md=(
            "## `ArrayList<Integer>`\n"
            "Use `ArrayList<Integer>` when you don't know the count upfront, and initialize `int best = list.get(0);` "
            "instead of `0` so negative inputs are never distorted."
        ),
        content_bn_md=(
            "## `ArrayList<Integer>` ব্যবহার\n"
            "আগে থেকে সংখ্যা জানা না থাকলে `ArrayList<Integer>` ব্যবহার করো এবং `best = list.get(0)` দিয়ে শুরু করো।"
        ),
        objectives=[
            "Populate ArrayList<Integer> from Scanner",
            "Initialize extrema from the first element",
        ],
        prereqs=["java-05-loops-boundaries"],
        tracks=["absolute_beginner", "basic_university", "intermediate"],
        example_title="ArrayList traversal",
        example_code="import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        ArrayList<Integer> a = new ArrayList<>(Arrays.asList(-5, -2, -9));\n        int best = a.get(0);\n        for (int x : a) if (x > best) best = x;\n        System.out.println(best);\n    }\n}\n",
        example_input="",
        example_output="-2",
        example_en="Correctly returns -2 for an all-negative list.",
        example_bn="সব ঋণাত্মক তালিকায় সঠিক মান -2 দেয়।",
        prompt_en="Read space-separated integers into an `ArrayList<Integer>` and print the **minimum** value.",
        prompt_bn="স্পেস-সেপারেটেড পূর্ণসংখ্যাগুলো `ArrayList<Integer>`-এ পড়ে **সর্বনিম্ন** মানটি প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        ArrayList<Integer> nums = new ArrayList<>();\n        while (sc.hasNextInt()) nums.add(sc.nextInt());\n        // Find and print the minimum element\n    }\n}\n",
        reference_solution="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        ArrayList<Integer> nums = new ArrayList<>();\n        while (sc.hasNextInt()) nums.add(sc.nextInt());\n        int best = nums.get(0);\n        for (int i = 1; i < nums.size(); i++) {\n            if (nums.get(i) < best) best = nums.get(i);\n        }\n        System.out.println(best);\n    }\n}\n",
        test_cases=[
            ("All positive", "18 24 15 30\n", "15"),
            ("All negative", "-4 -12 -7\n", "-12"),
            ("Single value", "42\n", "42"),
        ],
    ),
    _lesson(
        slug="java-07-indexing-bounds",
        language_slug="java",
        skill_slug="indexing",
        display_order=7,
        title_en="Java 07: Array Bounds & Preventing ArrayIndexOutOfBoundsException",
        title_bn="Java 07: অ্যারে সীমা ও ArrayIndexOutOfBoundsException এড়ানো",
        summary_en="Keep every Java index strictly inside 0..length-1 when traversing or comparing pairs.",
        summary_bn="০ থেকে length-1 সীমার মধ্যে ইনডেক্স রেখে Java ইনডেক্স এক্সেপশন এড়াও।",
        content_en_md=(
            "## Java Enforces Strict Bounds Checking\n"
            "Accessing `arr[arr.length]` immediately throws `ArrayIndexOutOfBoundsException`. For adjacent "
            "comparisons `arr[i]` and `arr[i + 1]`, loop while `i < arr.length - 1`."
        ),
        content_bn_md=(
            "## Java-তে কঠোর ইনডেক্স যাচাই\n"
            "`arr[arr.length]` পড়লে `ArrayIndexOutOfBoundsException` হয়। পাশাপাশি জোড়া দেখতে `i < arr.length - 1` ব্যবহার করো।"
        ),
        objectives=[
            "Respect 0..length-1 bounds",
            "Avoid IndexOutOfBounds exceptions in adjacent scans",
        ],
        prereqs=["java-06-arrays-arraylist"],
        tracks=["basic_university", "intermediate"],
        example_title="Safe pair scan",
        example_code="public class Main {\n    public static void main(String[] args) {\n        int[] a = {2, 5, 4, 9};\n        int cnt = 0;\n        for (int i = 0; i < a.length - 1; i++) if (a[i + 1] > a[i]) cnt++;\n        System.out.println(cnt);\n    }\n}\n",
        example_input="",
        example_output="2",
        example_en="Safely scans all adjacent pairs.",
        example_bn="নিরাপদভাবে পাশাপাশি জোড়াগুলো যাচাই করে।",
        prompt_en="Read integers into an `ArrayList<Integer>` and count how many adjacent pairs satisfy `nums.get(i + 1) > nums.get(i)`.",
        prompt_bn="পূর্ণসংখ্যাগুলো পড়ে কতটি পাশাপাশি জোড়ায় পরের সংখ্যাটি আগেরটির চেয়ে বড় (`nums.get(i + 1) > nums.get(i)`) তা প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        ArrayList<Integer> nums = new ArrayList<>();\n        while (sc.hasNextInt()) nums.add(sc.nextInt());\n        int count = 0;\n        // Count strictly increasing adjacent pairs\n        System.out.println(count);\n    }\n}\n",
        reference_solution="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        ArrayList<Integer> nums = new ArrayList<>();\n        while (sc.hasNextInt()) nums.add(sc.nextInt());\n        int count = 0;\n        for (int i = 0; i < nums.size() - 1; i++) {\n            if (nums.get(i + 1) > nums.get(i)) count++;\n        }\n        System.out.println(count);\n    }\n}\n",
        test_cases=[
            ("Mixed", "1 3 2 5 6\n", "3"),
            ("Decreasing", "8 6 4 2\n", "0"),
            ("Single", "10\n", "0"),
        ],
    ),
    _lesson(
        slug="java-08-methods-returns",
        language_slug="java",
        skill_slug="functions",
        display_order=8,
        title_en="Java 08: Static Methods & Return Statements",
        title_bn="Java 08: স্ট্যাটিক মেথড ও Return স্টেটমেন্ট",
        summary_en="Write clean static helper methods and guarantee a return on every branch.",
        summary_bn="পরিষ্কার স্ট্যাটিক হেল্পার মেথড লেখা এবং সব শাখায় return নিশ্চিত করা শেখো।",
        content_en_md=(
            "## Static Methods Inside `Main`\n"
            "Because `main` is `static`, helper methods called directly from `main` are also declared "
            "`static` (e.g. `static boolean isPrime(int n)`)."
        ),
        content_bn_md=(
            "## `Main` ক্লাসের ভেতর স্ট্যাটিক মেথড\n"
            "`main` স্ট্যাটিক হওয়ায় সরাসরি কল করার হেল্পার মেথডও `static` হিসেবে ঘোষণা করতে হয়।"
        ),
        objectives=["Declare static helper methods", "Return correct types along all code paths"],
        prereqs=["java-07-indexing-bounds"],
        tracks=["basic_university", "intermediate"],
        example_title="Static helper method",
        example_code="public class Main {\n    static int cube(int x) { return x * x * x; }\n    public static void main(String[] args) { System.out.println(cube(3)); }\n}\n",
        example_input="",
        example_output="27",
        example_en="Calls static helper cube(3).",
        example_bn="স্ট্যাটিক হেল্পার cube(3) কল করে।",
        prompt_en="Complete `static long sumEvens(List<Integer> nums)` to return the sum of all even integers.",
        prompt_bn="`static long sumEvens(List<Integer> nums)` মেথড সম্পূর্ণ করে সব জোড় সংখ্যার যোগফল প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    static long sumEvens(List<Integer> nums) {\n        // Return sum of all even integers\n        return 0;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        List<Integer> nums = new ArrayList<>();\n        while (sc.hasNextInt()) nums.add(sc.nextInt());\n        System.out.println(sumEvens(nums));\n    }\n}\n",
        reference_solution="import java.util.*;\n\npublic class Main {\n    static long sumEvens(List<Integer> nums) {\n        long total = 0;\n        for (int x : nums) {\n            if (x % 2 == 0) total += x;\n        }\n        return total;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        List<Integer> nums = new ArrayList<>();\n        while (sc.hasNextInt()) nums.add(sc.nextInt());\n        System.out.println(sumEvens(nums));\n    }\n}\n",
        test_cases=[
            ("Mixed", "1 2 3 4 5 6\n", "12"),
            ("Odd only", "1 3 5 7\n", "0"),
            ("Negative evens", "-4 -3 -2 0\n", "-6"),
        ],
    ),
    _lesson(
        slug="java-09-debugging-javac-exceptions",
        language_slug="java",
        skill_slug="debugging_basics",
        display_order=9,
        title_en="Java 09: Reading javac Compiler Errors & Runtime Exceptions",
        title_bn="Java 09: javac কম্পাইলার এরর ও রানটাইম এক্সেপশন ডিবাগিং",
        summary_en="Diagnose missing semicolons, missing return statements, and off-by-one bugs in Java.",
        summary_bn="javac এরর, missing return এবং অফ-বাই-ওয়ান বাগ ঠিক করা শেখো।",
        content_en_md=(
            "## Reading `javac` Messages\n"
            "Java clearly reports exact file & line numbers like `Main.java:8: error: ';' expected` or "
            "`missing return statement`. Fix compiler errors first, then check edge cases."
        ),
        content_bn_md=(
            "## `javac` এরর পড়া\n"
            "Java স্পষ্টভাবে লাইন নম্বরসহ এরর দেখায়। আগে কম্পাইলার এরর ঠিক করো, তারপর এজ-কেস যাচাই করো।"
        ),
        objectives=["Fix javac syntax errors", "Fix loop boundary off-by-one bugs"],
        prereqs=["java-08-methods-returns"],
        tracks=["basic_university", "intermediate", "advanced"],
        example_title="Clean factorial",
        example_code="public class Main {\n    public static void main(String[] args) {\n        long f = 1;\n        for (int i = 1; i <= 4; i++) f *= i;\n        System.out.println(f);\n    }\n}\n",
        example_input="",
        example_output="24",
        example_en="Computes 4! = 24.",
        example_bn="৪! = ২৪ হিসাব করে।",
        prompt_en="Fix the buggy Java starter code (missing semicolon, `fact = 0`, and `<` instead of `<=`) to print `n!` for `0 <= n <= 12`.",
        prompt_bn="বাগযুক্ত Java কোডটি ঠিক করে `0 <= n <= 12`-এর ফ্যাক্টোরিয়াল `n!` প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long fact = 0;\n        for (int i = 1; i < n; i++) {\n            fact *= i;\n        }\n        System.out.println(fact)\n    }\n}\n",
        reference_solution="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        long fact = 1;\n        for (int i = 1; i <= n; i++) {\n            fact *= i;\n        }\n        System.out.println(fact);\n    }\n}\n",
        test_cases=[
            ("5!", "5\n", "120"),
            ("0! boundary", "0\n", "1"),
            ("1!", "1\n", "1"),
        ],
    ),
    _lesson(
        slug="java-10-mixed-problem-solving",
        language_slug="java",
        skill_slug="mixed_problem_solving",
        display_order=10,
        title_en="Java 10: Mixed Problem Solving with TreeMap & Methods",
        title_bn="Java 10: TreeMap ও মেথড দিয়ে সমন্বিত Java সমস্যা সমাধান",
        summary_en="Use TreeMap<String, Integer> to count word frequencies in sorted alphabetical order.",
        summary_bn="TreeMap ব্যবহার করে বর্ণানুক্রমে শব্দের ফ্রিকোয়েন্সি নির্ণয় করো।",
        content_en_md=(
            "## Sorted Counting with `TreeMap`\n"
            "`TreeMap<String, Integer>` keeps keys sorted alphabetically, and `freq.getOrDefault(w, 0) + 1` "
            "updates counts cleanly without null-pointer exceptions."
        ),
        content_bn_md=(
            "## `TreeMap` দিয়ে সাজানো কাউন্টিং\n"
            "`TreeMap` কীগুলো বর্ণানুক্রমে রাখে এবং `getOrDefault(w, 0) + 1` দিয়ে নিরাপদভাবে সংখ্যা বাড়ানো যায়।"
        ),
        objectives=["Count tokens using TreeMap", "Avoid NullPointerException with getOrDefault"],
        prereqs=["java-09-debugging-javac-exceptions"],
        tracks=["intermediate", "advanced"],
        example_title="TreeMap count",
        example_code='import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        TreeMap<String, Integer> m = new TreeMap<>();\n        m.put("b", 1); m.put("a", 2);\n        for (Map.Entry<String, Integer> e : m.entrySet()) System.out.println(e.getKey() + ":" + e.getValue());\n    }\n}\n',
        example_input="",
        example_output="a:2\nb:1",
        example_en="Outputs keys in ascending alphabetical order.",
        example_bn="বর্ণানুক্রমে কী ও মান প্রিন্ট করে।",
        prompt_en="Read words from stdin and print each unique word and its count as `word:count` sorted alphabetically.",
        prompt_bn="ইনপুট থেকে শব্দগুলো পড়ে বর্ণানুক্রমে `word:count` আকারে প্রিন্ট করো।",
        starter_code="import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        TreeMap<String, Integer> freq = new TreeMap<>();\n        // Read words with sc.hasNext() and print sorted word:count lines\n    }\n}\n",
        reference_solution='import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        TreeMap<String, Integer> freq = new TreeMap<>();\n        while (sc.hasNext()) {\n            String w = sc.next();\n            freq.put(w, freq.getOrDefault(w, 0) + 1);\n        }\n        for (Map.Entry<String, Integer> entry : freq.entrySet()) {\n            System.out.println(entry.getKey() + ":" + entry.getValue());\n        }\n    }\n}\n',
        test_cases=[
            ("Repeated", "code think code learn\n", "code:2\nlearn:1\nthink:1"),
            ("Single", "java\n", "java:1"),
            ("Reverse", "zeta beta alpha\n", "alpha:1\nbeta:1\nzeta:1"),
        ],
    ),
]

ALL_MULTILANG_LESSONS: list[dict[str, Any]] = (
    JAVASCRIPT_LESSONS + C_LESSONS + CPP_LESSONS + JAVA_LESSONS
)
