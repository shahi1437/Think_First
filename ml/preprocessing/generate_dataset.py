"""Reproducible execution-validated Python mistake dataset generator.

Generates 32+ original Python program families with controlled, realistic student
mutations across all 8 error taxonomy classes. Every single candidate sample is
executed in an isolated subprocess against its ground-truth test suite; only
samples that demonstrably fail (compile error, runtime error, or wrong answer)
are retained with full execution evidence and program-family grouping metadata.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ml.preprocessing.features import ERROR_TAXONOMY, extract_exception_name


@dataclass(frozen=True)
class ProgramFamily:
    family_id: str
    topic: str
    reference_code: str
    tests: tuple[tuple[str, str], ...]
    mutations: tuple[tuple[str, str, str], ...]  # (mutation_name, label, buggy_code)


def _build_families() -> list[ProgramFamily]:
    """32 original Python program families spanning beginner to intermediate CS topics."""
    families: list[ProgramFamily] = []

    # -------------------------------------------------------------------------
    # Template builders to create genuinely distinct original program families
    # across loops, lists, strings, math, dicts, searching, and functions
    # -------------------------------------------------------------------------

    # 1. Inclusive Range Sum
    families.append(
        ProgramFamily(
            family_id="fam_01_range_sum",
            topic="loops",
            reference_code=(
                "def solve(a, b):\n"
                "    total = 0\n"
                "    for i in range(a, b + 1):\n"
                "        total += i\n"
                "    return total\n"
                "a, b = map(int, input().split())\n"
                "print(solve(a, b))\n"
            ),
            tests=(("3 5", "12"), ("1 4", "10"), ("-2 2", "0")),
            mutations=(
                ("missing_colon_for", "syntax_error", "def solve(a, b):\n    total = 0\n    for i in range(a, b + 1)\n        total += i\n    return total\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("unmatched_paren", "syntax_error", "def solve(a, b):\n    return sum(range(a, b + 1)\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("undefined_var", "runtime_error", "def solve(a, b):\n    total = 0\n    for i in range(a, b + 1):\n        totl += i\n    return total\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("type_error_str_add", "runtime_error", "def solve(a, b):\n    total = '0'\n    for i in range(a, b + 1):\n        total += i\n    return total\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("range_exclusive_upper", "loop_boundary_error", "def solve(a, b):\n    total = 0\n    for i in range(a, b):\n        total += i\n    return total\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("range_skip_start", "loop_boundary_error", "def solve(a, b):\n    total = 0\n    for i in range(a + 1, b + 1):\n        total += i\n    return total\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("init_total_one", "initialization_error", "def solve(a, b):\n    total = 1\n    for i in range(a, b + 1):\n        total += i\n    return total\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("missing_return", "function_return_error", "def solve(a, b):\n    total = 0\n    for i in range(a, b + 1):\n        total += i\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("early_return_in_loop", "function_return_error", "def solve(a, b):\n    total = 0\n    for i in range(a, b + 1):\n        total += i\n        return total\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
                ("subtract_instead_of_add", "logic_error", "def solve(a, b):\n    total = 0\n    for i in range(a, b + 1):\n        total -= i\n    return total\na, b = map(int, input().split())\nprint(solve(a, b))\n"),
            ),
        )
    )

    # 2. Maximum in Integer List (including all-negative)
    families.append(
        ProgramFamily(
            family_id="fam_02_max_list",
            topic="lists",
            reference_code=(
                "def find_max(nums):\n"
                "    best = nums[0]\n"
                "    for x in nums[1:]:\n"
                "        if x > best:\n"
                "            best = x\n"
                "    return best\n"
                "nums = [int(v) for v in input().split()]\n"
                "print(find_max(nums))\n"
            ),
            tests=(("4 9 2", "9"), ("-10 -3 -25", "-3"), ("12 4 7", "12"), ("1 3 15", "15")),
            mutations=(
                ("missing_colon_if", "syntax_error", "def find_max(nums):\n    best = nums[0]\n    for x in nums:\n        if x > best\n            best = x\n    return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("index_out_of_range", "indexing_error", "def find_max(nums):\n    best = nums[0]\n    for i in range(len(nums) + 1):\n        if nums[i] > best:\n            best = nums[i]\n    return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("index_skip_first", "indexing_error", "def find_max(nums):\n    best = nums[1]\n    for i in range(1, len(nums)):\n        if nums[i] > best:\n            best = nums[i]\n    return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("init_zero_max", "initialization_error", "def find_max(nums):\n    best = 0\n    for x in nums:\n        if x > best:\n            best = x\n    return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("inverted_comparator", "condition_error", "def find_max(nums):\n    best = nums[0]\n    for x in nums:\n        if x < best:\n            best = x\n    return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("loop_skips_last", "loop_boundary_error", "def find_max(nums):\n    best = nums[0]\n    for i in range(len(nums) - 1):\n        if nums[i] > best:\n            best = nums[i]\n    return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("missing_return", "function_return_error", "def find_max(nums):\n    best = nums[0]\n    for x in nums:\n        if x > best:\n            best = x\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("early_return", "function_return_error", "def find_max(nums):\n    best = nums[0]\n    for x in nums:\n        if x > best:\n            best = x\n        return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("type_error_int_len", "runtime_error", "def find_max(nums):\n    best = nums[0]\n    for x in len(nums):\n        if x > best:\n            best = x\n    return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
                ("adds_instead_of_assign", "logic_error", "def find_max(nums):\n    best = nums[0]\n    for x in nums[1:]:\n        if x > best:\n            best += x\n    return best\nnums = [int(v) for v in input().split()]\nprint(find_max(nums))\n"),
            ),
        )
    )

    # 3. Minimum in Positive Integer List
    families.append(
        ProgramFamily(
            family_id="fam_03_min_list",
            topic="lists",
            reference_code=(
                "def find_min(nums):\n"
                "    low = nums[0]\n"
                "    for x in nums[1:]:\n"
                "        if x < low:\n"
                "            low = x\n"
                "    return low\n"
                "nums = [int(v) for v in input().split()]\n"
                "print(find_min(nums))\n"
            ),
            tests=(("8 3 11 2", "2"), ("15 22 9", "9"), ("5 12 4", "4")),
            mutations=(
                ("init_zero_min", "initialization_error", "def find_min(nums):\n    low = 0\n    for x in nums:\n        if x < low:\n            low = x\n    return low\nnums = [int(v) for v in input().split()]\nprint(find_min(nums))\n"),
                ("inverted_cmp", "condition_error", "def find_min(nums):\n    low = nums[0]\n    for x in nums:\n        if x > low:\n            low = x\n    return low\nnums = [int(v) for v in input().split()]\nprint(find_min(nums))\n"),
                ("loop_drops_last", "loop_boundary_error", "def find_min(nums):\n    low = nums[0]\n    for i in range(len(nums) - 1):\n        if nums[i] < low:\n            low = nums[i]\n    return low\nnums = [int(v) for v in input().split()]\nprint(find_min(nums))\n"),
                ("index_past_end", "indexing_error", "def find_min(nums):\n    low = nums[0]\n    for i in range(len(nums)):\n        if nums[i + 1] < low:\n            low = nums[i + 1]\n    return low\nnums = [int(v) for v in input().split()]\nprint(find_min(nums))\n"),
                ("no_return", "function_return_error", "def find_min(nums):\n    low = nums[0]\n    for x in nums:\n        if x < low:\n            low = x\nnums = [int(v) for v in input().split()]\nprint(find_min(nums))\n"),
                ("assign_in_if_syntax", "syntax_error", "def find_min(nums):\n    low = nums[0]\n    for x in nums:\n        if x = low:\n            low = x\n    return low\nnums = [int(v) for v in input().split()]\nprint(find_min(nums))\n"),
                ("zero_div_runtime", "runtime_error", "def find_min(nums):\n    low = nums[0] / 0\n    return low\nnums = [int(v) for v in input().split()]\nprint(find_min(nums))\n"),
                ("wrong_logic_avg", "logic_error", "def find_min(nums):\n    return sum(nums) // len(nums)\nnums = [int(v) for v in input().split()]\nprint(find_min(nums))\n"),
            ),
        )
    )

    # 4. Product of List Elements
    families.append(
        ProgramFamily(
            family_id="fam_04_product_list",
            topic="loops",
            reference_code=(
                "def list_product(nums):\n"
                "    prod = 1\n"
                "    for n in nums:\n"
                "        prod *= n\n"
                "    return prod\n"
                "nums = [int(v) for v in input().split()]\n"
                "print(list_product(nums))\n"
            ),
            tests=(("2 3 4", "24"), ("5 2 3", "30"), ("-2 3 4", "-24")),
            mutations=(
                ("init_prod_zero", "initialization_error", "def list_product(nums):\n    prod = 0\n    for n in nums:\n        prod *= n\n    return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
                ("reset_prod_in_loop", "initialization_error", "def list_product(nums):\n    for n in nums:\n        prod = 1\n        prod *= n\n    return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
                ("add_instead_of_mul", "logic_error", "def list_product(nums):\n    prod = 1\n    for n in nums:\n        prod += n\n    return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
                ("skip_first_loop", "loop_boundary_error", "def list_product(nums):\n    prod = 1\n    for i in range(1, len(nums)):\n        prod *= nums[i]\n    return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
                ("skip_last_loop", "loop_boundary_error", "def list_product(nums):\n    prod = 1\n    for i in range(0, len(nums) - 1):\n        prod *= nums[i]\n    return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
                ("index_len_oob", "indexing_error", "def list_product(nums):\n    prod = 1\n    for i in range(len(nums) + 1):\n        prod *= nums[i]\n    return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
                ("early_return_loop", "function_return_error", "def list_product(nums):\n    prod = 1\n    for n in nums:\n        prod *= n\n        return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
                ("missing_colon_def", "syntax_error", "def list_product(nums)\n    prod = 1\n    for n in nums:\n        prod *= n\n    return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
                ("name_error_typo", "runtime_error", "def list_product(nums):\n    prod = 1\n    for n in nums:\n        product *= n\n    return prod\nnums = [int(v) for v in input().split()]\nprint(list_product(nums))\n"),
            ),
        )
    )

    # 5. Sum of Even Numbers
    families.append(
        ProgramFamily(
            family_id="fam_05_sum_even",
            topic="conditionals",
            reference_code=(
                "def sum_even(nums):\n"
                "    total = 0\n"
                "    for n in nums:\n"
                "        if n % 2 == 0:\n"
                "            total += n\n"
                "    return total\n"
                "nums = [int(v) for v in input().split()]\n"
                "print(sum_even(nums))\n"
            ),
            tests=(("1 2 3 4 5 6", "12"), ("2 4 7", "6"), ("-4 3 8", "4")),
            mutations=(
                ("odd_instead_of_even", "condition_error", "def sum_even(nums):\n    total = 0\n    for n in nums:\n        if n % 2 != 0:\n            total += n\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
                ("positive_even_only", "condition_error", "def sum_even(nums):\n    total = 0\n    for n in nums:\n        if n % 2 == 0 and n > 0:\n            total += n\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
                ("count_instead_of_sum", "logic_error", "def sum_even(nums):\n    total = 0\n    for n in nums:\n        if n % 2 == 0:\n            total += 1\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
                ("init_total_ten", "initialization_error", "def sum_even(nums):\n    total = 1\n    for n in nums:\n        if n % 2 == 0:\n            total += n\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
                ("range_misses_last", "loop_boundary_error", "def sum_even(nums):\n    total = 0\n    for i in range(len(nums) - 1):\n        if nums[i] % 2 == 0:\n            total += nums[i]\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
                ("index_oob", "indexing_error", "def sum_even(nums):\n    total = 0\n    for i in range(1, len(nums) + 1):\n        if nums[i] % 2 == 0:\n            total += nums[i]\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
                ("returns_inside_if", "function_return_error", "def sum_even(nums):\n    total = 0\n    for n in nums:\n        if n % 2 == 0:\n            total += n\n            return total\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
                ("bad_syntax_mod", "syntax_error", "def sum_even(nums):\n    total = 0\n    for n in nums:\n        if n % 2 = 0:\n            total += n\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
                ("zero_mod_runtime", "runtime_error", "def sum_even(nums):\n    total = 0\n    for n in nums:\n        if n % 0 == 0:\n            total += n\n    return total\nnums = [int(v) for v in input().split()]\nprint(sum_even(nums))\n"),
            ),
        )
    )

    # 6. Factorial of N
    families.append(
        ProgramFamily(
            family_id="fam_06_factorial",
            topic="loops",
            reference_code=(
                "def factorial(n):\n"
                "    ans = 1\n"
                "    for i in range(1, n + 1):\n"
                "        ans *= i\n"
                "    return ans\n"
                "print(factorial(int(input())))\n"
            ),
            tests=(("5", "120"), ("4", "24"), ("1", "1")),
            mutations=(
                ("init_ans_zero", "initialization_error", "def factorial(n):\n    ans = 0\n    for i in range(1, n + 1):\n        ans *= i\n    return ans\nprint(factorial(int(input())))\n"),
                ("range_stops_at_n", "loop_boundary_error", "def factorial(n):\n    ans = 1\n    for i in range(1, n):\n        ans *= i\n    return ans\nprint(factorial(int(input())))\n"),
                ("range_starts_at_zero", "loop_boundary_error", "def factorial(n):\n    ans = 1\n    for i in range(0, n + 1):\n        ans *= i\n    return ans\nprint(factorial(int(input())))\n"),
                ("adds_instead_of_mul", "logic_error", "def factorial(n):\n    ans = 1\n    for i in range(1, n + 1):\n        ans += i\n    return ans\nprint(factorial(int(input())))\n"),
                ("missing_return", "function_return_error", "def factorial(n):\n    ans = 1\n    for i in range(1, n + 1):\n        ans *= i\nprint(factorial(int(input())))\n"),
                ("early_return", "function_return_error", "def factorial(n):\n    ans = 1\n    for i in range(1, n + 1):\n        ans *= i\n        return ans\nprint(factorial(int(input())))\n"),
                ("indent_syntax", "syntax_error", "def factorial(n):\nans = 1\n    return ans\nprint(factorial(int(input())))\n"),
                ("type_error_range_str", "runtime_error", "def factorial(n):\n    ans = 1\n    for i in range('1', n + 1):\n        ans *= i\n    return ans\nprint(factorial(int(input())))\n"),
            ),
        )
    )

    # 7. Count Vowels in String
    families.append(
        ProgramFamily(
            family_id="fam_07_count_vowels",
            topic="strings",
            reference_code=(
                "def count_vowels(text):\n"
                "    count = 0\n"
                "    for ch in text.lower():\n"
                "        if ch in 'aeiou':\n"
                "            count += 1\n"
                "    return count\n"
                "print(count_vowels(input().strip()))\n"
            ),
            tests=(("education", "5"), ("Python", "1"), ("AEIOU", "5")),
            mutations=(
                ("missing_lowercase_cond", "condition_error", "def count_vowels(text):\n    count = 0\n    for ch in text:\n        if ch in 'aeiou':\n            count += 1\n    return count\nprint(count_vowels(input().strip()))\n"),
                ("counts_consonants", "condition_error", "def count_vowels(text):\n    count = 0\n    for ch in text.lower():\n        if ch not in 'aeiou':\n            count += 1\n    return count\nprint(count_vowels(input().strip()))\n"),
                ("init_count_one", "initialization_error", "def count_vowels(text):\n    count = 1\n    for ch in text.lower():\n        if ch in 'aeiou':\n            count += 1\n    return count\nprint(count_vowels(input().strip()))\n"),
                ("loop_skips_last_char", "loop_boundary_error", "def count_vowels(text):\n    count = 0\n    for i in range(len(text) - 1):\n        if text[i].lower() in 'aeiou':\n            count += 1\n    return count\nprint(count_vowels(input().strip()))\n"),
                ("index_oob_str", "indexing_error", "def count_vowels(text):\n    count = 0\n    for i in range(len(text) + 1):\n        if text[i].lower() in 'aeiou':\n            count += 1\n    return count\nprint(count_vowels(input().strip()))\n"),
                ("missing_return", "function_return_error", "def count_vowels(text):\n    count = 0\n    for ch in text.lower():\n        if ch in 'aeiou':\n            count += 1\nprint(count_vowels(input().strip()))\n"),
                ("syntax_unclosed_quote", "syntax_error", "def count_vowels(text):\n    count = 0\n    for ch in text.lower():\n        if ch in 'aeiou:\n            count += 1\n    return count\nprint(count_vowels(input().strip()))\n"),
                ("attr_error_runtime", "runtime_error", "def count_vowels(text):\n    count = 0\n    for ch in text.toLower():\n        if ch in 'aeiou':\n            count += 1\n    return count\nprint(count_vowels(input().strip()))\n"),
                ("logic_adds_two", "logic_error", "def count_vowels(text):\n    count = 0\n    for ch in text.lower():\n        if ch in 'aeiou':\n            count += 2\n    return count\nprint(count_vowels(input().strip()))\n"),
            ),
        )
    )

    # 8. Palindrome Check
    families.append(
        ProgramFamily(
            family_id="fam_08_palindrome",
            topic="strings",
            reference_code=(
                "def is_palindrome(s):\n"
                "    left = 0\n"
                "    right = len(s) - 1\n"
                "    while left < right:\n"
                "        if s[left] != s[right]:\n"
                "            return False\n"
                "        left += 1\n"
                "        right -= 1\n"
                "    return True\n"
                "print(is_palindrome(input().strip()))\n"
            ),
            tests=(("radar", "True"), ("hello", "False"), ("abba", "True"), ("abca", "False"), ("xbbz", "False")),
            mutations=(
                ("right_init_len_oob", "indexing_error", "def is_palindrome(s):\n    left = 0\n    right = len(s)\n    while left < right:\n        if s[left] != s[right]:\n            return False\n        left += 1\n        right -= 1\n    return True\nprint(is_palindrome(input().strip()))\n"),
                ("early_return_true", "function_return_error", "def is_palindrome(s):\n    left = 0\n    right = len(s) - 1\n    while left < right:\n        if s[left] == s[right]:\n            return True\n        left += 1\n        right -= 1\n    return False\nprint(is_palindrome(input().strip()))\n"),
                ("inverted_cond", "condition_error", "def is_palindrome(s):\n    left = 0\n    right = len(s) - 1\n    while left < right:\n        if s[left] == s[right]:\n            return False\n        left += 1\n        right -= 1\n    return True\nprint(is_palindrome(input().strip()))\n"),
                ("wrong_pointer_update", "logic_error", "def is_palindrome(s):\n    left = 0\n    right = len(s) - 1\n    while left < right:\n        if s[left] != s[right]:\n            return False\n        left += 2\n        right -= 1\n    return True\nprint(is_palindrome(input().strip()))\n"),
                ("missing_return_true", "function_return_error", "def is_palindrome(s):\n    left = 0\n    right = len(s) - 1\n    while left < right:\n        if s[left] != s[right]:\n            return False\n        left += 1\n        right -= 1\nprint(is_palindrome(input().strip()))\n"),
                ("syntax_while_no_colon", "syntax_error", "def is_palindrome(s):\n    left = 0\n    right = len(s) - 1\n    while left < right\n        left += 1\n    return True\nprint(is_palindrome(input().strip()))\n"),
                ("runtime_int_cast", "runtime_error", "def is_palindrome(s):\n    return int(s) == int(s[::-1])\nprint(is_palindrome(input().strip()))\n"),
                ("loop_starts_at_one", "loop_boundary_error", "def is_palindrome(s):\n    for i in range(1, len(s) // 2):\n        if s[i] != s[len(s) - 1 - i]:\n            return False\n    return True\nprint(is_palindrome(input().strip()))\n"),
            ),
        )
    )

    # 9-32: Programmatically build 24 additional genuinely distinct original CS problem families
    # Each has unique domain, variable names, structure, tests, and execution-validated mutations!

    extra_specs: list[dict[str, Any]] = [
        # 9. Linear Search First Index
        {
            "id": "fam_09_linear_search",
            "topic": "searching",
            "ref": "def search_idx(arr, target):\n    for i in range(len(arr)):\n        if arr[i] == target:\n            return i\n    return -1\nt = int(input())\narr = [int(x) for x in input().split()]\nprint(search_idx(arr, t))\n",
            "tests": (("7\n3 5 7 9", "2"), ("9\n3 5 7 9", "3"), ("1\n3 5 7 9", "-1")),
            "muts": [
                ("skip_last_idx", "loop_boundary_error", "def search_idx(arr, target):\n    for i in range(len(arr) - 1):\n        if arr[i] == target:\n            return i\n    return -1\nt = int(input())\narr = [int(x) for x in input().split()]\nprint(search_idx(arr, t))\n"),
                ("oob_idx", "indexing_error", "def search_idx(arr, target):\n    for i in range(len(arr) + 1):\n        if arr[i] == target:\n            return i\n    return -1\nt = int(input())\narr = [int(x) for x in input().split()]\nprint(search_idx(arr, t))\n"),
                ("early_else_return", "function_return_error", "def search_idx(arr, target):\n    for i in range(len(arr)):\n        if arr[i] == target:\n            return i\n        else:\n            return -1\nt = int(input())\narr = [int(x) for x in input().split()]\nprint(search_idx(arr, t))\n"),
                ("cond_neq", "condition_error", "def search_idx(arr, target):\n    for i in range(len(arr)):\n        if arr[i] != target:\n            return i\n    return -1\nt = int(input())\narr = [int(x) for x in input().split()]\nprint(search_idx(arr, t))\n"),
                ("returns_val_not_idx", "logic_error", "def search_idx(arr, target):\n    for i in range(len(arr)):\n        if arr[i] == target:\n            return arr[i]\n    return -1\nt = int(input())\narr = [int(x) for x in input().split()]\nprint(search_idx(arr, t))\n"),
                ("syntax_err", "syntax_error", "def search_idx(arr, target):\n    for i in range(len(arr)):\n        if arr[i] == target\n            return i\n    return -1\nt = int(input())\narr = [int(x) for x in input().split()]\nprint(search_idx(arr, t))\n"),
                ("runtime_err", "runtime_error", "def search_idx(arr, target):\n    for i in range(len(arr)):\n        if arr[i] == trget:\n            return i\n    return -1\nt = int(input())\narr = [int(x) for x in input().split()]\nprint(search_idx(arr, t))\n"),
            ],
        },
        # 10. Count Strictly Positive Numbers
        {
            "id": "fam_10_count_positive",
            "topic": "conditionals",
            "ref": "def count_pos(vals):\n    cnt = 0\n    for v in vals:\n        if v > 0:\n            cnt += 1\n    return cnt\nprint(count_pos([int(x) for x in input().split()]))\n",
            "tests": (("-2 0 3 5", "2"), ("0 0 1", "1"), ("-5 -1 0", "0")),
            "muts": [
                ("ge_zero_cond", "condition_error", "def count_pos(vals):\n    cnt = 0\n    for v in vals:\n        if v >= 0:\n            cnt += 1\n    return cnt\nprint(count_pos([int(x) for x in input().split()]))\n"),
                ("lt_zero_cond", "condition_error", "def count_pos(vals):\n    cnt = 0\n    for v in vals:\n        if v < 0:\n            cnt += 1\n    return cnt\nprint(count_pos([int(x) for x in input().split()]))\n"),
                ("init_cnt_one", "initialization_error", "def count_pos(vals):\n    cnt = 1\n    for v in vals:\n        if v > 0:\n            cnt += 1\n    return cnt\nprint(count_pos([int(x) for x in input().split()]))\n"),
                ("sum_instead_count", "logic_error", "def count_pos(vals):\n    cnt = 0\n    for v in vals:\n        if v > 0:\n            cnt += v\n    return cnt\nprint(count_pos([int(x) for x in input().split()]))\n"),
                ("skip_last_val", "loop_boundary_error", "def count_pos(vals):\n    cnt = 0\n    for i in range(len(vals) - 1):\n        if vals[i] > 0:\n            cnt += 1\n    return cnt\nprint(count_pos([int(x) for x in input().split()]))\n"),
                ("oob_val", "indexing_error", "def count_pos(vals):\n    cnt = 0\n    for i in range(len(vals) + 1):\n        if vals[i] > 0:\n            cnt += 1\n    return cnt\nprint(count_pos([int(x) for x in input().split()]))\n"),
                ("missing_return", "function_return_error", "def count_pos(vals):\n    cnt = 0\n    for v in vals:\n        if v > 0:\n            cnt += 1\nprint(count_pos([int(x) for x in input().split()]))\n"),
                ("syntax_bad_paren", "syntax_error", "def count_pos(vals:\n    return 0\nprint(count_pos([int(x) for x in input().split()]))\n"),
                ("runtime_div_zero", "runtime_error", "def count_pos(vals):\n    return sum(1 for v in vals if 10 / v > 0)\nprint(count_pos([int(x) for x in input().split()]))\n"),
            ],
        },
        # 11. Reverse List Manual
        {
            "id": "fam_11_reverse_list",
            "topic": "lists",
            "ref": "def rev_list(items):\n    out = []\n    for i in range(len(items) - 1, -1, -1):\n        out.append(items[i])\n    return out\narr = [int(x) for x in input().split()]\nprint(' '.join(map(str, rev_list(arr))))\n",
            "tests": (("1 2 3 4", "4 3 2 1"), ("9 5 2", "2 5 9")),
            "muts": [
                ("stops_at_zero_excl", "loop_boundary_error", "def rev_list(items):\n    out = []\n    for i in range(len(items) - 1, 0, -1):\n        out.append(items[i])\n    return out\narr = [int(x) for x in input().split()]\nprint(' '.join(map(str, rev_list(arr))))\n"),
                ("starts_at_len_oob", "indexing_error", "def rev_list(items):\n    out = []\n    for i in range(len(items), -1, -1):\n        out.append(items[i])\n    return out\narr = [int(x) for x in input().split()]\nprint(' '.join(map(str, rev_list(arr))))\n"),
                ("missing_return", "function_return_error", "def rev_list(items):\n    out = []\n    for i in range(len(items) - 1, -1, -1):\n        out.append(items[i])\narr = [int(x) for x in input().split()]\nprint(rev_list(arr))\n"),
                ("appends_forward_logic", "logic_error", "def rev_list(items):\n    out = []\n    for i in range(len(items)):\n        out.append(items[i])\n    return out\narr = [int(x) for x in input().split()]\nprint(' '.join(map(str, rev_list(arr))))\n"),
                ("attr_error_push", "runtime_error", "def rev_list(items):\n    out = []\n    for i in range(len(items) - 1, -1, -1):\n        out.push(items[i])\n    return out\narr = [int(x) for x in input().split()]\nprint(' '.join(map(str, rev_list(arr))))\n"),
                ("syntax_bracket", "syntax_error", "def rev_list(items):\n    out = [\n    return out\narr = [int(x) for x in input().split()]\nprint(rev_list(arr))\n"),
            ],
        },
        # 12. Count Adjacent Increasing Pairs
        {
            "id": "fam_12_adj_increasing",
            "topic": "indexing",
            "ref": "def count_inc(nums):\n    c = 0\n    for i in range(len(nums) - 1):\n        if nums[i + 1] > nums[i]:\n            c += 1\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n",
            "tests": (("1 3 2 5 6", "3"), ("5 4 3 2", "0"), ("1 2 2 3", "2")),
            "muts": [
                ("range_len_oob", "indexing_error", "def count_inc(nums):\n    c = 0\n    for i in range(len(nums)):\n        if nums[i + 1] > nums[i]:\n            c += 1\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n"),
                ("ge_instead_gt", "condition_error", "def count_inc(nums):\n    c = 0\n    for i in range(len(nums) - 1):\n        if nums[i + 1] >= nums[i]:\n            c += 1\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n"),
                ("lt_instead_gt", "condition_error", "def count_inc(nums):\n    c = 0\n    for i in range(len(nums) - 1):\n        if nums[i + 1] < nums[i]:\n            c += 1\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n"),
                ("range_len_minus_2", "loop_boundary_error", "def count_inc(nums):\n    c = 0\n    for i in range(len(nums) - 2):\n        if nums[i + 1] > nums[i]:\n            c += 1\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n"),
                ("init_c_one", "initialization_error", "def count_inc(nums):\n    c = 1\n    for i in range(len(nums) - 1):\n        if nums[i + 1] > nums[i]:\n            c += 1\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n"),
                ("early_ret", "function_return_error", "def count_inc(nums):\n    c = 0\n    for i in range(len(nums) - 1):\n        if nums[i + 1] > nums[i]:\n            c += 1\n            return c\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n"),
                ("adds_diff_logic", "logic_error", "def count_inc(nums):\n    c = 0\n    for i in range(len(nums) - 1):\n        if nums[i + 1] > nums[i]:\n            c += nums[i + 1] - nums[i]\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n"),
                ("syntax_err", "syntax_error", "def count_inc(nums):\n    c = 0\n    for i in range(len(nums) - 1)\n        c += 1\n    return c\nprint(count_inc([int(x) for x in input().split()]))\n"),
                ("runtime_type", "runtime_error", "def count_inc(nums):\n    return len(nums) + '1'\nprint(count_inc([int(x) for x in input().split()]))\n"),
            ],
        },
        # 13. Check Sorted Non-Decreasing
        {
            "id": "fam_13_is_sorted",
            "topic": "indexing",
            "ref": "def is_sorted(arr):\n    for i in range(len(arr) - 1):\n        if arr[i] > arr[i + 1]:\n            return False\n    return True\nprint(is_sorted([int(x) for x in input().split()]))\n",
            "tests": (("1 2 2 5", "True"), ("1 4 3 5", "False"), ("1 2 5 3", "False")),
            "muts": [
                ("oob_len", "indexing_error", "def is_sorted(arr):\n    for i in range(len(arr)):\n        if arr[i] > arr[i + 1]:\n            return False\n    return True\nprint(is_sorted([int(x) for x in input().split()]))\n"),
                ("strict_ge_cond", "condition_error", "def is_sorted(arr):\n    for i in range(len(arr) - 1):\n        if arr[i] >= arr[i + 1]:\n            return False\n    return True\nprint(is_sorted([int(x) for x in input().split()]))\n"),
                ("early_return_true", "function_return_error", "def is_sorted(arr):\n    for i in range(len(arr) - 1):\n        if arr[i] <= arr[i + 1]:\n            return True\n    return False\nprint(is_sorted([int(x) for x in input().split()]))\n"),
                ("misses_last_pair", "loop_boundary_error", "def is_sorted(arr):\n    for i in range(len(arr) - 2):\n        if arr[i] > arr[i + 1]:\n            return False\n    return True\nprint(is_sorted([int(x) for x in input().split()]))\n"),
                ("missing_return", "function_return_error", "def is_sorted(arr):\n    for i in range(len(arr) - 1):\n        if arr[i] > arr[i + 1]:\n            return False\nprint(is_sorted([int(x) for x in input().split()]))\n"),
                ("syntax_err", "syntax_error", "def is_sorted(arr):\n    for i in range(len(arr) - 1):\n        if arr[i] > arr[i + 1]\n            return False\n    return True\nprint(is_sorted([int(x) for x in input().split()]))\n"),
                ("runtime_name", "runtime_error", "def is_sorted(arr):\n    for i in range(length(arr) - 1):\n        if arr[i] > arr[i + 1]:\n            return False\n    return True\nprint(is_sorted([int(x) for x in input().split()]))\n"),
            ],
        },
        # 14. Leap Year Check
        {
            "id": "fam_14_leap_year",
            "topic": "conditionals",
            "ref": "def is_leap(y):\n    if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):\n        return True\n    return False\nprint(is_leap(int(input())))\n",
            "tests": (("2024", "True"), ("1900", "False"), ("2000", "True"), ("2023", "False"), ("1800", "False")),
            "muts": [
                ("missing_100_rule", "condition_error", "def is_leap(y):\n    return y % 4 == 0\nprint(is_leap(int(input())))\n"),
                ("and_instead_or", "condition_error", "def is_leap(y):\n    if (y % 4 == 0 and y % 100 != 0) and (y % 400 == 0):\n        return True\n    return False\nprint(is_leap(int(input())))\n"),
                ("or_instead_and", "condition_error", "def is_leap(y):\n    if (y % 4 == 0 or y % 100 != 0) or (y % 400 == 0):\n        return True\n    return False\nprint(is_leap(int(input())))\n"),
                ("missing_return_false", "function_return_error", "def is_leap(y):\n    if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):\n        return True\nprint(is_leap(int(input())))\n"),
                ("wrong_mod_40", "logic_error", "def is_leap(y):\n    return (y % 4 == 0 and y % 100 != 0) or (y % 40 == 0)\nprint(is_leap(int(input())))\n"),
                ("syntax_eq", "syntax_error", "def is_leap(y):\n    if y % 4 = 0:\n        return True\n    return False\nprint(is_leap(int(input())))\n"),
                ("runtime_str_mod", "runtime_error", "def is_leap(y):\n    return str(y) % 4 == 0\nprint(is_leap(int(input())))\n"),
            ],
        },
        # 15. Celsius to Fahrenheit
        {
            "id": "fam_15_c_to_f",
            "topic": "math",
            "ref": "def to_f(c):\n    return (c * 9) // 5 + 32\nprint(to_f(int(input())))\n",
            "tests": (("0", "32"), ("100", "212"), ("25", "77")),
            "muts": [
                ("missing_plus_32", "logic_error", "def to_f(c):\n    return (c * 9) // 5\nprint(to_f(int(input())))\n"),
                ("wrong_ratio_5_9", "logic_error", "def to_f(c):\n    return (c * 5) // 9 + 32\nprint(to_f(int(input())))\n"),
                ("sub_32_logic", "logic_error", "def to_f(c):\n    return (c * 9) // 5 - 32\nprint(to_f(int(input())))\n"),
                ("prints_no_return", "function_return_error", "def to_f(c):\n    f = (c * 9) // 5 + 32\nprint(to_f(int(input())))\n"),
                ("syntax_missing_paren", "syntax_error", "def to_f(c):\n    return (c * 9 // 5 + 32\nprint(to_f(int(input())))\n"),
                ("runtime_div_zero", "runtime_error", "def to_f(c):\n    return (c * 9) // (5 - 5) + 32\nprint(to_f(int(input())))\n"),
            ],
        },
        # 16. Grade Letter Classifier
        {
            "id": "fam_16_grade_letter",
            "topic": "conditionals",
            "ref": "def grade(score):\n    if score >= 90:\n        return 'A'\n    elif score >= 80:\n        return 'B'\n    elif score >= 70:\n        return 'C'\n    else:\n        return 'F'\nprint(grade(int(input())))\n",
            "tests": (("90", "A"), ("80", "B"), ("75", "C"), ("60", "F")),
            "muts": [
                ("strict_gt_90", "condition_error", "def grade(score):\n    if score > 90:\n        return 'A'\n    elif score > 80:\n        return 'B'\n    elif score >= 70:\n        return 'C'\n    else:\n        return 'F'\nprint(grade(int(input())))\n"),
                ("wrong_order_elif", "condition_error", "def grade(score):\n    if score >= 70:\n        return 'C'\n    elif score >= 80:\n        return 'B'\n    elif score >= 90:\n        return 'A'\n    else:\n        return 'F'\nprint(grade(int(input())))\n"),
                ("missing_return_f", "function_return_error", "def grade(score):\n    if score >= 90:\n        return 'A'\n    elif score >= 80:\n        return 'B'\n    elif score >= 70:\n        return 'C'\nprint(grade(int(input())))\n"),
                ("syntax_else_if", "syntax_error", "def grade(score):\n    if score >= 90:\n        return 'A'\n    else if score >= 80:\n        return 'B'\n    return 'F'\nprint(grade(int(input())))\n"),
                ("runtime_str_cmp", "runtime_error", "def grade(score):\n    if score >= '90':\n        return 'A'\n    return 'F'\nprint(grade(int(input())))\n"),
                ("wrong_thresholds_logic", "logic_error", "def grade(score):\n    if score >= 95:\n        return 'A'\n    elif score >= 85:\n        return 'B'\n    return 'F'\nprint(grade(int(input())))\n"),
            ],
        },
        # 17. Count Digits of Positive Integer
        {
            "id": "fam_17_count_digits",
            "topic": "loops",
            "ref": "def count_digits(n):\n    c = 0\n    while n > 0:\n        n //= 10\n        c += 1\n    return c\nprint(count_digits(int(input())))\n",
            "tests": (("12345", "5"), ("9", "1"), ("100", "3")),
            "muts": [
                ("init_c_one", "initialization_error", "def count_digits(n):\n    c = 1\n    while n > 0:\n        n //= 10\n        c += 1\n    return c\nprint(count_digits(int(input())))\n"),
                ("while_gt_10_bound", "loop_boundary_error", "def count_digits(n):\n    c = 0\n    while n > 10:\n        n //= 10\n        c += 1\n    return c\nprint(count_digits(int(input())))\n"),
                ("mod_instead_div_logic", "logic_error", "def count_digits(n):\n    c = 0\n    while n > 0:\n        c += n % 10\n        n //= 10\n    return c\nprint(count_digits(int(input())))\n"),
                ("early_return", "function_return_error", "def count_digits(n):\n    c = 0\n    while n > 0:\n        n //= 10\n        c += 1\n        return c\n    return c\nprint(count_digits(int(input())))\n"),
                ("syntax_colon", "syntax_error", "def count_digits(n):\n    c = 0\n    while n > 0\n        n //= 10\n        c += 1\n    return c\nprint(count_digits(int(input())))\n"),
                ("runtime_len_int", "runtime_error", "def count_digits(n):\n    return len(n)\nprint(count_digits(int(input())))\n"),
            ],
        },
        # 18. Sum of Digits
        {
            "id": "fam_18_digit_sum",
            "topic": "math",
            "ref": "def digit_sum(n):\n    s = 0\n    while n > 0:\n        s += n % 10\n        n //= 10\n    return s\nprint(digit_sum(int(input())))\n",
            "tests": (("1234", "10"), ("905", "14"), ("7", "7")),
            "muts": [
                ("init_s_one", "initialization_error", "def digit_sum(n):\n    s = 1\n    while n > 0:\n        s += n % 10\n        n //= 10\n    return s\nprint(digit_sum(int(input())))\n"),
                ("div_before_mod_logic", "logic_error", "def digit_sum(n):\n    s = 0\n    while n > 0:\n        n //= 10\n        s += n % 10\n    return s\nprint(digit_sum(int(input())))\n"),
                ("while_n_gt_1_bound", "loop_boundary_error", "def digit_sum(n):\n    s = 0\n    while n > 1:\n        s += n % 10\n        n //= 10\n    return s\nprint(digit_sum(int(input())))\n"),
                ("missing_return", "function_return_error", "def digit_sum(n):\n    s = 0\n    while n > 0:\n        s += n % 10\n        n //= 10\nprint(digit_sum(int(input())))\n"),
                ("runtime_iter_int", "runtime_error", "def digit_sum(n):\n    return sum(int(d) for d in n)\nprint(digit_sum(int(input())))\n"),
                ("syntax_err", "syntax_error", "def digit_sum(n)\n    return 0\nprint(digit_sum(int(input())))\n"),
            ],
        },
        # 19. Power a^b by Repeated Multiplication
        {
            "id": "fam_19_power_loop",
            "topic": "loops",
            "ref": "def power(base, exp):\n    res = 1\n    for _ in range(exp):\n        res *= base\n    return res\na, b = map(int, input().split())\nprint(power(a, b))\n",
            "tests": (("2 5", "32"), ("3 3", "27"), ("5 0", "1")),
            "muts": [
                ("init_res_zero", "initialization_error", "def power(base, exp):\n    res = 0\n    for _ in range(exp):\n        res *= base\n    return res\na, b = map(int, input().split())\nprint(power(a, b))\n"),
                ("range_exp_minus_1", "loop_boundary_error", "def power(base, exp):\n    res = 1\n    for _ in range(exp - 1):\n        res *= base\n    return res\na, b = map(int, input().split())\nprint(power(a, b))\n"),
                ("range_1_to_exp", "loop_boundary_error", "def power(base, exp):\n    res = 1\n    for _ in range(1, exp):\n        res *= base\n    return res\na, b = map(int, input().split())\nprint(power(a, b))\n"),
                ("adds_base_logic", "logic_error", "def power(base, exp):\n    res = 1\n    for _ in range(exp):\n        res += base\n    return res\na, b = map(int, input().split())\nprint(power(a, b))\n"),
                ("early_ret", "function_return_error", "def power(base, exp):\n    res = 1\n    for _ in range(exp):\n        res *= base\n        return res\n    return res\na, b = map(int, input().split())\nprint(power(a, b))\n"),
                ("syntax_err", "syntax_error", "def power(base, exp):\n    res = 1\n    for _ in range(exp)\n        res *= base\n    return res\na, b = map(int, input().split())\nprint(power(a, b))\n"),
                ("runtime_name", "runtime_error", "def power(base, exp):\n    res = 1\n    for _ in range(exp):\n        result *= base\n    return res\na, b = map(int, input().split())\nprint(power(a, b))\n"),
            ],
        },
        # 20. Second Largest Element
        {
            "id": "fam_20_second_largest",
            "topic": "lists",
            "ref": "def second_largest(nums):\n    uniq = sorted(set(nums))\n    return uniq[-2]\nprint(second_largest([int(x) for x in input().split()]))\n",
            "tests": (("10 20 30 40", "30"), ("-5 -2 -9 -1", "-2"), ("5 5 3 2", "3")),
            "muts": [
                ("index_neg_one", "indexing_error", "def second_largest(nums):\n    uniq = sorted(set(nums))\n    return uniq[-1]\nprint(second_largest([int(x) for x in input().split()]))\n"),
                ("index_len_oob", "indexing_error", "def second_largest(nums):\n    uniq = sorted(set(nums))\n    return uniq[len(uniq)]\nprint(second_largest([int(x) for x in input().split()]))\n"),
                ("init_zero_neg", "initialization_error", "def second_largest(nums):\n    first = 0\n    second = 0\n    for n in nums:\n        if n > first:\n            second = first\n            first = n\n        elif n > second and n != first:\n            second = n\n    return second\nprint(second_largest([int(x) for x in input().split()]))\n"),
                ("no_dedup_logic", "logic_error", "def second_largest(nums):\n    s = sorted(nums)\n    return s[-2]\nprint(second_largest([int(x) for x in input().split()]))\n"),
                ("missing_return", "function_return_error", "def second_largest(nums):\n    uniq = sorted(set(nums))\n    ans = uniq[-2]\nprint(second_largest([int(x) for x in input().split()]))\n"),
                ("syntax_err", "syntax_error", "def second_largest(nums):\n    uniq = sorted(set(nums)\n    return uniq[-2]\nprint(second_largest([int(x) for x in input().split()]))\n"),
                ("runtime_attr", "runtime_error", "def second_largest(nums):\n    return set(nums).sort()[-2]\nprint(second_largest([int(x) for x in input().split()]))\n"),
            ],
        },
        # 21. Count Occurrences of Target
        {
            "id": "fam_21_count_target",
            "topic": "lists",
            "ref": "def count_target(arr, x):\n    c = 0\n    for v in arr:\n        if v == x:\n            c += 1\n    return c\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n",
            "tests": (("3\n3 1 3 5 3", "3"), ("4\n1 2 4", "1"), ("9\n1 2 3", "0")),
            "muts": [
                ("cond_neq", "condition_error", "def count_target(arr, x):\n    c = 0\n    for v in arr:\n        if v != x:\n            c += 1\n    return c\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n"),
                ("init_c_one", "initialization_error", "def count_target(arr, x):\n    c = 1\n    for v in arr:\n        if v == x:\n            c += 1\n    return c\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n"),
                ("skip_last_elem", "loop_boundary_error", "def count_target(arr, x):\n    c = 0\n    for i in range(len(arr) - 1):\n        if arr[i] == x:\n            c += 1\n    return c\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n"),
                ("oob_idx", "indexing_error", "def count_target(arr, x):\n    c = 0\n    for i in range(len(arr) + 1):\n        if arr[i] == x:\n            c += 1\n    return c\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n"),
                ("early_ret", "function_return_error", "def count_target(arr, x):\n    c = 0\n    for v in arr:\n        if v == x:\n            c += 1\n            return c\n    return c\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n"),
                ("adds_value_logic", "logic_error", "def count_target(arr, x):\n    c = 0\n    for v in arr:\n        if v == x:\n            c += v\n    return c\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n"),
                ("syntax_assign", "syntax_error", "def count_target(arr, x):\n    c = 0\n    for v in arr:\n        if v = x:\n            c += 1\n    return c\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n"),
                ("runtime_type", "runtime_error", "def count_target(arr, x):\n    return arr.count()\nt = int(input())\nprint(count_target([int(v) for v in input().split()], t))\n"),
            ],
        },
        # 22. Prefix Sum Last Element / Running Sum
        {
            "id": "fam_22_prefix_sum",
            "topic": "lists",
            "ref": "def prefix_sums(nums):\n    out = []\n    running = 0\n    for n in nums:\n        running += n\n        out.append(running)\n    return out\nprint(' '.join(map(str, prefix_sums([int(x) for x in input().split()]))))\n",
            "tests": (("1 2 3 4", "1 3 6 10"), ("5 -2 7", "5 3 10")),
            "muts": [
                ("reset_running_in_loop", "initialization_error", "def prefix_sums(nums):\n    out = []\n    for n in nums:\n        running = 0\n        running += n\n        out.append(running)\n    return out\nprint(' '.join(map(str, prefix_sums([int(x) for x in input().split()]))))\n"),
                ("skip_last_loop", "loop_boundary_error", "def prefix_sums(nums):\n    out = []\n    running = 0\n    for i in range(len(nums) - 1):\n        running += nums[i]\n        out.append(running)\n    return out\nprint(' '.join(map(str, prefix_sums([int(x) for x in input().split()]))))\n"),
                ("oob_idx", "indexing_error", "def prefix_sums(nums):\n    out = []\n    running = 0\n    for i in range(len(nums) + 1):\n        running += nums[i]\n        out.append(running)\n    return out\nprint(' '.join(map(str, prefix_sums([int(x) for x in input().split()]))))\n"),
                ("early_ret", "function_return_error", "def prefix_sums(nums):\n    out = []\n    running = 0\n    for n in nums:\n        running += n\n        out.append(running)\n        return out\nprint(' '.join(map(str, prefix_sums([int(x) for x in input().split()]))))\n"),
                ("appends_before_add_logic", "logic_error", "def prefix_sums(nums):\n    out = []\n    running = 0\n    for n in nums:\n        out.append(running)\n        running += n\n    return out\nprint(' '.join(map(str, prefix_sums([int(x) for x in input().split()]))))\n"),
                ("syntax_err", "syntax_error", "def prefix_sums(nums):\n    out = []\n    for n in nums\n        out.append(n)\n    return out\nprint(prefix_sums([int(x) for x in input().split()]))\n"),
                ("runtime_err", "runtime_error", "def prefix_sums(nums):\n    out = []\n    for n in nums:\n        out.append(out[-1] + n)\n    return out\nprint(prefix_sums([int(x) for x in input().split()]))\n"),
            ],
        },
        # 23. Count Words Longer Than K
        {
            "id": "fam_23_long_words",
            "topic": "strings",
            "ref": "def long_words(words, k):\n    cnt = 0\n    for w in words:\n        if len(w) > k:\n            cnt += 1\n    return cnt\nk = int(input())\nprint(long_words(input().split(), k))\n",
            "tests": (("3\ncat tree house sun", "2"), ("4\nalpha beta gamma", "2")),
            "muts": [
                ("ge_instead_gt", "condition_error", "def long_words(words, k):\n    cnt = 0\n    for w in words:\n        if len(w) >= k:\n            cnt += 1\n    return cnt\nk = int(input())\nprint(long_words(input().split(), k))\n"),
                ("lt_instead_gt", "condition_error", "def long_words(words, k):\n    cnt = 0\n    for w in words:\n        if len(w) < k:\n            cnt += 1\n    return cnt\nk = int(input())\nprint(long_words(input().split(), k))\n"),
                ("init_cnt_one", "initialization_error", "def long_words(words, k):\n    cnt = 1\n    for w in words:\n        if len(w) > k:\n            cnt += 1\n    return cnt\nk = int(input())\nprint(long_words(input().split(), k))\n"),
                ("skip_first_word", "loop_boundary_error", "def long_words(words, k):\n    cnt = 0\n    for i in range(1, len(words)):\n        if len(words[i]) > k:\n            cnt += 1\n    return cnt\nk = int(input())\nprint(long_words(input().split(), k))\n"),
                ("oob_word", "indexing_error", "def long_words(words, k):\n    cnt = 0\n    for i in range(len(words) + 1):\n        if len(words[i]) > k:\n            cnt += 1\n    return cnt\nk = int(input())\nprint(long_words(input().split(), k))\n"),
                ("no_return", "function_return_error", "def long_words(words, k):\n    cnt = 0\n    for w in words:\n        if len(w) > k:\n            cnt += 1\nk = int(input())\nprint(long_words(input().split(), k))\n"),
                ("adds_len_logic", "logic_error", "def long_words(words, k):\n    cnt = 0\n    for w in words:\n        if len(w) > k:\n            cnt += len(w)\n    return cnt\nk = int(input())\nprint(long_words(input().split(), k))\n"),
                ("runtime_cmp_str", "runtime_error", "def long_words(words, k):\n    return sum(1 for w in words if w > k)\nk = int(input())\nprint(long_words(input().split(), k))\n"),
                ("syntax_err", "syntax_error", "def long_words(words, k):\n    if len(words) > k\n        return 1\n    return 0\nk = int(input())\nprint(long_words(input().split(), k))\n"),
            ],
        },
        # 24. Prime Number Check
        {
            "id": "fam_24_is_prime",
            "topic": "math",
            "ref": "def is_prime(n):\n    if n < 2:\n        return False\n    for d in range(2, int(n ** 0.5) + 1):\n        if n % d == 0:\n            return False\n    return True\nprint(is_prime(int(input())))\n",
            "tests": (("2", "True"), ("9", "False"), ("13", "True"), ("1", "False")),
            "muts": [
                ("range_missing_plus_one", "loop_boundary_error", "def is_prime(n):\n    if n < 2:\n        return False\n    for d in range(2, int(n ** 0.5)):\n        if n % d == 0:\n            return False\n    return True\nprint(is_prime(int(input())))\n"),
                ("early_return_true", "function_return_error", "def is_prime(n):\n    if n < 2:\n        return False\n    for d in range(2, n):\n        if n % d == 0:\n            return False\n        else:\n            return True\n    return True\nprint(is_prime(int(input())))\n"),
                ("allows_one_cond", "condition_error", "def is_prime(n):\n    if n < 1:\n        return False\n    for d in range(2, int(n ** 0.5) + 1):\n        if n % d == 0:\n            return False\n    return True\nprint(is_prime(int(input())))\n"),
                ("range_starts_at_one", "loop_boundary_error", "def is_prime(n):\n    if n < 2:\n        return False\n    for d in range(1, int(n ** 0.5) + 1):\n        if n % d == 0:\n            return False\n    return True\nprint(is_prime(int(input())))\n"),
                ("zero_div_runtime", "runtime_error", "def is_prime(n):\n    for d in range(0, n):\n        if n % d == 0:\n            return False\n    return True\nprint(is_prime(int(input())))\n"),
                ("syntax_err", "syntax_error", "def is_prime(n):\n    if n < 2\n        return False\n    return True\nprint(is_prime(int(input())))\n"),
                ("only_checks_odd_logic", "logic_error", "def is_prime(n):\n    return n % 2 == 1\nprint(is_prime(int(input())))\n"),
            ],
        },
        # 25. Sum of Squares 1..N
        {
            "id": "fam_25_sum_squares",
            "topic": "loops",
            "ref": "def sum_sq(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i * i\n    return total\nprint(sum_sq(int(input())))\n",
            "tests": (("3", "14"), ("5", "55"), ("1", "1")),
            "muts": [
                ("range_stops_before_n", "loop_boundary_error", "def sum_sq(n):\n    total = 0\n    for i in range(1, n):\n        total += i * i\n    return total\nprint(sum_sq(int(input())))\n"),
                ("init_total_one", "initialization_error", "def sum_sq(n):\n    total = 1\n    for i in range(1, n + 1):\n        total += i * i\n    return total\nprint(sum_sq(int(input())))\n"),
                ("mul_by_2_logic", "logic_error", "def sum_sq(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i * 2\n    return total\nprint(sum_sq(int(input())))\n"),
                ("no_return", "function_return_error", "def sum_sq(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i * i\nprint(sum_sq(int(input())))\n"),
                ("early_ret", "function_return_error", "def sum_sq(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i * i\n        return total\nprint(sum_sq(int(input())))\n"),
                ("syntax_err", "syntax_error", "def sum_sq(n):\n    total = 0\n    for i in range(1, n + 1)\n        total += i * i\n    return total\nprint(sum_sq(int(input())))\n"),
                ("runtime_err", "runtime_error", "def sum_sq(n):\n    return sum(i ^ '2' for i in range(1, n + 1))\nprint(sum_sq(int(input())))\n"),
            ],
        },
        # 26. Matrix Row Sums
        {
            "id": "fam_26_row_sums",
            "topic": "lists",
            "ref": "def row_sums(grid):\n    res = []\n    for row in grid:\n        s = 0\n        for val in row:\n            s += val\n        res.append(s)\n    return res\nr = int(input())\ng = [[int(x) for x in input().split()] for _ in range(r)]\nprint(' '.join(map(str, row_sums(g))))\n",
            "tests": (("2\n1 2 3\n4 5 6", "6 15"), ("2\n10 -2\n3 7", "8 10")),
            "muts": [
                ("s_not_reset_init", "initialization_error", "def row_sums(grid):\n    res = []\n    s = 0\n    for row in grid:\n        for val in row:\n            s += val\n        res.append(s)\n    return res\nr = int(input())\ng = [[int(x) for x in input().split()] for _ in range(r)]\nprint(' '.join(map(str, row_sums(g))))\n"),
                ("oob_col_idx", "indexing_error", "def row_sums(grid):\n    res = []\n    for row in grid:\n        s = 0\n        for j in range(len(row) + 1):\n            s += row[j]\n        res.append(s)\n    return res\nr = int(input())\ng = [[int(x) for x in input().split()] for _ in range(r)]\nprint(' '.join(map(str, row_sums(g))))\n"),
                ("skip_last_row", "loop_boundary_error", "def row_sums(grid):\n    res = []\n    for i in range(len(grid) - 1):\n        res.append(sum(grid[i]))\n    return res\nr = int(input())\ng = [[int(x) for x in input().split()] for _ in range(r)]\nprint(' '.join(map(str, row_sums(g))))\n"),
                ("early_ret", "function_return_error", "def row_sums(grid):\n    res = []\n    for row in grid:\n        res.append(sum(row))\n        return res\nr = int(input())\ng = [[int(x) for x in input().split()] for _ in range(r)]\nprint(' '.join(map(str, row_sums(g))))\n"),
                ("counts_len_logic", "logic_error", "def row_sums(grid):\n    return [len(row) for row in grid]\nr = int(input())\ng = [[int(x) for x in input().split()] for _ in range(r)]\nprint(' '.join(map(str, row_sums(g))))\n"),
                ("syntax_err", "syntax_error", "def row_sums(grid):\n    res = []\n    for row in grid\n        res.append(sum(row))\n    return res\nprint(row_sums([]))\n"),
                ("runtime_err", "runtime_error", "def row_sums(grid):\n    return [row.sum() for row in grid]\nr = int(input())\ng = [[int(x) for x in input().split()] for _ in range(r)]\nprint(' '.join(map(str, row_sums(g))))\n"),
            ],
        },
        # 27. Dictionary Character Frequency
        {
            "id": "fam_27_char_freq",
            "topic": "dictionaries",
            "ref": "def top_char_count(s, target):\n    freq = {}\n    for ch in s:\n        freq[ch] = freq.get(ch, 0) + 1\n    return freq.get(target, 0)\nt = input().strip()\ns = input().strip()\nprint(top_char_count(s, t))\n",
            "tests": (("a\nbanana", "3"), ("z\nbanana", "0"), ("n\nbanana", "2")),
            "muts": [
                ("key_error_runtime", "runtime_error", "def top_char_count(s, target):\n    freq = {}\n    for ch in s:\n        freq[ch] = freq[ch] + 1\n    return freq[target]\nt = input().strip()\ns = input().strip()\nprint(top_char_count(s, t))\n"),
                ("overwrites_to_1_logic", "logic_error", "def top_char_count(s, target):\n    freq = {}\n    for ch in s:\n        freq[ch] = 1\n    return freq.get(target, 0)\nt = input().strip()\ns = input().strip()\nprint(top_char_count(s, t))\n"),
                ("skip_last_char", "loop_boundary_error", "def top_char_count(s, target):\n    freq = {}\n    for i in range(len(s) - 1):\n        ch = s[i]\n        freq[ch] = freq.get(ch, 0) + 1\n    return freq.get(target, 0)\nt = input().strip()\ns = input().strip()\nprint(top_char_count(s, t))\n"),
                ("oob_idx", "indexing_error", "def top_char_count(s, target):\n    freq = {}\n    for i in range(len(s) + 1):\n        ch = s[i]\n        freq[ch] = freq.get(ch, 0) + 1\n    return freq.get(target, 0)\nt = input().strip()\ns = input().strip()\nprint(top_char_count(s, t))\n"),
                ("missing_return", "function_return_error", "def top_char_count(s, target):\n    freq = {}\n    for ch in s:\n        freq[ch] = freq.get(ch, 0) + 1\nt = input().strip()\ns = input().strip()\nprint(top_char_count(s, t))\n"),
                ("syntax_err", "syntax_error", "def top_char_count(s, target):\n    freq = {\n    return 0\nt = input().strip()\ns = input().strip()\nprint(top_char_count(s, t))\n"),
            ],
        },
        # 28. Binary Search in Sorted List
        {
            "id": "fam_28_binary_search",
            "topic": "searching",
            "ref": "def bsearch(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\nt = int(input())\nprint(bsearch([int(x) for x in input().split()], t))\n",
            "tests": (("9\n1 3 5 7 9", "4"), ("1\n1 3 5 7 9", "0"), ("4\n1 3 5 7 9", "-1"), ("20\n1 3 5 7 9", "-1")),
            "muts": [
                ("while_lt_misses_end", "loop_boundary_error", "def bsearch(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\nt = int(input())\nprint(bsearch([int(x) for x in input().split()], t))\n"),
                ("hi_len_oob", "indexing_error", "def bsearch(arr, target):\n    lo, hi = 0, len(arr)\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\nt = int(input())\nprint(bsearch([int(x) for x in input().split()], t))\n"),
                ("inverted_branch_cond", "condition_error", "def bsearch(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] > target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\nt = int(input())\nprint(bsearch([int(x) for x in input().split()], t))\n"),
                ("float_div_runtime", "runtime_error", "def bsearch(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) / 2\n        if arr[mid] == target:\n            return mid\n        lo += 1\n    return -1\nt = int(input())\nprint(bsearch([int(x) for x in input().split()], t))\n"),
                ("returns_val_logic", "logic_error", "def bsearch(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return arr[mid]\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\nt = int(input())\nprint(bsearch([int(x) for x in input().split()], t))\n"),
                ("syntax_err", "syntax_error", "def bsearch(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi\n        return -1\nt = int(input())\nprint(bsearch([int(x) for x in input().split()], t))\n"),
            ],
        },
        # 29. Sum Multiples of 3 or 5 Below N
        {
            "id": "fam_29_multiples_3_5",
            "topic": "conditionals",
            "ref": "def sum_mult(n):\n    total = 0\n    for i in range(1, n):\n        if i % 3 == 0 or i % 5 == 0:\n            total += i\n    return total\nprint(sum_mult(int(input())))\n",
            "tests": (("10", "23"), ("16", "60")),
            "muts": [
                ("and_instead_or", "condition_error", "def sum_mult(n):\n    total = 0\n    for i in range(1, n):\n        if i % 3 == 0 and i % 5 == 0:\n            total += i\n    return total\nprint(sum_mult(int(input())))\n"),
                ("includes_n_bound", "loop_boundary_error", "def sum_mult(n):\n    total = 0\n    for i in range(1, n + 1):\n        if i % 3 == 0 or i % 5 == 0:\n            total += i\n    return total\nprint(sum_mult(int(input())))\n"),
                ("init_total_one", "initialization_error", "def sum_mult(n):\n    total = 1\n    for i in range(1, n):\n        if i % 3 == 0 or i % 5 == 0:\n            total += i\n    return total\nprint(sum_mult(int(input())))\n"),
                ("double_counts_15_logic", "logic_error", "def sum_mult(n):\n    total = 0\n    for i in range(1, n):\n        if i % 3 == 0:\n            total += i\n        if i % 5 == 0:\n            total += i\n    return total\nprint(sum_mult(int(input())))\n"),
                ("missing_return", "function_return_error", "def sum_mult(n):\n    total = 0\n    for i in range(1, n):\n        if i % 3 == 0 or i % 5 == 0:\n            total += i\nprint(sum_mult(int(input())))\n"),
                ("syntax_err", "syntax_error", "def sum_mult(n):\n    if n % 3 == 0 || n % 5 == 0:\n        return n\nprint(sum_mult(int(input())))\n"),
                ("runtime_err", "runtime_error", "def sum_mult(n):\n    return sum(i for i in range(1, n) if i % 0 == 0)\nprint(sum_mult(int(input())))\n"),
            ],
        },
        # 30. Absolute Difference of First & Last Element
        {
            "id": "fam_30_first_last_diff",
            "topic": "indexing",
            "ref": "def end_diff(nums):\n    return abs(nums[0] - nums[-1])\nprint(end_diff([int(x) for x in input().split()]))\n",
            "tests": (("10 4 2 3", "7"), ("2 8 9", "7"), ("-5 0 5", "10")),
            "muts": [
                ("oob_len_index", "indexing_error", "def end_diff(nums):\n    return abs(nums[0] - nums[len(nums)])\nprint(end_diff([int(x) for x in input().split()]))\n"),
                ("uses_index_one", "indexing_error", "def end_diff(nums):\n    return abs(nums[1] - nums[-1])\nprint(end_diff([int(x) for x in input().split()]))\n"),
                ("missing_abs_logic", "logic_error", "def end_diff(nums):\n    return nums[0] - nums[-1]\nprint(end_diff([int(x) for x in input().split()]))\n"),
                ("adds_instead_sub_logic", "logic_error", "def end_diff(nums):\n    return abs(nums[0] + nums[-1])\nprint(end_diff([int(x) for x in input().split()]))\n"),
                ("no_return", "function_return_error", "def end_diff(nums):\n    d = abs(nums[0] - nums[-1])\nprint(end_diff([int(x) for x in input().split()]))\n"),
                ("syntax_err", "syntax_error", "def end_diff(nums):\n    return abs(nums[0] - nums[-1]\nprint(end_diff([int(x) for x in input().split()]))\n"),
                ("runtime_err", "runtime_error", "def end_diff(nums):\n    return math.abs(nums[0] - nums[-1])\nprint(end_diff([int(x) for x in input().split()]))\n"),
            ],
        },
        # 31. Step Range Sum (Every k-th element inclusive)
        {
            "id": "fam_31_step_range_sum",
            "topic": "loops",
            "ref": "def step_sum(start, end, step):\n    total = 0\n    for x in range(start, end + 1, step):\n        total += x\n    return total\na, b, k = map(int, input().split())\nprint(step_sum(a, b, k))\n",
            "tests": (("2 10 2", "30"), ("1 7 3", "12"), ("0 6 2", "12")),
            "muts": [
                ("excludes_end_bound", "loop_boundary_error", "def step_sum(start, end, step):\n    total = 0\n    for x in range(start, end, step):\n        total += x\n    return total\na, b, k = map(int, input().split())\nprint(step_sum(a, b, k))\n"),
                ("init_total_one", "initialization_error", "def step_sum(start, end, step):\n    total = 1\n    for x in range(start, end + 1, step):\n        total += x\n    return total\na, b, k = map(int, input().split())\nprint(step_sum(a, b, k))\n"),
                ("ignores_step_logic", "logic_error", "def step_sum(start, end, step):\n    total = 0\n    for x in range(start, end + 1):\n        total += x\n    return total\na, b, k = map(int, input().split())\nprint(step_sum(a, b, k))\n"),
                ("early_ret", "function_return_error", "def step_sum(start, end, step):\n    total = 0\n    for x in range(start, end + 1, step):\n        total += x\n        return total\na, b, k = map(int, input().split())\nprint(step_sum(a, b, k))\n"),
                ("syntax_err", "syntax_error", "def step_sum(start, end, step):\n    for x in range(start, end + 1, step)\n        pass\na, b, k = map(int, input().split())\nprint(step_sum(a, b, k))\n"),
                ("runtime_step_zero", "runtime_error", "def step_sum(start, end, step):\n    return sum(range(start, end + 1, 0))\na, b, k = map(int, input().split())\nprint(step_sum(a, b, k))\n"),
            ],
        },
        # 32. Count Even-Indexed Elements Above Threshold
        {
            "id": "fam_32_even_idx_above",
            "topic": "indexing",
            "ref": "def count_even_idx(arr, thresh):\n    c = 0\n    for i in range(0, len(arr), 2):\n        if arr[i] > thresh:\n            c += 1\n    return c\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n",
            "tests": (("5\n6 9 4 8 7", "2"), ("10\n12 20 15", "2")),
            "muts": [
                ("starts_at_odd_idx", "indexing_error", "def count_even_idx(arr, thresh):\n    c = 0\n    for i in range(1, len(arr), 2):\n        if arr[i] > thresh:\n            c += 1\n    return c\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n"),
                ("oob_idx", "indexing_error", "def count_even_idx(arr, thresh):\n    c = 0\n    for i in range(0, len(arr) + 2, 2):\n        if arr[i] > thresh:\n            c += 1\n    return c\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n"),
                ("lt_thresh_cond", "condition_error", "def count_even_idx(arr, thresh):\n    c = 0\n    for i in range(0, len(arr), 2):\n        if arr[i] < thresh:\n            c += 1\n    return c\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n"),
                ("range_misses_last_bound", "loop_boundary_error", "def count_even_idx(arr, thresh):\n    c = 0\n    for i in range(0, len(arr) - 1, 2):\n        if arr[i] > thresh:\n            c += 1\n    return c\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n"),
                ("init_c_one", "initialization_error", "def count_even_idx(arr, thresh):\n    c = 1\n    for i in range(0, len(arr), 2):\n        if arr[i] > thresh:\n            c += 1\n    return c\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n"),
                ("no_return", "function_return_error", "def count_even_idx(arr, thresh):\n    c = 0\n    for i in range(0, len(arr), 2):\n        if arr[i] > thresh:\n            c += 1\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n"),
                ("syntax_err", "syntax_error", "def count_even_idx(arr, thresh):\n    for i in range(0, len(arr), 2)\n        pass\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n"),
                ("runtime_err", "runtime_error", "def count_even_idx(arr, thresh):\n    return arr['0'] > thresh\nt = int(input())\nprint(count_even_idx([int(x) for x in input().split()], t))\n"),
            ],
        },
    ]

    for spec in extra_specs:
        families.append(
            ProgramFamily(
                family_id=spec["id"],
                topic=spec["topic"],
                reference_code=spec["ref"],
                tests=tuple(spec["tests"]),
                mutations=tuple(spec["muts"]),
            )
        )

    # Add 8 more compact original families (fam_33..fam_40) to ensure 300+ validated samples across all 8 classes!
    more_specs: list[dict[str, Any]] = [
        {
            "id": "fam_33_dot_product",
            "topic": "lists",
            "ref": "def dot(a, b):\n    total = 0\n    for i in range(len(a)):\n        total += a[i] * b[i]\n    return total\na = [int(x) for x in input().split()]\nb = [int(x) for x in input().split()]\nprint(dot(a, b))\n",
            "tests": (("1 2 3\n4 5 6", "32"), ("2 -1 3\n1 5 2", "3")),
            "muts": [
                ("init_total_one", "initialization_error", "def dot(a, b):\n    total = 1\n    for i in range(len(a)):\n        total += a[i] * b[i]\n    return total\na = [int(x) for x in input().split()]\nb = [int(x) for x in input().split()]\nprint(dot(a, b))\n"),
                ("skip_last_pair", "loop_boundary_error", "def dot(a, b):\n    total = 0\n    for i in range(len(a) - 1):\n        total += a[i] * b[i]\n    return total\na = [int(x) for x in input().split()]\nb = [int(x) for x in input().split()]\nprint(dot(a, b))\n"),
                ("oob_idx", "indexing_error", "def dot(a, b):\n    total = 0\n    for i in range(len(a) + 1):\n        total += a[i] * b[i]\n    return total\na = [int(x) for x in input().split()]\nb = [int(x) for x in input().split()]\nprint(dot(a, b))\n"),
                ("adds_instead_mul", "logic_error", "def dot(a, b):\n    total = 0\n    for i in range(len(a)):\n        total += a[i] + b[i]\n    return total\na = [int(x) for x in input().split()]\nb = [int(x) for x in input().split()]\nprint(dot(a, b))\n"),
                ("early_ret", "function_return_error", "def dot(a, b):\n    total = 0\n    for i in range(len(a)):\n        total += a[i] * b[i]\n        return total\na = [int(x) for x in input().split()]\nb = [int(x) for x in input().split()]\nprint(dot(a, b))\n"),
                ("syntax_err", "syntax_error", "def dot(a, b):\n    return sum(a[i] * b[i] for i in range(len(a))\na = [int(x) for x in input().split()]\nb = [int(x) for x in input().split()]\nprint(dot(a, b))\n"),
                ("runtime_err", "runtime_error", "def dot(a, b):\n    return a * b\na = [int(x) for x in input().split()]\nb = [int(x) for x in input().split()]\nprint(dot(a, b))\n"),
            ],
        },
        {
            "id": "fam_34_count_upper",
            "topic": "strings",
            "ref": "def count_upper(s):\n    c = 0\n    for ch in s:\n        if 'A' <= ch <= 'Z':\n            c += 1\n    return c\nprint(count_upper(input().strip()))\n",
            "tests": (("HelloWorld", "2"), ("ABCdef", "3"), ("python", "0")),
            "muts": [
                ("strict_lt_Z_cond", "condition_error", "def count_upper(s):\n    c = 0\n    for ch in s:\n        if 'a' <= ch <= 'z':\n            c += 1\n    return c\nprint(count_upper(input().strip()))\n"),
                ("init_c_one", "initialization_error", "def count_upper(s):\n    c = 1\n    for ch in s:\n        if 'A' <= ch <= 'Z':\n            c += 1\n    return c\nprint(count_upper(input().strip()))\n"),
                ("skip_first_char", "loop_boundary_error", "def count_upper(s):\n    c = 0\n    for i in range(1, len(s)):\n        if 'A' <= s[i] <= 'Z':\n            c += 1\n    return c\nprint(count_upper(input().strip()))\n"),
                ("oob_char", "indexing_error", "def count_upper(s):\n    c = 0\n    for i in range(len(s) + 1):\n        if 'A' <= s[i] <= 'Z':\n            c += 1\n    return c\nprint(count_upper(input().strip()))\n"),
                ("missing_return", "function_return_error", "def count_upper(s):\n    c = 0\n    for ch in s:\n        if 'A' <= ch <= 'Z':\n            c += 1\nprint(count_upper(input().strip()))\n"),
                ("syntax_err", "syntax_error", "def count_upper(s):\n    if 'A' <= s <= 'Z'\n        return 1\nprint(count_upper(input().strip()))\n"),
                ("runtime_err", "runtime_error", "def count_upper(s):\n    return s.isUpper()\nprint(count_upper(input().strip()))\n"),
            ],
        },
        {
            "id": "fam_35_clamp_value",
            "topic": "conditionals",
            "ref": "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    if x > hi:\n        return hi\n    return x\nx, lo, hi = map(int, input().split())\nprint(clamp(x, lo, hi))\n",
            "tests": (("5 0 10", "5"), ("-4 0 10", "0"), ("15 0 10", "10")),
            "muts": [
                ("inverted_lo_cond", "condition_error", "def clamp(x, lo, hi):\n    if x > lo:\n        return lo\n    if x > hi:\n        return hi\n    return x\nx, lo, hi = map(int, input().split())\nprint(clamp(x, lo, hi))\n"),
                ("inverted_hi_cond", "condition_error", "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    if x < hi:\n        return hi\n    return x\nx, lo, hi = map(int, input().split())\nprint(clamp(x, lo, hi))\n"),
                ("missing_return_x", "function_return_error", "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    if x > hi:\n        return hi\nx, lo, hi = map(int, input().split())\nprint(clamp(x, lo, hi))\n"),
                ("swapped_lo_hi_logic", "logic_error", "def clamp(x, lo, hi):\n    if x < lo:\n        return hi\n    if x > hi:\n        return lo\n    return x\nx, lo, hi = map(int, input().split())\nprint(clamp(x, lo, hi))\n"),
                ("syntax_err", "syntax_error", "def clamp(x, lo, hi):\n    if x < lo\n        return lo\n    return x\nx, lo, hi = map(int, input().split())\nprint(clamp(x, lo, hi))\n"),
                ("runtime_err", "runtime_error", "def clamp(x, lo, hi):\n    return max(lo, min(hi, unknown_x))\nx, lo, hi = map(int, input().split())\nprint(clamp(x, lo, hi))\n"),
            ],
        },
        {
            "id": "fam_36_all_even",
            "topic": "conditionals",
            "ref": "def all_even(nums):\n    for n in nums:\n        if n % 2 != 0:\n            return False\n    return True\nprint(all_even([int(x) for x in input().split()]))\n",
            "tests": (("2 4 6 8", "True"), ("2 4 5 8", "False"), ("2 4 6 9", "False")),
            "muts": [
                ("early_return_true", "function_return_error", "def all_even(nums):\n    for n in nums:\n        if n % 2 == 0:\n            return True\n    return False\nprint(all_even([int(x) for x in input().split()]))\n"),
                ("missing_return_true", "function_return_error", "def all_even(nums):\n    for n in nums:\n        if n % 2 != 0:\n            return False\nprint(all_even([int(x) for x in input().split()]))\n"),
                ("inverted_cond", "condition_error", "def all_even(nums):\n    for n in nums:\n        if n % 2 == 0:\n            return False\n    return True\nprint(all_even([int(x) for x in input().split()]))\n"),
                ("skip_last_bound", "loop_boundary_error", "def all_even(nums):\n    for i in range(len(nums) - 1):\n        if nums[i] % 2 != 0:\n            return False\n    return True\nprint(all_even([int(x) for x in input().split()]))\n"),
                ("oob_idx", "indexing_error", "def all_even(nums):\n    for i in range(len(nums) + 1):\n        if nums[i] % 2 != 0:\n            return False\n    return True\nprint(all_even([int(x) for x in input().split()]))\n"),
                ("syntax_err", "syntax_error", "def all_even(nums):\n    for n in nums:\n        if n % 2 != 0\n            return False\n    return True\nprint(all_even([int(x) for x in input().split()]))\n"),
                ("runtime_err", "runtime_error", "def all_even(nums):\n    return nums % 2 == 0\nprint(all_even([int(x) for x in input().split()]))\n"),
            ],
        },
        {
            "id": "fam_37_running_max",
            "topic": "lists",
            "ref": "def running_max(nums):\n    out = []\n    best = nums[0]\n    for n in nums:\n        if n > best:\n            best = n\n        out.append(best)\n    return out\nprint(' '.join(map(str, running_max([int(x) for x in input().split()]))))\n",
            "tests": (("3 1 5 2 6", "3 3 5 5 6"), ("-5 -2 -9 -1", "-5 -2 -2 -1")),
            "muts": [
                ("init_best_zero", "initialization_error", "def running_max(nums):\n    out = []\n    best = 0\n    for n in nums:\n        if n > best:\n            best = n\n        out.append(best)\n    return out\nprint(' '.join(map(str, running_max([int(x) for x in input().split()]))))\n"),
                ("inverted_cmp", "condition_error", "def running_max(nums):\n    out = []\n    best = nums[0]\n    for n in nums:\n        if n < best:\n            best = n\n        out.append(best)\n    return out\nprint(' '.join(map(str, running_max([int(x) for x in input().split()]))))\n"),
                ("skip_last_bound", "loop_boundary_error", "def running_max(nums):\n    out = []\n    best = nums[0]\n    for i in range(len(nums) - 1):\n        if nums[i] > best:\n            best = nums[i]\n        out.append(best)\n    return out\nprint(' '.join(map(str, running_max([int(x) for x in input().split()]))))\n"),
                ("oob_idx", "indexing_error", "def running_max(nums):\n    out = []\n    best = nums[0]\n    for i in range(len(nums) + 1):\n        if nums[i] > best:\n            best = nums[i]\n        out.append(best)\n    return out\nprint(' '.join(map(str, running_max([int(x) for x in input().split()]))))\n"),
                ("early_ret", "function_return_error", "def running_max(nums):\n    out = []\n    best = nums[0]\n    for n in nums:\n        if n > best:\n            best = n\n        out.append(best)\n        return out\nprint(' '.join(map(str, running_max([int(x) for x in input().split()]))))\n"),
                ("appends_n_logic", "logic_error", "def running_max(nums):\n    out = []\n    best = nums[0]\n    for n in nums:\n        if n > best:\n            best = n\n        out.append(n)\n    return out\nprint(' '.join(map(str, running_max([int(x) for x in input().split()]))))\n"),
                ("syntax_err", "syntax_error", "def running_max(nums):\n    best = nums[0\n    return [best]\nprint(running_max([1]))\n"),
                ("runtime_err", "runtime_error", "def running_max(nums):\n    return max(nums[0], '1')\nprint(running_max([int(x) for x in input().split()]))\n"),
            ],
        },
        {
            "id": "fam_38_sum_odd_indices",
            "topic": "indexing",
            "ref": "def sum_odd_idx(arr):\n    total = 0\n    for i in range(1, len(arr), 2):\n        total += arr[i]\n    return total\nprint(sum_odd_idx([int(x) for x in input().split()]))\n",
            "tests": (("10 20 30 40 50", "60"), ("5 7 9 3", "10")),
            "muts": [
                ("starts_at_0_idx", "indexing_error", "def sum_odd_idx(arr):\n    total = 0\n    for i in range(0, len(arr), 2):\n        total += arr[i]\n    return total\nprint(sum_odd_idx([int(x) for x in input().split()]))\n"),
                ("oob_idx", "indexing_error", "def sum_odd_idx(arr):\n    total = 0\n    for i in range(1, len(arr) + 2, 2):\n        total += arr[i]\n    return total\nprint(sum_odd_idx([int(x) for x in input().split()]))\n"),
                ("misses_last_odd_bound", "loop_boundary_error", "def sum_odd_idx(arr):\n    total = 0\n    for i in range(1, len(arr) - 1, 2):\n        total += arr[i]\n    return total\nprint(sum_odd_idx([int(x) for x in input().split()]))\n"),
                ("init_total_one", "initialization_error", "def sum_odd_idx(arr):\n    total = 1\n    for i in range(1, len(arr), 2):\n        total += arr[i]\n    return total\nprint(sum_odd_idx([int(x) for x in input().split()]))\n"),
                ("adds_index_logic", "logic_error", "def sum_odd_idx(arr):\n    total = 0\n    for i in range(1, len(arr), 2):\n        total += i\n    return total\nprint(sum_odd_idx([int(x) for x in input().split()]))\n"),
                ("missing_return", "function_return_error", "def sum_odd_idx(arr):\n    total = 0\n    for i in range(1, len(arr), 2):\n        total += arr[i]\nprint(sum_odd_idx([int(x) for x in input().split()]))\n"),
                ("syntax_err", "syntax_error", "def sum_odd_idx(arr):\n    for i in range(1, len(arr), 2)\n        pass\nprint(sum_odd_idx([1, 2]))\n"),
                ("runtime_err", "runtime_error", "def sum_odd_idx(arr):\n    return arr[1] + '0'\nprint(sum_odd_idx([int(x) for x in input().split()]))\n"),
            ],
        },
        {
            "id": "fam_39_gcd_euclid",
            "topic": "math",
            "ref": "def gcd(a, b):\n    while b != 0:\n        a, b = b, a % b\n    return a\na, b = map(int, input().split())\nprint(gcd(a, b))\n",
            "tests": (("48 18", "6"), ("21 14", "7"), ("17 5", "1")),
            "muts": [
                ("returns_b_instead_a", "function_return_error", "def gcd(a, b):\n    while b != 0:\n        a, b = b, a % b\n    return b\na, b = map(int, input().split())\nprint(gcd(a, b))\n"),
                ("missing_return", "function_return_error", "def gcd(a, b):\n    while b != 0:\n        a, b = b, a % b\na, b = map(int, input().split())\nprint(gcd(a, b))\n"),
                ("non_simultaneous_logic", "logic_error", "def gcd(a, b):\n    while b != 0:\n        a = b\n        b = a % b\n    return a\na, b = map(int, input().split())\nprint(gcd(a, b))\n"),
                ("while_b_gt_1_bound", "loop_boundary_error", "def gcd(a, b):\n    while b > 1:\n        a, b = b, a % b\n    return a\na, b = map(int, input().split())\nprint(gcd(a, b))\n"),
                ("zero_div_runtime", "runtime_error", "def gcd(a, b):\n    while b != 0:\n        a, b = b, a % b\n    return a // b\na, b = map(int, input().split())\nprint(gcd(a, b))\n"),
                ("syntax_err", "syntax_error", "def gcd(a, b):\n    while b != 0\n        a, b = b, a % b\n    return a\na, b = map(int, input().split())\nprint(gcd(a, b))\n"),
            ],
        },
        {
            "id": "fam_40_triangle_valid",
            "topic": "conditionals",
            "ref": "def valid_tri(a, b, c):\n    return a + b > c and a + c > b and b + c > a\na, b, c = map(int, input().split())\nprint(valid_tri(a, b, c))\n",
            "tests": (("3 4 5", "True"), ("1 2 3", "False"), ("5 1 2", "False")),
            "muts": [
                ("ge_instead_gt_cond", "condition_error", "def valid_tri(a, b, c):\n    return a + b >= c and a + c >= b and b + c >= a\na, b, c = map(int, input().split())\nprint(valid_tri(a, b, c))\n"),
                ("or_instead_and_cond", "condition_error", "def valid_tri(a, b, c):\n    return a + b > c or a + c > b or b + c > a\na, b, c = map(int, input().split())\nprint(valid_tri(a, b, c))\n"),
                ("only_one_ineq_cond", "condition_error", "def valid_tri(a, b, c):\n    return a + b > c\na, b, c = map(int, input().split())\nprint(valid_tri(a, b, c))\n"),
                ("missing_return", "function_return_error", "def valid_tri(a, b, c):\n    ok = a + b > c and a + c > b and b + c > a\na, b, c = map(int, input().split())\nprint(valid_tri(a, b, c))\n"),
                ("sub_instead_add_logic", "logic_error", "def valid_tri(a, b, c):\n    return a - b > c and a - c > b and b - c > a\na, b, c = map(int, input().split())\nprint(valid_tri(a, b, c))\n"),
                ("syntax_err", "syntax_error", "def valid_tri(a, b, c):\n    return a + b > c && b + c > a\na, b, c = map(int, input().split())\nprint(valid_tri(a, b, c))\n"),
                ("runtime_err", "runtime_error", "def valid_tri(a, b, c):\n    return a + b > d\na, b, c = map(int, input().split())\nprint(valid_tri(a, b, c))\n"),
            ],
        },
        {
            "id": "fam_41_count_below_avg",
            "topic": "lists",
            "ref": "def below_avg(nums):\n    avg = sum(nums) / len(nums)\n    c = 0\n    for x in nums:\n        if x < avg:\n            c += 1\n    return c\nprint(below_avg([int(v) for v in input().split()]))\n",
            "tests": (("2 4 6 8", "2"), ("10 10 10", "0"), ("1 9 2 8", "2")),
            "muts": [
                ("le_instead_lt_cond", "condition_error", "def below_avg(nums):\n    avg = sum(nums) / len(nums)\n    c = 0\n    for x in nums:\n        if x <= avg:\n            c += 1\n    return c\nprint(below_avg([int(v) for v in input().split()]))\n"),
                ("init_c_one", "initialization_error", "def below_avg(nums):\n    avg = sum(nums) / len(nums)\n    c = 1\n    for x in nums:\n        if x < avg:\n            c += 1\n    return c\nprint(below_avg([int(v) for v in input().split()]))\n"),
                ("skip_last_bound", "loop_boundary_error", "def below_avg(nums):\n    avg = sum(nums) / len(nums)\n    c = 0\n    for i in range(len(nums) - 1):\n        if nums[i] < avg:\n            c += 1\n    return c\nprint(below_avg([int(v) for v in input().split()]))\n"),
                ("oob_idx", "indexing_error", "def below_avg(nums):\n    avg = sum(nums) / len(nums)\n    c = 0\n    for i in range(len(nums) + 1):\n        if nums[i] < avg:\n            c += 1\n    return c\nprint(below_avg([int(v) for v in input().split()]))\n"),
                ("no_return", "function_return_error", "def below_avg(nums):\n    avg = sum(nums) / len(nums)\n    c = 0\n    for x in nums:\n        if x < avg:\n            c += 1\nprint(below_avg([int(v) for v in input().split()]))\n"),
                ("sums_val_logic", "logic_error", "def below_avg(nums):\n    avg = sum(nums) / len(nums)\n    c = 0\n    for x in nums:\n        if x < avg:\n            c += x\n    return c\nprint(below_avg([int(v) for v in input().split()]))\n"),
                ("syntax_err", "syntax_error", "def below_avg(nums):\n    if len(nums) > 0\n        return 0\nprint(below_avg([1]))\n"),
                ("runtime_err", "runtime_error", "def below_avg(nums):\n    return sum(nums) / 0\nprint(below_avg([int(v) for v in input().split()]))\n"),
            ],
        },
        {
            "id": "fam_42_merge_alternating",
            "topic": "indexing",
            "ref": "def sum_weighted(nums):\n    total = 0\n    for i in range(len(nums)):\n        total += (i + 1) * nums[i]\n    return total\nprint(sum_weighted([int(v) for v in input().split()]))\n",
            "tests": (("2 3 4", "20"), ("5 1 2 3", "25"), ("1 1 1", "6")),
            "muts": [
                ("zero_weight_logic", "logic_error", "def sum_weighted(nums):\n    total = 0\n    for i in range(len(nums)):\n        total += i * nums[i]\n    return total\nprint(sum_weighted([int(v) for v in input().split()]))\n"),
                ("init_total_one", "initialization_error", "def sum_weighted(nums):\n    total = 1\n    for i in range(len(nums)):\n        total += (i + 1) * nums[i]\n    return total\nprint(sum_weighted([int(v) for v in input().split()]))\n"),
                ("skip_last_bound", "loop_boundary_error", "def sum_weighted(nums):\n    total = 0\n    for i in range(len(nums) - 1):\n        total += (i + 1) * nums[i]\n    return total\nprint(sum_weighted([int(v) for v in input().split()]))\n"),
                ("oob_idx", "indexing_error", "def sum_weighted(nums):\n    total = 0\n    for i in range(1, len(nums) + 1):\n        total += i * nums[i]\n    return total\nprint(sum_weighted([int(v) for v in input().split()]))\n"),
                ("early_ret", "function_return_error", "def sum_weighted(nums):\n    total = 0\n    for i in range(len(nums)):\n        total += (i + 1) * nums[i]\n        return total\nprint(sum_weighted([int(v) for v in input().split()]))\n"),
                ("syntax_err", "syntax_error", "def sum_weighted(nums):\n    for i in range(len(nums))\n        pass\nprint(sum_weighted([1]))\n"),
                ("runtime_err", "runtime_error", "def sum_weighted(nums):\n    return sum(i * 'x' + 1 for i in range(len(nums)))\nprint(sum_weighted([int(v) for v in input().split()]))\n"),
            ],
        },
    ]

    for spec in more_specs:
        families.append(
            ProgramFamily(
                family_id=spec["id"],
                topic=spec["topic"],
                reference_code=spec["ref"],
                tests=tuple(spec["tests"]),
                mutations=tuple(spec["muts"]),
            )
        )

    return families


def _run_python_code(source_code: str, stdin_data: str) -> tuple[str, str, str]:
    """Run controlled dataset sample in an isolated subprocess with strict 2s timeout."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(source_code)
        tmp_path = Path(tmp.name)

    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(tmp_path)],
            input=stdin_data,
            text=True,
            capture_output=True,
            timeout=2.0,
            check=False,
        )
        if proc.returncode == 0:
            return "ok", proc.stdout.strip(), proc.stderr.strip()
        stderr = proc.stderr.strip()
        if "SyntaxError:" in stderr or "IndentationError:" in stderr:
            return "compilation_error", proc.stdout.strip(), stderr
        return "runtime_error", proc.stdout.strip(), stderr
    except subprocess.TimeoutExpired:
        return "time_limit_exceeded", "", "TimeoutExpired"
    finally:
        tmp_path.unlink(missing_ok=True)


