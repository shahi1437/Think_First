-- =============================================================================
-- Seed 003: 4 Learning Tracks, 10 Skill Graph Nodes + DAG Prerequisites,
--           8 Bilingual Beginner Python Lessons (with Real Judge0 Exercises),
--           and 18 Admin-Reviewed Diagnostic Questions Across All 8 Domains
-- =============================================================================

-- 1. Four Learning Tracks
INSERT INTO public.learning_tracks (
    slug, title_en, title_bn, summary_en, summary_bn,
    target_audience_en, target_audience_bn, display_order, recommended_focus_skills
)
VALUES
(
    'absolute_beginner',
    'Absolute Beginner',
    'একদম নতুন শিক্ষার্থী',
    'Start from zero coding background with step-by-step Python concepts, guided examples, and real code execution.',
    'একদম শূন্য থেকে ধাপে ধাপে Python প্রোগ্রামিং, উদাহরণ এবং আসল কোড রান করে শেখা শুরু করো।',
    'School students and learners who have never written code before.',
    'স্কুল শিক্ষার্থী এবং যারা আগে কখনো কোড লেখেনি।',
    1,
    ARRAY['programming_basics', 'variables', 'input_output', 'conditions', 'loops']
),
(
    'basic_university',
    'Basic University',
    'বেসিক ইউনিভার্সিটি ট্র্যাক',
    'Build solid university programming fundamentals across loops, lists, indexing, functions, and runtime debugging.',
    'লুপ, লিস্ট, ইনডেক্সিং, ফাংশন এবং রানটাইম ডিবাগিংয়ে মজবুত বিশ্ববিদ্যালয় পর্যায়ের ভিত্তি গড়ো।',
    'CSE/SWE/IT university students with limited hands-on coding experience.',
    'CSE/SWE/IT বিশ্ববিদ্যালয়ের শিক্ষার্থী যাদের প্র্যাকটিক্যাল কোডিং অভিজ্ঞতা কম।',
    2,
    ARRAY['conditions', 'loops', 'lists', 'indexing', 'functions', 'debugging_basics']
),
(
    'intermediate',
    'Intermediate',
    'ইন্টারমিডিয়েট ট্র্যাক',
    'Strengthen boundary reasoning, safe initialization, systematic debugging, and independent transfer problem solving.',
    'বাউন্ডারি বিশ্লেষণ, সঠিক ভেরিয়েবল ইনিশিয়ালাইজেশন, ডিবাগিং এবং স্বাধীন সমস্যা সমাধানে দক্ষতা বাড়াও।',
    'Learners comfortable with Python syntax who want stronger debugging and logic reliability.',
    'যারা Python সিনট্যাক্স জানে এবং ডিবাগিং ও লজিকে আরও দক্ষ হতে চায়।',
    3,
    ARRAY['loops', 'indexing', 'functions', 'debugging_basics', 'mixed_problem_solving']
),
(
    'advanced',
    'Advanced',
    'অ্যাডভান্সড ট্র্যাক',
    'Tackle complex edge-case debugging, invariant checks, and zero-hint independent transfer verification challenges.',
    'জটিল এজ-কেস ডিবাগিং, ইনভ্যারিয়েন্ট যাচাই এবং হিন্ট ছাড়া স্বাধীন ট্রান্সফার চ্যালেঞ্জ সমাধান করো।',
    'Experienced learners focused on rigorous debugging and multi-step algorithmic reasoning.',
    'অভিজ্ঞ প্রোগ্রামার যারা গভীর ডিবাগিং এবং জটিল সমস্যা সমাধানে মনোযোগী।',
    4,
    ARRAY['debugging_basics', 'mixed_problem_solving']
)
ON CONFLICT (slug) DO UPDATE SET
    title_en = EXCLUDED.title_en,
    title_bn = EXCLUDED.title_bn,
    summary_en = EXCLUDED.summary_en,
    summary_bn = EXCLUDED.summary_bn,
    target_audience_en = EXCLUDED.target_audience_en,
    target_audience_bn = EXCLUDED.target_audience_bn,
    display_order = EXCLUDED.display_order,
    recommended_focus_skills = EXCLUDED.recommended_focus_skills;

-- 2. Skill Graph Nodes (10 prerequisite-linked concepts)
INSERT INTO public.skill_nodes (
    slug, title_en, title_bn, description_en, description_bn, domain_slug, tier, display_order
)
VALUES
('programming_basics', 'Programming Basics', 'প্রোগ্রামিংয়ের মূল ধারণা', 'Sequential execution, print statements, and reading program flow.', 'ধাপে ধাপে কোড চলা, print স্টেটমেন্ট এবং প্রোগ্রামের প্রবাহ বোঝা।', 'variables', 1, 1),
('variables', 'Variables & Data Types', 'ভেরিয়েবল ও ডেটা টাইপ', 'Storing numbers/strings, type conversion, and safe accumulator initialization.', 'সংখ্যা/স্ট্রিং সংরক্ষণ, টাইপ রূপান্তর এবং সঠিক ইনিশিয়ালাইজেশন।', 'variables', 1, 2),
('input_output', 'Input & Output', 'ইনপুট ও আউটপুট', 'Reading stdin safely with input(), split(), and int() and formatting output.', 'input(), split() ও int() দিয়ে নিরাপদে ইনপুট পড়া ও আউটপুট দেখানো।', 'variables', 1, 3),
('conditions', 'Conditions & Branching', 'শর্ত ও ব্রাঞ্চিং (if/elif/else)', 'Comparing values (<, <=, ==), boolean operators (and/or), and branch order.', 'তুলনা চিহ্ন (<, <=, ==), বুলিয়ান অপারেটর (and/or) এবং শাখার ক্রম।', 'conditions', 2, 4),
('loops', 'Loops & Boundaries', 'লুপ ও বাউন্ডারি', 'for/while iteration, Python range() exclusive stop bounds, and off-by-one reasoning.', 'for/while লুপ, Python range()-এর শেষ সীমা এবং অফ-বাই-ওয়ান বিশ্লেষণ।', 'loop_boundaries', 2, 5),
('lists', 'Arrays & Lists', 'লিস্ট ও অ্যারে', 'Building, scanning, filtering, and aggregating Python lists safely.', 'Python লিস্ট তৈরি, স্ক্যান, ফিল্টার এবং যোগফল/সর্বোচ্চ মান নির্ণয়।', 'arrays_lists', 3, 6),
('indexing', '0-Based Indexing', '০-ভিত্তিক ইনডেক্সিং', 'Valid indices 0..len-1, adjacent pair checks, and avoiding IndexError.', 'বৈধ ইনডেক্স 0..len-1, পাশাপাশি উপাদান তুলনা এবং IndexError প্রতিরোধ।', 'indexing', 3, 7),
('functions', 'Functions & Returns', 'ফাংশন ও রিটার্ন', 'Parameters, return values vs print(), and avoiding early returns inside loops.', 'প্যারামিটার, print বনাম return এবং লুপের ভেতরে অকাল return এড়ানো।', 'functions', 3, 8),
('debugging_basics', 'Syntax & Runtime Debugging', 'সিনট্যাক্স ও রানটাইম ডিবাগিং', 'Reading tracebacks, fixing SyntaxError/TypeError/NameError, and state-table tracing.', 'Traceback পড়া, SyntaxError/TypeError/NameError ঠিক করা এবং হাতে ট্রেস করা।', 'syntax_runtime_debugging', 4, 9),
('mixed_problem_solving', 'Mixed Problem-Solving Logic', 'মিশ্র সমস্যা সমাধানের লজিক', 'Combining loops, conditions, lists, and functions under unseen edge cases.', 'লুপ, শর্ত, লিস্ট ও ফাংশন একত্রে ব্যবহার করে নতুন এজ-কেস সমাধান।', 'mixed_logic', 5, 10)
ON CONFLICT (slug) DO UPDATE SET
    title_en = EXCLUDED.title_en,
    title_bn = EXCLUDED.title_bn,
    description_en = EXCLUDED.description_en,
    description_bn = EXCLUDED.description_bn,
    domain_slug = EXCLUDED.domain_slug,
    tier = EXCLUDED.tier,
    display_order = EXCLUDED.display_order;

