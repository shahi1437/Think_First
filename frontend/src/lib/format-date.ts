/**
 * Deterministic UTC date/time formatting utilities.
 *
 * Pinning both locale ("en-US") and timeZone ("UTC") guarantees identical output
 * between Next.js SSR (Node/Vercel UTC) and client hydration in any browser timezone,
 * eliminating React Hydration Error #418 without using suppressHydrationWarning.
 */

const UTC_DATE_TIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const UTC_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  year: "numeric",
  month: "short",
  day: "2-digit",
});

const UTC_TIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

function parseDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const parsed = value instanceof Date ? value : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** Format an ISO timestamp deterministically in UTC, e.g. "Nov 28, 2026, 14:35 UTC". */
export function formatUtcDateTime(value: string | Date | null | undefined): string {
  const parsed = parseDate(value);
  if (!parsed) return "";
  return `${UTC_DATE_TIME_FORMATTER.format(parsed)} UTC`;
}

/** Format an ISO timestamp deterministically as a UTC date, e.g. "Nov 28, 2026". */
export function formatUtcDate(value: string | Date | null | undefined): string {
  const parsed = parseDate(value);
  if (!parsed) return "";
  return UTC_DATE_FORMATTER.format(parsed);
}

/** Format an ISO timestamp deterministically as a UTC clock time, e.g. "14:35:09 UTC". */
export function formatUtcTime(value: string | Date | null | undefined): string {
  const parsed = parseDate(value);
  if (!parsed) return "";
  return `${UTC_TIME_FORMATTER.format(parsed)} UTC`;
}