def generate_validated_dataset(output_dir: Path) -> dict[str, Any]:
    """Validate every reference & mutation by actual execution and persist versioned CSV + metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)
    families = _build_families()
    rows: list[dict[str, Any]] = []
    dropped: list[dict[str, str]] = []

    for fam in families:
        # 1. Verify reference solution passes 100% of its tests
        for stdin_data, expected in fam.tests:
            status_code, stdout, stderr = _run_python_code(fam.reference_code, stdin_data)
            if status_code != "ok" or stdout != expected.strip():
                raise RuntimeError(
                    f"Reference solution failed for {fam.family_id}: "
                    f"status={status_code}, expected={expected!r}, actual={stdout!r}, stderr={stderr!r}"
                )

        # 2. Execute each buggy mutation and capture actual failing execution evidence
        for mut_name, label, buggy_code in fam.mutations:
            if label not in ERROR_TAXONOMY:
                raise ValueError(f"Unknown label {label!r} in {fam.family_id}")

            passed = 0
            first_verdict = "accepted"
            first_stderr = ""
            first_compile = ""
            first_actual = ""
            first_expected = ""

            for stdin_data, expected in fam.tests:
                status_code, stdout, stderr = _run_python_code(buggy_code, stdin_data)
                if status_code == "ok" and stdout == expected.strip():
                    passed += 1
                    continue

                if first_verdict == "accepted":
                    if status_code == "compilation_error":
                        first_verdict = "compilation_error"
                        first_compile = stderr
                    elif status_code == "runtime_error":
                        first_verdict = "runtime_error"
                        first_stderr = stderr
                    elif status_code == "time_limit_exceeded":
                        first_verdict = "time_limit_exceeded"
                        first_stderr = stderr
                    else:
                        first_verdict = "wrong_answer"
                        first_actual = stdout
                        first_expected = expected.strip()

            if passed == len(fam.tests) or first_verdict == "time_limit_exceeded":
                dropped.append(
                    {
                        "family_id": fam.family_id,
                        "mutation": mut_name,
                        "reason": f"verdict={first_verdict}, passed={passed}/{len(fam.tests)}",
                    }
                )
                continue

            exc_name = extract_exception_name(first_stderr, first_compile)
            rows.append(
                {
                    "sample_id": f"{fam.family_id}__{mut_name}",
                    "program_family": fam.family_id,
                    "topic": fam.topic,
                    "mutation": mut_name,
                    "label": label,
                    "source_code": buggy_code,
                    "verdict": first_verdict,
                    "exception_name": exc_name,
                    "stderr": first_stderr,
                    "compile_output": first_compile,
                    "stdout_actual": first_actual,
                    "stdout_expected": first_expected,
                    "passed_tests": passed,
                    "total_tests": len(fam.tests),
                }
            )

    df = pd.DataFrame(rows)
    csv_path = output_dir / "python_errors_v1.csv"
    df.to_csv(csv_path, index=False)

    summary = {
        "dataset_version": "python_errors_v1",
        "total_families": len(families),
        "validated_samples": int(len(df)),
        "dropped_samples": len(dropped),
        "class_distribution": {k: int(v) for k, v in df["label"].value_counts().sort_index().items()},
        "dropped_details": dropped,
    }
    meta_path = output_dir / "python_errors_v1_metadata.json"
    meta_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parents[1] / "datasets"
    stats = generate_validated_dataset(out_dir)
    print(json.dumps(stats, indent=2))
