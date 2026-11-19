"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Loader2,
  RefreshCw,
  Server,
} from "lucide-react";
import {
  fetchBackendConnectivity,
  type BackendConnectivityStatus,
} from "@/lib/api-client";

interface SystemStatusCardProps {
  fetchStatus?: () => Promise<BackendConnectivityStatus>;
}

export function SystemStatusCard({
  fetchStatus = () => fetchBackendConnectivity(),
}: SystemStatusCardProps) {
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["backend-connectivity"],
    queryFn: fetchStatus,
    retry: false,
  });

  return (
    <section
      aria-labelledby="system-connectivity-heading"
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
            <Server className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2
              id="system-connectivity-heading"
              className="text-base font-semibold text-slate-900"
            >
              Platform Connectivity Check
            </h2>
            <p className="text-sm text-slate-600">
              Live FastAPI &amp; PostgreSQL readiness probe
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            void refetch();
          }}
          disabled={isFetching}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-800 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw
            className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
            aria-hidden="true"
          />
          {isFetching ? "Checking..." : "Re-check"}
        </button>
      </div>

      <div className="mt-4" aria-live="polite">
        {isLoading ? (
          <div className="flex items-center gap-3 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
            <Loader2
              className="h-4 w-4 animate-spin text-indigo-600"
              aria-hidden="true"
            />
            <span>Checking FastAPI backend connectivity...</span>
          </div>
        ) : isError ? (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
          >
            <AlertTriangle
              className="mt-0.5 h-4 w-4 shrink-0 text-rose-600"
              aria-hidden="true"
            />
            <div>
              <p className="font-medium">Backend API unreachable</p>
              <p className="mt-1 text-rose-800">
                {error instanceof Error
                  ? error.message
                  : "Unable to connect to the FastAPI service."}
              </p>
            </div>
          </div>
        ) : data ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-emerald-200 bg-emerald-50/70 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-900">
                <CheckCircle2
                  className="h-4 w-4 text-emerald-600"
                  aria-hidden="true"
                />
                <span>API Server Connected</span>
              </div>
              <dl className="mt-3 space-y-1 text-xs text-slate-700">
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Service</dt>
                  <dd className="font-medium text-slate-900">
                    {data.meta.service}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Contract</dt>
                  <dd className="font-mono text-slate-900">
                    {data.meta.api_version} ({data.meta.app_version})
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Request ID</dt>
                  <dd className="truncate font-mono text-slate-900">
                    {data.meta.request_id}
                  </dd>
                </div>
              </dl>
            </div>

            <div
              className={`rounded-lg border p-4 ${
                data.readiness.database === "ok"
                  ? "border-teal-200 bg-teal-50/70"
                  : "border-amber-200 bg-amber-50/80"
              }`}
            >
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Database
                  className={`h-4 w-4 ${
                    data.readiness.database === "ok"
                      ? "text-teal-700"
                      : "text-amber-700"
                  }`}
                  aria-hidden="true"
                />
                <span>
                  PostgreSQL:{" "}
                  {data.readiness.database === "ok" ? "Ready" : "Unavailable"}
                </span>
              </div>
              <p className="mt-2 text-xs text-slate-700">
                {data.readiness.database === "ok"
                  ? "Database probe succeeded via asyncpg / SQLAlchemy 2.x."
                  : "API is running, but PostgreSQL is not reachable yet (HTTP 503). Start Docker Postgres to verify full readiness."}
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
