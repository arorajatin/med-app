import { describe, expect, it } from "vitest";
import { readOptionalEnv } from "./env";

describe("readOptionalEnv", () => {
  it("keeps a real value", () => {
    expect(readOptionalEnv("https://api.example")).toBe("https://api.example");
  });

  it("trims surrounding whitespace", () => {
    expect(readOptionalEnv("  2026-07-01  ")).toBe("2026-07-01");
  });

  it("treats an unfilled .env line as unset", () => {
    // `VITE_API_BASE_URL=` arrives as an empty string, not as undefined, so a
    // nullish fallback alone would keep it and break every request path.
    expect(readOptionalEnv("")).toBeNull();
    expect(readOptionalEnv("   ")).toBeNull();
  });

  it("treats a missing variable as unset", () => {
    expect(readOptionalEnv(undefined)).toBeNull();
  });
});
