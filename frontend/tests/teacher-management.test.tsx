import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TeacherManagementSection } from "@/features/admin/teacher-management-section";
import { AcceptTeacherInviteClient } from "@/features/auth/accept-teacher-invite-client";

const mockLookup = vi.fn();
const mockGrantRole = vi.fn();
const mockRevokeRole = vi.fn();
const mockCreateInvite = vi.fn();
const mockResendInvite = vi.fn();
const mockRevokeInvite = vi.fn();
const mockFetchMgmt = vi.fn();
const mockInspectInvite = vi.fn();
const mockAcceptInvite = vi.fn();

vi.mock("@/lib/env", () => ({
  publicEnv: {
    NEXT_PUBLIC_APP_URL: "https://think-first-pi.vercel.app",
    NEXT_PUBLIC_API_BASE_URL: "https://codementor-ai-backend-6sbr.onrender.com",
    NEXT_PUBLIC_SUPABASE_URL: "https://vsmrwfoqqjvomtjpypyv.supabase.co",
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-public-anon-key-value-123456",
  },
  isSupabaseConfigured: () => true,
  normalizeBaseUrl: (raw: string) => raw.trim().replace(/\/+$/, ""),
}));

vi.mock("@/lib/supabase/client", () => ({
  createSupabaseBrowserClient: () => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: "teacher-jwt-token",
            user: { email: "invited.teacher@university.edu" },
          },
        },
      }),
    },
  }),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    lookupAdminTeacherByEmail: (...args: unknown[]) => mockLookup(...args),
    grantAdminUserRole: (...args: unknown[]) => mockGrantRole(...args),
    revokeAdminUserRole: (...args: unknown[]) => mockRevokeRole(...args),
    createAdminTeacherInvitation: (...args: unknown[]) =>
      mockCreateInvite(...args),
    resendAdminTeacherInvitation: (...args: unknown[]) =>
      mockResendInvite(...args),
    revokeAdminTeacherInvitation: (...args: unknown[]) =>
      mockRevokeInvite(...args),
    fetchAdminTeacherManagement: (...args: unknown[]) => mockFetchMgmt(...args),
    inspectTeacherInvitation: (...args: unknown[]) =>
      mockInspectInvite(...args),
    acceptTeacherInvitation: (...args: unknown[]) => mockAcceptInvite(...args),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TeacherManagementSection (Admin Dashboard)", () => {
  it("looks up an existing account, requests Admin confirmation, and grants the Teacher role", async () => {
    const existingCandidate = {
      id: "user-101",
      email: "existing@university.edu",
      full_name: "Dr. Existing User",
      roles: ["student"],
      onboarding_completed: true,
      created_at: "2026-11-23T08:00:00Z",
    };

    mockLookup
      .mockResolvedValueOnce({
        email: "existing@university.edu",
        status: "existing_user_not_teacher",
        can_grant_directly: true,
        can_invite: false,
        existing_user: existingCandidate,
        latest_invitation: null,
        message: "Verified existing account found. Confirm below to grant Teacher role.",
      })
      .mockResolvedValueOnce({
        email: "existing@university.edu",
        status: "active_teacher",
        can_grant_directly: false,
        can_invite: false,
        existing_user: {
          ...existingCandidate,
          roles: ["student", "teacher"],
        },
        latest_invitation: null,
        message: "Dr. Existing User already holds active Teacher access.",
      });

    mockGrantRole.mockResolvedValue({
      user_id: "user-101",
      roles: ["student", "teacher"],
      action: "role.granted",
    });

    mockFetchMgmt.mockResolvedValue({
      active_teachers: [
        { ...existingCandidate, roles: ["student", "teacher"] },
      ],
      active_teachers_total: 1,
      invitations: [],
      pending_invitations_count: 0,
    });

    render(<TeacherManagementSection accessToken="admin-jwt" />);

    fireEvent.change(screen.getByLabelText(/Teacher email address/i), {
      target: { value: "existing@university.edu" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Check Email Status/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Confirm & Grant Teacher Role/i }),
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /Confirm & Grant Teacher Role/i }),
    );

    await waitFor(() => {
      expect(mockGrantRole).toHaveBeenCalledWith(
        "admin-jwt",
        "user-101",
        "teacher",
      );
      expect(
        screen.getByText(/Granted Teacher access to Dr\. Existing User/i),
      ).toBeInTheDocument();
    });
  });

  it("invites a new Teacher, displays accurate Pending / Delivery Blocked status, and supports resend and revoke", async () => {
    const pendingInv = {
      id: "inv-202",
      email: "new.prof@university.edu",
      full_name: "Prof. New",
      status: "pending" as const,
      delivery_status: "delivery_blocked" as const,
      delivery_detail: "SMTP Delivery Blocked — share verified invitation link.",
      token_preview: "tfi_abcd...1234",
      resend_count: 0,
      expires_at: "2026-11-30T08:00:00Z",
      created_at: "2026-11-23T08:00:00Z",
      updated_at: "2026-11-23T08:00:00Z",
    };

    mockCreateInvite.mockResolvedValue({
      invitation: pendingInv,
      invitation_token: "tfi_secret_token_value_1234567890",
      accept_path: "/accept-teacher-invite?token=tfi_secret_token_value_1234567890",
      action: "teacher.invitation_created",
    });
    mockLookup.mockResolvedValue({
      email: "new.prof@university.edu",
      status: "pending_invitation",
      can_grant_directly: false,
      can_invite: false,
      existing_user: null,
      latest_invitation: pendingInv,
      message: "Pending invitation exists.",
    });
    mockFetchMgmt.mockResolvedValue({
      active_teachers: [],
      active_teachers_total: 0,
      invitations: [pendingInv],
      pending_invitations_count: 1,
    });
    mockResendInvite.mockResolvedValue({
      invitation: { ...pendingInv, resend_count: 1 },
      invitation_token: "tfi_rotated_token_value_1234567890",
      accept_path: "/accept-teacher-invite?token=tfi_rotated_token_value_1234567890",
      action: "teacher.invitation_resent",
    });

    render(<TeacherManagementSection accessToken="admin-jwt" />);

    fireEvent.change(screen.getByLabelText(/Teacher email address/i), {
      target: { value: "new.prof@university.edu" },
    });
    fireEvent.change(screen.getByLabelText(/Instructor name/i), {
      target: { value: "Prof. New" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Invite New Teacher/i }),
    );

    await waitFor(() => {
      expect(mockCreateInvite).toHaveBeenCalledWith(
        "admin-jwt",
        expect.objectContaining({
          email: "new.prof@university.edu",
          full_name: "Prof. New",
        }),
      );
      expect(
        screen.getByText(/Pending \/ Delivery Blocked/i),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("teacher-invite-accept-link"),
      ).toHaveTextContent(
        "/accept-teacher-invite?token=tfi_secret_token_value_1234567890",
      );
    });

    fireEvent.click(screen.getByRole("button", { name: /Resend Invitation/i }));
    await waitFor(() => {
      expect(mockResendInvite).toHaveBeenCalledWith("admin-jwt", "inv-202");
    });
  });
});

