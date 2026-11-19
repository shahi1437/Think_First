-- =============================================================================
-- Seed 001: Supported Languages + 4 Original Python Problems (2 Coding, 2 Debugging)
-- Idempotent seed script for Think_First local/dev database
-- =============================================================================

-- 1. Supported Languages (Judge0 CE v1.13.1 standard IDs; synced dynamically via Admin API)
INSERT INTO public.supported_languages (slug, display_name, judge0_language_id, monaco_language, version_label, is_enabled)
VALUES
    ('python', 'Python 3', 71, 'python', 'Python (3.8.1)', true),
    ('javascript', 'JavaScript (Node.js)', 63, 'javascript', 'JavaScript (Node.js 12.14.0)', false),
    ('cpp', 'C++ (GCC)', 54, 'cpp', 'C++ (GCC 9.2.0)', false),
    ('java', 'Java (OpenJDK)', 62, 'java', 'Java (OpenJDK 13.0.1)', false)
ON CONFLICT (slug) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    judge0_language_id = EXCLUDED.judge0_language_id,
    monaco_language = EXCLUDED.monaco_language,
    version_label = EXCLUDED.version_label;

-- 2. Problem 1 (Normal Coding / Beginner): Sum of Even Numbers
WITH p AS (
    INSERT INTO public.problems (slug)
    VALUES ('sum-of-even-numbers')
    ON CONFLICT (slug) DO UPDATE SET slug = EXCLUDED.slug
    RETURNING id
),
pv AS (
    INSERT INTO public.problem_versions (
        problem_id, version_number, title, statement_md, difficulty, mode,
        topics, skills, prerequisites, learning_objectives, examples,
        time_limit_ms, memory_limit_kb, status, validated_at, published_at
    )
    SELECT
        p.id, 1,
        'Sum of Even Numbers',
        E'Given a line of space-separated integers, compute and print the sum of all **even** integers.\n\n### Input\nA single line containing one or more space-separated integers.\n\n### Output\nA single integer representing the sum of all even numbers in the list (print `0` if none are even).',
        'beginner', 'coding',
        ARRAY['loops', 'conditionals', 'lists'],
        ARRAY['loop-iteration', 'modulo-check', 'accumulator-pattern'],
        ARRAY['variables', 'input-output'],
        ARRAY['Iterate through a list of integers', 'Filter values with the modulo operator', 'Accumulate a running total safely'],
        '[{"input":"1 2 3 4 5 6","output":"12","explanation":"2 + 4 + 6 = 12"},{"input":"1 3 5","output":"0","explanation":"No even integers exist"}]'::jsonb,
        2000, 131072, 'published', now(), now()
    FROM p
    ON CONFLICT (problem_id, version_number) DO UPDATE SET
        title = EXCLUDED.title,
        status = 'published',
        published_at = COALESCE(public.problem_versions.published_at, now())
    RETURNING id, problem_id
),
upd AS (
    UPDATE public.problems
    SET current_published_version_id = (SELECT id FROM pv)
    WHERE id = (SELECT problem_id FROM pv)
),
var AS (
    INSERT INTO public.problem_language_variants (problem_version_id, language_slug, starter_code)
    SELECT
        pv.id, 'python',
        E'def sum_even(nums: list[int]) -> int:\n    # Write your solution below\n    pass\n\nif __name__ == "__main__":\n    values = [int(x) for x in input().split()]\n    print(sum_even(values))\n'
    FROM pv
    ON CONFLICT (problem_version_id, language_slug) DO UPDATE SET starter_code = EXCLUDED.starter_code
    RETURNING id
),
ref AS (
    INSERT INTO public.problem_reference_solutions (variant_id, reference_solution)
    SELECT
        var.id,
        E'def sum_even(nums: list[int]) -> int:\n    total = 0\n    for n in nums:\n        if n % 2 == 0:\n            total += n\n    return total\n\nif __name__ == "__main__":\n    values = [int(x) for x in input().split()]\n    print(sum_even(values))\n'
    FROM var
    ON CONFLICT (variant_id) DO UPDATE SET reference_solution = EXCLUDED.reference_solution
)
INSERT INTO public.test_cases (problem_version_id, ordinal, name, input_data, expected_output, is_hidden)
SELECT pv.id, t.ordinal, t.name, t.input_data, t.expected_output, t.is_hidden
FROM pv
CROSS JOIN (VALUES
    (1, 'Basic mixed numbers', '1 2 3 4 5 6', '12', false),
    (2, 'No even numbers', '1 3 5 7', '0', false),
    (3, 'Negative even numbers', '-4 -3 -2 0 5', '-6', true),
    (4, 'Single even value', '42', '42', true),
    (5, 'Large values', '100000 99999 -100000 8', '8', true)
) AS t(ordinal, name, input_data, expected_output, is_hidden)
ON CONFLICT (problem_version_id, ordinal) DO UPDATE SET
    input_data = EXCLUDED.input_data,
    expected_output = EXCLUDED.expected_output,
    is_hidden = EXCLUDED.is_hidden;

