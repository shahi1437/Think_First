"use client";

import { ServiceUnavailableState } from "@/components/service-unavailable-state";

export default function TeacherErrorBoundary({
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
          ? "Teacher Portal Temporarily Unavailable"
          : "Unable to Load Teacher Portal"
      }
      message={
        isBackendError
          ? "We could not reach the learning server to load your classes and student submissions. Please try again shortly."
          : "An unexpected error occurred while loading the Teacher Portal."
      }
      onRetry={reset}
    />
  );
}