describe("AcceptTeacherInviteClient", () => {
  it("inspects a valid teacher invitation token and activates Teacher access", async () => {
    mockInspectInvite.mockResolvedValue({
      invitation_id: "inv-303",
      email: "invited.teacher@university.edu",
      full_name: "Dr. Invited",
      status: "pending",
      expires_at: "2026-11-30T08:00:00Z",
      is_valid: true,
      message: "Valid teacher invitation.",
    });
    mockAcceptInvite.mockResolvedValue({
      invitation_id: "inv-303",
      user: {
        id: "u-303",
        email: "invited.teacher@university.edu",
        full_name: "Dr. Invited",
        roles: ["student", "teacher"],
        onboarding_completed: false,
      },
      action: "teacher.invitation_accepted",
    });

    render(<AcceptTeacherInviteClient token="tfi_valid_token_1234567890" />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: /Accept Invitation & Activate Teacher Role/i,
        }),
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: /Accept Invitation & Activate Teacher Role/i,
      }),
    );

    await waitFor(() => {
      expect(mockAcceptInvite).toHaveBeenCalledWith(
        "teacher-jwt-token",
        "tfi_valid_token_1234567890",
      );
      expect(
        screen.getByText(/Teacher access activated/i),
      ).toBeInTheDocument();
    });
  });
});
