"use client";

import { ServiceUnavailableState } from "@/components/service-unavailable-state";

export default function AdminErrorBoundary({
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
          ? "Admin Console Temporarily Unavailable"
          : "Unable to Load Admin Console"
      }
      message={
        isBackendError
          ? "We could not reach the backend service to load platform telemetry and user governance data."
          : "An unexpected error occurred while loading the Admin Console."
      }
      onRetry={reset}
    />
  );
}
