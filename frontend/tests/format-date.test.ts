import { describe, expect, it } from "vitest";
import {
  formatUtcDate,
  formatUtcDateTime,
  formatUtcTime,
} from "@/lib/format-date";

describe("format-date deterministic UTC utilities", () => {
  it("renders identical UTC strings across environments without timezone drift", () => {
    const iso = "2026-11-28T14:35:09.000Z";
    expect(formatUtcDateTime(iso)).toBe("Nov 28, 2026, 14:35 UTC");
    expect(formatUtcDate(iso)).toBe("Nov 28, 2026");
    expect(formatUtcTime(iso)).toBe("14:35:09 UTC");
  });

  it("handles null, undefined, and invalid date inputs safely", () => {
    expect(formatUtcDateTime(null)).toBe("");
    expect(formatUtcDate(undefined)).toBe("");
    expect(formatUtcTime("not-a-date")).toBe("");
  });
});
