from datetime import UTC, datetime
from uuid import uuid4

from app.integrations.judge0.client import map_judge0_status_to_verdict
from app.models.problems import ExecutionResult
from app.models.problems import TestCase as ProblemTestCase
from app.services.execution.service import _aggregate_verdict, _sanitize_results


def test_judge0_status_mapping_covers_all_verdicts() -> None:
    assert map_judge0_status_to_verdict(3, None) == "accepted"
    assert map_judge0_status_to_verdict(4, None) == "wrong_answer"
    assert map_judge0_status_to_verdict(5, None) == "time_limit_exceeded"
    assert map_judge0_status_to_verdict(6, None) == "compilation_error"
    assert map_judge0_status_to_verdict(11, "ZeroDivisionError") == "runtime_error"
    assert map_judge0_status_to_verdict(11, "MemoryError: out of memory") == "memory_limit_exceeded"
    assert map_judge0_status_to_verdict(13, None) == "internal_error"


def test_verdict_aggregation_precedence() -> None:
    assert _aggregate_verdict(["accepted", "accepted"]) == "accepted"
    assert _aggregate_verdict(["accepted", "wrong_answer"]) == "wrong_answer"
    assert _aggregate_verdict(["wrong_answer", "runtime_error"]) == "runtime_error"
    assert _aggregate_verdict(["runtime_error", "compilation_error"]) == "compilation_error"
    assert _aggregate_verdict([]) == "internal_error"


def test_hidden_test_results_sanitized_for_students() -> None:
    version_id = uuid4()
    pub_id = uuid4()
    hid_id = uuid4()
    sub_id = uuid4()

    test_map = {
        pub_id: ProblemTestCase(
            id=pub_id,
            problem_version_id=version_id,
            ordinal=1,
            name="Public Case",
            input_data="1 2",
            expected_output="3",
            is_hidden=False,
            weight=1,
            created_at=datetime.now(UTC),
        ),
        hid_id: ProblemTestCase(
            id=hid_id,
            problem_version_id=version_id,
            ordinal=2,
            name="Secret Edge Case",
            input_data="-999 -1",
            expected_output="-1000",
            is_hidden=True,
            weight=1,
            created_at=datetime.now(UTC),
        ),
    }

    results = [
        ExecutionResult(
            id=uuid4(),
            submission_id=sub_id,
            test_case_id=pub_id,
            is_hidden=False,
            judge0_token="tok-1",
            judge0_status_id=3,
            verdict="accepted",
            stdout="3\n",
            stderr=None,
            compile_output=None,
            runtime_ms=15,
            memory_kb=3200,
            created_at=datetime.now(UTC),
        ),
        ExecutionResult(
            id=uuid4(),
            submission_id=sub_id,
            test_case_id=hid_id,
            is_hidden=True,
            judge0_token="tok-2",
            judge0_status_id=4,
            verdict="wrong_answer",
            stdout="0\n",
            stderr="secret trace",
            compile_output=None,
            runtime_ms=18,
            memory_kb=3400,
            created_at=datetime.now(UTC),
        ),
    ]

    student_view = _sanitize_results(results, test_map, reveal_hidden=False)
    assert len(student_view) == 2
    assert student_view[0].input_data == "1 2"
    assert student_view[0].expected_output == "3"
    assert student_view[0].stdout == "3\n"

    # Hidden test strictly strips name, input, expected output, stdout, stderr
    assert student_view[1].is_hidden is True
    assert student_view[1].name == "Hidden Test #2"
    assert student_view[1].verdict == "wrong_answer"
    assert student_view[1].input_data is None
    assert student_view[1].expected_output is None
    assert student_view[1].stdout is None
    assert student_view[1].stderr is None

    admin_view = _sanitize_results(results, test_map, reveal_hidden=True)
    assert admin_view[1].input_data == "-999 -1"
    assert admin_view[1].expected_output == "-1000"
