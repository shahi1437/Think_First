-- =============================================================================
-- Seed 002: Error Taxonomy + Genuinely Distinct Linked Transfer Challenges
-- =============================================================================

-- 1. Error Taxonomy (8 classes matching ML classifier)
INSERT INTO public.error_taxonomy (code, display_name, description, is_observable_runtime)
VALUES
    ('syntax_error', 'Syntax Error', 'Code violates Python grammar rules (missing colon, unmatched bracket, bad indentation, or invalid operator).', true),
    ('runtime_error', 'Runtime Error', 'Execution raised an unhandled exception such as ZeroDivisionError, TypeError, NameError, KeyError, or AttributeError.', true),
    ('indexing_error', 'Indexing Error', 'List/string index is out of bounds (IndexError) or accesses the wrong 0-based position.', false),
    ('loop_boundary_error', 'Loop Boundary Error', 'Off-by-one loop start, stop, or range() exclusive upper bound omits or adds an unintended iteration.', false),
    ('condition_error', 'Condition Error', 'Branch predicate uses an inverted comparator, wrong boundary (< vs <=), or incorrect boolean connector (and vs or).', false),
    ('initialization_error', 'Initialization Error', 'Accumulator or extremum variable starts with an invalid sentinel value (e.g., 0 for negative max or product) or resets inside a loop.', false),
    ('function_return_error', 'Function Return Error', 'Function omits a return statement (returning None), returns early inside a loop, or returns the wrong value.', false),
    ('logic_error', 'Logic Error', 'Algorithmic formula, arithmetic operation, or update order produces incorrect output despite valid syntax and loop bounds.', false)
ON CONFLICT (code) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    is_observable_runtime = EXCLUDED.is_observable_runtime;

-- 2. Transfer Challenge A (linked to debug-range-sum-off-by-one):
-- Genuinely distinct problem: Inclusive Step Range Sum (3 inputs: start, end, step)
WITH p AS (
    INSERT INTO public.problems (slug)
    VALUES ('transfer-step-range-sum')
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
        'Transfer Challenge: Inclusive Step Range Sum',
        E'Write a Python program that reads three integers `start`, `end`, and `step` (`start <= end`, `step > 0`) on one line and prints the sum of every `step`-th integer starting at `start` up to and **including** `end` (if `end` lands on a step).\n\n### Input\nThree space-separated integers: `start end step`.\n\n### Output\nA single integer: the inclusive stepped sum.\n\n*Independent Verification: Solve without AI hints to verify you can apply loop boundary reasoning to a new problem.*',
        'beginner', 'coding',
        ARRAY['loops', 'loop-boundary-debugging'],
        ARRAY['loop-boundaries', 'step-iteration'],
        ARRAY['variables', 'loops'],
        ARRAY['Apply inclusive upper bounds to stepped ranges', 'Handle exact endpoint hits and non-hits independently'],
        '[{"input":"2 10 2","output":"30","explanation":"2 + 4 + 6 + 8 + 10 = 30"},{"input":"1 7 3","output":"12","explanation":"1 + 4 + 7 = 12"}]'::jsonb,
        2000, 131072, 'published', now(), now()
    FROM p
    ON CONFLICT (problem_id, version_number) DO UPDATE SET
        title = EXCLUDED.title,
        status = 'published',
        published_at = COALESCE(public.problem_versions.published_at, now())
    RETURNING id, problem_id
),
var AS (
    INSERT INTO public.problem_language_variants (problem_version_id, language_slug, starter_code)
    SELECT
        pv.id, 'python',
        E'def step_range_sum(start: int, end: int, step: int) -> int:\n    # Write your independent solution below\n    pass\n\nif __name__ == "__main__":\n    start, end, step = map(int, input().split())\n    print(step_range_sum(start, end, step))\n'
    FROM pv
    ON CONFLICT (problem_version_id, language_slug) DO UPDATE SET starter_code = EXCLUDED.starter_code
    RETURNING id
),
ref AS (
    INSERT INTO public.problem_reference_solutions (variant_id, reference_solution)
    SELECT
        var.id,
        E'def step_range_sum(start: int, end: int, step: int) -> int:\n    total = 0\n    for value in range(start, end + 1, step):\n        total += value\n    return total\n\nif __name__ == "__main__":\n    start, end, step = map(int, input().split())\n    print(step_range_sum(start, end, step))\n'
    FROM var
    ON CONFLICT (variant_id) DO UPDATE SET reference_solution = EXCLUDED.reference_solution
)
INSERT INTO public.test_cases (problem_version_id, ordinal, name, input_data, expected_output, is_hidden)
SELECT pv.id, t.ordinal, t.name, t.input_data, t.expected_output, t.is_hidden
FROM pv
CROSS JOIN (VALUES
    (1, 'Even step hitting endpoint', '2 10 2', '30', false),
    (2, 'Step of 3 hitting endpoint', '1 7 3', '12', false),
    (3, 'Endpoint not on step grid', '1 8 3', '12', true),
    (4, 'Single point start == end', '5 5 2', '5', true),
    (5, 'Negative to positive step', '-4 4 4', '0', true)
) AS t(ordinal, name, input_data, expected_output, is_hidden)
ON CONFLICT (problem_version_id, ordinal) DO UPDATE SET
    input_data = EXCLUDED.input_data,
    expected_output = EXCLUDED.expected_output,
    is_hidden = EXCLUDED.is_hidden;