-- Prerequisite DAG Edges
INSERT INTO public.skill_prerequisites (skill_slug, prerequisite_slug)
VALUES
    ('variables', 'programming_basics'),
    ('input_output', 'variables'),
    ('conditions', 'variables'),
    ('conditions', 'input_output'),
    ('loops', 'variables'),
    ('loops', 'conditions'),
    ('lists', 'loops'),
    ('indexing', 'lists'),
    ('functions', 'conditions'),
    ('functions', 'loops'),
    ('debugging_basics', 'variables'),
    ('debugging_basics', 'conditions'),
    ('debugging_basics', 'loops'),
    ('mixed_problem_solving', 'indexing'),
    ('mixed_problem_solving', 'functions'),
    ('mixed_problem_solving', 'debugging_basics')
ON CONFLICT DO NOTHING;

-- 3. Eight Bilingual Beginner Python Lessons (with Real Judge0 Guided Exercises)
DO $$
DECLARE
    v_lesson_id uuid;
    v_ver_id uuid;
BEGIN
    -- Lesson 1: Introduction to Programming
    INSERT INTO public.lessons (slug, skill_slug, display_order)
    VALUES ('intro-to-programming', 'programming_basics', 1)
    ON CONFLICT (slug) DO UPDATE SET display_order = EXCLUDED.display_order
    RETURNING id INTO v_lesson_id;

    INSERT INTO public.lesson_versions (
        lesson_id, version_number, title_en, title_bn, summary_en, summary_bn,
        content_en_md, content_bn_md, learning_objectives, prerequisite_lesson_slugs,
        track_slugs, interactive_examples, guided_exercise, estimated_minutes, status, published_at
    )
    VALUES (
        v_lesson_id, 1,
        'Introduction to Programming & Python Execution',
        'প্রোগ্রামিং পরিচিতি ও Python কীভাবে কোড চালায়',
        'Understand how a computer executes Python instructions top-to-bottom and produces exact output.',
        'কম্পিউটার কীভাবে উপর থেকে নিচে Python নির্দেশনা চালায় এবং সঠিক আউটপুট তৈরি করে তা শেখো।',
        E'## What Is a Program?\nA program is a precise, ordered sequence of instructions executed one line at a time.\n\n## Printing Exact Output\nIn Python, `print(...)` writes text or numbers to standard output (`stdout`). Notice that automated judges compare your output character-by-character.\n\n```python\nprint("Think First")\nprint(2 + 3)\n```\n\n## Think Before Running\nBefore clicking **Run Exercise**, predict what each line will print in order.',
        E'## প্রোগ্রাম কী?\nপ্রোগ্রাম হলো ধারাবাহিক কিছু সুনির্দিষ্ট নির্দেশনা যা কম্পিউটার এক লাইন পর এক লাইন চালায়।\n\n## সঠিক আউটপুট প্রিন্ট করা\nPython-এ `print(...)` ফাংশন আউটপুট দেখায়। অটোমেটেড জাজ প্রতিটি অক্ষর মিলিয়ে দেখে।\n\n```python\nprint("Think First")\nprint(2 + 3)\n```\n\n## চালানোর আগে ভাবো\n**Run Exercise** চাপার আগে নিজে অনুমান করো কোন লাইন কী প্রিন্ট করবে।',
        ARRAY['Trace top-to-bottom Python execution', 'Use print() to display exact text and arithmetic results'],
        ARRAY[]::text[],
        ARRAY['absolute_beginner'],
        '[{"title":"Two sequential print statements","code":"print(\"Hello\")\nprint(10 + 5)","input_data":"","expected_output":"Hello\n15","explanation_en":"Python runs line 1 first, then evaluates 10 + 5 on line 2.","explanation_bn":"প্রথমে প্রথম লাইন চলে, তারপর দ্বিতীয় লাইনে 10 + 5 হিসাব হয়ে 15 প্রিন্ট হয়।"}]'::jsonb,
        '{"prompt_en":"Write a Python program that prints `CodeMentor` on the first line and the result of `6 * 7` (`42`) on the second line.","prompt_bn":"এমন একটি Python প্রোগ্রাম লেখো যা প্রথম লাইনে `CodeMentor` এবং দ্বিতীয় লাইনে `6 * 7` (অর্থাৎ `42`) প্রিন্ট করে।","language_slug":"python","starter_code":"# Print CodeMentor on line 1 and 6 * 7 on line 2\nprint(\"CodeMentor\")\n","test_cases":[{"name":"Exact two-line output","input_data":"","expected_output":"CodeMentor\n42"}]}'::jsonb,
        10, 'published', now()
    )
    ON CONFLICT (lesson_id, version_number) DO UPDATE SET
        title_en = EXCLUDED.title_en, title_bn = EXCLUDED.title_bn,
        summary_en = EXCLUDED.summary_en, summary_bn = EXCLUDED.summary_bn,
        content_en_md = EXCLUDED.content_en_md, content_bn_md = EXCLUDED.content_bn_md,
        interactive_examples = EXCLUDED.interactive_examples,
        guided_exercise = EXCLUDED.guided_exercise, status = 'published', published_at = COALESCE(public.lesson_versions.published_at, now())
    RETURNING id INTO v_ver_id;
    UPDATE public.lessons SET current_published_version_id = v_ver_id WHERE id = v_lesson_id;

    -- Lesson 2: Variables & Data Types
    INSERT INTO public.lessons (slug, skill_slug, display_order)
    VALUES ('variables-and-data-types', 'variables', 2)
    ON CONFLICT (slug) DO UPDATE SET display_order = EXCLUDED.display_order
    RETURNING id INTO v_lesson_id;

    INSERT INTO public.lesson_versions (
        lesson_id, version_number, title_en, title_bn, summary_en, summary_bn,
        content_en_md, content_bn_md, learning_objectives, prerequisite_lesson_slugs,
        track_slugs, interactive_examples, guided_exercise, estimated_minutes, status, published_at
    )
    VALUES (
        v_lesson_id, 1,
        'Variables, Data Types & Safe Initialization',
        'ভেরিয়েবল, ডেটা টাইপ এবং সঠিক ইনিশিয়ালাইজেশন',
        'Store integers, floats, and strings cleanly and avoid str/int TypeError mistakes.',
        'পূর্ণসংখ্যা, দশমিক সংখ্যা ও স্ট্রিং সংরক্ষণ করো এবং str/int টাইপ এরর এড়াও।',
        E'## Naming & Updating Variables\nA variable binds a clear name to a value in memory: `price = 50`, `quantity = 3`, `total = price * quantity`.\n\n## Common Beginner Mistake: String vs Integer\n`\"5\" + \"3\"` produces `\"53\"` (string concatenation), while `5 + 3` produces `8` (integer addition). Mixing `\"5\" + 3` raises `TypeError`.\n\n## Identity Starting Values\nSums start at `0`; products start at `1`.',
        E'## ভেরিয়েবল তৈরি ও আপডেট করা\nভেরিয়েবল কোনো মানকে একটি নামের সাথে যুক্ত করে: `price = 50`, `quantity = 3`, `total = price * quantity`।\n\n## সাধারণ ভুল: স্ট্রিং বনাম পূর্ণসংখ্যা\n`\"5\" + \"3\"` এর ফল `\"53\"`, কিন্তু `5 + 3` এর ফল `8`। স্ট্রিং আর সংখ্যা সরাসরি যোগ করলে `TypeError` হয়।\n\n## নিরাপদ শুরুর মান\nযোগফলের শুরু `0` এবং গুণফলের শুরু `1` হওয়া উচিত।',
        ARRAY['Distinguish int, float, and str types in Python', 'Convert numeric strings with int() before arithmetic'],
        ARRAY['intro-to-programming'],
        ARRAY['absolute_beginner', 'basic_university'],
        '[{"title":"Converting text to integer","code":"a = int(\"12\")\nb = int(\"8\")\nprint(a + b)","input_data":"","expected_output":"20","explanation_en":"int() converts numeric text so + performs addition instead of concatenation.","explanation_bn":"int() স্ট্রিংকে পূর্ণসংখ্যায় রূপান্তর করে যাতে + যোগফল হিসাব করে।"}]'::jsonb,
        '{"prompt_en":"Read two integers on separate lines (`price` and `count`) and print their total cost (`price * count`).","prompt_bn":"দুটি আলাদা লাইনে দুটি পূর্ণসংখ্যা (`price` এবং `count`) পড়ে তাদের গুণফল (`price * count`) প্রিন্ট করো।","language_slug":"python","starter_code":"price = int(input())\ncount = int(input())\n# Compute and print total cost\n","test_cases":[{"name":"Basic multiplication","input_data":"15\n4","expected_output":"60"},{"name":"Zero count","input_data":"25\n0","expected_output":"0"}]}'::jsonb,
        12, 'published', now()
    )
    ON CONFLICT (lesson_id, version_number) DO UPDATE SET
        title_en = EXCLUDED.title_en, title_bn = EXCLUDED.title_bn,
        summary_en = EXCLUDED.summary_en, summary_bn = EXCLUDED.summary_bn,
        content_en_md = EXCLUDED.content_en_md, content_bn_md = EXCLUDED.content_bn_md,
        interactive_examples = EXCLUDED.interactive_examples,
        guided_exercise = EXCLUDED.guided_exercise, status = 'published', published_at = COALESCE(public.lesson_versions.published_at, now())
    RETURNING id INTO v_ver_id;
    UPDATE public.lessons SET current_published_version_id = v_ver_id WHERE id = v_lesson_id;

    -- Lesson 3: Input & Output
    INSERT INTO public.lessons (slug, skill_slug, display_order)
    VALUES ('input-and-output', 'input_output', 3)
    ON CONFLICT (slug) DO UPDATE SET display_order = EXCLUDED.display_order
    RETURNING id INTO v_lesson_id;

    INSERT INTO public.lesson_versions (
        lesson_id, version_number, title_en, title_bn, summary_en, summary_bn,
        content_en_md, content_bn_md, learning_objectives, prerequisite_lesson_slugs,
        track_slugs, interactive_examples, guided_exercise, estimated_minutes, status, published_at
    )
    VALUES (
        v_lesson_id, 1,
        'Reading Input & Formatting Clean Output',
        'ইনপুট পড়া ও পরিষ্কার আউটপুট ফরম্যাটিং',
        'Parse single-line and space-separated inputs cleanly with input().split() and map(int, ...).',
        'এক লাইনে স্পেস দিয়ে আলাদা করা ইনপুট `input().split()` এবং `map(int, ...)` দিয়ে পড়তে শেখো।',
        E'## Reading Multiple Numbers on One Line\nIn programming challenges, two integers often appear on a single line like `7 5`:\n```python\na, b = map(int, input().split())\nprint(a + b)\n```\n\n## Avoid Extra Prompt Text in `input()`\nNever pass `"Enter a number: "` inside `input()` for judged exercises, because that extra text gets printed to stdout and causes `Wrong Answer`.',
        E'## একই লাইনে একাধিক সংখ্যা পড়া\nপ্রোগ্রামিং সমস্যায় প্রায়ই এক লাইনে `7 5` এর মতো দুটি সংখ্যা দেওয়া থাকে:\n```python\na, b = map(int, input().split())\nprint(a + b)\n```\n\n## সতর্কতা\nজাজড প্র্যাকটিসে `input()`-এর ভেতরে অতিরিক্ত টেক্সট (যেমন `"Enter: "`) লিখবে না, এতে আউটপুট মিলবে না।',
        ARRAY['Parse space-separated integers on one line', 'Produce exact stdout without stray prompt strings'],
        ARRAY['variables-and-data-types'],
        ARRAY['absolute_beginner', 'basic_university'],
        '[{"title":"Two numbers on one line","code":"x, y = map(int, input().split())\nprint(x - y)","input_data":"10 4","expected_output":"6","explanation_en":"split() breaks \"10 4\" into [\"10\", \"4\"] and map(int, ...) converts both.","explanation_bn":"split() লাইনটিকে ভাগ করে এবং map(int, ...) দুটিকেই সংখ্যায় রূপান্তর করে।"}]'::jsonb,
        '{"prompt_en":"Read three space-separated integers `a b c` on one line and print their sum `a + b + c`.","prompt_bn":"এক লাইনে স্পেস দিয়ে আলাদা করা তিনটি পূর্ণসংখ্যা `a b c` পড়ে তাদের যোগফল প্রিন্ট করো।","language_slug":"python","starter_code":"a, b, c = map(int, input().split())\n# Print the sum of a, b, and c\n","test_cases":[{"name":"Positive integers","input_data":"2 5 8","expected_output":"15"},{"name":"Includes negative","input_data":"-3 10 3","expected_output":"10"}]}'::jsonb,
        12, 'published', now()
    )
    ON CONFLICT (lesson_id, version_number) DO UPDATE SET
        title_en = EXCLUDED.title_en, title_bn = EXCLUDED.title_bn,
        summary_en = EXCLUDED.summary_en, summary_bn = EXCLUDED.summary_bn,
        content_en_md = EXCLUDED.content_en_md, content_bn_md = EXCLUDED.content_bn_md,
        interactive_examples = EXCLUDED.interactive_examples,
        guided_exercise = EXCLUDED.guided_exercise, status = 'published', published_at = COALESCE(public.lesson_versions.published_at, now())
    RETURNING id INTO v_ver_id;
    UPDATE public.lessons SET current_published_version_id = v_ver_id WHERE id = v_lesson_id;

    -- Lesson 4: Conditions & Branching
    INSERT INTO public.lessons (slug, skill_slug, display_order)
    VALUES ('conditions-and-branching', 'conditions', 4)
    ON CONFLICT (slug) DO UPDATE SET display_order = EXCLUDED.display_order
    RETURNING id INTO v_lesson_id;

    INSERT INTO public.lesson_versions (
        lesson_id, version_number, title_en, title_bn, summary_en, summary_bn,
        content_en_md, content_bn_md, learning_objectives, prerequisite_lesson_slugs,
        track_slugs, interactive_examples, guided_exercise, estimated_minutes, status, published_at
    )
    VALUES (
        v_lesson_id, 1,
        'Conditions, Boundary Comparisons & Boolean Logic',
        'শর্ত, বাউন্ডারি তুলনা এবং বুলিয়ান লজিক',
        'Master if/elif/else, strict vs inclusive operators (< vs <=), and exact boundary checking.',
        'if/elif/else, `<` বনাম `<=` তুলনা এবং সঠিক বাউন্ডারি পরীক্ষা করা শেখো।',
        E'## Strict vs Inclusive Thresholds\nWhen a rule says *"score is at least 60"*, `60` must pass (`score >= 60`), not `score > 60`.\n\n## `elif` Chain Order\nPython runs only the **first** matching branch. Always place stricter/higher thresholds before lower ones.',
        E'## বাউন্ডারি চিহ্ন (`>` বনাম `>=`)\nযদি শর্ত হয় *"নম্বর কমপক্ষে 60"*, তবে `score >= 60` ব্যবহার করতে হবে, `score > 60` নয়।\n\n## `elif`-এর ক্রম\nPython প্রথম যে শর্ত সত্য হয় শুধু সেই শাখাই চালায়। তাই বড় বা নির্দিষ্ট শর্ত আগে রাখো।',
        ARRAY['Choose between > and >= at exact threshold values', 'Structure multi-branch if/elif/else logic cleanly'],
        ARRAY['input-and-output'],
        ARRAY['absolute_beginner', 'basic_university'],
        '[{"title":"Pass/Fail boundary check","code":"score = int(input())\nif score >= 60:\n    print(\"PASS\")\nelse:\n    print(\"FAIL\")","input_data":"60","expected_output":"PASS","explanation_en":"At the exact boundary 60, >= evaluates to True.","explanation_bn":"ঠিক 60 মানেও >= শর্তটি True হয়।"}]'::jsonb,
        '{"prompt_en":"Read an integer `n` and print `POSITIVE` if `n > 0`, `ZERO` if `n == 0`, or `NEGATIVE` if `n < 0`.","prompt_bn":"একটি পূর্ণসংখ্যা `n` পড়ে `n > 0` হলে `POSITIVE`, `n == 0` হলে `ZERO`, আর `n < 0` হলে `NEGATIVE` প্রিন্ট করো।","language_slug":"python","starter_code":"n = int(input())\n# Print POSITIVE, ZERO, or NEGATIVE\n","test_cases":[{"name":"Positive","input_data":"9","expected_output":"POSITIVE"},{"name":"Exact zero boundary","input_data":"0","expected_output":"ZERO"},{"name":"Negative","input_data":"-4","expected_output":"NEGATIVE"}]}'::jsonb,
        15, 'published', now()
    )
    ON CONFLICT (lesson_id, version_number) DO UPDATE SET
        title_en = EXCLUDED.title_en, title_bn = EXCLUDED.title_bn,
        summary_en = EXCLUDED.summary_en, summary_bn = EXCLUDED.summary_bn,
        content_en_md = EXCLUDED.content_en_md, content_bn_md = EXCLUDED.content_bn_md,
        interactive_examples = EXCLUDED.interactive_examples,
        guided_exercise = EXCLUDED.guided_exercise, status = 'published', published_at = COALESCE(public.lesson_versions.published_at, now())
    RETURNING id INTO v_ver_id;
    UPDATE public.lessons SET current_published_version_id = v_ver_id WHERE id = v_lesson_id;

    -- Lesson 5: Loops & Boundaries
    INSERT INTO public.lessons (slug, skill_slug, display_order)
    VALUES ('loops-and-boundaries', 'loops', 5)
    ON CONFLICT (slug) DO UPDATE SET display_order = EXCLUDED.display_order
    RETURNING id INTO v_lesson_id;

    INSERT INTO public.lesson_versions (
        lesson_id, version_number, title_en, title_bn, summary_en, summary_bn,
        content_en_md, content_bn_md, learning_objectives, prerequisite_lesson_slugs,
        track_slugs, interactive_examples, guided_exercise, estimated_minutes, status, published_at
    )
    VALUES (
        v_lesson_id, 1,
        'Loops & Off-By-One Boundary Reasoning',
        'লুপ এবং অফ-বাই-ওয়ান বাউন্ডারি বিশ্লেষণ',
        'Understand Python half-open range(start, stop) intervals and trace first/last iterations accurately.',
        'Python-এর `range(start, stop)` কীভাবে শেষ সংখ্যার আগে থামে এবং প্রথম ও শেষ ধাপ ট্রেস করা শেখো।',
        E'## Half-Open `range(start, stop)`\n`range(1, 5)` produces `1, 2, 3, 4` — it stops **before** `5`. To include `n`, write `range(1, n + 1)`.\n\n## Always Trace First & Last Values\nBefore submitting any loop, check the loop variable on iteration #1 and the final iteration.',
        E'## Python `range(start, stop)` নিয়ম\n`range(1, 5)` শুধু `1, 2, 3, 4` তৈরি করে—`5` বাদ দেয়। `n` অন্তর্ভুক্ত করতে `range(1, n + 1)` লিখতে হয়।\n\n## প্রথম ও শেষ ধাপ ট্রেস করো\nযেকোনো লুপ জমা দেওয়ার আগে প্রথম মান এবং শেষ মান হাতে যাচাই করো।',
        ARRAY['Use range(a, b + 1) for inclusive upper bounds', 'Trace accumulator updates across loop iterations'],
        ARRAY['conditions-and-branching'],
        ARRAY['absolute_beginner', 'basic_university', 'intermediate'],
        '[{"title":"Inclusive sum 1..N","code":"n = int(input())\ntotal = 0\nfor i in range(1, n + 1):\n    total += i\nprint(total)","input_data":"4","expected_output":"10","explanation_en":"1 + 2 + 3 + 4 = 10 because stop is n + 1 = 5.","explanation_bn":"stop মান n + 1 = 5 হওয়ায় 1 + 2 + 3 + 4 = 10 হয়।"}]'::jsonb,
        '{"prompt_en":"Read a positive integer `n` and print the sum of all **even** integers from `1` through `n` inclusive.","prompt_bn":"একটি ধনাত্মক পূর্ণসংখ্যা `n` পড়ে `1` থেকে `n` (অন্তর্ভুক্ত) পর্যন্ত সব জোড় সংখ্যার যোগফল প্রিন্ট করো।","language_slug":"python","starter_code":"n = int(input())\ntotal = 0\n# Sum all even numbers from 1 to n inclusive\n","test_cases":[{"name":"Even upper bound","input_data":"6","expected_output":"12"},{"name":"Odd upper bound","input_data":"5","expected_output":"6"},{"name":"Boundary n=1","input_data":"1","expected_output":"0"}]}'::jsonb,
        15, 'published', now()
    )
    ON CONFLICT (lesson_id, version_number) DO UPDATE SET
        title_en = EXCLUDED.title_en, title_bn = EXCLUDED.title_bn,
        summary_en = EXCLUDED.summary_en, summary_bn = EXCLUDED.summary_bn,
        content_en_md = EXCLUDED.content_en_md, content_bn_md = EXCLUDED.content_bn_md,
        interactive_examples = EXCLUDED.interactive_examples,
        guided_exercise = EXCLUDED.guided_exercise, status = 'published', published_at = COALESCE(public.lesson_versions.published_at, now())
    RETURNING id INTO v_ver_id;
    UPDATE public.lessons SET current_published_version_id = v_ver_id WHERE id = v_lesson_id;

    -- Lesson 6: Lists & Indexing
    INSERT INTO public.lessons (slug, skill_slug, display_order)
    VALUES ('lists-and-indexing', 'indexing', 6)
    ON CONFLICT (slug) DO UPDATE SET display_order = EXCLUDED.display_order
    RETURNING id INTO v_lesson_id;

    INSERT INTO public.lesson_versions (
        lesson_id, version_number, title_en, title_bn, summary_en, summary_bn,
        content_en_md, content_bn_md, learning_objectives, prerequisite_lesson_slugs,
        track_slugs, interactive_examples, guided_exercise, estimated_minutes, status, published_at
    )
    VALUES (
        v_lesson_id, 1,
        'Lists, 0-Based Indexing & Preventing IndexError',
        'লিস্ট, ০-ভিত্তিক ইনডেক্সিং ও IndexError প্রতিরোধ',
        'Access list positions safely from 0 to len(nums) - 1 and initialize extrema from nums[0].',
        '0 থেকে len(nums) - 1 সীমার মধ্যে নিরাপদে লিস্ট অ্যাক্সেস করা এবং `nums[0]` থেকে শুরু করা শেখো।',
        E'## 0-Based Indices\nFor a list of length `N`, valid indices are `0` through `N - 1`. Accessing `nums[len(nums)]` always raises `IndexError`.\n\n## Safe Maximum/Minimum\nInitialize `best = nums[0]` (not `0`) so all-negative or all-positive lists always work.',
        E'## ০-ভিত্তিক ইনডেক্স\n`N` দৈর্ঘ্যের লিস্টের বৈধ ইনডেক্স `0` থেকে `N - 1`। `nums[len(nums)]` অ্যাক্সেস করলে `IndexError` হয়।\n\n## নিরাপদ সর্বোচ্চ/সর্বনিম্ন মান\n`0` নয়, বরং `best = nums[0]` দিয়ে শুরু করলে সব ঋণাত্মক বা সব ধনাত্মক লিস্টেই সঠিক ফল আসে।',
        ARRAY['Index first (nums[0]) and last (nums[-1]) elements safely', 'Avoid IndexError when iterating with indices'],
        ARRAY['loops-and-boundaries'],
        ARRAY['absolute_beginner', 'basic_university', 'intermediate'],
        '[{"title":"First and last element sum","code":"nums = [int(x) for x in input().split()]\nprint(nums[0] + nums[-1])","input_data":"4 9 11 6","expected_output":"10","explanation_en":"nums[0] is 4 and nums[-1] is 6.","explanation_bn":"nums[0] হলো 4 এবং nums[-1] হলো 6।"}]'::jsonb,
        '{"prompt_en":"Read a line of space-separated integers and print how many elements are strictly greater than the first element `nums[0]`.","prompt_bn":"এক লাইনে স্পেস-সেপারেটেড পূর্ণসংখ্যার লিস্ট পড়ে প্রথম উপাদান `nums[0]`-এর চেয়ে বড় কয়টি সংখ্যা আছে তা প্রিন্ট করো।","language_slug":"python","starter_code":"nums = [int(x) for x in input().split()]\n# Count elements strictly greater than nums[0]\n","test_cases":[{"name":"Mixed values","input_data":"5 2 8 5 9","expected_output":"2"},{"name":"All negative","input_data":"-10 -3 -15 -1","expected_output":"2"}]}'::jsonb,
        15, 'published', now()
    )
    ON CONFLICT (lesson_id, version_number) DO UPDATE SET
        title_en = EXCLUDED.title_en, title_bn = EXCLUDED.title_bn,
        summary_en = EXCLUDED.summary_en, summary_bn = EXCLUDED.summary_bn,
        content_en_md = EXCLUDED.content_en_md, content_bn_md = EXCLUDED.content_bn_md,
        interactive_examples = EXCLUDED.interactive_examples,
        guided_exercise = EXCLUDED.guided_exercise, status = 'published', published_at = COALESCE(public.lesson_versions.published_at, now())
    RETURNING id INTO v_ver_id;
    UPDATE public.lessons SET current_published_version_id = v_ver_id WHERE id = v_lesson_id;

    -- Lesson 7: Functions & Returns
    INSERT INTO public.lessons (slug, skill_slug, display_order)
    VALUES ('functions-and-returns', 'functions', 7)
    ON CONFLICT (slug) DO UPDATE SET display_order = EXCLUDED.display_order
    RETURNING id INTO v_lesson_id;

    INSERT INTO public.lesson_versions (
        lesson_id, version_number, title_en, title_bn, summary_en, summary_bn,
        content_en_md, content_bn_md, learning_objectives, prerequisite_lesson_slugs,
        track_slugs, interactive_examples, guided_exercise, estimated_minutes, status, published_at
    )
    VALUES (
        v_lesson_id, 1,
        'Functions, Return Values & Avoiding Early Exits',
        'ফাংশন, Return স্টেটমেন্ট এবং অকাল প্রস্থান এড়ানো',
        'Separate pure computation (return) from output (print) and place return outside loops when accumulating.',
        'গণনা (`return`) ও প্রিন্ট (`print`) আলাদা রাখো এবং লুপের বাইরে সঠিক জায়গায় `return` বসাতে শেখো।',
        E'## `return` vs `print()`\nIf a function omits `return`, Python implicitly returns `None`.\n\n## Avoid Returning Inside a Loop Too Early\nA `return` inside a loop exits on iteration #1. Finish scanning all items before returning an accumulated result.',
        E'## `return` বনাম `print()`\nফাংশনে `return` না থাকলে Python নিজে থেকেই `None` রিটার্ন করে।\n\n## লুপের ভেতরে ভুল `return`\nলুপের ভেতরে শর্তহীন `return` দিলে প্রথম ধাপেই ফাংশন শেষ হয়ে যায়।',
        ARRAY['Return computed values cleanly instead of returning None', 'Place accumulator return statements outside loops'],
        ARRAY['lists-and-indexing'],
        ARRAY['basic_university', 'intermediate'],
        '[{"title":"Pure square helper","code":"def square(n):\n    return n * n\nprint(square(int(input())))","input_data":"7","expected_output":"49","explanation_en":"square(7) returns 49, which the caller prints.","explanation_bn":"square(7) ফাংশন 49 রিটার্ন করে, যা পরে প্রিন্ট হয়।"}]'::jsonb,
        '{"prompt_en":"Complete `count_positives(nums)` so it **returns** the count of numbers `> 0`, then print the returned value.","prompt_bn":"`count_positives(nums)` ফাংশনটি সম্পূর্ণ করো যাতে এটি `0`-এর চেয়ে বড় সংখ্যার গণনা `return` করে এবং ফলাফল প্রিন্ট হয়।","language_slug":"python","starter_code":"def count_positives(nums: list[int]) -> int:\n    # Return count of elements > 0\n    pass\n\nnums = [int(x) for x in input().split()]\nprint(count_positives(nums))\n","test_cases":[{"name":"Mixed with zero","input_data":"-2 0 4 7 -1","expected_output":"2"},{"name":"None positive","input_data":"-5 -1 0","expected_output":"0"}]}'::jsonb,
        15, 'published', now()
    )
    ON CONFLICT (lesson_id, version_number) DO UPDATE SET
        title_en = EXCLUDED.title_en, title_bn = EXCLUDED.title_bn,
        summary_en = EXCLUDED.summary_en, summary_bn = EXCLUDED.summary_bn,
        content_en_md = EXCLUDED.content_en_md, content_bn_md = EXCLUDED.content_bn_md,
        interactive_examples = EXCLUDED.interactive_examples,
        guided_exercise = EXCLUDED.guided_exercise, status = 'published', published_at = COALESCE(public.lesson_versions.published_at, now())
    RETURNING id INTO v_ver_id;
    UPDATE public.lessons SET current_published_version_id = v_ver_id WHERE id = v_lesson_id;

    -- Lesson 8: Debugging Basics
    INSERT INTO public.lessons (slug, skill_slug, display_order)
    VALUES ('debugging-basics', 'debugging_basics', 8)
    ON CONFLICT (slug) DO UPDATE SET display_order = EXCLUDED.display_order
    RETURNING id INTO v_lesson_id;

    INSERT INTO public.lesson_versions (
        lesson_id, version_number, title_en, title_bn, summary_en, summary_bn,
        content_en_md, content_bn_md, learning_objectives, prerequisite_lesson_slugs,
        track_slugs, interactive_examples, guided_exercise, estimated_minutes, status, published_at
    )
    VALUES (
        v_lesson_id, 1,
        'Debugging Basics: Tracebacks & State Tables',
        'ডিবাগিংয়ের মূল কৌশল: Traceback ও স্টেট টেবিল',
        'Diagnose syntax/runtime tracebacks systematically and trace logic bugs with tiny test inputs.',
        'সিনট্যাক্স ও রানটাইম Traceback পড়ে ভুল খুঁজে বের করা এবং ছোট ইনপুটে কোড ট্রেস করা শেখো।',
        E'## Three-Step Debugging Habit\n1. **Read the exact error or mismatch** (last line of traceback, or expected vs actual output).\n2. **Trace a 2–3 element input by hand** (write variable values after each line).\n3. **Fix one root cause and test edge cases** (negative numbers, zeros, single elements).',
        E'## ডিবাগিংয়ের ৩টি ধাপ\n১. **সঠিক এরর বা আউটপুটের অমিল পড়ো** (Traceback-এর শেষ লাইন দেখো)।\n২. **২-৩টি উপাদানের ছোট ইনপুট হাতে ট্রেস করো**।\n৩. **মূল কারণ ঠিক করে এজ-কেস (ঋণাত্মক, শূন্য, ১টি উপাদান) যাচাই করো**।',
        ARRAY['Interpret Python tracebacks from the bottom line up', 'Fix a subtle initialization bug using edge-case tracing'],
        ARRAY['functions-and-returns'],
        ARRAY['basic_university', 'intermediate', 'advanced'],
        '[{"title":"Fixing product initialization","code":"nums = [int(x) for x in input().split()]\nprod = 1\nfor x in nums:\n    prod *= x\nprint(prod)","input_data":"2 3 4","expected_output":"24","explanation_en":"Starting prod at 1 instead of 0 preserves multiplication.","explanation_bn":"prod = 1 দিয়ে শুরু করলে গুণফল সঠিকভাবে হিসাব হয়।"}]'::jsonb,
        '{"prompt_en":"The starter code below tries to compute the product of all numbers in a list, but contains an initialization bug. Fix it and run to verify.","prompt_bn":"নিচের কোডটি লিস্টের সব সংখ্যার গুণফল বের করতে গিয়ে একটি ইনিশিয়ালাইজেশন ভুল করেছে। ভুলটি ঠিক করে রান করো।","language_slug":"python","starter_code":"def list_product(nums: list[int]) -> int:\n    prod = 0  # BUG: fix initialization\n    for x in nums:\n        prod *= x\n    return prod\n\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n","test_cases":[{"name":"Positive product","input_data":"2 3 4","expected_output":"24"},{"name":"Includes negative","input_data":"-2 5 3","expected_output":"-30"}]}'::jsonb,
        15, 'published', now()
    )
    ON CONFLICT (lesson_id, version_number) DO UPDATE SET
        title_en = EXCLUDED.title_en, title_bn = EXCLUDED.title_bn,
        summary_en = EXCLUDED.summary_en, summary_bn = EXCLUDED.summary_bn,
        content_en_md = EXCLUDED.content_en_md, content_bn_md = EXCLUDED.content_bn_md,
        interactive_examples = EXCLUDED.interactive_examples,
        guided_exercise = EXCLUDED.guided_exercise, status = 'published', published_at = COALESCE(public.lesson_versions.published_at, now())
    RETURNING id INTO v_ver_id;
    UPDATE public.lessons SET current_published_version_id = v_ver_id WHERE id = v_lesson_id;
