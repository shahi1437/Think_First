"use client";

import { ServiceUnavailableState } from "@/components/service-unavailable-state";

export default function GlobalPortalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const isBackendError =
    error.name === "BackendUnavailableError" ||
    error.message.toLowerCase().includes("fetch failed") ||
    error.message.toLowerCase().includes("unable to reach");

  return (
    <main className="min-h-screen bg-slate-50">
      <ServiceUnavailableState
        title={
          isBackendError
            ? "Service Temporarily Unavailable"
            : "Something Went Wrong"
        }
        message={
          isBackendError
            ? "We could not connect to the learning backend right now. Please wait a moment and try again."
            : "An unexpected error occurred while loading this page. You can retry safely or return home."
        }
        onRetry={reset}
      />
    </main>
  );
}