-- 3. Problem 2 (Normal Coding / Basic): Word Frequency Counter
WITH p AS (
    INSERT INTO public.problems (slug)
    VALUES ('word-frequency-counter')
    ON CONFLICT (slug) DO UPDATE SET slug = EXCLUDED.slug
    RETURNING id
),
pv AS (
    INSERT INTO public.problem_versions (
        problem_id, version_number, title, statement_md, difficulty, mode,
        topics, skills, prerequisites, learning_objectives, examples,
        time_limit_ms, memory_limit_kb, status, validated_at, published_at
    )
    SELECT
        p.id, 1,
        'Word Frequency Counter',
        E'Given a single line of lowercase words separated by spaces, count how many times each distinct word appears and print `word:count` pairs sorted alphabetically by word, one per line.\n\n### Input\nA single line of space-separated lowercase words.\n\n### Output\nEach unique word and its frequency formatted as `word:count`, sorted alphabetically.',
        'basic', 'coding',
        ARRAY['strings', 'dictionaries', 'sorting'],
        ARRAY['dictionary-counting', 'string-splitting', 'alphabetical-sorting'],
        ARRAY['loops', 'strings'],
        ARRAY['Tokenize input strings cleanly', 'Aggregate counts with a dictionary', 'Output deterministic sorted results'],
        '[{"input":"code think code learn think code","output":"code:3\nlearn:1\nthink:2","explanation":"Counts sorted alphabetically"}]'::jsonb,
        2000, 131072, 'published', now(), now()
    FROM p
    ON CONFLICT (problem_id, version_number) DO UPDATE SET
        title = EXCLUDED.title,
        status = 'published',
        published_at = COALESCE(public.problem_versions.published_at, now())
    RETURNING id, problem_id
),
upd AS (
    UPDATE public.problems
    SET current_published_version_id = (SELECT id FROM pv)
    WHERE id = (SELECT problem_id FROM pv)
),
var AS (
    INSERT INTO public.problem_language_variants (problem_version_id, language_slug, starter_code)
    SELECT
        pv.id, 'python',
        E'def count_words(line: str) -> list[str]:\n    # Return sorted ["word:count", ...] entries\n    pass\n\nif __name__ == "__main__":\n    line = input().strip()\n    for row in count_words(line):\n        print(row)\n'
    FROM pv
    ON CONFLICT (problem_version_id, language_slug) DO UPDATE SET starter_code = EXCLUDED.starter_code
    RETURNING id
),
ref AS (
    INSERT INTO public.problem_reference_solutions (variant_id, reference_solution)
    SELECT
        var.id,
        E'def count_words(line: str) -> list[str]:\n    counts: dict[str, int] = {}\n    for word in line.split():\n        counts[word] = counts.get(word, 0) + 1\n    return [f"{word}:{counts[word]}" for word in sorted(counts)]\n\nif __name__ == "__main__":\n    line = input().strip()\n    for row in count_words(line):\n        print(row)\n'
    FROM var
    ON CONFLICT (variant_id) DO UPDATE SET reference_solution = EXCLUDED.reference_solution
)
INSERT INTO public.test_cases (problem_version_id, ordinal, name, input_data, expected_output, is_hidden)
SELECT pv.id, t.ordinal, t.name, t.input_data, t.expected_output, t.is_hidden
FROM pv
CROSS JOIN (VALUES
    (1, 'Repeated words', 'code think code learn think code', E'code:3\nlearn:1\nthink:2', false),
    (2, 'Single word', 'python', 'python:1', false),
    (3, 'Already unique reverse order', 'zeta beta alpha', E'alpha:1\nbeta:1\nzeta:1', true),
    (4, 'Multiple spaces between words', 'bug   fix   bug', E'bug:2\nfix:1', true),
    (5, 'All identical words', 'loop loop loop loop', 'loop:4', true)
) AS t(ordinal, name, input_data, expected_output, is_hidden)
ON CONFLICT (problem_version_id, ordinal) DO UPDATE SET
    input_data = EXCLUDED.input_data,
    expected_output = EXCLUDED.expected_output,
    is_hidden = EXCLUDED.is_hidden;

