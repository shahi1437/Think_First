import { z } from "zod";
import { publicEnv } from "@/lib/env";

export const apiMetaSchema = z.object({
  service: z.string(),
  api_version: z.literal("v1"),
  app_version: z.string(),
  environment: z.string(),
  request_id: z.string(),
});

export const healthReadySchema = z.object({
  status: z.enum(["ok", "degraded"]),
  service: z.string(),
  version: z.string(),
  database: z.enum(["ok", "unavailable"]),
});

export type ApiMeta = z.infer<typeof apiMetaSchema>;
export type HealthReady = z.infer<typeof healthReadySchema>;

export interface BackendConnectivityStatus {
  meta: ApiMeta;
  readiness: HealthReady;
  readinessHttpStatus: number;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code = "API_ERROR") {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
  }
}

export async function fetchBackendConnectivity(
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<BackendConnectivityStatus> {
  const [metaResponse, readyResponse] = await Promise.all([
    fetch(`${baseUrl}/api/v1/meta`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    }),
    fetch(`${baseUrl}/health/ready`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    }),
  ]);

  if (!metaResponse.ok) {
    throw new ApiClientError(
      `API metadata check failed with HTTP ${metaResponse.status}`,
      metaResponse.status,
      "META_CHECK_FAILED",
    );
  }

  const metaJson: unknown = await metaResponse.json();
  const readyJson: unknown = await readyResponse.json();

  return {
    meta: apiMetaSchema.parse(metaJson),
    readiness: healthReadySchema.parse(readyJson),
    readinessHttpStatus: readyResponse.status,
  };
}
