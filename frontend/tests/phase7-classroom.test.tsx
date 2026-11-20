import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StudentAssignmentsClient } from "@/features/student-classroom/student-assignments-client";
import { StudentClassesClient } from "@/features/student-classroom/student-classes-client";
import { TeacherClassesClient } from "@/features/teacher/teacher-classes-client";
import { TeacherDashboardClient } from "@/features/teacher/teacher-dashboard-client";
import type {
  CourseSummaryView,
  StudentAssignmentListItemView,
  StudentEnrolledCourseView,
  TeacherDashboardView,
} from "@/types/classroom";

const mockCourses: CourseSummaryView[] = [
  {
    id: "course-1",
    teacher_id: "teacher-1",
    teacher_name: "Prof. Rahman",
    code: "CSE101-A",
    title: "Structured Programming Lab",
    description: "Python fundamentals & debugging lab.",
    term: "Fall 2026",
    enrollment_policy: "open_with_code",
    allow_student_leave: true,
    status: "active",
    active_students_count: 18,
    pending_students_count: 1,
    assignments_count: 2,
    created_at: "2026-11-20T08:00:00Z",
    updated_at: "2026-11-20T08:00:00Z",
  },
];

const mockDashboard: TeacherDashboardView = {
  courses_count: 1,
  active_courses_count: 1,
  total_enrolled_students: 18,
  active_assignments_count: 2,
  pending_grading_count: 3,
  graded_submissions_count: 12,
  courses: mockCourses,
  upcoming_deadlines: [
    {
      id: "asg-1",
      course_id: "course-1",
      course_code: "CSE101-A",
      course_title: "Structured Programming Lab",
      title: "Lab 1: Loop Boundary Debugging",
      status: "published",
      opens_at: null,
      due_at: "2026-11-25T18:00:00Z",
      max_marks: 50,
      max_attempts: 3,
      allow_ai_hints: true,
      hint_limit: 2,
      allow_late_submissions: false,
      allow_resubmission_on_revision: true,
      problem_count: 1,
      enrolled_students_count: 18,
      submitted_count: 15,
      graded_count: 12,
      pending_grading_count: 3,
      created_at: "2026-11-20T08:00:00Z",
    },
  ],
  analytics: {
    active_students: 18,
    total_attempts: 34,
    accepted_attempts: 22,
    verdict_breakdown: [
      { verdict: "accepted", count: 22 },
      { verdict: "wrong_answer", count: 12 },
    ],
    common_misconceptions: [
      { error_code: "loop_boundary_error", occurrences: 9 },
    ],
    skill_gaps: [
      {
        skill_slug: "loops",
        unobserved_or_guided_count: 6,
        verified_count: 12,
      },
    ],
    total_hints_used: 14,
    verified_independent_transfers: 8,
    students_needing_support: [
      {
        student_id: "stu-1",
        full_name: "Nadia Islam",
        email: "nadia@thinkfirst.test",
        course_title: "Structured Programming Lab",
        reason: "2 non-accepted Judge0 assignment attempt(s) with 0 accepted.",
        failed_attempts: 2,
        hints_used: 2,
      },
    ],
  },
  methodology_note:
    "All dashboard counts are computed strictly from real database records.",
};

const mockStudentClasses: StudentEnrolledCourseView[] = [
  {
    membership_id: "mem-1",
    course_id: "course-1",
    code: "CSE101-A",
    title: "Structured Programming Lab",
    description: "Python fundamentals & debugging lab.",
    term: "Fall 2026",
    teacher_name: "Prof. Rahman",
    course_status: "active",
    membership_status: "active",
    allow_student_leave: true,
    published_assignments_count: 2,
    joined_at: "2026-11-20T08:00:00Z",
  },
];

const mockStudentAssignments: StudentAssignmentListItemView[] = [
  {
    assignment_id: "asg-1",
    course_id: "course-1",
    course_code: "CSE101-A",
    course_title: "Structured Programming Lab",
    title: "Lab 1: Loop Boundary Debugging",
    opens_at: null,
    due_at: "2026-11-25T18:00:00Z",
    max_marks: 50,
    max_attempts: 3,
    allow_ai_hints: true,
    hint_limit: 2,
    allow_late_submissions: false,
    allow_resubmission_on_revision: true,
    problem_count: 1,
    workflow_status: "graded",
    attempts_used: 2,
    is_overdue: false,
    is_late: false,
    released_marks: 48,
    released_grade_status: "published",
    submitted_at: "2026-11-20T09:00:00Z",
  },
];

describe("Phase 7 Teacher Dashboard, Classrooms & Student Assignments UI", () => {
  it("renders Teacher Dashboard analytics and supports Bangla toggle", () => {
    render(
      <TeacherDashboardClient
        teacherName="Prof. Rahman"
        initialDashboard={mockDashboard}
      />,
    );
    expect(
      screen.getByText(/Structured Programming Lab/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/loop_boundary_error/i)).toBeInTheDocument();
    expect(screen.getByText(/Nadia Islam/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "বাংলা" }));
    expect(
      screen.getByText(/শিক্ষক ড্যাশবোর্ড ও ক্লাসরুম অ্যানালিটিক্স/i),
    ).toBeInTheDocument();
  });

  it("renders Teacher Classes management form and course cards", () => {
    render(
      <TeacherClassesClient accessToken="tok" initialClasses={mockCourses} />,
    );
    expect(screen.getByText(/CSE101-A/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Create Class/i }),
    ).toBeInTheDocument();
  });

  it("renders Student Classes and Student Assignments with released grades", () => {
    render(
      <StudentClassesClient
        accessToken="tok"
        initialClasses={mockStudentClasses}
      />,
    );
    expect(
      screen.getByRole("button", { name: /Join Class/i }),
    ).toBeInTheDocument();

    render(
      <StudentAssignmentsClient
        accessToken="tok"
        initialAssignments={mockStudentAssignments}
      />,
    );
    expect(
      screen.getByText(/Lab 1: Loop Boundary Debugging/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Grade: 48 \/ 50/i)).toBeInTheDocument();
  });
});