-- 3. Transfer Challenge B (linked to debug-max-negative-init):
-- Genuinely distinct problem: Minimum Temperature Reading (positive-only & negative-only)
WITH p AS (
    INSERT INTO public.problems (slug)
    VALUES ('transfer-min-temperature')
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
        'Transfer Challenge: Minimum Temperature Reading',
        E'A weather station records one line of space-separated integer temperatures (which may be all positive, all negative, or mixed). Print the **lowest** recorded temperature.\n\n### Input\nOne line of one or more space-separated integers.\n\n### Output\nThe single minimum integer temperature.\n\n*Independent Verification: Solve without AI hints to verify safe accumulator initialization on positive-only and negative-only inputs.*',
        'basic', 'coding',
        ARRAY['lists', 'initialization-debugging'],
        ARRAY['variable-initialization', 'edge-case-testing'],
        ARRAY['loops', 'lists'],
        ARRAY['Initialize extremum variables from input data rather than arbitrary constants', 'Verify behavior on all-positive and all-negative lists'],
        '[{"input":"18 24 15 30","output":"15","explanation":"All positive readings; lowest is 15"},{"input":"-4 -12 -7","output":"-12","explanation":"All negative readings; lowest is -12"}]'::jsonb,
        2000, 131072, 'published', now(), now()
    FROM p
    ON CONFLICT (problem_id, version_number) DO UPDATE SET
        title = EXCLUDED.title,
        status = 'published',
        published_at = COALESCE(public.problem_versions.published_at, now())
    RETURNING id, problem_id
),
var AS (
    INSERT INTO public.problem_language_variants (problem_version_id, language_slug, starter_code)
    SELECT
        pv.id, 'python',
        E'def lowest_temperature(readings: list[int]) -> int:\n    # Write your independent solution below\n    pass\n\nif __name__ == "__main__":\n    readings = [int(x) for x in input().split()]\n    print(lowest_temperature(readings))\n'
    FROM pv
    ON CONFLICT (problem_version_id, language_slug) DO UPDATE SET starter_code = EXCLUDED.starter_code
    RETURNING id
),
ref AS (
    INSERT INTO public.problem_reference_solutions (variant_id, reference_solution)
    SELECT
        var.id,
        E'def lowest_temperature(readings: list[int]) -> int:\n    lowest = readings[0]\n    for temp in readings[1:]:\n        if temp < lowest:\n            lowest = temp\n    return lowest\n\nif __name__ == "__main__":\n    readings = [int(x) for x in input().split()]\n    print(lowest_temperature(readings))\n'
    FROM var
    ON CONFLICT (variant_id) DO UPDATE SET reference_solution = EXCLUDED.reference_solution
)
INSERT INTO public.test_cases (problem_version_id, ordinal, name, input_data, expected_output, is_hidden)
SELECT pv.id, t.ordinal, t.name, t.input_data, t.expected_output, t.is_hidden
FROM pv
CROSS JOIN (VALUES
    (1, 'All positive temperatures', '18 24 15 30', '15', false),
    (2, 'All negative temperatures', '-4 -12 -7', '-12', false),
    (3, 'Single positive element', '42', '42', true),
    (4, 'Mixed around zero', '5 0 -1 12', '-1', true),
    (5, 'High positive temperatures', '105 210 99 150', '99', true)
) AS t(ordinal, name, input_data, expected_output, is_hidden)
ON CONFLICT (problem_version_id, ordinal) DO UPDATE SET
    input_data = EXCLUDED.input_data,
    expected_output = EXCLUDED.expected_output,
    is_hidden = EXCLUDED.is_hidden;

-- Ensure current_published_version_id is set for newly seeded transfer problems
UPDATE public.problems p
SET current_published_version_id = pv.id
FROM public.problem_versions pv
WHERE pv.problem_id = p.id
  AND pv.status = 'published'
  AND p.current_published_version_id IS NULL;

-- 4. Link Debugging Problems -> Unseen Transfer Verification Challenges
INSERT INTO public.verification_links (
    source_problem_id, transfer_problem_id, skill_focus, max_hints_allowed, instructions_md
)
SELECT
    src.id,
    dst.id,
    'loop-boundary-reasoning',
    0,
    'Now prove independent mastery: solve this unseen stepped-range problem without AI hints using Judge0 verification.'
FROM public.problems src
JOIN public.problems dst ON dst.slug = 'transfer-step-range-sum'
WHERE src.slug = 'debug-range-sum-off-by-one'
ON CONFLICT (source_problem_id, transfer_problem_id) DO UPDATE SET
    skill_focus = EXCLUDED.skill_focus,
    instructions_md = EXCLUDED.instructions_md;

INSERT INTO public.verification_links (
    source_problem_id, transfer_problem_id, skill_focus, max_hints_allowed, instructions_md
)
SELECT
    src.id,
    dst.id,
    'accumulator-initialization',
    0,
    'Prove independent transfer: solve this unseen minimum-temperature problem without AI hints so your initialization strategy works for both positive and negative inputs.'
FROM public.problems src
JOIN public.problems dst ON dst.slug = 'transfer-min-temperature'
WHERE src.slug = 'debug-max-negative-init'
ON CONFLICT (source_problem_id, transfer_problem_id) DO UPDATE SET
    skill_focus = EXCLUDED.skill_focus,
    instructions_md = EXCLUDED.instructions_md;