-- 4. Problem 3 (Debugging Mode / Beginner): Fix Off-By-One Range Sum
WITH p AS (
    INSERT INTO public.problems (slug)
    VALUES ('debug-range-sum-off-by-one')
    ON CONFLICT (slug) DO UPDATE SET slug = EXCLUDED.slug
    RETURNING id
),
pv AS (
    INSERT INTO public.problem_versions (
        problem_id, version_number, title, statement_md, difficulty, mode,
        topics, skills, prerequisites, learning_objectives, examples,
        time_limit_ms, memory_limit_kb, status, validated_at, published_at
    )
    SELECT
        p.id, 1,
        'Debug: Inclusive Range Sum',
        E'The provided Python program is supposed to read two integers `a` and `b` (`a <= b`) and print the **inclusive** sum of all integers from `a` through `b`.\n\nHowever, the starter code contains a **loop boundary bug**.\n\n### Debugging Goal\n1. Predict what the buggy code outputs for `3 5`.\n2. Run the code and compare actual vs expected output.\n3. Explain why the bug occurs.\n4. Fix the code and verify against all tests.',
        'beginner', 'debugging',
        ARRAY['loops', 'loop-boundary-debugging'],
        ARRAY['loop-boundaries', 'debugging-trace'],
        ARRAY['variables', 'loops'],
        ARRAY['Recognize Python range() exclusive upper bound', 'Predict execution output before running code', 'Fix off-by-one loop boundary defects'],
        '[{"input":"3 5","output":"12","explanation":"3 + 4 + 5 = 12"},{"input":"1 1","output":"1","explanation":"Single inclusive endpoint"}]'::jsonb,
        2000, 131072, 'published', now(), now()
    FROM p
    ON CONFLICT (problem_id, version_number) DO UPDATE SET
        title = EXCLUDED.title,
        status = 'published',
        published_at = COALESCE(public.problem_versions.published_at, now())
    RETURNING id, problem_id
),
upd AS (
    UPDATE public.problems
    SET current_published_version_id = (SELECT id FROM pv)
    WHERE id = (SELECT problem_id FROM pv)
),
var AS (
    INSERT INTO public.problem_language_variants (
        problem_version_id, language_slug, starter_code, buggy_starter_code, debugging_prompt
    )
    SELECT
        pv.id, 'python',
        E'def inclusive_sum(a: int, b: int) -> int:\n    total = 0\n    for num in range(a, b):\n        total += num\n    return total\n\nif __name__ == "__main__":\n    a, b = map(int, input().split())\n    print(inclusive_sum(a, b))\n',
        E'def inclusive_sum(a: int, b: int) -> int:\n    total = 0\n    for num in range(a, b):\n        total += num\n    return total\n\nif __name__ == "__main__":\n    a, b = map(int, input().split())\n    print(inclusive_sum(a, b))\n',
        'Before clicking Run, trace the loop for input "3 5". What value will the current code print, and which integer is missing?'
    FROM pv
    ON CONFLICT (problem_version_id, language_slug) DO UPDATE SET
        starter_code = EXCLUDED.starter_code,
        buggy_starter_code = EXCLUDED.buggy_starter_code,
        debugging_prompt = EXCLUDED.debugging_prompt
    RETURNING id
),
ref AS (
    INSERT INTO public.problem_reference_solutions (variant_id, reference_solution, expected_bug_summary)
    SELECT
        var.id,
        E'def inclusive_sum(a: int, b: int) -> int:\n    total = 0\n    for num in range(a, b + 1):\n        total += num\n    return total\n\nif __name__ == "__main__":\n    a, b = map(int, input().split())\n    print(inclusive_sum(a, b))\n',
        'range(a, b) excludes the upper bound b; changing it to range(a, b + 1) makes the sum inclusive.'
    FROM var
    ON CONFLICT (variant_id) DO UPDATE SET
        reference_solution = EXCLUDED.reference_solution,
        expected_bug_summary = EXCLUDED.expected_bug_summary
)
INSERT INTO public.test_cases (problem_version_id, ordinal, name, input_data, expected_output, is_hidden)
SELECT pv.id, t.ordinal, t.name, t.input_data, t.expected_output, t.is_hidden
FROM pv
CROSS JOIN (VALUES
    (1, 'Small positive range', '3 5', '12', false),
    (2, 'Single element range', '1 1', '1', false),
    (3, 'Negative to positive', '-2 2', '0', true),
    (4, 'All negative range', '-5 -3', '-12', true),
    (5, 'Zero to ten', '0 10', '55', true)
) AS t(ordinal, name, input_data, expected_output, is_hidden)
ON CONFLICT (problem_version_id, ordinal) DO UPDATE SET
    input_data = EXCLUDED.input_data,
    expected_output = EXCLUDED.expected_output,
    is_hidden = EXCLUDED.is_hidden;

