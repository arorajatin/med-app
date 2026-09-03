import { describe, expect, it } from "vitest";
import { formatDecimal, formatReportedDate } from "./format";

describe("formatReportedDate", () => {
  it("reads a timestamp without an offset as UTC", () => {
    // 23:30 UTC is the next day in Asia/Kolkata, and the same day either way
    // only if the value is not treated as local time.
    expect(formatReportedDate("2026-07-01T23:30:00")).toBe(
      formatReportedDate("2026-07-01T23:30:00Z"),
    );
  });

  it("keeps an explicit offset", () => {
    expect(formatReportedDate("2026-07-01T00:00:00+05:30")).toContain("2026");
  });

  it("falls back when the value is missing or unusable", () => {
    expect(formatReportedDate(null)).toBe("date unknown");
    expect(formatReportedDate("not a date")).toBe("date unknown");
  });
});

describe("formatDecimal", () => {
  it("drops the exact decimal's trailing zeros", () => {
    expect(formatDecimal("61.50000000")).toBe("61.5");
    expect(formatDecimal("150.00000000")).toBe("150");
    expect(formatDecimal("70")).toBe("70");
    expect(formatDecimal(null)).toBe("");
  });
});
