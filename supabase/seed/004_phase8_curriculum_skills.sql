-- =============================================================================
-- Seed 004: Expanded Intermediate & Advanced Skill Graph Nodes & Track Mapping
-- Safe Public Curriculum Metadata (Zero private solutions or hidden test keys)
-- =============================================================================

INSERT INTO public.skill_nodes (
    slug, title_en, title_bn, description_en, description_bn, domain_slug, tier, display_order
)
VALUES
(
    'nested_control_flow',
    'Nested Control Flow & State',
    'নেস্টেড কন্ট্রোল ফ্লো ও স্টেট',
    'Coordinating nested loops, break/continue guards, and state flags without off-by-one drift.',
    'নেস্টেড লুপ, break/continue গার্ড এবং স্টেট ফ্ল্যাগ সঠিকভাবে সমন্বয় করা।',
    'loop_boundaries',
    3,
    11
),
(
    'dictionaries_strings',
    'Strings, Sets & Dictionaries',
    'স্ট্রিং, সেট ও ডিকশনারি',
    'Efficient string parsing, frequency maps, grouping, and safe dictionary lookup patterns.',
    'স্ট্রিং পার্সিং, ফ্রিকোয়েন্সি ম্যাপ, গ্রুপিং এবং নিরাপদ ডিকশনারি লুকআপ।',
    'arrays_lists',
    4,
    12
),
(
    'searching_sorting',
    'Searching & Sorting Fundamentals',
    'সার্চিং ও সর্টিংয়ের মূলনীতি',
    'Binary search invariants, custom sort keys, and avoiding boundary infinite loops.',
    'বাইনারি সার্চ ইনভ্যারিয়েন্ট, কাস্টম সর্ট কী এবং অসীম লুপ এড়ানো।',
    'indexing',
    4,
    13
),
(
    'input_validation_edge_cases',
    'Validation, Complexity & Edge Cases',
    'ইনপুট ভ্যালিডেশন, কমপ্লেক্সিটি ও এজ-কেস',
    'Empty/single-element boundary handling, O(n) vs O(n^2) reasoning, and invariant testing.',
    'খালি/এক-উপাদান এজ-কেস সামলানো, O(n) বনাম O(n^2) বিশ্লেষণ এবং ইনভ্যারিয়েন্ট টেস্টিং।',
    'mixed_logic',
    4,
    14
),
(
    'recursion_fundamentals',
    'Recursion & Call-Stack Reasoning',
    'রিকার্সন ও কল-স্ট্যাক বিশ্লেষণ',
    'Base cases, recursive state reduction, stack depth, and avoiding missing returns in recursion.',
    'বেস কেস, রিকার্সিভ স্টেট হ্রাস, স্ট্যাক গভীরতা এবং রিকার্সনে মিসিং রিটার্ন এড়ানো।',
    'functions',
    5,
    15
),
(
    'data_structures_graphs',
    'Stacks, Queues & Graph Traversal',
    'স্ট্যাক, কিউ ও গ্রাফ ট্রাভার্সাল',
    'Adjacency lists, BFS/DFS visited-set tracking, cycle detection, and queue invariants.',
    'অ্যাডজাসেন্সি লিস্ট, BFS/DFS ভিজিটেড সেট, সাইকেল শনাক্তকরণ ও কিউ ইনভ্যারিয়েন্ট।',
    'mixed_logic',
    5,
    16
),
(
    'dynamic_programming',
    'Dynamic Programming Fundamentals',
    'ডাইনামিক প্রোগ্রামিংয়ের মূলনীতি',
    'Memoization, 1D/2D DP state transitions, base initialization, and overlapping subproblems.',
    'মেমোয়াইজেশন, 1D/2D DP স্টেট ট্রানজিশন, বেস ইনিশিয়ালাইজেশন এবং ওভারল্যাপিং সাবপ্রবলেম।',
    'mixed_logic',
    5,
    17
),
(
    'stateful_debugging_optimization',
    'Stateful Debugging & Trade-offs',
    'স্টেটফুল ডিবাগিং ও পারফরম্যান্স ট্রেড-অফ',
    'Diagnosing aliasing/mutation bugs, stale DP/BFS state, and time-memory optimization trade-offs.',
    'অ্যালিয়াসিং/মিউটেশন বাগ, পুরনো DP/BFS স্টেট এবং সময়-মেমরি ট্রেড-অফ নির্ণয়।',
    'syntax_runtime_debugging',
    5,
    18
)
ON CONFLICT (slug) DO UPDATE SET
    title_en = EXCLUDED.title_en,
    title_bn = EXCLUDED.title_bn,
    description_en = EXCLUDED.description_en,
    description_bn = EXCLUDED.description_bn,
    domain_slug = EXCLUDED.domain_slug,
    tier = EXCLUDED.tier,
    display_order = EXCLUDED.display_order;

INSERT INTO public.skill_prerequisites (skill_slug, prerequisite_slug)
VALUES
    ('nested_control_flow', 'loops'),
    ('nested_control_flow', 'conditions'),
    ('dictionaries_strings', 'lists'),
    ('dictionaries_strings', 'indexing'),
    ('searching_sorting', 'indexing'),
    ('searching_sorting', 'nested_control_flow'),
    ('input_validation_edge_cases', 'functions'),
    ('input_validation_edge_cases', 'debugging_basics'),
    ('recursion_fundamentals', 'functions'),
    ('data_structures_graphs', 'dictionaries_strings'),
    ('data_structures_graphs', 'recursion_fundamentals'),
    ('dynamic_programming', 'recursion_fundamentals'),
    ('dynamic_programming', 'searching_sorting'),
    ('stateful_debugging_optimization', 'input_validation_edge_cases'),
    ('stateful_debugging_optimization', 'dynamic_programming'),
    ('stateful_debugging_optimization', 'data_structures_graphs')
ON CONFLICT DO NOTHING;

-- Update Intermediate & Advanced Track recommended focus skills to reflect expanded DAG
UPDATE public.learning_tracks
SET recommended_focus_skills = ARRAY[
    'nested_control_flow',
    'dictionaries_strings',
    'searching_sorting',
    'input_validation_edge_cases',
    'debugging_basics'
]
WHERE slug = 'intermediate';

UPDATE public.learning_tracks
SET recommended_focus_skills = ARRAY[
    'recursion_fundamentals',
    'data_structures_graphs',
    'dynamic_programming',
    'stateful_debugging_optimization',
    'mixed_problem_solving'
]
WHERE slug = 'advanced';