-- 5. Problem 4 (Debugging Mode / Basic): Fix Maximum Element Initialization
WITH p AS (
    INSERT INTO public.problems (slug)
    VALUES ('debug-max-negative-init')
    ON CONFLICT (slug) DO UPDATE SET slug = EXCLUDED.slug
    RETURNING id
),
pv AS (
    INSERT INTO public.problem_versions (
        problem_id, version_number, title, statement_md, difficulty, mode,
        topics, skills, prerequisites, learning_objectives, examples,
        time_limit_ms, memory_limit_kb, status, validated_at, published_at
    )
    SELECT
        p.id, 1,
        'Debug: Maximum Value in Any Integer List',
        E'The provided function `find_max(nums)` should return the largest integer from a non-empty list of integers (which may include **all negative** values).\n\nThe current implementation passes on positive inputs, but fails on an important edge case.\n\n### Debugging Goal\n1. Predict what the buggy code prints for `-10 -3 -25`.\n2. Run the code and inspect the failing test.\n3. Explain why initializing `best = 0` is flawed.\n4. Fix the initialization bug and submit.',
        'basic', 'debugging',
        ARRAY['lists', 'initialization-debugging'],
        ARRAY['variable-initialization', 'edge-case-testing'],
        ARRAY['loops', 'lists'],
        ARRAY['Identify unsafe sentinel initializations', 'Test negative-only edge cases', 'Initialize accumulators from input elements'],
        '[{"input":"4 9 2","output":"9","explanation":"Largest positive number is 9"},{"input":"-10 -3 -25","output":"-3","explanation":"Largest negative number is -3"}]'::jsonb,
        2000, 131072, 'published', now(), now()
    FROM p
    ON CONFLICT (problem_id, version_number) DO UPDATE SET
        title = EXCLUDED.title,
        status = 'published',
        published_at = COALESCE(public.problem_versions.published_at, now())
    RETURNING id, problem_id
),
upd AS (
    UPDATE public.problems
    SET current_published_version_id = (SELECT id FROM pv)
    WHERE id = (SELECT problem_id FROM pv)
),
var AS (
    INSERT INTO public.problem_language_variants (
        problem_version_id, language_slug, starter_code, buggy_starter_code, debugging_prompt
    )
    SELECT
        pv.id, 'python',
        E'def find_max(nums: list[int]) -> int:\n    best = 0\n    for value in nums:\n        if value > best:\n            best = value\n    return best\n\nif __name__ == "__main__":\n    nums = [int(x) for x in input().split()]\n    print(find_max(nums))\n',
        E'def find_max(nums: list[int]) -> int:\n    best = 0\n    for value in nums:\n        if value > best:\n            best = value\n    return best\n\nif __name__ == "__main__":\n    nums = [int(x) for x in input().split()]\n    print(find_max(nums))\n',
        'Trace find_max([-10, -3, -25]) line by line. What does best equal at the end of the loop and why?'
    FROM pv
    ON CONFLICT (problem_version_id, language_slug) DO UPDATE SET
        starter_code = EXCLUDED.starter_code,
        buggy_starter_code = EXCLUDED.buggy_starter_code,
        debugging_prompt = EXCLUDED.debugging_prompt
    RETURNING id
),
ref AS (
    INSERT INTO public.problem_reference_solutions (variant_id, reference_solution, expected_bug_summary)
    SELECT
        var.id,
        E'def find_max(nums: list[int]) -> int:\n    best = nums[0]\n    for value in nums[1:]:\n        if value > best:\n            best = value\n    return best\n\nif __name__ == "__main__":\n    nums = [int(x) for x in input().split()]\n    print(find_max(nums))\n',
        'Initializing best = 0 causes lists containing only negative integers to wrongly return 0 instead of the largest element (nums[0]).'
    FROM var
    ON CONFLICT (variant_id) DO UPDATE SET
        reference_solution = EXCLUDED.reference_solution,
        expected_bug_summary = EXCLUDED.expected_bug_summary
)
INSERT INTO public.test_cases (problem_version_id, ordinal, name, input_data, expected_output, is_hidden)
SELECT pv.id, t.ordinal, t.name, t.input_data, t.expected_output, t.is_hidden
FROM pv
CROSS JOIN (VALUES
    (1, 'Positive list', '4 9 2', '9', false),
    (2, 'All negative numbers', '-10 -3 -25', '-3', false),
    (3, 'Single negative element', '-99', '-99', true),
    (4, 'Mixed with zero', '-5 0 -1', '0', true),
    (5, 'Duplicate maximums', '-7 -7 -12', '-7', true)
) AS t(ordinal, name, input_data, expected_output, is_hidden)
ON CONFLICT (problem_version_id, ordinal) DO UPDATE SET
    input_data = EXCLUDED.input_data,
    expected_output = EXCLUDED.expected_output,
    is_hidden = EXCLUDED.is_hidden;

-- Ensure current_published_version_id points to the latest published version for all seeded problems
UPDATE public.problems p
SET current_published_version_id = pv.id
FROM public.problem_versions pv
WHERE pv.problem_id = p.id
  AND pv.status = 'published'
  AND p.current_published_version_id IS NULL;

