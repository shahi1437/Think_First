import { z } from "zod";

export function normalizeBaseUrl(raw: string, stripApiPrefix = false): string {
  let cleaned = raw.trim().replace(/\/+$/, "");
  if (stripApiPrefix) {
    cleaned = cleaned.replace(/\/api\/v1$/i, "").replace(/\/+$/, "");
  }
  return cleaned;
}

const publicEnvSchema = z.object({
  NEXT_PUBLIC_APP_URL: z.url().default("http://localhost:3000"),
  NEXT_PUBLIC_API_BASE_URL: z.url().default("http://localhost:8000"),
  NEXT_PUBLIC_SUPABASE_URL: z.string().default(""),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().default(""),
});

export const publicEnv = publicEnvSchema.parse({
  NEXT_PUBLIC_APP_URL: normalizeBaseUrl(
    process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  ),
  NEXT_PUBLIC_API_BASE_URL: normalizeBaseUrl(
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    true,
  ),
  NEXT_PUBLIC_SUPABASE_URL: (process.env.NEXT_PUBLIC_SUPABASE_URL || "").trim(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: (
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""
  ).trim(),
});

export function isSupabaseConfigured(): boolean {
  return (
    publicEnv.NEXT_PUBLIC_SUPABASE_URL.startsWith("http") &&
    publicEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY.length > 10 &&
    !publicEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY.includes("replace-with")
  );
}