END $$;

-- 4. 18 Admin-Reviewed, Published Diagnostic Questions Across All 8 Domains
--    (8 core primary probes + 6 adaptive foundation follow-ups + 4 stretch real-Judge0 coding probes)
DO $$
DECLARE
    v_qid uuid;
BEGIN
    -- DOMAIN 1: VARIABLES (core MCQ + foundation follow-up + stretch coding)
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-var-core-1', 'variables', 'variables', 'core', 'mcq',
        'Why does initializing `best = 0` fail when finding the maximum of `[-10, -3, -25]`?',
        '`[-10, -3, -25]` লিস্টের সর্বোচ্চ মান খুঁজতে `best = 0` ধরলে কেন ভুল উত্তর আসে?',
        E'best = 0\nfor x in [-10, -3, -25]:\n    if x > best:\n        best = x\nprint(best)',
        '[{"id":"a","text_en":"0 is larger than every negative number, so best never updates and prints 0","text_bn":"0 সব ঋণাত্মক সংখ্যার চেয়ে বড়, তাই best কখনোই আপডেট হয় না এবং 0 প্রিন্ট হয়"},{"id":"b","text_en":"Python cannot compare negative numbers with 0","text_bn":"Python ঋণাত্মক সংখ্যার সাথে 0 তুলনা করতে পারে না"},{"id":"c","text_en":"The for loop skips negative numbers","text_bn":"for লুপ ঋণাত্মক সংখ্যা বাদ দেয়"},{"id":"d","text_en":"It causes a SyntaxError","text_bn":"এতে SyntaxError হয়"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'a', 'Because 0 > -3, no negative item updates best; initialize best = nums[0].', '0 সব ঋণাত্মক সংখ্যার চেয়ে বড় হওয়ায় best আপডেট হয় না; nums[0] দিয়ে শুরু করতে হবে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-var-found-1', 'variables', 'variables', 'foundation', 'mcq',
        'What does `print("4" + "5")` output in Python?',
        'Python-এ `print("4" + "5")` চালালে কী আউটপুট আসবে?',
        E'print("4" + "5")',
        '[{"id":"a","text_en":"9","text_bn":"9"},{"id":"b","text_en":"45","text_bn":"45"},{"id":"c","text_en":"TypeError","text_bn":"TypeError"},{"id":"d","text_en":"4 5","text_bn":"4 5"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'b', 'Both operands are strings, so + concatenates them into "45".', 'দুটোই স্ট্রিং হওয়ায় + তাদের জোড়া লাগিয়ে "45" তৈরি করে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    -- DOMAIN 2: SYNTAX & RUNTIME DEBUGGING (core MCQ + foundation follow-up)
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-dbg-core-1', 'syntax_runtime_debugging', 'debugging_basics', 'core', 'mcq',
        'Which exception does the code below raise when executed?',
        'নিচের কোডটি চালালে Python কোন Exception দেখাবে?',
        E'counts = {"a": 1}\nprint(counts["b"])',
        '[{"id":"a","text_en":"IndexError","text_bn":"IndexError"},{"id":"b","text_en":"KeyError","text_bn":"KeyError"},{"id":"c","text_en":"SyntaxError","text_bn":"SyntaxError"},{"id":"d","text_en":"ZeroDivisionError","text_bn":"ZeroDivisionError"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'b', 'Accessing a missing dictionary key with [] raises KeyError; use .get("b", 0).', 'ডিকশনারিতে অনুপস্থিত কী [] দিয়ে খুঁজলে KeyError হয়; .get() ব্যবহার করা নিরাপদ।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-dbg-found-1', 'syntax_runtime_debugging', 'debugging_basics', 'foundation', 'mcq',
        'Why does `if x = 5:` fail before the program even runs?',
        'প্রোগ্রাম শুরু হওয়ার আগেই `if x = 5:` কেন এরর দেয়?',
        E'x = 5\nif x = 5:\n    print("ok")',
        '[{"id":"a","text_en":"= is assignment; equality check in Python requires ==","text_bn":"= হলো মান বসানো; তুলনার জন্য Python-এ == লাগে"},{"id":"b","text_en":"if statements cannot check integers","text_bn":"if স্টেটমেন্ট সংখ্যা পরীক্ষা করতে পারে না"},{"id":"c","text_en":"x must be a string","text_bn":"x অবশ্যই স্ট্রিং হতে হবে"},{"id":"d","text_en":"print needs a semicolon","text_bn":"print-এর শেষে সেমিকোলন লাগে"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'a', 'Python raises SyntaxError because assignment (=) is invalid where equality (==) is expected.', 'তুলনার জায়গায় = দিলে SyntaxError হয়; == ব্যবহার করতে হবে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    -- DOMAIN 3: CONDITIONS (core MCQ + foundation follow-up)
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-cond-core-1', 'conditions', 'conditions', 'core', 'mcq',
        'If `score = 90`, what does this buggy grading chain print?',
        '`score = 90` হলে নিচের ভুল গ্রেডিং কোডটি কী প্রিন্ট করবে?',
        E'score = 90\nif score >= 70:\n    print("C")\nelif score >= 90:\n    print("A")',
        '[{"id":"a","text_en":"A","text_bn":"A"},{"id":"b","text_en":"C","text_bn":"C"},{"id":"c","text_en":"Both C and A","text_bn":"C এবং A দুটোই"},{"id":"d","text_en":"Nothing","text_bn":"কিছুই না"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'b', 'score >= 70 is checked first and is True for 90, so elif score >= 90 is never reached.', 'score >= 70 আগে থাকায় 90-এর জন্য সেটাই সত্য হয়ে "C" প্রিন্ট হয়।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-cond-found-1', 'conditions', 'conditions', 'foundation', 'mcq',
        'Which condition checks that `age` is **at least 18**?',
        '`age` কমপক্ষে ১৮ কি না তা কোন শর্তটি সঠিকভাবে যাচাই করে?',
        NULL,
        '[{"id":"a","text_en":"age > 18","text_bn":"age > 18"},{"id":"b","text_en":"age >= 18","text_bn":"age >= 18"},{"id":"c","text_en":"age <= 18","text_bn":"age <= 18"},{"id":"d","text_en":"age == 18","text_bn":"age == 18"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'b', '"At least 18" includes 18 itself, requiring >=.', '"কমপক্ষে ১৮" মানে ১৮-ও অন্তর্ভুক্ত, তাই >= ব্যবহার করতে হবে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    -- DOMAIN 4: LOOP BOUNDARIES (core MCQ + foundation follow-up + stretch Judge0 code execution!)
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-loop-core-1', 'loop_boundaries', 'loops', 'core', 'mcq',
        'What is the exact output of the loop below?',
        'নিচের লুপটির সঠিক আউটপুট কী হবে?',
        E'total = 0\nfor i in range(2, 5):\n    total += i\nprint(total)',
        '[{"id":"a","text_en":"9","text_bn":"9"},{"id":"b","text_en":"14","text_bn":"14"},{"id":"c","text_en":"12","text_bn":"12"},{"id":"d","text_en":"7","text_bn":"7"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'a', 'range(2, 5) yields 2, 3, 4 (stopping before 5), so 2 + 3 + 4 = 9.', 'range(2, 5) শুধু 2, 3, 4 দেয় (5 বাদ পড়ে), তাই যোগফল 9।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-loop-found-1', 'loop_boundaries', 'loops', 'foundation', 'mcq',
        'How many times does `for i in range(4):` execute?',
        '`for i in range(4):` লুপটি মোট কতবার চলবে?',
        E'for i in range(4):\n    print(i)',
        '[{"id":"a","text_en":"3 times (1, 2, 3)","text_bn":"৩ বার (1, 2, 3)"},{"id":"b","text_en":"4 times (0, 1, 2, 3)","text_bn":"৪ বার (0, 1, 2, 3)"},{"id":"c","text_en":"5 times (0, 1, 2, 3, 4)","text_bn":"৫ বার (0, 1, 2, 3, 4)"},{"id":"d","text_en":"Infinite loop","text_bn":"অসীম লুপ"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'b', 'range(4) starts at 0 and stops before 4: 0, 1, 2, 3 (4 iterations).', 'range(4) 0 থেকে শুরু হয়ে 3 পর্যন্ত মোট ৪ বার চলে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, starter_code, language_slug, status, published_at)
    VALUES (
        'diag-loop-stretch-code', 'loop_boundaries', 'loops', 'stretch', 'code_execution',
        'Execution Check: Read two integers `a b` (`a <= b`) on one line and print the sum of all integers from `a` through `b` **inclusive**.',
        'কোড এক্সিকিউশন যাচাই: এক লাইনে দুটি পূর্ণসংখ্যা `a b` পড়ে `a` থেকে `b` (উভয়ই অন্তর্ভুক্ত) পর্যন্ত সব পূর্ণসংখ্যার যোগফল প্রিন্ট করো।',
        E'a, b = map(int, input().split())\n# Write your solution and print the inclusive sum\n',
        'python', 'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn, evaluation_tests)
    VALUES (
        v_qid, NULL,
        'Use range(a, b + 1) so the upper endpoint b is included, including when a == b.',
        'range(a, b + 1) ব্যবহার করলে শেষ সংখ্যা b এবং a == b কেসটিও সঠিকভাবে অন্তর্ভুক্ত হয়।',
        '[{"name":"Basic range","input_data":"3 6","expected_output":"18"},{"name":"Single point","input_data":"5 5","expected_output":"5"},{"name":"Negative to positive","input_data":"-2 2","expected_output":"0"}]'::jsonb
    )
    ON CONFLICT (question_id) DO UPDATE SET evaluation_tests = EXCLUDED.evaluation_tests, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    -- DOMAIN 5: ARRAYS / LISTS (core MCQ + foundation follow-up)
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-list-core-1', 'arrays_lists', 'lists', 'core', 'mcq',
        'What is the bug in this loop that tries to sum all elements of `nums`?',
        '`nums` লিস্টের সব উপাদানের যোগফল বের করার নিচের কোডটিতে ভুল কোথায়?',
        E'nums = [3, 5, 2]\nfor x in nums:\n    total = 0\n    total += x\nprint(total)',
        '[{"id":"a","text_en":"total = 0 is inside the loop, resetting total on every iteration (prints 2)","text_bn":"total = 0 লুপের ভেতরে থাকায় প্রতিবার রিসেট হয় (আউটপুট শুধু 2 আসে)"},{"id":"b","text_en":"for x in nums is invalid syntax","text_bn":"for x in nums ভুল সিনট্যাক্স"},{"id":"c","text_en":"+= cannot add integers","text_bn":"+= পূর্ণসংখ্যা যোগ করতে পারে না"},{"id":"d","text_en":"There is no bug; it prints 10","text_bn":"কোনো ভুল নেই; এটি 10 প্রিন্ট করবে"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'a', 'Move total = 0 before the loop so each element accumulates into the running sum.', 'total = 0 লুপের বাইরে রাখলে সব উপাদান সঠিকভাবে যোগ হবে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-list-found-1', 'arrays_lists', 'lists', 'foundation', 'mcq',
        'What does `len([10, 20, 30])` return in Python?',
        'Python-এ `len([10, 20, 30])` এর মান কত?',
        NULL,
        '[{"id":"a","text_en":"2","text_bn":"2"},{"id":"b","text_en":"3","text_bn":"3"},{"id":"c","text_en":"30","text_bn":"30"},{"id":"d","text_en":"60","text_bn":"60"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'b', 'len() returns the number of items in the list (3).', 'len() লিস্টে মোট কয়টি উপাদান আছে তা জানায় (3)।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    -- DOMAIN 6: INDEXING (core MCQ + foundation follow-up)
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-idx-core-1', 'indexing', 'indexing', 'core', 'mcq',
        'Why does this adjacent-pair comparison raise `IndexError`?',
        'পাশাপাশি দুটি উপাদান তুলনা করার নিচের কোডটি কেন `IndexError` দেয়?',
        E'arr = [1, 3, 2, 5]\nfor i in range(len(arr)):\n    if arr[i + 1] > arr[i]:\n        print(i)',
        '[{"id":"a","text_en":"When i == len(arr) - 1, arr[i + 1] requests arr[4] which is out of range","text_bn":"i == len(arr) - 1 হলে arr[i + 1] অর্থাৎ arr[4] সীমার বাইরে চলে যায়"},{"id":"b","text_en":"arr[0] is invalid in Python","text_bn":"Python-এ arr[0] বৈধ নয়"},{"id":"c","text_en":"range(len(arr)) runs 0 times","text_bn":"range(len(arr)) ০ বার চলে"},{"id":"d","text_en":"Lists cannot be indexed inside if statements","text_bn":"if-এর ভেতরে লিস্ট ইনডেক্স করা যায় না"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'a', 'Use range(len(arr) - 1) whenever accessing both arr[i] and arr[i + 1].', 'arr[i] ও arr[i + 1] একসাথে অ্যাক্সেস করলে range(len(arr) - 1) ব্যবহার করতে হবে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-idx-found-1', 'indexing', 'indexing', 'foundation', 'mcq',
        'For `nums = [10, 20, 30, 40]`, what is `nums[1]`?',
        '`nums = [10, 20, 30, 40]` হলে `nums[1]`-এর মান কত?',
        NULL,
        '[{"id":"a","text_en":"10","text_bn":"10"},{"id":"b","text_en":"20","text_bn":"20"},{"id":"c","text_en":"30","text_bn":"30"},{"id":"d","text_en":"IndexError","text_bn":"IndexError"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'b', 'Python lists are 0-indexed: nums[0] is 10, nums[1] is 20.', 'Python লিস্ট 0 থেকে শুরু হয়: nums[0]=10, nums[1]=20।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    -- DOMAIN 7: FUNCTIONS (core MCQ + stretch Judge0 code execution!)
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-fn-core-1', 'functions', 'functions', 'core', 'mcq',
        'What does `print(add(3, 4))` display for the function below?',
        'নিচের ফাংশনটির জন্য `print(add(3, 4))` কী আউটপুট দেখাবে?',
        E'def add(a, b):\n    result = a + b\n\nprint(add(3, 4))',
        '[{"id":"a","text_en":"7","text_bn":"7"},{"id":"b","text_en":"None","text_bn":"None"},{"id":"c","text_en":"0","text_bn":"0"},{"id":"d","text_en":"NameError","text_bn":"NameError"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'b', 'Without a return statement, Python functions implicitly return None.', 'return না থাকায় ফাংশনটি None রিটার্ন করে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, starter_code, language_slug, status, published_at)
    VALUES (
        'diag-fn-stretch-code', 'functions', 'functions', 'stretch', 'code_execution',
        'Execution Check: Complete `find_min(nums)` so it returns the minimum integer in any non-empty list (including all-positive and all-negative lists).',
        'কোড এক্সিকিউশন যাচাই: `find_min(nums)` ফাংশনটি সম্পূর্ণ করো যাতে সব ধনাত্মক বা সব ঋণাত্মক লিস্টের সর্বনিম্ন মান সঠিকভাবে `return` করে।',
        E'def find_min(nums: list[int]) -> int:\n    # Return the smallest integer in nums\n    pass\n\nnums = [int(x) for x in input().split()]\nprint(find_min(nums))\n',
        'python', 'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn, evaluation_tests)
    VALUES (
        v_qid, NULL,
        'Initialize lowest = nums[0] and update whenever an element is strictly smaller.',
        'lowest = nums[0] ধরে প্রতিটি উপাদানের সাথে তুলনা করলে সব ধনাত্মক ও ঋণাত্মক কেস পাস করে।',
        '[{"name":"All positive","input_data":"12 5 19 8","expected_output":"5"},{"name":"All negative","input_data":"-4 -18 -9","expected_output":"-18"},{"name":"Single element","input_data":"42","expected_output":"42"}]'::jsonb
    )
    ON CONFLICT (question_id) DO UPDATE SET evaluation_tests = EXCLUDED.evaluation_tests, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    -- DOMAIN 8: MIXED PROBLEM-SOLVING LOGIC (core MCQ + stretch Judge0 code execution!)
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, code_snippet, options, status, published_at)
    VALUES (
        'diag-mix-core-1', 'mixed_logic', 'mixed_problem_solving', 'core', 'mcq',
        'Why does `all_even([2, 4, 5, 8])` wrongly return `True` below?',
        'নিচের `all_even([2, 4, 5, 8])` কেন ভুলভাবে `True` রিটার্ন করে?',
        E'def all_even(nums):\n    for n in nums:\n        if n % 2 == 0:\n            return True\n    return False',
        '[{"id":"a","text_en":"It returns True on the first even number (2) without checking the remaining elements","text_bn":"এটি প্রথম জোড় সংখ্যা (2) দেখেই True রিটার্ন করে বাকিগুলো না দেখেই"},{"id":"b","text_en":"% 2 checks odd numbers instead of even","text_bn":"% 2 জোড় সংখ্যার বদলে বিজোড় যাচাই করে"},{"id":"c","text_en":"for n in nums skips index 2","text_bn":"for n in nums ইনডেক্স ২ বাদ দেয়"},{"id":"d","text_en":"return False is unreachable syntax","text_bn":"return False সিনট্যাক্স এরর"}]'::jsonb,
        'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn)
    VALUES (v_qid, 'a', 'Universal checks must return False on the first counterexample (n % 2 != 0) and return True only after the loop.', 'সব উপাদান যাচাই করতে বিজোড় পেলেই False রিটার্ন করতে হবে এবং লুপ শেষে True রিটার্ন করতে হবে।')
    ON CONFLICT (question_id) DO UPDATE SET correct_option_id = EXCLUDED.correct_option_id, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, starter_code, language_slug, status, published_at)
    VALUES (
        'diag-mix-stretch-code', 'mixed_logic', 'mixed_problem_solving', 'stretch', 'code_execution',
        'Execution Check: Read a line of space-separated integers and print the count of **adjacent strictly increasing pairs** (`nums[i + 1] > nums[i]`).',
        'কোড এক্সিকিউশন যাচাই: এক লাইনে পূর্ণসংখ্যার লিস্ট পড়ে কতগুলো পাশাপাশি জোড়া (`nums[i + 1] > nums[i]`) ক্রমবর্ধমান আছে তা প্রিন্ট করো।',
        E'nums = [int(x) for x in input().split()]\n# Print count of adjacent strictly increasing pairs\n',
        'python', 'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn, evaluation_tests)
    VALUES (
        v_qid, NULL,
        'Iterate i over range(len(nums) - 1) and increment when nums[i + 1] > nums[i].',
        'range(len(nums) - 1) চালিয়ে nums[i + 1] > nums[i] হলে গণনা বাড়াও।',
        '[{"name":"Mixed sequence","input_data":"1 3 2 5 6","expected_output":"3"},{"name":"Equal values not strictly increasing","input_data":"2 2 2","expected_output":"0"},{"name":"Strictly decreasing","input_data":"9 7 4 1","expected_output":"0"}]'::jsonb
    )
    ON CONFLICT (question_id) DO UPDATE SET evaluation_tests = EXCLUDED.evaluation_tests, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;

    -- Bonus stretch execution question for variables/debugging
    INSERT INTO public.diagnostic_questions (slug, domain_slug, skill_slug, difficulty, question_type, prompt_en, prompt_bn, starter_code, language_slug, status, published_at)
    VALUES (
        'diag-var-stretch-code', 'variables', 'variables', 'stretch', 'code_execution',
        'Execution Check: Read a line of space-separated integers (may be all negative) and print the **maximum** integer.',
        'কোড এক্সিকিউশন যাচাই: এক লাইনে পূর্ণসংখ্যার লিস্ট (সব ঋণাত্মকও হতে পারে) পড়ে সর্বোচ্চ সংখ্যাটি প্রিন্ট করো।',
        E'nums = [int(x) for x in input().split()]\n# Print the maximum integer safely\n',
        'python', 'published', now()
    ) ON CONFLICT (slug) DO UPDATE SET prompt_en = EXCLUDED.prompt_en, prompt_bn = EXCLUDED.prompt_bn, options = EXCLUDED.options, status = 'published' RETURNING id INTO v_qid;
    INSERT INTO public.diagnostic_question_answers (question_id, correct_option_id, explanation_en, explanation_bn, evaluation_tests)
    VALUES (
        v_qid, NULL,
        'Initialize best = nums[0] so all-negative inputs never falsely return 0.',
        'best = nums[0] দিয়ে শুরু করলে সব ঋণাত্মক লিস্টেও সঠিক সর্বোচ্চ মান আসে।',
        '[{"name":"All negative","input_data":"-15 -4 -22 -9","expected_output":"-4"},{"name":"Mixed","input_data":"3 11 -2 7","expected_output":"11"},{"name":"Single negative","input_data":"-8","expected_output":"-8"}]'::jsonb
    )
    ON CONFLICT (question_id) DO UPDATE SET evaluation_tests = EXCLUDED.evaluation_tests, explanation_en = EXCLUDED.explanation_en, explanation_bn = EXCLUDED.explanation_bn;
END $$;
