import { z } from "zod";
import { publicEnv } from "@/lib/env";
import {
  userMeResponseSchema,
  type OnboardingFormValues,
  type UserMeResponse,
} from "@/types/identity";

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

async function parseErrorResponse(response: Response): Promise<ApiClientError> {
  try {
    const data = (await response.json()) as {
      code?: string;
      message?: string;
    };
    return new ApiClientError(
      data.message || `Request failed with HTTP ${response.status}`,
      response.status,
      data.code || `HTTP_${response.status}`,
    );
  } catch {
    return new ApiClientError(
      `Request failed with HTTP ${response.status}`,
      response.status,
      `HTTP_${response.status}`,
    );
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

export async function fetchCurrentUser(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<UserMeResponse> {
  const response = await fetch(`${baseUrl}/api/v1/users/me`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const payload: unknown = await response.json();
  return userMeResponseSchema.parse(payload);
}

export async function submitOnboarding(
  accessToken: string,
  values: OnboardingFormValues,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<UserMeResponse> {
  const response = await fetch(`${baseUrl}/api/v1/users/me/onboarding`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(values),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const payload: unknown = await response.json();
  return userMeResponseSchema.parse(payload);
}

export async function updateUserPreferences(
  accessToken: string,
  values: Partial<Omit<OnboardingFormValues, "full_name">>,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<UserMeResponse> {
  const response = await fetch(`${baseUrl}/api/v1/users/me/preferences`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(values),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const payload: unknown = await response.json();
  return userMeResponseSchema.parse(payload);
}
