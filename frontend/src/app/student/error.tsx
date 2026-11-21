"use client";

import { ServiceUnavailableState } from "@/components/service-unavailable-state";

export default function PortalErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const isBackendError =
    error.name === "BackendUnavailableError" ||
    error.message.toLowerCase().includes("fetch failed") ||
    error.message.toLowerCase().includes("unable to connect");

  return (
    <ServiceUnavailableState
      title={
        isBackendError
          ? "Student Workspace Temporarily Unavailable"
          : "Unable to Load Student Workspace"
      }
      message={
        isBackendError
          ? "We could not reach the learning server to load your lessons, progress, or problem bank. Please try again in a moment."
          : "An unexpected error occurred while loading your student workspace. You can retry safely."
      }
      onRetry={reset}
    />
  );
}
