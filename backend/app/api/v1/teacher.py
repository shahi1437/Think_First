"""Phase 7 Teacher Portal API endpoints (strict DB-backed teacher/admin RBAC + class ownership)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import (
    get_assignment_service,
    get_classroom_course_service,
    get_grading_service,
    get_teacher_analytics_service,
    require_roles,
)
from app.repositories.identity import UserRecord
from app.schemas.classroom import (
    AssignmentCreateRequest,
    AssignmentSummaryView,
    AssignmentUpdateRequest,
    ClassInvitationView,
    CourseCreateRequest,
    CourseSummaryView,
    CourseUpdateRequest,
    GradeSubmissionRequest,
    InvitationCreateRequest,
    MembershipActionRequest,
    RosterMemberView,
    TeacherAssignmentDetailView,
    TeacherCourseDetailView,
    TeacherDashboardView,
    TeacherSubmissionReviewItem,
)
from app.services.classroom.analytics_service import TeacherAnalyticsService
from app.services.classroom.assignment_service import AssignmentService
from app.services.classroom.course_service import ClassroomCourseService
from app.services.classroom.grading_service import GradingService

teacher_classroom_router = APIRouter(prefix="/teacher", tags=["teacher-classroom-phase7"])

_TEACHER_ROLES = require_roles("teacher", "admin")


@teacher_classroom_router.get("/dashboard", response_model=TeacherDashboardView)
async def get_teacher_dashboard(
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: TeacherAnalyticsService = Depends(get_teacher_analytics_service),
) -> TeacherDashboardView:
    """Return real aggregated Teacher Dashboard across authorized classes."""
    return await service.get_teacher_dashboard(teacher)


@teacher_classroom_router.get("/classes", response_model=list[CourseSummaryView])
async def list_teacher_classes(
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> list[CourseSummaryView]:
    """List classes taught by the authenticated teacher."""
    return await service.list_teacher_courses(teacher)


@teacher_classroom_router.post(
    "/classes",
    response_model=CourseSummaryView,
    status_code=status.HTTP_201_CREATED,
)
async def create_teacher_class(
    payload: CourseCreateRequest,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> CourseSummaryView:
    """Create a new class and generate an initial high-entropy invitation code."""
    return await service.create_course(teacher=teacher, payload=payload)


@teacher_classroom_router.get("/classes/{course_id}", response_model=TeacherCourseDetailView)
async def get_teacher_class_detail(
    course_id: UUID,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: TeacherAnalyticsService = Depends(get_teacher_analytics_service),
) -> TeacherCourseDetailView:
    """Inspect class details, invitations, roster, assignments, and class-level analytics."""
    return await service.get_teacher_course_detail(teacher=teacher, course_id=course_id)


@teacher_classroom_router.patch("/classes/{course_id}", response_model=CourseSummaryView)
async def update_teacher_class(
    course_id: UUID,
    payload: CourseUpdateRequest,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> CourseSummaryView:
    """Edit class metadata and enrollment policy."""
    return await service.update_course(teacher=teacher, course_id=course_id, payload=payload)


@teacher_classroom_router.post("/classes/{course_id}/archive", response_model=CourseSummaryView)
async def archive_teacher_class(
    course_id: UUID,
    archive: bool = Query(default=True),
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> CourseSummaryView:
    """Archive or restore a class without losing historic records."""
    return await service.archive_course(teacher=teacher, course_id=course_id, archive=archive)


@teacher_classroom_router.post(
    "/classes/{course_id}/invitations",
    response_model=ClassInvitationView,
    status_code=status.HTTP_201_CREATED,
)
async def create_class_invitation(
    course_id: UUID,
    payload: InvitationCreateRequest,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> ClassInvitationView:
    """Generate a new high-entropy class invitation code."""
    return await service.create_invitation(teacher=teacher, course_id=course_id, payload=payload)


@teacher_classroom_router.post(
    "/classes/{course_id}/invitations/{invitation_id}/revoke",
    response_model=ClassInvitationView,
)
async def revoke_class_invitation(
    course_id: UUID,
    invitation_id: UUID,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> ClassInvitationView:
    """Revoke an active class invitation code."""
    return await service.revoke_invitation(
        teacher=teacher, course_id=course_id, invitation_id=invitation_id
    )


@teacher_classroom_router.patch(
    "/classes/{course_id}/memberships/{membership_id}",
    response_model=RosterMemberView,
)
async def manage_class_membership(
    course_id: UUID,
    membership_id: UUID,
    payload: MembershipActionRequest,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: ClassroomCourseService = Depends(get_classroom_course_service),
) -> RosterMemberView:
    """Approve a pending student or remove a student from the class roster."""
    return await service.manage_membership(
        teacher=teacher,
        course_id=course_id,
        membership_id=membership_id,
        payload=payload,
    )


@teacher_classroom_router.get("/assignments", response_model=list[AssignmentSummaryView])
async def list_teacher_assignments(
    course_id: UUID | None = Query(default=None),
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: AssignmentService = Depends(get_assignment_service),
) -> list[AssignmentSummaryView]:
    """List assignments across authorized classes."""
    return await service.list_teacher_assignments(teacher=teacher, course_id=course_id)


@teacher_classroom_router.post(
    "/assignments",
    response_model=AssignmentSummaryView,
    status_code=status.HTTP_201_CREATED,
)
async def create_teacher_assignment(
    payload: AssignmentCreateRequest,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: AssignmentService = Depends(get_assignment_service),
) -> AssignmentSummaryView:
    """Create a draft or published assignment pinned to Admin-approved problem versions."""
    return await service.create_assignment(teacher=teacher, payload=payload)


@teacher_classroom_router.get(
    "/assignments/{assignment_id}",
    response_model=TeacherAssignmentDetailView,
)
async def get_teacher_assignment_detail(
    assignment_id: UUID,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: GradingService = Depends(get_grading_service),
) -> TeacherAssignmentDetailView:
    """Inspect assignment metadata, pinned problems, student submissions, grades, and audit logs."""
    return await service.get_teacher_assignment_detail(teacher=teacher, assignment_id=assignment_id)


@teacher_classroom_router.patch(
    "/assignments/{assignment_id}",
    response_model=AssignmentSummaryView,
)
async def update_teacher_assignment(
    assignment_id: UUID,
    payload: AssignmentUpdateRequest,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: AssignmentService = Depends(get_assignment_service),
) -> AssignmentSummaryView:
    """Edit an unpublished draft assignment."""
    return await service.update_assignment(
        teacher=teacher, assignment_id=assignment_id, payload=payload
    )


@teacher_classroom_router.post(
    "/assignments/{assignment_id}/publish",
    response_model=AssignmentSummaryView,
)
async def publish_teacher_assignment(
    assignment_id: UUID,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: AssignmentService = Depends(get_assignment_service),
) -> AssignmentSummaryView:
    """Publish a draft assignment to enrolled students."""
    return await service.set_assignment_status(
        teacher=teacher, assignment_id=assignment_id, target_status="published"
    )


@teacher_classroom_router.post(
    "/assignments/{assignment_id}/archive",
    response_model=AssignmentSummaryView,
)
async def archive_teacher_assignment(
    assignment_id: UUID,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: AssignmentService = Depends(get_assignment_service),
) -> AssignmentSummaryView:
    """Archive an assignment safely while retaining historical submissions and grades."""
    return await service.set_assignment_status(
        teacher=teacher, assignment_id=assignment_id, target_status="archived"
    )


@teacher_classroom_router.post(
    "/submissions/{submission_id}/grade",
    response_model=TeacherSubmissionReviewItem,
)
async def grade_student_submission(
    submission_id: UUID,
    payload: GradeSubmissionRequest,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: GradingService = Depends(get_grading_service),
) -> TeacherSubmissionReviewItem:
    """Save draft grade, publish grade, or request revision with immutable audit trail."""
    return await service.grade_submission(
        teacher=teacher, submission_id=submission_id, payload=payload
    )
