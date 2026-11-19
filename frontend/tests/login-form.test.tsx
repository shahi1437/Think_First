import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LoginForm } from "@/features/auth/login-form";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
}));

describe("LoginForm", () => {
  it("validates email and minimum password length before authenticating", async () => {
    const onAuthenticate = vi.fn().mockResolvedValue(undefined);
    render(<LoginForm onAuthenticate={onAuthenticate} />);

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "not-an-email" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "short" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Please enter a valid email address/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Password must be at least 8 characters/i),
      ).toBeInTheDocument();
    });
    expect(onAuthenticate).not.toHaveBeenCalled();
  });

  it("submits valid credentials and redirects to safe next path", async () => {
    pushMock.mockClear();
    refreshMock.mockClear();
    const onAuthenticate = vi.fn().mockResolvedValue(undefined);
    render(<LoginForm nextPath="/student/onboarding" onAuthenticate={onAuthenticate} />);

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "student@university.edu" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "securepass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => {
      expect(onAuthenticate).toHaveBeenCalledWith({
        email: "student@university.edu",
        password: "securepass123",
      });
    });
    expect(pushMock).toHaveBeenCalledWith("/student/onboarding");
    expect(refreshMock).toHaveBeenCalled();
  });

  it("blocks open-redirect URLs in nextPath", async () => {
    pushMock.mockClear();
    const onAuthenticate = vi.fn().mockResolvedValue(undefined);
    render(<LoginForm nextPath="//evil.example.com" onAuthenticate={onAuthenticate} />);

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "student@university.edu" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "securepass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/student");
    });
  });
});
