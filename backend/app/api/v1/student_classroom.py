"""Phase 7 Student Classroom & Assignment API endpoints (membership + server-side policy)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import (
    get_assignment_service,
    get_classroom_course_service,
    require_roles,
)
from app.repositories.identity import UserRecord
from app.schemas.classroom import (
    JoinClassRequest,
    StudentAssignmentAttemptResponse,
    StudentAssignmentDetailView,
    StudentAssignmentFilter,
    StudentAssignmentListItemView,
    StudentAssignmentSubmitRequest,
    StudentEnrolledCourseView,
)
from app.services.classroom.assignment_service import AssignmentService
from app.services.classroom.course_service import ClassroomCourseService

student_classroom_router = APIRouter(prefix="/student", tags=["student-classroom-phase7"])

_STUDENT_ROLES = require_roles("student", "teacher", "admin")


@student_classroom_router.get("/classes", response_model=list[StudentEnrolledCourseView])
async def list_student_classes(
    student: UserRecord = Depends(_STUDENT_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> list[StudentEnrolledCourseView]:
    """List classes where the authenticated student has an active or pending membership."""
    return await service.list_student_courses(student)


@student_classroom_router.post(
    "/classes/join",
    response_model=StudentEnrolledCourseView,
    status_code=status.HTTP_201_CREATED,
)
async def join_student_class(
    payload: JoinClassRequest,
    student: UserRecord = Depends(_STUDENT_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> StudentEnrolledCourseView:
    """Join an authorized class using a rate-limited, hashed invitation code."""
    return await service.join_class_with_code(student=student, payload=payload)


@student_classroom_router.post(
    "/classes/{course_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def leave_student_class(
    course_id: UUID,
    student: UserRecord = Depends(_STUDENT_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> None:
    """Leave an enrolled class if permitted by class policy."""
    await service.leave_class(student=student, course_id=course_id)


@student_classroom_router.get(
    "/assignments",
    response_model=list[StudentAssignmentListItemView],
)
async def list_student_assignments(
    filter_status: StudentAssignmentFilter = Query(default="all", alias="status"),
    student: UserRecord = Depends(_STUDENT_ROLES),
    service: AssignmentService = Depends(get_assignment_service),
) -> list[StudentAssignmentListItemView]:
    """List published assignments belonging to the student's active enrolled classes."""
    return await service.list_student_assignments(student=student, status_filter=filter_status)


@student_classroom_router.get(
    "/assignments/{assignment_id}",
    response_model=StudentAssignmentDetailView,
)
async def get_student_assignment_detail(
    assignment_id: UUID,
    student: UserRecord = Depends(_STUDENT_ROLES),
    service: AssignmentService = Depends(get_assignment_service),
) -> StudentAssignmentDetailView:
    """Inspect assignment details, pinned problems, attempts, released grade, and feedback."""
    return await service.get_student_assignment_detail(student=student, assignment_id=assignment_id)


@student_classroom_router.post(
    "/assignments/{assignment_id}/submit",
    response_model=StudentAssignmentAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_student_assignment(
    assignment_id: UUID,
    payload: StudentAssignmentSubmitRequest,
    student: UserRecord = Depends(_STUDENT_ROLES),
    service: AssignmentService = Depends(get_assignment_service),
) -> StudentAssignmentAttemptResponse:
    """Evaluate code on Judge0 and record an assignment attempt with server-enforced policies."""
    return await service.submit_student_assignment(
        student=student, assignment_id=assignment_id, payload=payload
    )
