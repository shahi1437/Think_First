import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OnboardingForm } from "@/features/onboarding/onboarding-form";
import type { UserMeResponse } from "@/types/identity";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
}));

const baseUser: UserMeResponse = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "amina@example.edu",
  full_name: "",
  roles: ["student"],
  onboarding_completed: false,
  preferences: null,
};

describe("OnboardingForm", () => {
  it("validates required name and practice time bounds", async () => {
    const submitSpy = vi.fn();
    render(
      <OnboardingForm
        mode="onboarding"
        accessToken="token-123"
        initialUser={baseUser}
        onSubmitValues={submitSpy}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Available daily practice time/i), {
      target: { value: "5" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Complete onboarding/i }),
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Please enter your full name/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Choose at least 10 minutes per day/i),
      ).toBeInTheDocument();
    });
    expect(submitSpy).not.toHaveBeenCalled();
  });

  it("submits all 6 onboarding fields and displays recommended entry track", async () => {
    pushMock.mockClear();
    const updatedUser: UserMeResponse = {
      ...baseUser,
      full_name: "Amina Rahman",
      onboarding_completed: true,
      preferences: {
        programming_experience: "none",
        preferred_language: "python",
        learning_goal: "school_fundamentals",
        daily_practice_minutes: 30,
        preferred_explanation_language: "bn",
        starting_preference: "guided_beginner",
        recommended_entry_track: "foundation_lessons",
        recommendation_rationale:
          "Starting with structured foundation lessons before the diagnostic assessment.",
      },
    };

    const submitSpy = vi.fn().mockResolvedValue(updatedUser);
    render(
      <OnboardingForm
        mode="onboarding"
        accessToken="token-123"
        initialUser={baseUser}
        onSubmitValues={submitSpy}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Full name/i), {
      target: { value: "Amina Rahman" },
    });
    fireEvent.change(screen.getByLabelText(/Primary learning goal/i), {
      target: { value: "school_fundamentals" },
    });
    fireEvent.change(screen.getByLabelText(/Preferred explanation language/i), {
      target: { value: "bn" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Complete onboarding/i }),
    );

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith({
        full_name: "Amina Rahman",
        programming_experience: "none",
        preferred_language: "python",
        learning_goal: "school_fundamentals",
        daily_practice_minutes: 30,
        preferred_explanation_language: "bn",
        starting_preference: "guided_beginner",
      });
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        "foundation_lessons",
      );
    });
    expect(pushMock).toHaveBeenCalledWith("/student");
  });
});
